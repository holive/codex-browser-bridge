# Validação do MVP

Em 15/10/2026, um orquestrador real chamou o MCP, o Codex CLI local controlou um navegador real do Browser Use Cloud e a ferramenta retornou apenas o resultado final após encerrar o navegador.

A tarefa pública de referência abriu `https://example.com`, clicou em “Learn more” e retornou o título **Example Domains** e `https://www.iana.org/help/example-domains`.

- Primeira confirmação da ferramenta genérica: 85,2 segundos.
- Repetição solicitada diretamente pelo usuário ao orquestrador: 39,2 segundos, usando o conector já cadastrado. Resultado correto e encerramento confirmados nos registros locais e pelo usuário.
- Perfil persistente e reabertura de navegadores foram validados na POC. O login em novos sites é preparado manualmente; a validade depende de cada site.

Os testes antigos específicos de sites, contas pessoais, relatórios completos, screenshots e identificadores reais ficaram fora deste repositório. Estes resultados demonstram a conexão e o contrato de delegação; não medem confiabilidade geral, economia de tokens do orquestrador ou prontidão para SaaS.

A versão limpa foi instalada no Mac após autorização. A checagem de contrato com configuração fictícia expôs somente `navegar`. Em seguida, uma chamada MCP local com Codex e Browser Use Cloud reais repetiu a tarefa pública: sucesso em 36,9 segundos e navegador encerrado. Essa última chamada confirma o executor limpo; as execuções anteriores pelo orquestrador confirmam o transporte remoto. Essa checagem ocorreu na instalação do Mac.

## Executor no computador do Grok Bot

Em 15/10/2026, o Maestro chamou `navegar` pelo novo conector `codex-browser-command`, do tipo Command/stdio. O processo MCP e o Codex CLI rodaram no computador do Grok; o navegador continuou no Browser Use Cloud. A chave foi fornecida manualmente pelo usuário no gerenciador de segredos e configurada no runtime privado, sem Git. O mesmo perfil Cloud foi configurado; esta tarefa pública não verifica login.

A primeira execução falhou porque o shell de login redefiniu o PATH (`agent-browser: command not found`); o navegador foi encerrado. A correção informa ao Codex o caminho absoluto do wrapper permitido, preservando a interface e as permissões. Uma repetição da tarefa de referência concluiu com `succeeded`, título **Example Domains**, URL `https://www.iana.org/help/example-domains` e `browser_closed: true`.

- Tempo total: cerca de 18,0 s; preparação 1,8 s; Codex 15,4 s.
- Tokens do Codex: entrada 75.371; cache 59.136; sem cache 16.235; saída 271.
- Resultado entregue pelo MCP após encerrar o navegador; sem observações ou cliques intermediários enviados ao orquestrador. Não foi medida a contagem de tokens do Maestro.
- Código executado: commit `1495004`. A instalação HTTPS do Mac foi preservada como alternativa. Não foi necessária VPS independente nem túnel para esse conector.

Esta validação cobre uma tarefa pública no novo host. Retomada após recuperação da máquina, uso multiusuário e novas sessões autenticadas nesse host não foram testados.

## Encerramento da instalação no Mac

Após a validação no computador do Grok, o usuário solicitou manter apenas esse caminho. Em 15/10/2026, os serviços macOS da ponte e do túnel foram parados e desabilitados no launchd; o conector HTTPS antigo foi retirado do Maestro. `codex-browser-command` permanece ativo. Arquivos e configurações privadas do Mac não foram apagados. Nenhuma nova navegação foi necessária para essa desativação.
