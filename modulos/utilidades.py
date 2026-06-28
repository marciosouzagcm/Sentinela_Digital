"""
Módulo de utilidades compartilhadas.

Fornece logger padronizado e a classe `Vulnerabilidade`, que representa
um achado normalizado pelos demais módulos do scanner.
"""

import logging  # Biblioteca padrão para registro de eventos
import os       # Manipulação de caminhos do sistema operacional
from dataclasses import dataclass, field, asdict  # Estruturas de dados imutáveis e serializáveis
from datetime import datetime  # Marcação temporal dos achados
from typing import List, Dict, Any  # Tipagem estática para clareza


# Diretório onde os arquivos de log serão persistidos
DIR_LOGS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(DIR_LOGS, exist_ok=True)  # Garante que a pasta de logs exista


def obter_logger(nome: str) -> logging.Logger:
    """
    Cria (ou recupera) um logger configurado para escrever simultaneamente
    em arquivo e no console. Centraliza a configuração para evitar
    duplicação de handlers em chamadas repetidas.
    """
    logger = logging.getLogger(nome)
    if logger.handlers:  # Evita adicionar handlers duplicados
        return logger
    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de arquivo: persiste todos os eventos em logs/scanner.log
    fh = logging.FileHandler(os.path.join(DIR_LOGS, "scanner.log"), encoding="utf-8")
    fh.setFormatter(formato)
    logger.addHandler(fh)

    # Handler de console: exibe ao operador em tempo real
    ch = logging.StreamHandler()
    ch.setFormatter(formato)
    logger.addHandler(ch)

    return logger


# Mapeamento de severidade textual -> peso numérico (usado na priorização)
PESO_SEVERIDADE: Dict[str, int] = {
    "BAIXA": 1,
    "MEDIA": 2,
    "ALTA": 3,
    "CRITICA": 4,
}


@dataclass
class Vulnerabilidade:
    """
    Representação canônica de uma vulnerabilidade descoberta.

    Atributos:
        identificador  -> Código único (ex.: A01-001)
        categoria      -> Categoria OWASP (A01..A10) ou tipo livre
        titulo         -> Nome curto da falha
        descricao      -> Detalhamento técnico
        ativo          -> Alvo onde foi encontrada (URL, IP, arquivo)
        severidade     -> BAIXA | MEDIA | ALTA | CRITICA
        evidencia      -> Trecho ou prova coletada
        mitigacao      -> Recomendação de correção
        descoberta_em  -> Timestamp ISO 8601 do achado
        corrigida      -> Marcador atualizado na fase de reavaliação
    """
    identificador: str
    categoria: str
    titulo: str
    descricao: str
    ativo: str
    severidade: str = "MEDIA"
    evidencia: str = ""
    mitigacao: str = ""
    descoberta_em: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    corrigida: bool = False

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (útil para serialização JSON)."""
        return asdict(self)


def normalizar_lista(vulns: List[Vulnerabilidade]) -> List[Dict[str, Any]]:
    """Converte uma lista de Vulnerabilidade em lista de dicionários."""
    return [v.para_dict() for v in vulns]
