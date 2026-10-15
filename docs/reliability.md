# Reliability and limits

These observations describe the tested scenarios, not a general success rate or a security certification. Full reports, account data, session identifiers, and logs remain private.

## Real integration battery — 2026-10-15

**11/11 cases passed** through MCP Command, Codex CLI, agent-browser, and Browser Use Cloud on the Grok Bot Linux host, using runner commit `bd29ef8`. Each task browser was confirmed stopped independently through the provider API. No `cleanup_pending` or active-run marker remained at the end.

| Scenario | Calls | Expected outcome observed |
| --- | ---: | --- |
| Public page → link → destination | 3 | Correct title and final URL. |
| Public search | 2 | Requested destination reached. |
| Query using a saved login | 2 | Authenticated without another login. |
| Information absent from the page | 1 | Reported missing information. |
| Request to publish a change | 1 | `out_of_scope`; no change made. |
| Owned executor interrupted with SIGTERM | 1 | `timed_out`; browser stopped. |
| Owned executor killed with SIGKILL | 1 | `failed`; recovery stopped the browser. |

A separate concurrent MCP request during the interruption scenario returned `busy` without admitting another execution. The orchestrator initiated the battery and read status; Codex handled the browsing decisions.

- Combined execution time: approximately **170 seconds**, excluding waits and coordination.
- Saved-login queries: **31 minutes 46.9 seconds between starts**. The final round was advanced at the user's request; this was not a 55-minute persistence test.
- Known Codex usage: **571,514 input tokens**, including **422,144 cached** and **149,370 uncached**; **2,088 output tokens**.
- The two interrupted runs did not report usage. Their consumption is **unknown**, excluded from those totals; it must not be reported as zero. Orchestrator usage and cost savings were not measured.

The first launch exposed a runner compatibility bug before any `navegar` call: it used camelCase MCP result attributes rather than the Python SDK's snake_case attributes. The runner was corrected, checked with a real MCP handshake without model/Cloud, and resumed once. Original evidence was preserved. The final three cases were run by a private continuation after confirming the original runner was idle and cleanup complete; previous results and the global 11-call limit were preserved.

## Other supporting checks

Earlier real calls confirmed public navigation, saved authentication, and refusal to publish: **3/3 passed**, all browsers stopped. They are additional evidence, not part of the 11 cases above.

The installer was exercised in a new isolated directory with spaces in its path, real dependencies, and an already authenticated Codex. Real MCP handshake and a missing-configuration response worked without model/Cloud. Reinstallation preserved fictitious private settings, did not save environment secrets, and rejected an incompatible fake CLI. The installer was also applied to the existing Grok runtime, preserving its private configuration and followed by one successful public task. **This was not an independent person's installation or a fresh Codex authentication.**

A supporting suite passed **21/21 checks** in development and on Grok Linux. It used real processes with substitute model/provider implementations to exercise locks, cancellation, timeouts, invalid output, descendant cleanup, and uncertain creation. These checks supplement the real use cases; they do not establish Cloud behavior. Run with `python3 -m unittest discover -s tests -v` if needed for development.

## Release-candidate acceptance — 2026-10-15

Candidate `b3b238a` was installed into a new isolated Linux runtime on the Grok host using the installation guide. Codex authentication, CLI binaries, and the existing private Cloud profile were inherited; the Python environment, application copy, configuration file, and launcher were newly prepared. Local diagnostics returned `ready` with all 14 checks passing and no warnings.

The real MCP acceptance runner passed **6/6 user journeys in 98.6 seconds**:

| Journey | Time | Observed behavior |
| --- | ---: | --- |
| Public page → link → destination | 19.1 s | Correct title/URL; recorded browser stopped. |
| Saved login | 14.1 s | Authenticated without logging in again or returning account data. |
| Loss of the owned MCP/executor/model processes | 3.6 s | Restarted MCP blocked new work; operator recovery confirmed stop before releasing the marker. |
| Navigation after process recovery | 21.7 s | A fresh request succeeded and its browser stopped. |
| Simulated provider unavailability during cleanup | 21.5 s | Returned failure with pending cleanup; refused another task; recovered the recorded browser after restoring the API boundary. |
| Navigation after provider recovery | 17.9 s | A fresh request succeeded and its browser stopped. |

The faults used real MCP, Codex, and Cloud sessions. Process loss was injected only into verified owned processes in the isolated runtime; the shared computer was not rebooted. Provider unavailability was injected at the private transport boundary; Browser Use Cloud itself was not taken offline. The private transport file was restored after the run. The runtime ended with no pending cleanup or active marker.

