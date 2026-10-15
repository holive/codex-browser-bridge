# Codex Browser Bridge

An MCP bridge for delegating browser tasks to a dedicated execution agent. Send a task and a URL; the agent navigates, closes the browser, and returns one final result.

**Current implementation:** Codex CLI + agent-browser + Browser Use Cloud. **Tested orchestrator:** Grok Bot / Maestro. Codex can use your existing ChatGPT subscription.

## One task, one result

Ask Maestro in Grok Bot:

> Use codex-browser-command to open https://example.com, click “Learn more,” and return the destination page's title and URL. Wait and give me only the final result.

Or:

> Use codex-browser-command to open https://news.ycombinator.com/ and return the titles and links of the first three stories. Give me only the final result.

The orchestrator calls `navegar(tarefa, url)` once. Codex handles the clicks, searches, and observations; the orchestrator waits for the answer. Task instructions can be in English; the tool and parameter names remain in Portuguese.

## Why this exists

Browser tasks were expensive in my Grok Bot usage, while I already had access to Codex through a subscription. This bridge delegates the browsing work to Codex. Reducing cost is the motivation; actual savings have not been measured. Codex subscription limits and Browser Use Cloud charges still apply.

```text
Grok Bot / Maestro → MCP Command → Codex CLI → agent-browser → Browser Use Cloud
Grok Bot / Maestro ← one final result, after browser cleanup
```

The layers are an orchestrator, an execution agent, and browser infrastructure. Any MCP client capable of launching this Command/stdio server on a compatible host can be an orchestrator; Grok Bot is the validated client today. Replacing Codex CLI or Browser Use Cloud would require integration changes. Alternative execution agents and browser backends are not implemented.

The bridge and Codex CLI run on the host that launches the MCP server; the validated deployment uses the Grok Bot computer. Codex accesses the model remotely; Browser Use Cloud hosts the browser. Command/stdio needs no public bridge endpoint or tunnel.

Each task uses a temporary browser with a persistent Cloud profile. Log into sites manually in that remote profile first; later tasks reuse the login until the site expires or revokes it. Website instructions and skills belong outside this connector and can be passed in the task.

## Get started

Requirements: a POSIX host (tested on Linux), Python 3.11+, Node.js 20+ with npm, authenticated Codex access, a Browser Use Cloud API key, and a Cloud profile.

From the repository directory:

```sh
python3 scripts/setup_command.py --home /workspace/codex-browser-bridge-runtime
```

Choose a private, durable runtime directory outside the repository. Then authenticate Codex on that host, provide the Cloud key and profile privately, and register the generated `run-command.sh` as an MCP Command/stdio connector named `codex-browser-command`.

Follow the [installation and usage guide](docs/install.md) for configuration, the first task, site login, recovery, updates, and rollback.

## Scope and evidence

This connector supports **reading and research**: opening pages, following links, scrolling, and filling searches. Editing data, publishing, messaging, purchases, and deletions are outside its scope. It runs one task per runtime at a time, with no queue or automatic retries.

The real integration battery passed **11/11 cases** through MCP, Codex, and Browser Use Cloud on the Grok Bot computer. It covered public navigation, search, saved login, missing information, refusal to publish, executor interruptions, and a concurrent request. All task browsers were confirmed stopped by the provider. Login was reused about **32 minutes** between queries. See [reliability and limits](docs/reliability.md).

The release candidate also passed six real-use acceptance journeys from a new isolated runtime, including recovery after owned process loss and a simulated cleanup API outage. Source rollback and update were confirmed with a real task after each. Authentication and CLI binaries were inherited; an independent person's first installation remains to be checked.

If browser cleanup cannot be confirmed, the bridge reports failure and blocks further work until an operator resolves it. The read/research policy is not a security sandbox. Multiuser isolation, distributed coordination, general reliability rates, and orchestrator token savings have not been demonstrated.

## Documentation

- [Install and use](docs/install.md): setup, requests, login, and operational recovery.
- [Technical reference](docs/technical.md): MCP contract, components, and private state.
- [Architecture](docs/architecture.mmd): the flow in Mermaid.
- [Reliability](docs/reliability.md): measured results and remaining limits.

## License

[MIT](LICENSE). The license covers this repository; external tools and services retain their own terms and licenses.
