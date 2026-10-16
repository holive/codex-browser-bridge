# Codex Browser Bridge

Designed for read-only browser research through one MCP call to Codex. Send a task and a public URL; Codex navigates and gathers the answer, and the bridge returns the final result after browser cleanup.

Built with Codex CLI, agent-browser, and Browser Use Cloud. Tested with Grok Bot / Maestro; other compatible MCP Command/stdio clients have not been validated.

Supports reading pages, following links, scrolling, and searching. Agent instructions require refusal of requests to edit, publish, send messages, purchase, or delete. A wrapper allowlists browser command names and some arguments, but does not determine whether clicks or typing change site data. This is not a security sandbox or a guarantee of read-only browser actions. Operators who change configuration or code can expand the scope.

If browser shutdown cannot be confirmed, the bridge reports failure and blocks new tasks until an operator resolves the cleanup.

## One task, one result

Ask Maestro in Grok Bot:

> Use codex-browser-command to open https://example.com, click “Learn more,” and return the destination page's title and URL. Wait and give me only the final result.

Or:

> Use codex-browser-command to open https://news.ycombinator.com/ and return the titles and links of the first three stories. Give me only the final result.

The orchestrator calls `navegar(tarefa, url)` once. Codex handles the clicks, searches, and observations; the orchestrator waits for the answer. Task instructions can be in English; the tool and parameter names remain in Portuguese.

## Why this exists

I built this bridge to move browser work from Grok Bot to Codex, which I already accessed through a subscription. Cost reduction is the motivation; savings have not been measured. Codex usage limits and Browser Use Cloud charges still apply.

The orchestrator sends one `navegar(tarefa, url)` request. Codex handles navigation and research, and the bridge handles browser cleanup before returning the result.

Grok Bot / Maestro → MCP Command/stdio → Codex CLI → agent-browser → Browser Use Cloud

The bridge and Codex CLI run on the host that launches the MCP server. The browser runs in Browser Use Cloud; no public bridge endpoint or tunnel is required.

Each task creates a temporary browser using a persistent Cloud profile. Prepare site logins manually in that profile before requesting authenticated research.

Grok Bot / Maestro is the tested orchestrator. Other compatible MCP clients may work; replacing Codex CLI or the browser backend requires integration changes.

## Get started

Requirements: a POSIX host (tested on Linux), Python 3.11+, Node.js 20+ with npm, authenticated Codex access, a Browser Use Cloud API key, and a Cloud profile.

From the repository directory:

```sh
python3 scripts/setup_command.py --home /workspace/codex-browser-bridge-runtime
```

Choose a private, durable runtime directory outside the repository. Then authenticate Codex on that host, provide the Cloud key and profile privately, and register the generated `run-command.sh` as an MCP Command/stdio connector named `codex-browser-command`.

Follow the [installation and usage guide](docs/install.md) for configuration, the first task, site login, recovery, updates, and rollback.

## Scope and evidence

One task runs at a time in each runtime. There is no queue or automatic retry. Use one account/profile per installation, and avoid simultaneous use of the same Cloud profile from separate runtimes.

Reported validation includes:

- 11/11 real integration cases covering navigation, search, saved login, missing information, refusal to publish, and executor interruptions. A separate concurrent request returned `busy`.
- 6/6 release-candidate acceptance journeys, including recovery after owned process loss and a simulated cleanup API outage.
- Successful source rollback and update, each followed by a real navigation task.

Task browsers were confirmed stopped in these checks. Installation checks reused existing authentication and CLI binaries; an independent person's first installation remains untested.

These results do not establish a general success rate, cost savings, multiuser isolation, or behavior during a whole-host failure or real provider-wide outage. The read/research policy is not a security sandbox.

See [Reliability and limits](docs/reliability.md) for test conditions, usage figures, and remaining gaps.

## Documentation

- [Install and use](docs/install.md): setup, requests, login, and operational recovery.
- [Technical reference](docs/technical.md): MCP contract, components, and private state.
- [Architecture](docs/architecture.mmd): the flow in Mermaid.
- [Reliability](docs/reliability.md): measured results and remaining limits.

## License

[MIT](LICENSE). The license covers this repository; external tools and services retain their own terms and licenses.
