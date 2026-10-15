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

## Onze execuções reais adicionais no Grok

Em 15/10/2026, o runner com a correção `bd29ef8` conduziu três rodadas pelo MCP Command real, Codex CLI e Browser Use Cloud no computador do Grok. **11/11 casos passaram**, com encerramento confirmado tanto pela ponte quanto pela API do provedor em todos os casos. O Maestro iniciou o trabalho e leu status a pedido do usuário; não acompanhou cliques.

A primeira tentativa parou no handshake MCP antes de chamar `navegar`: o runner usava `serverInfo` e `isError`, enquanto o SDK Python instalado expõe `server_info` e `is_error`. A correção foi verificada com um handshake MCP real sem modelo/Cloud antes da retomada. O runner passou a guardar a exceção completa em arquivo privado. Os registros da tentativa original foram preservados.

| Rodada | Caso | Status esperado e observado | Tempo aproximado | Entrada | Cache | Sem cache | Saída |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `public_link` | `succeeded` | 20.8 s | 75.393 | 59.136 | 16.257 | 280 |
| 1 | `public_search` | `succeeded` | 24.5 s | 105.268 | 85.376 | 19.892 | 309 |
| 1 | `saved_login` | `succeeded` | 16.5 s | 29.861 | 14.720 | 15.141 | 136 |
| 1 | `SIGTERM` | `timed_out` | 3.8 s | Desconhecido | Desconhecido | Desconhecido | Desconhecido |
| 1 | `SIGKILL` | `failed` | 3.0 s | Desconhecido | Desconhecido | Desconhecido | Desconhecido |
| 2 | `missing_information` | `succeeded` | 14.9 s | 45.154 | 29.568 | 15.586 | 165 |
| 2 | `refuse_publication` | `out_of_scope` | 12.4 s | 29.744 | 14.592 | 15.152 | 128 |
| 2 | `public_link` | `succeeded` | 20.0 s | 75.686 | 59.520 | 16.166 | 378 |
| 3 | `saved_login` | `succeeded` | 13.3 s | 29.862 | 14.720 | 15.142 | 133 |
| 3 | `public_search` | `succeeded` | 22.4 s | 105.258 | 85.376 | 19.882 | 312 |
| 3 | `public_link` | `succeeded` | 18.4 s | 75.288 | 59.136 | 16.152 | 247 |

**Uso conhecido:** 571.514 tokens de entrada, sendo 422.144 em cache e 149.370 sem cache; 2.088 de saída. As duas interrupções não reportaram uso e estão excluídas das somas; seu consumo é desconhecido. O limite de 250.000 tokens sem cache foi respeitado no uso medido, mas não permite afirmar um teto absoluto incluindo essas interrupções. O consumo do Maestro não foi medido.

Os casos somaram aproximadamente **170 s de execução**. As duas primeiras rodadas foram iniciadas às 16:34 e 16:54 BRT. A pedido do usuário, a terceira foi antecipada de 17:29 para **17:07 BRT**: o runner ocioso foi encerrado após confirmar ausência de tarefa/limpeza pendente, e uma continuação privada executou somente os três casos restantes. Os oito resultados anteriores e seus relatórios foram preservados; a continuação manteve o limite global de 11 execuções admitidas e o consumo conhecido acumulado.

O login salvo funcionou nas duas consultas, separadas por **31 min 46,9 s entre os inícios** (aproximadamente 31 min 30,4 s entre o fim da primeira e o início da segunda). Isso não constitui o teste originalmente previsto de 55 minutos. O período total do início original até o fim foi de aproximadamente 33 min 27 s, incluindo as esperas.

**Interrupções reais:** SIGTERM no executor próprio devolveu `timed_out`; SIGKILL devolveu `failed`; ambos passaram porque esses eram os resultados esperados e o navegador foi parado. Uma chamada MCP concorrente real recebeu `busy`, sem admitir outra execução. Essa evidência permanece no relatório original; não foi copiada pelo wrapper para o relatório da continuação. Não houve `cleanup_pending` nem marcador `active-run.json` ao final. Nenhuma alteração nos sites ou novo login foi feito.

Os relatórios completos, identificação dos processos/sessões e wrapper de continuação permanecem privados. Esta bateria adicional não repetiu a suíte de testes unitários. Não foram alterados a chave, o perfil, o conector de produção ou a visibilidade do repositório.

## Limites que continuam explícitos

- A trava coordena apenas processos usando a mesma pasta no mesmo host; não coordena máquinas/instalações distintas.
- Se a criação remota não devolver uma identidade, se o provedor ficar indisponível ou se todo o host morrer, não é possível prometer encerramento imediato. A ponte conserva um marcador e bloqueia outra tarefa até conferência do operador. Veja [encerramento incerto](usage.md#encerramento-incerto).
- Foram interrompidos somente executores próprios em duas chamadas Cloud reais (SIGTERM e SIGKILL), com parada do navegador confirmada. Indisponibilidade do provedor, perda total do host e falhas destrutivas de infraestrutura não foram provocadas.
- A identificação inicial depende de uma nova sessão inequívoca na conta Cloud. Evite criar sessões externas simultâneas durante a tarefa; múltiplas sessões novas tornam a identificação incerta e bloqueiam a continuação.
- Leitura/pesquisa é o escopo atual. Regras do modelo e a lista de comandos não constituem isolamento contra um executor malicioso ou garantia absoluta de que todo clique seja semanticamente inofensivo. Alterações em dados empresariais continuam fora do escopo.
- Os resultados cobrem os casos listados; não são uma medição estatística de confiabilidade geral.

O comportamento de criação desconhecida e de fechamento pendente também é descrito na [documentação oficial do agent-browser](https://github.com/vercel-labs/agent-browser#browser-use). A ponte trata esses casos como pendência operacional, não como sucesso nem motivo de repetição automática.

## Antes de publicar

Uma busca automatizada por padrões de tokens/chaves, chaves privadas, URLs de controle e IDs reais de perfil em 75 blobs do histórico não encontrou correspondências. Isso é uma checagem direcionada, não prova de ausência de qualquer informação sensível. Novos registros deste relatório foram mantidos sem dados da conta.

O repositório permanece privado. Falta escolher uma licença de distribuição e autorizar a mudança de visibilidade. Não foi atribuída uma licença nem publicada uma versão durante esta bateria.
