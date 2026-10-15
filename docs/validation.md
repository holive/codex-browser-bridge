# Validação da POC

Em 15/10/2026, o Maestro chamou `navegar` pelo conector `codex-browser-command`, do tipo Command/stdio. O processo MCP e o Codex CLI rodaram no computador do Grok; o navegador rodou no Browser Use Cloud. A chave foi fornecida pelo usuário em armazenamento privado, sem Git. Somente o resultado final foi entregue depois de encerrar o navegador.

A tarefa abriu `https://example.com`, clicou em “Learn more” e retornou **Example Domains** e `https://www.iana.org/help/example-domains`, com `succeeded` e `browser_closed: true`.

- Tempo total: cerca de 18,0 s; preparação 1,8 s; Codex 15,4 s.
- Tokens Codex: entrada 75.371; cache 59.136; sem cache 16.235; saída 271.
- Código dessa execução: commit `1495004`. O erro inicial de PATH foi corrigido usando o caminho absoluto do wrapper permitido, sem ampliar permissões.

Isso confirma a conexão e essa tarefa pública. Não comprova confiabilidade geral, suporte multiusuário, economia quantitativa de tokens do Maestro ou retomada após recuperação do host. Login manual e persistência de perfil foram exercitados em etapas anteriores da POC; esta chamada pública no host do Grok não verifica login.

Resultados de contas pessoais, capturas, logs e identificadores reais não pertencem ao repositório. Histórico detalhado permanece nos commits e nas evidências privadas, sem fazer parte da instalação atual.

## Instalação e recuperação — simulação isolada

Em 15/10/2026, o novo instalador foi executado em uma pasta privada nova, com espaços no caminho, fora do repositório. Ele criou uma `.venv`, instalou o MCP SDK 2.1.1 e agent-browser 0.39.1 reais e reutilizou um Codex já instalado e autenticado. A etapa de autenticação apenas consultou o estado local. A versão registrada do pacote Codex para instalações novas também foi encontrada no registro npm.

A checagem usou o SDK MCP real para iniciar o lançador, fazer handshake e listar a ferramenta única `navegar`. Uma chamada sem chave/perfil retornou `requires_setup`, sem abrir navegador ou iniciar o modelo. Em seguida, uma reinstalação preservou configuração privada fictícia de chave, perfil, modelo e esforço; um valor fictício recebido por variável de ambiente não foi gravado nem mostrado. Um executável Codex fictício com interface alterada foi corretamente recusado pelo diagnóstico.

A ausência de Node/npm também produziu uma orientação explícita antes da instalação. O teste cobre preparação e diagnóstico no ambiente isolado; não simula a interface de cadastro do Grok, não autentica uma conta nova e não valida a recuperação dos logins Cloud. Não houve novas chamadas ao modelo ou ao Browser Use Cloud. A instalação em uso no Grok não foi modificada nesta rodada.

## Aplicação no computador do Grok — confirmação única

Em 15/10/2026, o commit `0a1f6c0` foi aplicado ao runtime existente no computador do Grok. O instalador foi executado e o conector `codex-browser-command` recarregado. O Maestro confirmou que a chave e o ID do perfil foram preservados, sem expor os valores.

Após o diagnóstico, foi feita uma única chamada `navegar`: `https://example.com` → “Learn more” → **Example Domains**, `https://www.iana.org/help/example-domains`.

- Status: `succeeded`; `browser_closed: true`.
- Tempo do executor: cerca de 24,0 s.
- Tokens Codex: entrada 75.685; cache 59.648; sem cache 16.037; saída 317.

Não foi repetida a bateria anterior. Esta chamada confirma a aplicação da versão nova e a navegação pública pelo conector existente; não verifica login em sites ou recuperação após perda completa do host.
