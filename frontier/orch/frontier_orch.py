#!/usr/bin/env python3
"""frontier-orch: runs the Battle Frontier tasks with Claude Code and Codex, unattended, one agent at a time.

    frontier/orch/frontier-orch auto      run until every task is done, one is blocked, or nothing makes progress
    frontier/orch/frontier-orch once      a single agent run
    frontier/orch/frontier-orch status    tasks, cooldowns and sessions
    frontier/orch/frontier-orch release   give the turn back (after a crash of the supervisor itself)

The supervisor, not the agents, decides who works: a task's owner when available, else the other agent. An agent
that hits a usage limit is cooled down and the other one inherits the task, told to inspect the uncommitted state
first. A run that ends with the task still open is resumed in the same session, without anyone typing «continúa».

Tasks: frontier/orch/tasks.json (the agents edit `status`, `notes`, `evidence`). Settings: frontier/orch/config.json.
State and logs: work/orch/ (not in git). The supervisor holds the REPARTO.md turn while it runs (one writer).
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

LIMIT = re.compile(r'usage limit|rate.?limit|quota|limit reached|too many requests|\b429\b|out of credits'
                   r'|insufficient.{0,20}credit', re.I)
TURN = re.compile(r'(## Turno\n\n)(.*)\n')
HOLDER = 'frontier-orch'


class Orch:
    def __init__(self, root, now=time.time, sleep=time.sleep, out=print):
        self.root = Path(root).resolve()
        self.cfg = json.loads((self.root / 'frontier/orch/config.json').read_text())
        self.tasks_path = self.root / 'frontier/orch/tasks.json'
        self.work = self.root / 'work/orch'
        self.state_path = self.work / 'state.json'
        self.now, self.sleep, self.out = now, sleep, out
        self.work.mkdir(parents=True, exist_ok=True)
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        for key in ('sessions', 'cooldown', 'no_progress', 'handoff'):
            self.state.setdefault(key, {})
        self.state.setdefault('runs', 0)

    # ---- files ------------------------------------------------------------------------------------------------
    def save_state(self):
        self.state_path.write_text(json.dumps(self.state, indent=2) + '\n')

    def tasks(self):
        return json.loads(self.tasks_path.read_text())['tasks']

    def set_task(self, task_id, **fields):
        data = json.loads(self.tasks_path.read_text())
        for t in data['tasks']:
            if t['id'] == task_id:
                t.update(fields)
        self.tasks_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], check=check, capture_output=True,
                              text=True).stdout

    def snapshot(self):
        head = self.git('rev-parse', 'HEAD').strip()
        dirty = self.git('status', '--porcelain', '--untracked-files=all')
        return head, hashlib.sha256(dirty.encode()).hexdigest(), hashlib.sha256(self.tasks_path.read_bytes()).hexdigest()

    # ---- the turn (frontier/REPARTO.md) -----------------------------------------------------------------------
    def turn(self):
        m = TURN.search((self.root / 'frontier/REPARTO.md').read_text())
        if not m:
            raise SystemExit('frontier/REPARTO.md has no «## Turno» line')
        return m.group(2)

    def set_turn(self, text, message):
        path = self.root / 'frontier/REPARTO.md'
        path.write_text(TURN.sub(lambda m: m.group(1) + text + '\n', path.read_text(), count=1))
        self.git('add', 'frontier/REPARTO.md')
        if self.git('diff', '--cached', '--name-only').strip():
            self.git('-c', 'user.name=rubenb114', '-c', 'user.email=rubenb114@hotmail.com', 'commit', '-q',
                     '-m', f'{message}\n\nAgent: frontier-orch', '--', 'frontier/REPARTO.md')

    def take_turn(self):
        current = self.turn()
        if not (current.startswith('libre') or current.startswith(HOLDER)):
            raise SystemExit(f'the turn is held: «{current}». Let that session release it first.')
        stamp = datetime.datetime.fromtimestamp(self.now()).strftime('%Y-%m-%d %H:%M')
        self.set_turn(f'{HOLDER} (orquestador automático), desde {stamp}', 'frontier-orch: take the turn')

    def release_turn(self):
        if self.turn().startswith(HOLDER):
            stamp = datetime.datetime.fromtimestamp(self.now()).strftime('%Y-%m-%d %H:%M')
            self.set_turn(f'libre (último: {HOLDER}, {stamp})', 'frontier-orch: release the turn')

    # ---- choosing ---------------------------------------------------------------------------------------------
    def next_task(self):
        tasks = self.tasks()
        for wanted in ('in_progress', 'pending'):
            for t in tasks:
                if t['status'] == wanted:
                    return t
        return None

    def available(self, agent):
        return self.state['cooldown'].get(agent, 0) <= self.now()

    def pick_agent(self, task):
        order = [task['owner']] + [a for a in self.cfg['agents'] if a != task['owner']]
        return next((a for a in order if a in self.cfg['agents'] and self.available(a)), None)

    # ---- running ----------------------------------------------------------------------------------------------
    def prompt(self, task, agent, resuming):
        handoff = self.state['handoff'].get(task['id'])
        lines = []
        if handoff:     # first: the inheriting agent must look at the half-done state before anything else
            lines.append(f'AVISO DE RELEVO: la sesión anterior ({handoff["from"]}) se cortó ({handoff["reason"]}), '
                         'quizá a mitad de un cambio. Antes de seguir, revisa `git status`, `git diff` y el último '
                         'commit: completa o deshaz con criterio lo que esté a medias (nunca `git stash` ni '
                         '`git reset --hard` a ciegas) y anótalo en la bitácora.')
        if resuming and not handoff:
            lines.append(f'Continúa la tarea {task["id"]} donde la dejaste. La tarea sigue abierta en '
                         'frontier/orch/tasks.json; sigue trabajando hacia sus criterios de aceptación.')
        else:
            lines.append(self.cfg['brief'].format(agent=agent, id=task['id'], title=task['title'],
                                                  design=task.get('design', '-'), owner=task['owner'],
                                                  accept=task.get('accept', '')))
        if task.get('notes'):
            lines.append(f'Notas de la tarea: {task["notes"]}')
        return '\n\n'.join(lines)

    def command(self, agent, task, resuming):
        spec = self.cfg['agents'][agent]
        session = self.state['sessions'].get(task['id'], {}).get(agent)
        resume = resuming and session is not None
        if not resume and spec['kind'] == 'claude':
            session = str(uuid.uuid4())     # Claude takes the id up front; Codex reports its thread id
        values = {'prompt': self.prompt(task, agent, resume), 'session': session or '', 'root': str(self.root)}
        return [part.format(**values) for part in spec['resume' if resume else 'new']], session, resume

    def run(self, agent, task, resuming):
        cmd, session, resumed = self.command(agent, task, resuming)
        stamp = datetime.datetime.fromtimestamp(self.now()).strftime('%Y%m%d-%H%M%S')
        log = self.work / 'logs' / f'{stamp}-{agent}-{task["id"]}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        self.out(f'[{stamp}] {agent} {"resumes" if resumed else "starts"} {task["id"]} (log {log})')
        try:
            proc = subprocess.run(cmd, cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                  timeout=self.cfg['run_timeout_minutes'] * 60)
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as e:
            stdout, stderr, code = (e.stdout or ''), (e.stderr or '') + '\n[timeout]', -1
            stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode() if isinstance(stderr, bytes) else stderr
        log.write_text(f'$ {" ".join(cmd[:3])} ...\nexit {code}\n--- stdout\n{stdout}\n--- stderr\n{stderr}\n')
        for cleanup in self.cfg.get('after_run', []):   # outside the agents' sandboxes, e.g. a lab left running
            done = subprocess.run(cleanup, cwd=self.root, capture_output=True, text=True)
            with log.open('a') as f:
                f.write(f'--- after_run {cleanup[-1][:80]!r}: exit {done.returncode}\n{done.stdout}{done.stderr}')
        parsed = parse(self.cfg['agents'][agent]['kind'], stdout, stderr, code)
        if parsed['session'] or session:
            self.state['sessions'].setdefault(task['id'], {})[agent] = parsed['session'] or session
        return parsed

    def accept(self):
        for cmd in self.cfg['acceptance']:
            proc = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, shell=isinstance(cmd, str))
            if proc.returncode:
                return False, (proc.stdout + proc.stderr)[-1500:]
        return True, ''

    def step(self):
        """One agent run. Returns 'done' (nothing left), 'stop' (needs the user), 'wait' (no agent free) or 'ran'."""
        task = self.next_task()
        if task is None:
            return 'done'
        agent = self.pick_agent(task)
        if agent is None:
            return 'wait'
        resuming = task['status'] == 'in_progress'
        if not resuming:
            self.set_task(task['id'], status='in_progress')
        before = self.snapshot()        # after the status change, so a run that changes nothing counts as none
        result = self.run(agent, task, resuming)
        self.state['runs'] += 1
        if result['limited']:
            self.state['cooldown'][agent] = self.now() + self.cfg['cooldown_minutes'] * 60
            self.state['handoff'][task['id']] = {'from': agent, 'reason': 'límite de uso: ' + result['message'][:200]}
            self.out(f'  {agent} hit a usage limit; cooled down {self.cfg["cooldown_minutes"]} min')
            self.save_state()
            return 'ran'
        self.state['handoff'].pop(task['id'], None)
        try:
            now = next(t for t in self.tasks() if t['id'] == task['id'])
        except (json.JSONDecodeError, StopIteration) as e:
            self.out(f'  tasks.json unreadable after the run: {e}')
            self.save_state()
            return 'stop'
        if now['status'] == 'blocked':
            self.out(f'  {task["id"]} is blocked: {now.get("notes", "")}')
            self.save_state()
            return 'stop'
        if now['status'] == 'done':
            ok, why = self.accept()
            if ok:
                self.out(f'  {task["id"]} done and accepted')
                self.state['no_progress'].pop(task['id'], None)
                self.save_state()
                return 'ran'
            self.set_task(task['id'], status='in_progress',
                          notes=(now.get('notes', '') + f'\n[frontier-orch] aceptación fallida: {why}').strip())
            self.out(f'  {task["id"]} claimed done but acceptance failed; back to in_progress')
        if result['error'] and not result['limited']:
            self.out(f'  {agent} ended with an error: {result["message"][:200]}')
        if self.snapshot() == before:
            n = self.state['no_progress'].get(task['id'], 0) + 1
            self.state['no_progress'][task['id']] = n
            if n >= self.cfg['no_progress_limit']:
                self.set_task(task['id'], status='blocked',
                              notes=(now.get('notes', '') + f'\n[frontier-orch] {n} ejecuciones sin cambios').strip())
                self.out(f'  {task["id"]}: {n} runs without any change; blocked for the user')
                self.save_state()
                return 'stop'
        else:
            self.state['no_progress'].pop(task['id'], None)
        self.save_state()
        return 'ran'

    def auto(self, max_runs=None):
        max_runs = max_runs or self.cfg['max_runs']
        self.take_turn()
        try:
            for _ in range(max_runs):
                outcome = self.step()
                if outcome in ('done', 'stop'):
                    self.out('all tasks done' if outcome == 'done' else 'stopped: needs the user')
                    return outcome
                if outcome == 'wait':
                    wake = min(self.state['cooldown'].values())
                    self.out(f'  no agent available; waiting until {time.ctime(wake)}')
                    self.sleep(max(60, wake - self.now()))
            self.out(f'stopped after {max_runs} runs (max_runs)')
            return 'max'
        finally:
            self.save_state()
            self.release_turn()


def parse(kind, stdout, stderr, code):
    """{'session', 'error', 'limited', 'message'} from one CLI run."""
    session, error, message = None, code != 0, ''
    if kind == 'claude':
        try:
            data = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
        except json.JSONDecodeError:
            data = {}
        session = data.get('session_id')
        error = error or bool(data.get('is_error'))
        message = str(data.get('result') or '') + ' ' + str(data.get('api_error_status') or '')
        limited = error and (data.get('api_error_status') == 429 or bool(LIMIT.search(message + stderr)))
    else:
        for line in stdout.splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get('type') == 'thread.started':
                session = ev.get('thread_id')
            if ev.get('type') in ('error', 'turn.failed'):
                error = True
                message += ' ' + json.dumps(ev.get('error') or ev.get('message') or ev)
        limited = error and bool(LIMIT.search(message + stderr))
    return {'session': session, 'error': error, 'limited': bool(limited), 'message': (message or stderr).strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['auto', 'once', 'status', 'release'])
    ap.add_argument('--root', default=Path(__file__).resolve().parents[2])
    ap.add_argument('--max-runs', type=int)
    args = ap.parse_args()
    orch = Orch(args.root)
    lock = open(orch.work / 'orch.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('another frontier-orch is running')
    if args.action == 'status':
        for t in orch.tasks():
            print(f'{t["id"]:14} {t["status"]:11} owner {t["owner"]:6} {t["title"]}')
        for agent in orch.cfg['agents']:
            left = orch.state['cooldown'].get(agent, 0) - orch.now()
            print(f'{agent}: ' + ('available' if left <= 0 else f'cooling down {left / 60:.0f} min'))
        print(f'turn: {orch.turn()}; runs so far: {orch.state["runs"]}')
    elif args.action == 'release':
        orch.release_turn()
    elif args.action == 'once':
        orch.take_turn()
        try:
            print(orch.step())
        finally:
            orch.save_state()
            orch.release_turn()
    else:
        sys.exit(0 if orch.auto(args.max_runs) == 'done' else 1)


if __name__ == '__main__':
    main()
