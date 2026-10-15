"""Serial stdio MCP with an inherited host lock and fail-closed lifecycle journal."""
import asyncio
import fcntl
import json
import os
from pathlib import Path
import sys
import time
import uuid
from mcp.server import MCPServer
from runtime import ROOT, CONFIG
from lifecycle import read_journal, recover

os.umask(0o077)
server = MCPServer('codex-browser-bridge', version='0.9.0-rc.1', instructions='Use navegar(tarefa,url) only for read/search. No editing, publishing, messages, purchases or deletion. Return only the final result. Do not poll or retry automatically. Never send credentials in task text.')
lock = asyncio.Lock()
EXECUTOR_TIMEOUT = 300
CANCEL_GRACE = 60


@server.tool()
async def navegar(tarefa: str, url: str) -> dict:
    """Delegate read/search to Codex and return only its final result after browser cleanup. One task at a time. Never include credentials. requires_auth means manual login is needed; out_of_scope means changes are forbidden. Never retry cleanup_pending automatically."""
    if not tarefa.strip() or len(tarefa) > 6000:
        return {'status': 'failed', 'error': 'Task must contain 1-6000 characters'}
    from navigation_guard import check_url
    try: check_url(url)
    except ValueError: return {'status': 'failed', 'error': 'Use a public HTTP(S) URL without credentials'}
    if not CONFIG.get('browser_use_api_key') or not CONFIG.get('profile_id'):
        return {'status': 'requires_setup', 'error': 'Provide BROWSER_USE_API_KEY and BROWSER_USE_PROFILE_ID privately to the MCP process.'}
    return await dispatch({'task': tarefa, 'url': url})


def valid_result(result):
    return (isinstance(result, dict) and result.get('status') in {'succeeded', 'failed', 'requires_auth', 'out_of_scope', 'timed_out'}
            and all(isinstance(result.get(k), str) for k in ('result', 'final_url', 'error'))
            and isinstance(result.get('metrics'), dict) and type(result.get('browser_closed')) is bool
            and (result['status'] not in {'succeeded', 'requires_auth', 'out_of_scope'} or result['browser_closed']))


async def dispatch(request):
    if lock.locked():
        return {'status': 'busy', 'error': 'Another task is running. Do not poll or retry automatically.'}
    async with lock:
        lease = (ROOT / 'executor.lock').open('a')
        try:
            try: fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: return {'status': 'busy', 'error': 'Another MCP process owns this runtime. Do not retry automatically.'}
            active = ROOT / 'active-run.json'
            if active.exists():
                return {'status': 'busy', 'cleanup_pending': True, 'error': 'Previous cleanup is unconfirmed. Inspect the private active-run.json and Cloud session before allowing another task.'}
            run_id = time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:12]
            state = ROOT / 'runs' / run_id
            state.mkdir(mode=0o700)
            active.write_text(json.dumps({'run_id': run_id}))
            started = time.monotonic()
            proc = None
            env = dict(os.environ, BROWSER_EXECUTOR_STATE=str(state), BROWSER_EXECUTOR_SESSION=run_id)
            try:
                with (state / 'executor-stderr.log').open('wb') as err:
                    # Child holds this same lock even if the MCP parent disappears.
                    proc = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'app/executor.py'), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=err, env=env, pass_fds=(lease.fileno(),))
                    output, _ = await asyncio.wait_for(proc.communicate(json.dumps(request).encode()), timeout=EXECUTOR_TIMEOUT)
                if proc.returncode != 0:
                    raise ValueError('Executor exited unsuccessfully')
                lines = [line for line in output.decode().splitlines() if line.strip()]
                if len(lines) != 1:
                    raise ValueError('Expected one final result')
                result = json.loads(lines[0])
                if not valid_result(result):
                    raise ValueError('Invalid final result')
                journal = read_journal(state)
                if result['browser_closed'] and (journal.get('phase') != 'closed' or not journal.get('browser_closed')):
                    raise ValueError('Result disagrees with cleanup journal')
                result['run_id'] = run_id
                (state / 'delivery.json').write_text(json.dumps({'elapsed_seconds': round(time.monotonic() - started, 3), 'stdout_lines': 1, 'returncode': proc.returncode, 'result': result}, ensure_ascii=False, indent=2))
                return result
            except BaseException as exc:
                if proc is not None and proc.returncode is None:
                    proc.terminate()
                    try: await asyncio.wait_for(proc.wait(), timeout=CANCEL_GRACE)
                    except asyncio.TimeoutError: proc.kill(); await proc.wait()
                closed, pending = False, proc is not None
                if proc is not None:
                    try: closed, pending = await asyncio.to_thread(recover, state, run_id)
                    except Exception: pass
                (state / 'delivery-error.json').write_text(json.dumps({'type': type(exc).__name__, 'browser_closed': closed, 'cleanup_pending': pending}))
                if isinstance(exc, asyncio.CancelledError):
                    raise
                return {'status': 'timed_out' if isinstance(exc, asyncio.TimeoutError) else 'failed', 'run_id': run_id, 'browser_closed': closed, 'cleanup_pending': pending, 'error': 'Executor/delivery failed (' + type(exc).__name__ + '). Do not retry automatically.'}
            finally:
                try:
                    journal = read_journal(state)
                    safe = journal['phase'] == 'not_started' or (journal['phase'] == 'closed' and journal.get('browser_closed'))
                except Exception:
                    safe = proc is None
                if safe:
                    active.unlink(missing_ok=True)
        finally:
            # Do not LOCK_UN: the executor may still hold the inherited descriptor.
            lease.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--transport', choices=['stdio'], default='stdio')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        from diagnostics import diagnose
        report = diagnose(ROOT)
        print(json.dumps(report, ensure_ascii=False))
        sys.exit(0 if report['status'] == 'ready' else 1)
    server.run(transport='stdio')
