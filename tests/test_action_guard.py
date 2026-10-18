"""Offline checks for app/action_guard.py with a fake browser (no Chrome, no network)."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import action_guard as g


def fake(refs=None, focus=None):
    def browser(args):
        if args[:2] == ['snapshot', '-i']:
            return json.dumps({'success': True, 'data': {'refs': refs or {}}})
        if args[0] == 'eval':
            return json.dumps({'success': True, 'data': {'result': json.dumps(focus or {'none': True})}})
        raise AssertionError(args)
    return browser


def allowed(cmd, args, **kw):
    try:
        g.decide(cmd, args, fake(**kw))
        return True
    except g.Blocked:
        return False


class ActionGuard(unittest.TestCase):
    refs = {'e1': {'role': 'link', 'name': 'Next page'}, 'e2': {'role': 'button', 'name': 'Send'},
            'e3': {'role': 'button', 'name': 'Publicar'}, 'e4': {'role': 'searchbox', 'name': 'Search'},
            'e5': {'role': 'textbox', 'name': 'Write a message'}, 'e6': {'role': 'button', 'name': ''},
            'e7': {'role': 'button', 'name': 'Show more'}, 'e8': {'role': 'button', 'name': 'Excluir'}}

    def test_click(self):
        self.assertTrue(allowed('click', ['click', '@e1'], refs=self.refs))
        self.assertTrue(allowed('click', ['click', '@e7'], refs=self.refs))
        for ref in ('@e2', '@e3', '@e6', '@e8', '@e5', '@e99'):
            self.assertFalse(allowed('click', ['click', ref], refs=self.refs), ref)
        self.assertFalse(allowed('click', ['click', 'text=Send'], refs=self.refs))

    def test_fill(self):
        self.assertTrue(allowed('fill', ['fill', '@e4', 'sofa'], refs=self.refs))
        self.assertFalse(allowed('fill', ['fill', '@e5', 'hello'], refs=self.refs))
        self.assertFalse(allowed('fill', ['fill', '@e4', 'x' * 301], refs=self.refs))

    def test_enter(self):
        search = {'tag': 'input', 'type': 'search', 'role': '', 'editable': False, 'text': 'q', 'form_hint': ''}
        self.assertTrue(allowed('press', ['press', 'Enter'], focus=search))
        self.assertFalse(allowed('press', ['press', 'Enter'], focus={'none': True}))
        composer = dict(search, tag='textarea', type='', text='Search')
        self.assertFalse(allowed('press', ['press', 'Enter'], focus=composer))
        reply = dict(search, type='text', text='Reply')
        self.assertFalse(allowed('press', ['press', 'Enter'], focus=reply))

    def test_guard_fails_closed(self):
        def broken(args):
            raise RuntimeError('page gone')
        with self.assertRaises(SystemExit):
            g.guard('click', ['click', '@e1'], broken)
        self.assertIsNone(g.guard('snapshot', ['snapshot', '-i'], broken))


if __name__ == '__main__':
    unittest.main()
