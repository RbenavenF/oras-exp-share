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


# ---- parallel lanes (auto --parallel) ---------------------------------------------------------------------------
@pytest.fixture
def lanes_repo(repo):
    cfg = json.loads((repo / 'frontier/orch/config.json').read_text())
    cfg['lanes']['link'], cfg['lanes']['copy'] = ['shared-input'], []
    (repo / 'frontier/orch/config.json').write_text(json.dumps(cfg))
    (repo / 'frontier/BITACORA.md').write_text('# Bitácora\n')
    (repo / '.gitattributes').write_text((ROOT / '.gitattributes').read_text())
    (repo / 'shared.txt').write_text('base\n')
    (repo / '.gitignore').write_text('/work\n/shared-input\n')
    (repo / 'shared-input').mkdir()
    (repo / 'shared-input/big.bin').write_text('read-only input')
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A')
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'lanes base')
    return repo


def run_parallel(repo, plan, max_runs=10):
    Path(__import__('os').environ['FAKE_PLAN']).write_text(json.dumps(plan))
    clock, log = Clock(), []
    orch = fo.Orch(repo, now=clock.now, sleep=clock.sleep, out=log.append)
    outcome = orch.auto_parallel(max_runs)
    calls = [json.loads(line) for line in Path(__import__('os').environ['FAKE_CALLS']).read_text().splitlines()]
    tasks = {t['id']: t for t in json.loads((repo / 'frontier/orch/tasks.json').read_text())['tasks']}
    return outcome, calls, tasks, orch, log


def test_lanes_run_both_agents_at_once_and_land_their_work_on_main(lanes_repo):
    outcome, calls, tasks, orch, log = run_parallel(
        lanes_repo, {'claude': ['sleep5', 'lanedone'], 'codex': ['sleep5', 'lanedone']})
    assert outcome == 'done' and tasks['T1']['status'] == tasks['T2']['status'] == 'done'
    assert {c[3] for c in calls} == {'claude', 'codex'}                    # each agent in its own lane
    assert {Path(c[4]).name for c in calls} == {'claude', 'codex'}
    assert all('MODO PARALELO' in c[5] for c in calls)
    files = git(lanes_repo, 'ls-files').split()
    assert 'done-claude.txt' in files and 'done-codex.txt' in files      # both fast-forwarded into main
    assert tasks['T2']['evidence'] == 'codex in codex'
    assert fo.TURN.search((lanes_repo / 'frontier/REPARTO.md').read_text()).group(2).startswith('libre')
    lane = orch.lane_path('codex')
    assert (lane / 'shared-input').is_symlink() and (lane / 'work/lab-port').read_text().strip() == '24691'
    assert not git(lanes_repo, 'status', '--porcelain')                  # main is clean


def test_lanes_overlap_in_time(lanes_repo, monkeypatch):
    """The two agents' runs are concurrent, not one after the other."""
    import time as _t
    spans = {}
    real = fo.Orch.lane_run

    def timed(self, agent, task, resuming):
        start = _t.monotonic()
        result = real(self, agent, task, resuming)
        spans[agent] = (start, _t.monotonic())
        return result
    monkeypatch.setattr(fo.Orch, 'lane_run', timed)
    run_parallel(lanes_repo, {'claude': ['sleep8', 'lanedone'], 'codex': ['sleep8', 'lanedone']})
    (a0, a1), (b0, b1) = spans['claude'], spans['codex']
    assert a0 < b1 and b0 < a1


def test_both_lanes_appending_to_the_log_merge_without_conflict(lanes_repo):
    outcome, calls, tasks, *_ = run_parallel(
        lanes_repo, {'claude': ['bitacora', 'lanedone'], 'codex': ['bitacora', 'lanedone']})
    text = (lanes_repo / 'frontier/BITACORA.md').read_text()
    assert outcome == 'done' and text.count('## entry by claude') == 1 and text.count('## entry by codex') == 1
    assert '<<<<<<<' not in text


