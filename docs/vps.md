# Migração para VPS — adiada

A arquitetura permite trocar o host do executor mantendo o Browser Use Cloud e a interface `navegar(tarefa, url)`. A migração abaixo é um plano, não uma implantação já validada.

1. Preparar um usuário de serviço, Python, Codex CLI e agent-browser compatíveis na VPS. Definir `CODEX_BROWSER_BRIDGE_HOME` para uma pasta privada.
2. Preparar a autenticação do Codex na VPS e transferir somente a configuração necessária de forma privada. Reutilizar o perfil Cloud existente; não copiar logs ou o diretório inteiro de autenticação sem necessidade.
3. Instalar o código e criar um serviço equivalente ao LaunchAgent usando o gerenciador da VPS. O instalador deste repositório é específico de macOS.
4. Mover o conector do túnel fixo para a VPS. Evitar dois executores usando o mesmo perfil simultaneamente: parar o lado Mac durante a troca e iniciar o lado VPS. Preservar hostname, caminho MCP e credencial.
5. Executar uma tarefa pública pelo orquestrador e confirmar a resposta final e o encerramento do navegador.
6. Desativar os serviços locais. Manter um caminho de retorno ao Mac caso a execução na VPS falhe.

Não há VPS, fila distribuída, agendador, múltiplas contas ou novo provedor incluídos nesta etapa.

## Alternativa: computador do Grok Bot

O executor pode, em princípio, rodar no computador persistente do próprio Grok Bot, mantendo o Browser Use Cloud separado. Essa opção ainda não foi instalada ou validada com o código deste repositório.

Requisitos mínimos: Python e dependências, Codex CLI autenticado, agent-browser, chave Browser Use e perfil, código/configuração em armazenamento persistente, e uma forma de executar a tarefa até o retorno final. O Codex suporta autenticação em ambiente remoto por device code quando habilitada na conta.

O Grok suporta MCP por comando na máquina da conversa. Esse transporte pode dispensar o túnel para uso pessoal, mas o servidor deste repositório ainda implementa HTTP; seria preciso adicionar a entrada stdio e validar a entrega final. Se mantiver HTTP, precisará de um processo disponível e do endereço alcançável pelo cliente.

A documentação orienta guardar projetos duráveis em `/workspace` e tratar pacotes instalados manualmente como substituíveis após recuperação. Guardar instalação reproduzível e conferir a retomada faz parte da preparação. Arquivos e credenciais CLI são compartilhados pelos bots da mesma conta; a separação de telas não isola credenciais.

Fontes: [Computador do Grok Bot](https://docs.x.ai/grok-bot/computer-and-apps), [MCP por comando](https://docs.x.ai/grok-bot/team-bots), [Autenticação remota do Codex](https://learn.chatgpt.com/docs/auth#login-on-headless-devices).
