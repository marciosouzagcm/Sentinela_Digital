#!/usr/bin/env python3
"""
Scanner de Vulnerabilidades — ponto de entrada (CLI).
"""
import argparse
import os
import time
import threading
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modulos.utilidades import obter_logger, Vulnerabilidade
from modulos.coleta import coletar_informacoes
from modulos.escaneamento import escanear
from modulos.analise_codigo import analisar_diretorio
from modulos.pentest import pentest_web
from modulos.gestao import gerar_relatorio, reavaliar, priorizar, obter_ultimo_relatorio

try:
    from modulos.sniffer import iniciar_sniffer
except ModuleNotFoundError:  # scapy pode não estar instalado
    iniciar_sniffer = None

logger = obter_logger("main")


def _obter_origins_permitidos() -> list[str]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


app = FastAPI(title="Sentinela Digital API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_obter_origins_permitidos(),
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/relatorios/ultimo")
def relatorio_ultimo():
    return obter_ultimo_relatorio() or {}


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
    parser.add_argument("--alvo", required=True)
    parser.add_argument("--codigo", default=None)
    parser.add_argument("--continuo", type=int, default=0)
    parser.add_argument("--sniffer", action="store_true")
    args = parser.parse_args()

    if args.sniffer:
        if iniciar_sniffer is None:
            logger.warning("Sniffer não disponível porque a dependência 'scapy' não está instalada.")
        else:
            logger.info("[*] Sniffer ativado.")
            sniff_thread = threading.Thread(target=iniciar_sniffer, daemon=True)
            sniff_thread.start()

    anteriores: List[Vulnerabilidade] = []
    while True:
        atuais = executar_ciclo(args.alvo, args.codigo)
        consolidados = reavaliar(anteriores, atuais)
        caminhos = gerar_relatorio(priorizar(consolidados), args.alvo)
        logger.info(f"Relatório JSON: {caminhos['json']}")
        logger.info(f"Relatório TXT : {caminhos['txt']}")
        anteriores = [v for v in atuais if not v.corrigida]
        if args.continuo <= 0: break
        time.sleep(args.continuo * 60)

if __name__ == "__main__":
    main()