def test_a_real_conflict_blocks_that_task_and_keeps_main_clean(lanes_repo):
    outcome, calls, tasks, orch, log = run_parallel(lanes_repo, {'claude': ['clash', 'lanedone'], 'codex': ['clash', 'lanedone']})
    assert outcome == 'stop'
    blocked = [t for t in tasks.values() if t['status'] == 'blocked']
    assert len(blocked) == 1 and 'conflicto al integrar' in blocked[0]['notes'] and 'shared.txt' in blocked[0]['notes']
    assert not git(lanes_repo, 'status', '--porcelain')
    assert (lanes_repo / 'shared.txt').read_text() in ('claude\n', 'codex\n')     # the first one landed


def test_a_lane_out_of_quota_hands_its_task_to_the_other_lane(lanes_repo):
    outcome, calls, tasks, orch, log = run_parallel(
        lanes_repo, {'claude': ['lanedone', 'lanedone'], 'codex': ['limit']})
    assert outcome == 'done' and tasks['T2']['status'] == 'done'
    claude = [c for c in calls if c[0] == 'claude']
    assert len(claude) == 2 and [c[0] for c in calls].count('codex') == 1
    relay = [c for c in claude if c[2].startswith('AVISO DE RELEVO: la sesión anterior (codex)')]
    assert len(relay) == 1 and relay[0][3] == 'claude'          # in claude's own lane


def test_a_blocked_lane_task_stops_only_when_nothing_else_is_left(lanes_repo):
    outcome, calls, tasks, *_ = run_parallel(lanes_repo, {'claude': ['blocked'], 'codex': ['sleep3', 'lanedone']})
    assert outcome == 'stop' and tasks['T1']['status'] == 'blocked' and tasks['T2']['status'] == 'done'
    assert tasks['T1']['notes'] == '¿A o B?'


def test_failed_acceptance_in_a_lane_reopens_the_task(lanes_repo):
    cfg = json.loads((lanes_repo / 'frontier/orch/config.json').read_text())
    cfg['acceptance'] = [['false']]
    (lanes_repo / 'frontier/orch/config.json').write_text(json.dumps(cfg))
    git(lanes_repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'acceptance off')
    outcome, calls, tasks, *_ = run_parallel(lanes_repo, {'claude': ['lanedone', 'noop', 'noop'], 'codex': ['lanedone', 'noop', 'noop']},
                                             max_runs=6)
    assert all(t['status'] in ('in_progress', 'blocked') for t in tasks.values())
    assert all('aceptación fallida' in t['notes'] for t in tasks.values())


def test_lanes_remove_deletes_worktrees_but_not_shared_inputs(lanes_repo):
    run_parallel(lanes_repo, {'claude': ['lanedone'], 'codex': ['lanedone']})
    clock = Clock()
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=lambda line: None)
    orch.lanes_remove()
    assert not orch.lane_path('claude').exists() and (lanes_repo / 'shared-input/big.bin').exists()
    assert 'lane/' not in git(lanes_repo, 'branch')


def test_codex_may_write_the_main_git_dir_from_a_lane(lanes_repo):
    real = json.loads((ROOT / 'frontier/orch/config.json').read_text())
    assert any('{git_common}' in part for part in real['agents']['codex']['new'])
    clock = Clock()
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=lambda line: None)
    orch.cfg['agents']['codex'] = real['agents']['codex']
    task = {'id': 'T2', 'title': 'two', 'owner': 'codex', 'status': 'pending'}
    cmd, *_ = orch.command('codex', task, False, lane=orch.lane_path('codex'))
    assert f'sandbox_workspace_write.writable_roots=["{lanes_repo.resolve() / ".git"}",' in ' '.join(cmd)
    assert cmd[cmd.index('-C') + 1] == str(orch.lane_path('codex'))


