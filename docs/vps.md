# Migração para VPS — adiada

O executor já funciona no computador do Grok por MCP Command/stdio. A POC dispensa VPS independente, Mac e túnel. A ponte e o túnel do Mac foram desativados, e o conector HTTPS foi retirado.

A arquitetura permite trocar o host mantendo Browser Use Cloud e `navegar(tarefa, url)`. O roteiro abaixo descreve a alternativa HTTP para uma VPS independente; não é um passo pendente da POC nem uma implantação validada.

1. Preparar um usuário de serviço, Python, Codex CLI e agent-browser compatíveis na VPS. Definir `CODEX_BROWSER_BRIDGE_HOME` para uma pasta privada.
2. Preparar a autenticação do Codex na VPS e transferir somente a configuração necessária de forma privada. Reutilizar o perfil Cloud existente; não copiar logs ou o diretório inteiro de autenticação sem necessidade.
3. Instalar o código e criar um serviço equivalente ao LaunchAgent usando o gerenciador da VPS. O instalador deste repositório é específico de macOS.
4. Se optar por HTTP remoto, preparar endereço/túnel e cadastrar o conector correspondente no orquestrador. Evitar executores simultâneos usando o mesmo perfil; o lado Mac já está desativado.
5. Executar uma tarefa pública pelo orquestrador e confirmar a resposta final e o encerramento do navegador.
6. Após validar a VPS, desativar o conector Command anterior para manter um só caminho ativo.

Não há VPS, fila distribuída, agendador, múltiplas contas ou novo provedor incluídos nesta etapa.

## Alternativa: computador do Grok Bot

O executor pode rodar no computador persistente do próprio Grok Bot, mantendo o Browser Use Cloud separado. Essa opção foi instalada e validada por uma tarefa pública com o código deste repositório; veja [a validação](validation.md).

Requisitos mínimos: Python e dependências, Codex CLI autenticado, agent-browser, chave Browser Use e perfil, código/configuração em armazenamento persistente, e uma forma de executar a tarefa até o retorno final. O Codex suporta autenticação em ambiente remoto por device code quando habilitada na conta.

O Grok suporta MCP por comando na máquina da conversa. Esse transporte pode dispensar o túnel para uso pessoal, e o servidor agora oferece `--transport stdio`; instalação, configuração privada e entrega final foram confirmadas no computador do Grok. O conector é `codex-browser-command`, com o `run-command.sh` gerado pelo instalador. Se mantiver HTTP, precisará de um processo disponível e do endereço alcançável pelo cliente.

A documentação orienta guardar projetos duráveis em `/workspace` e tratar pacotes instalados manualmente como substituíveis após recuperação. Guardar instalação reproduzível e conferir a retomada faz parte da preparação. Arquivos e credenciais CLI são compartilhados pelos bots da mesma conta; a separação de telas não isola credenciais.

Fontes: [Computador do Grok Bot](https://docs.x.ai/grok-bot/computer-and-apps), [MCP por comando](https://docs.x.ai/grok-bot/team-bots), [Autenticação remota do Codex](https://learn.chatgpt.com/docs/auth#login-on-headless-devices).
