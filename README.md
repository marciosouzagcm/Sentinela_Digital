# Sentinela Digital 🛡️
Scanner OWASP Top 10 Open Source com Python + React

[![Python](https://img.shields.io/badge/Python-3.12-blue)]()
[![React](https://img.shields.io/badge/React-Vite-61DAFB)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**[👉 Testar Demo Ao Vivo](https://SEU-LINK-VERCEL.vercel.app)**

![Demo GIF do Sentinela escaneando um site](link-do-seu-gif.gif)

### O que é?
O Sentinela Digital é uma ferramenta que audita sites em busca de vulnerabilidades do OWASP Top 10.
Em 2 minutos você recebe um relatório com falhas de segurança, severidade e como corrigir.

**Pipeline completo:** Recon → Port Scan → SAST → DAST → SCA → Sniffer → Relatório

### O que ele faz
| Etapa | Ferramenta | OWASP Coberto |
| --- | --- | --- |
| **Coleta** | DNS/HTTP | Recon Passivo |
| **Port Scan** | Nmap/Socket | A05, A07 |
| **SAST** | Regex Heurístico | A03, A08 |
| **DAST** | Testes HTTP | A01, A02, A10 |
| **SCA** | pip-audit | A06 |
| **Sniffer** | Scapy | Análise de Tráfego |

### Stack Técnica
`Python 3.12` `FastAPI` `TiDB` `React` `Vite` `Tailwind` `Render` `Vercel` `Scapy`

Backend deployado na Render. Frontend na Vercel. DB TiDB na nuvem.

### Como usar
```bash
# 1. Clone
git clone https://github.com/marciosouzagcm/Sentinela_Digital.git

# 2. Backend
cd Sentinela_Digital
pip install -r requirements.txt
python3 main.py --alvo https://seusite.com

# 3. Frontend
npm install && npm run dev
