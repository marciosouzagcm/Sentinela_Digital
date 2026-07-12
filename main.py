#!/usr/bin/env python3
"""
Scanner de Vulnerabilidades — ponto de entrada (CLI + API).
"""
import argparse
import os
import time
import threading
import uvicorn
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modulos.utilidades import obter_logger, Vulnerabilidade
from modulos.coleta import coletar_informacoes
from modulos.escaneamento import escanear
from modulos.analise_codigo import analisar_diretorio
from modulos.pentest import pentest_web
from modulos.gestao import gerar_relatorio, reavaliar, priorizar, obter_ultimo_relatorio

# Evento para sinalizar o encerramento seguro
parar_sniff = threading.Event()

try:
    from modulos.sniffer import iniciar_sniffer_v2 as iniciar_sniffer
except ModuleNotFoundError:
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
def health(): return {"status": "ok"}

@app.get("/relatorios/ultimo")
def relatorio_ultimo(): return obter_ultimo_relatorio() or {}

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

    sniff_thread = None
    if args.sniffer and iniciar_sniffer:
        logger.info("[*] Sniffer ativado.")
        sniff_thread = threading.Thread(
            target=iniciar_sniffer, 
            args=("ens33", parar_sniff), 
            daemon=True
        )
        sniff_thread.start()

    try:
        anteriores: List[Vulnerabilidade] = []
        while True:
            atuais = executar_ciclo(args.alvo, args.codigo)
            consolidados = reavaliar(anteriores, atuais)
            caminhos = gerar_relatorio(priorizar(consolidados), args.alvo)
            logger.info(f"Relatório JSON: {caminhos['json']}")
            anteriores = [v for v in atuais if not v.corrigida]
            
            if args.continuo <= 0: break
            time.sleep(args.continuo * 60)
            
    except KeyboardInterrupt:
        logger.info("Encerrando ciclo...")
    finally:
        # Finalização segura
        parar_sniff.set()
        if sniff_thread:
            sniff_thread.join(timeout=3.0)
        logger.info("Sistema finalizado com sucesso.")

if __name__ == "__main__":
    # Rodar API em thread separada
    threading.Thread(target=lambda: uvicorn.run(app, host="127.0.0.1", port=8000), daemon=True).start()
    main()
