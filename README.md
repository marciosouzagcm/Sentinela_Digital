# Scanner de Vulnerabilidades (Python)

Ferramenta automatizada de análise de vulnerabilidades desenvolvida em **Python 3**, focada em ambientes **Linux**. O projeto automatiza a identificação de riscos seguindo as categorias do **OWASP Top 10**.

## 🛠 Arquitetura do Projeto

```text
scanner/
├── main.py              # Entrada principal
├── modulos/             # Lógica de negócio e varredura
│   ├── coleta.py
│   ├── escaneamento.py
│   ├── analise_codigo.py
│   ├── pentest.py
│   └── gestao.py        # Ciclo de vida das vulnerabilidades
├── relatorios/          # Saídas em formato JSON e TXT
├── logs/                # Histórico de execução
└── requirements.txt     # Dependências Python
```

## 📋 Categorias OWASP Implementadas
Cobertura completa (A01 - A10), incluindo:
- **Análise Estática:** Identificação de falhas em código (`analise_codigo.py`).
- **Análise Dinâmica:** Varredura de rede e testes de penetração leves.
- **Gestão de Risco:** Implementação de pontuação **CVSS simplificada** para priorização.

## 🚀 Instalação

```bash
# Atualização e dependências do sistema
sudo apt update && sudo apt install -y python3 python3-pip nmap

# Configuração do ambiente
git clone https://github.com/marciosouzagcm/Sentinela_Digital.git
cd Sentinela_Digital
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 💻 Uso

```bash
# Escaneamento de rede
python3 main.py --alvo 192.168.0.1

# Análise completa (web + código)
python3 main.py --alvo https://exemplo.com --codigo ./projeto_alvo

# Monitoramento contínuo (reavaliação a cada 60 min)
python3 main.py --alvo 192.168.0.1 --continuo 60
```

## ⚖️ Aviso Legal
*Utilize apenas em ativos próprios ou com autorização formal por escrito. O autor não se responsabiliza pelo uso indevido desta ferramenta, que pode infringir a Lei 12.737/2012 (Lei Carolina Dieckmann) e legislações correlatas.*

---
*Desenvolvido por Marcio Souza | 2026*