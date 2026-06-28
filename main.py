#!/usr/bin/env python3
"""
Scanner de Vulnerabilidades — ponto de entrada (CLI).

Orquestra as quatro fases de identificação (Coleta, Escaneamento,
Análise de Código e Pentest leve) e executa o ciclo de gestão
(Categorização, Priorização, Mitigação, Reavaliação e Relatório).

Uso:
    python3 main.py --alvo 192.168.0.10
    python3 main.py --alvo https://exemplo.com --codigo ./projeto
    python3 main.py --alvo 192.168.0.10 --continuo 30
"""

import argparse  # Parser de argumentos de linha de comando
import time      # Sleep para o modo contínuo
from typing import List

from modulos.utilidades import obter_logger, Vulnerabilidade
from modulos.coleta import coletar_informacoes
from modulos.escaneamento import escanear
from modulos.analise_codigo import analisar_diretorio
from modulos.pentest import pentest_web
from modulos.gestao import gerar_relatorio, reavaliar, priorizar

logger = obter_logger("main")


def executar_ciclo(alvo: str, caminho_codigo: str | None) -> List[Vulnerabilidade]:
    """Executa um ciclo completo de identificação e retorna os achados."""
    logger.info("===== Iniciando ciclo de escaneamento em %s =====", alvo)

    # Etapa 1 — Coleta de Informações
    info = coletar_informacoes(alvo)
    host = info.get("host", alvo)

    # Etapa 2 — Escaneamento de portas/serviços
    achados: List[Vulnerabilidade] = escanear(host)

    # Etapa 3 — Análise estática de código (opcional)
    if caminho_codigo:
        achados.extend(analisar_diretorio(caminho_codigo))

    # Etapa 4 — Pentest leve em alvos web
    achados.extend(pentest_web(alvo))

    logger.info("Ciclo concluído: %d achados.", len(achados))
    return achados


def main() -> None:
    """Função principal: lê argumentos e dispara o(s) ciclo(s)."""
    parser = argparse.ArgumentParser(
        description="Scanner de Vulnerabilidades baseado no OWASP Top 10.",
    )
    parser.add_argument("--alvo", required=True,
                        help="IP, hostname ou URL (http(s)://...) a auditar.")
    parser.add_argument("--codigo", default=None,
                        help="Caminho de um diretório de código para análise estática.")
    parser.add_argument("--continuo", type=int, default=0,
                        help="Se > 0, repete o escaneamento a cada N minutos (modo contínuo).")
    args = parser.parse_args()

    # Conjunto de achados do ciclo anterior, usado para a reavaliação
    anteriores: List[Vulnerabilidade] = []

    while True:
        atuais = executar_ciclo(args.alvo, args.codigo)

        # Etapa 5 — Reavaliação (marca corrigidas comparando com o ciclo anterior)
        consolidados = reavaliar(anteriores, atuais)

        # Etapa 6 — Relatório (gera arquivos em relatorios/)
        caminhos = gerar_relatorio(priorizar(consolidados), args.alvo)
        logger.info("Relatório JSON: %s", caminhos["json"])
        logger.info("Relatório TXT : %s", caminhos["txt"])

        # Atualiza o histórico para a próxima rodada (somente os ainda abertos)
        anteriores = [v for v in atuais if not v.corrigida]

        if args.continuo <= 0:
            break  # Execução única
        logger.info("Aguardando %d minutos para o próximo ciclo...", args.continuo)
        time.sleep(args.continuo * 60)


# Bloco padrão de execução direta via `python3 main.py ...`
if __name__ == "__main__":
    main()
