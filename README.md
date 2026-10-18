# Codex Browser Bridge

Delegate browser navigation, reading, and search to Codex in one MCP call.

An orchestrator sends a task and a starting URL. Codex navigates and gathers the answer in a browser running in Browser Use Cloud; the bridge handles cleanup before returning the final result.

## Why

I built this to cut cost: Grok Bot’s in-app browser agent is excellent, but expensive when I rely heavily on browser navigation for tools without an API or MCP. I couldn’t find an existing tool that offloads that navigation from inside the orchestrator to an external browser driven by Codex, so this bridge moves the work to Codex plus a cloud browser with one orchestrator call.

## One task, one result

Use the bridge to read pages, follow links, or search for information without having your orchestrator direct each browser step. Send the question once and wait for the answer.

For example, ask your orchestrator to use `<connector-name>` to open a news page and return the titles and links of its first three stories. Include the starting URL and request only the final result.

## Get started

Requirements: a POSIX host (tested on Linux), Python 3.11+, Node.js 20+ with npm, authenticated Codex access, a Browser Use Cloud API key, and a Cloud profile.

From the repository directory:

```sh
python3 scripts/setup_command.py --home "<runtime-dir>"
```

Choose a private, durable runtime directory outside the repository. Then authenticate Codex on that host, provide the Cloud key and profile privately, and register the generated `run-command.sh` as an MCP Command/stdio connector named `<connector-name>`.

Follow the [installation and usage guide](docs/install.md) for configuration, the first task, site login, recovery, updates, and rollback.

## Scope and limits

The intended scope is read-only browser research. Agent instructions require refusal of requests to edit, publish, send messages, purchase, or delete. A wrapper allowlists browser command names and some arguments, and an action guard checks each click, text entry and Enter against the live page, refusing targets that look like send, publish, delete, buy, share or similar controls. The guard works from element roles and names, so unusual labels can slip past it; it is an extra layer, not a guarantee. It is not a shell-command allowlist for Codex. This is not a security sandbox or a guarantee of read-only browser actions. Operators who change configuration or code can expand the scope. See [scope enforcement](docs/technical.md#scope-enforcement).

Tested with Grok Bot; other compatible MCP Command/stdio clients have not been validated. See the [technical reference](docs/technical.md#runtime-and-contract) for the host architecture, tool contract, and integration boundaries.

Each task creates a temporary Cloud browser using a persistent profile. One task runs at a time per runtime, with no queue or automatic retry. If browser shutdown cannot be confirmed, the bridge reports failure and blocks new tasks until an operator resolves cleanup. See the installation guide for [site login](docs/install.md#prepare-a-site-login) and [profile usage and recovery](docs/install.md#handle-a-result).

Cost savings have not been measured. Codex usage limits and Browser Use Cloud charges still apply.

An independent person's first installation remains untested. See [Reliability and limits](docs/reliability.md) for validation results, conditions, and remaining gaps; these checks do not establish a general success rate or multiuser isolation.

## Documentation

- [Install and use](docs/install.md): setup, requests, login, and operational recovery.
- [Technical reference](docs/technical.md): MCP contract, components, and private state.
- [Architecture](docs/architecture.mmd): the flow in Mermaid.
- [Reliability](docs/reliability.md): measured results and remaining limits.

## License

[MIT](LICENSE). The license covers this repository; external tools and services retain their own terms and licenses.
