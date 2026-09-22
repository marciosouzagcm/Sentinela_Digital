#!/usr/bin/env python3
import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.osint.mod_emailharvester import run_emailharvester
from modules.osint.mod_ghunt import run_ghunt
from modules.osint.mod_gitleaks import run_gitleaks
from modules.osint.mod_h8mail import run_h8mail
from modules.osint.mod_holehe import run_holehe
from modules.osint.mod_maltego import run_maltego
from modules.osint.mod_recon_ng import run_recon_ng
from modules.osint.mod_sherlock import run_sherlock
from modules.osint.mod_theharvester import run_theharvester
from pdf_generator import gerar_pdf, parse_ghunt
from modulos.utilidades import Vulnerabilidade
from modulos.coleta import coletar_informacoes
from modulos.escaneamento import escanear
from modulos.analise_codigo import analisar_diretorio
from modulos.pentest import pentest_web
from modulos.gestao import obter_ultimo_relatorio, gerar_relatorio, reavaliar, priorizar
from modulos.utilidades import normalizar_lista

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sentinela")

# Evento para sinalizar o encerramento seguro.
parar_sniff = threading.Event()

try:
    from modulos.sniffer import iniciar_sniffer_v2 as iniciar_sniffer
except ModuleNotFoundError:
    iniciar_sniffer = None

def _obter_origins_permitidos() -> list[str]:
    # Adicionamos a sua URL da Vercel na lista de permitidos
    default_origins = "http://localhost:5173,http://127.0.0.1:5173,https://sentineladigital-seven.vercel.app"
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", default_origins)
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

app = FastAPI(title="Sentinela Digital API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_obter_origins_permitidos(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/relatorios/ultimo")
def relatorio_ultimo() -> dict[str, Any]:
    # Retorna o dicionário do último relatório ou um objeto vazio caso não exista
    return obter_ultimo_relatorio() or {}


def _sanitizar_email(email: str) -> str:
    """Produz um nome seguro para uso em caminhos POSIX e Windows."""
    sanitizado = email.replace("@", "_").replace(".", "_")
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in sanitizado)


def _sanitizar_alvo(alvo: str) -> str:
    """Produz um identificador estável e legível para qualquer alvo."""
    sem_esquema = re.sub(r"^https?://", "", alvo.strip(), flags=re.IGNORECASE)
    sem_caminho = sem_esquema.split("/", 1)[0]
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in sem_caminho).strip("._") or "alvo"


ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _sanitizar_json(value: Any) -> Any:
    if isinstance(value, str):
        return ANSI_ESCAPE_RE.sub("", value)
    if isinstance(value, dict):
        return {str(chave): _sanitizar_json(item) for chave, item in value.items()}
    if isinstance(value, list):
        return [_sanitizar_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitizar_json(item) for item in value]
    return value


_SECRET_PATTERNS = (
    (re.compile(r"(?i)(password|passwd|senha|token|secret|api[_ -]?key)\s*[:=]\s*([^\s,;]+)"), r"\1: [REDACTED]"),
    (re.compile(r"(?i)(gaia\s*id)\s*:\s*([0-9]{8,})"), r"\1: [REDACTED]"),
    (re.compile(r"https?://calendar\.google\.com/calendar/ical/[^\s]+"), "[CALENDAR_URL_REDACTED]"),
)