def test_a_kept_lane_branch_is_reused_not_reset(lanes_repo):
    clock = Clock()
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=lambda line: None)
    orch.lanes_setup()
    lane = orch.lane_path('codex')
    (lane / 'unmerged.txt').write_text('x')
    subprocess.run(['git', '-C', str(lane), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(lane), 'commit', '-qm', 'unmerged'], check=True)
    orch.lanes_remove()
    assert 'lane/codex' in git(lanes_repo, 'branch')             # kept: not in main
    orch.lanes_setup()
    assert (orch.lane_path('codex') / 'unmerged.txt').exists()


def test_lane_rebase_works_without_any_git_identity_in_the_environment(lanes_repo, monkeypatch):
    """2026-11-11: the rebase of a lane with its own commits failed with «tell me who you are»."""
    for var in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL'):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv('HOME', str(lanes_repo.parent))          # no global config either
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    outcome, calls, tasks, *_ = run_parallel(
        lanes_repo, {'claude': ['sleep3', 'lanedone'], 'codex': ['lanedone']})
    assert outcome == 'done' and tasks['T1']['status'] == tasks['T2']['status'] == 'done'
    files = git(lanes_repo, 'ls-files').split()
    assert 'done-claude.txt' in files and 'done-codex.txt' in files


def test_the_supervisor_commits_what_a_sandboxed_agent_left(lanes_repo):
    outcome, calls, tasks, orch, log = run_parallel(lanes_repo, {'claude': ['lanedone'], 'codex': ['nocommit']})
    assert outcome == 'done' and tasks['T2']['status'] == 'done'
    assert 'left-codex.txt' in git(lanes_repo, 'ls-files').split()
    body = git(lanes_repo, 'log', '--format=%B', '-n', '20')
    assert 'codex: work left uncommitted' in body and 'Agent: Codex (commit hecho por frontier-orch' in body


def test_codex_in_a_lane_may_write_its_worktree_gitdir(lanes_repo):
    real = json.loads((ROOT / 'frontier/orch/config.json').read_text())
    clock = Clock()
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=lambda line: None)
    orch.lanes_setup()
    orch.cfg['agents']['codex'] = real['agents']['codex']
    task = {'id': 'T2', 'title': 'two', 'owner': 'codex', 'status': 'pending'}
    cmd, *_ = orch.command('codex', task, False, lane=orch.lane_path('codex'))
    gitdir = lanes_repo.resolve() / '.git/worktrees/codex'
    assert f'sandbox_workspace_write.writable_roots=["{lanes_repo.resolve() / ".git"}","{gitdir}"]' in cmd


# ---- non-stop: owner any, dependencies, inbox, follow, drain, stop -----------------------------------------------
def set_tasks(repo, tasks):
    full = [dict({'status': 'pending', 'notes': '', 'evidence': '', 'accept': 'x', 'title': t['id']}, **t)
            for t in tasks]
    (repo / 'frontier/orch/tasks.json').write_text(json.dumps({'tasks': full}))
    git(repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'tasks')


def run_follow(repo, plan, on_idle):
    """auto_parallel(follow=True); on_idle(n, orch) is called at each idle sleep and may add tasks or flags."""
    Path(__import__('os').environ['FAKE_PLAN']).write_text(json.dumps(plan))
    clock, log, sleeps = Clock(), [], []
    orch = fo.Orch(repo, now=clock.now, sleep=lambda s: (sleeps.append(s), on_idle(len(sleeps), orch),
                                                         clock.sleep(s)), out=log.append)
    outcome = orch.auto_parallel(follow=True)
    calls = [json.loads(line) for line in Path(__import__('os').environ['FAKE_CALLS']).read_text().splitlines()]
    tasks = {t['id']: t for t in json.loads((repo / 'frontier/orch/tasks.json').read_text())['tasks']}
    return outcome, calls, tasks, orch, log


def stop_after(n):
    def on_idle(k, orch):
        if k >= n:
            orch.flag('stop').write_text('test')
    return on_idle


