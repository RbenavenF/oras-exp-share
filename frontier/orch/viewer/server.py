#!/usr/bin/env python3
"""Local dashboard and optional controls for frontier-orch."""
import argparse
import fcntl
import hashlib
import importlib.util
import secrets
import subprocess
import sys
import uuid
from contextlib import contextmanager
from collections import Counter
import json
import os
from pathlib import Path
import re
import socket
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


class ControlError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


class Controller:
    """Only named actions; the supervisor lock protects stopped-only task edits."""
    def __init__(self, root):
        self.root = root.resolve()
        self.work = self.root / 'work/orch'
        self.work.mkdir(parents=True, exist_ok=True)
        self.queue = self.work / 'viewer-replies'
        self.queue.mkdir(exist_ok=True)
        key = self.work / 'viewer-control.key'
        try:
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w') as f:
                f.write(secrets.token_urlsafe(24) + '\n')
        self.key = key.read_text().strip()
        if len(self.key) < 20:
            raise ValueError('Clave local de control demasiado corta')
        self.mutex = threading.RLock()
        self.child = None

    @contextmanager
    def exclusive(self):
        with (self.work / 'orch.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ControlError('El supervisor sigue activo; espera a su parada limpia.')
            yield

    def running(self):
        if self.child and self.child.poll() is None:
            return True
        try:
            with self.exclusive():
                return False
        except ControlError:
            return True

    def status(self):
        items = []
        for p in sorted(self.queue.glob('*.json'))[-20:]:
            try:
                item = json.loads(p.read_text())
                items.append({k: item.get(k) for k in ('id', 'task_id', 'status', 'created', 'error')})
            except (OSError, ValueError):
                continue
        return {'enabled': True, 'running': self.running(), 'replies': items,
                'launch_exit': self.child.poll() if self.child else None,
                'launch_log': [clean(line, 500) for line in tail(self.work / 'viewer-supervisor.log', 4000)[-5:]]}

    def audit(self, action, message):
        with (self.work / 'viewer-actions.jsonl').open('a') as f:
            f.write(json.dumps({'at': time.time(), 'action': action, 'message': message}, ensure_ascii=False) + '\n')

    def dispatch(self, payload):
        if not isinstance(payload, dict):
            raise ControlError('Se esperaba un objeto JSON.', 400)
        action = payload.get('action')
        with self.mutex:
            if action == 'unlock':
                return 'Controles habilitados en este navegador.'
            if action in ('drain', 'stop'):
                (self.work / action).write_text(time.ctime() + '\n')
                message = 'Terminará las tareas actuales y saldrá.' if action == 'drain' else 'Terminará las ejecuciones actuales y saldrá.'
            elif action == 'resume':
                for name in ('drain', 'stop'):
                    (self.work / name).unlink(missing_ok=True)
                message = 'Parada pendiente cancelada. Si ya salió, usa Iniciar.'
            elif action == 'start':
                if self.running():
                    raise ControlError('El supervisor ya está activo.')
                self.apply_replies()
                mode = payload.get('mode', 'follow')
                flags = {'follow': ['--follow'], 'parallel': ['--parallel']}.get(mode)
                if flags is None:
                    raise ControlError('Modo de ejecución inválido.', 400)
                # Check lock again; the CLI takes the same lock before starting any worker.
                with self.exclusive():
                    cfg = json.loads((self.root / 'frontier/orch/config.json').read_text())
                    workers, _ = process_state(self.root, cfg.get('agents', {}), cfg.get('lanes', {}).get('root', 'work/orch/lanes'))
                    if any(workers.values()):
                        raise ControlError('Hay workers activos sin supervisor; revisa sus procesos antes de iniciar.')
                    for name in ('drain', 'stop'):
                        (self.work / name).unlink(missing_ok=True)
                    with (self.work / 'viewer-supervisor.log').open('ab') as log:
                        self.child = subprocess.Popen([sys.executable, str(self.root / 'frontier/orch/frontier_orch.py'),
                            'auto', '--root', str(self.root), *flags], cwd=self.root,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                message = 'Arranque solicitado. El estado confirmará si el supervisor está activo.'
            elif action == 'reply':
                task_id, answer = payload.get('task_id'), payload.get('answer')
                if not isinstance(answer, str) or not answer.strip() or len(answer) > 12000:
                    raise ControlError('Escribe una respuesta de 1 a 12000 caracteres.', 400)
                tasks = json.loads((self.root / 'frontier/orch/tasks.json').read_text())['tasks']
                task = next((t for t in tasks if t['id'] == task_id), None)
                if not task or task.get('status') != 'blocked':
                    raise ControlError('La tarea ya no está bloqueada; actualiza su detalle.')
                if any(x.get('task_id') == task_id and x.get('status') == 'pending'
                       for x in (json.loads(p.read_text()) for p in self.queue.glob('*.json'))):
                    raise ControlError('Esta tarea ya tiene una respuesta pendiente.')
                item = {'id': uuid.uuid4().hex, 'task_id': task_id, 'answer': answer.strip(),
                        'fingerprint': self.fingerprint(task), 'created': time.time(), 'status': 'pending'}
                self.save_reply(item)
                if self.running():
                    (self.work / 'stop').write_text(time.ctime() + '\n')
                    message = 'Respuesta guardada. Parada limpia solicitada; se aplicará al salir el supervisor. Después podrás iniciar de nuevo.'
                else:
                    self.apply_replies()
                    message = 'Respuesta procesada. Revisa su estado antes de iniciar.'
            else:
                raise ControlError('Acción desconocida.', 400)
            self.audit(action, message)
            return message

    @staticmethod
    def fingerprint(task):
        return hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def save_reply(self, item):
        path = self.queue / (item['id'] + '.json')
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(item, ensure_ascii=False, indent=2) + '\n')
        tmp.replace(path)

    def apply_replies(self):
        with self.mutex:
            if self.running():
                return
            with self.exclusive():
                for path in sorted(self.queue.glob('*.json')):
                    item = json.loads(path.read_text())
                    if item['status'] != 'pending':
                        continue
                    try:
                        self.apply_reply(item)
                        item['status'] = 'applied'
                    except Exception as exc:
                        item['status'], item['error'] = 'failed', clean(str(exc), 300)
                    self.save_reply(item)

    def apply_reply(self, item):
        spec = importlib.util.spec_from_file_location('frontier_web_orch', self.root / 'frontier/orch/frontier_orch.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        orch = module.Orch(self.root)
        workers, _ = process_state(self.root, orch.cfg.get('agents', {}), orch.cfg.get('lanes', {}).get('root', 'work/orch/lanes'))
        if any(workers.values()):
            raise ControlError('Quedan workers activos sin supervisor; respuesta conservada sin aplicar.')
        data = json.loads(orch.tasks_path.read_text())
        task = next((t for t in data['tasks'] if t['id'] == item['task_id']), None)
        if not task or task.get('status') != 'blocked' or self.fingerprint(task) != item['fingerprint']:
            raise ControlError('La tarea cambió desde que respondiste. Revisa el bloqueo y vuelve a responder.')
        paths = ['frontier/orch/tasks.json', 'frontier/BITACORA.md', 'frontier/REPARTO.md']
        if orch.git('status', '--porcelain', '--', *paths).strip():
            raise ControlError('Hay cambios locales pendientes en cola, turno o bitácora; no se aplicó la respuesta.')
        orch.take_turn()
        try:
            task['notes'] = (task.get('notes', '') + '\n\n[Respuesta del usuario · web]\n' + item['answer']).strip()
            task['status'] = 'in_progress'
            orch.tasks_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
            with (self.root / 'frontier/BITACORA.md').open('a') as f:
                f.write('\n\n## ' + time.strftime('%Y-%m-%d %H:%M') + ' — frontier-orch web — Respuesta a ' + task['id'] +
                        '\nEstado: en curso.\nHecho: usuario responde desde el panel; notas añadidas y tarea desbloqueada.\n'
                        'Evidencia: respuesta en tasks.json y registro local viewer-actions.jsonl.\n'
                        'Commits: el de esta entrada.\nDecisiones: aplicada con supervisor parado y lock exclusivo.\n'
                        'Siguiente paso: reanudar desde el panel cuando el usuario lo indique.\n')
            orch.commit('frontier-orch: respuesta web a ' + task['id'], *paths[:2])
            orch.state['no_progress'].pop(task['id'], None)
            orch.save_state()
        finally:
            orch.release_turn()

    def watch(self, stopped):
        while not stopped.wait(2):
            try:
                self.apply_replies()
            except (OSError, ValueError, ControlError):
                pass


class Snapshot:
    def __init__(self, root, controller=None):
        self.controller = controller
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
        return {'control': self.controller.status() if self.controller else {'enabled': False}, 'generated_at': now, 'root': str(root), 'tasks': tasks, 'counts': dict(Counter(t.get('status', 'pending') for t in tasks)),
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
            controller = snapshot.controller
            if urlsplit(self.path).path != '/api/control' or controller is None:
                self.respond(b'Controls disabled', 'text/plain', 405)
                return
            try:
                # Browser writes require an exact Origin and a secret never served by GET.
                origin = self.headers.get('Origin', '')
                if origin != 'http://' + self.headers.get('Host', ''):
                    raise ControlError('Origen no permitido.', 403)
                auth = self.headers.get('Authorization', '')
                if not secrets.compare_digest(auth.encode(), ('Bearer ' + controller.key).encode()):
                    raise ControlError('Introduce la clave local de control.', 401)
                if self.headers.get_content_type() != 'application/json':
                    raise ControlError('Se requiere JSON.', 415)
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 64000:
                    raise ControlError('Petición demasiado grande o vacía.', 413)
                self.connection.settimeout(10)
                payload = json.loads(self.rfile.read(size))
                message = controller.dispatch(payload)
                snapshot.updated = 0
                self.respond(json.dumps({'message': message}, ensure_ascii=False).encode(), 'application/json')
            except ControlError as exc:
                self.respond(json.dumps({'error': str(exc)}, ensure_ascii=False).encode(), 'application/json', exc.status)
            except (OSError, ValueError, subprocess.SubprocessError):
                self.respond(b'{"error":"No se pudo ejecutar la accion; revisa los registros locales."}', 'application/json', 500)

        def deny_mutation(self):
            self.respond(b'Method not allowed', 'text/plain', 405)

        do_PUT = do_DELETE = do_PATCH = deny_mutation

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


def create_server(host, port, snapshot):
    host = host or ('::' if socket.has_dualstack_ipv6() else '0.0.0.0')
    if ':' in host:
        class IPv6Server(ThreadingHTTPServer):
            address_family = socket.AF_INET6

            def server_bind(self):
                if socket.has_dualstack_ipv6():
                    self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                super().server_bind()
        return IPv6Server((host, port), handler_for(snapshot))
    return ThreadingHTTPServer((host, port), handler_for(snapshot))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Checkout principal que contiene work/orch')
    parser.add_argument('--host', help='Dirección de escucha; por defecto todas las interfaces IPv4/IPv6')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--control', action='store_true', help='Habilita controles con clave local en work/orch/viewer-control.key')
    args = parser.parse_args()
    if not (args.root / 'frontier/orch/tasks.json').is_file():
        parser.error('--root debe apuntar al checkout del orquestador')
    controller = Controller(args.root) if args.control else None
    stopped = threading.Event()
    if controller:
        threading.Thread(target=controller.watch, args=(stopped,), daemon=True).start()
    server = create_server(args.host, args.port, Snapshot(args.root, controller))
    print(f'Frontier · observatorio → http://localhost:{args.port} (escucha: {server.server_address[0]})', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        server.server_close()


if __name__ == '__main__':
    main()
