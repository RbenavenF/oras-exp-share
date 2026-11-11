"""Suppress Frontier battle videos using the measured Maison script routines (reports/frontier.md §33).

The Factory shares its script with the original Maison: `route` limits suppression to its challenge.
Other facilities suppress unconditionally. No engine, menu text or result values change.
"""
from pawn import OP, Op, Program
import patch

VIDEO_MENU = 'L3d2c'   # 0x3d08 LOAD arg20 / JNZ: skip ListMenuAdd(68, 1, 0)
VIDEO_ITEM = 68
VIDEO_RECORD = 'L3fdc' # SaveBattleRecord + L4 wait; calls at 0x21d0, 0x2250, 0x25dc


def _guard(p, route, target, jump):
    b = Program(p.script)
    b.native_hashes = p.native_hashes
    b.sysreq('WorkGet', patch.WORK_ROUTE)
    b.emit('EQ_P_C_PRI', route)
    b.emit(jump, target)
    return b.items


def hide_video(p, route=None):
    """The «next battle» menu (0x3ce4..0x3d20: Continuar 67, Pausar 69, Guardar vídeo 68 only if argument 20 is 0)
    skips the video item unconditionally, or only on `route` when sharing the script with the original Maison."""
    add = p.native('ListMenuAdd')
    found = []
    for i in range(len(p.items) - 6):
        a, b, c, d, e, f = p.items[i:i + 6]
        if (all(isinstance(x, Op) for x in (a, b, c, d, e, f)) and a.op == OP['LOAD_P_S_PRI'] and a.args == [20]
                and b.op == OP['JNZ'] and b.args == [VIDEO_MENU] and [x.op for x in (c, d, e)] == [OP['PUSH_P_C']] * 3
                and [x.args for x in (c, d, e)] == [[0], [1], [VIDEO_ITEM]] and f.op == OP['SYSREQ_N']
                and f.args[0] == add):
            found.append(i)
    if len(found) != 1:
        raise ValueError(f'video menu item not found once ({len(found)})')
    if route is None:
        p.items[found[0]:found[0] + 2] = [Op(OP['JUMP'], [VIDEO_MENU])]
    else:
        p.items[found[0]:found[0]] = _guard(p, route, VIDEO_MENU, 'JNZ')
    return p


def hide_record(p, route=None):
    """Return without the record applet/wait, unconditionally or only on `route`."""
    record = p.native('SaveBattleRecord')
    at = [i for i, x in enumerate(p.items) if not isinstance(x, Op) and x[1] == VIDEO_RECORD]
    if len(at) != 1:
        raise ValueError(f'{VIDEO_RECORD} not found once')
    i = at[0]
    body = p.items[i + 1:i + 10]
    want = [(OP['PROC'], [0]), (OP['PUSH_P_S'], [12]), (OP['SYSREQ_N'], [record, 4]), (OP['PUSH_P_C'], [1]),
            (OP['PUSH_P_C'], [4]), (OP['CALL'], ['L4']), (OP['ZERO_PRI'], [0]), (OP['RETN'], [0])]
    if [(x.op, x.args) if isinstance(x, Op) else x for x in body[:8]] != want:
        raise ValueError(f'{VIDEO_RECORD} is not the measured record routine')
    if route is None:
        p.items[i + 2:i + 7] = []
    else:
        p.items[i + 2:i + 2] = _guard(p, route, 'frontier_video_return', 'JNZ')
        at = p.items.index(body[6], i + 2)
        p.items.insert(at, ('label', 'frontier_video_return'))
    return p


def suppress(p, route=None):
    return hide_record(hide_video(p, route), route)
