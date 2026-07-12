"""
Módulo de Escaneamento (Etapa 2 do processo).

Realiza varredura de portas TCP comuns e detecção de serviços.
Caso o pacote `python-nmap` esteja disponível e o binário `nmap`
instalado, usa-o. Caso contrário, recorre a um scanner TCP simples
implementado com `socket`, garantindo funcionamento mínimo.
"""

import socket
from typing import List, Dict, Any

from .utilidades import obter_logger, Vulnerabilidade

logger = obter_logger("escaneamento")

# Portas frequentemente expostas e relevantes para auditoria
PORTAS_COMUNS: List[int] = [
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445,
    3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017,
]


def _scan_socket(host: str, portas: List[int]) -> List[Dict[str, Any]]:
    """Scanner TCP de fallback baseado apenas em `socket` (sem dependências)."""
    abertas: List[Dict[str, Any]] = []
    for porta in portas:
        # Cria um socket TCP com timeout curto para não travar a varredura
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            try:
                # connect_ex retorna 0 quando a porta aceita conexão
                if s.connect_ex((host, porta)) == 0:
                    abertas.append({"porta": porta, "servico": "desconhecido"})
            except OSError:
                # Falhas individuais são ignoradas; seguimos para a próxima porta
                continue
    return abertas


def escanear(host: str) -> List[Vulnerabilidade]:
    """
    Escaneia o host e devolve vulnerabilidades referentes a serviços
    abertos considerados arriscados (telnet, ftp sem TLS, RDP exposto…).
    """
    achados: List[Vulnerabilidade] = []
    portas_abertas: List[Dict[str, Any]] = []

    # Tenta usar python-nmap para enriquecer com versão/serviço
    try:
        import nmap  # Import tardio: dependência opcional
        scanner = nmap.PortScanner()
        scanner.scan(host, arguments="-sT -sV --version-light -T4")
        for h in scanner.all_hosts():
            for proto in scanner[h].all_protocols():
                for porta, dados in scanner[h][proto].items():
                    if dados.get("state") == "open":
                        portas_abertas.append({
                            "porta": porta,
                            "servico": dados.get("name", "desconhecido"),
                            "produto": dados.get("product", ""),
                            "versao": dados.get("version", ""),
                        })
        logger.info("Nmap concluído em %s (%d portas abertas)", host, len(portas_abertas))
    except Exception as erro:  # noqa: BLE001 - fallback genérico intencional
        logger.warning("Nmap indisponível (%s). Usando scanner TCP simples.", erro)
        portas_abertas = _scan_socket(host, PORTAS_COMUNS)

    # Regras simples que transformam portas/serviços em vulnerabilidades
    # Mapa: porta -> (categoria OWASP, severidade, motivo, mitigação)
    regras = {
        21:   ("A02", "ALTA",    "FTP em texto claro exposto.",
               "Substituir por SFTP/FTPS e restringir acesso."),
        23:   ("A02", "CRITICA", "Telnet exposto: tráfego sem criptografia.",
               "Desativar Telnet e usar SSH."),
        3389: ("A07", "ALTA",    "RDP exposto à rede.",
               "Restringir por VPN, exigir MFA e bloquear força-bruta."),
        6379: ("A05", "ALTA",    "Redis exposto sem autenticação por padrão.",
               "Habilitar requirepass e bind em interface interna."),
        27017:("A05", "ALTA",    "MongoDB exposto.",
               "Habilitar autenticação e firewall."),
        3306: ("A05", "MEDIA",   "MySQL acessível externamente.",
               "Restringir bind-address e revisar contas."),
        5432: ("A05", "MEDIA",   "PostgreSQL acessível externamente.",
               "Ajustar pg_hba.conf e listen_addresses."),
    }

    for idx, item in enumerate(portas_abertas, start=1):
        porta = item["porta"]
        if porta in regras:
            cat, sev, motivo, mitig = regras[porta]
            achados.append(Vulnerabilidade(
                identificador=f"{cat}-PORTA-{porta}",
                categoria=cat,
                titulo=f"Serviço sensível exposto na porta {porta}",
                descricao=f"{motivo} Serviço detectado: {item.get('servico','?')}.",
                ativo=f"{host}:{porta}",
                severidade=sev,
                evidencia=str(item),
                mitigacao=mitig,
            ))

    return achados
