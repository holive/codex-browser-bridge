"""Browser Use transport. No website-specific workflow or login recipe."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from runtime import ROOT, CONFIG


def api(path, method='GET', body=None):
    request = urllib.request.Request(
        'https://api.browser-use.com/api/v4' + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'X-Browser-Use-API-Key': CONFIG['browser_use_api_key'], 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def create_browser():
    # The response identifies this task's browser even if other sessions exist.
    return api('/browsers', 'POST', {'profileId': CONFIG['profile_id'],
                                   'proxyCountryCode': None, 'enableRecording': False})


def call(args, session):
    env = dict(os.environ)
    env.update({
        'AGENT_BROWSER_CONFIG': str(ROOT / 'agent-browser.json'),
        'AGENT_BROWSER_AUTO_CONNECT': 'false',
        'AGENT_BROWSER_NAMESPACE': 'codex-browser-bridge',
        'AGENT_BROWSER_SESSION': session,
        'AGENT_BROWSER_IDLE_TIMEOUT_MS': '900000',
    })
    for key in ('AGENT_BROWSER_PROVIDER', 'AGENT_BROWSER_CDP', 'AGENT_BROWSER_PROFILE', 'AGENT_BROWSER_STATE',
                'AGENT_BROWSER_RESTORE', 'AGENT_BROWSER_SESSION_NAME'):
        env.pop(key, None)
    if args[0] != 'close':
        state = os.environ.get('BROWSER_EXECUTOR_STATE')
        if not state:
            raise RuntimeError('No owned browser state')
        record = json.loads((Path(state) / 'lifecycle.json').read_text())
        if record.get('session') != session or record.get('phase') != 'active' or not record.get('cdp_url'):
            raise RuntimeError('No owned browser connection')
        env['AGENT_BROWSER_CDP'] = record['cdp_url']
    started = time.monotonic()
    result = subprocess.run([
        CONFIG['agent_browser_bin'], '--config', str(ROOT / 'agent-browser.json'),
        '--namespace', 'codex-browser-bridge', '--session', session, *args,
    ], cwd=ROOT / 'execution', env=env, capture_output=True, text=True, timeout=60)
    with (ROOT / 'execution/browser-call-times.jsonl').open('a') as log:
        log.write(json.dumps({'action': args[0], 'seconds': round(time.monotonic() - started, 3),
                              'returncode': result.returncode}) + '\n')
    if result.returncode:
        raise RuntimeError('Browser command failed: ' + args[0] + '; output withheld')
    return result.stdout.strip()
