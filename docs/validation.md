# Validação do MVP

Em 15/10/2026, um orquestrador real chamou o MCP, o Codex CLI local controlou um navegador real do Browser Use Cloud e a ferramenta retornou apenas o resultado final após encerrar o navegador.

A tarefa pública de referência abriu `https://example.com`, clicou em “Learn more” e retornou o título **Example Domains** e `https://www.iana.org/help/example-domains`.

- Primeira confirmação da ferramenta genérica: 85,2 segundos.
- Repetição solicitada diretamente pelo usuário ao orquestrador: 39,2 segundos, usando o conector já cadastrado. Resultado correto e encerramento confirmados nos registros locais e pelo usuário.
- Perfil persistente e reabertura de navegadores foram validados na POC. O login em novos sites é preparado manualmente; a validade depende de cada site.

Os testes antigos específicos de sites, contas pessoais, relatórios completos, screenshots e identificadores reais ficaram fora deste repositório. Estes resultados demonstram a conexão e o contrato de delegação; não medem confiabilidade geral, economia de tokens do orquestrador ou prontidão para SaaS.

A versão limpa foi instalada no Mac após autorização. A checagem de contrato com configuração fictícia expôs somente `navegar`. Em seguida, uma chamada MCP local com Codex e Browser Use Cloud reais repetiu a tarefa pública: sucesso em 36,9 segundos e navegador encerrado. Essa última chamada confirma o executor limpo; as execuções anteriores pelo orquestrador confirmam o transporte remoto. Nenhuma migração para outro host foi executada.
