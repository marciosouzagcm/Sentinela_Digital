# Sentinela Digital 🛡️

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Linux](https://img.shields.io/badge/Ambiente-Linux%20VM-orange)
![OWASP](https://img.shields.io/badge/OWASP-Top%2010-red)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

> **Scanner modular de vulnerabilidades web** desenvolvido em Python, com foco em **OWASP Top 10**, análise estática (SAST), auditoria de dependências (SCA) e captura de tráfego (Sniffer). Projetado para rodar em ambiente **Linux (VM)** e servir como ferramenta de triagem contínua de segurança em pipelines de **DevSecOps**.

### 🌐 Aplicação em produção

| Ambiente | URL |
| -------- | --- |
| 🖥️ **Frontend (Vercel)** | [sentineladigital-marciosouzagcm-9672s-projects.vercel.app](https://sentineladigital-marciosouzagcm-9672s-projects.vercel.app) |
| ⚙️ **Backend / API (Render)** | [sentinela-digital-cxk8.onrender.com](https://sentinela-digital-cxk8.onrender.com) |
| 📦 **Código-fonte (GitHub)** | [github.com/marciosouzagcm/Sentinela_Digital](https://github.com/marciosouzagcm/Sentinela_Digital) |

---

## 📌 Sobre o Projeto

O **Sentinela Digital** é uma ferramenta open source de *Pentest* automatizado, criada para apoiar times de **Cibersegurança** e **DevOps** na identificação precoce de falhas em aplicações web. Ele combina múltiplas técnicas em um único pipeline:

**Recon → Port Scan → SAST → DAST → SCA → Sniffer → Relatório HTML**

O objetivo é entregar, em poucos minutos, um relatório claro contendo vulnerabilidades detectadas, severidade e recomendações de correção — reduzindo o tempo entre a descoberta e a mitigação (MTTR).

---

## 🎬 Demonstração

Assista à demo completa de 4 minutos do Sentinela Digital em funcionamento:

[![Assista à Demo](https://img.youtube.com/vi/uE9Vl4iQVuQ/maxresdefault.jpg)](https://youtu.be/uE9Vl4iQVuQ)

> O vídeo mostra: **Execução do scan → Análise de vulnerabilidades → Geração do `relatorio.html`.**

---

## 🧠 Fundamentação Teórica

### 🔐 OWASP — Open Web Application Security Project

A **OWASP** é uma fundação sem fins lucrativos, reconhecida internacionalmente, que produz artefatos livres sobre segurança de software. Seu material mais famoso é o **OWASP Top 10**, uma lista consolidada com as dez categorias de vulnerabilidades mais críticas em aplicações web, atualizada periodicamente com base em dados reais de milhares de aplicações auditadas.

Categorias abordadas pelo Sentinela Digital (baseadas no OWASP Top 10 — 2021):

| Código | Categoria | Descrição resumida |
| ------ | --------- | ------------------ |
| **A01** | Broken Access Control | Falhas no controle de acesso a recursos protegidos. |
| **A02** | Cryptographic Failures | Uso incorreto ou ausência de criptografia. |
| **A03** | Injection | Injeção de código (SQLi, XSS, Command Injection). |
| **A05** | Security Misconfiguration | Serviços expostos, headers ausentes, configs padrão. |
| **A06** | Vulnerable & Outdated Components | Bibliotecas com CVEs conhecidos. |
| **A07** | Identification & Authentication Failures | Falhas em autenticação e gestão de sessão. |
| **A08** | Software & Data Integrity Failures | Pipelines e artefatos sem verificação de integridade. |
| **A10** | Server-Side Request Forgery (SSRF) | Requisições forjadas a partir do servidor. |

Adotar o OWASP Top 10 como referência é considerado **boa prática de mercado** e frequentemente exigido em frameworks de conformidade como **ISO 27001, PCI-DSS, LGPD e SOC 2**.

### 📡 Sniffers — Análise de Tráfego de Rede

Um **Sniffer** (ou *Packet Analyzer*) é uma ferramenta que **captura e inspeciona pacotes que trafegam em uma interface de rede**. Ele opera em modo **promíscuo**, permitindo observar não apenas o tráfego destinado à máquina local, mas também pacotes que atravessam o segmento de rede em que ela está conectada.

**Aplicações legítimas de sniffers em Cibersegurança e DevOps:**

- 🔍 **Diagnóstico de rede** — troubleshooting de latência, perda de pacotes e falhas de conectividade.
- 🕵️ **Detecção de intrusões (IDS)** — identificação de padrões maliciosos (port scans, exfiltração, C2).
- 🔐 **Auditoria de protocolos** — verificar se credenciais/tokens trafegam sem criptografia (HTTP, FTP, Telnet).
- 📊 **Análise forense** — reconstrução de eventos após incidentes de segurança.
- ⚙️ **Validação de hardening** — confirmar que apenas portas/serviços autorizados estão expostos.

No **Sentinela Digital**, o módulo de sniffer é implementado com a biblioteca **Scapy**, utilizada de forma **ética e controlada** dentro da própria VM Linux, com o objetivo de identificar tráfego em texto claro e serviços expostos que representem risco à aplicação alvo.

> ⚠️ **Aviso legal:** A captura de tráfego em redes de terceiros sem autorização é ilegal na maioria das jurisdições (no Brasil, Lei 12.737/2012 — Lei Carolina Dieckmann). Use apenas em ambientes próprios ou com autorização formal.

---

## 🏗️ Arquitetura

```text
┌──────────────────────────────────────────────────────────────┐
│                   Sentinela Digital (VM Linux)               │
├──────────────────────────────────────────────────────────────┤
│  [ CLI ] ──▶ main.py ──▶ orquestrador de módulos             │
│                              │                               │
│      ┌───────────┬───────────┼──────────┬──────────┐         │
│      ▼           ▼           ▼          ▼          ▼         │
│   Recon      Port Scan     SAST       DAST        SCA        │
│  (DNS/HTTP)   (Nmap)     (Regex)   (HTTP tests) (pip-audit)  │
│                              │                               │
│                              ▼                               │
│                       Sniffer (Scapy)                        │
│                              │                               │
│                              ▼                               │
│                     Geração de relatorio.html                │
└──────────────────────────────────────────────────────────────┘
```

---

## 🧰 Stack Técnica

`Python 3.12` · `Scapy` · `Requests` · `BeautifulSoup` · `Nmap` · `pip-audit` · `Jinja2` · `Linux (Debian/Ubuntu VM)`

---

## 🚀 Como Usar

Projeto testado em **VM Linux (Debian 12 / Ubuntu 22.04)**.

### 1. Pré-requisitos

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nmap git
```

### 2. Clone e ambiente virtual

```bash
git clone https://github.com/marciosouzagcm/Sentinela_Digital.git
cd Sentinela_Digital
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute o scanner

```bash
sudo python3 main.py --alvo https://example.com
```

> `sudo` é necessário apenas para o módulo Sniffer (Scapy exige privilégios de raw socket).

### 5. Visualize o relatório

```bash
xdg-open relatorio.html
```

---

## 💻 Habilidades Demonstradas

- ✅ **Automação em Python** aplicada a Segurança Ofensiva.
- ✅ **Análise de vulnerabilidades OWASP Top 10** (SAST + DAST + SCA).
- ✅ **Captura e análise de pacotes** com Scapy.
- ✅ **Web Scraping e requisições HTTP** com `requests` + `BeautifulSoup`.
- ✅ **Geração de relatórios HTML** com templates Jinja2.
- ✅ **Boas práticas de código** — modularização, tratamento de exceções, logging estruturado.
- ✅ **Ambiente Linux (VM)** — familiaridade com `bash`, `apt`, `systemd`, permissões e hardening.
- ✅ **Mentalidade DevSecOps** — segurança integrada ao ciclo de desenvolvimento.

---

## 🗺️ Roadmap

- [ ] Integração com **CI/CD** (GitHub Actions) para scan automatizado a cada push.
- [ ] Exportação de relatórios em **JSON** e **SARIF** (compatível com GitHub Security).
- [ ] Dashboard web em **FastAPI + React**.
- [ ] Containerização com **Docker**.
- [ ] Suporte a autenticação para scan de áreas logadas.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma *issue* descrevendo a proposta ou envie um *pull request* seguindo o padrão de commits [Conventional Commits](https://www.conventionalcommits.org/).

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais detalhes.

---

## 🔗 Contato

**Márcio Almeida de Souza**

- 🐙 GitHub: [github.com/marciosouzagcm](https://github.com/marciosouzagcm)
- 💼 LinkedIn: [linkedin.com/in/márcio-almeida-de-souza](https://www.linkedin.com/in/m%C3%A1rcio-almeida-de-souza-155171115)

> *Aberto a oportunidades nas áreas de **Cibersegurança**, **DevSecOps** e **SRE**.*

---

## 📝 Descrição sugerida para o vídeo no YouTube

```text
🛡️ Sentinela Digital — Scanner de Vulnerabilidades OWASP Top 10 em Python

Nesta demo de 4 minutos, mostro o Sentinela Digital em ação: uma ferramenta
open source de Pentest automatizado que desenvolvi em Python, rodando em VM
Linux, para auditar aplicações web com base no OWASP Top 10.

🔎 O que você vai ver no vídeo:
 • Execução do scan a partir da linha de comando
 • Pipeline completo: Recon → Port Scan → SAST → DAST → SCA → Sniffer
 • Detecção de vulnerabilidades e classificação por severidade
 • Geração do relatório final em HTML
 • Aplicação disponível online (Frontend na Vercel + Backend na Render)

🌐 Acesse a aplicação:
 • Frontend (Vercel): https://sentineladigital-marciosouzagcm-9672s-projects.vercel.app
 • Backend  (Render): https://sentinela-digital-cxk8.onrender.com

🧰 Stack: Python 3.12 · Scapy · Requests · BeautifulSoup · Nmap · pip-audit · Jinja2 · React (Vite) · FastAPI
💻 Ambiente: Linux (VM Debian/Ubuntu) · Deploy: Vercel + Render

📂 Código-fonte: https://github.com/marciosouzagcm/Sentinela_Digital
👨‍💻 GitHub: https://github.com/marciosouzagcm
💼 LinkedIn: https://www.linkedin.com/in/m%C3%A1rcio-almeida-de-souza-155171115

Projeto desenvolvido com foco em Cibersegurança e DevSecOps, demonstrando
automação, análise de vulnerabilidades, deploy em nuvem e boas práticas
de programação.

#Cibersegurança #DevSecOps #Python #OWASP #Pentest #Linux #InfoSec #Vercel #Render
```
