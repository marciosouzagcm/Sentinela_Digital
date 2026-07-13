import json
import os

# Ajuste: O caminho agora é relativo à pasta do projeto
# Isso evita depender do caminho absoluto da sua máquina local (/home/marciosouza/...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_FRONTEND = os.path.join(BASE_DIR, 'public', 'relatorios')
DIR_RELATORIOS = os.path.join(BASE_DIR, 'relatorios')

def garantir_diretorio(caminho):
    """Função robusta para criar diretório e evitar FileExistsError."""
    if os.path.exists(caminho):
        if not os.path.isdir(caminho):
            os.remove(caminho)  # Remove se for um arquivo bloqueando a pasta
            os.makedirs(caminho)
    else:
        os.makedirs(caminho, exist_ok=True)

def salvar_relatorio(dados):
    # 1. Garante que os diretórios existam de forma segura
    garantir_diretorio(DIR_RELATORIOS)
    garantir_diretorio(CAMINHO_FRONTEND)

    # 2. Nome do arquivo com timestamp
    timestamp = dados['gerado_em'].replace(':', '').replace('-', '').replace('.', '')
    nome_arquivo = os.path.join(DIR_RELATORIOS, f"relatorio_{timestamp}.json")
    
    # 3. Salva o histórico
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    # 4. Salva o 'ultimo_relatorio.json' para o React consumir
    caminho_fixo = os.path.join(CAMINHO_FRONTEND, "ultimo_relatorio.json")
    with open(caminho_fixo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    print(f"[*] Relatório salvo em: {nome_arquivo}")
    print(f"[*] Frontend atualizado em: {caminho_fixo}")
