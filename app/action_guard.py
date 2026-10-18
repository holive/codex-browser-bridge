"""Deterministic action guard for read-only browser research.

Called by browser_cli.py before click/fill/press. It resolves the target from
the live page (snapshot refs or the focused element) and refuses actions that
could send, publish, submit, post, delete, buy, share, follow or log out.
Fails closed: if the target cannot be identified, the action is refused.
Logs only the action, role and reason (never names or page text).
"""
import json
import re
import time
import unicodedata
from pathlib import Path

# Whole-word terms (accent-insensitive, lowercase) that mark a write action.
DANGER_TERMS = [
    # send / reply / message
    "send", "enviar", "envie", "envia", "reply", "responder", "responda", "comment", "comentar",
    "message", "mensagem", "nova mensagem", "dm", "forward", "encaminhar", "reenviar", "resend",
    "mark as read", "marcar como lida", "marcar como lido", "mark read",
    "recipient", "recipients", "destinatario", "destinatarios", "cc", "bcc", "cco",
    # publish / post / submit
    "post", "postar", "publish", "publicar", "tweet", "tuitar", "repost", "retweet", "repostar",
    "quote", "citar", "retuitar", "submit", "submeter", "enviar formulario", "upload", "carregar arquivo",
    # delete / destructive
    "delete", "deletar", "excluir", "apagar", "remove", "remover", "trash", "lixeira",
    "archive", "arquivar", "clear", "limpar", "discard", "descartar", "revoke", "revogar",
    # money / commitments
    "buy", "comprar", "purchase", "pay", "pagar", "checkout", "place order", "fazer pedido", "assinar",
    "subscribe", "donate", "doar", "contratar", "reservar",
    # confirm / save / change
    "confirm", "confirmar", "save", "salvar", "save changes", "salvar alteracoes",
    "edit", "editar", "accept", "aceitar", "approve", "aprovar", "agree", "concordo",
    "allow", "permitir", "authorize", "autorizar",
    # social graph / account
    "share", "compartilhar", "follow", "seguir", "unfollow", "deixar de seguir", "like", "curtir",
    "block", "bloquear", "report", "denunciar", "mute", "silenciar", "invite", "convidar",
    "join", "entrar no grupo", "participar", "leave", "sair", "log out", "logout", "sign out",
    "desconectar", "sign up", "cadastrar", "criar conta", "change password", "alterar senha",
    "call", "ligar", "video call", "chamada",
]
# Links and content rows only navigate/open (a chat, a post); opening a
# composer does not send, and sending needs a button or Enter, which are
# checked with the full list. Their names are usually content (post text, a
# chat preview), so only the narrow session-ending set applies to them.
# Buttons, menu items and everything else get the full list at any length.
LINK_ROLES = {"link", "listitem", "row", "gridcell", "cell", "article", "option", "treeitem",
              "heading", "img", "tab"}
NARROW_TERMS = ["log out", "logout", "sign out", "sair", "desconectar", "delete account",
                "excluir conta", "unsubscribe", "cancelar inscricao"]
_TERMS = sorted({t for t in DANGER_TERMS}, key=len, reverse=True)
DANGER_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in _TERMS) + r")(?![a-z0-9])")
NARROW_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in NARROW_TERMS) + r")(?![a-z0-9])")
SEARCH_RE = re.compile(r"(?<![a-z0-9])(search|pesquis\w*|busca\w*|procur\w*|find|localizar|filtr\w*|lookup)(?![a-z0-9])")
DENY_CLICK_ROLES = {"textbox", "checkbox", "switch", "radio", "spinbutton", "slider",
                    "menuitemcheckbox", "menuitemradio"}
NAMELESS_DENY_ROLES = {"button", "menuitem"}
REF_RE = re.compile(r"^@e[0-9]{1,6}$")

FOCUS_JS = r"""(() => {
  let el = document.activeElement, depth = 0;
  while (el && depth < 10) {
    depth++;
    if (el.shadowRoot && el.shadowRoot.activeElement) { el = el.shadowRoot.activeElement; continue; }
    if (el.tagName === 'IFRAME') { try { const d = el.contentDocument; if (d && d.activeElement) { el = d.activeElement; continue; } } catch (e) { return JSON.stringify({opaque: true}); } }
    break;
  }
  if (!el || el === document.body || el === document.documentElement) return JSON.stringify({none: true});
  const lbl = [];
  const by = el.getAttribute('aria-labelledby');
  if (by) by.split(/\s+/).forEach(id => { const n = el.ownerDocument.getElementById(id); if (n) lbl.push(n.textContent || ''); });
  if (el.labels) Array.from(el.labels).forEach(l => lbl.push(l.textContent || ''));
  const form = el.form || el.closest('form');
  return JSON.stringify({
    tag: el.tagName.toLowerCase(), type: (el.getAttribute('type') || '').toLowerCase(),
    role: (el.getAttribute('role') || '').toLowerCase(), editable: !!el.isContentEditable,
    text: [el.getAttribute('aria-label'), el.getAttribute('placeholder'), el.getAttribute('name'),
           el.getAttribute('title'), el.id, el.getAttribute('data-testid'), lbl.join(' ')].filter(Boolean).join(' ').slice(0, 400),
    search_region: !!el.closest('[role=search],[role=searchbox],[type=search]'),
    form_hint: form ? [form.getAttribute('role'), form.getAttribute('action'), form.getAttribute('aria-label'), form.id, form.getAttribute('name')].filter(Boolean).join(' ').slice(0, 300) : ''
  });
})()"""


