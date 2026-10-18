"""Local test for action_guard against a fixture page in a local headless Chrome.

Run: AGENT_BROWSER_BIN=.../agent-browser.js python3 tests/action_guard_browser_check.py
No network; uses a private agent-browser namespace.
"""
import json, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))
import action_guard as g

BIN = os.environ["AGENT_BROWSER_BIN"]
ENV = dict(os.environ, AGENT_BROWSER_EXECUTABLE_PATH=os.environ.get("CHROME", "/usr/bin/google-chrome"))
PAGE = HERE / "action_guard_fixture.html"


def browser(args):
    r = subprocess.run([BIN, "--namespace", "action-guard-test", "--session", "unit", *args],
                       capture_output=True, text=True, timeout=60, env=ENV)
    if r.returncode:
        raise RuntimeError(r.stderr[:200])
    return r.stdout.strip()


def allowed(cmd, args):
    try:
        g.decide(cmd, args, browser)
        return True
    except g.Blocked:
        return False


browser(["open", PAGE.as_uri()])
refs = json.loads(browser(["snapshot", "-i", "--json"]))["data"]["refs"]
if os.environ.get("SHOW_REFS"): print(refs)
by = {(v["role"], v["name"]): "@" + k for k, v in refs.items()}
R = lambda role, name: by[(role, name)]
cases = [
    ("click link", "click", ["click", R("link", "Próxima página")], True),
    ("click show more", "click", ["click", R("button", "Mostrar mais")], True),
    ("click search submit", "click", ["click", R("button", "Buscar")], True),
    ("click Enviar", "click", ["click", R("button", "Enviar")], False),
    ("click Publicar", "click", ["click", R("button", "Publicar")], False),
    ("click Send (form submit)", "click", ["click", R("button", "Send")], False),
    ("click X Post div", "click", ["click", R("button", "Post")], False),
    ("click compose link Post (opens composer only)", "click", ["click", R("link", "Post")], True),
    ("click SendNow", "click", ["click", R("button", "SendNow")], False),
    ("click zero-width Send", "click", ["click", R("button", "S\u200bend")], False),
    ("click long-named send button", "click", ["click", R("button", "Clique aqui para enviar a mensagem agora mesmo por favor obrigado")], False),
    ("click chat row with 'enviar' preview", "click", ["click", R("option", "Ana: vou te enviar amanhã")], True),
    ("click Excluir conversa", "click", ["click", R("button", "Excluir conversa")], False),
    ("click unnamed button", "click", ["click", R("button", "")], False),
    ("click composer textbox", "click", ["click", R("textbox", "Digite uma mensagem")], False),
    ("click checkbox", "click", ["click", R("checkbox", "Aceito os termos")], False),
    ("click long content row", "click", ["click", R("link", "Ana: vou te enviar o orçamento amanhã cedo, combinado?")], True),
    ("click unknown ref", "click", ["click", "@e9999"], False),
    ("click css selector", "click", ["click", "#send"], False),
    ("fill searchbox", "fill", ["fill", R("searchbox", "Pesquisar"), "cozinha planejada"], True),
    ("fill combobox", "fill", ["fill", R("combobox", "Search query"), "sofa"], True),
    ("fill composer", "fill", ["fill", R("textbox", "Digite uma mensagem"), "oi"], False),
    ("fill email", "fill", ["fill", R("textbox", "Email"), "a@b.c"], False),
    ("fill message", "fill", ["fill", R("textbox", "Mensagem"), "oi"], False),
    ("fill Recipients combobox", "fill", ["fill", R("combobox", "Recipients"), "x@y.z"], False),
    ("fill 'Search message' textbox", "fill", ["fill", R("textbox", "Search message"), "oi"], False),
]
fails = 0
for label, cmd, args, want in cases:
    got = allowed(cmd, args)
    ok = got == want
    fails += not ok
    print(("PASS" if ok else "FAIL"), label, "allowed" if got else "blocked")

# Enter: after filling the search box (allowed) vs focused composer / Send button.
browser(["fill", R("searchbox", "Pesquisar"), "teste"])
for label, js, want in [
    ("Enter on search field", None, True),
    ("Enter on composer", "document.getElementById('composer').focus()", False),
    ("Enter on Send button", "document.getElementById('send').focus()", False),
    ("Enter on contact textarea", "document.querySelector('textarea').focus()", False),
    ("Enter on nothing", "document.activeElement.blur()", False),
    ("Enter on X search combobox", "document.getElementById('xq').focus()", True),
    ("Enter on textarea named Pesquisar", "document.getElementById('ta').focus()", False),
]:
    if js:
        browser(["eval", js])
    got = allowed("press", ["press", "Enter"])
    ok = got == want
    fails += not ok
    print(("PASS" if ok else "FAIL"), label, "allowed" if got else "blocked")
browser(["close"])
print("FAILS", fails)
sys.exit(1 if fails else 0)
