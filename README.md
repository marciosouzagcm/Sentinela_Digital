# Sentinela Digital

**Inteligência de segurança on-chain e off-chain no modelo Pay-per-Query da Solana.**

Sentinela Digital é uma plataforma defensiva para avaliações de ativos autorizados. O usuário conecta uma carteira, solicita uma cobrança Solana Pay e, depois da confirmação on-chain, recebe créditos e inicia a análise vinculada ao alvo da ordem. A camada Solana reúne saldo, tokens SPL/Token-2022, resolução SNS `.sol` e indicadores de listas locais; o resultado alimenta o dashboard e um relatório JSON/PDF.

> Use somente em carteiras, domínios e sistemas para os quais exista autorização. As listas de flags configuráveis são fontes locais preliminares, não uma triagem oficial nem uma conclusão legal.

## Tese do produto

O modelo Pay-per-Query reduz a barreira de entrada para consultas pontuais: cada ordem tem uma referência única, o backend verifica a transação e só então credita o usuário e agenda a varredura solicitada. O relatório combina telemetria pública da Solana com adaptadores OSINT disponíveis, preservando estado parcial quando serviços externos estão indisponíveis.

## Arquitetura e stack

```text
React 19 + Vite + Tailwind 4 + Solana Wallet Adapter
          │ JSON API / checkout Solana Pay
          ▼
FastAPI (main.py) ── autenticação, ordens, confirmação, orquestração
          ├── SQLAlchemy + TiDB Cloud: usuários, pagamentos e créditos
          ├── Solana RPC + httpx.AsyncClient: saldo, SPL/Token-2022, transações
          ├── SNS .sol + listas locais: resolução e sinais de risco
          ├── OSINT off-chain: adaptadores isolados e resultados parciais
          └── ReportLab: PDF executivo ← JSON para dashboard/histórico
```

### Componentes

- **Frontend:** React/Vite, tema escuro Cyberpunk/Web3, Solana Wallet Adapter, checkout QR e visualização de métricas.
- **API:** FastAPI em `main.py`; rotas de pagamento no pacote `app/api/`.
- **Motor on-chain:** `app/services/mod_solana.py`, com requisições RPC não bloqueantes via HTTPX e fallback de endpoints.
- **Relatórios Solana:** `app/services/solana_reporting.py` adapta os dados on-chain ao contrato do dashboard, persiste JSON e gera PDF.
- **Dados:** SQLAlchemy e TiDB Cloud, incluindo ordens e ledger de créditos.
- **Documentos:** relatórios executivos gerados por `pdf_generator.py` (ReportLab).

## Requisitos

- Python 3.10 ou superior;
- Node.js compatível com Vite 8 (Node.js 20.19+ ou 22.12+);
- npm;
- acesso à Solana Mainnet RPC (ou endpoint de provedor próprio);
- TiDB Cloud configurado para persistência de usuários e ordens. O acesso ao banco pode ficar indisponível durante desenvolvimento, mas operações de pagamento exigem persistência correta.

## Instalação local

Na raiz do repositório:

### Backend (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Backend (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend

```bash
npm install
```

## Configuração

Crie `.env` na raiz. Não versione credenciais ou URLs de RPC com chaves privadas.

```env
# Persistência TiDB Cloud
TIDB_HOST=seu-gateway.tidbcloud.com
TIDB_PORT=4000
TIDB_USER=seu-usuario
TIDB_PASSWORD=sua-senha
TIDB_DATABASE=sentinela

# Pagamentos: carteira da tesouraria Mainnet
SOLANA_TREASURY_WALLET=sua-chave-publica-solana
SOLANA_PAY_DEFAULT_AMOUNT_SOL=0.05

# RPC failover: URLs em ordem de preferência, separadas por vírgula
SOLANA_ENV=mainnet-beta
SOLANA_RPC_URLS=https://seu-rpc-mainnet,https://api.mainnet-beta.solana.com
SOLANA_RPC_TIMEOUT_SECONDS=12

# Enriquecimento opcional; objetos JSON mapeiam domínio/endereço a metadados
SOLANA_SNS_STATIC_MAP_JSON={}
SOLANA_SNS_RESOLVER_URL=https://sns-api.bonfida.com/resolve
SOLANA_SNS_TIMEOUT_SECONDS=10
SOLANA_FLAGGED_ADDRESSES_JSON={}
SOLANA_SANCTIONED_ADDRESSES_JSON={}
SOLANA_TOKEN_METADATA_JSON={}

# SIWS: configure o domínio público e um segredo JWT aleatório de pelo menos 32 caracteres
SIWS_DOMAIN=sentinela.example
SIWS_URI=https://sentinela.example/
JWT_SECRET_KEY=<segredo-aleatorio-com-no-minimo-32-caracteres>

# Frontend Vite
VITE_API_URL=http://127.0.0.1:8000
VITE_SOLANA_CLUSTER=mainnet-beta
```

Para listas de endereços, os valores JSON podem ser um array de chaves ou um objeto `{"pubkey": {"label": "...", "risk_level": "high"}}`. A configuração estática deve ser mantida atualizada e revisada pelo operador.

## Execução

Abra terminais separados, ambos na raiz do repositório.

### API

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Documentação interativa: `http://127.0.0.1:8000/docs`. O comando `python main.py` também inicia a API.

### Dashboard

```bash
npm run dev
```

O Vite disponibiliza a aplicação em `http://127.0.0.1:5173`. Para conferir compilação e lint:

```bash
npm run lint
npm run build
```

## API principal

Todos os corpos e respostas são JSON, salvo a URL do checkout `solana:`.

