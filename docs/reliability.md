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

## Current operating limits

- One account/profile and one runtime on one host. Locks do not coordinate different hosts or runtime directories.
- The current session identification relies on an unambiguous newly created Cloud browser. Avoid unrelated concurrent session creation with the same Cloud account during a task. Ambiguity must block continuation.
- Total host loss and provider unavailability during cleanup have **not yet been exercised in real integration**. The intended behavior is to retain the pending marker, block new work, and require operator recovery; immediate shutdown cannot be promised.
- Independent clean installation and a full update/rollback rehearsal remain pending.
- Read/research rules and allowed commands are not security isolation. Data-changing business workflows and multiuser deployments are outside the validated scope.
- Correct navigation in these examples does not establish correctness for every website or answer.

If cleanup is uncertain, follow [operator recovery](install.md#unconfirmed-cleanup). Do not retry automatically or delete state to bypass the block.

## Distribution

The repository remains private. No distribution license has been selected and no public release is claimed here. Before sharing logs or publishing, inspect the actual changes for secrets and account data; a previous targeted history scan is not a guarantee for new files.
