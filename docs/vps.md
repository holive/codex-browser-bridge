# Migração para VPS — adiada

A arquitetura permite trocar o host do executor mantendo o Browser Use Cloud e a interface `navegar(tarefa, url)`. A migração abaixo é um plano, não uma implantação já validada.

1. Preparar um usuário de serviço, Python, Codex CLI e agent-browser compatíveis na VPS. Definir `CODEX_BROWSER_BRIDGE_HOME` para uma pasta privada.
2. Preparar a autenticação do Codex na VPS e transferir somente a configuração necessária de forma privada. Reutilizar o perfil Cloud existente; não copiar logs ou o diretório inteiro de autenticação sem necessidade.
3. Instalar o código e criar um serviço equivalente ao LaunchAgent usando o gerenciador da VPS. O instalador deste repositório é específico de macOS.
4. Mover o conector do túnel fixo para a VPS. Evitar dois executores usando o mesmo perfil simultaneamente: parar o lado Mac durante a troca e iniciar o lado VPS. Preservar hostname, caminho MCP e credencial.
5. Executar uma tarefa pública pelo orquestrador e confirmar a resposta final e o encerramento do navegador.
6. Desativar os serviços locais. Manter um caminho de retorno ao Mac caso a execução na VPS falhe.

Não há VPS, fila distribuída, agendador, múltiplas contas ou novo provedor incluídos nesta etapa.
