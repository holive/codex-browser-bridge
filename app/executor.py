"""One request, one Codex process group, one owned browser, one final result."""
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from runtime import ROOT, CONFIG
from browser import api, create_browser, call
from lifecycle import kill_model_group, stop_owned, write_journal

STATE = Path(os.environ.get('BROWSER_EXECUTOR_STATE', str(ROOT / 'runs/manual')))
SESSION = os.environ.get('BROWSER_EXECUTOR_SESSION', 'browser-task')
os.umask(0o077)


def browser(args):
    return call(args, session=SESSION)


def cancel(signum, frame):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise TimeoutError('Executor cancelled')


def execute(request, model_timeout=180):
    start = time.monotonic()
    child = None
    events = []
    record = {'session': SESSION, 'phase': 'not_started', 'browser_closed': False}
    audit = {'session': SESSION, 'started_epoch': time.time(), 'codex_invocations': 0}
    result = {'status': 'failed', 'result': '', 'final_url': '', 'error': '', 'metrics': {}, 'browser_closed': False}
    write_journal(STATE, record)
    try:
        if set(request) != {'task', 'url'} or not isinstance(request['task'], str) or not 1 <= len(request['task'].strip()) <= 6000:
            raise ValueError('Expected task and initial URL')
        from navigation_guard import check_url
        check_url(request['url'])
        (STATE / 'received-request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2))
        setup = time.monotonic()
        record['phase'] = 'creating'
        write_journal(STATE, record)
        created = create_browser()
        browser_id = created.get('id') if isinstance(created, dict) else None
        if not isinstance(browser_id, str) or not browser_id:
            raise RuntimeError('Browser creation returned no identity; cleanup requires inspection')
        # Record ownership before attachment: an invalid endpoint must not lose the ID.
        record.update(phase='active', browser_id=browser_id)
        write_journal(STATE, record)
        audit['browser_id'] = browser_id
        endpoint = created.get('cdpUrl')
        from urllib.parse import urlparse
        if not isinstance(endpoint, str) or urlparse(endpoint).scheme not in {'ws', 'wss', 'http', 'https'} or not urlparse(endpoint).hostname:
            raise RuntimeError('Browser creation returned an invalid connection endpoint')
        record['cdp_url'] = endpoint
        write_journal(STATE, record)
        browser(['open', 'about:blank'])
        result['metrics']['setup_seconds'] = round(time.monotonic() - setup, 3)
        prompt = (Path(__file__).with_name('executor-policy.txt')).read_text() + '\nExecutável permitido: ' + shlex.quote(str(ROOT / 'commands/agent-browser')) + '\nUse sempre esse caminho absoluto no lugar de agent-browser; o shell pode redefinir PATH.\nURL inicial: ' + json.dumps(request['url']) + '\nTarefa: ' + json.dumps(request['task'], ensure_ascii=False) + '\nComece abrindo a URL inicial. Execute somente leitura/pesquisa e termine com o JSON solicitado.'
        (STATE / 'codex-prompt.txt').write_text(prompt)
        env = dict(os.environ)
        env['PATH'] = str(ROOT / 'commands') + os.pathsep + env.get('PATH', '')
        args = [CONFIG['codex_bin'], 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check', '--approve-for-me', '--json', '-c', 'sandbox_workspace_write.network_access=true', '-c', 'model=' + json.dumps(CONFIG.get('codex_model', 'gpt-6.1-sol')), '-c', 'model_reasoning_effort=' + json.dumps(CONFIG.get('codex_reasoning_effort', 'high')), '--output-schema', str(Path(__file__).with_name('schema.json')), '-o', str(STATE / 'codex-final.json'), '-']
        began = time.monotonic()
        audit['codex_invocations'] = 1
        with (STATE / 'codex-events.jsonl').open('w') as raw, (STATE / 'codex-stderr.log').open('w') as err:
            child = subprocess.Popen(args, cwd=ROOT / 'execution', env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True, start_new_session=True)
            record['model_pgid'] = child.pid
            write_journal(STATE, record)
            def consume():
                for line in child.stdout:
                    raw.write(line)
                    raw.flush()
                    try: events.append(json.loads(line))
                    except ValueError: pass
            reader = threading.Thread(target=consume, daemon=True)
            reader.start()
            child.stdin.write(prompt)
            child.stdin.close()
            try:
                rc = child.wait(timeout=model_timeout)
            except subprocess.TimeoutExpired:
                raise TimeoutError('Codex deadline reached')
            reader.join(timeout=5)
        result['metrics']['codex_seconds'] = round(time.monotonic() - began, 3)
        usages = [e['usage'] for e in events if e.get('type') == 'turn.completed']
        usage = usages[-1] if usages else {}
        result['metrics'].update(input_tokens=usage.get('input_tokens', 0), cached_input_tokens=usage.get('cached_input_tokens', 0), uncached_input_tokens=usage.get('input_tokens', 0) - usage.get('cached_input_tokens', 0), output_tokens=usage.get('output_tokens', 0))
        audit['shell_calls'] = sum(e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'command_execution' for e in events)
        answer = json.loads((STATE / 'codex-final.json').read_text())
        final_url = browser(['get', 'url']).strip()
        verified = bool(rc == 0 and usage and answer.get('final_url') == final_url and answer.get('status') in {'succeeded', 'failed', 'requires_auth', 'out_of_scope'} and all(isinstance(answer.get(k), str) for k in ('result', 'error', 'final_url')))
        (STATE / 'verification.json').write_text(json.dumps({'process_and_final_url_checked': verified, 'answer': answer, 'observed_final_url': final_url}, ensure_ascii=False, indent=2))
        audit['process_and_final_url_checked'] = verified
        if verified:
            result.update(status=answer['status'], result=answer['result'], final_url=final_url, error=answer['error'])
        else:
            result['error'] = 'Execução ou URL final não confirmada.'
    except TimeoutError:
        result.update(status='timed_out', error='Prazo de execução atingido.')
    except Exception as exc:
        result.update(status='failed', error='Falha de execução ou verificação (' + type(exc).__name__ + ').')
    finally:
        # Descendants may survive a normally exited leader; always terminate the owned group.
        kill_model_group(record)
        if child is not None:
            child.wait()
            if child.stdout:
                child.stdout.close()
        closed, pending = stop_owned(STATE, lambda: browser(['close']), api)
        result.update(browser_closed=closed, cleanup_pending=pending)
        if pending:
            if result['status'] != 'timed_out':
                result['status'] = 'failed'
            result.update(result='', error='Encerramento não confirmado. Não repita; confira a sessão Cloud e o registro privado antes de liberar nova tarefa.')
        result['metrics']['total_seconds'] = round(time.monotonic() - start, 3)
        audit.update(finished_epoch=time.time(), browser_stop_confirmed=closed, cleanup_pending=pending)
        (STATE / 'executor-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
        (STATE / 'executor-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, cancel)
    print(json.dumps(execute(json.load(sys.stdin)), ensure_ascii=False), flush=True)
