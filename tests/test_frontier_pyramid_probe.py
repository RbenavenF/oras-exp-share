"""Experiment apparatus: VM assertions are not evidence of running in Azahar."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import factory
import overlay
import patch
import pyramid_probe as probe
import tower
from pawn import Script, gf_hash, s32
from pawn_vm import VM


@pytest.fixture(scope='module')
def retail():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    return overlay.maison_retail(overlay.ZONES.read_bytes())[1]


def run_select(retail, mode=(1, 0, 7), selected=1, busy=None):
    p = probe.program(retail)
    labels = p.layout()
    script = p.build_script(f'L{retail.main:x}')
    works, log = dict(busy or {}), []
    def app(vm, args):
        works.update(zip((0x800c, 0x800d, 0x800e), mode))
    def select(vm, args):
        log.append(('selection', args))
        return selected
    functions = {
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
    }
    for name in ('BattleInstWorkCreate', 'BattleInstWorkDelete', 'BattleHouse_End', 'SetRank', '_MapChangeCore'):
        functions[name] = lambda vm, a, name=name: log.append((name, a))
    calls = {labels[name]: lambda vm, a: 0 for name in
             ('L798', 'La9c', f'L{factory.MSG:x}', f'L{factory.MSG_WAIT:x}', f'L{factory.MSG_CLOSE:x}')}
    calls[labels[tower.MODE_APP]] = app
    calls[labels['L457c']] = select
    VM(script, {s32(gf_hash(n)): f for n, f in functions.items()}, calls).run(labels['probe_select'])
    return works, log


def test_selection_kept_alive_until_map_change(retail):
    works, log = run_select(retail)
    assert works[patch.WORK_ROUTE] == 7 and works[probe.ACTIVE] == 1
    assert ('selection', [7]) in log
    assert log[-1] == ('_MapChangeCore', [141, 19, 0, 18, 0, 0, 0, 1, 0])
    assert not any(name in ('BattleInstWorkDelete', 'BattleHouse_End') for name, _ in log)


@pytest.mark.parametrize('mode,selected', [((0, 0, 7), 1), ((1, 1, 7), 1), ((1, 0, 7), 0)])
def test_cancel_releases_work_without_warp_or_active_flag(retail, mode, selected):
    works, log = run_select(retail, mode, selected)
    assert works.get(probe.ACTIVE, 0) == 0
    assert not any(name == '_MapChangeCore' for name, _ in log)
    assert log[-2:] == [('BattleHouse_End', []), ('BattleInstWorkDelete', [])]


@pytest.mark.parametrize('other', [n for n in patch.ACTIVE_WORK if n != 'pyramid'])
def test_other_challenges_refused_before_work_created(retail, other):
    before = {patch.ACTIVE_WORK[other]: 1}
    works, log = run_select(retail, busy=before)
    assert works == before and log == []


@pytest.mark.parametrize('floor', [False, True])
def test_probe_roundtrip_and_dispatch(retail, floor):
    p = probe.program(retail, floor)
    script = p.build_script(f'L{retail.main:x}')
    assert Script.parse(script.build()).build() == script.build()
    assert len(script.build()) < 16000
    # An entry event must not run the Maison cleanup, which would destroy the experiment.
    from pawn import OP, Op
    at = factory._index(p, f'L{retail.main:x}')
    table = next(o for o in p.items[at:] if isinstance(o, Op) and o.op == OP['CASETBL'])
    stub = dict(zip(table.args[2::2], table.args[3::2]))[1]
    at = factory._index(p, stub)
    call = next(o for o in p.items[at:] if isinstance(o, Op) and o.op == OP['CALL'])
    assert call.args == ['L1294']


def test_floor_battle_uses_existing_work_without_incrementing_streak(retail):
    p = probe.program(retail, True)
    script, labels, log = p.build_script(f'L{retail.main:x}'), p.layout(), []
    functions = {s32(gf_hash(name)): (lambda vm, a, name=name: log.append((name, a)))
                 for name in ('SetTrainer', 'StartBattle', 'IsWin')}
    calls = {labels[n]: lambda vm, a: 0 for n in ('L798', 'La9c', 'L4')}
    VM(script, functions, calls).run(labels['probe_battle'])
    assert log == [('SetTrainer', [0]), ('StartBattle', [0, 1]), ('IsWin', [])]
