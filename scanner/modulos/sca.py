"""
Módulo de Análise de Composição de Software (SCA).

Verifica dependências (requirements.txt) em busca de vulnerabilidades 
conhecidas utilizando o pip-audit.
"""

import subprocess
import json
import os
from typing import List
from .utilidades import obter_logger, Vulnerabilidade

logger = obter_logger("sca")

def analisar_dependencias(diretorio: str) -> List[Vulnerabilidade]:
    """Executa o pip-audit para checar vulnerabilidades nas dependências."""
    achados = []
    caminho_req = os.path.join(diretorio, "requirements.txt")
    
    if not os.path.exists(caminho_req):
        return achados

    logger.info("Iniciando auditoria de dependências (SCA) em: %s", caminho_req)

    try:
        # Executa o pip-audit em formato JSON
        resultado = subprocess.run(
            ["pip-audit", "-r", caminho_req, "--format", "json"],
            capture_output=True, text=True
        )
        
        if resultado.returncode != 0 and not resultado.stdout:
            return achados

        dados = json.loads(resultado.stdout)
        
        for dep in dados.get("dependencies", []):
            for vulns in dep.get("vulns", []):
                achados.append(Vulnerabilidade(
                    identificador=f"A06-SCA-{vulns['id']}",
                    categoria="A06",
                    titulo=f"Vulnerabilidade em {dep['name']}",
                    descricao=f"Pacote {dep['name']} ({dep['version']}) vulnerável: {vulns['description']}",
                    ativo=caminho_req,
                    severidade="ALTA",
                    evidencia=f"ID CVE: {vulns['id']}",
                    mitigacao=f"Atualize para uma versão segura conforme recomendado em: {vulns.get('fix_versions', 'verifique o repositório oficial')}"
                ))
                
    except Exception as e:
        logger.warning("Erro ao executar SCA: %s", e)

    logger.info("Análise SCA concluída: %d achados.", len(achados))
    return achados
