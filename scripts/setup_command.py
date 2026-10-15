"""Install or repair the private command MCP runtime; never persist environment secrets."""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
VERSIONS = json.loads((SOURCE / 'dependencies.json').read_text())


def run(args):
    # Child output goes to stderr so stdout remains a single reusable setup report.
    subprocess.run([str(a) for a in args], check=True, stdout=sys.stderr, stderr=sys.stderr)


def executable(value):
    if not value:
        return None
    found = shutil.which(str(value))
    return str(Path(found).absolute()) if found else None


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=os.environ.get('CODEX_BROWSER_BRIDGE_HOME', str(Path.home() / '.local/share/codex-browser-bridge')))
    parser.add_argument('--codex', help='Use an existing Codex executable')
    parser.add_argument('--agent-browser', help='Use an existing agent-browser executable')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11+ is required; use a compatible Python to run setup.')
    root = Path(args.home).expanduser().resolve()
    if root == SOURCE or root.is_relative_to(SOURCE):
        parser.error('Choose a private runtime folder outside the source repository.')
    # Read before writing anything: malformed configuration must not be overwritten.
    config_path = root / 'config.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    if not isinstance(config, dict):
        parser.error('Private config.json must contain an object; it was not changed.')
    selected = {}
    packages = []
    for name, option, key in (('codex', args.codex, 'codex_bin'), ('agent-browser', args.agent_browser, 'agent_browser_bin')):
        if option:
            found = executable(option)
            if not found:
                parser.error(f'{name} executable not found; check the explicit path.')
        else:
            found = executable(config.get(key)) or executable(name) or executable(root / 'tools/node_modules/.bin' / name)
        if found:
            selected[key] = found
        else:
            packages.append(VERSIONS[name]['package'] + '@' + VERSIONS[name]['version'])
            selected[key] = str(root / 'tools/node_modules/.bin' / name)
    if packages:
        if not (shutil.which('npm') and shutil.which('node')):
            parser.error('Install Node.js 20+ with npm, then rerun setup; missing CLI dependencies were not installed.')
        node = subprocess.run([shutil.which('node'), '--version'], capture_output=True, text=True, timeout=15)
        if node.returncode or int(node.stdout.strip().lstrip('v').split('.')[0]) < 20:
            parser.error('Node.js 20+ is required to install missing CLIs; upgrade Node and rerun setup.')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    python = root / '.venv/bin/python'
    if not python.exists():
        run([sys.executable, '-m', 'venv', root / '.venv'])
    run([python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', SOURCE / 'requirements.txt'])
    if packages:
        run([shutil.which('npm'), 'install', '--prefix', root / 'tools', '--no-audit', '--no-fund', *packages])
    for name in ('app', 'commands', 'runs', 'execution'):
        (root / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copytree(SOURCE / 'app', root / 'app', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(SOURCE / 'dependencies.json', root / 'dependencies.json')
    config.update(selected)
    config.setdefault('codex_model', 'gpt-6.1-sol')
    config.setdefault('codex_reasoning_effort', 'high')
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    config_path.chmod(0o600)
    (root / 'agent-browser.json').write_text(json.dumps({
        'provider': 'browseruse', 'autoConnect': False, 'restoreSave': 'never',
        'idleTimeout': '15m', 'ignoreHttpsErrors': False, 'allowFileAccess': False, 'plugins': []}))
    wrapper = root / 'commands/agent-browser'
    wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(str(python)) + ' ' + shlex.quote(str(root / 'app/browser_cli.py')) + ' "$@"\n')
    wrapper.chmod(0o700)
    entry = root / 'run-command.sh'
    entry.write_text('#!/bin/sh\nexport CODEX_BROWSER_BRIDGE_HOME=' + shlex.quote(str(root)) + '\nexec ' + shlex.quote(str(python)) + ' ' + shlex.quote(str(root / 'app/server.py')) + ' "$@"\n')
    entry.chmod(0o700)
    report = subprocess.run([python, root / 'app/diagnostics.py', '--home', root], capture_output=True, text=True)
    if report.returncode not in (0, 1):
        raise SystemExit('Runtime diagnostics failed; run app/diagnostics.py directly for local diagnosis.')
    print(json.dumps({'command': str(entry), 'transport': 'stdio', 'tool': 'navegar',
                      'secrets_saved_from_environment': False, 'diagnostics': json.loads(report.stdout)}, ensure_ascii=False))
    return 0 if report.returncode == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        # Avoid echoing commands, configuration contents, or registry credentials.
        print('Setup failed (' + type(exc).__name__ + '). Private configuration was not reset; fix the failing prerequisite and rerun.', file=sys.stderr)
        sys.exit(2)
