Atue como Engenheiro de Cibersegurança e Desenvolvedor Python responsável pelos adaptadores de coleta do Sentinela Digital.

## Contexto e objetivo

O backend é uma API FastAPI iniciada em `main.py`. Os adaptadores off-chain são executados isoladamente para que uma falha individual não interrompa o relatório. O serviço `app/services/mod_solana.py` complementa essas fontes com dados públicos on-chain usando `httpx.AsyncClient` e RPC JSON-RPC da Solana. Preserve os contratos atuais e evite substituir silenciosamente funcionalidades existentes.

## Regras para scripts e adaptadores OSINT

1. **GHunt:** verificar o caminho configurado para `cookies.json` antes da execução; registrar aviso claro se estiver ausente e classificar falhas de autenticação/cookies expirados sem expor conteúdo de cookie.
2. **recon-ng:** gerar arquivos resource (.rc) apenas com comandos aceitos pela versão instalada. Não usar `search contacts <email>`; selecionar workspace, módulo disponível e opções documentadas, tratando módulo inexistente como falha isolada.
3. **theHarvester / EmailHarvester:** capturar engines indisponíveis ou removidas (incluindo `bing` e `google`) e reportar cobertura parcial. Ler chaves Hunter.io, Shodan e outras exclusivamente de `.env`/configuração de servidor; nunca imprimir ou serializar segredos.
4. **Holehe e serviços sujeitos a rate limit:** permitir timeout e intervalo configuráveis. Registrar respostas limitadas como `rate_limited`/aviso, sem transformar ausência de resposta em achado negativo.
5. **Saída comum:** emitir JSON UTF-8 estruturado com `status`, `output_file` e `data`; remover códigos ANSI antes de persistir. Capturar exceções por adaptador e preservar os resultados das demais ferramentas.

## Serviço Solana (`app/services/mod_solana.py`)

- Usar `httpx.AsyncClient` assíncrono com timeout configurável por `SOLANA_RPC_TIMEOUT_SECONDS` e fallback ordenado em `SOLANA_RPC_URLS`/`SOLANA_RPC_URL`; o padrão é o RPC público Mainnet.
- Consultar saldo por `getBalance`, contas SPL e Token-2022 por `getTokenAccountsByOwner` com `jsonParsed`, resolver `.sol` via `SOLANA_SNS_STATIC_MAP_JSON` ou resolvedor configurado e verificar listas locais `SOLANA_FLAGGED_ADDRESSES_JSON` / `SOLANA_SANCTIONED_ADDRESSES_JSON`.
- Capturar erros de HTTP, timeout, JSON-RPC e resposta malformada. A indisponibilidade do nó deve produzir dados parciais e estado `partial`/`warning`, nunca interromper a API nem ser descrita como saldo zero confirmado ou carteira limpa.
- Não registrar URL RPC completa se ela puder conter API key. Não afirmar que listas mock/estáticas equivalem a uma decisão legal ou a uma triagem oficial de sanções.
- Mantenha a orquestração de chamada assíncrona fora de adaptadores síncronos; se o pipeline legado precisar de wrapper síncrono, não o invoque dentro de um event loop ativo.

## Integração e regras de varredura

- A criação de ordem Solana Pay persiste referência, carteira, alvo, valor, destinatário e créditos no servidor. A verificação usa os dados persistidos, valida a transação confirmada e só então credita; chamadas repetidas devem ser idempotentes.
- A varredura on-chain vinculada à ordem só pode ser agendada após confirmação. O retry `POST /api/v1/solana/scan` recebe referência de uma ordem `verified`; não aceitar alvo arbitrário sem pagamento.
- Conservar no relatório JSON o contrato do dashboard: `alvo`, `gerado_em`, `metricas` (`TOTAL`, `CRITICA`, `ALTA`, `MEDIA`, `BAIXA`) e `categorias`. Incluir dados de carteira, saldo, tokens, SNS, flags e estado parcial em campos estruturados, além da seção Solana do PDF.
- Não contar dados de inventário (saldo/tokens) como vulnerabilidade sem regra de risco explícita. As contagens devem refletir achados de risco classificados e os mesmos achados precisam estar nas categorias do relatório.

## Validação

Adicionar/ajustar testes sem chamadas reais à Mainnet: simular RPC válido, erro JSON-RPC, timeout, fallback de endpoint, falha do resolvedor, estado parcial, classificação de flags, ausência de crédito antes de confirmação e idempotência pós-confirmação. Executar testes e checagem de sintaxe antes de concluir.