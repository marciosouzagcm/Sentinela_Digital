"""
Módulo de Gestão de Vulnerabilidades.

Implementa as 6 etapas do processo de identificação:

1. Identificação  -> recebe a lista bruta de achados dos demais módulos
2. Categorização  -> agrupa por categoria OWASP
3. Priorização    -> ordena por severidade (CVSS simplificado)
4. Mitigação      -> consolida recomendações
5. Reavaliação    -> compara com escaneamento anterior e marca corrigidas
6. Relatório      -> gera arquivos JSON e TXT em relatorios/
"""

import json
import os
import importlib.util
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional

from .utilidades import (
    Vulnerabilidade, PESO_SEVERIDADE, normalizar_lista, obter_logger,
)

logger = obter_logger("gestao")

# Diretórios padrão dos relatórios
DIR_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
DIR_FRONTEND_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "relatorios")
os.makedirs(DIR_RELATORIOS, exist_ok=True)
os.makedirs(DIR_FRONTEND_RELATORIOS, exist_ok=True)

def _obter_configuracao_tidb() -> Dict[str, object]:
    """Extrai host, porta, usuário, senha e banco a partir da URL do TiDB."""
    url = os.getenv("TIDB_URL") or ""
    if not url:
        return {"host": None, "port": 4000, "user": None, "password": None, "database": None}

    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or int(os.getenv("TIDB_PORT", "4000"))
    database = urllib.parse.unquote(parsed.path.lstrip("/")) or os.getenv("TIDB_DATABASE", "sentinela")

    user = os.getenv("TIDB_USER")
    password = os.getenv("TIDB_PASSWORD")
    if not user and not password:
        user_info = parsed.netloc.rsplit("@", 1)[0] if "@" in parsed.netloc else ""
        if user_info:
            user, password = user_info.split(":", 1) if ":" in user_info else (user_info, "")
            user = urllib.parse.unquote(user)
            password = urllib.parse.unquote(password)

    return {
        "host": host,
        "port": port,
        "user": user or os.getenv("TIDB_USER", "root"),
        "password": password or os.getenv("TIDB_PASSWORD", ""),
        "database": database or os.getenv("TIDB_DATABASE", "sentinela"),
    }


def _credenciais_tidb_estao_validas(configuracao: Dict[str, object]) -> bool:
    """Indica se as credenciais do TiDB parecem estar configuradas."""
    user = str(configuracao.get("user") or "").strip()
    password = str(configuracao.get("password") or "").strip()
    placeholders = {"", "<password>", "<PASSWORD>", "<your_password>", "password", "senha", "changeme"}
    return user not in placeholders and password not in placeholders


def _carregar_modulo_tidb():
    """Carrega o driver de TiDB quando disponível."""
    if not os.getenv("TIDB_URL"):
        return None
    if importlib.util.find_spec("pymysql") is None:
        logger.warning("Driver pymysql não encontrado; persistência em TiDB desabilitada.")
        return None
    try:
        import pymysql
        return pymysql
    except Exception as exc:  # pragma: no cover - depende do ambiente
        logger.warning("Não foi possível importar pymysql: %s", exc)
        return None


