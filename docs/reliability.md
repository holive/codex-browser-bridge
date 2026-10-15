# Confiabilidade — bateria de 15/10/2026

A bateria encontrou e corrigiu cinco falhas antes de confirmar o fluxo real. O código aplicado no computador do Grok foi `78ac5c9` (servidor 0.8.0). A chave, o perfil Cloud e a autenticação Codex foram preservados.

## Testes sem modelo ou Cloud

A suíte usa processos reais e implementações fictícias do modelo/provedor. Passou **21/21** no ambiente de desenvolvimento em cerca de 6,8 s e **21/21 no Linux do Grok em cerca de 4,2 s**. Nenhuma tarefa de modelo ou sessão Cloud é iniciada por esses testes.

| Grupo | Casos | O que foi exercitado |
| --- | ---: | --- |
| Adaptador MCP e concorrência | 8 | Dois processos disputando o runtime, morte abrupta do processo MCP, cancelamento, timeout, saída inválida, código de saída com erro, bloqueio persistente e liberação após limpeza confirmada |
| Executor e encerramento | 9 | Timeout e SIGTERM reais, processo descendente após saída do líder, falha antes da criação, criação com resultado desconhecido, falha de fechamento, parada por API, recusa de alteração e estado de modelo inválido |
| Entradas/configuração | 2 | URLs inválidas/privadas/credenciais, tarefas vazias/grandes e configuração ausente sem iniciar executor |
| Recuperação | 2 | Parar somente o ID registrado e não adivinhar um navegador quando a criação não devolveu identidade |

Para repetir a suíte a partir do repositório, use um Python com `requirements.txt` instalado:

```sh
python3 -m unittest discover -s tests -v
```

A instalação nova e a reinstalação com configuração fictícia preservada já tinham sido exercitadas separadamente; veja [o registro de validação](validation.md). A bateria acima passou também no host implantado.

## Falhas reproduzidas e corrigidas

1. A trava em memória permitia que processos MCP distintos executassem tarefas simultâneas. Agora há uma trava por runtime/host, herdada pelo executor.
2. O adaptador podia entregar um JSON de sucesso mesmo após saída não zero do executor. Agora confere código de saída, formato e registro de encerramento.
3. Um descendente podia sobreviver à saída normal do processo Codex. O grupo de processos é encerrado também nessa situação.
4. Falha ao encerrar o navegador podia manter uma resposta `requires_auth` como se a tarefa tivesse terminado normalmente. Falhas de limpeza agora prevalecem e bloqueiam a próxima tarefa.
5. Uma falha anterior à criação ainda disparava um comando de fechar sessão. O ciclo de vida agora distingue navegador não iniciado, criação, sessão identificada e encerramento.

Esses cinco casos foram observados falhando na versão anterior; passaram depois das correções. A suíte adicional cobre os limites e caminhos de recuperação relacionados.

## Três chamadas reais pelo Grok

O Maestro chamou `navegar` uma vez por cenário, sequencialmente, sem observar os cliques e sem repetição automática. Somente resultados finais e métricas foram retornados.

| Caso | Resultado esperado/observado | Tempo do executor | Entrada | Cache | Sem cache | Saída | Navegador encerrado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Página pública → link → destino | `succeeded`; Example Domains / IANA | 21,8 s | 75.341 | 44.160 | 31.181 | 273 | Sim |
| Consulta em painel com login salvo | `succeeded`; autenticação preservada | 13,4 s | 48.383 | 29.568 | 18.815 | 166 | Sim |
| Pedido de alteração/publicação | `out_of_scope`; alteração recusada | 12,6 s | 29.746 | 14.592 | 15.154 | 136 | Sim |
| **Total** | **3/3 aprovados** | **47,8 s** | **153.470** | **88.320** | **65.150** | **575** | **3/3** |

Não houve `cleanup_pending`. Tempos são somados das execuções; não incluem instalação e coordenação do Maestro. Tokens são do Codex; o consumo do Maestro não foi medido. Resultados de conta, IDs de execução e registros completos ficaram privados.

## Limites que continuam explícitos

- A trava coordena apenas processos usando a mesma pasta no mesmo host; não coordena máquinas/instalações distintas.
- Se a criação remota não devolver uma identidade, se o provedor ficar indisponível ou se todo o host morrer, não é possível prometer encerramento imediato. A ponte conserva um marcador e bloqueia outra tarefa até conferência do operador. Veja [encerramento incerto](usage.md#encerramento-incerto).
- Não foram provocadas falhas destrutivas na infraestrutura real. Os testes de falha usam o provedor fictício; os três casos reais verificam a integração normal e a recusa.
- A identificação inicial depende de uma nova sessão inequívoca na conta Cloud. Evite criar sessões externas simultâneas durante a tarefa; múltiplas sessões novas tornam a identificação incerta e bloqueiam a continuação.
- Leitura/pesquisa é o escopo atual. Regras do modelo e a lista de comandos não constituem isolamento contra um executor malicioso ou garantia absoluta de que todo clique seja semanticamente inofensivo. Alterações em dados empresariais continuam fora do escopo.
- Os resultados cobrem os casos listados; não são uma medição estatística de confiabilidade geral.

O comportamento de criação desconhecida e de fechamento pendente também é descrito na [documentação oficial do agent-browser](https://github.com/vercel-labs/agent-browser#browser-use). A ponte trata esses casos como pendência operacional, não como sucesso nem motivo de repetição automática.

## Antes de publicar

Uma busca automatizada por padrões de tokens/chaves, chaves privadas, URLs de controle e IDs reais de perfil em 75 blobs do histórico não encontrou correspondências. Isso é uma checagem direcionada, não prova de ausência de qualquer informação sensível. Novos registros deste relatório foram mantidos sem dados da conta.

O repositório permanece privado. Falta escolher uma licença de distribuição e autorizar a mudança de visibilidade. Não foi atribuída uma licença nem publicada uma versão durante esta bateria.
