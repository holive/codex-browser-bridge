# Outro host — opcional

A POC usa o computador do Grok por MCP Command/stdio. Uma VPS independente não é requisito do fluxo atual.

O instalador pode preparar o runtime em outro host com Python e Node/npm compatíveis; veja [instalação e recuperação](install.md). Isso não conecta automaticamente o Grok à VPS: MCP por comando executa na máquina escolhida pelo cliente. Para um host externo, seria necessário definir transporte ou execução remota, autenticação e disponibilidade. Esse caminho não está implementado neste projeto.

Browser Use Cloud e `navegar(tarefa, url)` podem ser preservados. Evite instalações simultâneas com o mesmo perfil. Uma migração só estará validada após uma tarefa real pelo orquestrador no novo caminho, com resultado final e navegador encerrado.
