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
from datetime import datetime
from typing import Dict, List

from .utilidades import (
    Vulnerabilidade, PESO_SEVERIDADE, normalizar_lista, obter_logger,
)

logger = obter_logger("gestao")

# Diretório padrão dos relatórios
DIR_RELATORIOS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
os.makedirs(DIR_RELATORIOS, exist_ok=True)


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

    logger.info("Relatórios gerados: %s | %s", caminho_json, caminho_txt)
    return {"json": caminho_json, "txt": caminho_txt}
