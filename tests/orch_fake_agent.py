"""Fake Claude/Codex CLI for tests/test_frontier_orch.py: fake_agent.py KIND SESSION_ARG PROMPT.

Pops the next action from $FAKE_PLAN (a JSON list of [kind, action]); appends (kind, session, prompt head) to
$FAKE_CALLS. Actions: commit (a change and a commit), dirty (an uncommitted change), done / blocked (set the first
in_progress task's status and commit), limit / auth (print the CLI's usage-limit / expired-login output), noop.
"""
import fcntl
import json
import os
import time
import subprocess
import sys
import uuid
from pathlib import Path

kind, session, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
plan_path = Path(os.environ['FAKE_PLAN'])
lane = os.environ.get('ORCH_LANE')     # parallel lanes run at once: the plan is then {kind: [actions]}
with open(str(plan_path) + '.lock', 'w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    plan = json.loads(plan_path.read_text())
    if isinstance(plan, dict):
        expected, action = kind, plan[kind].pop(0)
    else:
        expected, action = plan.pop(0)
    plan_path.write_text(json.dumps(plan))
    with open(os.environ['FAKE_CALLS'], 'a') as f:
        f.write(json.dumps([kind, session, prompt[:300], lane, os.getcwd(), prompt[-1500:]]) + '\n')
assert expected == kind, f'plan expected {expected}, {kind} was run'


def git(*args):
    subprocess.run(['git', *args], check=True, capture_output=True)


tasks = Path('frontier/orch/tasks.json')
if action.startswith('sleep'):          # sleepN: take N tenths of a second (to overlap with the other lane)
    time.sleep(int(action[5:] or 3) / 10)
    action = 'commit'
if action == 'bitacora':                # append to the shared log, as every agent does at a milestone
    with open('frontier/BITACORA.md', 'a') as f:
        f.write(f'\n## entry by {kind} {uuid.uuid4().hex[:6]}\n')
    git('add', '-A')
    git('commit', '-q', '-m', 'log entry')
elif action == 'clash':                 # both lanes rewrite the same line of the same file
    Path('shared.txt').write_text(f'{kind}\n')
    git('add', '-A')
    git('commit', '-q', '-m', 'clash')
elif lane and action in ('done', 'blocked', 'lanedone'):
    Path('work').mkdir(exist_ok=True)
    Path('work/lane-task.json').write_text(json.dumps({'status': 'done' if action == 'lanedone' else action,
                                                       'notes': '¿A o B?' if action == 'blocked' else '',
                                                       'evidence': f'{kind} in {lane}'}))
    if action == 'lanedone':
        Path(f'done-{kind}.txt').write_text('x')
        git('add', '-A')
        git('commit', '-q', '-m', 'finish')
if action in ('commit', 'dirty'):
    Path(f'change-{uuid.uuid4().hex[:6]}.txt').write_text(action)
    if action == 'commit':
        git('add', '-A')
        git('commit', '-q', '-m', 'fake work')
elif action in ('done', 'blocked') and not lane:
    data = json.loads(tasks.read_text())
    task = next(t for t in data['tasks'] if t['status'] == 'in_progress')
    task['status'] = action
    task['notes'] = '¿A o B?' if action == 'blocked' else ''
    tasks.write_text(json.dumps(data))
    git('add', '-A')
    git('commit', '-q', '-m', action)

if kind == 'claude':
    sid = session or str(uuid.uuid4())
    if action == 'auth':     # what Claude Code printed when its OAuth session expired (2026-11-03)
        print(json.dumps({'type': 'result', 'is_error': True, 'api_error_status': None, 'session_id': sid,
                          'result': 'Failed to authenticate: OAuth session expired and could not be refreshed'}))
        sys.exit(1)
    if action == 'limit_reset':     # the 5-hour limit as Claude Code printed it on 2026-11-04
        print(json.dumps({'type': 'result', 'is_error': True, 'api_error_status': None, 'session_id': sid,
                          'result': "You've hit your 5-hour limit · resets 6:30am (Europe/Madrid)"}))
        sys.exit(1)
    if action == 'limit':
        print(json.dumps({'type': 'result', 'is_error': True, 'api_error_status': 429,
                          'result': "You've hit your usage limit", 'session_id': sid}))
        sys.exit(1)
    print(json.dumps({'type': 'result', 'is_error': False, 'result': 'ok', 'session_id': sid}))
else:
    print(json.dumps({'type': 'thread.started', 'thread_id': session or 'codex-' + uuid.uuid4().hex[:8]}))
    if action == 'auth':
        print(json.dumps({'type': 'error', 'message': 'Not logged in. Run codex login.'}))
        sys.exit(1)
    if action == 'limit':
        print(json.dumps({'type': 'turn.failed', 'error': {'message': 'You have hit your usage limit.'}}))
        sys.exit(1)
    print(json.dumps({'type': 'turn.completed'}))
