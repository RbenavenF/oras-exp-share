#!/usr/bin/env python3
"""frontier-orch: runs the Battle Frontier tasks with Claude Code and Codex, unattended, one agent at a time.

    frontier/orch/frontier-orch auto      run until every task is done, one is blocked, or nothing makes progress
    frontier/orch/frontier-orch once      a single agent run
    frontier/orch/frontier-orch status    tasks, cooldowns and sessions
    frontier/orch/frontier-orch release   give the turn back (after a crash of the supervisor itself)
    frontier/orch/frontier-orch auto --parallel   one lane per agent, both at once (see «Parallel lanes» below)
    frontier/orch/frontier-orch lanes setup|remove   create or delete the lanes' git worktrees

The supervisor, not the agents, decides who works: a task's owner when available, else the other agent. An agent
that hits a usage limit is cooled down and the other one inherits the task, told to inspect the uncommitted state
first. A run that ends with the task still open is resumed in the same session, without anyone typing «continúa».

Tasks: frontier/orch/tasks.json (the agents edit `status`, `notes`, `evidence`). Settings: frontier/orch/config.json.
State and logs: work/orch/ (not in git). The supervisor holds the REPARTO.md turn while it runs (one writer).

Parallel lanes (`auto --parallel`, config `lanes`): each agent works in its own git worktree (work/orch/lanes/<agent>,
branch lane/<agent>) with its own work/, its own Azahar lab and GDB port (work/lab-port), the big read-only inputs
linked from the main checkout. An agent takes the open tasks it owns, or the other agent's while that one is out of
quota. The agents do not edit tasks.json there: they write work/lane-task.json, and after every run the supervisor
rebases the lane onto main, fast-forwards main to it, runs the acceptance on main and records the task status. A
rebase conflict blocks that task (BITACORA.md and reports/frontier.md merge as a union, .gitattributes). Sequential
`auto` is unchanged.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

LIMIT = re.compile(r'usage limit|hit your .{0,20}limit|rate.?limit|quota|limit reached|too many requests|\b429\b'
                   r'|out of credits'
                   r'|insufficient.{0,20}credit', re.I)
AUTH = re.compile(r'failed to authenticate|oauth|not logged in|/login|log ?in again|unauthori[sz]ed|\b401\b'
                  r'|authentication (?:failed|required|error)|invalid api key', re.I)
# The reset time the CLIs print with a usage limit (measured 2026-11-04): Claude «resets 6:30am (Europe/Madrid)»,
# Codex «try again at 10:04 AM». Local time of this machine. With a date when the wait is longer than a day (Codex's
# weekly limit, measured 2026-11-05): «try again at Nov 8th, 2026 1:43 PM».
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
RESET = re.compile(r'(?:resets|try again at)\s+(?:(?P<mon>' + '|'.join(MONTHS) + r')[a-z]*\.?\s+(?P<day>\d{1,2})'
                   r'(?:st|nd|rd|th)?,?\s+(?:(?P<year>\d{4}),?\s+)?(?:at\s+)?)?'
                   r'(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap])\.?m\b', re.I)
TURN = re.compile(r'(## Turno\n\n)(.*)\n')
HOLDER = 'frontier-orch'


class Orch:
    def __init__(self, root, now=time.time, sleep=time.sleep, out=None):
        self.root = Path(root).resolve()
        self.cfg = json.loads((self.root / 'frontier/orch/config.json').read_text())
        self.tasks_path = self.root / 'frontier/orch/tasks.json'
        self.work = self.root / 'work/orch'
        self.state_path = self.work / 'state.json'
        self.now, self.sleep = now, sleep
        self.work.mkdir(parents=True, exist_ok=True)
        self.out = out or self.say
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        for key in ('sessions', 'cooldown', 'no_progress', 'handoff', 'needs_login'):
            self.state.setdefault(key, {})
        self.state.setdefault('runs', 0)
        self.lock = threading.RLock()       # parallel lanes: state, tasks.json and the main checkout's git

    def say(self, line):
        """Print and keep in work/orch/orch.log, which survives the terminal (tmux closes with the supervisor)."""
        with self.lock:
            print(line, flush=True)
            stamp = datetime.datetime.fromtimestamp(self.now()).strftime('%Y-%m-%d %H:%M:%S')
            with (self.work / 'orch.log').open('a') as f:
                f.write(f'{stamp} {line}\n')

    # ---- files ------------------------------------------------------------------------------------------------
    def save_state(self):
        with self.lock:
            self.state_path.write_text(json.dumps(self.state, indent=2) + '\n')

    def tasks(self):
        return json.loads(self.tasks_path.read_text())['tasks']

    def set_task(self, task_id, **fields):
        with self.lock:
            data = json.loads(self.tasks_path.read_text())
            for t in data['tasks']:
                if t['id'] == task_id:
                    t.update(fields)
            self.tasks_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    def commit(self, message, *paths):
        """A supervisor commit on the main checkout (parallel mode: tasks.json changes go straight in)."""
        with self.lock:
            self.git('add', *paths)
            if self.git('diff', '--cached', '--name-only').strip():
                self.git('-c', 'user.name=rubenb114', '-c', 'user.email=rubenb114@hotmail.com', 'commit', '-q',
                         '-m', f'{message}\n\nAgent: frontier-orch', '--', *paths)

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

    def command(self, agent, task, resuming, lane=None):
        spec = self.cfg['agents'][agent]
        session = self.state['sessions'].get(task['id'], {}).get(agent)
        # fresh_sessions: never resume. Measured 2026-11-04: a resumed Codex session re-sent ~142k tokens per call
        # (124 calls, 17.2M input) and spent a whole quota window in ~15 min; the repository holds the state anyway.
        fresh = bool(spec.get('fresh_sessions'))
        resume = resuming and session is not None and not fresh
        if not resume and spec['kind'] == 'claude':
            session = str(uuid.uuid4())     # Claude takes the id up front; Codex reports its thread id
        prompt = self.prompt(task, agent, resume)
        if fresh and resuming and session is not None:
            prompt += ('\n\nLa tarea ya está empezada (sesión nueva, sin el historial de la anterior): antes de '
                       'seguir, mira `git log`, `git status` y la última entrada de la bitácora de esta tarea.')
        if lane is not None:
            prompt += '\n\n' + self.cfg['lanes']['brief'].format(agent=agent, root=lane,
                                                                  port=self.cfg['lanes']['agents'][agent]['gdb_port'])
        values = {'prompt': prompt, 'session': session or '', 'root': str(lane or self.root),
                  'git_common': str(self.root / '.git')}
        return [part.format(**values) for part in spec['resume' if resume else 'new']], session, resume

    def run(self, agent, task, resuming, lane=None):
        cmd, session, resumed = self.command(agent, task, resuming, lane)
        cwd, env = self.root, None
        if lane is not None:
            cwd = lane
            env = dict(os.environ, ORCH_LANE=agent, ORAS_GDB_PORT=str(self.cfg['lanes']['agents'][agent]['gdb_port']))
        stamp = datetime.datetime.fromtimestamp(self.now()).strftime('%Y%m%d-%H%M%S')
        log = self.work / 'logs' / f'{stamp}-{agent}-{task["id"]}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        where = f' in lane {agent}' if lane is not None else ''
        self.out(f'[{stamp}] {agent} {"resumes" if resumed else "starts"} {task["id"]}{where} (log {log})')
        with log.open('w') as f:        # written as the agent works: tail -f it to follow a run live
            f.write(f'$ {" ".join(cmd[:3])} ...\n--- output (stdout and stderr)\n')
            f.flush()
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=f,
                                    stderr=subprocess.STDOUT)
            try:
                code = proc.wait(timeout=self.cfg['run_timeout_minutes'] * 60)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait()
                f.write('\n[frontier-orch: timeout]\n')
            f.write(f'\n--- exit {code}\n')
        stdout, stderr = log.read_text(errors='replace'), ''
        for cleanup in self.cfg.get('after_run', []):   # outside the agents' sandboxes, e.g. a lab left running
            done = subprocess.run(cleanup, cwd=cwd, env=env, capture_output=True, text=True)
            with log.open('a') as f:
                f.write(f'--- after_run {cleanup[-1][:80]!r}: exit {done.returncode}\n{done.stdout}{done.stderr}')
        parsed = parse(self.cfg['agents'][agent]['kind'], stdout, stderr, code)
        if parsed['session'] or session:
            with self.lock:
                self.state['sessions'].setdefault(task['id'], {})[agent] = parsed['session'] or session
        return parsed

    def accept(self):
        for cmd in self.cfg['acceptance']:
            proc = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, shell=isinstance(cmd, str))
            if proc.returncode:
                return False, (proc.stdout + proc.stderr)[-1500:]
        return True, ''

    def cut_short(self, agent, task, result):
        """A run that ended on a usage limit or an expired login: cool the agent down and leave a handoff note."""
        with self.lock:
            if result['auth']:      # waiting does not fix it: out until the user logs in and restarts auto
                self.state['needs_login'][agent] = True
                self.state['cooldown'][agent] = self.now() + 10 * 365 * 86400
                reason = 'sesión caducada o sin login: ' + result['message'][:200]
                self.out(f'  {agent} is not logged in ({result["message"][:120]}); run its login, then auto again')
            else:
                until = reset_time(result['message'], self.now())
                self.state['cooldown'][agent] = until or self.now() + self.cfg['cooldown_minutes'] * 60
                reason = 'límite de uso: ' + result['message'][:200]
                self.out(f'  {agent} hit a usage limit; back at {time.ctime(self.state["cooldown"][agent])}'
                         + ('' if until else ' (no reset time given: the default cooldown)'))
            self.state['handoff'][task['id']] = {'from': agent, 'reason': reason}
            self.save_state()

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
        if result['limited'] or result['auth']:
            self.cut_short(agent, task, result)
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
        if result['error']:
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
        for agent in list(self.state['needs_login']):   # a restart means the user logged in again
            self.state['cooldown'].pop(agent, None)
        self.state['needs_login'] = {}
        self.take_turn()
        try:
            runs = 0
            while runs < max_runs:      # agent runs; waiting for a cooldown does not count
                outcome = self.step()
                runs += outcome == 'ran'
                if outcome in ('done', 'stop'):
                    self.out('all tasks done' if outcome == 'done' else 'stopped: needs the user')
                    return outcome
                if outcome == 'wait':
                    timed = [w for a, w in self.state['cooldown'].items() if a not in self.state['needs_login']]
                    if not timed:
                        self.out('stopped: ' + ', '.join(self.state['needs_login']) + ' need a login')
                        return 'stop'
                    wake = min(timed)
                    self.out(f'  no agent available; waiting until {time.ctime(wake)}')
                    self.sleep(max(60, wake - self.now()))
            if self.next_task() is None:
                self.out('all tasks done')
                return 'done'
            self.out(f'stopped after {max_runs} agent runs (max_runs)')
            return 'max'
        finally:
            self.save_state()
            self.release_turn()

    # ---- parallel lanes -----------------------------------------------------------------------------------------
    def lane_path(self, agent):
        return self.root / self.cfg['lanes'].get('root', 'work/orch/lanes') / agent

    def lane_git(self, agent, *args, check=True):
        return subprocess.run(['git', '-C', str(self.lane_path(agent)), *args], check=check, capture_output=True,
                              text=True)

    def lanes_setup(self):
        """A worktree per agent on branch lane/<agent> at main's HEAD, with the shared inputs linked, the lab's
        saves and settings copied and its own GDB port. Idempotent: an existing lane is only completed."""
        lanes = self.cfg['lanes']
        for agent, spec in lanes['agents'].items():
            path = self.lane_path(agent)
            if not (path / '.git').exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                self.git('worktree', 'add', '-B', f'lane/{agent}', str(path), 'HEAD')
            for rel in lanes.get('link', []):
                src, dst = self.root / rel, path / rel
                if src.exists() and not (dst.exists() or dst.is_symlink()):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.symlink_to(src)
            for rel in lanes.get('copy', []):
                src, dst = self.root / rel, path / rel
                if src.exists() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(['cp', '-a', str(src), str(dst)], check=True)
            (path / 'work').mkdir(exist_ok=True)
            (path / 'work/lab-port').write_text(f'{spec["gdb_port"]}\n')
            self.out(f'lane {agent}: {path} (branch lane/{agent}, gdb port {spec["gdb_port"]})')

    def lanes_remove(self):
        """Delete the lanes' worktrees (links first, so nothing shared is touched) and their branches if merged."""
        for agent in self.cfg['lanes']['agents']:
            path = self.lane_path(agent)
            if path.exists():
                for rel in self.cfg['lanes'].get('link', []):
                    if (path / rel).is_symlink():
                        (path / rel).unlink()
                self.git('worktree', 'remove', '--force', str(path))
            self.git('worktree', 'prune')
            branch = f'lane/{agent}'
            if self.git('branch', '--list', branch).strip():
                if self.git('branch', '--merged', 'HEAD', '--list', branch).strip():
                    self.git('branch', '-D', branch)
                else:
                    self.out(f'{branch} has commits that are not in main; branch kept')
            self.out(f'lane {agent} removed')

    def lane_task(self, agent, claimed):
        """The agent's own open task (in progress first), else one of an agent that is out of quota."""
        tasks = [t for t in self.tasks() if t['id'] not in claimed]
        for mine in (True, False):
            for wanted in ('in_progress', 'pending'):
                for t in tasks:
                    if t['status'] == wanted and (t['owner'] == agent) == mine and (
                            mine or not self.available(t['owner'])):
                        return t
        return None

    def lane_snapshot(self, agent):
        head = self.lane_git(agent, 'rev-parse', 'HEAD').stdout.strip()
        dirty = self.lane_git(agent, 'status', '--porcelain', '--untracked-files=all').stdout
        status = self.lane_path(agent) / 'work/lane-task.json'
        return head, hashlib.sha256(dirty.encode()).hexdigest(), status.read_bytes() if status.exists() else b''

    def lane_integrate(self, agent):
        """Rebase the lane onto main and fast-forward main to it. (False, why) on a conflict, which is aborted."""
        with self.lock:
            main = self.git('rev-parse', 'HEAD').strip()
            r = self.lane_git(agent, 'rebase', '--autostash', main, check=False)
            if r.returncode:
                files = self.lane_git(agent, 'diff', '--name-only', '--diff-filter=U', check=False).stdout.split()
                self.lane_git(agent, 'rebase', '--abort', check=False)
                return False, 'conflicto al integrar con main en ' + (', '.join(files) or (r.stdout + r.stderr)[-300:])
            lane = self.lane_git(agent, 'rev-parse', 'HEAD').stdout.strip()
            if lane != main:
                self.git('merge', '-q', '--ff-only', lane)
            return True, ''

    def lane_run(self, agent, task, resuming):
        try:
            return self.run(agent, task, resuming, lane=self.lane_path(agent))
        except Exception as e:      # noqa: BLE001 — a crashed run must not kill the other lane
            return {'session': None, 'error': True, 'limited': False, 'auth': False, 'message': f'frontier-orch: {e}'}

    def lane_finish(self, agent, task, before, result):
        """After a lane run: limits, integration, the status the agent wrote, acceptance and no-progress."""
        self.state['runs'] += 1
        after = self.lane_snapshot(agent)
        status_file = self.lane_path(agent) / 'work/lane-task.json'
        try:
            status = json.loads(status_file.read_text()) if status_file.exists() else {}
        except json.JSONDecodeError as e:
            status = {'notes': f'[frontier-orch] work/lane-task.json ilegible: {e}'}
        status_file.unlink(missing_ok=True)
        ok, why = self.lane_integrate(agent)
        if result['limited'] or result['auth']:
            self.cut_short(agent, task, result)
            if not ok:
                self.set_task(task['id'], status='blocked', notes=(task.get('notes', '') + '\n' + why).strip())
                self.commit(f'frontier-orch: {task["id"]} blocked (integration)', 'frontier/orch/tasks.json')
            return
        self.state['handoff'].pop(task['id'], None)
        if not ok:
            self.set_task(task['id'], status='blocked', notes=(task.get('notes', '') + f'\n[frontier-orch] {why}').strip())
            self.commit(f'frontier-orch: {task["id"]} blocked (integration)', 'frontier/orch/tasks.json')
            self.out(f'  {task["id"]}: {why}; blocked for the user')
            return
        fields = {k: status[k] for k in ('status', 'notes', 'evidence') if k in status}
        if fields.get('status') not in (None, 'in_progress', 'done', 'blocked'):
            fields['status'] = 'in_progress'
        if fields.get('status') == 'done':
            accepted, why = self.accept()
            if accepted:
                self.out(f'  {task["id"]} done and accepted')
                self.state['no_progress'].pop(task['id'], None)
            else:
                fields['status'] = 'in_progress'
                fields['notes'] = (fields.get('notes', task.get('notes', '')) +
                                   f'\n[frontier-orch] aceptación fallida: {why}').strip()
                self.out(f'  {task["id"]} claimed done but acceptance failed; back to in_progress')
        elif fields.get('status') == 'blocked':
            self.out(f'  {task["id"]} is blocked: {fields.get("notes", "")}')
        if result['error']:
            self.out(f'  {agent} ended with an error: {result["message"][:200]}')
        if after == before and fields.get('status') != 'done':
            n = self.state['no_progress'].get(task['id'], 0) + 1
            self.state['no_progress'][task['id']] = n
            if n >= self.cfg['no_progress_limit']:
                fields['status'] = 'blocked'
                fields['notes'] = (fields.get('notes', task.get('notes', '')) +
                                   f'\n[frontier-orch] {n} ejecuciones sin cambios').strip()
                self.out(f'  {task["id"]}: {n} runs without any change; blocked for the user')
        else:
            self.state['no_progress'].pop(task['id'], None)
        if fields:
            self.set_task(task['id'], **fields)
            self.commit(f'frontier-orch: {task["id"]} {fields.get("status", "notes")} (lane {agent})',
                        'frontier/orch/tasks.json')
        self.save_state()

    def auto_parallel(self, max_runs=None):
        """Both lanes at once until nothing open is left that someone can take. 'done', 'stop' or 'max'."""
        max_runs = max_runs or self.cfg['max_runs']
        for agent in list(self.state['needs_login']):
            self.state['cooldown'].pop(agent, None)
        self.state['needs_login'] = {}
        self.take_turn()
        try:
            self.lanes_setup()
            finished, busy, runs = queue.Queue(), {}, 0
            while True:
                for agent in self.cfg['lanes']['agents']:
                    if runs + len(busy) >= max_runs or agent in busy or not self.available(agent):
                        continue
                    task = self.lane_task(agent, set(busy.values()))
                    if task is None:
                        continue
                    resuming = task['status'] == 'in_progress'
                    if not resuming:
                        self.set_task(task['id'], status='in_progress')
                        self.commit(f'frontier-orch: {task["id"]} in progress (lane {agent})',
                                    'frontier/orch/tasks.json')
                    ok, why = self.lane_integrate(agent)        # the lane starts from main as it is now
                    if not ok:
                        self.set_task(task['id'], status='blocked',
                                      notes=(task.get('notes', '') + f'\n[frontier-orch] {why}').strip())
                        self.commit(f'frontier-orch: {task["id"]} blocked (integration)', 'frontier/orch/tasks.json')
                        self.out(f'  {task["id"]}: {why}; blocked for the user')
                        continue
                    before = self.lane_snapshot(agent)
                    busy[agent] = task['id']
                    threading.Thread(target=lambda a=agent, t=task, r=resuming, b=before:
                                     finished.put((a, t, b, self.lane_run(a, t, r))), daemon=True).start()
                if not busy:
                    open_ = [t for t in self.tasks() if t['status'] in ('in_progress', 'pending')]
                    blocked = any(t['status'] == 'blocked' for t in self.tasks())
                    if not open_:
                        self.out('stopped: needs the user' if blocked else 'all tasks done')
                        return 'stop' if blocked else 'done'
                    if runs >= max_runs:
                        self.out(f'stopped after {max_runs} agent runs (max_runs)')
                        return 'max'
                    timed = [w for a, w in self.state['cooldown'].items()
                             if a not in self.state['needs_login'] and w > self.now()]
                    if not timed:
                        self.out('stopped: no lane can take the open tasks ('
                                 + ', '.join(t['id'] for t in open_) + ')')
                        return 'stop'
                    wake = min(timed)
                    self.out(f'  no lane can start; waiting until {time.ctime(wake)}')
                    self.sleep(max(60, wake - self.now()))
                    continue
                agent, task, before, result = finished.get()
                busy.pop(agent)
                runs += 1
                self.lane_finish(agent, task, before, result)
        finally:
            self.save_state()
            self.release_turn()


