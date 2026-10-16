# Technical reference

## Runtime and contract

The orchestrator launches `run-command.sh` as an MCP Command/stdio server on its own POSIX host. Stdout is reserved for MCP. The bridge starts authenticated Codex CLI on that host; Codex accesses the model remotely and controls a Cloud browser through agent-browser. No public bridge endpoint is required.

The server exposes one tool:

```text
navegar(tarefa: str, url: str)
```

```json
{
  "tarefa": "Open the page, click Learn more, and return the destination title and URL.",
  "url": "https://example.com"
}
```

`tarefa` must contain 1–6,000 characters. `url` must be a public HTTP(S) URL without credentials. Site recipes and skills are external to this connector and may be included in `tarefa`; there is no site-specific skill loader here.

A completed execution returns `status`, `result`, `final_url`, `error`, `metrics`, `browser_closed`, and `run_id`. Early refusals may contain only `status` and `error`; delivery failures may include `run_id` and cleanup state without a full result. Consumers must accept missing fields. Possible statuses and operator actions are in the [usage guide](install.md#handle-a-result).

## Execution and cleanup

Only one task can run at a time in a given runtime directory. Processes sharing that directory on the same host use a file lock, which the executor inherits. Separate runtime directories and hosts are not coordinated.

A persistent `active-run.json` marker blocks new work when cleanup is uncertain. There is no queue or automatic retry.

Codex has a 180-second deadline; preparation and cleanup add time. The adapter waits up to 300 seconds, allows up to 60 seconds for executor termination after cancellation, and attempts journal-based recovery if the executor fails. Provider cleanup requests have their own limits.

The lifecycle journal records whether browser creation never started, is in progress, has a known session, or has confirmed closure. Cleanup targets only an owned session. The adapter checks exit status, response structure, and cleanup records before delivering a result. Codex and descendants in its process group are terminated when the run finishes or times out. The MCP returns the final result after cleanup; observations and progress remain private.

Browser Use Cloud creates the browser through `POST /api/v4/browsers`. The returned identity is journaled before attaching agent-browser through `AGENT_BROWSER_CDP`; ownership is never inferred from account-wide session lists. CDP disconnect alone does not stop the Cloud browser: cleanup explicitly stops the recorded ID through the provider API and checks its status. If creation returns no usable identity, the outcome remains uncertain and new work is blocked.

A temporary browser uses the configured persistent Cloud profile. Login and MFA preparation are manual and separate; see [site login](install.md#prepare-a-site-login).

## Scope enforcement

The bridge is designed for read-only browser research. Enforcement combines agent instructions with a browser-command wrapper; it does not guarantee that browser actions are read-only.

- `app/server.py` advertises read/search only in MCP instructions. It checks task length and the initial URL, but does not classify request text or reject change requests itself. `app/executor.py` repeats input validation and appends the task to `app/executor-policy.txt`; that policy tells Codex to restrict clicks to navigation, typing and Enter to search, treat page content as untrusted, and return `out_of_scope` for change requests. Those semantic decisions depend on the agent following instructions.
- Setup generates `commands/agent-browser` to invoke `app/browser_cli.py`. The wrapper allows `open`, `snapshot`, `click`, `fill`, `press`, `scroll`, `scrollintoview`, `wait`, `back`, `forward`, `reload`, `get`, and `is`. It validates explicit `open` URLs, limits `get` to `url`/`title`/`text` and `press` to `Enter`, and rejects dash-prefixed arguments except snapshot flags `-i`/`-c`. It does not inspect clicked elements or filled fields, or verify that an action is navigation/search. Allowed clicks, typing, and Enter can still change site data.
- The wrapper is not a shell-command allowlist for Codex. The executor prepends its directory to the inherited PATH and instructs Codex to use the wrapper's absolute path; it does not make other executables inaccessible. Codex is launched with `--ignore-user-config`, `--ephemeral`, `--skip-git-repo-check`, `--approve-for-me`, and `sandbox_workspace_write.network_access=true`. The bridge does not explicitly select a `--sandbox` mode or install a read-only execution policy. These flags do not enforce read-only browser actions.
- `app/navigation_guard.py` checks URL syntax, credentials, selected local hostnames, and literal non-global IP addresses for initial URLs and wrapper `open` calls. It does not resolve DNS or mediate links, redirects, or every browser request. Setup sets `allowFileAccess: false`, `plugins: []`, `autoConnect: false`, and `restoreSave: never` in the browser configuration; the transport binds commands to the recorded active browser. These are separate connection/configuration checks, not semantic read-only enforcement.
- The response schema, final-URL comparison, deadlines, locks, and cleanup checks validate output or lifecycle behavior; they do not audit whether earlier browser actions changed data. A tested refusal to publish is evidence for that request, not a guarantee for arbitrary requests.

This is not a security sandbox. Operators who change configuration or code can expand the scope.

## Source map

| File | Responsibility |
| --- | --- |
| `app/server.py` | MCP contract, concurrency, and final delivery. |
| `app/executor.py` | Codex execution, metrics, and browser lifecycle. |
| `app/lifecycle.py` | Private journal and owned-session cleanup recovery. |
| `app/browser.py`, `app/browser_cli.py` | Cloud connection and allowed browser commands. |
| `app/navigation_guard.py` | Navigation URL checks. |
| `app/executor-policy.txt` | Generic read/research instructions. |
| `app/schema.json` | Model response format; the executor adds metrics and cleanup state. |
| `app/diagnostics.py` | Local configuration and CLI compatibility checks. |
| `scripts/setup_command.py` | Dependency installation and private runtime preparation. |
| `scripts/readiness_check.py` | Bounded real-use acceptance and fault injection; isolated development runtimes only. |

Dependencies are recorded in `dependencies.json` and `requirements.txt`: Codex 0.162.1, agent-browser 0.39.1, and MCP Python SDK 2.1.1. Setup reuses existing CLIs; recorded versions are installation defaults, not an automatic version migration.

## Private state and boundaries

Keep API keys, Codex authentication, real profile/session IDs, cookies, prompts, results, screenshots, and logs outside Git. The runtime is private and outside the source tree. `.gitignore` protects common paths but does not replace reviewing a commit.

The scope controls described above are not a security sandbox. URL checks and structured results do not prove semantic correctness or that every click is harmless. Tokens describe Codex usage only, not orchestrator consumption.

The lock is local to one runtime on one POSIX host. There is no distributed coordination or multiuser isolation. Total host loss or an unavailable provider can prevent immediate browser shutdown. Uncertain creation or cleanup must block new work until [operator recovery](install.md#unconfirmed-cleanup); never remove a marker merely to bypass the block. See [reliability](reliability.md) for the evidence and untested scenarios.
