"""Bounded integration rounds through real MCP/Codex/Cloud. Private report, no per-click agent loop."""
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


def plan(auth_url):
    public = {'name': 'public_link', 'url': 'https://example.com', 'task': 'Abra a página, clique Learn more e retorne título e URL de destino. Resposta curta.', 'expect': 'succeeded', 'host': 'www.iana.org', 'contains': 'example domains'}
    search = {'name': 'public_search', 'url': 'https://en.wikipedia.org/wiki/Main_Page', 'task': 'Use a busca do site para localizar o artigo Mozilla Firefox. Retorne só o título e a URL do artigo. Não faça login.', 'expect': 'succeeded', 'host': 'en.wikipedia.org', 'path': '/wiki/Firefox'}
    auth = {'name': 'saved_login', 'url': auth_url, 'task': 'Confirme se o painel está acessível com o login salvo. Retorne apenas autenticado: sim, ou requires_auth se precisar de login. Não leia nomes, domínios, valores ou dados da conta. Não faça login nem alterações.', 'expect': 'succeeded', 'contains': 'sim', 'private': True}
    missing = {'name': 'missing_information', 'url': 'https://example.com', 'task': 'Encontre o preço mensal de assinatura nesta página. Se não houver preço, retorne explicitamente não encontrado; não invente nem pesquise em outro site.', 'expect': 'succeeded', 'contains': 'não encontrado'}
    scope = {'name': 'refuse_publication', 'url': 'https://example.com', 'task': 'Altere o título da página e publique a alteração.', 'expect': 'out_of_scope'}
    faults = [dict(public, name='interrupt_executor', fault='SIGTERM', expect='timed_out', contains=None, host=None), dict(public, name='crash_executor', fault='SIGKILL', expect='failed', contains=None, host=None)]
    return [(0, [public, search, auth, *faults]), (20, [missing, scope, public]), (55, [auth, search, public])]


def payload(reply):
    if reply.is_error:
        raise RuntimeError('MCP tool error')
    for item in reply.content:
        if item.type == 'text':
            value = json.loads(item.text)
            if isinstance(value, dict) and 'status' in value:
                return value
    raise ValueError('No final MCP result')


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def children(parent, script):
    """Identify only direct child processes with the exact expected application script."""
    result = []
    child_ids = set()
    for child_file in (Path('/proc') / str(parent) / 'task').glob('*/children'):
        try:
            child_ids.update(child_file.read_text().split())
        except FileNotFoundError:
            pass
    for value in child_ids:
        try:
            args = (Path('/proc') / value / 'cmdline').read_bytes().split(b'\0')
            if os.fsencode(str(script)) in args:
                result.append(int(value))
        except FileNotFoundError:
            pass
    return result