class Blocked(Exception):
    pass


ZERO_WIDTH = re.compile("[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


def norm(value):
    text = ZERO_WIDTH.sub("", str(value or ""))
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # SendNow -> Send Now
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", text).strip()


def danger(value, narrow=False):
    text = norm(value)
    m = (NARROW_RE if narrow else DANGER_RE).search(text)
    return m.group(1) if m else None


def is_search(value):
    return bool(SEARCH_RE.search(norm(value)))


def _json(out):
    data = json.loads(out)
    if not data.get("success"):
        raise Blocked("estado da página indisponível")
    return data.get("data") or {}


def ref_info(browser, ref):
    refs = _json(browser(["snapshot", "-i", "--json"])).get("refs") or {}
    info = refs.get(ref[1:])
    if not isinstance(info, dict):
        raise Blocked("ref não encontrada; faça snapshot -i de novo")
    return (info.get("role") or "").lower(), info.get("name") or ""


def focused(browser):
    raw = _json(browser(["eval", FOCUS_JS, "--json"])).get("result")
    return json.loads(raw) if isinstance(raw, str) else {}


def decide(cmd, args, browser):
    """Return (role, reason) when allowed; raise Blocked otherwise."""
    if cmd in ("click", "fill"):
        if len(args) < 2 or not REF_RE.match(args[1]):
            raise Blocked("use somente refs @eN do snapshot")
        role, name = ref_info(browser, args[1])
        if not role:
            raise Blocked("papel do alvo desconhecido")
        term = danger(name, narrow=(cmd == "click" and role in LINK_ROLES))
        if cmd == "click":
            if len(args) != 2:
                raise Blocked("click aceita só uma ref")
            if term:
                raise Blocked("alvo parece ação de escrita (%s)" % term)
            if role in DENY_CLICK_ROLES:
                raise Blocked("clique em campo/controle de formulário (%s)" % role)
            if role in NAMELESS_DENY_ROLES and not norm(name):
                raise Blocked("botão sem nome; não dá para confirmar que é só navegação")
            return role, "ok"
        if len(args) != 3 or len(args[2]) > 300:
            raise Blocked("fill aceita uma ref e uma consulta curta")
        if term:
            raise Blocked("campo parece de mensagem/escrita (%s)" % term)
        if role == "searchbox" or (role in ("combobox", "textbox") and is_search(name)):
            return role, "ok"
        raise Blocked("fill só em campos de busca")
    if cmd == "press":
        f = focused(browser)
        if f.get("none") or f.get("opaque") or not f:
            raise Blocked("Enter sem campo de busca focado")
        hint = " ".join([f.get("text", ""), f.get("form_hint", "")])
        term = danger(hint)
        searchy = (f.get("type") == "search" or f.get("role") == "searchbox" or f.get("search_region")
                   or is_search(hint))
        # Composers are textareas or contenteditable: never Enter there.
        field = f.get("tag") == "input" and not f.get("editable") and f.get("type") in ("", "text", "search")
        if field and searchy and not term:
            return f.get("role") or f.get("tag"), "ok"
        raise Blocked("Enter só para submeter busca")
    return None, "n/a"


def guard(cmd, args, browser, log_dir=None):
    """Raise SystemExit(2) with a clear message when blocked. Logs no page text."""
    if cmd not in ("click", "fill", "press"):
        return
    role, outcome = None, "allowed"
    try:
        role, _ = decide(cmd, args, browser)
    except Blocked as exc:
        outcome = "blocked: " + str(exc)
    except Exception as exc:  # fail closed
        outcome = "blocked: verificação falhou (%s)" % type(exc).__name__
    if log_dir:
        try:
            with (Path(log_dir) / "action-guard.jsonl").open("a") as fh:
                fh.write(json.dumps({"ts": round(time.time(), 3), "action": cmd, "role": role,
                                     "outcome": outcome}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    if outcome != "allowed":
        import sys
        print("Ação bloqueada pela trava de leitura: " + outcome[9:] +
              ". Se a tarefa exigir isso, termine com out_of_scope.", file=sys.stderr)
        sys.exit(2)
