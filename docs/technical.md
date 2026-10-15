# Guia técnico

## Instalação ativa: MCP Command no computador do Grok

A única instalação ativa no Maestro é `codex-browser-command`, com transporte MCP Command/stdio. O processo MCP inicia o Codex CLI autenticado com ChatGPT no computador do Grok. O CLI acessa o modelo remotamente e controla, via agent-browser, um navegador no Browser Use Cloud. Host do executor e navegador são camadas separadas.

O servidor usa exclusivamente stdio. O orquestrador inicia o processo e aguarda o retorno da ferramenta. A instalação e a recuperação estão no [guia de instalação](install.md): um comando prepara as dependências e gera o lançador; autenticação e configuração privada permanecem separadas.

`run-command.sh --check` executa somente o diagnóstico local. Sem argumentos, o processo serve MCP e reserva stdout ao protocolo. O instalador pode ser repetido e preserva a configuração existente. Modelo e esforço são configuráveis no runtime privado.

## Interface MCP

Uma ferramenta: `navegar(tarefa: str, url: str)`.

```json
{
  "tarefa": "Abra a página, clique em Learn more e retorne o título e a URL de destino.",
  "url": "https://example.com"
}
```

`tarefa` deve conter de 1 a 6.000 caracteres; `url` deve ser uma URL pública HTTP(S), sem credenciais. Skills, receitas e instruções de cada site pertencem a outra camada e podem ser incluídas em `tarefa`. Não há carregador de skills específicas neste projeto.

O resultado de uma execução contém `status`, `result`, `final_url`, `error`, `metrics`, `browser_closed` e `run_id`. Recusas anteriores à execução, como `busy`, `requires_setup` ou entrada inválida, podem retornar apenas `status` e `error`. Falhas de entrega podem incluir `run_id` sem os demais campos. Consumidores devem tratar esses campos como opcionais.

Estados possíveis: `succeeded`, `failed`, `requires_auth`, `out_of_scope`, `timed_out`, `busy` e `requires_setup`. Veja [como lidar com os retornos](usage.md#erros-e-escopo).

Uma tarefa por runtime/host, protegida por trava de arquivo herdada pelo executor, inclusive entre processos MCP diferentes; sem fila, polling ou repetição automática. O Codex tem prazo de 180 segundos; preparação e encerramento acrescentam tempo. O adaptador aguarda até 300 segundos, dá até 60 segundos para o executor terminar após cancelamento e tenta recuperar o encerramento pelo registro privado se ele falhar. Chamadas de limpeza ao provedor também têm limites próprios. Progresso, observações e logs ficam no executor; o MCP entrega somente o resultado final.

## Implementação e limites

| Arquivo | Responsabilidade |
| --- | --- |
| `app/server.py` | Contrato MCP stdio, uma execução por vez e entrega final. |
| `app/diagnostics.py` | Verifica requisitos e compatibilidade básica das CLIs, sem modelo ou navegador. |
| `app/lifecycle.py` | Registra criação/encerramento e recupera a limpeza da sessão identificada. |
| `app/executor.py` | Inicia Codex, registra métricas da execução e encerra o navegador. |
| `app/browser.py` e `app/browser_cli.py` | Conexão com Browser Use Cloud e comandos permitidos. |
| `app/navigation_guard.py` | Verificação de URLs de navegação. |
| `app/executor-policy.txt` | Regras genéricas de leitura e pesquisa. |
| `app/schema.json` | Formato da resposta solicitada ao modelo; o executor acrescenta métricas e estado do navegador. |
| `scripts/setup_command.py` | Instala dependências ausentes e prepara os lançadores Command/stdio. |

O executor permite abrir páginas públicas HTTP(S), navegar por links/menus, rolar e preencher buscas, reutilizando um perfil de login persistente. O navegador de cada tarefa é efêmero. Login e MFA são preparados manualmente no mesmo perfil Cloud, fora da ferramenta MCP; veja [o guia de uso](usage.md#login-em-outro-site).

A política do modelo e a lista de comandos reduzem as operações expostas; não constituem isolamento de segurança para múltiplos clientes. A checagem genérica confere execução e URL final, sem provar semanticamente todas as respostas. As métricas de tokens são do Codex; não medem o consumo do Maestro nem demonstram economia de tokens do orquestrador.

## Dados privados

Chaves API, autenticação Codex, IDs de perfis reais, cookies, logs, prompts de tarefas, resultados, capturas e dados pessoais ficam fora do repositório. O `.gitignore` exclui os caminhos comuns; revise os arquivos antes de qualquer commit.

Não copie a pasta privada inteira para o GitHub. A instalação Command depende do host do Grok, da autenticação Codex e do acesso ao Browser Use.

## Falhas e limites do supervisor

O Codex e seus descendentes no mesmo grupo são encerrados ao terminar ou exceder o prazo. O MCP confere código de saída, formato da resposta e confirmação no registro de encerramento; não encaminha sucesso apenas porque recebeu um JSON. Se um processo MCP morrer abruptamente, o executor conserva a trava enquanto estiver ativo. O marcador persistente impede outra execução quando não há confirmação de limpeza.

Interrupção total do host e criação Cloud com resultado desconhecido não permitem prometer encerramento imediato. Nesses casos a ponte bloqueia novas tarefas e exige conferência do operador; consulte [encerramento incerto](usage.md#encerramento-incerto). Isso também se aplica a uma indisponibilidade do provedor durante a limpeza. Não há coordenação distribuída, sandbox contra um executor malicioso ou garantia semântica de todas as respostas. O ambiente implantado é Linux; a trava exige POSIX.
