Atue como um Engenheiro de Cibersegurança e Desenvolvedor Python especialista em ferramentas OSINT.

OBJETIVO:
Refatorar e corrigir o módulo de execução das ferramentas de coleta no projeto Sentinela Digital com base nos diagnósticos de falha recentes.

MUDANÇAS E CORREÇÕES NECESSÁRIAS:

1. GHunt (Google OSINT):
   - Ajustar o script de chamada para verificar se existe o arquivo `cookies.json` configurado antes da execução.
   - Tratar erros de autenticação exibindo uma mensagem amigável no log caso os cookies do Google estejam ausentes ou expirados.

2. recon-ng:
   - Corrigir a sintaxe dos comandos enviados no arquivo resource (.rc).
   - O comando `search contacts <email>` é inválido. Ajuste o fluxo para carregar o workspace, carregar um módulo válido de contatos/profiling (ex: `profiler/templates`) e executar o run de forma adequada.

3. theHarvester / EmailHarvester:
   - Tratar a exceção de motores descontinuados ({'bing', 'google'}).
   - Permitir passar chaves de API (Hunter.io, Shodan) dinamicamente via arquivo de configuração `.env` ou `config.json`.

4. Holehe & Rate Limiting:
   - Adicionar uma opção de timeout e espaçamento entre requisições para mitigar o Rate Limit ([x]) de serviços sensíveis.

5. Parser Generico do Output:
   - Garantir que todos os logs e saídas salvem o JSON padronizado em `relatorio_mestre.json` tratando codificação UTF-8 e evitando falhas de parser em caracteres de terminal ANSI.

Gere o código modificado ou o plano de refatoração para os scripts do Sentinela Digital.