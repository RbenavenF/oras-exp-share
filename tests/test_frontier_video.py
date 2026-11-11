"""F7-VIDEO: execute the generated menus and recorder for every facility, preserving the original Maison."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import arena
import battle_video
import dome
import overlay
import palace
import patch
import pike
import pyramid
import tower
from pawn import OP, Op, Program, gf_hash, s32
from pawn_vm import Stop, VM


@pytest.fixture(scope='module')
def retail():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    return overlay.maison_retail(overlay.ZONES.read_bytes())[1]


BUILDERS = {
    'factory': overlay.maison_program, 'tower': tower.tower_program, 'palace': palace.palace_program,
    'arena': arena.arena_program, 'dome': dome.dome_program, 'pike': pike.pike_program,
    'pyramid': pyramid.lobby_program, 'pyramid_floor': pyramid.floor_program,
}


def menu(program, route, hidden):
    """Run the actual next-battle menu, stopping when it opens its applet. Preserve labels and all branches."""
    labels = program.layout()
    script = program.build_script(f'L{program.script.main:x}')
    added = []
    natives = {h: lambda vm, a: 0 for _, h in script.natives}
    natives[s32(gf_hash('WorkGet'))] = lambda vm, a: route if a == [patch.WORK_ROUTE] else 0
    natives[s32(gf_hash('ListMenuAdd'))] = lambda vm, a: added.append(a)
    calls = {labels[x.args[0]]: lambda vm, a: 0 for x in program.items
             if isinstance(x, Op) and x.op == OP['CALL']}
    def show(vm, args):
        raise Stop()
    calls[labels['L10b4']] = show
    with pytest.raises(Stop):
        VM(script, natives, calls).run(labels['L3b90'], 0, 0, hidden)
    return added


def record(program, route):
    labels = program.layout()
    script = program.build_script(f'L{program.script.main:x}')
    events = []
    natives = {
        s32(gf_hash('WorkGet')): lambda vm, a: route if a == [patch.WORK_ROUTE] else 0,
        s32(gf_hash('SaveBattleRecord')): lambda vm, a: events.append(('record', a)),
    }
    calls = {labels['L4']: lambda vm, a: events.append(('wait', a))}
    assert VM(script, natives, calls).run(labels[battle_video.VIDEO_RECORD], 0) == 0
    return events


@pytest.mark.parametrize('facility', BUILDERS)
def test_each_facility_has_no_video_after_win_loss_or_pause(retail, facility):
    program = BUILDERS[facility](retail)
    route = patch.ROUTE['pyramid' if facility == 'pyramid_floor' else facility]
    # Both argument values used by the retail flow; Continue=0 and Pause=2 remain exactly as before.
    for hidden in (0, 1):
        assert menu(program, route, hidden) == [[67, 0, 0], [69, 2, 0]]
    # All three loss/end call sites still return normally, without opening SaveBattleRecord or its wait.
    assert record(program, route) == []
    assert len([x for x in program.items if isinstance(x, Op) and x.op == OP['CALL']
                and x.args == [battle_video.VIDEO_RECORD]]) == 3


def test_original_maison_keeps_its_video_and_other_menu_entries(retail):
    original, modified = Program.from_script(retail), overlay.maison_program(retail)
    for hidden in (0, 1):
        assert menu(modified, 0, hidden) == menu(original, 0, hidden)
    assert menu(modified, 0, 0) == [[67, 0, 0], [69, 2, 0], [68, 1, 0]]
    assert record(modified, 0) == record(original, 0) == [('record', [0]), ('wait', [1])]
