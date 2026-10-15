"""Bounded user journeys on an explicitly isolated Linux runtime. Real MCP/Codex/Cloud.

Faults are a simulated loss of owned processes and a SIMULATED_OUTAGE at the private
provider transport boundary, not a real host reboot or an actual Cloud outage.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PUBLIC = {'tarefa': 'Open this page, click Learn more, and return the destination title and URL. Read only; short answer.', 'url': 'https://example.com'}


def payload(reply):
    if reply.is_error:
        raise RuntimeError('MCP tool error')
    for item in reply.content:
        if item.type == 'text':
            value = json.loads(item.text)
            if isinstance(value, dict) and 'status' in value:
                return value
    raise RuntimeError('Missing final result')


def process(pid, include_env=False):
    """A live process snapshot; zombies cannot execute work or retain open descriptors."""
    try:
        root = Path('/proc') / str(pid)
        stat = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': int(pid), 'state': stat[0], 'ppid': int(stat[1]), 'pgid': int(stat[2]),
                'args': (root / 'cmdline').read_bytes().split(b'\0'),
                'env': (root / 'environ').read_bytes().split(b'\0') if include_env else []}
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None


def members(group):
    rows = []
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            row = process(path.name)
            if row and row['pgid'] == group and row['state'] != 'Z':
                rows.append(process(path.name, include_env=True))
    return rows


class Check:
    def __init__(self, home):
        self.home = home
        self.started = time.time()
        self.out = home / 'readiness-checks' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid()))
        self.out.mkdir(mode=0o700, parents=True)
        self.report = {'status': 'running', 'started_epoch': self.started, 'max_real_calls': 6, 'cases': [],
                       'limits': ['isolated Linux runtime; inherited Codex authentication and supplied Cloud profile',
                                  'owned process loss, not an actual shared-host reboot',
                                  'SIMULATED_OUTAGE at provider API boundary, not an actual Cloud outage']}
        self.calls = 0
        self.owned = set()
        self.patch = home / 'app/browser.py'
        self.original = self.patch.read_bytes()
        self.flag = self.out / 'simulated-provider-outage'
        self.write()

    def write(self):
        self.report.update(elapsed_seconds=round(time.time() - self.started, 3), updated_epoch=time.time())
        temporary = self.out / 'report.tmp'
        temporary.write_text(json.dumps(self.report, indent=2))
        temporary.replace(self.out / 'report.json')

    def active(self):
        marker = self.home / 'active-run.json'
        if not marker.exists():
            return None
        run = json.loads(marker.read_text())['run_id']
        if not isinstance(run, str) or Path(run).name != run:
            raise RuntimeError('Invalid active run reference')
        return self.home / 'runs' / run

    def record(self, state):
        value = json.loads((state / 'lifecycle.json').read_text())
        if state not in self.owned or value.get('session') != state.name or not value.get('browser_id'):
            raise RuntimeError('Browser ownership is not established')
        return value

    def group(self, state):
        group = self.record(state).get('model_pgid')
        if not isinstance(group, int) or group <= 1 or group == os.getpgrp():
            raise RuntimeError('Invalid owned model group')
        rows = members(group)
        expected = os.fsencode('BROWSER_EXECUTOR_STATE=' + str(state))
        if any(row is None or expected not in row['env'] for row in rows):
            raise RuntimeError('Model process group ownership mismatch')
        return group, rows

    @asynccontextmanager
    async def client(self):
        with (self.out / 'mcp-stderr.log').open('a') as err:
            async with stdio_client(StdioServerParameters(command=str(self.home / 'run-command.sh'), env=dict(os.environ)), errlog=err) as streams:
                async with ClientSession(*streams) as client:
                    initialized = await client.initialize()
                    if initialized.server_info.name != 'codex-browser-bridge':
                        raise RuntimeError('Unexpected MCP server')
                    yield client

    def server(self):
        script = os.fsencode(str(self.home / 'app/server.py'))
        rows = [process(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()]
        rows = [r for r in rows if r and r['ppid'] == os.getpid() and script in r['args']]
        if len(rows) != 1:
            raise RuntimeError('MCP child is not uniquely owned')
        return rows[0]

    async def call(self, client, task):
        if self.calls >= 6:
            raise RuntimeError('Real-call budget exceeded')
        self.calls += 1
        return payload(await asyncio.wait_for(client.call_tool('navegar', task), timeout=420))

    def row(self, name):
        row = {'case': name, 'started_epoch': time.time()}
        self.report['cases'].append(row)
        self.write()
        return row

    def finish(self, row, result, state):
        from browser import api
        rec = self.record(state)
        row.update(status=result.get('status'), elapsed_seconds=round(time.time() - row['started_epoch'], 3),
                   metrics=result.get('metrics', {}), usage_known='input_tokens' in result.get('metrics', {}),
                   browser_closed=result.get('browser_closed'), cleanup_pending=result.get('cleanup_pending', False),
                   creation_identity_recorded=True,
                   provider_stop_verified=api('/browsers/' + rec['browser_id'])['status'] == 'stopped')
        self.write()

    async def normal(self, name, task, authenticated=False):
        if self.active():
            raise RuntimeError('Unconfirmed run; no new navigation')
        row = self.row(name)
        async with self.client() as client:
            result = await self.call(client, task)
        state = self.home / 'runs' / result['run_id']
        self.owned.add(state)
        self.finish(row, result, state)
        passed = result.get('status') == 'succeeded' and row['browser_closed'] is True and row['provider_stop_verified'] and not self.active()
        if authenticated:
            text = result.get('result', '').strip().lower()
            passed = passed and ('authenticated: yes' in text or 'autenticado: sim' in text)
        else:
            passed = passed and urlparse(result.get('final_url', '')).hostname in {'www.iana.org', 'iana.org'} and 'example domains' in result.get('result', '').lower()
        row['passed'] = bool(passed)
        self.write()
        if not passed:
            raise RuntimeError('User journey did not pass')

    async def blocked(self):
        before = {p.name for p in (self.home / 'runs').iterdir()}
        async with self.client() as client:
            result = payload(await asyncio.wait_for(client.call_tool('navegar', PUBLIC), 30))
        if result.get('status') != 'busy' or result.get('cleanup_pending') is not True or before != {p.name for p in (self.home / 'runs').iterdir()}:
            raise RuntimeError('Unconfirmed cleanup did not block new work')

    async def recover(self, state):
        from browser import api
        from lifecycle import recover
        self.record(state)
        group, _ = self.group(state)
        closed, pending = await asyncio.to_thread(recover, state, state.name)
        stopped = api('/browsers/' + self.record(state)['browser_id'])['status'] == 'stopped'
        if not closed or pending or not stopped or members(group):
            raise RuntimeError('Recovery unconfirmed; active marker preserved')
        marker = self.home / 'active-run.json'
        if self.active() != state:
            raise RuntimeError('Active marker ownership changed')
        marker.replace(state / 'confirmed-recovery-active-run.json')
        return True

    async def crash(self):
        row = self.row('owned_process_loss')
        triggered = False
        state = None
        try:
            async with self.client() as client:
                server = self.server()
                task = asyncio.create_task(self.call(client, PUBLIC))
                deadline = time.monotonic() + 90
                while time.monotonic() < deadline and not task.done():
                    state = self.active()
                    if state:
                        try:
                            rec = json.loads((state / 'lifecycle.json').read_text())
                        except FileNotFoundError:
                            rec = {}
                        if rec.get('phase') == 'active' and rec.get('model_pgid'):
                            self.owned.add(state)
                            self.record(state)
                            group, models = self.group(state)
                            executors = [process(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()]
                            executors = [p for p in executors if p and p['ppid'] == server['pid'] and os.fsencode(str(self.home / 'app/executor.py')) in p['args']]
                            executors = [process(p['pid'], include_env=True) for p in executors]
                            expected = os.fsencode('BROWSER_EXECUTOR_STATE=' + str(state))
                            current_server = process(server['pid'])
                            if len(executors) != 1 or not executors[0] or expected not in executors[0]['env'] or not models or not current_server or current_server['args'] != server['args']:
                                raise RuntimeError('Owned process tree verification failed')
                            # Remove the supervisor first so it cannot race operator recovery.
                            os.kill(server['pid'], signal.SIGKILL)
                            os.kill(executors[0]['pid'], signal.SIGKILL)
                            os.killpg(group, signal.SIGKILL)
                            triggered = True
                            break
                    await asyncio.sleep(.05)
                if not triggered:
                    await task
                    raise RuntimeError('Process-loss injection was not reached')
                try:
                    await asyncio.wait_for(task, 20)
                except Exception:
                    pass  # The killed stdio server cannot return a result.
        except BaseException as exc:
            if not triggered or isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
                raise
            row['transport_error_type'] = type(exc).__name__
        if self.active() != state:
            raise RuntimeError('Process loss did not retain the owned marker')
        await self.blocked()
        row.update(status='interrupted', usage_known=False, metrics={}, blocked_after_restart=True,
                   creation_identity_recorded=True, operator_recovery_confirmed=await self.recover(state),
                   elapsed_seconds=round(time.time() - row['started_epoch'], 3), passed=True)
        self.write()

    async def outage(self):
        row = self.row('SIMULATED_OUTAGE_provider_cleanup')
        addition = ('\n# Readiness-only fault adapter; private isolated runtime, not production.\n'
                    '_readiness_real_api = api\ndef api(path, method="GET", body=None):\n'
                    '    if Path(' + repr(str(self.flag)) + ').exists() and path.startswith("/browsers/"):\n'
                    '        raise ConnectionError("SIMULATED_OUTAGE")\n'
                    '    return _readiness_real_api(path, method, body)\n')
        try:
            self.patch.write_bytes(self.original + addition.encode())
            self.flag.touch(mode=0o600)
            async with self.client() as client:
                result = await self.call(client, PUBLIC)
            state = self.home / 'runs' / result['run_id']
            self.owned.add(state)
            self.record(state)
            row.update(status=result.get('status'), metrics=result.get('metrics', {}),
                       usage_known='input_tokens' in result.get('metrics', {}), cleanup_pending=result.get('cleanup_pending'),
                       creation_identity_recorded=True)
            if result.get('status') != 'failed' or result.get('cleanup_pending') is not True or result.get('browser_closed') is not False or self.active() != state:
                raise RuntimeError('Simulated provider failure was not retained')
            await self.blocked()
            row['new_work_blocked'] = True
        finally:
            self.flag.unlink(missing_ok=True)
            self.patch.write_bytes(self.original)
        row.update(operator_recovery_confirmed=await self.recover(state), passed=True,
                   elapsed_seconds=round(time.time() - row['started_epoch'], 3))
        self.write()

    async def run(self, authenticated_url):
        await self.normal('public_navigation', PUBLIC)
        if authenticated_url:
            await self.normal('saved_login', {'url': authenticated_url, 'tarefa': 'Confirm whether the saved login opens the authenticated dashboard. Return only authenticated: yes, or requires_auth. Do not report account data, names, domains or values; do not log in or change anything.'}, True)
        await self.crash()
        await self.normal('navigation_after_process_recovery', PUBLIC)
        await self.outage()
        await self.normal('navigation_after_provider_recovery', PUBLIC)
        self.report['status'] = 'passed'


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    parser.add_argument('--authenticated-url')
    args = parser.parse_args()
    home = Path(args.home).expanduser().resolve()
    if sys.platform != 'linux' or json.loads((home / 'readiness-isolated.json').read_text()).get('purpose') != 'readiness-check' or (home / 'active-run.json').exists():
        parser.error('Use an explicitly marked isolated Linux runtime with no active run.')
    os.environ['CODEX_BROWSER_BRIDGE_HOME'] = str(home)
    sys.path.insert(0, str(home / 'app'))
    # Load the real transport before applying the private fault adapter.
    import browser
    check = Check(home)
    try:
        asyncio.run(check.run(args.authenticated_url))
    except BaseException as exc:
        (check.out / 'exception.log').write_text(''.join(traceback.format_exception(exc)))
        check.report.update(status='stopped', error_type=type(exc).__name__)
    finally:
        check.flag.unlink(missing_ok=True)
        check.patch.write_bytes(check.original)
        check.report['private_fault_adapter_restored'] = check.patch.read_bytes() == check.original
        check.report['cleanup_pending'] = check.active() is not None
        check.report['real_calls_admitted'] = check.calls
        fields = ('input_tokens', 'cached_input_tokens', 'uncached_input_tokens', 'output_tokens')
        check.report['known_totals'] = {field: sum(row.get('metrics', {}).get(field, 0) for row in check.report['cases']) for field in fields}
        check.report['usage_unknown_cases'] = sum(not row.get('usage_known', False) for row in check.report['cases'])
        check.report['finished_epoch'] = time.time()
        check.write()
    print(json.dumps(check.report), flush=True)
    return 0 if check.report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
