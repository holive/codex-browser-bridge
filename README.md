# Codex Browser Bridge

Delegate browser navigation, reading, and search to Codex in one MCP call.

An orchestrator like Grok Bot sends a task and a starting URL. Codex navigates and gathers the answer in a browser running in Browser Use Cloud; the bridge handles cleanup before returning the final result.

## One task, one result

Use the bridge to read pages, follow links, or search for information without having your orchestrator direct each browser step. Send the question once and wait for the answer.

For example, ask Grok Bot / Maestro to use `codex-browser-command` to open a news page and return the titles and links of its first three stories. Include the starting URL and request only the final result.

## Get started

Requirements: a POSIX host (tested on Linux), Python 3.11+, Node.js 20+ with npm, authenticated Codex access, a Browser Use Cloud API key, and a Cloud profile.

From the repository directory:

```sh
python3 scripts/setup_command.py --home /workspace/codex-browser-bridge-runtime
```

Choose a private, durable runtime directory outside the repository. Then authenticate Codex on that host, provide the Cloud key and profile privately, and register the generated `run-command.sh` as an MCP Command/stdio connector named `codex-browser-command`.

Follow the [installation and usage guide](docs/install.md) for configuration, the first task, site login, recovery, updates, and rollback.

## Scope and limits

The intended scope is read-only browser research. Agent instructions require refusal of requests to edit, publish, send messages, purchase, or delete. A wrapper allowlists browser command names and some arguments, but does not determine whether clicks or typing change site data. It is not a shell-command allowlist for Codex. This is not a security sandbox or a guarantee of read-only browser actions. Operators who change configuration or code can expand the scope. See [scope enforcement](docs/technical.md#scope-enforcement).

The bridge uses Codex CLI and agent-browser on the host that launches the MCP server; no public bridge endpoint or tunnel is required. The tool is `navegar(tarefa, url)`; task instructions may be in English. Grok Bot / Maestro is the tested orchestrator; other compatible MCP Command/stdio clients have not been validated. Replacing Codex CLI or the browser backend requires integration changes.

Each task creates a temporary Cloud browser using a persistent profile. Prepare site logins manually in that profile. One task runs at a time per runtime, with no queue or automatic retry. Use one account/profile per installation and avoid simultaneous use of that profile from separate runtimes. If browser shutdown cannot be confirmed, the bridge reports failure and blocks new tasks until an operator resolves cleanup.

Cost reduction motivated moving browser work to existing Codex subscription access; savings have not been measured. Codex usage limits and Browser Use Cloud charges still apply.

Reported validation includes 11/11 real integration cases, 6/6 release-candidate acceptance journeys, a concurrent request returning `busy`, and source rollback/update followed by real navigation tasks. Task browsers were confirmed stopped in these checks. An independent person's first installation remains untested. These results do not establish a general success rate, cost savings, multiuser isolation, or behavior during a whole-host failure or real provider-wide outage. See [Reliability and limits](docs/reliability.md) for conditions and remaining gaps.

## Documentation

- [Install and use](docs/install.md): setup, requests, login, and operational recovery.
- [Technical reference](docs/technical.md): MCP contract, components, and private state.
- [Architecture](docs/architecture.mmd): the flow in Mermaid.
- [Reliability](docs/reliability.md): measured results and remaining limits.

## License

[MIT](LICENSE). The license covers this repository; external tools and services retain their own terms and licenses.
