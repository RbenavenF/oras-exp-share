"""Event-state regression checks; native rendering, movement and battles are mocked, not emulated."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'faraway'))
import build as faraway_build
import event as ev
from pawn import OPCODES, Program, Script, gf_hash, s32
from formats import garc_entries


@pytest.fixture
def programs(monkeypatch):
    game = ROOT / 'baseline/oras/repolished/romfs'
    if not (game / 'a/0/1/3').exists():
        pytest.skip('Local baseline required')
    shared = (game / 'a/0/2/9').read_bytes()
    entries = garc_entries(shared)
    ferry, giver = (Script.parse(shared[entries[i][2]:entries[i][2] + entries[i][3]]) for i in (79, 10))
    meadow = faraway_build.zone_files(game, 215)
    # Retain symbolic labels for entering event routines; still assemble and round-trip every script.
    build_script = Program.build_script

    def checked_program(self, main):
        raw = build_script(self, main).build()
        assert Script.parse(raw).build() == raw
        return self

    monkeypatch.setattr(Program, 'build_script', checked_program)
    return (ev.meadow_entity_script(faraway_build.entity_script(meadow[1])),
            ev.meadow_script(Script.parse(meadow[2]), ferry, giver))


def run(program, entry, works, flags, battle_result=4):
    """Execute the event's symbolic control flow, mocking retail helpers and native side effects."""
    labels = {item[1]: i for i, item in enumerate(program.items) if isinstance(item, tuple)}
    names = {s32(gf_hash(n)): n for n in (
        'FlagGet', 'FlagSet', 'WorkGet', 'WorkSet', 'WildBattleResultGet', 'CallWildBattle',
        'VoicePlay', 'MdlAcmdInit', 'MdlAcmdMakeMoveEx', 'MdlAcmdSetEnd', 'LastKeyWait', 'MdlDel',
        'CallApplicationDemo')}
    pc, pri, stack, locals_, calls = labels[entry], 0, [], {}, []
    for _ in range(1000):
        item = program.items[pc]
        pc += 1
        if isinstance(item, tuple):
            continue
        op, a = OPCODES[item.op], item.args
        if op in ('PROC', 'STACK_P'):
            continue
        if op in ('PUSH_C', 'PUSH_P_C'):
            stack.append(a[0])
        elif op == 'PUSH_PRI':
            stack.append(pri)
        elif op == 'PUSH_P_S':
            stack.append(locals_[a[0]])
        elif op == 'STOR_P_S_PRI':
            locals_[a[0]] = pri
        elif op == 'LOAD_P_S_PRI':
            pri = locals_[a[0]]
        elif op == 'ZERO_PRI':
            pri = 0
        elif op == 'EQ_P_C_PRI':
            pri = int(pri == a[0])
        elif op in ('JUMP', 'JNZ', 'JZER'):
            if op == 'JUMP' or (op == 'JNZ' and pri) or (op == 'JZER' and not pri):
                pc = labels[a[0]]
        elif op == 'SWITCH':
            table = program.items[labels[a[0]] + 1].args
            pc = labels[dict(zip(table[2::2], table[3::2])).get(pri, table[1])]
        elif op == 'CALL':
            # These tests enter routines directly; only retail dialogue/wait helpers may be mocked.
            assert a[0].startswith('f') or a[0] == 'L4', a[0]
            count = stack.pop() // 4
            args = tuple(stack.pop() for _ in range(count))
            calls.append(('helper:' + a[0], args))
        elif op == 'SYSREQ_N':
            name = names.get(program.native_hashes[a[0]], f'native{program.native_hashes[a[0]]:x}')
            args = tuple(stack.pop() for _ in range(a[1] // 4))
            calls.append((name, args))
            pri = 0
            if name == 'WorkGet':
                pri = works.get(args[0], 0)
            elif name == 'WorkSet':
                works[args[0]] = args[1]
            elif name == 'FlagGet':
                pri = int(args[0] in flags)
            elif name == 'FlagSet':
                flags.add(args[0])
            elif name == 'WildBattleResultGet':
                pri = battle_result
        elif op == 'RETN':
            assert not stack
            return calls
        else:
            pytest.fail(f'Unsupported event instruction: {op}')
    pytest.fail('Event did not return')


@pytest.mark.parametrize('captured', [False, True])
def test_entry_only_arms_chase_when_mew_exists(programs, captured):
    works = {ev.WORK_MEW_SPOT: 3}
    flags = {ev.FLAG_MEW_CAPTURED} if captured else set()
    run(programs[0], 'meadow_reset', works, flags)
    assert works[ev.WORK_MEW_SPOT] == (ev.MEW_SPOT_INACTIVE if captured else 0)


@pytest.mark.parametrize('result', [1, 2, 3, 4])
def test_battle_disarms_triggers_until_next_visit(programs, result):
    works, flags = {ev.WORK_MEW_SPOT: len(ev.MEW_SPOTS) - 1}, set()
    calls = run(programs[1], 'mew', works, flags, result)
    assert ('CallWildBattle', (ev.STATIC_MEW,)) in calls
    assert ('MdlDel', (0,)) in calls
    after_battle = calls[calls.index(('CallWildBattle', (ev.STATIC_MEW,))) + 1:]
    fades = [i for i, (name, args) in enumerate(after_battle) if name.startswith('helper:ffade_in_')]
    if result != 4:
        assert len(fades) == 1
        assert after_battle[fades[0]][1] == (2, 4)
        assert fades[0] < after_battle.index(('LastKeyWait', ()))
        messages = [args for name, args in after_battle if name.startswith('helper:fmsg_')]
        assert messages == [(ev.M['vanished'], 255, 0, 256, 0)]
    else:
        assert not fades
    assert works[ev.WORK_MEW_SPOT] == ev.MEW_SPOT_INACTIVE
    assert (ev.FLAG_MEW_CAPTURED in flags) == (result == 4)
    assert not any(n.startswith('MdlAcmd') or n == 'VoicePlay'
                   for n, _ in run(programs[1], 'mew_flee', works, flags))
    run(programs[0], 'meadow_reset', works, flags)
    assert works[ev.WORK_MEW_SPOT] == (ev.MEW_SPOT_INACTIVE if result == 4 else 0)


def test_four_escapes_then_no_more_movement(programs):
    works, flags = {ev.WORK_MEW_SPOT: 0}, set()
    for expected in range(1, len(ev.MEW_SPOTS)):
        calls = run(programs[1], 'mew_flee', works, flags)
        assert works[ev.WORK_MEW_SPOT] == expected
        assert sum(n == 'MdlAcmdMakeMoveEx' for n, _ in calls) == 1
    assert not any(n.startswith('MdlAcmd') for n, _ in run(programs[1], 'mew_flee', works, flags))


def test_captured_mew_ignores_stale_armed_trigger(programs):
    calls = run(programs[1], 'mew_flee', {ev.WORK_MEW_SPOT: 0}, {ev.FLAG_MEW_CAPTURED})
    assert not any(n.startswith('MdlAcmd') or n == 'VoicePlay' for n, _ in calls)


@pytest.mark.parametrize('briney_state', [0, 2, 8])
def test_boat_scene_keeps_brineys_story_state(programs, briney_state):
    """The crossing plays Briney's boat scene with his work at 6, as retail does, then restores the player's value."""
    game = ROOT / 'baseline/oras/repolished/romfs'
    shared = (game / 'a/0/2/9').read_bytes()
    entries = garc_entries(shared)
    ferry, giver = (Script.parse(shared[entries[i][2]:entries[i][2] + entries[i][3]]) for i in (79, 10))
    p = Program.from_script(Script.parse(faraway_build.zone_files(game, 214)[2]))
    w = ev.Writer(p, ferry, ev.import_helpers(p, ferry, giver, 'L4'), ferry.natives[ev.FERRY_FADE_NATIVE][1])
    ev.begin_routine(p, 'crossing')
    w.travel(*ev.ARRIVE_HARBOR)
    ev.end_routine(p)
    works = {ev.WORK_BRINEY_BOAT: briney_state}
    calls = run(p, 'crossing', works, set())
    demo = calls.index(('CallApplicationDemo', (ev.APP_DEMO_BOAT, 0, 0, 0, 0, 0, 0, 0, ev.APP_DEMO_BOAT_ARG)))
    assert ('WorkSet', (ev.WORK_BRINEY_BOAT, ev.BRINEY_BOAT_DEMO_STATE)) in calls[:demo]
    assert calls[-1][0].startswith('helper:fmapchange_') and calls[-1][1] == ev.ARRIVE_HARBOR + (0,)
    assert works[ev.WORK_BRINEY_BOAT] == briney_state
