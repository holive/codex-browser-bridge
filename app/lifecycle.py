"""Private lifecycle journal and process cleanup; no inference about unrelated browsers."""
import json
import os
import signal
from pathlib import Path


def write_journal(state, record):
    path = Path(state) / 'lifecycle.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record))
    temporary.replace(path)


def read_journal(state):
    return json.loads((Path(state) / 'lifecycle.json').read_text())


def kill_model_group(record):
    group = record.get('model_pgid')
    if isinstance(group, int) and group > 1:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(group, sig)
            except ProcessLookupError:
                break


def stop_owned(state, close, api):
    record = read_journal(state)
    if record['phase'] in {'not_started', 'closed'}:
        return bool(record.get('browser_closed')), False
    if not record.get('browser_id'):
        record.update(phase='cleanup_pending', browser_closed=False)
        write_journal(state, record)
        return False, True
    # CDP close detaches; the provider API below stops only the recorded browser.
    try:
        close()
    except Exception:
        record['close_command_failed'] = True
    confirmed = False
    browser_id = record.get('browser_id')
    if browser_id:
        try:
            current = api('/browsers/' + browser_id)
            if current['status'] != 'stopped':
                api('/browsers/' + browser_id, 'PATCH', {'action': 'stop'})
                current = api('/browsers/' + browser_id)
            confirmed = current['status'] == 'stopped'
        except Exception:
            pass
    # Creation can time out before returning an ID. Never guess ownership or claim closure.
    record.update(phase='closed' if confirmed else 'cleanup_pending', browser_closed=confirmed)
    write_journal(state, record)
    return confirmed, not confirmed


def recover(state, session):
    from browser import api, call
    record = read_journal(state)
    kill_model_group(record)
    return stop_owned(state, lambda: call(['close'], session=session), api)
