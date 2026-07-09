=======
# Sentinela Digital — Auditoria Técnica e de Cibersegurança

> Documento de auditoria ponta a ponta do projeto **Sentinela_Digital**
> Repositório analisado: <https://github.com/marciosouzagcm/Sentinela_Digital.git>
> Ambiente de execução alvo: **Linux (Máquina Virtual)**
> Idioma: **Português (PT-BR)**
> Escopo: análise arquitetural, revisão de código, mapeamento OWASP, análise de dependências (SCA), análise dinâmica (DAST/pentest leve), captura de pacotes (sniffer), gestão de vulnerabilidades, boas práticas de programação, hardening operacional e recomendações de correção.

---

## Sumário

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Arquitetura e Componentes](#2-arquitetura-e-componentes)
3. [Estrutura do Repositório](#3-estrutura-do-repositório)
4. [Fundamentação Teórica](#4-fundamentação-teórica)
   - 4.1 [OWASP — o que é e por que importa](#41-owasp--o-que-é-e-por-que-importa)
   - 4.2 [OWASP Top 10 (2021) aplicado ao Sentinela](#42-owasp-top-10-2021-aplicado-ao-sentinela)
   - 4.3 [Sniffers — teoria, funcionamento e implicações legais](#43-sniffers--teoria-funcionamento-e-implicações-legais)
5. [Metodologia da Auditoria](#5-metodologia-da-auditoria)
6. [Requisitos, Instalação e Execução em Linux](#6-requisitos-instalação-e-execução-em-linux)
7. [Análise Módulo a Módulo](#7-análise-módulo-a-módulo)
8. [Análise Estática de Código (SAST)](#8-análise-estática-de-código-sast)
9. [Análise de Composição de Software (SCA)](#9-análise-de-composição-de-software-sca)
10. [Análise Dinâmica (DAST / Pentest Leve)](#10-análise-dinâmica-dast--pentest-leve)
11. [Análise de Rede e Sniffer](#11-análise-de-rede-e-sniffer)
12. [Front-end (Dashboard React)](#12-front-end-dashboard-react)
13. [Gestão de Vulnerabilidades e Relatórios](#13-gestão-de-vulnerabilidades-e-relatórios)
14. [Achados de Segurança Consolidados](#14-achados-de-segurança-consolidados)
15. [Boas Práticas de Programação — Diagnóstico e Recomendações](#15-boas-práticas-de-programação--diagnóstico-e-recomendações)
16. [Hardening do Ambiente Linux](#16-hardening-do-ambiente-linux)
17. [DevSecOps e CI/CD Recomendado](#17-devsecops-e-cicd-recomendado)
18. [Plano de Remediação Priorizado](#18-plano-de-remediação-priorizado)
19. [Roadmap de Evolução](#19-roadmap-de-evolução)
20. [Conformidade Legal (LGPD, ISO 27001, NIST)](#20-conformidade-legal-lgpd-iso-27001-nist)
21. [Glossário](#21-glossário)
22. [Referências](#22-referências)
23. [Licença](#23-licença)

---

## 1. Visão Geral do Projeto

O **Sentinela Digital** é uma plataforma didática/operacional de **auditoria e detecção de vulnerabilidades** escrita em **Python 3** para o núcleo de varredura, com um **dashboard web em React + Vite + TailwindCSS** para consumo dos relatórios.

A ferramenta implementa, de forma integrada, um ciclo clássico de gestão de vulnerabilidades composto por seis etapas:

1. **Coleta de Informações** (*reconhecimento passivo*)
2. **Escaneamento** de portas e serviços
3. **Análise Estática de Código** (SAST heurístico)
4. **Testes de Penetração Leves** (DAST em aplicações web)
5. **Análise de Composição de Software** (SCA via `pip-audit`)
6. **Captura de Tráfego** (Sniffer via Scapy)

Os achados são normalizados em um *dataclass* `Vulnerabilidade`, **categorizados segundo o OWASP Top 10**, priorizados por severidade e persistidos em relatórios `.json` e `.txt`, além de exportados para o front-end React em `public/relatorios/ultimo_relatorio.json`.

### Público-alvo

- Estudantes e profissionais de segurança ofensiva/defensiva.
- Equipes de DevSecOps que necessitam de uma prova de conceito auditável.
- Administradores de sistemas Linux que desejam automatizar auditorias periódicas.

### Escopo autorizado

> ⚠️ **Aviso ético e legal:** a ferramenta executa varreduras ativas (portas, cabeçalhos HTTP, caminhos administrativos) e captura de pacotes. Sua utilização é restrita a **ativos de propriedade do operador ou com autorização formal, expressa e documentada**. O uso indevido pode configurar crime nos termos da **Lei nº 12.737/2012 (Lei Carolina Dieckmann)** e do **Código Penal Brasileiro (art. 154-A)**.

---

## 2. Arquitetura e Componentes

```
                         ┌──────────────────────────────┐
                         │        main.py (CLI)         │
                         │  argparse + orquestração     │
                         └──────────────┬───────────────┘
                                        │
        ┌───────────────┬───────────────┼──────────────┬───────────────┐
        ▼               ▼               ▼              ▼               ▼
   coleta.py     escaneamento.py  analise_codigo   pentest.py       sca.py
   (recon)       (nmap/socket)    (SAST regex)    (DAST HTTP)     (pip-audit)
        │               │               │              │               │
        └───────────────┴───────┬───────┴──────────────┴───────────────┘
                                ▼
                          gestao.py
       (categorização, priorização, reavaliação, relatórios JSON/TXT)
                                │
                                ▼
                    relatorios/ + public/relatorios/
                                │
                                ▼
                    Dashboard React (Vite) — src/App.jsx

           Fluxo paralelo (thread daemon):
                sniffer.py (Scapy → relatorios/sniffer_log.txt)
```

**Padrões arquiteturais observados:**
- **Pipeline sequencial** com etapas independentes.
- **Modularização por responsabilidade** (`modulos/` com um arquivo por etapa).
- **Contrato único de saída** — todas as etapas emitem `List[Vulnerabilidade]`.
- **Logger centralizado** (`utilidades.obter_logger`) com escrita simultânea em arquivo e console.

---

## 3. Estrutura do Repositório

```
Sentinela_Digital/
├── App.jsx                 # Cópia legada (redundante — ver §15)
├── LICENSE
├── README.md
├── [192.168.0.10]          # Diretório suspeito com nome de IP (ver §14)
├── gestao.py               # Duplicata do módulo em modulos/ (ver §15)
├── index.html              # Entrada do Vite
├── main.py                 # CLI principal (Python)
├── modulos/
│   ├── __init__.py
│   ├── analise_codigo.py   # SAST heurístico por regex
│   ├── coleta.py           # Reconhecimento passivo (DNS/HTTP)
│   ├── escaneamento.py     # Nmap / fallback socket
│   ├── gestao.py           # Categorização, priorização, relatórios
│   ├── pentest.py          # DAST OWASP Top 10
│   ├── sca.py              # pip-audit
│   ├── sniffer.py          # Captura via Scapy
│   └── utilidades.py       # Logger + dataclass Vulnerabilidade
├── package.json / package-lock.json
├── postcss.config.js
├── public/
│   ├── favicon.svg
│   ├── icons.svg
│   └── relatorios/         # Consumido pelo React
├── requisitos.txt          # (nome PT-BR — divergente do padrão)
├── src/
│   ├── App.css / App.jsx / main.jsx / index.css
│   ├── assets/
│   ├── components/
│   └── lib/
├── tailwind.config.js
├── testes_código/          # Nome com acento — evitar (ver §15)
│   ├── requirements.txt
│   └── teste_inseguro.py   # Arquivo intencionalmente vulnerável
└── vite.config.js
```

---

## 4. Fundamentação Teórica

### 4.1 OWASP — o que é e por que importa

O **OWASP** (*Open Worldwide Application Security Project*) é uma **fundação sem fins lucrativos**, fundada em **2001**, que produz **padrões abertos, ferramentas, documentação e cursos** sobre segurança de software. Sua missão é **tornar a segurança de aplicações visível**, permitindo que organizações tomem decisões informadas sobre os riscos reais.

Os artefatos mais influentes mantidos pela OWASP incluem:

| Artefato | Descrição |
|----------|-----------|
| **OWASP Top 10** | Lista consensual das 10 categorias mais críticas de riscos em aplicações web. Atualizada a cada 3–4 anos. |
| **OWASP ASVS** | *Application Security Verification Standard* — padrão de requisitos verificáveis (níveis 1, 2 e 3). |
| **OWASP SAMM** | *Software Assurance Maturity Model* — modelo de maturidade para programas de segurança. |
| **OWASP Cheat Sheet Series** | Guias práticos e concisos por tema (CSRF, JWT, XSS, etc.). |
| **OWASP ZAP** | Proxy de interceptação e scanner DAST open-source. |
| **OWASP Dependency-Check / Dependency-Track** | Ferramentas de SCA. |
| **OWASP Juice Shop / WebGoat** | Aplicações vulneráveis para treinamento. |

**Por que o OWASP é relevante para o Sentinela Digital?**
O projeto **explicitamente mapeia cada regra de detecção a uma categoria do OWASP Top 10** (A01, A02, A03, A05, A06, A07, A08, A09, A10). Isso confere ao relatório final valor comunicacional e comparabilidade com auditorias externas — pois qualquer profissional que domine o Top 10 lê os achados sem tradução adicional.

### 4.2 OWASP Top 10 (2021) aplicado ao Sentinela

| ID | Categoria | Coberto pelo Sentinela? | Onde |
|----|-----------|-------------------------|------|
| **A01** | Broken Access Control | ✅ | `pentest.py` (caminhos administrativos), `analise_codigo.py` (`csrf_exempt`) |
| **A02** | Cryptographic Failures | ✅ | `analise_codigo.py` (MD5/SHA1, `verify=False`, segredos hardcoded), `pentest.py` (HTTP puro, HSTS ausente), `escaneamento.py` (FTP/Telnet) |
| **A03** | Injection | ✅ | `analise_codigo.py` (eval, `shell=True`, SQL concatenado) |
| **A04** | Insecure Design | ⚠️ Parcial | Não detectado programaticamente (requer *threat modeling*) |
| **A05** | Security Misconfiguration | ✅ | `pentest.py` (cabeçalhos ausentes, banner do servidor), `analise_codigo.py` (`debug=True`), `escaneamento.py` (Redis/Mongo expostos) |
| **A06** | Vulnerable and Outdated Components | ✅ | `sca.py` (pip-audit) |
| **A07** | Identification and Authentication Failures | ✅ | `escaneamento.py` (RDP exposto), `pentest.py` (autenticação fraca) |
| **A08** | Software and Data Integrity Failures | ✅ | `analise_codigo.py` (pickle, `yaml.load`) |
| **A09** | Security Logging and Monitoring Failures | ⚠️ Parcial | Heurística mínima em `pentest.py` |
| **A10** | Server-Side Request Forgery (SSRF) | ✅ | `pentest.py` (probe SSRF refletido) |

### 4.3 Sniffers — teoria, funcionamento e implicações legais

Um **sniffer** (também chamado de *packet analyzer*, *network analyzer* ou *protocol analyzer*) é um **software ou dispositivo capaz de capturar, decodificar e inspecionar pacotes de dados que trafegam por uma rede de computadores**. O termo consagrou-se nos anos 1990 com o programa comercial *Sniffer* da Network General, mas hoje refere-se genericamente a qualquer analisador de tráfego (Wireshark, tcpdump, tshark, Ettercap, Scapy, etc.).

#### 4.3.1 Como funciona (camada por camada)

1. **Camada Física / Enlace (L1/L2):** o sniffer coloca a interface de rede em **modo promíscuo** (`promiscuous mode`) — normalmente uma NIC descarta quadros Ethernet cujo endereço MAC de destino não seja o próprio; em modo promíscuo, todos os quadros do domínio de colisão/broadcast são entregues à pilha do SO. Em redes sem fio, o análogo é o **modo monitor**, que também remove a associação a um BSSID específico.
2. **Captura via kernel:** em Linux o mecanismo padrão é `AF_PACKET` + `PF_PACKET` sockets (usado por libpcap, tcpdump e Scapy). Em BSD/macOS existe o `BPF` (Berkeley Packet Filter). Em Windows, usa-se WinPcap/Npcap.
3. **Filtragem BPF:** os sniffers aceitam expressões BPF (por exemplo `tcp port 80 and host 10.0.0.5`) que são compiladas em bytecode executado dentro do kernel, descartando pacotes irrelevantes antes que cheguem ao *user space* — melhora radicalmente a performance.
4. **Decodificação:** cada pacote é interpretado camada por camada — Ethernet → IP → TCP/UDP → payload aplicacional (HTTP, DNS, TLS handshake, etc.).
5. **Persistência/Análise:** os pacotes são gravados em formato **PCAP** ou **PCAPNG**, ou processados em tempo real por *callbacks*.

#### 4.3.2 Tipos de sniffing

| Tipo | Descrição |
|------|-----------|
| **Passivo** | Apenas escuta o tráfego que naturalmente chega à interface (mais fácil em hubs, redes Wi-Fi abertas ou com espelhamento de porta / SPAN). É indetectável na camada de rede. |
| **Ativo** | Manipula a rede para forçar tráfego a passar pelo atacante — típico em switches. Técnicas: **ARP spoofing/poisoning**, **DHCP spoofing**, **MAC flooding**, **DNS spoofing**, **STP hijacking**. |

#### 4.3.3 Casos de uso legítimos

- **Troubleshooting** (latência, retransmissões, MTU, handshake TLS falho).
- **Detecção de intrusão** (IDS como Snort, Suricata, Zeek).
- **Auditoria de segurança** — verificar se dados sensíveis trafegam em texto claro.
- **Análise forense** — reconstruir sessões após incidente.
- **Ensino e pesquisa** — laboratórios de redes.

#### 4.3.4 Riscos e uso malicioso

- Captura de **credenciais** em protocolos sem criptografia (HTTP, FTP, Telnet, POP3, SMTP não-STARTTLS).
- **Session hijacking** via cookies capturados.
- **Reconhecimento** para *lateral movement* em redes comprometidas.
- **Vazamento de metadados** (padrões de tráfego, hosts consultados via DNS).

#### 4.3.5 Contramedidas

- **Criptografia ponta a ponta:** TLS 1.2+/1.3, SSH, VPN (IPsec/WireGuard), DoT/DoH.
- **Segmentação de rede** (VLANs, microssegmentação, zero-trust).
- **802.1X / NAC** para autenticação em porta de switch.
- **Detecção de modo promíscuo:** ferramentas como `PromiscDetect`, `nmap --script sniffer-detect`.
- **Port security** no switch (limite de MACs por porta, DAI — Dynamic ARP Inspection, DHCP Snooping).
- **Assinaturas digitais** e **integridade** de mensagens (HMAC).

#### 4.3.6 O sniffer do Sentinela

O módulo `modulos/sniffer.py` utiliza a biblioteca **Scapy** com filtro BPF `"tcp or udp"` e persiste alertas simples do tipo `IP_origem -> IP_destino` em `relatorios/sniffer_log.txt`. Trata-se de um sniffer **passivo, didático e minimalista**, cuja principal limitação é não decodificar payloads nem correlacionar eventos. Requer **privilégios de root** (`CAP_NET_RAW`) e a interface está **hardcoded** como `ens33` — típica de VMs VMware (ver §14).

> ⚠️ **Aspecto legal:** a captura de tráfego de terceiros sem autorização configura **interceptação telemática ilegal** no Brasil (Lei nº 9.296/1996). Use exclusivamente em redes próprias ou de laboratório.

---

## 5. Metodologia da Auditoria

A auditoria seguiu um modelo híbrido inspirado em **OWASP Code Review Guide v2.0**, **OWASP WSTG v4.2**, **NIST SP 800-115** (*Technical Guide to Information Security Testing and Assessment*) e **PTES** (*Penetration Testing Execution Standard*):

1. **Reconhecimento do repositório** (`git clone` + inventário de arquivos).
2. **Leitura arquitetural** (mapeamento de fluxos e responsabilidades).
3. **Revisão manual de código** — módulo a módulo (SAST manual).
4. **Análise heurística por padrões** — busca por *smells* de segurança.
5. **Revisão de dependências** — `requisitos.txt` vs. CVE conhecidas.
6. **Avaliação de configuração** — arquivos `vite.config.js`, `tailwind.config.js`, `package.json`.
7. **Verificação de boas práticas** — PEP 8, PEP 257, tipagem, cobertura de testes, tratamento de exceções.
8. **Categorização de achados** — OWASP Top 10 + CWE.
9. **Priorização** — matriz Severidade × Explorabilidade.
10. **Recomendações acionáveis** — com esforço estimado.

---

## 6. Requisitos, Instalação e Execução em Linux

### 6.1 Pré-requisitos do sistema (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nmap tcpdump libpcap-dev nodejs npm git
```

### 6.2 Ambiente virtual Python (isolamento recomendado)

```bash
cd Sentinela_Digital
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requisitos.txt
pip install scapy   # não listado em requisitos.txt (ver §14)
```

### 6.3 Front-end (dashboard React/Vite)

```bash
npm install
npm run dev            # servidor de desenvolvimento
npm run build          # build de produção
npm run preview        # servir build
```

### 6.4 Execução do scanner

```bash
# Escaneamento pontual de um alvo web + análise do próprio código
python3 main.py --alvo https://exemplo.com --codigo ./modulos

# Escaneamento contínuo (a cada 30 minutos)
python3 main.py --alvo https://exemplo.com --continuo 30

# Escaneamento com sniffer paralelo (requer root)
sudo -E python3 main.py --alvo 192.168.0.10 --sniffer
```

### 6.5 Permissões requeridas

| Recurso | Motivo | Como conceder |
|---------|--------|---------------|
| **`CAP_NET_RAW` / root** | Scapy precisa de sockets raw | `sudo setcap cap_net_raw,cap_net_admin+eip $(readlink -f $(which python3))` |
| **nmap SYN scan** (opcional) | Scans `-sS` exigem privilégio | `sudo` ou `setcap` |
| **Leitura de código-fonte alvo** | SAST varre diretório | Permissão de leitura no path |

---

## 7. Análise Módulo a Módulo

### 7.1 `main.py` — Orquestrador CLI
- Usa `argparse` corretamente e suporta modo contínuo (`--continuo`).
- ❌ **Bug de sintaxe potencial em Python < 3.12:** as f-strings `f"Relatório JSON: {caminhos["json"]}"` usam aspas duplas dentro de aspas duplas — só válido a partir do **PEP 701 (Python 3.12)**. Em 3.10/3.11 gera `SyntaxError`.
- ⚠️ Não trata `KeyboardInterrupt` — encerra com traceback ao pressionar `Ctrl+C`.

### 7.2 `modulos/coleta.py` — Reconhecimento
- Bem estruturado, tratamento explícito de `gaierror`.
- ✅ Usa `urlparse` e `User-Agent` próprio.
- ⚠️ Não valida se `alvo` é interno (SSRF interno se exposto como serviço).
- ⚠️ `requests` sem `verify` explícito herda o default (`True`) — OK, mas poderia ser explicitado para auditabilidade.

### 7.3 `modulos/escaneamento.py` — Port scan
- ✅ Fallback socket-only elegante quando `python-nmap` indisponível.
- ⚠️ `-sT` (TCP connect) é ruidoso — em redes reais, considerar `-sS` (SYN) com privilégios.
- ⚠️ Timeout de `0.8s` pode gerar falsos negativos em redes latentes.
- ⚠️ `except Exception` genérico mascarando erros do nmap.

### 7.4 `modulos/analise_codigo.py` — SAST heurístico
- ✅ Cobre 11 categorias relevantes com regex compilada e diretiva `# nosec`.
- ⚠️ Regex de SQLi é frágil (`SELECT .+ FROM .+ + var`) — muitos falsos positivos/negativos.
- ⚠️ Sem análise AST (Bandit/Semgrep seriam mais precisos).
- ⚠️ Não detecta XSS reflexivo/DOM.

### 7.5 `modulos/pentest.py` — DAST leve
- ✅ Cobertura ampla de cabeçalhos de segurança.
- ✅ Testes não-destrutivos.
- ⚠️ Lista fixa de caminhos sensíveis é curta; considerar wordlists (SecLists).
- ⚠️ Probe SSRF é experimental — vide continuação truncada no arquivo original.

### 7.6 `modulos/sca.py` — Dependency scanning
- ✅ Uso correto de `pip-audit --format json`.
- ❌ **`subprocess.run` sem `check=True` nem tratamento de `FileNotFoundError`** — se `pip-audit` não estiver no PATH, silenciosamente retorna vazio.
- ❌ `except Exception` genérico esconde erros de parsing.

### 7.7 `modulos/sniffer.py` — Captura de pacotes
- ❌ Interface **hardcoded** `ens33` — quebra em qualquer host que não seja VMware.
- ❌ Abre arquivo em modo `"a"` a cada pacote — I/O intensivo e sem `flush`/rotação.
- ❌ Sem *rate limiting* nem descarte de tráfego local (potencial DoS de disco).
- ❌ Não fecha o arquivo → *file descriptor leak* em captura longa.
- ⚠️ `store=0` corretamente evita crescimento de RAM.
- ⚠️ Scapy **não está declarado em `requisitos.txt`**.

### 7.8 `modulos/utilidades.py` — Contratos comuns
- ✅ `dataclass Vulnerabilidade` bem projetado.
- ⚠️ `datetime.utcnow()` está **deprecated no Python 3.12+** — usar `datetime.now(timezone.utc)`.

### 7.9 `modulos/gestao.py` — Gestão de vulnerabilidades
- ✅ Implementa categorização, priorização, reavaliação e relatórios.
- ⚠️ Reavaliação por identificador estrito pode marcar como "corrigida" falhas que apenas mudaram de posição no código.

### 7.10 `gestao.py` (raiz) — **Duplicata problemática**
- ❌ Contém `CAMINHO_FRONTEND = "/home/marciosouza/sentinela-dashboard/public/relatorios"` — **path absoluto do desenvolvedor** commitado no repositório.
- ❌ Duplica funcionalidade já presente em `modulos/gestao.py` — risco de divergência.
- ❌ **Vazamento de informação pessoal** (nome de usuário do sistema).

### 7.11 `testes_código/teste_inseguro.py`
- Arquivo com padrões intencionalmente inseguros, usado como *fixture* do SAST.
- ⚠️ Deve ser **explicitamente excluído** de ambientes de produção (adicionar a `.gitattributes`/`.dockerignore`).

---

## 8. Análise Estática de Código (SAST)

Ferramentas recomendadas além da heurística nativa:

| Ferramenta | Objetivo | Comando |
|------------|----------|---------|
| **Bandit** | SAST oficial para Python | `bandit -r modulos/ -ll` |
| **Semgrep** | Regras semânticas cross-language | `semgrep --config auto .` |
| **Ruff** | Linter rápido (inclui regras de segurança S) | `ruff check --select S .` |
| **Pylint** | Qualidade + smells | `pylint modulos/` |
| **Mypy** | Tipagem estática | `mypy modulos/` |
| **ESLint** + `eslint-plugin-security` | Front-end | `npx eslint src/` |

---

## 9. Análise de Composição de Software (SCA)

Dependências declaradas em `requisitos.txt`:

```
requests>=2.31.0        # OK — versão pós CVE-2023-32681
python-nmap>=0.7.1      # OK
packaging>=23.0         # OK
pip-audit>=2.6.0        # OK
colorama>=0.4.6         # OK
fastapi>=0.100.0        # Não é utilizada em nenhum módulo importado (dead dependency)
uvicorn>=0.23.0         # Idem
```

**Observações:**
- ❌ `scapy` é utilizada em `sniffer.py` mas **não está declarada**.
- ❌ `fastapi` e `uvicorn` não são importadas em lugar algum — dependências ociosas aumentam a superfície de ataque.
- ⚠️ Todas usam `>=` (*floating*) — irreprodutível. **Fixar via `pip-compile` (`requirements.txt` + `requirements.lock`)** ou migrar para **Poetry/uv**.
- ⚠️ `requisitos.txt` não é o nome padrão — quebra ferramentas automáticas (`pip-audit`, `Dependabot`, `Renovate`). Recomenda-se `requirements.txt`.

**Front-end (`package.json`):**
- `vite ^8.1.1` e `react ^19.2.7` são versões **futuras/experimentais** — verificar se realmente existem no registry no momento da instalação; podem quebrar reprodutibilidade.
- `oxlint` como linter é aceitável, mas complementar com `eslint-plugin-security` para regras específicas.

---

## 10. Análise Dinâmica (DAST / Pentest Leve)

Além de `pentest.py`, recomenda-se integrar:

- **OWASP ZAP (baseline scan)**: `zap-baseline.py -t https://alvo -r zap.html`
- **Nikto**: `nikto -h https://alvo -Format htm -o nikto.html`
- **testssl.sh**: `testssl.sh --severity HIGH https://alvo`
- **nuclei** (templates comunitários): `nuclei -u https://alvo -severity high,critical`

---

## 11. Análise de Rede e Sniffer

Vide teoria detalhada em [§4.3](#43-sniffers--teoria-funcionamento-e-implicações-legais).

### Recomendações específicas para `modulos/sniffer.py`

```python
# Correções sugeridas
import argparse, signal, sys, os
from scapy.all import sniff, TCP, UDP, IP

LOG_FILE = os.path.join("relatorios", "sniffer_log.txt")

def pacote_callback(pkt):
    if not pkt.haslayer(IP):
        return
    l4 = pkt.getlayer(TCP) or pkt.getlayer(UDP)
    if not l4:
        return
    linha = f"{pkt[IP].src}:{l4.sport} -> {pkt[IP].dst}:{l4.dport} [{l4.name}]\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha)

def iniciar_sniffer(interface: str = None, bpf: str = "tcp or udp"):
    if os.geteuid() != 0:
        raise PermissionError("Requer privilégios de root (CAP_NET_RAW).")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    sniff(iface=interface, filter=bpf, prn=pacote_callback, store=0)
```

Melhorias: interface parametrizada, verificação de privilégio, filtro BPF explícito, portas incluídas no log, tratamento de SIGINT, rotação de logs recomendada via `logrotate`.

---

## 12. Front-end (Dashboard React)

- **Stack:** React 19, Vite 8, TailwindCSS 4, Radix UI, lucide-react.
- **Consumo dos relatórios:** fetch estático em `/relatorios/ultimo_relatorio.json`.
- ⚠️ **Ausência de sanitização** — se o relatório for exibido via `dangerouslySetInnerHTML` (frequente em dashboards de logs), há risco de **XSS armazenado** caso o alvo devolva payloads maliciosos em cabeçalhos/banners.
- ⚠️ Sem **Content Security Policy** no `index.html`.
- ⚠️ Sem **Subresource Integrity (SRI)** nas dependências externas.
- ⚠️ Sem `noopener noreferrer` em links externos (verificar).
- ✅ Uso de Radix UI mitiga vários problemas de acessibilidade e foco.

Recomendações:
- Adicionar `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self';">`.
- Servir o build via Nginx com cabeçalhos `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`.
- Validar o JSON antes de renderizar (Zod/Yup).
- Não expor o dashboard publicamente sem autenticação.

---

## 13. Gestão de Vulnerabilidades e Relatórios

- **Formato JSON estruturado** — excelente para integração (SIEM, DefectDojo, ELK).
- **Formato TXT legível** — bom para revisão manual.
- ⚠️ Sem **assinatura digital** dos relatórios — não garante integridade forense.
- ⚠️ Sem *retention policy* — relatórios acumulam indefinidamente.
- Recomenda-se **export SARIF** para integração com GitHub Security tab e ferramentas empresariais.

---

## 14. Achados de Segurança Consolidados

| # | Severidade | Categoria OWASP | Descrição | Arquivo/Local |
|---|-----------|-----------------|-----------|--------------|
| 1 | 🔴 **CRÍTICA** | A05 | Diretório com nome `[192.168.0.10]` commitado no repositório — expõe topologia interna | Raiz |
| 2 | 🔴 **CRÍTICA** | A05 | Caminho absoluto do desenvolvedor hardcoded (`/home/marciosouza/…`) | `gestao.py` (raiz) |
| 3 | 🟠 **ALTA** | A06 | `scapy` não declarada em `requisitos.txt` | Dependências |
| 4 | 🟠 **ALTA** | A05 | Interface de rede `ens33` hardcoded | `modulos/sniffer.py` |
| 5 | 🟠 **ALTA** | A08 | Duplicação de código (`gestao.py` raiz vs `modulos/gestao.py`) — risco de divergência | Raiz |
| 6 | 🟠 **ALTA** | A09 | Sniffer sem rotação de logs / rate limiting | `modulos/sniffer.py` |
| 7 | 🟡 **MÉDIA** | A06 | Dependências não fixadas (`>=`) | `requisitos.txt` |
| 8 | 🟡 **MÉDIA** | A06 | `fastapi`/`uvicorn` declaradas mas não utilizadas | `requisitos.txt` |
| 9 | 🟡 **MÉDIA** | A05 | Nome de arquivo com acento (`testes_código/`) — quebra em sistemas ASCII-only | Estrutura |
| 10 | 🟡 **MÉDIA** | A05 | `requisitos.txt` foge do padrão `requirements.txt` | Estrutura |
| 11 | 🟡 **MÉDIA** | A03 | Regex SQLi permissiva (falsos positivos/negativos) | `modulos/analise_codigo.py` |
| 12 | 🟡 **MÉDIA** | A09 | `except Exception` genéricos escondendo erros | Vários módulos |
| 13 | 🟢 **BAIXA** | — | `datetime.utcnow()` deprecated (Python 3.12+) | `modulos/utilidades.py` |
| 14 | 🟢 **BAIXA** | — | Ausência de testes automatizados (pytest) | Repositório |
| 15 | 🟢 **BAIXA** | — | Ausência de `.gitignore` robusto (verificar `.venv/`, `relatorios/`, `logs/`) | Raiz |
| 16 | 🟢 **BAIXA** | — | Ausência de CI/CD | Repositório |
| 17 | 🟢 **BAIXA** | — | `App.jsx` na raiz duplica `src/App.jsx` | Raiz |
| 18 | 🟢 **BAIXA** | A05 | Front-end sem CSP nem SRI | `index.html` |
| 19 | 🟢 **BAIXA** | A02 | Front-end distribuível sem autenticação | `src/App.jsx` |

---

## 15. Boas Práticas de Programação — Diagnóstico e Recomendações

### 15.1 Estilo e formatação
- Adotar **Black** + **isort** + **Ruff** com pre-commit hooks.
- Seguir **PEP 8** (linhas ≤ 100 caracteres) e **PEP 257** (docstrings).
- Evitar nomes com acento ou caracteres não-ASCII em arquivos/pastas.

### 15.2 Tipagem
- Ampliar type hints em todas as funções públicas.
- Executar **mypy --strict** no CI.

### 15.3 Tratamento de erros
- **Nunca** usar `except Exception` sem re-raise ou log detalhado.
- Criar exceções customizadas (`SentinelaError`, `SniffingError`, etc.).

### 15.4 Testes
- Adotar **pytest** com estrutura `tests/` (não `testes_código/`).
- Cobertura mínima 70% via `coverage.py`.
- Testes específicos para: parsing de cabeçalhos, regex SAST, deduplicação de vulnerabilidades.

### 15.5 Documentação
- Docstrings em todos os módulos (várias já presentes — parabéns).
- Diagramas de sequência via **mermaid** no README.
- CHANGELOG.md seguindo *Keep a Changelog*.
- SECURITY.md com política de divulgação responsável.

### 15.6 Modularidade
- Remover duplicatas (`gestao.py` raiz, `App.jsx` raiz).
- Considerar transformar em pacote instalável (`pyproject.toml` + `setuptools`/`hatch`/`uv`).

### 15.7 Segurança do próprio código
- Nunca commitar caminhos absolutos, IPs internos, credenciais.
- Adicionar **`gitleaks`** ou **`trufflehog`** ao pre-commit.
- Adicionar `.gitignore` completo:
  ```
  .venv/
  __pycache__/
  *.pyc
  logs/
  relatorios/*.json
  relatorios/*.txt
  node_modules/
  dist/
  .env
  .env.*
  ```

### 15.8 Configuração
- Externalizar constantes (interface de rede, caminhos, timeouts) para `config.yaml`/`.env` com **Pydantic Settings**.

### 15.9 Concorrência
- `threading.Thread(daemon=True)` para sniffer é aceitável, mas considerar `multiprocessing` para isolamento real do sniffer (falhas não derrubam o scanner).

### 15.10 Logging
- Já centralizado em `utilidades.obter_logger` — excelente.
- Adicionar **structlog** para logs estruturados em JSON.
- Enviar logs para SIEM (Wazuh, Graylog, ELK).

---

## 16. Hardening do Ambiente Linux

Recomendações para a **VM Linux** que executa o Sentinela:

1. **Kernel e pacotes:** `unattended-upgrades` habilitado.
2. **Usuário dedicado:** criar `sentinela` sem shell interativo (`/usr/sbin/nologin`) para execução.
3. **Capabilities em vez de root:**
   ```bash
   sudo setcap cap_net_raw,cap_net_admin+eip $(readlink -f $(which python3))
   ```
4. **AppArmor / SELinux:** perfil restrito para o binário.
5. **Firewall:** UFW/nftables — permitir apenas portas necessárias.
6. **Fail2ban:** proteger SSH.
7. **Auditd:** monitorar chamadas críticas (`execve`, `open`, `connect`).
8. **Isolamento:** rodar em **contêiner** (Docker/Podman) ou **VM dedicada** com snapshot antes de cada auditoria.
9. **Segredos:** usar `systemd-creds` ou HashiCorp Vault — nunca `.env` versionado.
10. **NTP:** sincronizado (essencial para relatórios com timestamp confiável).
11. **Swap criptografado** e **LUKS** no disco.
12. **SSH:** apenas por chave, `PermitRootLogin no`, `PasswordAuthentication no`.

### Dockerfile sugerido (exemplo)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nmap libpcap0.8 && \
    rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /usr/sbin/nologin sentinela
WORKDIR /app
COPY requisitos.txt .
RUN pip install --no-cache-dir -r requisitos.txt scapy
COPY . .
USER sentinela
ENTRYPOINT ["python3", "main.py"]
```

---

## 17. DevSecOps e CI/CD Recomendado

**GitHub Actions** sugerida (`.github/workflows/security.yml`):

```yaml
name: security-pipeline
on: [push, pull_request]
jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install bandit ruff pip-audit semgrep
      - run: bandit -r modulos/ -ll -f sarif -o bandit.sarif
      - run: ruff check --output-format=github .
      - run: pip-audit -r requisitos.txt --strict
      - run: semgrep --config auto --sarif -o semgrep.sarif .
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: bandit.sarif }
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gitleaks/gitleaks-action@v2
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm audit --audit-level=high && npm run lint && npm run build
```

Complementos:
- **Dependabot** (`.github/dependabot.yml`) para Python e npm.
- **CodeQL** para análise semântica.
- **Trivy** para imagens Docker.
- **Renovate** como alternativa mais configurável ao Dependabot.

---

## 18. Plano de Remediação Priorizado

| Ordem | Ação | Esforço | Impacto |
|-------|------|---------|---------|
| 1 | Remover diretório `[192.168.0.10]` e reescrever histórico (`git filter-repo`) | Baixo | 🔴 Crítico |
| 2 | Remover caminho absoluto em `gestao.py` (raiz) — parametrizar via env | Baixo | 🔴 Crítico |
| 3 | Adicionar `scapy` ao `requisitos.txt` e renomear para `requirements.txt` | Baixo | 🟠 Alto |
| 4 | Parametrizar interface do sniffer (`--iface`) | Baixo | 🟠 Alto |
| 5 | Consolidar `gestao.py` em um único módulo | Médio | 🟠 Alto |
| 6 | Fixar dependências (`pip-compile` / `uv lock`) | Baixo | 🟡 Médio |
| 7 | Adicionar Bandit + Semgrep no CI | Médio | 🟡 Médio |
| 8 | Substituir `datetime.utcnow()` | Baixo | 🟢 Baixo |
| 9 | Criar suíte pytest com fixtures | Médio | 🟡 Médio |
| 10 | Adicionar CSP e cabeçalhos no dashboard | Baixo | 🟡 Médio |
| 11 | Publicar `SECURITY.md` com política de divulgação | Baixo | 🟢 Baixo |
| 12 | Dockerizar + rodar com usuário não-root | Médio | 🟠 Alto |

---

## 19. Roadmap de Evolução

- **v1.1:** integração SARIF + GitHub Security tab.
- **v1.2:** substituir SAST heurístico por **Semgrep** com regras próprias.
- **v1.3:** integração com **DefectDojo** para gestão longitudinal.
- **v1.4:** módulo de **compliance mapping** (CIS Benchmarks, PCI-DSS).
- **v2.0:** API REST autenticada (FastAPI + OAuth2) — aproveitando dependências já declaradas.
- **v2.1:** agendamento com **APScheduler** ou **cron** + notificações (Slack/Telegram/e-mail).
- **v2.2:** dashboard com autenticação (Auth.js/Clerk) e RBAC.
- **v3.0:** modo distribuído (workers Celery/RQ).

---

## 20. Conformidade Legal (LGPD, ISO 27001, NIST)

- **LGPD (Lei nº 13.709/2018):** logs e capturas de pacotes **podem conter dados pessoais** (IPs são dado pessoal segundo ANPD). Definir base legal (art. 7º), retenção mínima, criptografia em repouso e trânsito, e controle de acesso.
- **ISO/IEC 27001 (Anexo A):** controles relevantes — A.8.8 (gestão de vulnerabilidades técnicas), A.8.15 (logging), A.8.16 (monitoramento), A.8.28 (secure coding).
- **NIST SP 800-53 rev.5:** SI-2 (flaw remediation), SI-4 (system monitoring), RA-5 (vulnerability scanning), AU-* (auditoria).
- **NIST SSDF (SP 800-218):** práticas PW.4 (secure coding), PW.7 (revisão), RV.1 (vulnerability disclosure).

---

## 21. Glossário

| Termo | Definição |
|-------|-----------|
| **BPF** | *Berkeley Packet Filter* — linguagem de filtragem de pacotes no kernel. |
| **DAST** | *Dynamic Application Security Testing* — testes com aplicação em execução. |
| **DoS** | *Denial of Service* — negação de serviço. |
| **HSTS** | *HTTP Strict Transport Security* — força HTTPS. |
| **IDS/IPS** | Sistemas de detecção/prevenção de intrusão. |
| **PCAP** | Formato binário de captura de pacotes. |
| **SAST** | *Static Application Security Testing* — análise sem execução. |
| **SARIF** | *Static Analysis Results Interchange Format* — padrão OASIS para resultados de SAST. |
| **SCA** | *Software Composition Analysis* — análise de dependências. |
| **SSRF** | *Server-Side Request Forgery*. |
| **XSS** | *Cross-Site Scripting*. |
| **CVE** | *Common Vulnerabilities and Exposures* — identificador público de falhas. |
| **CWE** | *Common Weakness Enumeration* — taxonomia de fraquezas. |
| **CVSS** | *Common Vulnerability Scoring System* — sistema de pontuação. |

---

## 22. Referências

- OWASP Foundation — <https://owasp.org>
- OWASP Top 10 (2021) — <https://owasp.org/Top10/>
- OWASP ASVS v4.0.3 — <https://owasp.org/www-project-application-security-verification-standard/>
- OWASP WSTG v4.2 — <https://owasp.org/www-project-web-security-testing-guide/>
- NIST SP 800-115 — <https://csrc.nist.gov/pubs/sp/800/115/final>
- NIST SSDF SP 800-218 — <https://csrc.nist.gov/pubs/sp/800/218/final>
- PTES — <http://www.pentest-standard.org/>
- Scapy Docs — <https://scapy.readthedocs.io/>
- Nmap Reference Guide — <https://nmap.org/book/man.html>
- pip-audit — <https://pypi.org/project/pip-audit/>
- Bandit — <https://bandit.readthedocs.io/>
- Semgrep — <https://semgrep.dev/>
- Wireshark User Guide — <https://www.wireshark.org/docs/>
- LGPD — <http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm>
- Lei nº 12.737/2012 — <http://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12737.htm>
- Lei nº 9.296/1996 — <http://www.planalto.gov.br/ccivil_03/leis/l9296.htm>

---

## 23. Licença

Este projeto é distribuído sob os termos do arquivo `LICENSE` presente no repositório original. Consulte-o para detalhes de uso, redistribuição e responsabilidade.

---

> **Documento gerado como auditoria técnica independente do repositório `Sentinela_Digital`.** Nenhuma varredura ativa foi executada contra ativos de terceiros. Todas as análises foram realizadas sobre o código-fonte publicamente disponível.
>>>>>>> 313309f (Atualização do doc. README.md)
