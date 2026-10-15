# Codex Browser Bridge

Delegue tarefas de navegador ao Codex a partir do Grok Bot, usando sua assinatura do ChatGPT. Envie uma tarefa e uma URL; o Codex navega, pesquisa e devolve o resultado ao orquestrador.

## Por que esta ponte existe

O Grok Bot já oferece navegação. Criei esta ponte porque executar tarefas de navegador por ele estava caro no meu uso, e eu já tinha acesso ao Codex por assinatura. Queria uma forma de o Grok Bot delegar esse trabalho ao Codex e receber a resposta pronta.

A ponte oferece essa interface. O orquestrador envia o objetivo; o Codex conduz a navegação em um navegador real no Browser Use Cloud. Cliques, observações e buscas ficam com o executor, que fecha o navegador antes de devolver uma única resposta final.

Reduzir o custo foi a motivação. A economia ainda não foi medida: depende do uso, dos limites da assinatura e dos custos do navegador Cloud.

## Um pedido, um resultado

Peça ao Maestro, o orquestrador no Grok Bot:

> Use codex-browser-command para abrir https://news.ycombinator.com/ e retornar os títulos e links das três primeiras notícias.

O Maestro chama a ferramenta `navegar(tarefa, url)` e aguarda o resultado. Você também pode pedir para seguir um link e conferir a página de destino ou pesquisar um assunto na documentação de um site e trazer um resumo com as fontes.

Veja [o guia de uso](docs/usage.md) para mais exemplos, preparação de login e tratamento dos retornos.

## Como as peças se conectam

```text
Maestro → ponte MCP → Codex CLI → navegador no Browser Use Cloud
Maestro ← resultado final, após o encerramento do navegador
```

A instalação ativa usa o conector `codex-browser-command`, com transporte MCP Command/stdio. A ponte e o Codex CLI rodam no computador do Grok Bot; o modelo é acessado remotamente, e o navegador roda no Browser Use Cloud.

O login é preparado manualmente no mesmo perfil Cloud, antes da tarefa. Skills e receitas de sites ficam fora do conector e podem ser incluídas nas instruções enviadas ao Codex.

## O que funciona hoje

Esta é uma prova de conceito pessoal para leitura e pesquisa: abrir páginas, seguir links e preencher buscas. Edição de dados, publicação, mensagens, compras e exclusões ficam fora do escopo. Há uma tarefa por vez, sem fila nem repetição automática.

O fluxo foi validado em uma tarefa pública: abrir example.com, seguir “Learn more” e retornar o título e a URL da IANA. A execução levou cerca de 18 segundos e confirmou o encerramento do navegador antes da resposta. Esse teste verifica a conexão; confiabilidade geral, economia de tokens do Maestro e suporte multiusuário não foram demonstrados.

## Documentação

- [Instalação e recuperação](docs/install.md): preparar do zero, diagnosticar e adaptar mudanças de versão.
- [Uso](docs/usage.md): pedidos, login e tratamento dos retornos.
- [Guia técnico](docs/technical.md): instalação, interface MCP, implementação e limites.
- [Arquitetura](docs/architecture.mmd): diagrama das conexões e responsabilidades.
- [Confiabilidade](docs/reliability.md): testes de falha, concorrência, correções e três cenários reais.
- [Validação](docs/validation.md): resultados observados e limites dos testes.
- [VPS opcional](docs/vps.md): alternativa futura de hospedagem, ainda não validada.
