import os
import shutil

# Definição do caminho
DIR_FRONTEND_RELATORIOS = os.path.join(os.path.dirname(__file__), '..', 'public', 'relatorios')

# --- BLOCO DE CORREÇÃO ---
if os.path.exists(DIR_FRONTEND_RELATORIOS):
    # Se existir e NÃO for um diretório, apaga o "arquivo intruso"
    if not os.path.isdir(DIR_FRONTEND_RELATORIOS):
        os.remove(DIR_FRONTEND_RELATORIOS)
        os.makedirs(DIR_FRONTEND_RELATORIOS)
else:
    # Se não existir, cria o diretório
    os.makedirs(DIR_FRONTEND_RELATORIOS, exist_ok=True)

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
