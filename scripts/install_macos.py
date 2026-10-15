"""Install application code and the user LaunchAgent; leave tunnel and secrets private."""
import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

if sys.platform != 'darwin':
    raise SystemExit('This installer targets macOS; VPS migration is documented separately.')
os.umask(0o077)
source = Path(__file__).resolve().parents[1]
root = Path(os.environ.get('CODEX_BROWSER_BRIDGE_HOME', str(Path.home() / 'Library/Application Support/CodexBrowserBridge'))).expanduser().resolve()
config = json.loads((root / 'config.json').read_text())
for key in ('browser_use_api_key', 'profile_id', 'public_host', 'private_path', 'agent_browser_bin', 'codex_bin'):
    if not config.get(key):
        raise SystemExit('Private config missing: ' + key)
python = root / '.venv/bin/python'
if not python.exists() or not Path(config['agent_browser_bin']).is_file():
    raise SystemExit('Install dependencies first; see README.')
for request in (root / 'runs').glob('*/received-request.json'):
    if time.time() - request.stat().st_mtime < 360 and not any((request.parent / name).exists() for name in ('delivery.json', 'delivery-error.json')):
        raise SystemExit('A task may still be active; install after its final result.')
label = 'com.codex.browserbridge.bridge'
plist_path = Path.home() / 'Library/LaunchAgents' / (label + '.plist')
backup = root / 'backups' / time.strftime('%Y%m%dT%H%M%S')
backup.mkdir(mode=0o700, parents=True)
if plist_path.exists():
    shutil.copy2(plist_path, backup / 'bridge.plist')
if (root / 'app').exists():
    shutil.copytree(root / 'app', backup / 'app')
shutil.copytree(source / 'app', root / 'app', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
for name in ('commands', 'logs', 'execution', 'runs'):
    (root / name).mkdir(mode=0o700, exist_ok=True)
wrapper = root / 'commands/agent-browser'
wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(str(python)) + ' ' + shlex.quote(str(root / 'app/browser_cli.py')) + ' "$@"\n')
wrapper.chmod(0o700)
(root / 'agent-browser.json').write_text(json.dumps({'provider': 'browseruse', 'autoConnect': False,
    'restoreSave': 'never', 'idleTimeout': '15m', 'ignoreHttpsErrors': False, 'allowFileAccess': False, 'plugins': []}))
plist = {'Label': label, 'ProgramArguments': [str(python), str(root / 'app/server.py')],
    'WorkingDirectory': str(root), 'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 10,
    'ProcessType': 'Background', 'ExitTimeOut': 70,
    'EnvironmentVariables': {'HOME': str(Path.home()), 'PATH': str(Path.home() / '.local/bin') + ':/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin', 'CODEX_BROWSER_BRIDGE_HOME': str(root)},
    'StandardOutPath': str(root / 'logs/bridge.out.log'), 'StandardErrorPath': str(root / 'logs/bridge.err.log')}
plist_path.parent.mkdir(parents=True, exist_ok=True)
plist_path.write_bytes(plistlib.dumps(plist))
domain = 'gui/' + str(os.getuid())
subprocess.run(['launchctl', 'bootout', domain + '/' + label], capture_output=True)
subprocess.run(['launchctl', 'bootstrap', domain, str(plist_path)], check=True)
print(json.dumps({'installed': True, 'config_and_tunnel_preserved': True, 'tool': 'navegar'}))
