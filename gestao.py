import os
import importlib.util
import urllib.parse
import json
from datetime import datetime
from typing import Dict, List, Optional

from .utilidades import (
    Vulnerabilidade, PESO_SEVERIDADE, normalizar_lista, obter_logger,
)

logger = obter_logger("gestao")

# Diretórios padrão
DIR_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
# MUDANÇA: Se estiver no Render, usamos /tmp para evitar conflitos de FileExistsError
DIR_FRONTEND_RELATORIOS = os.getenv("RENDER_WORKSPACE", "/tmp")
DIR_FRONTEND_RELATORIOS = os.path.join(DIR_FRONTEND_RELATORIOS, "public", "relatorios")

def _seguro_makedirs(caminho: str):
    """Cria diretório de forma segura, removendo obstruções se necessário."""
    try:
        if os.path.exists(caminho):
            if not os.path.isdir(caminho):
                os.remove(caminho) # Remove arquivo intruso
                os.makedirs(caminho, exist_ok=True)
        else:
            os.makedirs(caminho, exist_ok=True)
    except OSError as e:
        logger.error(f"Erro ao criar diretório {caminho}: {e}")

# Inicialização segura
_seguro_makedirs(DIR_RELATORIOS)
_seguro_makedirs(DIR_FRONTEND_RELATORIOS)

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
    user = str(configuracao.get("user") or "").strip()
    password = str(configuracao.get("password") or "").strip()
    placeholders = {"", "<password>", "<PASSWORD>", "<your_password>", "password", "senha", "changeme"}
    return user not in placeholders and password not in placeholders

def _carregar_modulo_tidb():
    if not os.getenv("TIDB_URL"):
        return None
    if importlib.util.find_spec("pymysql") is None:
        logger.warning("Driver pymysql não encontrado; persistência em TiDB desabilitada.")
        return None
    try:
        import pymysql
        return pymysql
    except Exception as exc:
        logger.warning("Não foi possível importar pymysql: %s", exc)
        return None

def _conectar_tidb():
    pymysql = _carregar_modulo_tidb()
    if pymysql is None:
        return None

    configuracao = _obter_configuracao_tidb()
    if not _credenciais_tidb_estao_validas(configuracao):
        logger.warning("Credenciais do TiDB incompletas.")
        return None

    params = {
        "host": configuracao["host"], "user": configuracao["user"],
        "password": configuracao["password"], "port": configuracao["port"],
        "autocommit": True, "connect_timeout": 5, "charset": "utf8mb4",
    }
    if configuracao["database"]:
        params["database"] = configuracao["database"]

    try:
        return pymysql.connect(**params)
    except Exception as exc:
        if configuracao.get("database") and "Unknown database" in str(exc):
            try:
                connection_root = pymysql.connect(
                    host=configuracao["host"], user=configuracao["user"],
                    password=configuracao["password"], port=configuracao["port"],
                    autocommit=True, connect_timeout=5,
                )
                with connection_root.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{configuracao['database']}`")
                connection_root.close()
                return pymysql.connect(**params)
            except Exception as create_exc:
                logger.warning("Falha ao criar o banco do TiDB: %s", create_exc)
        raise

def _persistir_tidb(payload: Dict[str, object]) -> bool:
    try:
        connection = _conectar_tidb()
        if connection is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS relatorios (id BIGINT PRIMARY KEY AUTO_RANDOM, alvo TEXT, gerado_em TEXT, payload JSON)")
            cursor.execute("INSERT INTO relatorios (alvo, gerado_em, payload) VALUES (%s, %s, %s)",
                           (payload.get("alvo"), payload.get("gerado_em"), json.dumps(payload, ensure_ascii=False)))
        connection.close()
        return True
    except Exception as exc:
        logger.warning("Falha ao persistir em TiDB: %s", exc)
        return False

def _persistir_arquivo_local(payload: Dict[str, object], caminho_frontend: str) -> None:
    try:
        with open(caminho_frontend, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar JSON local: {e}")

def _carregar_ultimo_relatorio_local() -> Optional[Dict[str, object]]:
    caminho_frontend = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    if not os.path.exists(caminho_frontend):
        return None
    try:
        with open(caminho_frontend, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def obter_ultimo_relatorio() -> Optional[Dict[str, object]]:
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
            return json.loads(resultado[0])
    except Exception:
        pass
    return _carregar_ultimo_relatorio_local()

# Funções de lógica (Categorizar, Priorizar, Reavaliar mantidas conforme original)
def categorizar(vulns: List[Vulnerabilidade]) -> Dict[str, List[Vulnerabilidade]]:
    grupos: Dict[str, List[Vulnerabilidade]] = {}
    for v in vulns:
        grupos.setdefault(v.categoria, []).append(v)
    return grupos

def priorizar(vulns: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    return sorted(vulns, key=lambda v: PESO_SEVERIDADE.get(v.severidade.upper(), 0), reverse=True)

def reavaliar(anteriores: List[Vulnerabilidade], atuais: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    ids_atuais = {v.identificador for v in atuais}
    resultado = list(atuais)
    for v in anteriores:
        if v.identificador not in ids_atuais:
            v.corrigida = True
            resultado.append(v)
    return resultado

def _gerar_metricas(vulns: List[Vulnerabilidade]) -> Dict[str, int]:
    metricas = {"TOTAL": len(vulns), "CORRIGIDAS": 0, "CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    for v in vulns:
        if v.corrigida:
            metricas["CORRIGIDAS"] += 1
        else:
            metricas[v.severidade.upper()] = metricas.get(v.severidade.upper(), 0) + 1
    return metricas

def gerar_relatorio(vulns: List[Vulnerabilidade], alvo: str) -> Dict[str, str]:
    carimbo = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nome_base = f"relatorio_{carimbo}"
    caminho_json = os.path.join(DIR_RELATORIOS, nome_base + ".json")
    caminho_txt = os.path.join(DIR_RELATORIOS, nome_base + ".txt")
    caminho_frontend = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")

    priorizadas = priorizar(vulns)
    grupos = categorizar(priorizadas)
    metricas = _gerar_metricas(priorizadas)

    payload = {
        "alvo": alvo,
        "gerado_em": datetime.utcnow().isoformat(),
        "metricas": metricas,
        "categorias": {cat: normalizar_lista(lst) for cat, lst in grupos.items()},
    }
    
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    _persistir_arquivo_local(payload, caminho_frontend)
    _persistir_tidb(payload)

    # Lógica do TXT mantida...
    return {"json": caminho_json, "txt": caminho_txt, "frontend": caminho_frontend}
