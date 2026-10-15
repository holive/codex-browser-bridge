"""Prepare an on-demand stdio MCP installation without storing API keys."""
import argparse
import json
import os
import shlex
import shutil
from pathlib import Path

os.umask(0o077)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--home', required=True)
parser.add_argument('--agent-browser')
args = parser.parse_args()
root = Path(args.home).expanduser().resolve()
source = Path(__file__).resolve().parents[1]
python = root / '.venv/bin/python'
if not python.exists():
    raise SystemExit('Prepare .venv and install requirements.txt first.')
codex = shutil.which('codex')
agent = args.agent_browser or shutil.which('agent-browser') or str(root / 'tools/node_modules/.bin/agent-browser')
if not codex or not Path(agent).is_file():
    raise SystemExit('Codex and agent-browser must be installed first.')
for name in ('app', 'commands', 'runs', 'execution'):
    (root / name).mkdir(mode=0o700, parents=True, exist_ok=True)
root.chmod(0o700)
shutil.copytree(source / 'app', root / 'app', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
p = root / 'config.json'
config = json.loads(p.read_text()) if p.exists() else {}
config.update({'codex_bin': codex, 'agent_browser_bin': str(Path(agent).resolve())})
# Secrets arrive from the MCP process environment; do not save them here.
p.write_text(json.dumps(config, indent=2));p.chmod(0o600)
(root / 'agent-browser.json').write_text(json.dumps({'provider':'browseruse','autoConnect':False,
    'restoreSave':'never','idleTimeout':'15m','ignoreHttpsErrors':False,'allowFileAccess':False,'plugins':[]}))
wrapper = root / 'commands/agent-browser'
wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(str(python))+' '+shlex.quote(str(root / 'app/browser_cli.py'))+' "$@"\n');wrapper.chmod(0o700)
entry = root / 'run-command.sh'
entry.write_text('#!/bin/sh\nexport CODEX_BROWSER_BRIDGE_HOME='+shlex.quote(str(root))+'\nexec '+shlex.quote(str(python))+' '+shlex.quote(str(root / 'app/server.py'))+' --transport stdio\n');entry.chmod(0o700)
print(json.dumps({'command':str(entry),'tool':'navegar','transport':'stdio','secrets_saved':False,
                  'required_environment':['BROWSER_USE_API_KEY','BROWSER_USE_PROFILE_ID']}))
