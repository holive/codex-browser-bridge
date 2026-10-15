"""Local prerequisite checks. No browser sessions, model calls, or secret values."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CODEX_FLAGS = ('--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
               '--approve-for-me', '--json', '--output-schema', '--output-last-message')
BROWSER_FLAGS = ('--provider', '--namespace', '--session', '--config')


def probe(binary, *args):
    try:
        proc = subprocess.run([binary, *args], capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr
    except (OSError, subprocess.TimeoutExpired):
        return -1, ''


def diagnose(root):
    root = Path(root).expanduser().resolve()
    checks = []
    warnings = []
    def add(name, ok, action):
        checks.append({'check': name, 'ok': bool(ok), **({} if ok else {'action': action})})
    try:
        config = json.loads((root / 'config.json').read_text())
        if not isinstance(config, dict):
            raise ValueError('Expected object')
    except (OSError, ValueError):
        config = {}
        add('private_config', False, 'Run setup; if config.json exists, repair its JSON without discarding secrets.')
    add('host_locking', os.name == 'posix', 'Use a POSIX host; the deployed environment is Linux.')
    add('python', sys.version_info >= (3, 11), 'Run setup with Python 3.11+.')
    try:
        from mcp.server import MCPServer
        add('mcp_sdk', bool(MCPServer), '')
    except ImportError:
        add('mcp_sdk', False, 'Rerun setup to install the pinned requirements into the runtime .venv.')
    versions_file = root / 'dependencies.json'
    versions = json.loads(versions_file.read_text()) if versions_file.exists() else {}
    for name, key, flags in (('codex', 'codex_bin', CODEX_FLAGS), ('agent-browser', 'agent_browser_bin', BROWSER_FLAGS)):
        configured = config.get(key)
        binary = shutil.which(str(configured)) if configured else None
        add(name + '_executable', binary, 'Rerun setup, or pass an explicit executable path.')
        if not binary:
            continue
        code, output = probe(binary, '--version')
        expected = versions.get(name, {}).get('version')
        add(name + '_version', code == 0, 'Check that the installed executable starts; reinstall if necessary.')
        # Version output is not echoed: subprocess output can contain local configuration.
        if expected and code == 0 and expected not in output.split():
            warnings.append(name + ': differs from the recorded version ' + expected + '; required flags are checked separately.')
        code, output = probe(binary, *(('exec', '--help') if name == 'codex' else ('--help',)))
        add(name + '_interface', code == 0 and all(flag in output for flag in flags),
            'CLI interface changed or executable failed. Compare its current help with the bridge adapter; do not bypass approvals.')
        if name == 'codex':
            code, _ = probe(binary, 'login', 'status')
            add('codex_auth', code == 0, 'Authenticate Codex on this host using its supported login flow, then rerun --check.')
    for env_key, config_key in (('BROWSER_USE_API_KEY', 'browser_use_api_key'), ('BROWSER_USE_PROFILE_ID', 'profile_id')):
        add(env_key, bool(os.environ.get(env_key) or config.get(config_key)), 'Provide ' + env_key + ' privately to the MCP process, then rerun --check in the same environment.')
    add('previous_run_clear', not (root / 'active-run.json').exists(), 'An active or unconfirmed run exists. Wait for its final result, or inspect the private journal and Cloud session before clearing it.')
    add('launcher', (root / 'run-command.sh').is_file() and os.access(root / 'run-command.sh', os.X_OK), 'Rerun setup to generate the command launcher.')
    return {'status': 'ready' if all(c['ok'] for c in checks) else 'requires_setup',
            'checks': checks, 'warnings': warnings,
            'scope': 'Local prerequisites only; credentials, model access and Cloud profile are not remotely validated.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.environ.get('CODEX_BROWSER_BRIDGE_HOME', str(Path.home() / '.local/share/codex-browser-bridge')))
    args = parser.parse_args()
    try:
        result = diagnose(args.home)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result['status'] == 'ready' else 1)
    except (OSError, ValueError):
        print(json.dumps({'status': 'requires_setup', 'error': 'Invalid local diagnostic configuration; inspect it privately.'}))
        sys.exit(1)
