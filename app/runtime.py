"""Public application code; private configuration and runs live elsewhere."""
import json
import os
import sys
from pathlib import Path

os.umask(0o077)
default = (Path.home() / 'Library/Application Support/CodexBrowserBridge' if sys.platform == 'darwin'
           else Path.home() / '.local/share/codex-browser-bridge')
ROOT = Path(os.environ.get('CODEX_BROWSER_BRIDGE_HOME', str(default))).expanduser().resolve()
CONFIG = json.loads((ROOT / 'config.json').read_text())
for name in ('runs', 'execution', 'commands'):
    (ROOT / name).mkdir(mode=0o700, parents=True, exist_ok=True)
