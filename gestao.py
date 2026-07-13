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

# --- CONFIGURAÇÃO FORÇADA DE DIRETÓRIOS ---
DIR_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
# Forçando uso de /tmp para evitar conflitos de permissão/arquivo no Render
DIR_FRONTEND_RELATORIOS = "/tmp/relatorios"

def _garantir_ambientes():
    """Função única para garantir que os diretórios existam."""
    for path in [DIR_RELATORIOS, DIR_FRONTEND_RELATORIOS]:
        try:
            if os.path.exists(path) and not os.path.isdir(path):
                os.remove(path)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(f"Não foi possível garantir {path}: {e}")

# Executa a garantia uma única vez ao carregar o módulo
_garantir_ambientes()

def _obter_configuracao_tidb() -> Dict[str, object]:
    url = os.getenv("TIDB_URL") or ""
    if not url:
        return {"host": None, "port": 4000, "user": None, "password": None, "database": None}
    parsed = urllib.parse.urlparse(url)
    return {
        "host": parsed.hostname or "",
        "port": parsed.port or int(os.getenv("TIDB_PORT", "4000")),
        "user": os.getenv("TIDB_USER") or "root",
        "password": os.getenv("TIDB_PASSWORD") or "",
        "database": urllib.parse.unquote(parsed.path.lstrip("/")) or os.getenv("TIDB_DATABASE", "sentinela"),
    }

def _credenciais_tidb_estao_validas(configuracao: Dict[str, object]) -> bool:
    user = str(configuracao.get("user") or "").strip()
    password = str(configuracao.get("password") or "").strip()
    return user not in {"", "root"} and password != ""

def _carregar_modulo_tidb():
    if not os.getenv("TIDB_URL"): return None
    try:
        import pymysql
        return pymysql
    except ImportError:
        return None

def _conectar_tidb():
    pymysql = _carregar_modulo_tidb()
    if pymysql is None: return None
    config = _obter_configuracao_tidb()
    params = {"host": config["host"], "user": config["user"], "password": config["password"], "port": config["port"], "autocommit": True, "connect_timeout": 5}
    if config["database"]: params["database"] = config["database"]
    return pymysql.connect(**params)

def _persistir_tidb(payload: Dict[str, object]) -> bool:
    try:
        conn = _conectar_tidb()
        if not conn: return False
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS relatorios (id BIGINT PRIMARY KEY AUTO_RANDOM, alvo TEXT, gerado_em TEXT, payload JSON)")
            cur.execute("INSERT INTO relatorios (alvo, gerado_em, payload) VALUES (%s, %s, %s)", (payload.get("alvo"), payload.get("gerado_em"), json.dumps(payload, ensure_ascii=False)))
        conn.close()
        return True
    except: return False

def _persistir_arquivo_local(payload: Dict[str, object], caminho: str) -> None:
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar JSON local: {e}")

def obter_ultimo_relatorio() -> Optional[Dict[str, object]]:
    caminho = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def categorizar(vulns: List[Vulnerabilidade]) -> Dict[str, List[Vulnerabilidade]]:
    grupos = {}
    for v in vulns: grupos.setdefault(v.categoria, []).append(v)
    return grupos

def priorizar(vulns: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    return sorted(vulns, key=lambda v: PESO_SEVERIDADE.get(v.severidade.upper(), 0), reverse=True)

def reavaliar(anteriores: List[Vulnerabilidade], atuais: List[Vulnerabilidade]) -> List[Vulnerabilidade]:
    ids_atuais = {v.identificador for v in atuais}
    res = list(atuais)
    for v in anteriores:
        if v.identificador not in ids_atuais:
            v.corrigida = True
            res.append(v)
    return res

def _gerar_metricas(vulns: List[Vulnerabilidade]) -> Dict[str, int]:
    m = {"TOTAL": len(vulns), "CORRIGIDAS": 0, "CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    for v in vulns:
        if v.corrigida: m["CORRIGIDAS"] += 1
        else: m[v.severidade.upper()] = m.get(v.severidade.upper(), 0) + 1
    return m

def gerar_relatorio(vulns: List[Vulnerabilidade], alvo: str) -> Dict[str, str]:
    c = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path_json = os.path.join(DIR_RELATORIOS, f"relatorio_{c}.json")
    path_front = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    
    payload = {
        "alvo": alvo, "gerado_em": datetime.utcnow().isoformat(),
        "metricas": _gerar_metricas(priorizar(vulns)),
        "categorias": {cat: normalizar_lista(lst) for cat, lst in categorizar(priorizar(vulns)).items()}
    }
    with open(path_json, "w", encoding="utf-8") as f: json.dump(payload, f, ensure_ascii=False, indent=2)
    _persistir_arquivo_local(payload, path_front)
    _persistir_tidb(payload)
    return {"json": path_json, "frontend": path_front}
