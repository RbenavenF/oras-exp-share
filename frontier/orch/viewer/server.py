#!/usr/bin/env python3
"""Read-only, dependency-free local dashboard for frontier-orch."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

STATIC = Path(__file__).parent / 'static'
MAX_TAIL = 160_000


def read_json(path, default, warnings):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        warnings.append(f'{path.name}: {type(exc).__name__}')
        return default


def tail(path, limit=MAX_TAIL):
    try:
        with path.open('rb') as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - limit))
            data = f.read(limit).decode('utf-8', errors='replace')
        return data.splitlines()[1:] if size > limit else data.splitlines()
    except OSError:
        return []


def clean(value, limit=700):
    s = str(value or '')
    s = re.sub(r'(?i)((?:api[_-]?key|authorization|password|token|secret)\s*[=:]\s*)[^\s,;]+', r'\1[oculto]', s)
    s = re.sub(r'\b(?:sk-[\w-]{12,}|gh[pousr]_[\w]+)\b', '[oculto]', s)
    return s[:limit]


def events(lines):
    result = []
    for line in lines:
        try:
            data = json.loads(line)
        except ValueError:
            if line.startswith('--- exit'):
                result.append({'kind': 'system', 'text': line, 'status': 'completed'})
            continue
        if not isinstance(data, dict):
            continue
        kind = data.get('type', '')
        item = data.get('item') or {}
        if kind in ('item.started', 'item.completed', 'item.updated') and isinstance(item, dict):
            typ = item.get('type')
            if typ == 'command_execution':
                result.append({'kind': 'tool', 'text': clean(item.get('command')), 'status': item.get('status', 'running' if kind == 'item.started' else 'completed'), 'id': item.get('id')})
            elif typ == 'agent_message':
                result.append({'kind': 'message', 'text': clean(item.get('text')), 'status': 'completed'})
            elif typ == 'mcp_tool_call':
                result.append({'kind': 'tool', 'text': clean(f"{item.get('server', '')} / {item.get('tool', '')}"), 'status': item.get('status', 'running')})
            elif typ == 'file_change':
                result.append({'kind': 'file', 'text': clean(', '.join(str(c.get('path', '')) for c in item.get('changes', []) if isinstance(c, dict))), 'status': 'completed'})
        elif kind == 'assistant':
            msg = data.get('message') or {}
            for block in msg.get('content', []) if isinstance(msg, dict) else []:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'text':
                    result.append({'kind': 'message', 'text': clean(block.get('text')), 'status': 'completed'})
                elif block.get('type') == 'tool_use':
                    inp = block.get('input') or {}
                    detail = inp.get('command') or inp.get('file_path') or inp.get('pattern') or ''
                    result.append({'kind': 'tool', 'text': clean(f"{block.get('name', '')} {detail}"), 'status': 'invoked'})
        elif kind in ('error', 'turn.failed') or (kind == 'result' and data.get('is_error')):
            err = data.get('error') or {}
            result.append({'kind': 'error', 'text': clean(data.get('message') or (err.get('message') if isinstance(err, dict) else err) or data.get('result')), 'status': 'failed'})
    return result[-35:]


def process_state(root, agents, lane_root):
    workers = {name: [] for name in agents}
    supervisors = []
    try:
        entries = list(Path('/proc').iterdir())
    except OSError:
        return workers, supervisors
    for p in entries:
        if not p.name.isdigit():
            continue
        try:
            args = (p / 'cmdline').read_bytes().decode(errors='replace').split('\0')
            cwd = (p / 'cwd').resolve()
            if cwd != root and not cwd.is_relative_to(root):
                continue
            if 'auto' in args and any(Path(a).name in ('frontier-orch', 'frontier_orch.py') for a in args[:3]):
                supervisors.append(int(p.name))
            for name in agents:
                lane = root / lane_root / name
                if cwd == lane or cwd.is_relative_to(lane):
                    if any(Path(a).name == name for a in args[:3]) and ('exec' in args or '-p' in args):
                        workers[name].append(int(p.name))
        except (OSError, ValueError):
            continue
    return workers, supervisors


class Snapshot:
    def __init__(self, root):
        self.root = root.resolve()
        self.lock = threading.Lock()
        self.cached = None
        self.updated = 0

    def get(self):
        with self.lock:
            if self.cached and time.monotonic() - self.updated < 2:
                return self.cached
            self.cached = self.build()
            self.updated = time.monotonic()
            return self.cached

    def build(self):
        root, warnings, now = self.root, [], time.time()
        work = root / 'work/orch'
        state = read_json(work / 'state.json', {}, warnings)
        cfg = read_json(root / 'frontier/orch/config.json', {}, warnings)
        task_data = read_json(root / 'frontier/orch/tasks.json', {}, warnings)
        tasks = task_data.get('tasks', [])
        statuses = {t['id']: t.get('status', 'pending') for t in tasks}
        for index, task in enumerate(tasks):
            task['order'] = index + 1
            task['waiting_for'] = [dep for dep in task.get('after', []) if statuses.get(dep) != 'done']
            task['ready'] = task.get('status') in ('pending', 'in_progress') and not task['waiting_for']
            task['lane'] = state.get('lane_of', {}).get(task['id'])
        agents = cfg.get('agents', {})
        lane_root = cfg.get('lanes', {}).get('root', 'work/orch/lanes')
        processes, supervisor = process_state(root, agents, lane_root)
        workers = []
        for name, spec in agents.items():
            logs = sorted((work / 'logs').glob(f'*-{name}-*.log'), reverse=True)
            log = logs[0] if logs else None
            lines = tail(log) if log else []
            recent = events(lines)
            match = re.match(r'\d{8}-\d{6}-[^-]+-(.+)\.log$', log.name) if log else None
            task_id = match.group(1) if match else None
            reset = state.get('cooldown', {}).get(name, 0)
            auth = state.get('needs_login', {}).get(name)
            active = bool(processes.get(name))
            status = 'working' if active else 'login' if auth else 'cooldown' if reset > now else 'idle'
            task = next((t for t in tasks if t['id'] == task_id), None)
            command = spec.get('new', [])
            model = next((part.split('=', 1)[1].strip('"') for part in command if part.startswith('model=')), None)
            workers.append({'name': name, 'status': status, 'pids': processes.get(name, []),
                'task_id': task_id, 'task_title': task.get('title') if task else None,
                'cooldown_until': reset or None, 'needs_login': bool(auth), 'model': model,
                'last_update': log.stat().st_mtime if log else None, 'log': log.name if log else None,
                'events': recent, 'gdb_port': cfg.get('lanes', {}).get('agents', {}).get(name, {}).get('gdb_port'),
                'lane': str(Path(lane_root) / name), 'fresh_sessions': spec.get('fresh_sessions', False)})
        try:
            journal = tail(root / 'frontier/BITACORA.md', 24_000)
            starts = [i for i, line in enumerate(journal) if line.startswith('## ')]
            journal = '\n'.join(journal[starts[-1]:]) if starts else '\n'.join(journal[-50:])
        except OSError:
            journal = ''
        return {'generated_at': now, 'root': str(root), 'tasks': tasks, 'counts': dict(Counter(t.get('status', 'pending') for t in tasks)),
            'workers': workers, 'supervisor': {'running': bool(supervisor), 'pids': supervisor, 'runs': state.get('runs', 0),
                'controls': [n for n in ('stop', 'drain') if (work / n).exists()],
                'events': [clean(line, 1000) for line in tail(work / 'orch.log', 18_000)[-30:]],
                'last_update': (work / 'state.json').stat().st_mtime if (work / 'state.json').exists() else None},
            'journal': journal, 'warnings': warnings,
            'sources': ['frontier/orch/tasks.json', 'frontier/orch/config.json', 'work/orch/state.json', 'work/orch/logs/', 'work/orch/orch.log', 'frontier/BITACORA.md', '/proc (procesos)']}


def handler_for(snapshot):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/state':
                try:
                    self.respond(json.dumps(snapshot.get(), ensure_ascii=False).encode(), 'application/json; charset=utf-8')
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    self.respond(json.dumps({'error': f'No se puede leer el estado: {type(exc).__name__}'}).encode(), 'application/json', 503)
            elif path in ('/', '/app.js', '/style.css'):
                name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[path]
                mime = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript; charset=utf-8', '/style.css': 'text/css; charset=utf-8'}[path]
                self.respond((STATIC / name).read_bytes(), mime)
            else:
                self.respond(b'Not found', 'text/plain', 404)

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            self.respond(b'Read only', 'text/plain', 405)

        do_PUT = do_DELETE = do_PATCH = do_POST

        def respond(self, body, mime, status=200):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Checkout principal que contiene work/orch')
    parser.add_argument('--host', choices=['127.0.0.1'], default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8787)
    args = parser.parse_args()
    if not (args.root / 'frontier/orch/tasks.json').is_file():
        parser.error('--root debe apuntar al checkout del orquestador')
    server = ThreadingHTTPServer((args.host, args.port), handler_for(Snapshot(args.root)))
    print(f'Frontier · visor de solo lectura → http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
