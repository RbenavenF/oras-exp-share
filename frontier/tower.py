#!/usr/bin/env python3
"""Battle Tower v1 (reports/diseno/torre.md): the zone script of its interior, a clone of the Battle Maison hall.

Singles, Level 50, rank Normal, with the player's own team (the Maison's party selection screen, 0x457c, untouched),
an own streak and record, BP per round as Emerald, pause and resume as the Maison. Built from the **retail** zone
517 script (no Factory option), with these changes (addresses of work/frontier/survey/zone517.lst,
reports/frontier.md §1):
- reception (0x14f4): patch.WORK_ROUTE = 0 right after BattleInstWorkCreate (a save made during a challenge can
  hold the route), as the Factory;
- menu result (0x1634): option 0 («Combatir») calls `tower_reception` instead of the Maison's inline flow; its
  result is the «back to the menu» local (-4), as the Factory's option;
- `tower_reception`: refuses (text 619 line factory.LINE_BUSY) while another facility has a challenge in progress
  (patch.ACTIVE_WORK, frontier/REPARTO.md); else the Maison's mode selection app as at 0x1640 (the party selection
  screen needs it), back to the menu unless Singles was accepted; then SetRank(0), WORK_ROUTE = ROUTE (the code.bin streak hooks then
  point the Maison's Singles Normal streak and record at the Tower's works, patch.STREAK_ROUTES), a new challenge
  (ACTIVE = 0) starts its streak at 0, ACTIVE = 1 for the challenge (so the save the challenge makes holds it), the
  Maison challenge routine 0x18f8(rank 0, Singles, work 0x800E), then ACTIVE stays 1 only if the streak is not 0 (paused) and
  WORK_ROUTE = 0;
- lost battle (0x2210, before the record is saved) and the «did not save» cleanup (0x1458): ACTIVE = 0;
- BP (0x3de4): with WORK_ROUTE = ROUTE, none for battles 1-6 of a round and data.FRONTIER_BP['tower'][round - 1]
  (last value repeated) after the 7th; the Maison's brackets otherwise.
The Factory's reception refuses as well while the Tower's ACTIVE is not 0 (factory.reception_routine).

Known deviations (design §1, §6): the Maison's texts («Mansión Batalla»); its party rules (level capped to 50
instead of refused, its banned list); the Maison's boss can appear on the Tower streak (measured below,
BOSS_STREAKS); no Anabel, Doubles or Open Level.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from pawn import OP, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import patch  # noqa: E402

FACILITY = 'tower'
ZONE = 329                       # frontier/REPARTO.md; verified statically by frontier/zone_check.py (§25)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
TOWER_BP = fd.FRONTIER_BP[FACILITY]
MENU_BATTLE = 0                  # «Combatir»: the Maison's own challenge
MODE_APP, MSG_MODE = 'L12a0', 6  # 0x16fc: CALL 0x12a0 (_CallTrialDownloadApp) after message 6
SUPER_FLAGS = (385, 386, 387, 388, 389)   # its last five arguments, FlagGet of each (0x1680-0x16e0)
RECEPTION_MENU = [53, 54, 74, 55]


def reception_routine(p):
    """tower_reception() -> 1 = back to the reception menu, 0 = challenge played."""
    r = factory.Routine(p, 'tower_reception', [f'flag{f}' for f in SUPER_FLAGS] + ['x'])
    factory.busy_check(r, FACILITY, 'tower_refused')
    # The Maison's own mode selection, as 0x1640-0x1704: message 6, then the app (0x12a0, _CallTrialDownloadApp).
    # The party selection screen needs it: without it every Pokémon is refused (seen in Azahar, §25).
    r.call(f'L{factory.MSG:x}', MSG_MODE, 1, 0, 256, 0)
    r.call(f'L{factory.MSG_WAIT:x}')
    r.call(f'L{factory.MSG_CLOSE:x}', 0)
    for f in SUPER_FLAGS:
        r.sysreq('FlagGet', f)
        r.store(f'flag{f}')
    r.call(MODE_APP, 0, factory.WORK_SELECT_RESULT, factory.WORK_SELECT_TYPE, factory.WORK_SELECT_X,
           *(f'flag{f}' for f in SUPER_FLAGS))
    r.sysreq('WorkGet', factory.WORK_SELECT_RESULT)
    r.op('JZER', 'tower_refused')               # mode screen cancelled
    r.sysreq('WorkGet', factory.WORK_SELECT_TYPE)
    r.op('JNZ', 'tower_refused')                # v1: Singles only (the streak route covers Singles)
    r.sysreq('WorkGet', factory.WORK_SELECT_X)
    r.store('x')
    r.sysreq('SetRank', 0)                      # the streak route covers rank Normal only
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
    r.sysreq('WorkGet', ACTIVE)
    r.op('JNZ', 'tower_resume')                 # paused challenge: keep the streak, as Emerald
    r.sysreq('WorkSet', STREAK, 0)              # a new challenge starts at battle 1
    r.p.label('tower_resume')
    r.sysreq('WorkSet', ACTIVE, 1)
    r.call(factory.CHALLENGE, 0, 0, 'x')
    r.op('EQ_P_C_PRI', 1)
    r.op('JNZ', 'tower_declined')
    r.sysreq('GetMyWinCount', 0, 0)             # the Tower streak (route still set)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', 'tower_kept')                # 0 < streak: paused
    r.sysreq('WorkSet', ACTIVE, 0)
    r.p.label('tower_kept')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label('tower_declined')                 # declined or no team chosen: a paused challenge stays paused
    r.sysreq('GetMyWinCount', 0, 0)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', 'tower_declined_kept')
    r.sysreq('WorkSet', ACTIVE, 0)
    r.p.label('tower_declined_kept')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.p.label('tower_refused')
    r.const(1)
    r.ret()


def battle_points(p):
    """Tower BP as Emerald, inserted in the Maison's BP routine 0x3de4 once its locals exist (-4 win count, -8 BP),
    while WORK_ROUTE = ROUTE (factory.battle_points does the same for the Factory)."""
    start = factory._index(p, factory.BATTLE_POINTS)
    at = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
              and p.items[i].op == OP['STOR_P_S_PRI'] and p.items[i].args == [-4])
    if p.items[at + 1].op != OP['PUSH_P_C'] or p.items[at + 1].args != [0]:
        raise ValueError('BP routine locals not found at 0x3e04')
    table = p.data_block('tower_bp', list(TOWER_BP))
    b = Program(p.script)
    b.native_hashes = p.native_hashes
    b.sysreq('WorkGet', patch.WORK_ROUTE)
    b.emit('EQ_P_C_PRI', ROUTE)
    b.emit('JZER', 'tower_bp_retail')
    b.sysreq('GetMyWinCount', 0, 0)
    b.emit('STOR_P_S_PRI', -4)
    b.emit('MOVE_ALT', 0)
    b.emit('CONST_P_PRI', fd.STAGES_PER_ROUND)
    b.emit('SDIV_ALT', 0)                    # rounds won = streak / 7
    b.emit('STOR_P_S_PRI', -8)
    b.emit('SMUL_P_C', fd.STAGES_PER_ROUND)
    b.emit('LOAD_P_S_ALT', -4)
    b.emit('SUB_ALT', 0)                     # streak - 7 * rounds
    b.emit('JNZ', 'tower_bp_none')
    b.emit('LOAD_P_S_PRI', -8)
    b.emit('ADD_P_C', -1)
    b.emit('CONST_P_ALT', len(TOWER_BP) - 1)
    b.emit('JSLEQ', 'tower_bp_index')
    b.emit('CONST_P_PRI', len(TOWER_BP) - 1)
    b.label('tower_bp_index')
    b.emit('SMUL_P_C', 4)
    b.emit('ADD_P_C', table)
    b.emit('LOAD_I', 0)
    b.emit('STOR_P_S_PRI', -8)
    b.emit('JUMP', factory.BATTLE_POINTS_GIVE)
    b.label('tower_bp_none')
    b.emit('STACK_P', 8)
    b.emit('ZERO_PRI', 0)
    b.emit('RETN', 0)
    b.label('tower_bp_retail')
    p.items[at + 2:at + 2] = b.items


def _ops(p, build):
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    build(body)
    return body.items


def tower_program(retail):
    """Zone 517's retail script with the Tower (module docstring)."""
    p = Program.from_script(retail)
    start = factory._index(p, 'L14f4')
    create = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
                  and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == p.native('BattleInstWorkCreate'))
    p.items[create + 1:create + 1] = _ops(p, lambda b: b.sysreq('WorkSet', patch.WORK_ROUTE, 0))
    native = p.native('ListMenuAdd')
    adds = [i for i in range(start, factory._index(p, factory.RECEPTION_RESULT)) if isinstance(p.items[i], Op)
            and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == native]
    if len(adds) != len(RECEPTION_MENU):
        raise ValueError('reception menu not found (is this the retail script?)')

    at = factory._index(p, factory.RECEPTION_RESULT)
    head = p.items[at + 1:at + 3]
    if [o.op for o in head] != [OP['LOAD_P_S_PRI'], OP['JNZ']] or head[0].args != [-12] or head[1].args != ['L17b0']:
        raise ValueError('reception result check not found at 0x1634')

    def dispatch(b):                 # value 0 falls through here (others jump to 0x17b0)
        b.call('tower_reception')
        b.emit('STOR_P_S_PRI', factory.RECEPTION_AGAIN)
        b.emit('JUMP', factory.RECEPTION_NEXT)
    p.items[at + 3:at + 3] = _ops(p, dispatch)

    at = factory._index(p, factory.CLEANUP)
    if p.items[at + 1].op != OP['PROC']:
        raise ValueError('0x1458 is not a routine start')
    p.items[at + 2:at + 2] = _ops(p, lambda b: b.sysreq('WorkSet', ACTIVE, 0))
    at = factory._index(p, factory.LOST)  # before the loss is saved, so the save never holds a dead challenge
    if p.items[at + 1].op != OP['ZERO_P_S'] or p.items[at + 1].args != [-8]:
        raise ValueError('lost-battle path not found at 0x2210')
    p.items[at + 1:at + 1] = _ops(p, lambda b: b.sysreq('WorkSet', ACTIVE, 0))
    battle_points(p)
    reception_routine(p)
    return p


def zone_script(retail):
    """Built zone script bytes of the Tower's interior."""
    return tower_program(retail).build_script(f'L{retail.main:x}').build()