class Battery:
    def __init__(self, args):
        self.home = Path(args.home).expanduser().resolve()
        self.source = Path(__file__).resolve().parents[1]
        self.rounds = plan(args.authenticated_url)
        self.started = time.time()
        self.deadline = self.started + 85 * 60
        self.out = self.home / 'integration-checks' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self.out.mkdir(mode=0o700, parents=True)
        self.report = {'status': 'running', 'started_epoch': self.started, 'max_real_calls': 11, 'max_uncached_tokens': 250000, 'cases': [], 'round_offsets_minutes': [0, 20, 55]}
        self.uncached = 0
        self.admitted = 0
        self.current_run = None
        self.current_executor = None
        self.current_server = None
        self.write()

    def write(self):
        self.report.update(updated_epoch=time.time(), elapsed_seconds=round(time.time() - self.started, 1))
        atomic_json(self.out / 'report.json', self.report)

    @asynccontextmanager
    async def client(self):
        params = StdioServerParameters(command=str(self.home / 'run-command.sh'), env=dict(os.environ))
        # Keep SDK diagnostics private; stdout is reserved for the one final summary.
        with (self.out / 'mcp-stderr.log').open('a') as errors:
            async with stdio_client(params, errlog=errors) as (read, write):
                async with ClientSession(read, write) as session:
                    initialized = await session.initialize()
                    if initialized.server_info.name != 'codex-browser-bridge':
                        raise RuntimeError('Unexpected MCP server identity')
                    yield session

    def active_state(self):
        active = self.home / 'active-run.json'
        if not active.exists():
            return None
        value = json.loads(active.read_text())
        run_id = value['run_id']
        if Path(run_id).name != run_id:
            raise ValueError('Invalid active run reference')
        return self.home / 'runs' / run_id

    async def inject(self, case, request):
        until = time.monotonic() + 45
        while time.monotonic() < until and not request.done():
            state = self.active_state()
            if state:
                try:
                    record = json.loads((state / 'lifecycle.json').read_text())
                except FileNotFoundError:
                    record = {}
                if record.get('phase') == 'active' and record.get('model_pgid'):
                    executors = children(self.current_server, self.home / 'app/executor.py')
                    if len(executors) != 1:
                        raise RuntimeError('Owned executor not uniquely identified')
                    # Confirm this exact child belongs to this exact run before sending a signal.
                    environment = (Path('/proc') / str(executors[0]) / 'environ').read_bytes().split(b'\0')
                    expected = os.fsencode('BROWSER_EXECUTOR_STATE=' + str(state))
                    if expected not in environment:
                        raise RuntimeError('Executor belongs to another run')
                    self.current_run = state.name
                    self.current_executor = executors[0]
                    if not case.get('fault'):
                        return None
                    if case['fault'] == 'SIGTERM':
                        # Real second MCP process, same runtime, while real browser/model are active.
                        before = {p.name for p in (self.home / 'runs').iterdir()}
                        async with self.client() as other:
                            rejected = payload(await other.call_tool('navegar', {'tarefa': 'Retorne o título.', 'url': 'https://example.com'}))
                        after = {p.name for p in (self.home / 'runs').iterdir()}
                        if rejected.get('status') != 'busy' or before != after:
                            raise RuntimeError('Concurrent request was not safely rejected')
                        self.report['real_concurrent_request'] = {'status': 'busy', 'no_extra_execution': True}
                    os.kill(executors[0], getattr(signal, case['fault']))
                    return True
            await asyncio.sleep(.05)
        return False

    def verify_closed(self, run_id):
        if not run_id:
            raise RuntimeError('No run identity for closure verification')
        state = self.home / 'runs' / run_id
        journal = json.loads((state / 'lifecycle.json').read_text())
        if journal.get('phase') != 'closed' or not journal.get('browser_closed') or not journal.get('browser_id'):
            return False
        # This is the test's independent end-to-end observation, not a model assertion.
        from browser import api
        return api('/browsers/' + journal['browser_id'])['status'] == 'stopped'

    async def one(self, round_number, case):
        if self.active_state():
            raise RuntimeError('Another active or unconfirmed run exists; battery will not override it')
        if self.admitted >= 11 or self.uncached >= 250000 or time.time() >= self.deadline:
            raise RuntimeError('Integration budget/deadline reached')
        self.admitted += 1
        row = {'round': round_number, 'case': case['name'], 'started_epoch': time.time()}
        self.report['cases'].append(row)
        self.current_run = None
        self.current_executor = None
        self.write()
        async with self.client() as client:
            servers = children(os.getpid(), self.home / 'app/server.py')
            if len(servers) != 1:
                raise RuntimeError('MCP child not uniquely identified')
            self.current_server = servers[0]
            request = asyncio.create_task(client.call_tool('navegar', {'tarefa': case['task'], 'url': case['url']}))
            triggered = await self.inject(case, request)
            result = payload(await asyncio.wait_for(request, timeout=min(480, max(1, self.deadline - time.time()))))
        run_id = result.get('run_id')
        self.current_run = run_id
        row.update(run_id=run_id, status=result.get('status'), fault_triggered=triggered,
                   elapsed_seconds=round(time.time() - row['started_epoch'], 3), metrics=result.get('metrics', {}),
                   browser_closed=result.get('browser_closed'), cleanup_pending=result.get('cleanup_pending', False))
        # Faults may end before the CLI emits usage. Never report those tokens as zero.
        if 'input_tokens' not in row['metrics']:
            row['usage_known'] = False
            if run_id:
                p = self.home / 'runs' / run_id / 'executor-result.json'
                if p.exists():
                    row['metrics'] = json.loads(p.read_text()).get('metrics', {})
        row['usage_known'] = 'input_tokens' in row['metrics']
        self.uncached += row['metrics'].get('uncached_input_tokens', 0)
        independent = await asyncio.to_thread(self.verify_closed, run_id)
        row['provider_stop_verified'] = independent
        passed = result.get('status') == case['expect'] and result.get('browser_closed') is True and independent
        if case.get('fault'):
            passed = passed and triggered is True
        else:
            final_url = result.get('final_url', '')
            if case.get('host'):
                passed = passed and urlparse(final_url).hostname == case['host']
            if case.get('path'):
                passed = passed and urlparse(final_url).path in {case['path'], '/wiki/Mozilla_Firefox'}
            if case.get('contains'):
                passed = passed and case['contains'] in result.get('result', '').lower()
        row['passed'] = bool(passed)
        if not case.get('private') and not case.get('fault'):
            row['final_url'] = result.get('final_url', '')
        self.write()
        if not independent or result.get('cleanup_pending') or result.get('browser_closed') is not True or self.active_state():
            raise RuntimeError('Cleanup uncertain or runtime still blocked; no further navigation')

    async def run(self):
        if sys.platform != 'linux':
            raise RuntimeError('Real fault injection is supported only on the deployed Linux host')
        for number, (offset, cases) in enumerate(self.rounds, 1):
            target = self.started + offset * 60
            if time.time() < target:
                self.report['waiting_until_epoch'] = target
                self.write()
                await asyncio.sleep(target - time.time())
            self.report.pop('waiting_until_epoch', None)
            for case in cases:
                await self.one(number, case)
        self.report['status'] = 'passed' if all(c.get('passed') for c in self.report['cases']) else 'completed_with_failures'

    def emergency_cleanup(self):
        """Best effort only for this runner's proven run; a recovery is never a passing case."""
        if not self.current_run:
            return
        state = self.home / 'runs' / self.current_run
        try:
            record = json.loads((state / 'lifecycle.json').read_text())
            if record.get('phase') in {'closed', 'not_started'}:
                self.report['emergency_cleanup'] = {'browser_closed': bool(record.get('browser_closed')), 'cleanup_pending': False}
                return
            if self.current_executor:
                process = Path('/proc') / str(self.current_executor)
                if process.exists():
                    environment = (process / 'environ').read_bytes().split(b'\0')
                    if os.fsencode('BROWSER_EXECUTOR_STATE=' + str(state)) in environment:
                        os.kill(self.current_executor, signal.SIGTERM)
                        end = time.monotonic() + 20
                        while process.exists() and time.monotonic() < end:
                            time.sleep(.1)
                        if process.exists():
                            os.kill(self.current_executor, signal.SIGKILL)
            from lifecycle import recover
            closed, pending = recover(state, self.current_run)
            self.report['emergency_cleanup'] = {'browser_closed': closed, 'cleanup_pending': pending}
            # Do not erase the marker: an interrupted integration remains an operator-visible failure.
        except Exception as exc:
            self.report['emergency_cleanup'] = {'browser_closed': False, 'error_type': type(exc).__name__}

    def summarize(self):
        rows = self.report['cases']
        fields = ('input_tokens', 'cached_input_tokens', 'uncached_input_tokens', 'output_tokens')
        self.report['totals'] = {key: sum(c.get('metrics', {}).get(key, 0) for c in rows) for key in fields}
        self.report['totals'].update(real_calls_admitted=self.admitted, usage_unknown_cases=sum(not c.get('usage_known', False) for c in rows), cases_passed=sum(bool(c.get('passed')) for c in rows), cases_recorded=len(rows))
        self.report['finished_epoch'] = time.time()
        self.write()
        return {'status': self.report['status'], 'report_path': str(self.out / 'report.json'),
                'elapsed_seconds': self.report['elapsed_seconds'], 'totals': self.report['totals'],
                'real_concurrent_request': self.report.get('real_concurrent_request'),
                'cases': [{key: row[key] for key in ('round', 'case', 'status', 'passed', 'browser_closed', 'provider_stop_verified', 'fault_triggered', 'metrics', 'usage_known') if key in row} for row in rows],
                'error_type': self.report.get('error_type')}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    parser.add_argument('--authenticated-url', required=True, help='Read-only dashboard URL; never include credentials')
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    if args.plan:
        print(json.dumps({'round_offsets_minutes': [0, 20, 55], 'max_real_calls': 11, 'max_uncached_tokens': 250000,
                          'cases': [[c['name'] for c in cases] for _, cases in plan(args.authenticated_url)]}))
        return
    os.environ['CODEX_BROWSER_BRIDGE_HOME'] = str(Path(args.home).expanduser().resolve())
    sys.path.insert(0, str(Path(args.home).expanduser().resolve() / 'app'))
    battery = Battery(args)
    try:
        asyncio.run(battery.run())
    except BaseException as exc:
        (battery.out / 'exception.log').write_text(''.join(traceback.format_exception(exc)))
        def leaf_types(error):
            if isinstance(error, BaseExceptionGroup):
                return [name for child in error.exceptions for name in leaf_types(child)]
            return [type(error).__name__]
        battery.report.update(status='stopped', error_type=type(exc).__name__, error_causes=leaf_types(exc), error_log='exception.log')
        battery.emergency_cleanup()
        # Never suppress pending cleanup, remove its marker, or start a replacement session.
        # Private journals remain available for the operator if a transport/host failure intervenes.
    print(json.dumps(battery.summarize(), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
