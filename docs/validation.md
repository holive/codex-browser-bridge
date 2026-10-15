# Validação do MVP

Em 15/10/2026, um orquestrador real chamou o MCP, o Codex CLI local controlou um navegador real do Browser Use Cloud e a ferramenta retornou apenas o resultado final após encerrar o navegador.

A tarefa pública de referência abriu `https://example.com`, clicou em “Learn more” e retornou o título **Example Domains** e `https://www.iana.org/help/example-domains`.

- Primeira confirmação da ferramenta genérica: 85,2 segundos.
- Repetição solicitada diretamente pelo usuário ao orquestrador: 39,2 segundos, usando o conector já cadastrado. Resultado correto e encerramento confirmados nos registros locais e pelo usuário.
- Perfil persistente e reabertura de navegadores foram validados na POC. O login em novos sites é preparado manualmente; a validade depende de cada site.

Os testes antigos específicos de sites, contas pessoais, relatórios completos, screenshots e identificadores reais ficaram fora deste repositório. Estes resultados demonstram a conexão e o contrato de delegação; não medem confiabilidade geral, economia de tokens do orquestrador ou prontidão para SaaS.

A versão limpa deste repositório foi extraída da implementação validada. Ela não substituiu a instalação ativa; os tempos acima se referem à POC. A checagem local da extração carrega o MCP com configuração fictícia e confere apenas o contrato da ferramenta, sem abrir um navegador ou chamar o Codex.
