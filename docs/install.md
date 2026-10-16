# Install and use

The bridge runs beside the orchestrator on its POSIX host. The browser runs in Browser Use Cloud. This guide describes the required contract rather than a particular version of an orchestrator’s settings screen.

The bridge is designed for read-only browser research. Agent instructions require navigation/search only and refusal of change requests; a wrapper also restricts browser command names and some arguments. It does not check whether a click or text entry changes site data. This is not a security sandbox or a guarantee of read-only browser actions. Operators who change configuration or code can expand the scope. See [scope enforcement](technical.md#scope-enforcement) for the exact boundaries.

## 1. Prepare the host

Obtain the repository in a durable directory. You need Python 3.11+ and Node.js 20+ with npm to install missing CLIs. The deployed environment is Linux. Ensure Node is available on the MCP process PATH even when reusing an existing Node-based CLI; an installed executable may still need it to start.

From the repository directory:

```sh
python3 scripts/setup_command.py --home "<runtime-dir>"
```

Replace `<runtime-dir>` with an absolute path to a private, durable runtime directory **outside the repository**. If `--home` is omitted, the code defaults to `~/.local/share/codex-browser-bridge`, overridden by `CODEX_BROWSER_BRIDGE_HOME`. The installer creates the Python environment, installs missing CLIs, copies the application, and generates `run-command.sh`. Existing executables are reused; `--codex /absolute/path` and `--agent-browser /absolute/path` select them explicitly.

Rerunning setup preserves private configuration, Codex authentication, and the Cloud profile reference. It does not recover a deleted Cloud profile. Its JSON report gives the launcher path and outstanding requirements. Exit codes: `0` local requirements ready; `1` runtime prepared but setup remains incomplete; `2` preparation failed. Setup and its diagnostics do not call a model or open a browser.

## 2. Provide private access

Authenticate Codex **on this host** using its supported login flow. The installer checks local authentication; it does not copy credentials from another machine.

Provide these variables to the **MCP process**, using the platform's private environment or secret storage:

| Variable | Purpose |
| --- | --- |
| `BROWSER_USE_API_KEY` | Access to Browser Use Cloud. |
| `BROWSER_USE_PROFILE_ID` | The persistent profile this installation will reuse. |

Alternatively, set `browser_use_api_key` and `profile_id` in the runtime's private `config.json`. Environment variables take precedence. Setup preserves existing configuration but never saves secrets supplied through the environment. Keep values out of task text, command arguments, chat, and Git.

## 3. Register the connector

| Field | Value |
| --- | --- |
| Name you choose | `<connector-name>` |
| Transport | Command / stdio |
| Command | Absolute `run-command.sh` path returned by setup. |
| Arguments | None. |
| Private environment | Cloud key and profile available to this process. |
| Tool | `navegar(tarefa, url)` |

Register the connector using this contract; the exact settings labels may vary by orchestrator and version.

## 4. Confirm one real task

Run the generated launcher with `--check` in the same private environment the MCP will use. A `ready` result confirms local prerequisites only; it does not validate the Cloud key, profile, or model access remotely.

Then ask your orchestrator:

> Use `<connector-name>` to open https://example.com, click “Learn more,” and return the destination page's title and URL. Wait and give me only the final result.

Expected result: `succeeded`, title `Example Domains`, destination `https://www.iana.org/help/example-domains`, and `browser_closed: true`. A successful first task is enough to confirm a normal installation; do not repeat the development test battery.

## Everyday requests

Give a complete URL and a concrete question, without placeholders or credentials:

> Use `<connector-name>` to open https://news.ycombinator.com/ and return the titles and links of the first three stories. Give me only the final result.

The tool and its parameters retain their Portuguese names: `navegar(tarefa, url)`. Task instructions may be in English. Site-specific instructions can live in the orchestrator's skills or configuration and be included in `tarefa`; they do not need another MCP tool.

## Prepare a site login

Authenticated research uses the saved login in this installation's Browser Use Cloud profile. Logging into your ordinary browser does not authenticate that profile.

The bridge does not provide a login-window tool. An operator—the person managing the Cloud profile—must prepare the login separately. If you manage the installation yourself, you perform this role.

1. Create a Browser Use Cloud preparation session using the same profile configured for the bridge.
2. Open its remote browser window privately and complete the site's login and MFA there. Do not send credentials to the bot.
3. Close the preparation session so the profile is saved.
4. Submit a read-only task through the connector.

Repeat this preparation if the site expires or revokes the login. A `requires_auth` result ends the current task and closes its browser; it does not start an interactive login flow.

## Handle a result

| Status | Action |
| --- | --- |
| `succeeded` | Use the final answer. |
| `requires_setup` | Provide missing private configuration to the MCP process. |
| `requires_auth` | Prepare or renew the site login manually. |
| `out_of_scope` | The agent reports that the request is outside its instructed read/research scope. |
| `busy` | Wait for the active task; inspect cleanup if `cleanup_pending` is present. |
| `failed` / `timed_out` | Read the error before deciding whether to try again. |

There are no automatic retries. Use one runtime and one account/profile per installation. The lock coordinates processes using that runtime on the same host; it does not coordinate different directories or hosts.

### Unconfirmed cleanup

`cleanup_pending: true` means browser shutdown was not confirmed. Do not treat the response as success or retry automatically. The runtime remains blocked even after restarting the MCP.

The operator must inspect the private `active-run.json` and the run's `lifecycle.json`, check for remaining task processes, and stop the recorded Cloud browser if necessary. If creation returned no identity, inspect the provider dashboard and timestamps; do not guess or stop unrelated sessions. **Only after confirming that no task process or browser remains** may the operator archive `active-run.json` to release the runtime. Preserve diagnostic records privately.

## Update or roll back

Do this while no task is running. Resolve any cleanup pending before changing versions.

1. Record the current repository commit, CLI versions, and runtime path. Preserve a private backup of `config.json`; do not put it in Git.
2. Stop the connector's running bridge processes through the platform's process/restart controls and verify they actually exited. A reconnect or tool refresh may keep an old MCP process alive. Stop only this installation's idle bridge processes, never unrelated bots or pending executors.
3. Select the intended repository tag or commit and rerun setup against the **same** runtime directory.
4. Start/reconnect the existing connector, confirm its MCP `server_info.version` matches the intended release when the client exposes it, run `--check`, and confirm the example.com task once. If server metadata is unavailable, verify that the installation's old processes exited and its new process started after the intended code was installed. Checking the source file on disk alone does not confirm the loaded server version.
5. If the update fails, repeat this stop/install/start sequence using the previously recorded commit and confirm one task.

Setup reuses installed CLIs; it does not upgrade or downgrade them automatically. New installations use the versions in `dependencies.json` and `requirements.txt`. If a change requires different CLIs, install those versions explicitly and use the installer path options. Returning to an earlier source commit alone does not roll back external dependencies. The source rollback/update path was rehearsed on an isolated runtime with real tasks and preserved configuration; see [reliability](reliability.md). This does not validate a dependency-version migration.

## Recover after losing the host

Obtain the repository on a replacement POSIX host, run setup, authenticate Codex there, provide the Cloud key and existing profile reference, register the launcher, and confirm one real task. Logs from the lost host are not required for installation. Check the Cloud account for an unfinished browser from the lost task before allowing new work. Recovery of a deleted profile or expired site login requires separate manual preparation.

## When a component changes

`--check` warns about versions differing from the recorded versions and checks required CLI options. It cannot prove behavioral compatibility. Model and reasoning settings are `codex_model` and `codex_reasoning_effort` in private `config.json`; setup defaults are `gpt-6.1-sol` and `high`, respectively. See [technical reference](technical.md) for the component boundaries; adjust only the affected integration while preserving the lifecycle checks.
