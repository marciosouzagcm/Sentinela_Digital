Atue como Engenheiro de Software Python Sênior responsável pelo gerador executivo `pdf_generator.py` do Sentinela Digital.

## Objetivo

Ler os relatórios JSON do pipeline (OSINT legado e análise Solana) e produzir PDF executivo em ReportLab sem descartar dados estruturados, estados parciais ou a proveniência dos achados.

## Entrada e execução

Manter o uso CLI compatível:

`python pdf_generator.py <caminho_do_json> <caminho_do_pdf_saida>`

O documento de entrada pode conter `alvo`, `email`, `wallet`, `gerado_em`, `metricas`, `categorias`, `solana`, `solana_scan` e `ferramentas`. A ferramenta Solana segue o formato `ferramentas.solana = {status, output_file, data: {result: {...}}}`. Tratar campos ausentes e relatórios antigos sem falhar.

## Conteúdo obrigatório

1. **Resumo executivo:** alvo auditado, data UTC, analista, classificação/limitação de cobertura e total de achados.
2. **Matriz de ferramentas:** status `success`, `warning`, `partial`, `error`, `timeout`, `rate_limited`, `unavailable` ou `skipped`, com observações sem segredos.
3. **Achados off-chain:** achados confirmados e evidências OSINT relevantes, com filtros de falso positivo já usados pelos parsers (por exemplo, resultados genéricos do Sherlock).
4. **Inteligência On-Chain Solana:** incluir seção dedicada com:
   - alvo original, tipo (PubKey ou `.sol`) e endereço resolvido;
   - saldo SOL, usando `n/d` se desconhecido (não exibir zero como confirmado quando RPC falhou);
   - tokens SPL/Token-2022 com mint, símbolo conhecido quando disponível, conta e quantidade;
   - estado/resolução SNS `.sol`;
   - flags/listas locais e nível/score de risco, identificando explicitamente a fonte como configuração local/mock;
   - número de assinaturas recentes quando o dado estiver disponível;
   - status parcial e resumo de erros de cobertura, sem expor URL privada do RPC, API key ou detalhes sensíveis.
5. **Métricas:** manter no JSON/dashboard `TOTAL`, `CRITICA`, `ALTA`, `MEDIA`, `BAIXA`. `TOTAL` conta achados classificados; saldo e tokens são inventário e não aumentam a contagem de vulnerabilidades. Usar acentos apenas para apresentação; preservar os nomes de chave canônicos no JSON.
6. **Plano de ação:** recomendações proporcionais a achados confirmados e à cobertura. Não converter falha/timeout de RPC em conclusão de baixo risco.

## Apresentação e segurança

- ReportLab com paleta executiva Dark Navy `#0B192C`, ciano `#00D2FF` e cores consistentes por severidade/status.
- UTF-8, tratamento de exceções por seção e escape de valores inseridos em Paragraph/HTML.
- Marca d'água opcional `IMG-20260909-WA6745.jpg`, cabeçalho/rodapé, confidencialidade e paginação “Página X de Y”.
- Não apresentar lista local como screening oficial de sanções. Não imprimir segredos, credenciais, cookies ou URLs de RPC que contenham chaves.
- Manter compatibilidade com JSON legado que não contenha dados Solana; a seção on-chain deve ser omitida nesses documentos.

## Validação

Criar testes com JSON contendo carteira sinalizada, domínio `.sol`, saldo desconhecido, vários tokens, relatório parcial, além de relatório legado sem `solana`. Validar existência e conteúdo básico do PDF e confirmar que ausência de dados on-chain não interrompe a geração.