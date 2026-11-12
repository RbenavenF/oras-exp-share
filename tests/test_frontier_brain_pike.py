"""Lucy adapter: room thresholds, v2 state preservation and one room/reward per victory."""
import struct
import pytest
from test_frontier_pike import zone, rooms_run, battle_points_run, natives
import brains
import pike
import patch as fp
import data as fd
from pawn_vm import VM

SHIFT = 2 * (pike.ROUTE - 1)


@pytest.mark.parametrize('symbols', [0, 1, 2, 3])
def test_thresholds_and_pause_recomputation(zone, symbols):
    _, _, script, labels = zone
    works = {fp.WORK_ROUTE: 6, brains.WORK_SYMBOLS: symbols << SHIFT}
    streak = 0
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GetMyWinCount': lambda vm, a: streak})
    for streak in (26, 27, 28, 138, 139, 140, 194, 195, 196, 250, 251, 252):
        for _ in range(2):
            VM(script, stubs, {}).run(labels['brains_check'])
            v = brains.due('pike', streak + 1, 3 if symbols == 2 else symbols)
            assert works[brains.WORK_BRAIN] == (6 + 8*v if v else 0)
        assert works[brains.WORK_SYMBOLS] == symbols << SHIFT


@pytest.mark.parametrize('streak,symbols', [(27, 0), (139, 1), (195, 3), (27, 3)])
def test_lucy_replaces_room_draw_keeps_all_v2_state_and_normal_rank(zone, streak, symbols):
    state = {w: k + 1 for k, w in enumerate((*fp.PIKE_HP, *fp.PIKE_ST, *(w for pair in fp.PIKE_PP for w in pair)))}
    works = {fp.WORK_ROUTE: 6, pike.STREAK: streak, pike.RECORD: streak + 20,
             brains.WORK_SYMBOLS: symbols << SHIFT, fp.PIKE_WILD: fp.PIKE_WILD_FIRST, **state}
    assert rooms_run(zone, works, []) == [('rank', 0)]
    assert works[fp.PIKE_WILD] == 0 and works[pike.STREAK] == streak and works[pike.RECORD] == streak + 20
    assert {w: works[w] for w in state} == state
    assert works[brains.WORK_BRAIN] == 6 + 8 * brains.due('pike', streak + 1, symbols)


def test_nonbattle_room_can_lead_directly_to_lucy(zone):
    works = {fp.WORK_ROUTE: 6, pike.STREAK: 26, pike.RECORD: 26}
    assert rooms_run(zone, works, [pike.ROOM_DONE]) == [('global', pike.GLOBAL_ROOM), ('rank', 0)]
    assert works[pike.STREAK] == works[pike.RECORD] == 27 and works[brains.WORK_BRAIN] == 14


@pytest.mark.parametrize('variant,streak,initial', [(1, 27, 0), (2, 139, 1), (2, 195, 3)])
@pytest.mark.parametrize('win', [True, False])
def test_result_symbols_bonus_and_no_duplicate_room_or_prize(zone, variant, streak, initial, win):
    _, _, script, labels = zone
    works = {fp.WORK_ROUTE: 6, pike.STREAK: streak, brains.WORK_SYMBOLS: initial << SHIFT,
             brains.WORK_BRAIN: 6 + 8 * variant}
    log = []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GlobalCall': lambda vm, a: log.append(('msg', works[brains.WORK_MSG]))})
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    # Real win path already increments through AddWinCount. The award must never count a second room.
    if win:
        works[pike.STREAK] += 1
    routine = 'brains_won' if win else 'brains_lost'
    VM(script, stubs, calls).run(labels[routine])
    want = (1 if variant == 1 else 3) | initial if win else initial
    assert works[brains.WORK_SYMBOLS] == want << SHIFT
    assert works[pike.STREAK] == streak + int(win) and works[brains.WORK_BRAIN] == 0
    assert [v for k, v in log if k == 'bp'] == ([10] if win else [])
    if win:
        assert battle_points_run(zone, streak + 1)[0] == ('bp', fd.FRONTIER_BP['pike'][min((streak + 1)//14, 30)-1])
    before = dict(works), list(log)
    VM(script, stubs, calls).run(labels[routine])
    assert (works, log) == before


def test_lucy_exact_teams_and_identity():
    expected = {
        1: (16, [(336,217,2,(252,0,252,0,6,0),(207,242,305,202)),
                 (213,150,5,(252,0,0,0,106,252),(92,201,182,156)),
                 (350,234,15,(152,0,100,0,152,106),(58,243,57,105))]),
        2: (31, [(336,230,5,(252,0,0,0,252,6),(207,242,188,202)),
                 (208,213,2,(252,0,0,0,6,252),(89,157,153,103)),
                 (130,150,3,(252,6,0,0,0,252),(349,216,46,156))])}
    rows = brains.brain_rows()
    for v, (iv, team) in expected.items():
        trainer = brains.trainer_id('pike', v)
        assert trainer == 138 + v
        assert fd.parse_trainer(brains.trainers()[trainer]) == {'class': 13, 'sets': tuple(brains.set_index('pike',v,k) for k in range(3))}
        at = brains.ENTRY * (10 + v - 1)
        assert struct.unpack_from('<HBB', rows, at) == (trainer, iv, 0)
        for k, (species,item,nature,ev,moves) in enumerate(team):
            idx = brains.set_index('pike', v, k)
            s = fd.parse_set(brains.sets()[idx])
            assert (s['species'],s['item'],s['nature'],s['moves']) == (species,item,nature,moves)
            hp,atk,df,spe,spa,spd = ev
            assert struct.unpack_from('<H6B', rows, at+4+8*k) == (idx,hp,atk,df,spa,spd,spe)
    assert brains.trainer_names()[10:12] == ['Lucy','Lucy']
    assert brains.APPEARANCES['pike'] == (28,140,56) and 'pike' in brains.ENABLED


def test_reception_symbols_is_available(zone):
    _, _, script, labels = zone
    works = {brains.WORK_SYMBOLS: 1 << SHIFT, fp.WORK_ROUTE: 3}
    said = []
    stubs = natives({'WorkGet': lambda vm,a: works.get(a[0],0),
                     'WorkSet': lambda vm,a: works.__setitem__(a[0],a[1]),
                     'GlobalCall': lambda vm,a: said.append(works[brains.WORK_MSG])})
    VM(script, stubs, {}).run(labels['brains_symbols'])
    assert said == [brains.MORE+4*5+2] and works[fp.WORK_ROUTE] == 3
