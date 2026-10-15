"""Fast fault-injection checks: real processes, synthetic provider/model, zero Cloud calls."""
import asyncio
import importlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / 'app'))
TEST_HOME = tempfile.TemporaryDirectory(prefix='bridge-tests-')
os.environ['CODEX_BROWSER_BRIDGE_HOME'] = TEST_HOME.name
for key in ('BROWSER_USE_API_KEY', 'BROWSER_USE_PROFILE_ID'):
    os.environ.pop(key, None)
server = importlib.import_module('server')
executor = importlib.import_module('executor')

FINAL = {'status': 'succeeded', 'result': 'Example', 'final_url': 'https://example.com/', 'error': '',
         'metrics': {}, 'browser_closed': True}


def script(path, body):
    path.write_text('#!' + sys._base_executable + '\n' + body)
    path.chmod(0o700)
    return str(path)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='bridge-case-')
        self.root = Path(self.tmp.name)
        for name in ('runs', 'app', 'execution', 'commands'):
            (self.root / name).mkdir()
        self.config = {'browser_use_api_key': 'synthetic', 'profile_id': 'synthetic'}
        (self.root / 'config.json').write_text(json.dumps(self.config))
        self.state = self.root / 'runs/test'
        self.state.mkdir()
        for name in ('executor-policy.txt', 'schema.json'):
            shutil.copy2(SOURCE / 'app' / name, self.root / 'app' / name)

    def tearDown(self):
        self.tmp.cleanup()

    def fake_model(self, status='succeeded', hang=False, descendant=False):
        answer = {'status': status, 'result': 'synthetic', 'final_url': 'https://example.com/', 'error': ''}
        body = 'import json,sys,os,time,subprocess\nfrom pathlib import Path\n'
        if descendant:
            body += "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nPath(" + repr(str(self.root / 'descendant')) + ").write_text(str(p.pid))\n"
        if hang:
            body += 'time.sleep(60)\n'
        body += 'Path(sys.argv[sys.argv.index("-o")+1]).write_text(' + repr(json.dumps(answer)) + ')\n'
        body += 'print(json.dumps({"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}))\n'
        self.config['codex_bin'] = script(self.root / 'fake-codex', body)

    def run_executor(self, status='succeeded', close_fails=False, start_fails=False, list_fails=False, descendant=False, hang=False, api_fails=None, model_timeout=180):
        self.fake_model(status, hang, descendant)
        self.actions = []
        self.stopped = False
        def browser(args):
            self.actions.append(args[0])
            if args[0] == 'open':
                if start_fails:
                    raise TimeoutError('Unknown provider creation outcome')
            if args[0] == 'close':
                if close_fails:
                    raise RuntimeError('synthetic close failure')
                self.stopped = True
            return 'https://example.com/' if args[:2] == ['get', 'url'] else ''
        count = 0
        def browsers():
            nonlocal count
            count += 1
            if list_fails:
                raise ConnectionError('synthetic preflight failure')
            return [] if count == 1 else [{'id': 'owned', 'status': 'active'}]
        def api(path, method='GET', body=None):
            if api_fails if api_fails is not None else close_fails:
                raise ConnectionError('synthetic provider outage')
            if method == 'PATCH':
                self.stopped = True
            return {'id': 'owned', 'status': 'stopped' if self.stopped else 'active'}
        with patch.multiple(executor, ROOT=self.root, CONFIG=self.config, STATE=self.state,
                            SESSION='synthetic-session', browser=browser, browsers=browsers, api=api):
            return executor.execute({'task': 'Read title', 'url': 'https://example.com'}, model_timeout=model_timeout)


