Documento de Arquitetura e Estratégia TecnológicaProjeto: Sentinela Digital — Plataforma de Cyber Intelligence & OSINT On-Chain/Off-ChainEvento: Hackathon SolanaModelo de Negócio: Pay-Per-Query (Micropagamentos via Solana Pay e Créditos)Data de Emissão: 24 de Setembro de 20261. Status do Projeto & Matriz de Auditoria da Junta TécnicaDiagnóstico de Conclusão AtualInfraestrutura & Persistência (TiDB Cloud): 100% Concluído. Conexão estabelecida via SQLAlchemy/PyMySQL, resolução de restrições UNIQUE concluída, sincronização de schemas ativa e endpoint /api/v1/users validado.Autenticação & Registro: 100% Concluído. Endpoint /api/v1/auth/verify-wallet operacional. Leitura e criação de usuários com chave pública Solana testados com sucesso via cURL.Frontend Base: 70% Concluído. Conectividade com Solana Wallet Adapter funcional no React/Vite.Mapeamento de Lacunas (Gap Analysis) para o HackathonComponente / MóduloStatus AtualRequisito de Entrega do HackathonCriticidadeSolana Pay / GatewayNão implementadoCobrança Pay-Per-Query on-chain com validação instantânea via referência única (reference key).CríticaMotor Web3 OSINT (mod_solana.py)Não integradoLeitura de tokens SPL, resolução de domínios .sol e verificação de sanções/labels.AltaGeração de PDF (ReportLab)ParcialInclusão dos dados de inteligência Web3 no relatório final consolidado.MédiaMotor Off-Chain & Cross-DataParcialIngestão de alvos (E-mail, Domínio, Carteira) e busca em bases de vazamentos.AltaSegurança & Nonce (SIWS)ParcialAssinatura criptográfica ed25519 com Nonce temporário no login (evitar replay attacks).Alta2. Visão Integrada dos Agentes Técnicos1. Especialista em Cibersegurança da InformaçãoProteção de Segredos: Nenhuma API Key de scanners OSINT, Webhooks ou URIs privadas de RPC Solana devem residir no cliente (React/Vite). Toda consulta deve ser intermediada por endpoints autenticados no FastAPI.Autenticação SIWS Robusta: Implementar verificação estrita de Sign-In With Solana (SIWS). O backend deve emitir um nonce único com tempo de expiração no TiDB/Redis. A assinatura ed25519 do nonce enviada pela carteira Phantom deve ser validada no Python antes de autorizar a consulta ou emitir o JWT.Isolamento de Dados: Os relatórios PDF gerados e dados salvos no TiDB devem ser protegidos com controle de acesso baseado em função (RBAC), permitindo acesso apenas ao proprietário da carteira que pagou pela consulta.2. Gerente / Arquiteto de ProjetosFluxo de Micropagamento (Pay-Per-Query): O pipeline do usuário deve operar em 3 etapas sem fricção:O usuário submete o alvo (E-mail, Domínio ou Carteira) no Dashboard.A API gera uma requisição de pagamento Solana Pay (URL solana: + reference de 32 bytes).O backend escuta a confirmação da transação no bloco Solana (~400 ms) e dispara os adaptadores de varredura no ThreadPoolExecutor.Escopo de Execução para o Hackathon: Priorizar a jornada ponta a ponta: Conexão de Carteira $\rightarrow$ Pagamento via Solana Pay $\rightarrow$ Varredura On-Chain/Off-Chain $\rightarrow$ Exibição do Dashboard / Download do PDF.3. Arquiteto de Infraestrutura e DevOpsResiliência de RPC: Redes públicas de RPC da Solana podem sofrer rate-limiting durante eventos de pico. Implementar uma lista de fallbacks de nós RPC no database.py / config.py (Alchemy, QuickNode, Helius ou RPC público padrão).Processamento Assíncrono: As chamadas para os scanners OSINT off-chain e pesquisas on-chain não podem bloquear a thread principal do FastAPI. Utilizar chamadas assíncronas (httpx) ou ThreadPoolExecutor.4. Engenheiro de Compliance e Regulatório (LegalTech)Disclaimer OSINT Defensivo: A plataforma deve apresentar Termos de Uso claros na Landing Page e na primeira página do PDF, especificando que a ferramenta executa checagens defensivas baseadas em dados públicos disponíveis.Privacidade de Dados (LGPD/GDPR): Suporte ao mascaramento de dados sensíveis e opção para solicitar expurgo de histórico de varreduras na tabela users do TiDB (Right to be Forgotten).5. Designer de Experiência do Usuário (UX/UI)Estética Cyberpunk / Web3 Premium: Interface gráfica com modo escuro nativo (Dark Mode), utilizando a paleta oficial da Solana (Roxo #9945FF, Verde #14F195) com tipografia técnica (Monospace para endereços de carteira e hashes).Feedback de Transação em Tempo Real: Tela de checkout com exibição do QR Code Solana Pay, indicador de status "Aguardando confirmação no bloco..." e barra de progresso durante a montagem do relatório OSINT.3. Arquitetura da Solução e Fluxo de Dados[ Usuário / React Dashboard ]
        │
        ├─ 1. Solicita Varredura (Alvo: Email/Domain/Wallet)
        ▼
[ Backend FastAPI ] ─── 2. Cria Ordem & Reference Key ───► [ Solana Pay Protocol ]
        │                                                           │
        │ ◄── 3. Valida Confirmação On-Chain (RPC Listener) ───────┘
        │
        ├─ 4. Dispara Módulos de Análise em Paralelo:
        │       ├── OSINT Off-Chain (Vazamentos/IP/DNS)
        │       └── Web3 On-Chain Engine (Tokens SPL/SNS .sol/Cluster/Mixers)
        │
        ├─ 5. Persiste Consulta e Atualiza Créditos no [ TiDB Cloud ]
        │
        └─ 6. Retorna Dados em Tempo Real & Gera PDF (ReportLab)

4. Plano de Implementação (Prompt para GitHub Copilot)
Copie e cole o prompt abaixo no GitHub Copilot Chat no VS Code para executar a implementação dos módulos restantes:

Markdown
Atue como um Engenheiro de Software Principal Full-Stack especializando em FastAPI, Solana e React. Precisamos finalizar o projeto "Sentinela Digital" para o Hackathon Solana.

Execute as seguintes tarefas no repositório:

1. MOTOR WEB3 OSINT (`app/services/mod_solana.py`):
   - Crie o serviço `mod_solana.py` para realizar varreduras on-chain na Solana.
   - Implemente a verificação de saldo de SOL e tokens SPL da carteira alvo.
   - Adicione suporte à resolução de nomes de domínio `.sol` (Solana Name Service).
   - Implemente checagem básica contra listas de endereços conhecidos/sinalizados (labels/sanções).

2. PAGAMENTO SOLANA PAY (`app/api/v1/endpoints/payment.py`):
   - Crie o endpoint POST `/api/v1/payments/create-order` que gera um endereço de cobrança ou URL do Solana Pay contendo um `reference` (PublicKey única).
   - Crie o endpoint POST `/api/v1/payments/verify-payment` que consulta o nó RPC da Solana e confirma se a transação com a referência específica foi validada no bloco.
   - Atualize os créditos ou libere a execução da varredura na tabela `users` do TiDB Cloud.

3. ATUALIZAÇÃO DOS MODELOS E ROTAS:
   - Garanta que o modelo `User` em `app/db/models.py` suporte o registro de requisições e histórico de créditos.
   - Garanta que todos os modelos utilizem nomes de colunas compatíveis com o TiDB Cloud sem conflitos de palavras reservadas.

4. ATUALIZAÇÃO DA DOCUMENTAÇÃO (`README.md`):
   - Atualize o arquivo `README.md` do projeto contendo:
     - Visão Geral do Sentinela Digital (Solução Pay-per-Query na Solana).
     - Arquitetura da Solução (FastAPI, React/Vite, Solana Pay, TiDB Cloud, ReportLab).
     - Guia de Instalação e Configuração (.env, dependências Python e Node).
     - Instruções de Uso da API e endpoints principais.
     - Roadmap do Hackathon.
5. Roadmap de Execução do Hackathon
[Dias 1-3] Core & Solana Engine ──► [Dias 4-6] Solana Pay Gateway ──► [Dias 7-9] UI/UX & PDF Sync ──► [Dias 10-12] Pitch & Demo Video
Fase 1: Alinhamento de Core & Módulo Solana (Dias 1 a 3)

Integração do serviço mod_solana.py ao pipeline do FastAPI.

Resolução de domínios .sol e leitura de saldos de tokens SPL.

Fase 2: Integração do Solana Pay (Dias 4 a 6)

Implementação da API de cobrança Pay-per-Query (create-order e verify-payment).

Listener RPC para liberação automática da varredura após confirmação do bloco.

Fase 3: Refinamento do PDF & Interface Frontend (Dias 7 a 9)

Inclusão dos dados de inteligência Web3 nas seções do relatório ReportLab.

Tela de checkout e barra de progresso em tempo real no dashboard React.

Fase 4: Testes, Pitch & Vídeo Demo (Dias 10 a 12)

Auditoria da suíte de testes com pytest.

Gravação do vídeo demonstrativo (3 minutos) com foco no problema, solução, pagamento on-chain instantâneo e entrega do relatório.
