import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('viewer_server', Path(__file__).with_name('server.py'))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ViewerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'frontier/orch').mkdir(parents=True)
        (self.root / 'work/orch/logs').mkdir(parents=True)
        self.write('frontier/orch/config.json', {'agents': {'codex': {'new': ['codex', 'exec', 'model="test"']}}, 'lanes': {}})
        self.write('work/orch/state.json', {'runs': 4, 'cooldown': {'codex': 4102444800}, 'lane_of': {'A': 'codex'}})
        self.write('frontier/orch/tasks.json', {'tasks': [
            {'id': 'A', 'status': 'in_progress', 'title': 'A', 'owner': 'any'},
            {'id': 'B', 'status': 'pending', 'title': 'B', 'owner': 'codex', 'after': ['A']}]})

    def write(self, path, data):
        (self.root / path).write_text(json.dumps(data))

    def snapshot(self, active=False):
        with patch.object(server, 'process_state', return_value=({'codex': [99] if active else []}, [88])):
            return server.Snapshot(self.root).get()

    def test_in_progress_is_not_active_and_dependencies_block(self):
        d = self.snapshot()
        self.assertEqual(d['workers'][0]['status'], 'cooldown')
        self.assertEqual(d['tasks'][1]['waiting_for'], ['A'])
        self.assertFalse(d['tasks'][1]['ready'])
        self.assertEqual(d['tasks'][1]['order'], 2)
        self.assertEqual(d['counts'], {'in_progress': 1, 'pending': 1})

    def test_real_process_overrides_old_cooldown(self):
        self.assertEqual(self.snapshot(active=True)['workers'][0]['status'], 'working')

    def test_partial_json_is_reported_without_mutation(self):
        p = self.root / 'work/orch/state.json'
        p.write_text('{')
        self.assertTrue(self.snapshot()['warnings'])
        self.assertEqual(p.read_text(), '{')

    def test_both_log_formats_and_partial_lines(self):
        lines = [json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'pytest', 'id': '1'}}),
            json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'report.md'}}]}}),
            '{"type":',
            json.dumps({'type': 'turn.failed', 'error': {'message': 'quota'}})]
        e = server.events(lines)
        self.assertEqual([i['kind'] for i in e], ['tool', 'tool', 'error'])
        self.assertEqual(e[0]['status'], 'running')
        self.assertEqual(e[1]['text'], 'Read report.md')
        self.assertEqual(e[2]['text'], 'quota')

    def test_tail_is_bounded(self):
        p = self.root / 'large.log'
        p.write_text('x' * 50000 + '\nlast\n')
        self.assertEqual(server.tail(p, 20), ['last'])

    def test_latest_log_matches_correct_worker_and_no_tool_output(self):
        p = self.root / 'work/orch/logs/20261115-013758-codex-A.log'
        p.write_text(json.dumps({'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'pytest', 'aggregated_output': 'PRIVATE OUTPUT'}}))
        w = self.snapshot()['workers'][0]
        self.assertEqual(w['task_id'], 'A')
        self.assertNotIn('PRIVATE OUTPUT', json.dumps(w))
        self.assertEqual(w['events'][0]['text'], 'pytest')

    def test_secrets_in_command_excerpt(self):
        self.assertEqual(server.clean('token=abc password=xyz'), 'token=[oculto] password=[oculto]')

    def test_api_and_static_are_read_only(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.handler_for(server.Snapshot(self.root)))
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{http.server_port}'
        try:
            with urlopen(base + '/api/state') as res:
                self.assertEqual(res.status, 200)
                self.assertEqual(len(json.load(res)['tasks']), 2)
            with urlopen(base + '/') as res:
                self.assertIn(b'Observatorio', res.read())
                self.assertIn("default-src 'self'", res.headers['Content-Security-Policy'])
            for path in ('/../../frontier/orch/tasks.json', '/api/state/../config.json', '/anything', '/work/orch/state.json'):
                with self.assertRaises(HTTPError) as exc:
                    urlopen(base + path)
                self.assertEqual(exc.exception.code, 404)
                exc.exception.close()
            for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                with self.assertRaises(HTTPError) as exc:
                    urlopen(Request(base + '/api/state', method=method, data=b'{}'))
                self.assertEqual(exc.exception.code, 405)
                exc.exception.close()
        finally:
            http.shutdown()
            http.server_close()
            thread.join()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
