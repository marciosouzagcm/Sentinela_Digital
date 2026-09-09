Atue como um Engenheiro de Software Python Sênior especialista em geração de relatórios corporativos executivos.

OBJETIVO:
Criar o módulo Python `pdf_generator.py` para ler dinamicamente qualquer arquivo de relatório JSON gerado pelo Sentinela Digital e compilar um PDF executivo de alto impacto.

USO DA LINHA DE COMANDO (CLI):
O script deve ser executado aceitando argumentos:
`python pdf_generator.py <caminho_do_json> <caminho_do_pdf_saida>`

REQUISITOS TÉCNICOS E DESIGN:
1. Leitura Dinâmica do JSON:
   - Ler os campos de `email`, `gerado_em`, `ferramentas` e seus respectivos status[cite: 6, 7].
   - Filtrar falsos positivos conhecidos (ex: resultados genéricos do Sherlock ao pesquisar e-mails completos)[cite: 6, 7].
   - Tratar status `success`, `error` e `skipped` aplicando cores correspondentes nas tabelas[cite: 6, 7].

2. Layout & Estilização (ReportLab):
   - Paleta Cyber/Executive: Dark Navy (#0B192C), Cyan Accent (#00D2FF), Red/Green/Orange para status.
   - Background / Marca d'Água: Utilizar 'IMG-20260909-WA6745.jpg' com baixa opacidade (0.05 a 0.08) no canvas de fundo de todas as páginas.
   - Cabeçalho / Rodapé: Adicionar numeração "Página X de Y", carimbo de confidencialidade e nome do sistema via `NumberedCanvas`.

3. Seções do Documento:
   - Cabeçalho Executivo: Alvo auditado, data/hora da telemetria e analista responsável.
   - Matriz de Ferramentas OSINT: Tabela com o status de cada scanner executado[cite: 6, 7].
   - Destaques de Segurança: Lista de serviços/contas confirmadas (ex: Holehe `[+]`)[cite: 6, 7].
   - Plano de Ação e Recomendações de Higiene Digital.

Forneça o código Python completo, modularizado, com tratamento de exceções e suporte nativo a UTF-8.