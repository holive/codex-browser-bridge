# Instalar ou recuperar a ponte

O objetivo é preparar um executor no computador do Grok, disponibilizar sua configuração privada e cadastrar um MCP por comando. Telas e mecanismos de segredos podem mudar; o contrato abaixo é o que precisa continuar funcionando.

## 1. Preparar o computador

Obtenha este repositório privado em uma pasta durável. É necessário acesso ao GitHub privado, um host POSIX (Linux no ambiente implantado), Python 3.11+ e, para instalar os CLIs ausentes, Node.js 20+ com npm. Use os mecanismos disponíveis na versão atual do Grok para esses requisitos.

Na pasta do repositório, execute:

```sh
python3 scripts/setup_command.py --home /workspace/codex-browser-bridge-runtime
```

O caminho é um exemplo: escolha uma pasta privada e durável **fora do repositório**. O instalador cria o ambiente Python, instala as dependências, instala Codex e agent-browser se ausentes e gera `run-command.sh`. Executáveis existentes são reutilizados; `--codex /caminho` e `--agent-browser /caminho` permitem escolhê-los explicitamente. O mesmo comando pode reparar ou atualizar o código sem zerar configuração privada, autenticação Codex ou perfil Cloud.

O relatório JSON informa o comando MCP e as pendências. Saídas: `0` = requisitos locais prontos; `1` = instalação preparada, mas há requisito pendente; `2` = preparação falhou. O diagnóstico não chama modelo nem abre navegador.

## 2. Concluir as ações privadas

- Autentique o Codex **nesse host**, pelo fluxo suportado pela versão instalada. O instalador verifica o estado, sem copiar autenticação de outra máquina.
- Disponibilize `BROWSER_USE_API_KEY` e `BROWSER_USE_PROFILE_ID` no ambiente do processo MCP pelo armazenamento privado da plataforma. O `config.json` privado do runtime também é aceito; variáveis de ambiente têm prioridade. Não envie valores em tarefas, argumentos, Git ou mensagens.
- Para reutilizar logins Cloud, mantenha o mesmo perfil e uma conta/chave com acesso a ele. Recriar o código não recupera um perfil apagado. Login em sites segue o [fluxo manual separado](usage.md#login-em-outro-site).

O instalador não grava segredos vindos do ambiente. Valores existentes na configuração privada são preservados.

## 3. Cadastrar o MCP

Use o mecanismo MCP disponível na versão atual do Grok:

| Campo | Valor esperado |
| --- | --- |
| Nome sugerido | `codex-browser-command` |
| Transporte | Command / stdio |
| Comando | Caminho absoluto de `run-command.sh`, retornado pelo instalador |
| Argumentos | Nenhum |
| Segredos | Chave e perfil disponíveis **no processo MCP**, não só no terminal |
| Ferramenta | `navegar(tarefa, url)` |

Se a interface do Grok mudar, adapte o cadastro a esse contrato. Não reproduza obrigatoriamente uma sequência antiga de cliques. Evite conectores duplicados para a mesma ponte.

## 4. Conferir uma vez

Execute `run-command.sh --check` no mesmo ambiente que fornecerá os segredos ao MCP. Ele verifica dependências, autenticação local, presença de configuração e opções necessárias das CLIs, sem mostrar valores secretos. `ready` confirma somente requisitos locais; não valida remotamente chave, perfil ou acesso ao modelo.

Depois faça uma única tarefa real pelo conector:

> Use codex-browser-command para abrir https://example.com, clicar em Learn more e retornar título e URL de destino. Aguarde apenas o resultado final.

Resultado esperado: `succeeded`, título `Example Domains`, URL da IANA e `browser_closed: true`. Se funcionar, não precisa repetir uma bateria de testes.

## Quando alguma versão mudar

Versões para instalar CLIs ausentes ficam em `dependencies.json`; dependências Python ficam em `requirements.txt`. Executáveis já instalados não são atualizados/rebaixados automaticamente. O diagnóstico avisa se diferem das versões registradas e verifica as opções exigidas. Isso detecta incompatibilidades básicas, não toda mudança de comportamento.

Modelo e esforço ficam no `config.json` privado (`codex_model` e `codex_reasoning_effort`); padrões em `config.example.json`. Flags Codex pertencem a `app/executor.py`; conexão Browser Use pertence a `app/browser.py`. Consulte a ajuda/documentação atual do componente afetado para adaptar essa parte, preservando as proteções.

Para recuperar após perder o computador: obtenha o repositório, rode o instalador, autentique o Codex, forneça chave e referência ao perfil, cadastre o comando e confirme uma tarefa. Logs antigos não são requisitos de recuperação.
