# Uso da ponte

Envie ao Maestro uma URL completa, uma tarefa concreta e peça apenas o resultado final. Não envie placeholders, senhas, códigos ou tokens.

> Maestro, use a ponte para abrir https://example.com, clicar em “Learn more” e retornar o título e a URL da página de destino. Aguarde e entregue apenas o resultado final.

> Maestro, use a ponte para abrir https://news.ycombinator.com/ e retornar os títulos e links das três primeiras notícias. Aguarde e entregue apenas o resultado final.

O Maestro usa `navegar(tarefa, url)` do conector `codex-cloud-pilot`. As instruções específicas de outros sites podem ficar nas skills/configuração do orquestrador e ser enviadas na tarefa. Não precisam de uma ferramenta MCP por site.

## Login em outro site

A ferramenta MCP não prepara uma janela de login nem recebe credenciais. Essa preparação é manual e separada da navegação automática:

1. Peça ao operador/Codex: “Abra https://github.com/login no navegador Cloud com o mesmo perfil da ponte para eu fazer login manualmente.”
2. O operador prepara a sessão usando o `profile_id` da configuração privada e fornece a janela remota ao usuário. Faça login e MFA nessa janela.
3. Avise que terminou. O operador encerra a sessão de preparação para salvar o perfil; só depois envie outra tarefa ao Maestro.
4. O executor reutiliza esse perfil nas próximas execuções. Se a sessão expirar, repita a preparação.

Autenticar no navegador comum do computador não prepara o perfil remoto da ponte. Retorno `requires_auth` indica necessidade de login manual; a execução termina e fecha seu navegador remoto.

## Erros e escopo

- `busy`: já existe uma tarefa em execução. Aguarde a conclusão antes de enviar outra.
- `requires_auth`: prepare ou renove o login fora do MCP.
- `out_of_scope`: pedido exige uma alteração que este MVP não permite.
- `failed` / `timed_out`: leia o erro e decida se quer tentar novamente. Não há repetição automática.

O Mac deve permanecer ligado, acordado, com a sessão do usuário iniciada e conectado. Use uma conta/perfil por instalação neste MVP; múltiplos usuários, isolamento de contas e publicação de sites não foram implementados.
