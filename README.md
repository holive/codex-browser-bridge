# Codex Browser Bridge

Let Grok Bot delegate browser tasks to Codex using your existing ChatGPT subscription. Send a task and a URL; Codex handles the navigation in Browser Use Cloud, closes the browser, and returns one final result.

## Why use it?

I built this because browser tasks were expensive in my Grok Bot usage, while I already had access to Codex through a subscription. The bridge lets the orchestrator delegate the browsing work and receive the answer when it is done.

Codex handles the clicks, searches, and page observations. The orchestrator does not need to make each browsing decision or follow the execution step by step. Reducing cost is the motivation; actual savings have not been measured. Codex subscription limits and Browser Use Cloud charges still apply.

## One task, one result

Ask Maestro, the orchestrator in Grok Bot:

> Use codex-browser-command to open https://example.com, click “Learn more,” and return the destination page's title and URL. Wait and give me only the final result.

Or try a research task:

> Use codex-browser-command to open https://news.ycombinator.com/ and return the titles and links of the first three stories. Give me only the final result.

Maestro calls `navegar(tarefa, url)` once and waits. The tool name and parameter names remain in Portuguese; task instructions can be written in English.

## How it works

```text
Grok Bot / Maestro → MCP bridge → Codex CLI → agent-browser → Browser Use Cloud
Grok Bot / Maestro ← final result and metrics, after browser cleanup
```

The bridge and Codex CLI run on the Grok Bot computer. Codex accesses the model remotely; Browser Use Cloud hosts the browser. The MCP connection uses Command/stdio, so this setup needs no public bridge endpoint or tunnel.

Each task uses a temporary browser with a persistent Cloud profile. To use an authenticated site, log in manually in that same remote profile first, complete any MFA, and close the preparation session. Later tasks reuse the saved login until the site expires or revokes it. Logging in through your regular browser does not authenticate the Cloud profile.

Website instructions and skills belong outside this connector and can be passed in the task. There is no separate MCP tool or built-in recipe for each site.

## Get started

You need a POSIX host (tested on Linux), Python 3.11+, and Node.js 20+ with npm to install missing CLIs. You also need authenticated Codex access, a Browser Use Cloud API key, and a Cloud profile.

From the repository directory:

```sh
python3 scripts/setup_command.py --home /workspace/codex-browser-bridge-runtime
```

Choose a private, durable runtime directory outside the repository. The installer prepares dependencies and generates `run-command.sh`; rerunning it preserves existing private configuration.

Then:

1. Authenticate Codex on that host.
2. Provide `BROWSER_USE_API_KEY` and `BROWSER_USE_PROFILE_ID` through the private environment of the MCP process, or its private runtime configuration. Keep them out of tasks and Git.
3. Register the generated launcher as an MCP Command/stdio connector, named `codex-browser-command`, with no arguments.
4. Run the launcher with `--check`, then send the example.com task above once.

See the [installation guide](docs/install.md) for recovery, diagnostics, and adapting to platform updates.

## Scope and validation

This is a working MVP for **reading and research**: opening pages, following links, scrolling, and filling searches. Editing data, publishing, messaging, purchases, and deletions are outside its scope. It runs one task per runtime at a time, with no queue or automatic retries.

The latest real integration battery passed **11/11 cases** through MCP, Codex, and Browser Use Cloud on the Grok Bot computer:

- Public navigation, search, saved login, missing information, and refusal to publish.
- Controlled SIGTERM and SIGKILL interruptions of owned executors, with browser shutdown confirmed.
- A concurrent request returned `busy` without starting another execution.
- All task browsers were confirmed stopped by the provider; no cleanup remained pending.

The cases took about **170 seconds of combined execution**. Saved login worked across two queries roughly **32 minutes apart**. The final round was advanced at the user's request; this was not a 55-minute persistence test. See the [reliability report](docs/reliability.md) for timings, token measurements, the runner bug found and fixed, and the limits of these results.

If browser cleanup cannot be confirmed, the bridge reports the failure and blocks further work until an operator resolves it. The read/research policy is not a security sandbox or a guarantee that every answer is correct. Multiuser isolation, distributed coordination, general reliability rates, and orchestrator token savings have not been demonstrated.

## Further documentation

The supporting guides are currently in Portuguese.

- [Installation and recovery](docs/install.md): prerequisites, configuration, diagnostics, and updates.
- [Usage and login](docs/usage.md): requests, manual authentication, return statuses, and uncertain cleanup.
- [Technical reference](docs/technical.md): MCP contract, implementation, process supervision, and private data.
- [Architecture](docs/architecture.mmd): components and responsibilities in Mermaid.
- [Reliability](docs/reliability.md): real integration results, fault handling, and known limits.
- [Earlier validation](docs/validation.md): previous observations and test boundaries.
- [Optional VPS deployment](docs/vps.md): future independent hosting; not required for the current setup.
