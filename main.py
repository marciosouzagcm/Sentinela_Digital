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
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List
from urllib.parse import urlsplit

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from modules.osint.mod_emailharvester import run_emailharvester
from modules.osint.mod_ghunt import run_ghunt
from modules.osint.mod_gitleaks import run_gitleaks
from modules.osint.mod_h8mail import run_h8mail
from modules.osint.mod_holehe import run_holehe
from modules.osint.mod_blockchain import run_blockchain
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
from app.db.database import get_db, init_db
from app.db.models import PaymentTransaction, User
from app.api.solana_pay import router as solana_pay_router
from app.services.mod_solana import is_solana_address, run_solana_scan
from app.services.solana_reporting import generate_solana_report
from app.services.siws import (
    SiwsConfigurationError,
    SiwsInvalidSignature,
    SiwsMessageMismatch,
    SiwsNonceExpired,
    SiwsNonceUnavailable,
    create_session_jwt,
    get_jwt_secret,
    issue_siws_challenge,
    verify_siws_signature,
)

# Importação condicional da base de dados para sincronização no TiDB
try:
    from database import engine, Base
    import models
except ImportError:
    engine = None
    Base = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sentinela")

# Evento para sinalizar o encerramento seguro.
parar_sniff = threading.Event()

try:
    from modulos.sniffer import iniciar_sniffer_v2 as iniciar_sniffer
except ModuleNotFoundError:
    iniciar_sniffer = None


