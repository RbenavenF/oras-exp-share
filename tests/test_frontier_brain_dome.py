"""Tucker: final-only eligibility, exact teams, preview/selection and the native two-member constructor."""
from itertools import permutations
from pathlib import Path
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / d) for d in ("scripts", "frontier")]

import pytest

import brains
import dome
import data as fd
import overlay
import patch as fp
from pawn_vm import VM
from test_frontier_brain_arena import Game as ArenaGame
from test_frontier_brains import C, MEMBERS, TEMPS, start
from test_frontier_dome import helpers, natives, shared, round_run

ROUTE = dome.ROUTE
SHIFT = 2 * (ROUTE - 1)


@pytest.fixture(scope='module')
def zone():
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = dome.dome_program(retail)
    return program.build_script(f'L{retail.main:x}'), program.layout()


class Game(ArenaGame):
    def __init__(self, script, labels, symbols=0):
        super().__init__(script, labels, symbols)
        self.works[fp.WORK_ROUTE] = ROUTE

    @property
    def symbols(self):
        return self.works[brains.WORK_SYMBOLS] >> SHIFT & 3


def test_challenge_and_repeated_finals(zone):
    g = Game(*zone, symbols=0x0041)
    met = [(s + 1, v) for s in range(100) if (v := g.battle(s))]
    assert met == [(20, 1), (40, 2), (60, 2), (80, 2), (100, 2)]
    assert g.bp == 50 and g.symbols == 3
    assert g.works[brains.WORK_SYMBOLS] == 0x0041 | 3 << SHIFT


@pytest.mark.parametrize('symbols', range(4))
def test_every_battle_only_final_and_exact_unit(zone, symbols):
    g = Game(*zone, symbols=symbols << SHIFT)
    for s in range(101):
        g.run('brains_check', s)
        v = brains.due('dome', (s + 1) // 4, 3 if symbols == 2 else symbols) if s % 4 == 3 else 0
        assert g.works[brains.WORK_BRAIN] == (ROUTE + 8 * v if v else 0)
    assert g.bp == 0


@pytest.mark.parametrize('silver', [False, True])
def test_loss_pause_and_award_once(zone, silver):
    g = Game(*zone, symbols=(1 << SHIFT) if silver else 0)
    s, v = (39, 2) if silver else (19, 1)
    for _ in range(3):
        g.run('brains_check', s)
        assert g.works[brains.WORK_BRAIN] == ROUTE + 8 * v
    assert g.bp == 0
    assert g.battle(s, win=False) == v
    assert g.symbols == int(silver) and g.bp == 0
    assert g.said[-1] == brains.MORE + 4 * (ROUTE - 1)
    assert g.battle(s) == v
    saved = dict(g.works)
    g.run('brains_won')
    assert g.bp == 10 and g.works == saved
    g.run('brains_check', s + 1)
    assert g.works[brains.WORK_BRAIN] == 0


@pytest.mark.parametrize('symbols,offset', [(0, 1), (1, 2), (2, 3), (3, 3)])
def test_symbols_consult_without_changing_route(zone, symbols, offset):
    g = Game(*zone, symbols=symbols << SHIFT)
    g.works[fp.WORK_ROUTE] = 6
    g.run('brains_symbols')
    assert g.said == [brains.MORE + 4 * (ROUTE - 1) + offset]
    assert g.works[fp.WORK_ROUTE] == 6


@pytest.mark.parametrize('variant', [1, 2])
def test_preview_and_two_from_fixed_trio(shared, variant):
    *_, script, labels = shared
    works = {dome.WORK_STREAK: 19 if variant == 1 else 39, brains.WORK_BRAIN: ROUTE + 8 * variant,
             **dict(zip(dome.TEAM, (4, 1, 0)))}
    menus, answers = [], iter([0, 65535, 0, 2, 0])  # back once: the trio cannot change
    current = []
    def menu_init(vm, a):
        current.clear()
    def menu_run(vm, a):
        menus.append(list(current))
        return next(answers)
    h = helpers(labels)
    calls = {h['msg']: lambda vm, a: 0, h['msg_wait']: lambda vm, a: 0, h['msg_close']: lambda vm, a: 0,
             h['menu_init']: menu_init, h['menu_run']: menu_run}
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     '_GetRealTimeToSecond': lambda vm, a: 12345,
                     'ListMenuAdd': lambda vm, a: current.append((a[0], a[1])),
                     'WordSetTemotiMonsNickName': lambda vm, a: 0})
    VM(script, stubs, calls).run(labels['dome_round'])
    trio = [brains.set_index('dome', variant, k) for k in range(3)]
    assert [works[w] for w in dome.RIVAL] == trio
    preview = [(dome.brain_preview_base() + 3 * (variant - 1) + k, k) for k in range(3)]
    assert menus[0] == menus[2] == preview
    assert len(set(works[w] for w in fp.DOME_FORCED)) == 2
    assert {works[w] for w in fp.DOME_FORCED} <= set(trio)
    assert [works[w] for w in fp.DOME_FIGHT] == [0, 4]


