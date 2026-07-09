import json
import os
import shutil

# Defina o caminho para a pasta 'public' do seu projeto React
# Ajuste este caminho conforme a localização real da sua pasta sentinela-dashboard
CAMINHO_FRONTEND = "/home/marciosouza/sentinela-dashboard/public/relatorios"

def salvar_relatorio(dados):
    # 1. Garante que o diretório de relatórios exista
    os.makedirs("relatorios", exist_ok=True)
    os.makedirs(CAMINHO_FRONTEND, exist_ok=True)

    # 2. Nome do arquivo com timestamp (para histórico)
    nome_arquivo = f"relatorios/relatorio_{dados['gerado_em'].replace(':', '').replace('-', '').replace('.', '')}.json"
    
    # 3. Salva o histórico
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    # 4. Salva o 'ultimo_relatorio.json' para o React consumir
    caminho_fixo = os.path.join(CAMINHO_FRONTEND, "ultimo_relatorio.json")
    with open(caminho_fixo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
        
    print(f"[*] Relatório salvo em: {nome_arquivo}")
    print(f"[*] Frontend atualizado em: {caminho_fixo}")