def reset_time(message, now):
    """The epoch at which a usage limit with a printed reset time ends (+2 min), or None. The next such clock time
    after `now`, local time."""
    m = RESET.search(message)
    if not m:
        return None
    hour, minute = int(m['h']) % 12 + (12 if m['ap'].lower() == 'p' else 0), int(m['m'] or 0)
    base = datetime.datetime.fromtimestamp(now)
    at = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if m['mon']:
        at = at.replace(year=int(m['year'] or base.year), month=MONTHS.index(m['mon'].lower()[:3]) + 1,
                        day=int(m['day']))
        if at <= base and not m['year']:
            at = at.replace(year=at.year + 1)
    elif at <= base:
        at += datetime.timedelta(days=1)
    return at.timestamp() + 120


def parse(kind, stdout, stderr, code):
    """{'session', 'error', 'limited', 'auth', 'message'} from one CLI run (stdout may hold stderr lines too)."""
    session, error, message = None, code != 0, ''
    if kind == 'claude':
        data = {}
        for line in reversed(stdout.strip().splitlines()):     # the result event (json or stream-json)
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(ev, dict) and ev.get('type', 'result') == 'result':
                data = ev
                break
        session = data.get('session_id')
        error = error or bool(data.get('is_error'))
        message = str(data.get('result') or '') + ' ' + str(data.get('api_error_status') or '')
        limited = error and (data.get('api_error_status') == 429 or bool(LIMIT.search(message + stderr)))
        auth = error and (data.get('api_error_status') == 401 or bool(AUTH.search(message + stderr)))
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
        auth = error and bool(AUTH.search(message + stderr))
    auth = bool(auth) and not limited
    return {'session': session, 'error': error, 'limited': bool(limited), 'auth': auth,
            'message': (message or stderr).strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['auto', 'once', 'status', 'release', 'lanes'])
    ap.add_argument('what', nargs='?', choices=['setup', 'remove'], help='for lanes')
    ap.add_argument('--root', default=Path(__file__).resolve().parents[2])
    ap.add_argument('--max-runs', type=int)
    ap.add_argument('--parallel', action='store_true', help='auto: one lane per agent at once (config lanes)')
    args = ap.parse_args()
    orch = Orch(args.root)
    if args.action != 'status':     # status only reads, so it works while auto runs
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
            print(f'{agent}: ' + ('needs a login' if agent in orch.state['needs_login'] else
                                  'available' if left <= 0 else f'cooling down {left / 60:.0f} min'))
        logs = sorted((orch.work / 'logs').glob('*.log'))
        if logs:
            print(f'last run log (tail -f to follow it): {logs[-1]}')
        print(f'turn: {orch.turn()}; runs so far: {orch.state["runs"]}')
        for agent in (orch.cfg.get('lanes') or {}).get('agents', {}):
            path = orch.lane_path(agent)
            if (path / '.git').exists():
                ahead = orch.git('rev-list', '--count', f'HEAD..lane/{agent}', check=False).strip()
                print(f'lane {agent}: {path} ({ahead or "?"} commit(s) not in main)')
    elif args.action == 'lanes':
        if not args.what:
            ap.error('lanes needs setup or remove')
        orch.lanes_setup() if args.what == 'setup' else orch.lanes_remove()
    elif args.action == 'release':
        orch.release_turn()
    elif args.action == 'once':
        orch.take_turn()
        try:
            print(orch.step())
        finally:
            orch.save_state()
            orch.release_turn()
    elif args.parallel:
        sys.exit(0 if orch.auto_parallel(args.max_runs) == 'done' else 1)
    else:
        sys.exit(0 if orch.auto(args.max_runs) == 'done' else 1)


if __name__ == '__main__':
    main()