@pytest.mark.parametrize('variant', [1, 2])
@pytest.mark.parametrize('selected', list(permutations(range(3), 2)))
def test_native_keeps_the_two_selected_members_and_their_exact_evs(variant, selected):
    forced = tuple(brains.set_index('dome', variant, k) for k in selected)
    result, calls = start(ROUTE, ROUTE + 8 * variant, brains.trainer_id('dome', variant), 2, forced)
    assert result == 0x55
    loads = [c for c in calls if c[0] == C['CODE_LOAD_SET']]
    assert [c[3] for c in loads] == list(forced)
    copies = [c[1:3] for c in calls if c[0] == C['CODE_COPY']]
    assert copies == list(zip(MEMBERS[:2], TEMPS[:2]))
    iv, team = brains.TEAMS['dome', variant]
    assert [c[3] for c in calls if c[0] == C['CODE_MAKE_PARAM']] == [iv, iv]
    for k, index in enumerate(selected):
        hp, atk, df, spe, spa, spd = team[index][3]
        assert [c[2:4] for c in calls if c[0] == C['CODE_EV_SET'] and c[1] == TEMPS[k]] == (
            [(j, 0) for j in range(6)] + list(enumerate((hp, atk, df, spa, spd, spe))))


@pytest.mark.parametrize('forced,count', [((247, 247), 2), ((246, 248), 2), ((247, 250), 2), ((247, 248), 3)])
def test_native_invalid_dome_selection_never_indexes_outside_row(forced, count):
    _, calls = start(5, 13, 137, count, forced)
    assert [c[0] for c in calls] == [C['CODE_START']]


def test_annex_and_preview_text():
    expected = {1: [(260, 230, 2, (57, 89, 58, 68)), (373, 157, 3, (89, 280, 337, 332)),
                    (6, 214, 17, (315, 157, 332, 89))],
                2: [(260, 234, 2, (57, 89, 58, 243)), (376, 217, 2, (94, 309, 89, 182)),
                    (380, 150, 15, (85, 94, 347, 156))]}
    sets = brains.sets()
    for v in (1, 2):
        parsed = [fd.parse_set(sets[brains.set_index('dome', v, k)]) for k in range(3)]
        assert [(s['species'], s['item'], s['nature'], s['moves']) for s in parsed] == expected[v]
        assert fd.parse_trainer(brains.trainers()[136 + v])['class'] == 10
    assert dome.brain_preview_lines(7) == ['Swampert (Cinta Focus)', 'Salamence (Baya Ziuela)',
        'Charizard (Hierba Blanca)', 'Swampert (Restos)', 'Metagross (Garra Rápida)', 'Latias (Baya Atania)']


def test_temporary_selection_cleanup_preserves_symbols_streak_and_entry(zone):
    script, labels = zone
    works = {brains.WORK_SYMBOLS: 1 << SHIFT, dome.STREAK: 20, dome.RECORD: 20,
             **dict(zip(dome.TEAM, (4, 1, 0))),
             **{w: 250 for w in (*dome.RIVAL, *fp.DOME_FORCED, *fp.DOME_FIGHT)}}
    stubs = natives({'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1])})
    VM(script, stubs, {}).run(labels['dome_clear'])
    assert all(works[w] == 0 for w in (*dome.RIVAL, *fp.DOME_FORCED, *fp.DOME_FIGHT))
    assert works[brains.WORK_SYMBOLS] == 1 << SHIFT and works[dome.STREAK] == works[dome.RECORD] == 20
    assert [works[w] for w in dome.TEAM] == [4, 1, 0]