def _conectar_tidb():
    """Abre conexão com o TiDB, criando o banco quando necessário."""
    pymysql = _carregar_modulo_tidb()
    if pymysql is None:
        return None

    configuracao = _obter_configuracao_tidb()
    if not _credenciais_tidb_estao_validas(configuracao):
        logger.warning(
            "Credenciais do TiDB incompletas ou ainda em placeholder. Ajuste TIDB_URL/TIDB_USER/TIDB_PASSWORD para a senha real do cluster."
        )
        return None

    params = {
        "host": configuracao["host"],
        "user": configuracao["user"],
        "password": configuracao["password"],
        "port": configuracao["port"],
        "autocommit": True,
        "connect_timeout": 5,
        "charset": "utf8mb4",
    }
    if configuracao["database"]:
        params["database"] = configuracao["database"]

    try:
        return pymysql.connect(**params)
    except Exception as exc:  # pragma: no cover - depende do ambiente
        if configuracao.get("database") and "Unknown database" in str(exc):
            try:
                connection_root = pymysql.connect(
                    host=configuracao["host"],
                    user=configuracao["user"],
                    password=configuracao["password"],
                    port=configuracao["port"],
                    autocommit=True,
                    connect_timeout=5,
                )
                with connection_root.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{configuracao['database']}`")
                connection_root.close()
                return pymysql.connect(**params)
            except Exception as create_exc:
                logger.warning("Falha ao criar o banco do TiDB: %s", create_exc)
        raise


def _persistir_tidb(payload: Dict[str, object]) -> bool:
    """Persiste o relatório em TiDB quando configurado."""
    try:
        connection = _conectar_tidb()
        if connection is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS relatorios (id BIGINT PRIMARY KEY AUTO_RANDOM, alvo TEXT, gerado_em TEXT, payload JSON)"
            )
            cursor.execute(
                "INSERT INTO relatorios (alvo, gerado_em, payload) VALUES (%s, %s, %s)",
                (payload.get("alvo"), payload.get("gerado_em"), json.dumps(payload, ensure_ascii=False)),
            )
        connection.close()
        logger.info("Relatório persistido com sucesso no TiDB")
        return True
    except Exception as exc:  # pragma: no cover - depende do ambiente
        logger.warning("Falha ao persistir em TiDB: %s", exc)
        return False


def _persistir_arquivo_local(payload: Dict[str, object], caminho_frontend: str) -> None:
    with open(caminho_frontend, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _carregar_ultimo_relatorio_local() -> Optional[Dict[str, object]]:
    caminho_frontend = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    if not os.path.exists(caminho_frontend):
        return None
    with open(caminho_frontend, "r", encoding="utf-8") as f:
        return json.load(f)


def obter_ultimo_relatorio() -> Optional[Dict[str, object]]:
    """Retorna o último relatório do TiDB, ou fallback para o arquivo local."""
    pymysql = _carregar_modulo_tidb()
    if pymysql is None:
        return _carregar_ultimo_relatorio_local()
    try:
        connection = _conectar_tidb()
        if connection is None:
            return _carregar_ultimo_relatorio_local()
        with connection.cursor() as cursor:
            cursor.execute("SELECT payload FROM relatorios ORDER BY id DESC LIMIT 1")
            resultado = cursor.fetchone()
        connection.close()
        if resultado and resultado[0]:
            logger.info("Relatório carregado diretamente do TiDB")
            return json.loads(resultado[0])
    except Exception as exc:  # pragma: no cover - depende do ambiente
        logger.warning("Falha ao ler do TiDB: %s", exc)
    return _carregar_ultimo_relatorio_local()


def categorizar(vulns: List[Vulnerabilidade]) -> Dict[str, List[Vulnerabilidade]]:
    """Agrupa os achados por categoria (ex.: 'A01', 'A03')."""
    grupos: Dict[str, List[Vulnerabilidade]] = {}
    for v in vulns:
        grupos.setdefault(v.categoria, []).append(v)
    return grupos


def priorizar(vulns: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    """Ordena do mais crítico ao menos crítico."""
    return sorted(vulns,
                  key=lambda v: PESO_SEVERIDADE.get(v.severidade.upper(), 0),
                  reverse=True)


def reavaliar(anteriores: List[Vulnerabilidade],
              atuais: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    """
    Compara um conjunto anterior com o atual e marca como `corrigida`
    aquelas que estavam presentes antes e não foram mais detectadas.
    """
    ids_atuais = {v.identificador for v in atuais}
    resultado: List[Vulnerabilidade] = list(atuais)
    for v in anteriores:
        if v.identificador not in ids_atuais:
            v.corrigida = True
            resultado.append(v)
            logger.info("Vulnerabilidade %s aparentemente corrigida.", v.identificador)
    return resultado


def _gerar_metricas(vulns: List[Vulnerabilidade]) -> Dict[str, int]:
    """Calcula métricas-resumo usadas na etapa de Relatório."""
    metricas = {"TOTAL": len(vulns), "CORRIGIDAS": 0,
                "CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    for v in vulns:
        if v.corrigida:
            metricas["CORRIGIDAS"] += 1
        else:
            metricas[v.severidade.upper()] = metricas.get(v.severidade.upper(), 0) + 1
    return metricas


def gerar_relatorio(vulns: List[Vulnerabilidade], alvo: str) -> Dict[str, str]:
    """
    Persiste dois arquivos em `relatorios/`:
      - JSON estruturado (para integração com outras ferramentas)
      - TXT legível (para leitura humana)
    Retorna os caminhos gerados.
    """
    carimbo = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nome_base = f"relatorio_{carimbo}"
    caminho_json = os.path.join(DIR_RELATORIOS, nome_base + ".json")
    caminho_txt  = os.path.join(DIR_RELATORIOS, nome_base + ".txt")

    priorizadas = priorizar(vulns)
    grupos = categorizar(priorizadas)
    metricas = _gerar_metricas(priorizadas)

    # ---- JSON ----
    payload = {
        "alvo": alvo,
        "gerado_em": datetime.utcnow().isoformat(),
        "metricas": metricas,
        "categorias": {cat: normalizar_lista(lst) for cat, lst in grupos.items()},
    }
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    caminho_frontend = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    _persistir_arquivo_local(payload, caminho_frontend)
    _persistir_tidb(payload)

    # ---- TXT ----
    linhas: List[str] = []
    linhas.append("=" * 72)
    linhas.append(f"RELATÓRIO DE VULNERABILIDADES - {alvo}")
    linhas.append(f"Gerado em (UTC): {payload['gerado_em']}")
    linhas.append("=" * 72)
    linhas.append("MÉTRICAS:")
    for k, v in metricas.items():
        linhas.append(f"  - {k:<10}: {v}")
    linhas.append("")
    for cat, lst in grupos.items():
        linhas.append(f"[{cat}] {len(lst)} achado(s)")
        linhas.append("-" * 72)
        for v in priorizar(lst):
            status = "[CORRIGIDA]" if v.corrigida else f"[{v.severidade}]"
            linhas.append(f"{status} {v.identificador} - {v.titulo}")
            linhas.append(f"  Ativo    : {v.ativo}")
            linhas.append(f"  Descrição: {v.descricao}")
            if v.evidencia:
                linhas.append(f"  Evidência: {v.evidencia}")
            linhas.append(f"  Mitigação: {v.mitigacao}")
            linhas.append("")
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    logger.info("Relatórios gerados: %s | %s | %s", caminho_json, caminho_txt, caminho_frontend)
    return {"json": caminho_json, "txt": caminho_txt, "frontend": caminho_frontend}
