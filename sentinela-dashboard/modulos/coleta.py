"""
Módulo de Coleta de Informações (Etapa 1 do processo).

Reúne informações públicas sobre o alvo antes do escaneamento ativo:
- Resolução DNS
- Cabeçalhos HTTP
- Banner do servidor
"""

import socket           # Resolução DNS e conexões TCP de baixo nível
from typing import Dict, Any
from urllib.parse import urlparse  # Decomposição segura de URLs

import requests  # Cliente HTTP de alto nível

from .utilidades import obter_logger

logger = obter_logger("coleta")


def coletar_informacoes(alvo: str) -> Dict[str, Any]:
    """
    Executa o reconhecimento passivo sobre `alvo`.
    Aceita IP, hostname ou URL completa.
    Retorna um dicionário com os dados coletados.
    """
    info: Dict[str, Any] = {"alvo_original": alvo}

    # Detecta se o alvo é uma URL; caso contrário trata como host puro
    if alvo.startswith(("http://", "https://")):
        parsed = urlparse(alvo)
        host = parsed.hostname or alvo
        info["url"] = alvo
    else:
        host = alvo

    info["host"] = host

    # 1. Resolução DNS -> traduz o nome em um ou mais endereços IP
    try:
        ips = list({i[4][0] for i in socket.getaddrinfo(host, None)})
        info["enderecos_ip"] = ips
        logger.info("DNS resolvido para %s -> %s", host, ips)
    except socket.gaierror as erro:
        # Falha de DNS não interrompe o fluxo; apenas registra o problema
        info["enderecos_ip"] = []
        info["erro_dns"] = str(erro)
        logger.warning("Falha ao resolver DNS de %s: %s", host, erro)

    # 2. Coleta de cabeçalhos HTTP (apenas se um URL foi fornecido)
    if "url" in info:
        try:
            resposta = requests.get(
                info["url"],
                timeout=10,
                allow_redirects=True,
                headers={"User-Agent": "ScannerVulnerabilidades/1.0"},
            )
            info["status_http"] = resposta.status_code
            info["cabecalhos"] = dict(resposta.headers)
            info["servidor"] = resposta.headers.get("Server", "desconhecido")
            logger.info("HTTP %s coletado de %s", resposta.status_code, info["url"])
        except requests.RequestException as erro:
            info["erro_http"] = str(erro)
            logger.warning("Erro HTTP em %s: %s", info["url"], erro)

    return info
