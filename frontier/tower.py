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

Frontier Brains (frontier/brains.install): Anabel at battles 35/70 and every 35 after both symbols
(brains.APPEARANCES), symbols, no Maison boss on any Frontier route, and «Symbols» in the reception menu (value
brains.MENU_SYMBOLS) to consult Anabel's. Known deviations (design §1, §6): the Maison's texts («Mansión Batalla»); its party
rules (level capped to 50 instead of refused, its banned list); no Doubles. Open Level is offered by F9 (reports/modos-propios.md).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from pawn import OP, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import battle_video  # noqa: E402
import brains  # noqa: E402
import patch  # noqa: E402
import modes  # noqa: E402

FACILITY = 'tower'
ZONE = 329                       # frontier/REPARTO.md; verified statically by frontier/zone_check.py (§25)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
TOWER_BP = fd.FRONTIER_BP[FACILITY]
MENU_BATTLE = 0                  # «Combatir»: the Maison's own challenge
MODE_APP, MSG_MODE = 'L12a0', 6  # 0x16fc: CALL 0x12a0 (_CallTrialDownloadApp) after message 6
SUPER_FLAGS = (385, 386, 387, 388, 389)   # its last five arguments, FlagGet of each (0x1680-0x16e0)
RECEPTION_MENU = [53, 54, 74, 55]


def reception_routine(p, facility=FACILITY):
    """<facility>_reception() -> 1 = back to the reception menu, 0 = challenge played. Any facility run as the Tower
    in a 517 clone (route patch.ROUTE[facility], its streak and patch.ACTIVE_WORK); labels prefixed by its name."""
    route = patch.ROUTE[facility]
    streak, active, t = patch.STREAK_ROUTES[route][1], patch.ACTIVE_WORK[facility], facility
    r = factory.Routine(p, f'{t}_reception', [f'flag{f}' for f in SUPER_FLAGS] + ['x']
                        + (['level'] if facility in MODE_FACILITIES else []))
    factory.busy_check(r, facility, f'{t}_refused')
    if facility in MODE_FACILITIES:
        # Paused challenges choose resume/abandon before any new level selection.
        r.sysreq('WorkGet', active)
        r.op('JZER', f'{t}_choose_level')
        config_check(r, route, f'{t}_refused', f'{t}_pause_menu')
        r.p.label(f'{t}_pause_menu')
        level_menu(r, LINE_PAUSED, ((LINE_RESUME, 0), (LINE_ABANDON, 1), (55, 2)))
        r.op('JZER', f'{t}_selector')
        r.op('EQ_P_C_PRI', 1)
        r.op('JZER', f'{t}_refused')
        r.p.label(f'{t}_abandon')
        r.sysreq('WorkGet', modes.CONFIG[route])
        r.op('SHR_P_C_PRI', 8)
        r.op('JZER', f'{t}_abandon_50')
        r.sysreq('WorkSet', modes.bank(route, 1)[0], 0)
        r.op('JUMP', f'{t}_abandoned')
        r.p.label(f'{t}_abandon_50')
        r.sysreq('WorkSet', streak, 0)
        r.p.label(f'{t}_abandoned')
        r.sysreq('WorkSet', active, 0)
        r.op('JUMP', f'{t}_refused')
        r.p.label(f'{t}_choose_level')
        level_menu(r, LINE_LEVEL, ((LINE_50, 0), (LINE_OPEN, 1), (55, 2)))
        r.store('level')
        r.op('JZER', f'{t}_selector')
        r.op('EQ_P_C_PRI', 1)
        r.op('JZER', f'{t}_refused')
        r.p.label(f'{t}_selector')
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
    r.op('JZER', f'{t}_refused')               # mode screen cancelled
    r.sysreq('WorkGet', factory.WORK_SELECT_TYPE)
    r.op('JNZ', f'{t}_refused')                # v1: Singles only (the streak route covers Singles)
    r.sysreq('WorkGet', factory.WORK_SELECT_X)
    r.store('x')
    r.sysreq('SetRank', 0)                      # the streak route covers rank Normal only
    r.sysreq('WorkSet', patch.WORK_ROUTE, route)
    r.sysreq('WorkGet', active)
    r.op('JNZ', f'{t}_resume')                 # paused challenge: keep the streak, as Emerald
    r.p.label(f'{t}_new')
    if facility in MODE_FACILITIES:
        r.load('level')
        r.op('JZER', f'{t}_reset_50')
        r.sysreq('WorkSet', modes.CONFIG[route], modes.pack_config(route, 1, 60))
        r.sysreq('WorkSet', modes.bank(route, 1)[0], 0)
        r.op('JUMP', f'{t}_reset_done')
        r.p.label(f'{t}_reset_50')
        r.sysreq('WorkSet', modes.CONFIG[route], 0)
    r.sysreq('WorkSet', streak, 0)              # a new challenge starts at battle 1
    if facility in MODE_FACILITIES:
        r.p.label(f'{t}_reset_done')
        r.sysreq('WorkSet', active, NEW_ACTIVE)  # F9: «new, mode not registered yet» until registration()
        r.op('JUMP', f'{t}_challenge')
    r.p.label(f'{t}_resume')
    r.p.label(f'{t}_start')
    r.sysreq('WorkSet', active, 1)
    r.p.label(f'{t}_challenge')
    r.call(factory.CHALLENGE, 0, 0, 'x')
    r.op('EQ_P_C_PRI', 1)
    r.op('JNZ', f'{t}_declined')
    r.sysreq('GetMyWinCount', 0, 0)             # the facility streak (route still set)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', f'{t}_kept')                # 0 < streak: paused
    r.sysreq('WorkSet', active, 0)
    if facility in MODE_FACILITIES:
        r.op('JUMP', f'{t}_closed')
    r.p.label(f'{t}_kept')
    if facility in MODE_FACILITIES:
        r.sysreq('WorkSet', active, 1)          # F9: never leave NEW_ACTIVE behind a played challenge
    r.p.label(f'{t}_closed')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(f'{t}_declined')                 # declined or no team chosen: a paused challenge stays paused
    r.sysreq('GetMyWinCount', 0, 0)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', f'{t}_declined_kept')
    r.sysreq('WorkSet', active, 0)
    r.p.label(f'{t}_declined_kept')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.p.label(f'{t}_refused')
    r.const(1)
    r.ret()


