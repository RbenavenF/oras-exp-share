"""Control boundary, supervisor locks and real blocked-task round trip."""
import json
import os
import shutil
import subprocess
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from test_server import server
import test_server as fixtures


class ControlTest(unittest.TestCase):
    setUp = fixtures.ViewerTest.setUp
    write = fixtures.ViewerTest.write

    def controller(self):
        return server.Controller(self.root)

    def blocked(self):
        p = self.root / 'frontier/orch/tasks.json'
        data = json.loads(p.read_text())
        data['tasks'][0]['status'] = 'blocked'
        data['tasks'][0]['notes'] = 'Pregunta original'
        p.write_text(json.dumps(data))

    def init_git(self):
        shutil.copy(Path(server.__file__).parents[1] / 'frontier_orch.py', self.root / 'frontier/orch/frontier_orch.py')
        (self.root / 'frontier/REPARTO.md').write_text('# Reparto\n\n## Turno\n\nlibre\n')
        (self.root / 'frontier/BITACORA.md').write_text('# Bitácora\n')
        (self.root / '.gitignore').write_text('/work\n__pycache__/\n')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), '-c', 'user.name=Test', '-c', 'user.email=test@example.com', *args], stderr=subprocess.STDOUT).decode()

    def test_key_private_persistent_and_not_in_snapshot(self):
        c = self.controller()
        self.assertEqual(os.stat(c.work / 'viewer-control.key').st_mode & 0o777, 0o600)
        self.assertEqual(c.key, self.controller().key)
        self.assertNotIn(c.key, json.dumps(server.Snapshot(self.root, c).get()))

    def test_lock_detects_supervisor_even_when_process_not_visible(self):
        c = self.controller()
        self.assertFalse(c.running())
        with c.exclusive():
            self.assertTrue(c.running())
            with self.assertRaises(server.ControlError):
                c.dispatch({'action': 'start'})

    def test_flags_are_reversible_and_do_not_touch_tasks(self):
        c = self.controller()
        before = (self.root / 'frontier/orch/tasks.json').read_bytes()
        c.dispatch({'action': 'drain'})
        c.dispatch({'action': 'stop'})
        self.assertTrue((c.work / 'drain').exists())
        c.dispatch({'action': 'resume'})
        self.assertFalse((c.work / 'drain').exists())
        self.assertFalse((c.work / 'stop').exists())
        self.assertEqual(before, (self.root / 'frontier/orch/tasks.json').read_bytes())

    def test_start_named_mode_detached_no_shell_and_duplicate_guard(self):
        c = self.controller()
        child = Mock()
        child.poll.return_value = None
        with patch.object(server.subprocess, 'Popen', return_value=child) as start:
            c.dispatch({'action': 'start', 'mode': 'follow'})
            args, kw = start.call_args
            self.assertIn('--follow', args[0])
            self.assertTrue(kw['start_new_session'])
            self.assertNotIn('shell', kw)
            with self.assertRaises(server.ControlError):
                c.dispatch({'action': 'start'})
            self.assertEqual(start.call_count, 1)

    def test_orphan_worker_refuses_start(self):
        c = self.controller()
        with patch.object(server, 'process_state', return_value=({'codex': [123]}, [])):
            with self.assertRaises(server.ControlError):
                c.dispatch({'action': 'start'})

    def test_reply_waits_for_lock_then_commits_and_preserves_notes(self):
        self.blocked()
        self.init_git()
        c = self.controller()
        with c.exclusive():
            c.dispatch({'action': 'reply', 'task_id': 'A', 'answer': 'Sí, usa la opción 2; $(touch /tmp/no) es texto.'})
            self.assertTrue((c.work / 'stop').exists())
            self.assertEqual(c.status()['replies'][0]['status'], 'pending')
            self.assertEqual(json.loads((self.root / 'frontier/orch/tasks.json').read_text())['tasks'][0]['status'], 'blocked')
        c.apply_replies()
        self.assertEqual(c.status()['replies'][0]['status'], 'applied')
        task = json.loads((self.root / 'frontier/orch/tasks.json').read_text())['tasks'][0]
        self.assertEqual(task['status'], 'in_progress')
        self.assertIn('Pregunta original', task['notes'])
        self.assertIn('$(touch /tmp/no)', task['notes'])
        self.assertIn('libre', (self.root / 'frontier/REPARTO.md').read_text())
        self.assertIn('respuesta web a A', self.git('log', '--oneline'))
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_stale_reply_never_reopens_changed_task(self):
        self.blocked()
        c = self.controller()
        with c.exclusive():
            c.dispatch({'action': 'reply', 'task_id': 'A', 'answer': 'Confirmado'})
        p = self.root / 'frontier/orch/tasks.json'
        d = json.loads(p.read_text())
        d['tasks'][0]['status'] = 'done'
        p.write_text(json.dumps(d))
        self.init_git()
        c.apply_replies()
        self.assertEqual(c.status()['replies'][0]['status'], 'failed')
        self.assertEqual(json.loads(p.read_text())['tasks'][0]['status'], 'done')

    def test_invalid_reply_and_unknown_action(self):
        c = self.controller()
        for payload in ({'action': 'exec', 'command': 'sh'}, {'action': 'reply', 'task_id': 'A', 'answer': 'Sí'}, {'action': 'reply', 'answer': ''}, {'action': 'start', 'mode': ';shell'}):
            with self.assertRaises(server.ControlError):
                c.dispatch(payload)

    def test_http_requires_key_origin_json_and_bounds(self):
        c = self.controller()
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.handler_for(server.Snapshot(self.root, c)))
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{http.server_port}'
        def send(headers, body=b'{"action":"drain"}'):
            return urlopen(Request(base + '/api/control', data=body, headers=headers))
        valid = {'Authorization': 'Bearer ' + c.key, 'Origin': base, 'Content-Type': 'application/json'}
        try:
            for headers, status in (({}, 403), ({**valid, 'Origin': 'http://attacker.invalid'}, 403), ({**valid, 'Authorization': 'Bearer bad'}, 401), ({**valid, 'Content-Type': 'text/plain'}, 415)):
                with self.assertRaises(HTTPError) as exc:
                    send(headers)
                self.assertEqual(exc.exception.code, status)
                exc.exception.close()
            self.assertFalse((c.work / 'drain').exists())
            with send(valid) as res:
                self.assertEqual(res.status, 200)
            self.assertTrue((c.work / 'drain').exists())
            with self.assertRaises(HTTPError) as exc:
                send(valid, b'x' * 64001)
            self.assertEqual(exc.exception.code, 413)
            exc.exception.close()
        finally:
            http.shutdown()
            http.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
