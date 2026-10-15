# Codex Browser Bridge

Uma ponte para pedir ao seu assistente que pesquise em sites usando um navegador real. Você envia uma tarefa e uma URL; a ponte cuida da navegação e devolve uma única resposta final após fechar o navegador.

## Como funciona

O Maestro delega o pedido ao Codex, que abre páginas, segue links e faz buscas no Browser Use Cloud. Assim, o orquestrador recebe o resultado sem precisar decidir ou acompanhar cada clique.

A instalação ativa usa o conector **`codex-browser-command`**: a ponte e o Codex CLI rodam no computador do Grok Bot; o navegador roda separadamente no Browser Use Cloud. A execução do CLI nesse computador não significa que o modelo rode localmente.

```text
Maestro → ponte → Codex CLI no computador do Grok → navegador no Browser Use Cloud
Maestro ← resposta final da ponte, após encerrar o navegador
```

## O que pedir

- “Abra https://example.com, siga o link Learn more e retorne o título e a URL de destino.”
- “Abra https://news.ycombinator.com/ e retorne os títulos e links das três primeiras notícias.”
- “Abra a documentação neste endereço, pesquise o assunto indicado e resuma o que encontrar com os links das páginas.”

Veja [como enviar os pedidos ao Maestro e preparar login](docs/usage.md). O login é feito manualmente no mesmo perfil do navegador Cloud, antes da tarefa. Skills e receitas de sites ficam em uma camada separada e podem ser incluídas no pedido.

## Escopo e estado atual

Esta é uma **POC pessoal de leitura e pesquisa**: pode navegar e preencher buscas, mas não editar dados, publicar, enviar mensagens, comprar ou excluir. Aceita uma tarefa por vez, sem fila nem repetição automática.

O caminho ativo foi validado com a tarefa pública de example.com até a IANA: sucesso em cerca de 18 segundos, com o navegador encerrado antes da resposta. Isso confirma essa conexão e esse caso de uso; não comprova confiabilidade geral, suporte multiusuário ou economia quantitativa de tokens do Maestro. Veja [o registro da validação](docs/validation.md).

Uma VPS independente é uma opção futura, sem implantação validada.

## Documentação

- [Uso](docs/usage.md): pedidos, login e tratamento dos retornos.
- [Guia técnico](docs/technical.md): instalação ativa, interface MCP, implementação e limites.
- [Arquitetura](docs/architecture.mmd): diagrama das conexões e responsabilidades.
- [Validação](docs/validation.md): o que foi observado e o que ainda não foi testado.
- [VPS opcional](docs/vps.md): alternativa futura de hospedagem.
