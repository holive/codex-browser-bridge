# Codex Browser Bridge

MCP privado para um orquestrador delegar navegação de leitura e pesquisa ao Codex CLI, usando Browser Use Cloud. O orquestrador envia uma tarefa e recebe um único resultado final depois do encerramento do navegador. Progresso, observações e logs ficam no executor.

```text
Orquestrador → MCP Command (stdio) ou HTTPS → executor Codex → Browser Use Cloud
Orquestrador ← resultado final ← navegador encerrado
```

## Interface

Uma ferramenta: `navegar(tarefa: str, url: str)`.

```json
{
  "tarefa": "Abra a página, clique em Learn more e retorne o título e a URL de destino.",
  "url": "https://example.com"
}
```

O resultado contém `status`, `result`, `final_url`, `error`, `metrics`, `browser_closed` e `run_id`. Estados: `succeeded`, `failed`, `requires_auth`, `out_of_scope`, `timed_out`, `busy` ou `requires_setup`.

Uma tarefa por vez; sem fila, polling ou repetição automática. O Codex tem prazo de 180 segundos; preparação e encerramento acrescentam tempo. O adaptador aguarda até 300 segundos e tenta cancelar/encerrar a execução em caso de falha.

## Separação de responsabilidades

- `app/server.py`: contrato MCP, uma execução por vez e entrega final.
- `app/executor.py`: inicia Codex, mede uso e encerra o navegador.
- `app/browser.py` e `app/browser_cli.py`: conexão com Browser Use Cloud e comandos permitidos.
- `app/executor-policy.txt`: regras genéricas de execução de leitura/pesquisa.
- Skills, receitas e instruções de cada site pertencem a outra camada. O orquestrador pode incluí-las em `tarefa`, com até 6.000 caracteres. Não há carregador de skills específicas neste projeto.

## Uso e limites

Veja [o guia de uso](docs/usage.md), [a arquitetura](docs/architecture.mmd) e [a validação registrada](docs/validation.md).

Escopo atual: abrir páginas públicas HTTP(S), navegar por links/menus, rolar e preencher buscas, reutilizando um perfil de login. Edição de dados, publicação, mensagens, compras e exclusões ficam fora do escopo. A política do modelo e a lista de comandos reduzem as operações expostas; não constituem isolamento de segurança para múltiplos clientes. A checagem genérica confere execução e URL final, sem provar semanticamente todas as respostas.

Na instalação HTTPS do Mac, ele precisa estar ligado, acordado, com a sessão do usuário iniciada e conectado. O conector Command executa no computador do Grok e dispensa o Mac. O navegador remoto é efêmero; o perfil de autenticação é persistente, conforme as regras de cada site.

## Instalação no Mac

Dependências usadas na POC: Python 3.12, Codex CLI 0.162.1 autenticado, agent-browser 0.39.1 com suporte a Browser Use Cloud, e Cloudflare Tunnel. O navegador roda no Cloud; não é necessário instalar um Chrome local para o executor.

O código fica neste repositório. Configuração privada, dependências e logs ficam por padrão em `~/Library/Application Support/CodexBrowserBridge`, ou no caminho definido por `CODEX_BROWSER_BRIDGE_HOME`.

1. Crie essa pasta privada com permissão `700`. Crie nela `.venv` e instale `requirements.txt` com seu gerenciador Python. Instale os CLIs fora do repositório e autentique o Codex.
2. Copie `config.example.json` para `config.json` nessa pasta privada, com permissão `600`. Preencha chave Browser Use, ID do perfil, caminhos dos executáveis, hostname e um caminho MCP secreto aleatório. Não use o valor de exemplo como credencial.
3. Configure um túnel Cloudflare com hostname fixo apontando para `http://127.0.0.1:63317` e mantenha seu processo como serviço. Credenciais e configuração do túnel ficam fora do Git. Este projeto não provisiona DNS/Cloudflare; [documentação oficial](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/as-a-service/macos/).
4. Rode `python3 scripts/install_macos.py` somente quando quiser instalar ou substituir o serviço local. Ele copia o aplicativo para a pasta privada, cria o lançador do navegador e instala o LaunchAgent do executor. Usa a `.venv` já preparada; não baixa software nem altera o túnel. Inicia ao entrar no macOS e reinicia se o processo sair.
5. Cadastre o MCP Remote HTTPS no orquestrador usando o hostname e caminho secretos da sua configuração. Não coloque a URL completa em documentação, commits ou mensagens públicas.

O nome MCP permanece `codex-cloud-pilot` por compatibilidade com o conector já cadastrado. Após atualizar ferramentas, o cliente pode precisar recarregar seu catálogo; um parâmetro de revisão de esquema na URL pode invalidar o cache, mantendo host, caminho e credencial.


## MCP por comando no computador do Grok

O mesmo servidor oferece `--transport stdio`. O orquestrador inicia o processo e aguarda o retorno da ferramenta; esse caminho não usa túnel, hostname público ou serviço HTTP.

1. Guarde o código em uma pasta durável do computador remoto e prepare uma pasta privada para o runtime.
2. Crie `.venv` nessa pasta e instale `requirements.txt`. Confirme Codex autenticado e agent-browser disponível (a POC usa 0.39.1).
3. Execute `python3 scripts/setup_command.py --home /caminho/privado/do/runtime`, informando `--agent-browser /caminho/do/binario` se necessário.
4. Cadastre o `run-command.sh` gerado como MCP **Command**. Disponibilize `BROWSER_USE_API_KEY` pelo gerenciador de segredos do Grok no ambiente do processo e configure `BROWSER_USE_PROFILE_ID` com o perfil escolhido. Não coloque valores secretos no comando, nos argumentos ou no Git.
5. Chame `navegar` uma vez com uma tarefa pública simples e confira a conclusão. Se faltar chave ou perfil, a ferramenta retorna `requires_setup` sem executar Codex ou abrir navegador.

O instalador por comando copia o código e cria os lançadores; não instala dependências, não altera o Mac nem grava a chave recebida pelo ambiente em arquivo. O runtime lê configuração privada opcional e prioriza as duas variáveis acima. A disponibilidade de credenciais no conector por comando deve ser confirmada no chat do proprietário do Grok; não há suporte multiusuário neste MVP.

## Dados que não pertencem ao repositório

Chaves API, caminho secreto do MCP, certificados/tokens do túnel, autenticação Codex, IDs de perfis reais, cookies, logs, prompts de tarefas, resultados, capturas e dados pessoais. O `.gitignore` exclui os caminhos comuns; revise os arquivos antes de qualquer commit.

A instalação em uso guarda esses dados localmente. Não é preciso apagá-los para limpar o código. Não copie a pasta privada inteira para o GitHub.

## Estado

A versão limpa está instalada no Mac e expõe somente `navegar`. Endereço, credenciais e perfil existentes foram preservados. Uma chamada MCP com Codex e Browser Use Cloud reais confirmou o resultado e o encerramento em 36,9 segundos. A ferramenta antiga específica de site foi removida.

O conector `codex-browser-command` também foi instalado e validado no computador do Grok Bot: Codex autenticado, Browser Use Cloud real, tarefa pública concluída em cerca de 18 segundos e navegador encerrado. Esse caminho usa MCP Command/stdio e dispensa o Mac e o túnel. A instalação HTTPS do Mac continua como alternativa.

MVP para uso pessoal de leitura/pesquisa. Uma VPS independente permanece [documentada como opção futura](docs/vps.md), sem implantação nesta etapa.
