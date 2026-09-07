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

DIR_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
DIR_FRONTEND_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "relatorios")

def _seguro_makedirs(caminho: str):
    if not os.path.exists(caminho):
        os.makedirs(caminho, exist_ok=True)

_seguro_makedirs(DIR_RELATORIOS)
_seguro_makedirs(DIR_FRONTEND_RELATORIOS)

# --- CONFIGURAÇÃO TIDB ---
def _obter_configuracao_tidb() -> Dict[str, object]:
    url = os.getenv("TIDB_URL") or ""
    if not url:
        return {"host": None, "port": 4000, "user": None, "password": None, "database": None}
    parsed = urllib.parse.urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 4000,
        "user": parsed.username or os.getenv("TIDB_USER", "root"),
        "password": parsed.password or os.getenv("TIDB_PASSWORD", ""),
        "database": parsed.path.lstrip("/") or os.getenv("TIDB_DATABASE", "sentinela"),
    }

def _carregar_modulo_tidb():
    try:
        import pymysql
        return pymysql
    except ImportError:
        return None

def _conectar_tidb():
    pymysql = _carregar_modulo_tidb()
    if not pymysql: return None
    config = _obter_configuracao_tidb()
    if not config["host"]: return None
    try:
        return pymysql.connect(
            host=str(config["host"]), user=str(config["user"]),
            password=str(config["password"]), port=int(config["port"]),
            database=str(config["database"]), autocommit=True, connect_timeout=5
        )
    except Exception as exc:
        logger.error("Falha ao conectar no TiDB: %s", exc)
        return None

def _persistir_tidb(payload: Dict[str, object]) -> bool:
    connection = _conectar_tidb()
    if not connection: return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS relatorios (id BIGINT PRIMARY KEY AUTO_INCREMENT, alvo TEXT, gerado_em TEXT, payload JSON)")
            cursor.execute("INSERT INTO relatorios (alvo, gerado_em, payload) VALUES (%s, %s, %s)", 
                           (str(payload.get("alvo")), str(payload.get("gerado_em")), json.dumps(payload, ensure_ascii=False)))
        connection.close()
        logger.info("Relatório persistido com sucesso no TiDB")
        return True
    except Exception as exc:
        logger.error("Erro ao gravar no TiDB: %s", exc)
        return False

# --- LÓGICA DE NEGÓCIO ---
def categorizar(vulns: List[Vulnerabilidade]) -> Dict[str, List[Vulnerabilidade]]:
    grupos = {}
    for v in vulns: grupos.setdefault(v.categoria, []).append(v)
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
        if v.corrigida: metricas["CORRIGIDAS"] += 1
        else: metricas[v.severidade.upper()] = metricas.get(v.severidade.upper(), 0) + 1
    return metricas

def obter_ultimo_relatorio() -> Optional[Dict[str, object]]:
    caminho = os.path.join(DIR_FRONTEND_RELATORIOS, "ultimo_relatorio.json")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    return None

def gerar_relatorio(vulns: List[Vulnerabilidade], alvo: str) -> Dict[str, str]:
    carimbo = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    nome_base = f"relatorio_{carimbo}"
    caminho_json = os.path.join(DIR_RELATORIOS, nome_base + ".json")
    caminho_txt  = os.path.join(DIR_RELATORIOS, nome_base + ".txt")
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
    
    # Salvar JSONs (Histórico e Frontend)
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(caminho_frontend, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Persistir no TiDB
    _persistir_tidb(payload)

    # Gerar TXT completo e profissional
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write(f"RELATÓRIO DE VULNERABILIDADES - {alvo}\n")
        f.write(f"Gerado em (UTC): {payload['gerado_em']}\n")
        f.write("=" * 72 + "\n\n")
        f.write("MÉTRICAS:\n")
        for k, v in metricas.items():
            f.write(f"  - {k:<10}: {v}\n")
        f.write("\n")
        
        for cat, lst in grupos.items():
            f.write(f"[{cat}] {len(lst)} achado(s)\n")
            f.write("-" * 72 + "\n")
            for v in priorizar(lst):
                status = "[CORRIGIDA]" if v.corrigida else f"[{v.severidade.upper()}]"
                f.write(f"{status} {v.identificador} - {v.titulo}\n")
                f.write(f"  Ativo    : {v.ativo}\n")
                f.write(f"  Descrição: {v.descricao}\n")
                if v.evidencia:
                    f.write(f"  Evidência: {v.evidencia}\n")
                f.write(f"  Mitigação: {v.mitigacao}\n\n")

    logger.info(f"Relatório TXT completo gerado em: {caminho_txt}")
    return {"json": caminho_json, "txt": caminho_txt}