Known Codex usage: **350,086 input**, **267,392 cached**, **82,694 uncached**, and **1,397 output tokens**. The interrupted process-loss case has unknown usage and is excluded from these totals. This candidate records the browser ID directly from the creation response before CDP attachment; it does not infer ownership from session-list differences.

A separate empty-runtime setup on the development host also returned an honest `requires_setup` when Cloud credentials were missing; a real MCP handshake and tool call confirmed that response without starting a browser or model. This and the Linux run are installation simulations with inherited authentication, not an independent person's first installation.

## Update and rollback rehearsal

On the same isolated Linux runtime, setup was run from previous source commit `30ba7c4`, followed by `--check` and one real MCP navigation: **passed in 21.3 s**. Candidate `b3b238a` was then reinstalled and the same check/navigation passed in **18.9 s**. Both returned the expected IANA title/URL and confirmed browser shutdown, with no pending marker. The Cloud key, profile, model, and reasoning setting remained unchanged in both steps. Exactly two additional Codex tasks were used; installed CLI versions and authentication were inherited, not migrated.

## Existing connector deployment

Candidate `b3b238a` was applied to the existing Grok runtime with its key, profile, model, reasoning setting, and MCP registration preserved. Local diagnostics returned `ready`. A single task through Maestro's actual connector returned **Example Domains** and the IANA destination in **17.2 s** (`succeeded`, `browser_closed: true`, `cleanup_pending: false`). Codex usage: 75,488 input / 59,264 cached / 16,224 uncached / 308 output tokens. The platform's available reload operation reconnected all existing MCP connectors; it created no connector or permission. This exposed an update pitfall: reconnecting retained the old idle MCP processes, so their loaded server version was not confirmed by that call. An old server can launch an updated executor from disk; the first call alone does not establish which server version was loaded. The installation guide now requires actual process shutdown before replacement and a version check after restart.

The two verified idle bridge processes were then terminated and the existing connector started one new process after installation. Its real task passed in **18.4 s** with provider-confirmed stop, no pending cleanup, and no active marker. Known usage: **75,451 input / 59,264 cached / 16,187 uncached / 299 output tokens**. The client did not expose its server handshake version; the loaded candidate was established from the installed source and verified process replacement, rather than claiming unavailable metadata. The isolated runtime ended with no task processes, and only its copied Cloud key/profile were removed; production configuration remained intact.

## Reproduce the acceptance checks

`scripts/readiness_check.py` is a development runner, not part of the installed MCP runtime. Use a separate Linux runtime prepared by setup, with its own private configuration and a `readiness-isolated.json` file containing `{"purpose":"readiness-check"}`. Run it with that runtime's Python and `--home`; add `--authenticated-url` only for a saved-login check. It admits at most six real Codex/Cloud tasks, writes a private report, injects faults only into owned processes/private transport, and stops on uncertain cleanup. Its final `cleanup_pending` must be false before retiring the test runtime. Never run this fault exercise against a shared production runtime.

## Current operating limits

- One account/profile and one runtime on one host. Locks do not coordinate different hosts or runtime directories.
- Current code records the exact ID returned by Cloud creation and attaches to that browser. Creation can still have an unknown outcome if the request fails before returning an ID; this blocks further tasks and requires provider-side inspection. Avoid simultaneous use of the same saved profile from separate runtimes.
- Actual whole-host reboot and a real provider-wide outage have not been exercised. The isolated process-loss and simulated transport-outage checks above confirmed blocking and operator recovery at those boundaries; immediate remote shutdown during loss of connectivity cannot be promised.
- An independent person's first installation remains pending. Fresh-runtime installation and source rollback/update were exercised with inherited authentication and existing CLIs; new-account authentication and dependency migrations were not rehearsed.
- Read/research rules and allowed commands are not security isolation. Data-changing business workflows and multiuser deployments are outside the validated scope.
- Correct navigation in these examples does not establish correctness for every website or answer.

If cleanup is uncertain, follow [operator recovery](install.md#unconfirmed-cleanup). Do not retry automatically or delete state to bypass the block.

## Distribution

The repository remains private. No distribution license has been selected and no public release is claimed here. Before sharing logs or publishing, inspect the actual changes for secrets and account data; a previous targeted history scan is not a guarantee for new files.
