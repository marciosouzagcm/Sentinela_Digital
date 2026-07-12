"""
Módulo de Análise Estática de Código (Etapa 3 do processo).

Realiza análise heurística em código-fonte buscando padrões inseguros.
Suporta diretiva '# nosec' para ignorar linhas específicas.
"""

import os
import re
from typing import List, Tuple

from .utilidades import obter_logger, Vulnerabilidade

logger = obter_logger("analise_codigo")

# Extensões de arquivos que serão inspecionados
EXTENSOES_SUPORTADAS = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".rb", ".go"}

# Regras (regex, categoria OWASP, severidade, título, mitigação)
REGRAS: List[Tuple[re.Pattern, str, str, str, str]] = [
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{8,}['\"]"),
     "A02", "ALTA", "Segredo possivelmente hardcoded",
     "Mover para variáveis de ambiente ou cofre de segredos."),

    (re.compile(r"(?i)eval\s*\("),
     "A03", "ALTA", "Uso de eval() detectado",
     "Evitar eval; usar parsers seguros ou sandboxes."),

    (re.compile(r"(?i)exec\s*\(|subprocess\.(call|Popen|run)\([^)]*shell\s*=\s*True"),
     "A03", "ALTA", "Execução de comando potencialmente injetável",
     "Validar entradas e evitar shell=True; usar listas de argumentos."),

    (re.compile(r"(?i)select\s+.+\s+from\s+.+\+\s*\w+|f['\"].*SELECT.*\{.*\}"),
     "A03", "CRITICA", "Injeção SQL (concatenação ou f-string)",
     "Usar consultas parametrizadas ou ORM."),

    (re.compile(r"(?i)md5\(|sha1\("),
     "A02", "MEDIA", "Hash fraco (MD5/SHA1) em uso",
     "Substituir por SHA-256/512 ou algoritmos modernos (bcrypt/argon2)."),

    (re.compile(r"(?i)verify\s*=\s*False"),
     "A02", "ALTA", "Validação de certificado TLS desabilitada",
     "Manter verify=True; corrigir cadeia de certificados."),

    (re.compile(r"(?i)pickle\.loads?\("),
     "A08", "ALTA", "Desserialização insegura (pickle)",
     "Usar formatos seguros como JSON ou validar estritamente a origem."),

    (re.compile(r"(?i)debug\s*=\s*True|app\.run\(.*debug\s*=\s*True"),
     "A05", "CRITICA", "Modo debug habilitado em produção",
     "Desabilitar debug; nunca expor consoles interativos."),

    (re.compile(r"yaml\.load\("),
     "A08", "ALTA", "Desserialização insegura via PyYAML",
     "Utilizar yaml.safe_load()."),

    (re.compile(r"@csrf_exempt"),
     "A01", "ALTA", "CSRF desabilitado (csrf_exempt)",
     "Verificar se o endpoint realmente deve ser público."),

    (re.compile(r"format_html\s*\("),
     "A03", "ALTA", "Possível uso inseguro de format_html",
     "Garantir higienização total de inputs antes de renderizar."),
]


def analisar_diretorio(caminho: str) -> List[Vulnerabilidade]:
    """Varre recursivamente o diretório aplicando regras de segurança."""
    achados: List[Vulnerabilidade] = []
    if not os.path.isdir(caminho):
        logger.warning("Diretório inválido: %s", caminho)
        return achados

    contador = 0
    for raiz, _dirs, arquivos in os.walk(caminho):
        if any(p in raiz for p in ("node_modules", ".git", "dist", "build", "__pycache__")):
            continue
        for nome in arquivos:
            if os.path.splitext(nome)[1].lower() not in EXTENSOES_SUPORTADAS:
                continue
            
            caminho_arq = os.path.join(raiz, nome)
            try:
                with open(caminho_arq, "r", encoding="utf-8", errors="ignore") as f:
                    for n_linha, linha in enumerate(f, start=1):
                        # Mecanismo de supressão
                        if "# nosec" in linha:
                            continue
                            
                        for regex, cat, sev, titulo, mitig in REGRAS:
                            if regex.search(linha):
                                contador += 1
                                achados.append(Vulnerabilidade(
                                    identificador=f"{cat}-COD-{contador:04d}",
                                    categoria=cat,
                                    titulo=titulo,
                                    descricao=f"Padrão inseguro em {caminho_arq}:{n_linha}.",
                                    ativo=f"{caminho_arq}:{n_linha}",
                                    severidade=sev,
                                    evidencia=linha.strip()[:200],
                                    mitigacao=mitig,
                                ))
            except OSError as erro:
                logger.warning("Não foi possível ler %s: %s", caminho_arq, erro)

    logger.info("Análise estática concluída: %d achados.", len(achados))
    return achados