# F9 own-team Singles: a new challenge chooses 50/Open before the retail selector.
# A paused challenge offers resume/retire and retains its validated CONFIG.
MODE_FACILITIES = ('tower', 'palace', 'arena')
LINE_50, LINE_OPEN, LINE_LEVEL, LINE_RESUME, LINE_ABANDON, LINE_PAUSED = range(191, 197)
LEVEL_TEXT = {
    'es': ('Nivel 50', 'Nivel Libre',
           'Elige el nivel del desafío.\nDespués elige Individual. El rango será Normal.',
           'Reanudar', 'Abandonar', 'Hay un desafío en pausa.\nSe conservarán su modalidad y su nivel.'),
    'en': ('Level 50', 'Open Level',
           'Choose the challenge level.\nThen choose Single Battle. The rank will be Normal.',
           'Resume', 'Retire', 'A challenge is paused.\nIts format and level will be kept.'),
}


def level_menu(r, prompt, entries):
    r.call(f'L{factory.MSG:x}', prompt, 1, 0, 256, 0)
    r.call(f'L{factory.MSG_WAIT:x}')
    r.call(f'L{factory.MENU_INIT:x}', 180, 112, 0, 1, 0, 0)
    for line, value in entries:
        r.sysreq('ListMenuAdd', line, value, 0)
    r.call(f'L{factory.MENU_RUN:x}')
    r.store('x')
    r.call(f'L{factory.MSG_CLOSE:x}', 0)
    r.load('x')