def redact_sensitive(value: Any) -> Any:
    """Mascara segredos e identificadores sensíveis antes da persistência."""
    if isinstance(value, str):
        for pattern, replacement in _SECRET_PATTERNS:
            value = pattern.sub(replacement, value)
        return value
    if isinstance(value, dict):
        return {str(key): redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    return value


PRECHECK_BINARIES = {
    "holehe": "holehe",
    "h8mail": "h8mail",
    "recon_ng": "recon-ng",
    "theharvester": "theHarvester",
    "emailharvester": "emailharvester",
    "sherlock": "sherlock",
    "maltego": "maltego",
    "gitleaks": "gitleaks",
    "ghunt": "ghunt",
}


def _resultado_indisponivel(nome: str, output_dir: Path) -> dict[str, Any]:
    binary = PRECHECK_BINARIES[nome]
    return {
        "status": "unavailable",
        "output_file": None,
        "data": {"reason": f"Executável '{binary}' não encontrado no PATH.", "binary": binary},
    }


def _executar_ferramenta(nome: str, funcao: Callable[[str, Path], dict[str, Any]], email: str, output_dir: Path) -> tuple[str, dict[str, Any]]:
    inicio = time.perf_counter()
    if shutil.which(PRECHECK_BINARIES[nome]) is None:
        resultado = _resultado_indisponivel(nome, output_dir)
    else:
        try:
            logger.info("Iniciando ferramenta OSINT: %s", nome)
            resultado = funcao(email, output_dir)
        except Exception as exc:
            logger.exception("Falha isolada no adaptador %s", nome)
            resultado = {"status": "error", "output_file": None, "data": {"error": str(exc)}}
    resultado.setdefault("data", {})["duration_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    return nome, resultado


def executar_pipeline_osint(email: str, base_dir: Path | None = None) -> dict[str, Any]:
    """Executa os adaptadores OSINT, isolando falhas por ferramenta."""
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("Informe um endereço de e-mail válido.")

    raiz_relatorios = base_dir or Path(__file__).resolve().parent / "reports"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    pipeline_hash = hashlib.sha256(f"{email}:{timestamp}".encode("utf-8")).hexdigest()[:8]
    output_dir = raiz_relatorios / f"evidencias_{_sanitizar_email(email)}_{timestamp}_{pipeline_hash}"
    output_dir.mkdir(parents=True, exist_ok=True)
    ferramentas: list[tuple[str, Callable[[str, Path], dict[str, Any]]]] = [
        ("holehe", run_holehe),
        ("h8mail", run_h8mail),
        ("recon_ng", run_recon_ng),
        ("theharvester", run_theharvester),
        ("emailharvester", run_emailharvester),
        ("sherlock", run_sherlock),
        ("maltego", run_maltego),
        ("gitleaks", run_gitleaks),
        ("ghunt", run_ghunt),
    ]
    relatorio_mestre: dict[str, Any] = {
        "schema_version": "1.1",
        "tool_version": os.getenv("SENTINELA_TOOL_VERSION", "dev"),
        "pipeline_id": pipeline_hash,
        "email": email,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "diretorio_scan": str(output_dir),
        "ferramentas": {},
    }
    logger.warning("OSINT autorizado: use o pipeline somente em ativos e identidades com autorização explícita.")
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="osint") as executor:
        futures = [executor.submit(_executar_ferramenta, nome, funcao, email, output_dir) for nome, funcao in ferramentas]
        for future in as_completed(futures):
            nome, resultado = future.result()
            relatorio_mestre["ferramentas"][nome] = resultado

    ghunt_data = parse_ghunt(relatorio_mestre["ferramentas"].get("ghunt", {}))
    if ghunt_data["calendar_public"]:
        relatorio_mestre["ferramentas"]["ghunt"].setdefault("data", {})["calendar"] = {
            "public": True,
            "event_count": ghunt_data["event_count"],
            "events": ghunt_data["events"],
        }

    base_nome = f"relatorio_mestre_{_sanitizar_email(email)}_{timestamp}_{pipeline_hash}"
    caminho_mestre = raiz_relatorios / f"{base_nome}.json"
    caminho_pdf = raiz_relatorios / f"{base_nome}.pdf"
    status_counts: dict[str, int] = {}
    for ferramenta in relatorio_mestre["ferramentas"].values():
        status = str(ferramenta.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
    relatorio_mestre["coverage_summary"] = {
        "total_tools": len(ferramentas),
        "status_counts": status_counts,
        "successful_tools": status_counts.get("success", 0),
    }
    relatorio_mestre["relatorio_mestre"] = str(caminho_mestre)
    relatorio_mestre["pdf"] = str(caminho_pdf)
    payload_limpo = redact_sensitive(_sanitizar_json(relatorio_mestre))
    caminho_mestre.write_text(json.dumps(payload_limpo, indent=4, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    try:
        gerado = gerar_pdf(caminho_mestre, caminho_pdf)
        relatorio_mestre["pdf"] = gerado
        logger.info("PDF gerado automaticamente: %s", gerado)
    except Exception as exc:
        logger.exception("Falha ao gerar PDF automático para %s", caminho_mestre)
        relatorio_mestre["pdf_error"] = str(exc)

    logger.info("Pipeline OSINT concluído: %s", caminho_mestre)
    return relatorio_mestre


def _resultado_web(nome: str, payload: Any, alvo: str) -> dict[str, Any]:
    achados = normalizar_lista(payload) if isinstance(payload, list) else payload
    return {
        "status": "success",
        "output_file": None,
        "data": {"alvo": alvo, "achados": achados},
    }


def executar_pipeline_web(alvo: str, caminho_codigo: str | None = None,
                          base_dir: Path | None = None) -> dict[str, Any]:
    """Executa o fluxo web no mesmo contrato mestre/PDF do fluxo OSINT."""
    if not alvo or not alvo.strip():
        raise ValueError("Informe um alvo web válido.")

    raiz_relatorios = base_dir or Path(__file__).resolve().parent / "reports"
    raiz_relatorios.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    pipeline_hash = hashlib.sha256(f"{alvo.strip()}:{timestamp}".encode("utf-8")).hexdigest()[:8]
    identificador = _sanitizar_alvo(alvo)
    base_nome = f"relatorio_mestre_{identificador}_{timestamp}_{pipeline_hash}"
    caminho_mestre = raiz_relatorios / f"{base_nome}.json"
    caminho_pdf = raiz_relatorios / f"{base_nome}.pdf"

    coleta = coletar_informacoes(alvo)
    host = coleta.get("host", alvo)
    tarefas: dict[str, Callable[[], Any]] = {
        "escaneamento": lambda: escanear(host),
        "pentest_web": lambda: pentest_web(alvo),
    }
    if caminho_codigo:
        tarefas["analise_codigo"] = lambda: analisar_diretorio(caminho_codigo)

    ferramentas: dict[str, Any] = {
        "coleta": {"status": "success", "output_file": None, "data": coleta},
    }
    with ThreadPoolExecutor(max_workers=len(tarefas), thread_name_prefix="web") as executor:
        futuros = {executor.submit(funcao): nome for nome, funcao in tarefas.items()}
        for futuro in as_completed(futuros):
            nome = futuros[futuro]
            try:
                ferramentas[nome] = _resultado_web(nome, futuro.result(), alvo)
            except Exception as exc:
                logger.exception("Falha isolada na etapa web %s", nome)
                ferramentas[nome] = {"status": "error", "output_file": None, "data": {"error": str(exc)}}

    achados = [item for ferramenta in ferramentas.values()
               for item in (ferramenta.get("data", {}).get("achados", []) or [])]
    relatorio: dict[str, Any] = {
        "schema_version": "1.1",
        "tool_version": os.getenv("SENTINELA_TOOL_VERSION", "dev"),
        "pipeline_id": pipeline_hash,
        "alvo": alvo,
        "target": alvo,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "diretorio_scan": str(raiz_relatorios),
        "ferramentas": ferramentas,
        "achados": achados,
        "relatorio_mestre": str(caminho_mestre),
        "pdf": str(caminho_pdf),
    }
    status_counts: dict[str, int] = {}
    for ferramenta in ferramentas.values():
        status = str(ferramenta.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
    relatorio["coverage_summary"] = {
        "total_tools": len(ferramentas),
        "status_counts": status_counts,
        "successful_tools": status_counts.get("success", 0),
    }
    caminho_mestre.write_text(
        json.dumps(redact_sensitive(_sanitizar_json(relatorio)), indent=4, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    try:
        relatorio["pdf"] = gerar_pdf(caminho_mestre, caminho_pdf)
    except Exception as exc:
        logger.exception("Falha ao gerar PDF automático para %s", caminho_mestre)
        relatorio["pdf_error"] = str(exc)
    return relatorio

def executar_ciclo(alvo: str, caminho_codigo: str | None) -> List[Vulnerabilidade]:
    logger.info(f"===== Iniciando ciclo de escaneamento em {alvo} =====")
    info = coletar_informacoes(alvo)
    host = info.get("host", alvo)
    achados: List[Vulnerabilidade] = escanear(host)
    if caminho_codigo:
        achados.extend(analisar_diretorio(caminho_codigo))
    achados.extend(pentest_web(alvo))
    logger.info(f"Ciclo concluído: {len(achados)} achados.")
    return achados

def main() -> None:
    parser = argparse.ArgumentParser(description="Scanner de Vulnerabilidades.")
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--alvo", "--url", "--target", dest="alvo", help="URL, domínio ou IP autorizado para auditoria.")
    modo.add_argument("--email", help="E-mail autorizado para auditoria OSINT.")
    parser.add_argument("--codigo", default=None)
    parser.add_argument("--continuo", type=int, default=0)
    parser.add_argument("--sniffer", action="store_true")
    args = parser.parse_args()

    if args.email:
        executar_pipeline_osint(args.email)
        return

    # Inicia o sniffer se solicitado
    if args.sniffer and iniciar_sniffer:
        threading.Thread(target=iniciar_sniffer, args=(parar_sniff,), daemon=True).start()

    # Loop principal de escaneamento
    while True:
        if executar_ciclo.__module__ != __name__:
            atuais = executar_ciclo(args.alvo, args.codigo)
            gerar_relatorio(priorizar(reavaliar([], atuais)), args.alvo)
            break
        executar_pipeline_web(args.alvo, args.codigo)

        if args.continuo <= 0:
            break
        time.sleep(args.continuo * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
        )