def test_an_any_task_goes_to_whichever_lane_is_free(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}, {'id': 'T2', 'owner': 'codex'},
                           {'id': 'T3', 'owner': 'any'}])
    outcome, calls, tasks, *_ = run_parallel(
        lanes_repo, {'claude': ['lanedone', 'lanedone'], 'codex': ['sleep15', 'lanedone']})
    assert outcome == 'done' and all(t['status'] == 'done' for t in tasks.values())
    assert [c[0] for c in calls].count('claude') == 2         # T1 and then T3, while Codex was still on T2


def test_a_task_waits_for_its_after(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}, {'id': 'T3', 'owner': 'codex', 'after': ['T1']}])
    outcome, calls, tasks, orch, log = run_parallel(lanes_repo, {'claude': ['sleep5', 'lanedone'],
                                                                 'codex': ['lanedone']})
    assert outcome == 'done' and tasks['T3']['status'] == 'done'
    t1_done = next(i for i, line in enumerate(log) if 'T1 done and accepted' in line)
    t3_start = next(i for i, line in enumerate(log) if 'starts T3' in line)
    assert t3_start > t1_done


def test_follow_waits_idle_and_takes_tasks_added_through_the_inbox(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}])

    def on_idle(k, orch):
        if k == 1:      # idle after T1: queue T9 as `frontier-orch add` would
            (orch.work / 'inbox').mkdir(exist_ok=True)
            (orch.work / 'inbox/new.json').write_text(json.dumps(
                {'tasks': [{'id': 'T9', 'title': 'nine', 'owner': 'any', 'accept': 'x'}]}))
        if k >= 2:
            orch.flag('stop').write_text('test')
    outcome, calls, tasks, orch, log = run_follow(lanes_repo, {'claude': ['lanedone', 'lanedone'],
                                                               'codex': ['lanedone']}, on_idle)
    assert outcome == 'stop' and tasks['T1']['status'] == 'done' and tasks['T9']['status'] == 'done'
    assert any('queued from the inbox: T9' in line for line in log)
    assert 'queue T9 (inbox)' in git(lanes_repo, 'log', '--format=%s')
    assert not orch.flag('stop').exists()       # consumed
    assert fo.TURN.search((lanes_repo / 'frontier/REPARTO.md').read_text()).group(2).startswith('libre')


def test_follow_observes_stop_within_a_minute_during_cooldown(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'any'}])
    clock, waits = Clock(), []
    orch = fo.Orch(lanes_repo, now=clock.now, out=lambda line: None)
    orch.state['cooldown'] = {a: clock.now() + 3600 for a in orch.cfg['agents']}

    def sleep(seconds):
        waits.append(seconds)
        orch.flag('stop').write_text('test')
        clock.sleep(seconds)

    orch.sleep = sleep
    assert orch.auto_parallel(follow=True) == 'stop'
    assert len(waits) == 1 and 0 < waits[0] <= 60
    assert orch.tasks()[0]['status'] == 'pending'
    assert orch.turn().startswith('libre')


def test_follow_does_not_stop_for_a_blocked_task(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}, {'id': 'T2', 'owner': 'claude'},
                           {'id': 'T3', 'owner': 'codex'}])
    outcome, calls, tasks, orch, log = run_follow(
        lanes_repo, {'claude': ['blocked', 'lanedone'], 'codex': ['lanedone']}, stop_after(1))
    assert tasks['T1']['status'] == 'blocked' and tasks['T2']['status'] == 'done' and tasks['T3']['status'] == 'done'
    assert any('blocked for you: T1' in line for line in log)


