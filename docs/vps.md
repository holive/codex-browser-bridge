# Migração para VPS — adiada

O executor já funciona no computador do Grok por MCP Command/stdio. A POC dispensa VPS independente e túnel.

A arquitetura permite trocar o host mantendo Browser Use Cloud e `navegar(tarefa, url)`. O roteiro abaixo descreve a alternativa HTTP para uma VPS independente; não é um passo pendente da POC nem uma implantação validada.

1. Preparar um usuário de serviço, Python, Codex CLI e agent-browser compatíveis na VPS. Definir `CODEX_BROWSER_BRIDGE_HOME` para uma pasta privada.
2. Preparar a autenticação do Codex na VPS e transferir somente a configuração necessária de forma privada. Reutilizar o perfil Cloud existente; não copiar logs ou o diretório inteiro de autenticação sem necessidade.
3. Instalar o código e criar um serviço usando o gerenciador da VPS. O projeto ainda não inclui um instalador de serviço para VPS.
4. Se optar por HTTP remoto, preparar endereço/túnel e cadastrar o conector correspondente no orquestrador. Evitar executores simultâneos usando o mesmo perfil.
5. Executar uma tarefa pública pelo orquestrador e confirmar a resposta final e o encerramento do navegador.
6. Após validar a VPS, desativar o conector Command anterior para manter um só caminho ativo.

Não há VPS, fila distribuída, agendador, múltiplas contas ou novo provedor incluídos nesta etapa.

A instalação Command no computador do Grok já está descrita no [guia técnico](technical.md), com os resultados no [registro de validação](validation.md).
