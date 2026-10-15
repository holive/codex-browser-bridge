# Guia técnico

## Instalação ativa: MCP Command no computador do Grok

A única instalação ativa no Maestro é `codex-browser-command`, com transporte MCP Command/stdio. O processo MCP inicia o Codex CLI autenticado com ChatGPT no computador do Grok. O CLI acessa o modelo remotamente e controla, via agent-browser, um navegador no Browser Use Cloud. Host do executor e navegador são camadas separadas.

O mesmo servidor oferece `--transport stdio`. O orquestrador inicia o processo e aguarda o retorno da ferramenta; esse caminho não usa túnel, hostname público ou serviço HTTP.

1. Guarde o código em uma pasta durável do computador remoto e prepare uma pasta privada para o runtime.
2. Crie `.venv` nessa pasta e instale `requirements.txt`. Confirme Codex autenticado e agent-browser disponível (a POC usa 0.39.1).
3. Execute `python3 scripts/setup_command.py --home /caminho/privado/do/runtime`, informando `--agent-browser /caminho/do/binario` se necessário.
4. Cadastre o `run-command.sh` gerado como MCP **Command**. Disponibilize `BROWSER_USE_API_KEY` pelo gerenciador de segredos do Grok no ambiente do processo e configure `BROWSER_USE_PROFILE_ID` com o perfil escolhido. Não coloque valores secretos no comando, nos argumentos ou no Git.
5. Ao preparar uma nova instalação, chame `navegar` uma vez com uma tarefa pública simples e confira a conclusão. Se faltar chave ou perfil, a ferramenta retorna `requires_setup` sem executar Codex ou abrir navegador.

O instalador por comando copia o código e cria os lançadores; não instala dependências, não altera o Mac nem grava a chave recebida pelo ambiente em arquivo. O runtime lê configuração privada opcional e prioriza as duas variáveis acima. A disponibilidade de credenciais no conector por comando deve ser confirmada no chat do proprietário do Grok; não há suporte multiusuário neste MVP.

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

Uma tarefa por vez; sem fila, polling ou repetição automática. O Codex tem prazo de 180 segundos; preparação e encerramento acrescentam tempo. O adaptador aguarda até 300 segundos e tenta cancelar/encerrar a execução em caso de falha. Progresso, observações e logs ficam no executor; o MCP entrega somente o resultado final.

## Implementação e limites

| Arquivo | Responsabilidade |
| --- | --- |
| `app/server.py` | Contrato MCP, transporte stdio/HTTP, uma execução por vez e entrega final. |
| `app/executor.py` | Inicia Codex, registra métricas da execução e encerra o navegador. |
| `app/browser.py` e `app/browser_cli.py` | Conexão com Browser Use Cloud e comandos permitidos. |
| `app/navigation_guard.py` | Verificação de URLs de navegação. |
| `app/executor-policy.txt` | Regras genéricas de leitura e pesquisa. |
| `app/schema.json` | Formato da resposta solicitada ao modelo; o executor acrescenta métricas e estado do navegador. |
| `scripts/setup_command.py` | Prepara os lançadores do transporte Command/stdio. |

O executor permite abrir páginas públicas HTTP(S), navegar por links/menus, rolar e preencher buscas, reutilizando um perfil de login persistente. O navegador de cada tarefa é efêmero. Login e MFA são preparados manualmente no mesmo perfil Cloud, fora da ferramenta MCP; veja [o guia de uso](usage.md#login-em-outro-site).

A política do modelo e a lista de comandos reduzem as operações expostas; não constituem isolamento de segurança para múltiplos clientes. A checagem genérica confere execução e URL final, sem provar semanticamente todas as respostas. As métricas de tokens são do Codex; não medem o consumo do Maestro nem demonstram economia de tokens do orquestrador.

## Instalação no Mac — opção histórica, desativada

A ponte e o túnel do Mac foram parados e desabilitados no launchd; o conector HTTPS foi retirado do Maestro. O código HTTP/macOS permanece como opção histórica. Os passos abaixo servem apenas para uma eventual instalação deliberada desse caminho.

Dependências usadas na POC: Python 3.12, Codex CLI 0.162.1 autenticado, agent-browser 0.39.1 com suporte a Browser Use Cloud, e Cloudflare Tunnel. O navegador roda no Cloud; não é necessário instalar um Chrome local para o executor.

O código fica neste repositório. Configuração privada, dependências e logs ficam por padrão em `~/Library/Application Support/CodexBrowserBridge`, ou no caminho definido por `CODEX_BROWSER_BRIDGE_HOME`.

1. Crie essa pasta privada com permissão `700`. Crie nela `.venv` e instale `requirements.txt` com seu gerenciador Python. Instale os CLIs fora do repositório e autentique o Codex.
2. Copie `config.example.json` para `config.json` nessa pasta privada, com permissão `600`. Preencha chave Browser Use, ID do perfil, caminhos dos executáveis, hostname e um caminho MCP secreto aleatório. Não use o valor de exemplo como credencial.
3. Configure um túnel Cloudflare com hostname fixo apontando para `http://127.0.0.1:63317` e mantenha seu processo como serviço. Credenciais e configuração do túnel ficam fora do Git. Este projeto não provisiona DNS/Cloudflare; [documentação oficial](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/as-a-service/macos/).
4. Rode `python3 scripts/install_macos.py` somente quando quiser instalar ou substituir o serviço local. Ele copia o aplicativo para a pasta privada, cria o lançador do navegador e instala o LaunchAgent do executor. Usa a `.venv` já preparada; não baixa software nem altera o túnel. Inicia ao entrar no macOS e reinicia se o processo sair.
5. Cadastre o MCP Remote HTTPS no orquestrador usando o hostname e caminho secretos da sua configuração. Não coloque a URL completa em documentação, commits ou mensagens públicas.

O servidor ainda se identifica internamente como `codex-cloud-pilot` por compatibilidade histórica. O conector HTTPS com esse nome foi retirado do Maestro; esse identificador não indica uma instalação ativa.

## Dados privados

Chaves API, caminho secreto do MCP, certificados/tokens do túnel, autenticação Codex, IDs de perfis reais, cookies, logs, prompts de tarefas, resultados, capturas e dados pessoais ficam fora do repositório. O `.gitignore` exclui os caminhos comuns; revise os arquivos antes de qualquer commit.

Não copie a pasta privada inteira para o GitHub. Dados privados preservados no Mac não são usados pelo fluxo atual. A instalação Command depende do host do Grok, da autenticação Codex e do acesso ao Browser Use; não há fallback ativo no Mac.
