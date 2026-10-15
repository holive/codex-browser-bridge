# Uso da ponte

Envie ao Maestro uma URL completa, uma tarefa concreta e peça apenas o resultado final. Não envie placeholders, senhas, códigos ou tokens.

> Maestro, use codex-browser-command para abrir https://example.com, clicar em “Learn more” e retornar o título e a URL da página de destino. Aguarde e entregue apenas o resultado final.

> Maestro, use a ponte para abrir https://news.ycombinator.com/ e retornar os títulos e links das três primeiras notícias. Aguarde e entregue apenas o resultado final.

Peça ao Maestro que use `navegar(tarefa, url)` do conector **`codex-browser-command`** (Command/stdio). Esse é o único conector ativo desta ponte.

As instruções específicas de outros sites podem ficar nas skills/configuração do orquestrador e ser enviadas na tarefa. Não precisam de uma ferramenta MCP por site.

## Login em outro site

A ferramenta MCP não prepara uma janela de login nem recebe credenciais. Essa preparação é manual e separada da navegação automática:

1. Peça ao operador/Codex: “Abra https://github.com/login no navegador Cloud com o mesmo perfil da ponte para eu fazer login manualmente.”
2. O operador prepara a sessão usando o `profile_id` da configuração privada e fornece a janela remota ao usuário. Faça login e MFA nessa janela.
3. Avise que terminou. O operador encerra a sessão de preparação para salvar o perfil; só depois envie outra tarefa ao Maestro.
4. O executor reutiliza esse perfil nas próximas execuções. Se a sessão expirar, repita a preparação.

Autenticar no navegador comum do computador não prepara o perfil remoto da ponte. Retorno `requires_auth` indica necessidade de login manual; a execução termina e fecha seu navegador remoto.

## Erros e escopo

- `busy`: outra tarefa/processo usa o runtime, ou uma limpeza anterior ficou pendente. Aguarde uma tarefa ativa; se houver `cleanup_pending`, siga o procedimento abaixo.
- `requires_setup`: chave ou perfil não chegou ao processo MCP; configure-os no ambiente privado, fora da tarefa.
- `requires_auth`: prepare ou renove o login fora do MCP.
- `out_of_scope`: pedido exige uma alteração que este MVP não permite.
- `failed` / `timed_out`: leia o erro e decida se quer tentar novamente. Não há repetição automática.

O computador do Grok e o acesso ao Codex e Browser Use precisam estar disponíveis para o conector Command. Use uma conta/perfil por instalação neste MVP; múltiplos usuários, isolamento de contas e publicação de sites não foram implementados.

## Encerramento incerto

`cleanup_pending: true` significa que a ponte não confirmou o encerramento. A resposta não deve ser tratada como sucesso nem repetida automaticamente. O runtime fica bloqueado mesmo após reiniciar o MCP.

O operador deve ler `active-run.json` e o `lifecycle.json` da execução no armazenamento privado, verificar se ainda há executor/modelo ativo e encerrar a sessão identificada no Cloud. Se a criação não devolveu um ID, confira o painel Cloud e os horários; não adivinhe nem encerre sessões alheias. Só depois de confirmar ausência de processos da tarefa e de navegador ativo deve arquivar o marcador `active-run.json` para liberar o runtime. Guarde os registros para diagnóstico. Não publique IDs, URLs de controle ou valores da configuração.

A trava é por pasta de runtime, no mesmo host. Ela não coordena instalações em máquinas/pastas diferentes. Use um único runtime para os bots e evite sessões externas simultâneas com a conta/perfil durante as tarefas.