NEW_ACTIVE = 2                   # ACTIVE of a new challenge between the reception and its registration (registration)
REGISTERED = 'L1a38'             # challenge 0x18f8: the party app accepted the selection, before the save (0x13d4)


def registration(p, facility):
    """F9 registration in the challenge routine of a MODE_FACILITIES zone script, right after the party app accepted
    (REGISTERED, before the save): SetRank(modes.REGISTER + M + 4*resume), M = CONFIG[route] >> 8, resume unless
    ACTIVE is NEW_ACTIVE; the DllField SetRank native hands it to mode_register (frontier/asm/modes_selection.s),
    which fixes a new challenge's CONFIG from the effective selection (party or Battle Box) and keeps a resumed one.
    Then ACTIVE = 1, so the save holds an ordinary challenge in progress."""
    at = factory._index(p, REGISTERED)
    if p.items[at + 1].op != OP['SYSREQ_N'] or p.items[at + 1].args[0] != p.native('FieldMenuChangePagePlayNavi'):
        raise ValueError('accepted-selection path not found at 0x1a38')
    p.items[at + 1:at + 1] = _ops(p, lambda b: registration_ops(b, facility))


def registration_ops(b, facility):
    """The ops of registration() into Program `b`."""
    route, active = patch.ROUTE[facility], patch.ACTIVE_WORK[facility]
    b.sysreq('WorkGet', active)
    b.emit('EQ_P_C_PRI', NEW_ACTIVE)            # 1 new, 0 resumed
    b.emit('SMUL_P_C', -4)
    b.emit('ADD_P_C', 4)                        # 4*resume
    b.emit('PUSH_PRI', 0)
    b.sysreq('WorkGet', modes.CONFIG[route])
    b.emit('SHR_P_C_PRI', 8)
    b.emit('CONST_P_ALT', 3)
    b.emit('AND', 0)                            # M
    b.emit('ADD_P_C', modes.REGISTER)
    b.emit('PALT', 0)
    b.emit('ADD', 0)
    b.emit('PUSH_PRI', 0)
    b.items.append(Op(OP['SYSREQ_N'], [b.native('SetRank'), 4]))
    b.sysreq('WorkSet', active, 1)


def config_check(r, route, invalid, valid):
    """Jump to `valid` when CONFIG[route] is 0, Level 50 Singles or Singles Open Level with L 60-100, else `invalid`."""
    work = modes.CONFIG[route]
    singles_50 = modes.pack_config(route, modes.SINGLE_50, 50)
    low, high = (modes.pack_config(route, modes.SINGLE_OPEN, level) for level in (60, 100))
    r.sysreq('WorkGet', work)
    r.op('JZER', valid)
    r.op('ADD_P_C', -singles_50)
    r.op('JZER', valid)
    r.sysreq('WorkGet', work)
    r.const_alt(low)
    r.op('JSLESS', invalid)
    r.const_alt(high)
    r.op('JSGRTR', invalid)
    r.op('JUMP', valid)


STAGES = {'pike': 14}           # streak steps per round when not data.STAGES_PER_ROUND (the Pike's rooms)


