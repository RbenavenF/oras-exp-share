"""frontier/orch/frontier_orch.py with fake agents (tests/orch_fake_agent.py) on a scratch git repository."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier/orch'))
import frontier_orch as fo  # noqa: E402

FAKE = ROOT / 'tests/orch_fake_agent.py'


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / 'repo'
    (r / 'frontier/orch').mkdir(parents=True)
    (r / 'frontier/REPARTO.md').write_text('# Reparto\n\n## Turno\n\nlibre (último: nadie)\n\n## Resto\n')
    cfg = json.loads((ROOT / 'frontier/orch/config.json').read_text())
    for kind, session_flag in (('claude', '{session}'), ('codex', '{session}')):
        cfg['agents'][kind]['new'] = [sys.executable, str(FAKE), kind, '' if kind == 'codex' else session_flag,
                                      '{prompt}']
        cfg['agents'][kind]['resume'] = [sys.executable, str(FAKE), kind, session_flag, '{prompt}']
    cfg['acceptance'] = [['true']]
    cfg['after_run'] = [['bash', '-c', 'echo x >> work/after_run.txt']]
    (r / 'frontier/orch/config.json').write_text(json.dumps(cfg))
    tasks = [{'id': 'T1', 'title': 'one', 'owner': 'claude', 'status': 'pending', 'notes': ''},
             {'id': 'T2', 'title': 'two', 'owner': 'codex', 'status': 'pending', 'notes': ''}]
    (r / 'frontier/orch/tasks.json').write_text(json.dumps({'tasks': tasks}))
    (r / '.gitignore').write_text('work/\n')
    git(r, 'init', '-q')
    git(r, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A')
    git(r, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'init')
    monkeypatch.setenv('GIT_AUTHOR_NAME', 't')
    monkeypatch.setenv('GIT_AUTHOR_EMAIL', 't@t')
    monkeypatch.setenv('GIT_COMMITTER_NAME', 't')
    monkeypatch.setenv('GIT_COMMITTER_EMAIL', 't@t')
    monkeypatch.setenv('FAKE_CALLS', str(tmp_path / 'calls.jsonl'))
    monkeypatch.setenv('FAKE_PLAN', str(tmp_path / 'plan.json'))
    return r


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def run(repo, plan, max_runs=10):
    Path(__import__('os').environ['FAKE_PLAN']).write_text(json.dumps(plan))
    clock, log = Clock(), []
    orch = fo.Orch(repo, now=clock.now, sleep=clock.sleep, out=log.append)
    outcome = orch.auto(max_runs)
    calls = [json.loads(line) for line in Path(__import__('os').environ['FAKE_CALLS']).read_text().splitlines()]
    tasks = {t['id']: t for t in json.loads((repo / 'frontier/orch/tasks.json').read_text())['tasks']}
    return outcome, calls, tasks, orch, log


def test_tasks_run_to_done_without_a_continue_from_anyone(repo):
    outcome, calls, tasks, orch, _ = run(repo, [['claude', 'commit'], ['claude', 'done'], ['codex', 'done']])
    assert outcome == 'done' and [c[0] for c in calls] == ['claude', 'claude', 'codex']
    assert tasks['T1']['status'] == tasks['T2']['status'] == 'done'
    first, second = calls[0], calls[1]
    assert second[1] == first[1] and second[2].startswith('Continúa la tarea T1')   # same session, resumed
    assert fo.TURN.search((repo / 'frontier/REPARTO.md').read_text()).group(2).startswith('libre')
    assert (repo / 'work/after_run.txt').read_text().count('x') == 3     # after every run, outside the agent


def test_a_usage_limit_hands_the_task_to_the_other_agent(repo):
    outcome, calls, tasks, orch, log = run(repo, [['claude', 'limit'], ['codex', 'done'], ['codex', 'done']])
    assert [c[0] for c in calls] == ['claude', 'codex', 'codex'] and outcome == 'done'
    assert calls[1][2].startswith('AVISO DE RELEVO: la sesión anterior (claude)')
    assert 'AVISO' not in calls[2][2]       # told once; the next task starts clean
    assert orch.state['cooldown']['claude'] > 1_000_000.0


def test_both_limited_waits_for_the_first_cooldown(repo):
    outcome, calls, tasks, orch, log = run(repo, [['claude', 'limit'], ['codex', 'limit'], ['claude', 'done'],
                                                  ['codex', 'done']])
    assert [c[0] for c in calls] == ['claude', 'codex', 'claude', 'codex'] and outcome == 'done'
    assert any('no agent available' in line for line in log)


def test_an_expired_login_hands_over_and_keeps_that_agent_out(repo):
    """Measured 2026-11-03: Claude's OAuth session expired after 37 min; the supervisor retried it twice in a second
    and blocked the task. Now the other agent inherits the task and the logged-out one is not run again."""
    outcome, calls, tasks, orch, log = run(repo, [['claude', 'auth'], ['codex', 'done'], ['codex', 'done']])
    assert [c[0] for c in calls] == ['claude', 'codex', 'codex'] and outcome == 'done'
    assert calls[1][2].startswith('AVISO DE RELEVO: la sesión anterior (claude)')
    assert orch.state['needs_login'] == {'claude': True}
    assert any('not logged in' in line for line in log)


def test_both_logged_out_stops_instead_of_waiting(repo):
    outcome, calls, *_ , log = run(repo, [['claude', 'auth'], ['codex', 'auth']])
    assert outcome == 'stop' and len(calls) == 2
    assert any('need a login' in line for line in log)


def test_a_restart_lets_the_logged_out_agent_back(repo):
    run(repo, [['claude', 'auth'], ['codex', 'auth']])
    outcome, calls, *_ = run(repo, [['claude', 'done'], ['codex', 'done']])
    assert outcome == 'done' and [c[0] for c in calls][-2:] == ['claude', 'codex']


def test_the_run_log_is_written_while_the_agent_works(repo):
    outcome, calls, tasks, orch, log = run(repo, [['claude', 'done'], ['codex', 'done']])
    text = sorted((repo / 'work/orch/logs').glob('*claude*'))[0].read_text()
    assert '--- output' in text and '"session_id"' in text and '--- exit 0' in text


def test_waiting_for_a_cooldown_does_not_use_up_max_runs(repo):
    """2026-11-04: both agents were limited at 05:17 and the waits used up max_runs=40 by 25 agent runs; the
    supervisor exited (and tmux with it). Four agent runs fit in max_runs=4 whatever the waits."""
    outcome, calls, *_ = run(repo, [['claude', 'limit'], ['codex', 'limit'], ['claude', 'done'], ['codex', 'done']],
                             max_runs=4)
    assert outcome == 'done' and len(calls) == 4


def test_a_printed_reset_time_sets_the_cooldown(repo):
    outcome, calls, tasks, orch, log = run(repo, [['claude', 'limit_reset'], ['codex', 'done'], ['codex', 'done']])
    expected = fo.reset_time('resets 6:30am', 1_000_000.0)
    assert orch.state['cooldown']['claude'] == expected
    assert any('back at' in line for line in log)


def test_the_supervisor_keeps_its_own_log(repo, tmp_path):
    clock = Clock()
    orch = fo.Orch(repo, now=clock.now, sleep=clock.sleep)
    orch.say('hello there')
    assert (repo / 'work/orch/orch.log').read_text().endswith('hello there\n')


def test_failed_acceptance_reopens_the_task(repo):
    cfg = json.loads((repo / 'frontier/orch/config.json').read_text())
    cfg['acceptance'] = [['false']]
    (repo / 'frontier/orch/config.json').write_text(json.dumps(cfg))
    outcome, calls, tasks, *_ = run(repo, [['claude', 'done'], ['claude', 'noop'], ['claude', 'noop']], max_runs=3)
    assert tasks['T1']['status'] == 'blocked' and 'aceptación fallida' in tasks['T1']['notes']


def test_a_blocked_task_stops_for_the_user(repo):
    outcome, calls, tasks, *_ = run(repo, [['claude', 'blocked']])
    assert outcome == 'stop' and tasks['T1']['status'] == 'blocked' and len(calls) == 1


def test_runs_without_any_change_stop_instead_of_looping(repo):
    outcome, calls, tasks, *_ = run(repo, [['claude', 'noop'], ['claude', 'noop'], ['claude', 'commit']])
    assert outcome == 'stop' and len(calls) == 2 and tasks['T1']['status'] == 'blocked'


def test_uncommitted_work_counts_as_progress(repo):
    outcome, calls, tasks, *_ = run(repo, [['claude', 'dirty'], ['claude', 'noop'], ['claude', 'noop']], max_runs=3)
    assert len(calls) == 3      # the dirty run reset the no-progress count


def test_a_held_turn_is_refused(repo):
    text = (repo / 'frontier/REPARTO.md').read_text().replace('libre (último: nadie)', 'Codex, desde ayer')
    (repo / 'frontier/REPARTO.md').write_text(text)
    with pytest.raises(SystemExit, match='turn is held'):
        run(repo, [['claude', 'done']])


@pytest.mark.parametrize('kind, out, code, limited', [
    ('claude', json.dumps({'is_error': True, 'api_error_status': 429, 'result': 'x', 'session_id': 's'}), 1, True),
    ('claude', json.dumps({'is_error': True, 'api_error_status': None, 'result': 'Claude usage limit reached'}), 1,
     True),
    ('claude', json.dumps({'is_error': True, 'api_error_status': 500, 'result': 'Internal error'}), 1, False),
    ('claude', json.dumps({'is_error': False, 'result': 'I hit no limit today', 'session_id': 's'}), 0, False),
    ('codex', '{"type":"thread.started","thread_id":"t"}\n{"type":"turn.failed","error":{"message":"rate limit"}}',
     1, True),
    ('codex', '{"type":"thread.started","thread_id":"t"}\n{"type":"turn.completed"}', 0, False),
])
def test_parse_tells_a_usage_limit_from_other_errors(kind, out, code, limited):
    assert fo.parse(kind, out, '', code)['limited'] is limited


@pytest.mark.parametrize('kind, out, code, auth', [
    ('claude', json.dumps({'type': 'result', 'is_error': True, 'api_error_status': None,
                           'result': 'Failed to authenticate: OAuth session expired and could not be refreshed'}), 1,
     True),
    ('claude', 'stderr noise\n{"type":"system"}\n' + json.dumps({'type': 'result', 'is_error': True,
                                                                   'result': 'Not logged in · Please run /login'}),
     1, True),
    ('claude', json.dumps({'type': 'result', 'is_error': False, 'result': 'fixed the OAuth docs'}), 0, False),
    ('claude', json.dumps({'type': 'result', 'is_error': True, 'api_error_status': 429, 'result': 'usage limit'}), 1,
     False),
    ('codex', '{"type":"error","message":"Not logged in. Run codex login."}', 1, True),
])
def test_parse_tells_an_expired_login(kind, out, code, auth):
    assert fo.parse(kind, out, '', code)['auth'] is auth


def test_parse_reads_the_result_of_a_stream_json_run():
    out = '\n'.join([json.dumps({'type': 'system', 'session_id': 's'}), json.dumps({'type': 'assistant'}),
                     json.dumps({'type': 'result', 'is_error': False, 'result': 'ok', 'session_id': 's'})])
    assert fo.parse('claude', out, '', 0) == {'session': 's', 'error': False, 'limited': False, 'auth': False,
                                               'message': 'ok'}


@pytest.mark.parametrize('message, now, expect', [
    ("You've hit your 5-hour limit · resets 6:30am (Europe/Madrid)", (5, 0), (0, 6, 32)),
    ('You\u2019ve hit your usage limit. ... or try again at 10:04 AM.', (5, 17), (0, 10, 6)),
    ("You've hit your 5-hour limit · resets 1am (Europe/Madrid)", (23, 40), (1, 1, 2)),
    ('resets 11:50pm', (23, 55), (1, 23, 52)),
    ('try again at Nov 8th, 2026 1:43 PM.', (9, 54), (4, 13, 45)),          # Codex weekly limit, 2026-11-05
    ('try again at Nov 4th, 2026 4:35 AM.', (0, 19), (0, 4, 37)),
    ('resets Nov 8, 1pm', (9, 54), (4, 13, 2)),
    ("You've hit your usage limit", (5, 0), None),
])
def test_reset_time_from_the_limit_message(message, now, expect):
    import datetime
    base = datetime.datetime(2026, 11, 4, *now)
    got = fo.reset_time(message, base.timestamp())
    if expect is None:
        assert got is None
    else:
        days, hour, minute = expect
        assert datetime.datetime.fromtimestamp(got) == (base.replace(hour=hour, minute=minute)
                                                        + datetime.timedelta(days=days))


def test_fresh_sessions_never_resume_and_say_the_task_is_started(repo):
    cfg = json.loads((repo / 'frontier/orch/config.json').read_text())
    assert cfg['agents']['codex'].get('fresh_sessions') is True     # the real config carries it
    tasks = json.loads((repo / 'frontier/orch/tasks.json').read_text())
    tasks['tasks'][0]['status'] = 'done'
    (repo / 'frontier/orch/tasks.json').write_text(json.dumps(tasks))
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'T1 done')
    outcome, calls, tasks, orch, _ = run(repo, [['codex', 'commit'], ['codex', 'done']])
    assert outcome == 'done' and [c[0] for c in calls] == ['codex', 'codex']
    assert calls[1][1] == ''                         # the 'new' command again, no session id passed
    assert calls[1][2].startswith('Eres codex')         # the full brief, not «Continúa…»
    cmd, session, resumed = orch.command('codex', tasks['T2'], resuming=True)
    assert not resumed and 'La tarea ya está empezada' in cmd[-1]