SOLANA_TARGET_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SOLANA_DOMAIN_RE = re.compile(r"(?i)^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.sol\.?$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador do ciclo de vida da aplicação (Lifespan modernizado)."""
    try:
        init_db()
        logger.info("Tabelas do TiDB sincronizadas e criadas com sucesso.")
    except Exception as exc:
        logger.error("Erro ao sincronizar tabelas com o TiDB: %s", exc)
    yield


def _obter_origins_permitidos() -> list[str]:
    default_origins = "http://localhost:5173,http://127.0.0.1:5173,https://sentineladigital-seven.vercel.app"
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", default_origins)
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


app = FastAPI(title="Sentinela Digital API", lifespan=lifespan)
app.include_router(solana_pay_router)

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
    return obter_ultimo_relatorio() or {}


class SolanaScanRequest(BaseModel):
    reference: str = Field(..., min_length=32, max_length=88)


@app.post("/api/v1/solana/scan")
async def scan_solana_api(payload: SolanaScanRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Run/retry a scan only for an order that has already been verified on-chain."""
    reference = payload.reference.strip()
    order = db.query(PaymentTransaction).filter(PaymentTransaction.signature == reference).first()
    if order is None or order.status != "verified":
        raise HTTPException(status_code=403, detail="Uma cobrança Solana confirmada é necessária para executar a varredura.")
    try:
        payment_metadata = json.loads(order.user_metadata or "{}")
    except json.JSONDecodeError:
        payment_metadata = {}
    target = payment_metadata.get("target")
    if not isinstance(target, str) or not _parece_alvo_solana(target):
        raise HTTPException(status_code=422, detail="A ordem confirmada não contém um alvo Solana válido.")
    return await generate_solana_report(
        target,
        payment={"reference": reference, "signature": payment_metadata.get("confirmed_signature", "")},
    )


class SiwsAuthRequest(BaseModel):
    public_key: str = Field(..., min_length=32, max_length=44)
    signature: str = Field(..., min_length=64, max_length=132)
    message: str = Field(..., min_length=1, max_length=2048)
    nonce: str = Field(..., min_length=32, max_length=64)


def _siws_domain_and_uri(request: Request) -> tuple[str, str]:
    configured_domain = os.getenv("SIWS_DOMAIN", "").strip()
    configured_uri = os.getenv("SIWS_URI", "").strip()
    if configured_domain:
        domain = configured_domain
        uri = configured_uri or f"https://{domain}/"
        return domain, uri

    origin = request.headers.get("origin", "").rstrip("/")
    allowed_origins = set(_obter_origins_permitidos())
    candidate = origin if origin in allowed_origins else str(request.base_url).rstrip("/")
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Não foi possível determinar o domínio SIWS.")
    return parsed.netloc, f"{parsed.scheme}://{parsed.netloc}/"


@app.get("/api/v1/auth/nonce")
@app.get("/auth/nonce", include_in_schema=False)
def auth_nonce(
    request: Request,
    response: Response,
    public_key: str = Query(..., min_length=32, max_length=44),
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    if not is_solana_address(public_key):
        raise HTTPException(status_code=400, detail="public_key Solana inválida.")
    domain, uri = _siws_domain_and_uri(request)
    try:
        challenge = issue_siws_challenge(public_key, domain, uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "nonce": challenge.nonce,
        "message": challenge.message,
        "domain": challenge.domain,
        "issued_at": challenge.issued_at.isoformat().replace("+00:00", "Z"),
        "expires_at": challenge.expires_at.isoformat().replace("+00:00", "Z"),
    }


@app.post("/api/v1/auth/verify-wallet")
@app.post("/auth/verify-wallet", include_in_schema=False)
def verify_wallet(payload: SiwsAuthRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    public_key = payload.public_key.strip()
    if not is_solana_address(public_key):
        raise HTTPException(status_code=400, detail="public_key Solana inválida.")
    try:
        get_jwt_secret()
    except SiwsConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        challenge = verify_siws_signature(
            public_key=public_key,
            signature=payload.signature,
            message=payload.message,
            nonce=payload.nonce,
        )
    except SiwsNonceExpired as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SiwsMessageMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SiwsNonceUnavailable as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SiwsInvalidSignature as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    access_token, expires_in = create_session_jwt(public_key, challenge.domain)
    try:
        usuario = db.query(User).filter(User.wallet_address == public_key).first()
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        if usuario is None:
            usuario = User(
                wallet_address=public_key,
                auth_method="siws",
                created_at=agora,
                updated_at=agora,
            )
            db.add(usuario)
        else:
            usuario.auth_method = "siws"
            usuario.updated_at = agora
        db.commit()
        return {
            "status": "success",
            "message": "Carteira autenticada por SIWS.",
            "wallet_address": public_key,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Falha ao persistir autenticação SIWS.")
        raise HTTPException(status_code=500, detail="Não foi possível registrar a sessão SIWS.") from exc


@app.get("/api/v1/users")
def list_users(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    usuarios = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": usuario.id,
            "uuid": usuario.uuid,
            "email": usuario.email,
            "wallet_address": usuario.wallet_address,
            "auth_method": usuario.auth_method,
            "is_active": usuario.is_active,
            "created_at": usuario.created_at.isoformat() if usuario.created_at else None,
            "updated_at": usuario.updated_at.isoformat() if usuario.updated_at else None,
        }
        for usuario in usuarios
    ]


def _sanitizar_email(email: str) -> str:
    sanitizado = email.replace("@", "_").replace(".", "_")
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in sanitizado)


def _sanitizar_alvo(alvo: str) -> str:
    sem_esquema = re.sub(r"^https?://", "", alvo.strip(), flags=re.IGNORECASE)
    sem_caminho = sem_esquema.split("/", 1)[0]
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in sem_caminho).strip("._") or "alvo"


def _parece_alvo_solana(value: str | None) -> bool:
    candidate = (value or "").strip()
    return bool(SOLANA_TARGET_RE.fullmatch(candidate) or SOLANA_DOMAIN_RE.fullmatch(candidate))


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
    binary = PRECHECK_BINARIES.get(nome)
    if binary and shutil.which(binary) is None:
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


def executar_pipeline_osint(email: str | None = None, base_dir: Path | None = None, wallet: str | None = None) -> dict[str, Any]:
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        raise ValueError("Informe um endereço de e-mail válido.")
    if not email and not wallet:
        raise ValueError("Informe um e-mail ou uma carteira EVM válida.")

    raiz_relatorios = base_dir or Path(__file__).resolve().parent / "reports"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    alvo_osint = email or wallet or ""
    pipeline_hash = hashlib.sha256(f"{alvo_osint}:{timestamp}".encode("utf-8")).hexdigest()[:8]
    identificador = _sanitizar_email(email) if email else _sanitizar_alvo(wallet or "wallet")
    output_dir = raiz_relatorios / f"evidencias_{identificador}_{timestamp}_{pipeline_hash}"
    output_dir.mkdir(parents=True, exist_ok=True)
    if email:
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
            ("blockchain", lambda alvo, pasta: run_blockchain(alvo, pasta, wallet)),
        ]
    else:
        ferramentas = [
            ("blockchain", lambda alvo, pasta: run_blockchain(alvo, pasta, wallet)),
        ]
    if wallet and _parece_alvo_solana(wallet):
        ferramentas.append(("solana", lambda alvo, pasta: run_solana_scan(wallet, pasta)))
    relatorio_mestre: dict[str, Any] = {
        "schema_version": "1.1",
        "tool_version": os.getenv("SENTINELA_TOOL_VERSION", "dev"),
        "pipeline_id": pipeline_hash,
        "email": email,
        "wallet": wallet,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "diretorio_scan": str(output_dir),
        "ferramentas": {},
    }
    logger.warning("OSINT autorizado: use o pipeline somente em ativos e identidades com autorização explícita.")
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="osint") as executor:
        futures = [executor.submit(_executar_ferramenta, nome, funcao, alvo_osint, output_dir) for nome, funcao in ferramentas]
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

    base_nome = f"relatorio_mestre_{identificador}_{timestamp}_{pipeline_hash}"
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


def executar_pipeline_web(alvo: str, caminho_codigo: str | None = None, base_dir: Path | None = None) -> dict[str, Any]:
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

    achados = [item for ferramenta in ferramentas.values() for item in (ferramenta.get("data", {}).get("achados", []) or [])]
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
    modo.add_argument("--wallet", help="Endereço EVM autorizado para auditoria blockchain.")
    parser.add_argument("--wallet-correlacionada", dest="wallet_correlacionada", help="Carteira EVM opcional para correlacionar com o e-mail.")
    parser.add_argument("--codigo", default=None)
    parser.add_argument("--continuo", type=int, default=0)
    parser.add_argument("--sniffer", action="store_true")
    args = parser.parse_args()

    if args.email:
        executar_pipeline_osint(args.email, wallet=args.wallet_correlacionada)
        return
    if args.wallet:
        executar_pipeline_osint(wallet=args.wallet)
        return

    if args.sniffer and iniciar_sniffer:
        threading.Thread(target=iniciar_sniffer, args=(parar_sniff,), daemon=True).start()

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