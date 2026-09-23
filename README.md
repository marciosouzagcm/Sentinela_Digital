
# Sentinela Digital

Orquestrador modular de segurança para auditorias autorizadas de aplicações, infraestrutura e identidades digitais. O projeto combina uma API FastAPI, um dashboard React/Vite e uma CLI Python com dois modos de entrada.

> Use todas as funcionalidades somente em ativos, domínios, contas e endereços de e-mail para os quais exista autorização explícita.

## Funcionalidades

### Auditoria web e infraestrutura

O fluxo legado recebe um alvo com `--alvo` e combina coleta DNS/HTTP, port scan com Nmap e fallback por sockets, análise estática de código (SAST), testes HTTP (DAST), análise de dependências com `pip-audit` (SCA), sniffer opcional com Scapy e geração de relatórios JSON/TXT.

### Pipeline OSINT por e-mail

O modo `--email` executa sequencialmente nove adaptadores independentes em `modules/osint/`:

| Módulo | Ferramenta |
| --- | --- |
| `mod_holehe.py` | Holehe |
| `mod_h8mail.py` | h8mail |
| `mod_recon_ng.py` | recon-ng |
| `mod_theharvester.py` | theHarvester |
| `mod_emailharvester.py` | EmailHarvester |
| `mod_sherlock.py` | Sherlock |
| `mod_maltego.py` | Maltego |
| `mod_gitleaks.py` | Gitleaks |
| `mod_ghunt.py` | GHunt |

Cada adaptador usa `subprocess.run` sem `shell=True`, captura `stdout` e `stderr` em UTF-8, grava a saída bruta em `.txt`, trata ausência da ferramenta e timeout e retorna `status`, `output_file` e `data`. Uma falha individual não interrompe as demais etapas.

## Estrutura principal

```text
Sentinela_Digital/
├── main.py                 # CLI dupla e aplicação FastAPI
├── modulos/                # Fluxo web/infraestrutura existente
├── modules/osint/          # Adaptadores OSINT independentes
├── reports/                # JSON mestre, PDF e evidências de todas as buscas
├── public/relatorios/      # Compatibilidade do dashboard legado
├── src/                    # Dashboard React/Vite principal
└── tests/                  # Testes automatizados
```

## Requisitos e instalação

- Python 3.10 ou superior;
- Node.js e npm para o dashboard;
- ferramentas Kali correspondentes ao pipeline OSINT, quando esse modo for usado;
- permissões necessárias para Nmap, Scapy e demais ferramentas do fluxo web.

```bash
git clone https://github.com/marciosouzagcm/Sentinela_Digital.git
cd Sentinela_Digital
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
cd sentinela-dashboard
npm install
```

## Uso da CLI

Os modos são mutuamente exclusivos: o programa exige exatamente `--email` ou um alvo web (`--alvo`, `--url` ou `--target`).

### Auditoria web/infraestrutura

```bash
python main.py --url https://seusite-autorizado.com
python main.py --target https://seusite-autorizado.com --codigo ./src
python main.py --alvo https://seusite-autorizado.com --continuo 30
python main.py --url https://seusite-autorizado.com --sniffer
```

### Pipeline OSINT

```bash
python main.py --email pessoa@example.com
python main.py --wallet 0x0000000000000000000000000000000000000000
python main.py --email pessoa@example.com --wallet-correlacionada 0x0000000000000000000000000000000000000000
```

O modo `--wallet` consulta apenas o adaptador público de blockchain para evitar
enviar um endereço EVM aos scanners de identidade. A correlação por e-mail é
intencionalmente não determinística: domínios Web3 encontrados são sinalizados
para validação autorizada, mas não são tratados como prova de propriedade.

Cada execução gera o mesmo ciclo de entrega para e-mail e web:

```text
reports/
├── evidencias_pessoa_example_com_<timestamp>_<hash>/
│   ├── holehe.txt
│   └── ...
├── relatorio_mestre_pessoa_example_com_<timestamp>_<hash>.json
└── relatorio_mestre_pessoa_example_com_<timestamp>_<hash>.pdf
```

O e-mail é sanitizado no nome do caminho, substituindo `@`, `.`, espaços e caracteres especiais. O relatório mestre é gravado com `indent=4` e `ensure_ascii=False`.

## API FastAPI

Execução local:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`: verificação de disponibilidade;
- `GET /relatorios/ultimo`: retorna o último relatório disponível para o dashboard.

Configure origens adicionais com `CORS_ALLOWED_ORIGINS`:

```bash
CORS_ALLOWED_ORIGINS=https://seu-frontend.vercel.app,http://localhost:5173
```

## Frontend

No diretório `sentinela-dashboard/`:

```bash
npm run dev
npm run build
npm run preview
```

O build é gerado pelo Vite. A pasta `public/relatorios/` deve existir como diretório real no repositório para que o Vercel consiga preparar os arquivos públicos.

## Deploy

### Render

Configure o serviço como Web Service Python:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

O backend deve escutar em `0.0.0.0` e na porta fornecida pelo Render. Não use `python main.py` como comando de produção do serviço web.

### Vercel

Configure o projeto apontando para `sentinela-dashboard/`:

```text
Build Command: npm run build
Output Directory: dist
```

O backend permanece publicado separadamente no Render.

## Relatórios e persistência

- Ambos os fluxos gravam o JSON mestre, o PDF executivo e as evidências em `reports/`.
- O basename é compartilhado pelos artefatos: `relatorio_mestre_<alvo>_<timestamp>_<hash_curto>`.
- O fluxo web inclui coleta DNS/HTTP, port scan, headers e recursos sensíveis como ferramentas do relatório mestre.
- Ferramentas ausentes aparecem com status `unavailable`; o pipeline ainda gera o relatório mestre.
- Quando mais de 50% dos scanners falham, sofrem limitação ou ficam indisponíveis,
  o PDF classifica a postura como `INCOMPLETA / REQUER REEXECUÇÃO`.
- Em ambientes efêmeros de hospedagem, arquivos locais podem ser perdidos após reinicialização ou novo deploy. Use armazenamento externo quando a retenção permanente for necessária.

### Higienização de artefatos

Arquivos temporários de geração e smoke tests não devem ficar na raiz. Relatórios
de execução devem permanecer em `reports/` somente quando forem evidências oficiais
ou fixtures; versões antigas e duplicadas devem ser arquivadas fora do repositório
ou removidas após a confirmação da retenção necessária.

## Testes e validação

```bash
python -m compileall -q main.py modules
pytest -q
python main.py --help
```

### Cobertura dos adaptadores OSINT

Com `pytest-cov` instalado, valide especificamente os adaptadores com:

```bash
pytest --cov=modules/osint --cov-report=term-missing
```

O teste isolado dos adaptadores pode ser executado com `PYTHONPATH=.` em ambientes
que não incluem a raiz do projeto automaticamente:

```bash
PYTHONPATH=. pytest -q tests/test_mod_osint.py
```

## Stack

Python, FastAPI, Uvicorn, React, Vite, Tailwind CSS, Scapy, Nmap, `pip-audit`, Holehe, h8mail, recon-ng, theHarvester, EmailHarvester, Sherlock, Maltego, Gitleaks, GHunt, Render e Vercel.

## Licença

Este projeto está disponível sob a licença MIT. Consulte [LICENSE](LICENSE).
