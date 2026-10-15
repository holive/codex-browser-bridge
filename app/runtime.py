"""Public application code; private configuration and runs live elsewhere."""
import json
import os
from pathlib import Path

os.umask(0o077)
default = Path.home() / '.local/share/codex-browser-bridge'
ROOT = Path(os.environ.get('CODEX_BROWSER_BRIDGE_HOME', str(default))).expanduser().resolve()
config_path = ROOT / 'config.json'
CONFIG = json.loads(config_path.read_text()) if config_path.exists() else {}
for env_key, config_key in (('BROWSER_USE_API_KEY', 'browser_use_api_key'), ('BROWSER_USE_PROFILE_ID', 'profile_id')):
    if os.environ.get(env_key):
        CONFIG[config_key] = os.environ[env_key]
for name in ('runs', 'execution', 'commands'):
    (ROOT / name).mkdir(mode=0o700, parents=True, exist_ok=True)