def battle_points(p, facility=FACILITY):
    """BP of data.FRONTIER_BP[facility] as Emerald, inserted in the Maison's BP routine 0x3de4 once its locals exist (-4 win count, -8 BP),
    while WORK_ROUTE = patch.ROUTE[facility] (factory.battle_points does the same for the Factory). A round is
    STAGES.get(facility, data.STAGES_PER_ROUND) streak steps."""
    route, table_bp, t = patch.ROUTE[facility], fd.FRONTIER_BP[facility], facility
    stages = STAGES.get(facility, fd.STAGES_PER_ROUND)
    start = factory._index(p, factory.BATTLE_POINTS)
    at = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
              and p.items[i].op == OP['STOR_P_S_PRI'] and p.items[i].args == [-4])
    if p.items[at + 1].op != OP['PUSH_P_C'] or p.items[at + 1].args != [0]:
        raise ValueError('BP routine locals not found at 0x3e04')
    table = p.data_block(f'{t}_bp', list(table_bp))
    b = Program(p.script)
    b.native_hashes = p.native_hashes
    b.sysreq('WorkGet', patch.WORK_ROUTE)
    b.emit('EQ_P_C_PRI', route)
    b.emit('JZER', f'{t}_bp_retail')
    b.sysreq('GetMyWinCount', 0, 0)
    b.emit('STOR_P_S_PRI', -4)
    b.emit('MOVE_ALT', 0)
    b.emit('CONST_P_PRI', stages)
    b.emit('SDIV_ALT', 0)                    # rounds won = streak / 7
    b.emit('STOR_P_S_PRI', -8)
    b.emit('SMUL_P_C', stages)
    b.emit('LOAD_P_S_ALT', -4)
    b.emit('SUB_ALT', 0)                     # streak - 7 * rounds
    b.emit('JNZ', f'{t}_bp_none')
    b.emit('LOAD_P_S_PRI', -8)
    b.emit('ADD_P_C', -1)
    b.emit('CONST_P_ALT', len(table_bp) - 1)
    b.emit('JSLEQ', f'{t}_bp_index')
    b.emit('CONST_P_PRI', len(table_bp) - 1)
    b.label(f'{t}_bp_index')
    b.emit('SMUL_P_C', 4)
    b.emit('ADD_P_C', table)
    b.emit('LOAD_I', 0)
    b.emit('STOR_P_S_PRI', -8)
    b.emit('JUMP', factory.BATTLE_POINTS_GIVE)
    b.label(f'{t}_bp_none')
    b.emit('STACK_P', 8)
    b.emit('ZERO_PRI', 0)
    b.emit('RETN', 0)
    b.label(f'{t}_bp_retail')
    p.items[at + 2:at + 2] = b.items


def _ops(p, build):
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    build(body)
    return body.items


def facility_program(retail, facility):
    """Zone 517's retail script with `facility` run as the Tower (module docstring)."""
    active = patch.ACTIVE_WORK[facility]
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
        b.call(f'{facility}_reception')
        b.emit('STOR_P_S_PRI', factory.RECEPTION_AGAIN)
        b.emit('JUMP', factory.RECEPTION_NEXT)
    p.items[at + 3:at + 3] = _ops(p, dispatch)

    at = factory._index(p, factory.CLEANUP)
    if p.items[at + 1].op != OP['PROC']:
        raise ValueError('0x1458 is not a routine start')
    p.items[at + 2:at + 2] = _ops(p, lambda b: b.sysreq('WorkSet', active, 0))
    at = factory._index(p, factory.LOST)  # before the loss is saved, so the save never holds a dead challenge
    if p.items[at + 1].op != OP['ZERO_P_S'] or p.items[at + 1].args != [-8]:
        raise ValueError('lost-battle path not found at 0x2210')
    p.items[at + 1:at + 1] = _ops(p, lambda b: b.sysreq('WorkSet', active, 0))
    battle_points(p, facility)
    if facility in MODE_FACILITIES:
        registration(p, facility)
    reception_routine(p, facility)
    brains.install(p)             # Frontier Brains (frontier/brains.py) and no Maison boss on the route
    return battle_video.suppress(p)


def tower_program(retail):
    """Zone 517's retail script with the Tower (module docstring) and «Symbols» in its reception menu (Anabel's
    symbol, brains.symbols_option; text 619 line factory.LINE_SYMBOLS, as the Factory)."""
    p = facility_program(retail, FACILITY)
    brains.symbols_option(p, FACILITY, factory.LINE_SYMBOLS)
    return p


def zone_script(retail):
    """Built zone script bytes of the Tower's interior."""
    return tower_program(retail).build_script(f'L{retail.main:x}').build()
