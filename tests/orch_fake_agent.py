"""Fake Claude/Codex CLI for tests/test_frontier_orch.py: fake_agent.py KIND SESSION_ARG PROMPT.

Pops the next action from $FAKE_PLAN (a JSON list of [kind, action]); appends (kind, session, prompt head) to
$FAKE_CALLS. Actions: commit (a change and a commit), dirty (an uncommitted change), done / blocked (set the first
in_progress task's status and commit), limit (print the CLI's usage-limit output), noop.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

kind, session, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
plan_path = Path(os.environ['FAKE_PLAN'])
plan = json.loads(plan_path.read_text())
expected, action = plan.pop(0)
plan_path.write_text(json.dumps(plan))
with open(os.environ['FAKE_CALLS'], 'a') as f:
    f.write(json.dumps([kind, session, prompt[:300]]) + '\n')
assert expected == kind, f'plan expected {expected}, {kind} was run'


def git(*args):
    subprocess.run(['git', *args], check=True, capture_output=True)


tasks = Path('frontier/orch/tasks.json')
if action in ('commit', 'dirty'):
    Path(f'change-{uuid.uuid4().hex[:6]}.txt').write_text(action)
    if action == 'commit':
        git('add', '-A')
        git('commit', '-q', '-m', 'fake work')
elif action in ('done', 'blocked'):
    data = json.loads(tasks.read_text())
    task = next(t for t in data['tasks'] if t['status'] == 'in_progress')
    task['status'] = action
    task['notes'] = '¿A o B?' if action == 'blocked' else ''
    tasks.write_text(json.dumps(data))
    git('add', '-A')
    git('commit', '-q', '-m', action)

if kind == 'claude':
    sid = session or str(uuid.uuid4())
    if action == 'limit':
        print(json.dumps({'type': 'result', 'is_error': True, 'api_error_status': 429,
                          'result': "You've hit your usage limit", 'session_id': sid}))
        sys.exit(1)
    print(json.dumps({'type': 'result', 'is_error': False, 'result': 'ok', 'session_id': sid}))
else:
    print(json.dumps({'type': 'thread.started', 'thread_id': session or 'codex-' + uuid.uuid4().hex[:8]}))
    if action == 'limit':
        print(json.dumps({'type': 'turn.failed', 'error': {'message': 'You have hit your usage limit.'}}))
        sys.exit(1)
    print(json.dumps({'type': 'turn.completed'}))