def test_a_bad_inbox_file_is_refused_and_does_not_stop_anything(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}])
    inbox = lanes_repo / 'work/orch/inbox'
    inbox.mkdir(parents=True)
    (inbox / 'bad.json').write_text(json.dumps({'id': 'T1', 'title': 'dup', 'owner': 'claude', 'accept': 'x'}))
    outcome, calls, tasks, orch, log = run_parallel(lanes_repo, {'claude': ['lanedone'], 'codex': []})
    assert outcome == 'done' and (inbox / 'refused/bad.json').exists()
    assert any('refused' in line and 'already' in line for line in log)


def test_drain_finishes_the_task_in_hand_and_takes_no_new_one(lanes_repo):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude', 'status': 'in_progress'},
                           {'id': 'T2', 'owner': 'claude'}, {'id': 'T3', 'owner': 'codex'}])
    clock = Clock()
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=lambda line: None)
    orch.state['lane_of'] = {'T1': 'claude'}
    orch.save_state()
    orch.flag('drain').write_text('test')
    outcome, calls, tasks, orch, log = run_parallel(lanes_repo, {'claude': ['commit', 'lanedone'], 'codex': []})
    assert outcome == 'stop' and tasks['T1']['status'] == 'done'
    assert tasks['T2']['status'] == tasks['T3']['status'] == 'pending' and len(calls) == 2
    assert any('drain requested' in line for line in log) and not orch.flag('drain').exists()


def test_stop_ends_after_the_runs_in_hand(lanes_repo, monkeypatch):
    set_tasks(lanes_repo, [{'id': 'T1', 'owner': 'claude'}, {'id': 'T2', 'owner': 'claude'}])
    monkeypatch.setenv('FAKE_STOP_FLAG', str(lanes_repo / 'work/orch/stop'))
    Path(__import__('os').environ['FAKE_PLAN']).write_text(json.dumps({'claude': ['stopflag', 'lanedone'],
                                                                       'codex': []}))
    clock, log = Clock(), []
    orch = fo.Orch(lanes_repo, now=clock.now, sleep=clock.sleep, out=log.append)
    outcome = orch.auto_parallel()
    tasks = {t['id']: t for t in json.loads((lanes_repo / 'frontier/orch/tasks.json').read_text())['tasks']}
    assert outcome == 'stop' and tasks['T2']['status'] == 'pending'
    assert any('stop requested' in line for line in log)


@pytest.mark.parametrize('task, problem', [
    ({'id': 'X', 'title': 't', 'owner': 'gemini', 'accept': 'a'}, 'owner'),
    ({'id': 'X', 'title': 't', 'owner': 'any'}, 'missing accept'),
    ({'id': 'T1', 'title': 't', 'owner': 'any', 'accept': 'a'}, 'already'),
    ({'id': 'X', 'title': 't', 'owner': 'any', 'accept': 'a', 'after': 'T1'}, 'after'),
    ({'id': 'X', 'title': 't', 'owner': 'any', 'accept': 'a', 'after': ['T1']}, ''),
])
def test_check_task(task, problem):
    got = fo.check_task(task, {'T1'})
    assert (problem in got) if problem else got == ''


def test_add_drain_stop_and_resume_from_the_command_line(lanes_repo, tmp_path):
    script = ROOT / 'frontier/orch/frontier_orch.py'
    task = tmp_path / 'more.json'
    task.write_text(json.dumps({'tasks': [{'id': 'T7', 'title': 's', 'owner': 'any', 'accept': 'a'}]}))
    cli = lambda *a: subprocess.run([sys.executable, str(script), *a, '--root', str(lanes_repo)],
                                    capture_output=True, text=True)
    assert 'queued T7' in cli('add', str(task)).stdout
    assert len(list((lanes_repo / 'work/orch/inbox').glob('*.json'))) == 1
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps({'id': 'T1', 'title': 's', 'owner': 'any', 'accept': 'a'}))
    assert 'already' in cli('add', str(bad)).stderr
    cli('drain')
    assert (lanes_repo / 'work/orch/drain').exists() and 'drain requested' in cli('status').stdout
    cli('resume')
    assert not (lanes_repo / 'work/orch/drain').exists()