### Saúde e relatório

- `GET /health` — disponibilidade da API.
- `GET /relatorios/ultimo` — relatório mais recente no formato usado pelo dashboard: `alvo`, `gerado_em`, `metricas`, `categorias`, `solana`, `solana_scan` e, após geração, caminhos de relatório/PDF.

### Carteira

- `GET /api/v1/auth/nonce?public_key=<pubkey>` — cria um desafio SIWS de uso único, vinculado à chave e válido por cinco minutos. A resposta inclui a mensagem exata que deve ser assinada.
- `POST /api/v1/auth/verify-wallet` — valida assinatura Ed25519 sobre a mensagem SIWS e registra/autentica a carteira. Corpo: `{"public_key":"<pubkey>","signature":"<base58-ou-hex>","message":"<mensagem-exata>","nonce":"<nonce>"}`. Sucesso retorna um bearer JWT com validade de 15 minutos.
- `GET /api/v1/users` — lista registros de usuários (rota administrativa; proteger antes de expor publicamente).

O dashboard solicita a assinatura somente depois do clique em **Autenticar SIWS**. O JWT fica em memória no cliente. Gere `JWT_SECRET_KEY` aleatoriamente, mantenha-o fora do controle de versão e não use o placeholder do exemplo. Nonces são mantidos em memória pelo processo FastAPI; para múltiplos workers/instâncias, substitua o armazenamento local por Redis ou armazenamento compartilhado atômico. Em produção, configure `SIWS_DOMAIN`, `SIWS_URI` e `JWT_SECRET_KEY` com valores próprios e não reutilize chaves entre ambientes.

### Solana Pay e varredura

- `POST /api/v1/payments/create-order` — cria ordem e QR payload. Corpo: `wallet_address`, `target` opcional (carteira Solana, domínio `.sol`, e-mail, domínio/URL web; texto não vazio até 255 caracteres), `amount_sol`, `scans_to_credit` e `note`.
- `POST /api/v1/payments/verify-payment` — recebe `reference`, opcionalmente `wallet_address` e `txSignature`; verifica o status on-chain no cluster configurado e confere pagador, destinatário, valor e referência contra a ordem persistida.
- `POST /api/v1/payments/verify-tx` — aceita a mesma referência da ordem e `txSignature` em camelCase para consultar diretamente uma assinatura. Só uma transação confirmada e correspondente libera créditos e agenda a análise.
- `POST /api/v1/solana/scan` — executa/reexecuta a análise para uma ordem já verificada. Corpo: `{"reference":"<reference da ordem paga>"}`; não recebe alvo livre.

Exemplo do corpo de criação de ordem:

```json
{
  "wallet_address": "<pubkey do pagador>",
  "target": "exemplo.sol",
  "amount_sol": 0.05,
  "scans_to_credit": 1,
  "note": "Auditoria autorizada"
}
```

### Métricas do relatório

O campo `metricas` usa `TOTAL`, `CRITICA`, `ALTA`, `MEDIA` e `BAIXA`. `TOTAL` corresponde ao número de achados classificados, não à soma de saldo e tokens. Dados de inventário e estado RPC ficam no objeto `solana`; só flags/regras de risco classificadas entram nas categorias de achados.

## Fluxo de ponta a ponta

Configure `SOLANA_ENV` e `VITE_SOLANA_CLUSTER` com o mesmo valor (`mainnet-beta` ou `devnet`). O botão de demonstração do checkout simula somente o estado da interface; não confirma uma transação, não credita o banco e não comprova pagamento real.

1. Conectar carteira no dashboard e informar alvo autorizado.
2. Criar ordem; referência e alvo são persistidos no backend e o checkout mostra o QR Solana Pay.
3. O dashboard consulta a verificação; o backend confirma a transação e confere os dados contra a ordem persistida.
4. Após confirmação, o ledger recebe os créditos uma única vez e a análise é executada em background.
5. O motor consulta a RPC, resolve `.sol`, captura flags e mantém resultados parciais se um serviço falhar.
6. O relatório JSON atualiza `GET /relatorios/ultimo`; um PDF executivo é gerado quando o ReportLab conclui sem erro.

## Testes

Os testes do serviço Solana usam mocks e não necessitam acessar a Mainnet:

```bash
python -m unittest discover -s tests -p "test_solana_service.py" -v
python -m unittest discover -s tests -p "test_auth_siws.py" -v
```

Para executar a suíte pytest completa, instale também `pytest` no ambiente e rode `python -m pytest`.

## Roadmap do hackathon

- **Dias 1–3:** motor Solana, SNS e integração do core;
- **Dias 4–6:** checkout, referências e verificação de pagamento;
- **Dias 7–9:** dashboard, JSON/PDF e feedback de execução;
- **Dias 10–12:** testes de fluxo completo, pitch e vídeo demonstrativo.

## Segurança e limitações

- Consultar somente alvos com autorização explícita; saldos, tokens e assinaturas são dados públicos on-chain.
- Manter segredos no backend; nunca incluir chaves de RPC ou banco no bundle Vite.
- A verificação do pagamento precisa usar destinatário, valor, carteira e referência persistidos pelo servidor; valores recebidos do navegador não substituem os da ordem.
- RPC público pode sofrer rate limit e retornar dados incompletos. O relatório deve identificar estado parcial e nunca inferir “sem risco” por indisponibilidade.
- Flags estáticas/mock são indicadores preliminares e não equivalem a uma lista oficial de sanções.
- Proteja rotas de administração e configure CORS para os domínios necessários antes de produção.