class ExecutorFaults(Workspace):
    def test_preflight_failure_does_not_close_a_session(self):
        result = self.run_executor(list_fails=True)
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('close', self.actions)

    def test_cleanup_failure_overrides_requires_auth(self):
        result = self.run_executor(status='requires_auth', close_fails=True)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['browser_closed'])

    def test_descendant_stopped_even_when_model_leader_exits(self):
        pid = None
        try:
            result = self.run_executor(descendant=True)
            self.assertEqual(result['status'], 'succeeded')
            pid = int((self.root / 'descendant').read_text())
            time.sleep(.1)
            running = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
            self.assertTrue(not running or running.startswith('Z'), 'Model descendant survived completed task')
        finally:
            if pid:
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass

    def test_model_timeout_closes_browser_and_kills_group(self):
        result = self.run_executor(hang=True, model_timeout=.05)
        self.assertEqual(result['status'], 'timed_out')
        self.assertTrue(result['browser_closed'])
        pgid=json.loads((self.state/'lifecycle.json').read_text())['model_pgid']
        with self.assertRaises(ProcessLookupError): os.killpg(pgid, 0)

    def test_provider_stop_fallback_after_close_command_failure(self):
        result = self.run_executor(close_fails=True, api_fails=False)
        self.assertEqual(result['status'], 'succeeded')
        self.assertTrue(result['browser_closed'])

    def test_creation_outcome_unknown_is_not_claimed_closed(self):
        result = self.run_executor(start_fails=True)
        self.assertTrue(result['cleanup_pending'])
        self.assertFalse(result['browser_closed'])
        self.assertEqual(json.loads((self.state/'lifecycle.json').read_text())['phase'],'cleanup_pending')

    def test_out_of_scope_is_returned_only_after_cleanup(self):
        result = self.run_executor(status='out_of_scope')
        self.assertEqual(result['status'], 'out_of_scope')
        self.assertTrue(result['browser_closed'])

    def test_unrecognized_model_status_is_not_success(self):
        result = self.run_executor(status='invented')
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['browser_closed'])

    def test_sigterm_executor_stops_owned_browser_and_model(self):
        self.fake_model(hang=True)
        (self.root/'config.json').write_text(json.dumps(self.config))
        code="""import json,signal,sys,types
sys.path.insert(0,SOURCE)
fake=types.ModuleType('browser');counter=0;stopped=False
def call(args,session):
 global stopped
 if args[0]=='close':stopped=True
 return 'https://example.com/' if args[:2]==['get','url'] else ''
def browsers():
 global counter
 counter+=1
 return [] if counter==1 else [{'id':'owned','status':'active'}]
def api(*args):return {'status':'stopped' if stopped else 'active'}
fake.call=call;fake.browsers=browsers;fake.api=api;sys.modules['browser']=fake
import executor
signal.signal(signal.SIGTERM,executor.cancel)
print(json.dumps(executor.execute({'task':'read','url':'https://example.com'})),flush=True)
""".replace('SOURCE',repr(str(SOURCE/'app')))
        env=dict(os.environ,CODEX_BROWSER_BRIDGE_HOME=str(self.root),BROWSER_EXECUTOR_STATE=str(self.state),BROWSER_EXECUTOR_SESSION='signal-test')
        child=subprocess.Popen([sys.executable,'-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        pgid=None
        try:
            for _ in range(200):
                try:pgid=json.loads((self.state/'lifecycle.json').read_text()).get('model_pgid')
                except (FileNotFoundError,ValueError):pass
                if pgid:break
                time.sleep(.01)
            self.assertIsNotNone(pgid)
            child.terminate()
            out,err=child.communicate(timeout=3)
            self.assertEqual(child.returncode,0,err)
            result=json.loads(out)
            self.assertEqual(result['status'],'timed_out')
            self.assertTrue(result['browser_closed'])
            with self.assertRaises(ProcessLookupError):os.killpg(pgid,0)
        finally:
            if child.poll() is None:child.kill();child.communicate()
            if pgid:
                try:os.killpg(pgid,signal.SIGKILL)
                except ProcessLookupError:pass


class AdapterFaults(Workspace):
    def fake_executor(self, exit_code=0, hold=False):
        body = 'import json,os,sys,time\nfrom pathlib import Path\nr=json.load(sys.stdin)\ns=Path(os.environ["BROWSER_EXECUTOR_STATE"])\n'
        body += '(s/"lifecycle.json").write_text(json.dumps({"phase":"closed","browser_id":"owned","browser_closed":True}))\n'
        if hold:
            body += 'root=s.parents[1]\n(root/"entered").write_text(str(os.getpid()))\n'
            body += 'if r["task"]=="first":\n while not (root/"release").exists(): time.sleep(.01)\n'
        body += 'print(' + repr(json.dumps(FINAL)) + ')\nsys.exit(' + str(exit_code) + ')\n'
        (self.root / 'app/executor.py').write_text(body)

    def test_nonzero_process_exit_never_reports_success(self):
        self.fake_executor(exit_code=7)
        async def run():
            with patch.multiple(server, ROOT=self.root, lock=asyncio.Lock()):
                return await server.dispatch({'task': 'test', 'url': 'https://example.com'})
        self.assertEqual(asyncio.run(run())['status'], 'failed')

    def test_separate_mcp_processes_cannot_overlap(self):
        self.fake_executor(hold=True)
        env=dict(os.environ, CODEX_BROWSER_BRIDGE_HOME=str(self.root))
        code='import sys,asyncio,json;sys.path.insert(0,'+repr(str(SOURCE/'app'))+');import server;print(json.dumps(asyncio.run(server.dispatch({"task":sys.argv[1],"url":"https://example.com"}))))'
        first=subprocess.Popen([sys.executable,'-c',code,'first'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            end=time.monotonic()+4
            while not (self.root/'entered').exists() and time.monotonic()<end:time.sleep(.02)
            self.assertTrue((self.root/'entered').exists(),'First executor never started')
            second=subprocess.run([sys.executable,'-c',code,'second'],env=env,capture_output=True,text=True,timeout=4)
            self.assertEqual(json.loads(second.stdout)['status'],'busy')
        finally:
            (self.root/'release').touch()
            first.communicate(timeout=4)

    def dispatch(self):
        async def run():
            with patch.multiple(server, ROOT=self.root, lock=asyncio.Lock()):
                return await server.dispatch({'task':'test','url':'https://example.com'})
        return asyncio.run(run())

    def test_invalid_json_output_is_rejected(self):
        (self.root/'app/executor.py').write_text('print("not-json")')
        result=self.dispatch()
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['cleanup_pending'])
        self.assertTrue((self.root/'active-run.json').exists())

    def test_pending_cleanup_blocks_next_task_without_starting_worker(self):
        (self.root/'active-run.json').write_text('{"run_id":"previous"}')
        result=self.dispatch()
        self.assertEqual(result['status'],'busy')
        self.assertTrue(result['cleanup_pending'])
        self.assertEqual(list((self.root/'runs').iterdir()),[self.state])

    def test_adapter_timeout_terminates_child_and_clears_confirmed_run(self):
        self.fake_executor()
        p=self.root/'app/executor.py'
        p.write_text(p.read_text().replace('print(', 'time.sleep(60)\nprint('))
        async def run():
            with patch.multiple(server, ROOT=self.root, lock=asyncio.Lock(),EXECUTOR_TIMEOUT=.1):
                return await server.dispatch({'task':'test','url':'https://example.com'})
        result=asyncio.run(run())
        self.assertEqual(result['status'],'timed_out')
        self.assertTrue(result['browser_closed'])
        self.assertFalse((self.root/'active-run.json').exists())

    def test_cancellation_cleans_up_before_releasing_lock(self):
        self.fake_executor(hold=True)
        async def run():
            with patch.multiple(server, ROOT=self.root, lock=asyncio.Lock()):
                task=asyncio.create_task(server.dispatch({'task':'first','url':'https://example.com'}))
                for _ in range(100):
                    if (self.root/'entered').exists():break
                    await asyncio.sleep(.01)
                self.assertTrue((self.root/'entered').exists())
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertFalse((self.root/'active-run.json').exists())
        asyncio.run(run())

    def test_failed_process_does_not_leave_runtime_busy_after_confirmed_cleanup(self):
        self.fake_executor(exit_code=3)
        self.assertEqual(self.dispatch()['status'],'failed')
        self.assertFalse((self.root/'active-run.json').exists())
        self.fake_executor()
        self.assertEqual(self.dispatch()['status'],'succeeded')

    def test_lock_survives_abrupt_mcp_parent_death(self):
        self.fake_executor(hold=True)
        env=dict(os.environ,CODEX_BROWSER_BRIDGE_HOME=str(self.root))
        code='import sys,asyncio;sys.path.insert(0,'+repr(str(SOURCE/'app'))+');import server;asyncio.run(server.dispatch({"task":"first","url":"https://example.com"}))'
        parent=subprocess.Popen([sys.executable,'-c',code],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        worker=None
        try:
            for _ in range(200):
                if (self.root/'entered').exists():break
                time.sleep(.01)
            self.assertTrue((self.root/'entered').exists())
            worker=int((self.root/'entered').read_text())
            parent.kill();parent.wait(timeout=2)
            with (self.root/'executor.lock').open('a') as lease:
                with self.assertRaises(BlockingIOError):fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.dispatch()['status'],'busy')
        finally:
            if parent.poll() is None:parent.kill();parent.wait()
            (self.root/'release').touch()
            if worker:
                for _ in range(100):
                    stat=subprocess.run(['ps','-o','stat=','-p',str(worker)],capture_output=True,text=True).stdout.strip()
                    if not stat or stat.startswith('Z'):break
                    time.sleep(.01)
                else:
                    try:os.kill(worker,signal.SIGKILL)
                    except ProcessLookupError:pass


class InputGuards(Workspace):
    def test_invalid_requests_never_dispatch(self):
        async def run():
            with patch.object(server,'dispatch') as launch:
                for url in ('http://127.0.0.1','http://[::1]','file:///etc/passwd','http://user:pass@example.com','http://localhost','http://10.0.0.1'):
                    self.assertEqual((await server.navegar('read',url))['status'],'failed')
                self.assertEqual((await server.navegar(' ','https://example.com'))['status'],'failed')
                self.assertEqual((await server.navegar('x'*6001,'https://example.com'))['status'],'failed')
                launch.assert_not_called()
        asyncio.run(run())

    def test_missing_configuration_never_dispatches(self):
        async def run():
            with patch.object(server,'CONFIG',{}),patch.object(server,'dispatch') as launch:
                self.assertEqual((await server.navegar('read','https://example.com'))['status'],'requires_setup')
                launch.assert_not_called()
        asyncio.run(run())


class SupervisorRecovery(Workspace):
    def test_recovery_stops_only_recorded_browser(self):
        from lifecycle import recover,write_journal
        write_journal(self.state,{'phase':'active','browser_id':'owned','session':'unique'})
        calls=[]
        def api(path,method='GET',body=None):
            calls.append((path,method))
            return {'status':'active' if len(calls)==1 else 'stopped'}
        with patch('browser.call') as close,patch('browser.api',api):
            closed,pending=recover(self.state,'unique')
        self.assertTrue(closed)
        self.assertFalse(pending)
        close.assert_called_once_with(['close'],session='unique')
        self.assertTrue(all(path=='/browsers/owned' for path,_ in calls))

    def test_creation_without_id_does_not_stop_unrelated_browser(self):
        from lifecycle import stop_owned,write_journal
        write_journal(self.state,{'phase':'creating'})
        with patch('browser.api') as api:
            closed,pending=stop_owned(self.state,lambda:None,api)
            api.assert_not_called()
        self.assertFalse(closed)
        self.assertTrue(pending)


if __name__ == '__main__':
    unittest.main()
