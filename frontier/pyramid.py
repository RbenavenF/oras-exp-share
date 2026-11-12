#!/usr/bin/env python3
"""Battle Pyramid v2A (reports/diseno/piramide.md): seven fixed cave floors of trainers;
no darkness, wild Pokémon, items or persistent HP. Brandon (F8-CEREBRO-PIRAMIDE) at the summit.

Interiors (frontier/REPARTO.md), all with the Battle Maison native groups:
- LOBBY (140): the plaza's Pyramid door (32,57) leads here and its exit (warp 0) back to (32,58). The right-hand
  receptionist (event 2) runs `pyramid_reception`; every other event of the hall does nothing (0x1294).
- FLOORS (141, 142), cloned from Desert Ruins (77): floor n is FLOORS[(n - 1) % 2], so every floor change is a change of zone (re-entering the
  zone one is in was not needed). Their NPCs are replaced: TRAINERS trainers (events 2..) and an attendant (the
  «stairs», event STAIRS_EVENT). All three donor exits lead to the lobby: the challenge stays in progress and the
  receptionist offers to resume it.

Experiment 0 (reports/frontier.md §30, Azahar): the Maison's facility work does not survive _MapChangeCore. So a
battle on a floor creates its own work (BattleInstWorkCreate, SetRank(0), SetTrainer(0), StartBattle(0, 1), IsWin,
BattleInstWorkDelete, as the Maison's loop 0x1e1c without its presentation) and the code.bin hooks of
frontier/asm/pyramid.s carry the party chosen in the lobby in saved works (patch.PYRAMID_SEL): `pyramid_save` when
the lobby's work is deleted, `pyramid_party` in every floor battle. They act only with WORK_ROUTE = ROUTE.

Lobby, `pyramid_reception`: the mutual exclusion (factory.busy_check); with a challenge in progress (ACTIVE = its
floor), resume (back to that floor) or retire (streak 0); else the rules, «take part?», a work, the Maison's mode
screen (Singles only, as the Tower), SetRank(0), PYRAMID_COUNT = 0, WORK_ROUTE = ROUTE, the Maison's party screen
(0x457c), BattleHouse_End and BattleInstWorkDelete (the hook saves the three and PYRAMID_COUNT = 3; a Battle Box
team is refused), ACTIVE = 1 and BEATEN = 0, the save prompt (0x13d4; not saved: nothing kept) and floor 1.

Floors: a trainer already beaten (bit k of BEATEN) only says so; else the battle above. A win sets its bit; a loss
ends the challenge (ACTIVE = 0, WORK_ROUTE = 0, streak 0) and goes back to the lobby. The attendant says the floor;
with all its trainers beaten the streak (floors, as Emerald's pyramidWinStreaks) and its record go up and the player
climbs; after floor FLOORS_PER_CHALLENGE, data.FRONTIER_BP['pyramid'][challenge - 1] BP (last value repeated; the
streak goes on, as Emerald) and back to the lobby. Every battle is the Maison's: the party copied at level 50,
healed, no bag, no experience; the rival from the Maison's trainers by the Pyramid's streak (route 7).

Brandon (reports/diseno/cerebros.md §5): when floor 7's attendant counts the floor, brains_check (unit = the
streak just counted: floors 21 / 70 / 105...) decides; a Brain due is kept in saved WORK_SUMMIT before anything else,
so the attendant of floor 7 goes straight to Brandon on the next talk (after a reload too) without counting the
floor again; the trainers of that floor stay beaten. The battle is the floors' (own work, SetTrainer(0)) with
WORK_BRAIN = ROUTE + 8 * variant, so brains_cro.s supplies Brandon and his exact team; brains_intro/won/lost say his
lines; a win gives the symbol and BRAIN_BONUS BP once (brains_won) and then the challenge's BP and the way back; a
loss ends the challenge (streak 0, record and symbols kept). The lobby's other receptionist (SYMBOLS_EVENT) says the
Pyramid's symbols.

Texts: text 637 lines from LINE_BASE (after the Pike's), said by shared script 5 case GLOBAL_SAY (`pyramid_say`;
the zone passes the line in WORK_MSG, bit 8 = yes/no question answered in GlobalGetChildParam(0), and a number in
WORK_ARG). Known deviations (design §1, §6): the trainers remain visible after
being beaten (their saved bit prevents another battle), a battle heals, held items are allowed, the Maison's banned species; reordering the party between
floors changes who fights (the three are party slots).
"""
import sys
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from formats import zo_files
from pawn import OP, Op, Program, Script  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import battle_video  # noqa: E402
import brains  # noqa: E402
import patch  # noqa: E402
import pike  # noqa: E402
import tower  # noqa: E402

FACILITY = 'pyramid'
LOBBY = 140                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§30)
FLOORS = (141, 142)
FLOOR_DONOR = 77                # Desert Ruins, first chamber; reports/frontier.md §34
ZO_LIMIT = 17248                # measured safe container size, reports/frontier.md §11
FLOOR_WARPS = 3                # all donor exits are redirected to the lobby
ZONES = (LOBBY, *FLOORS)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))   # ACTIVE = current floor, 0 = none
WORK_BEATEN = 16686               # bit k: trainer k of the current floor beaten (free per frontier/ids.py; REPARTO.md)
WORK_MSG = 16687                  # line for pyramid_say (+ ASK for a yes/no question)
WORK_ARG = 16689                  # the number pyramid_say shows
PYRAMID_BP = fd.FRONTIER_BP[FACILITY]
FLOORS_PER_CHALLENGE = fd.STAGES_PER_ROUND   # FRONTIER_STAGES_PER_CHALLENGE
TRAINERS = 3
STAIRS_EVENT = 2 + TRAINERS
RECEPTION_EVENT = 2
SYMBOLS_EVENT = 3                 # the lobby's other receptionist (zone 517 NPC 2, model 62): «Symbols»
WORK_SUMMIT = brains.WORK_PYRAMID # Brandon pending at the summit: its variant (1 silver, 2 gold), 0 = none
GLOBAL_SAY = 9777
ASK = 0x100
YES, NO = 0, 1
EMPTY = 'L1294'                   # zone 517: PROC; ZERO_PRI; RETN
TALK_START, TALK_END, WAIT = 'L798', 'La9c', 'L4'
PARTY_SELECT = 'L457c'            # BattleHouse_CallPartySelectApp(x, 0x800C) -> 0 if cancelled
SAVE = 'L13d4'                    # GlobalCall 2003 (save prompt) -> 0 if saved (zone 517 0x1a60-0x1a70)
ADD_BP = 'L30'                    # (bp): PlayerGetBP + bp -> PlayerSetBP, RecordAdd 34
AFTER_BATTLE = [('L4', 1), ('L74', 2, 4), ('L6c0',), ('Lf34', 10)]   # as zone 517 after StartBattle (0x1ef0-0x1f28)
# _MapChangeCore destinations: zone, x, height, y, facing (0 = up; shared 79 @724 adds 0, 0, 1, 0).
FLOOR_ARRIVAL = (12, 0, 16, 0)    # inside Desert Ruins, above the south exit (12,18)
LOBBY_RETURN = (LOBBY, 23, 0, 25, 0)   # in front of the receptionist (NPC 1 of zone 517, tile 23,24)
# Floor NPCs (plan lines): (model, x, y, facing); models of zone 517's own registry (its NPCs 2, 3, 4, 9).
TRAINER_NPCS = [(263, 8, 10, 1), (298, 12, 10, 1), (277, 16, 10, 1)]
STAIRS_NPC = (62, 12, 6, 1)

TEXTS = {
    'es': {'intro': 'Te damos la bienvenida a la Pirámide Batalla.\nSube sus 7 pisos venciendo a todos\nlos Entrenadores de cada uno.',
           'enter': '¿Quieres participar en el desafío?',
           'box': 'Elige a tus Pokémon de tu equipo,\nno de la Caja de Combate.',
           'resume': 'Tu desafío sigue en el piso [VAR 0203 1,0].\n¿Quieres continuar?',
           'retire': '¿Quieres abandonar el desafío?',
           'retired': 'Has abandonado el desafío.',
           'floor': 'Piso [VAR 0203 1,0] de 7.',
           'not_yet': 'Vence a los 3 Entrenadores de este\npiso para poder subir.',
           'up': '¡Piso superado!\nSube al siguiente.',
           'beaten': 'Ya hemos combatido.\n¡Sigue adelante!',
           'trainer': '¡Te reto a un combate!',
           'lost': 'Has perdido...\nTu desafío termina aquí.',
           'won': '¡Has conquistado la Pirámide Batalla!\nRecibes [VAR 0203 1,0] PB.',
           'yes': 'Sí', 'no': 'No'},
    'en': {'intro': 'Welcome to the Battle Pyramid.\nClimb its 7 floors by defeating\nevery Trainer on each one.',
           'enter': 'Would you like to take the challenge?',
           'box': 'Please choose Pokémon from your\nparty, not from the Battle Box.',
           'resume': 'Your challenge is on floor [VAR 0203 1,0].\nWould you like to continue?',
           'retire': 'Would you like to give up\nthe challenge?',
           'retired': 'You gave up the challenge.',
           'floor': 'Floor [VAR 0203 1,0] of 7.',
           'not_yet': 'Defeat the 3 Trainers on this floor\nto go up.',
           'up': 'Floor cleared!\nGo up to the next one.',
           'beaten': 'We already battled.\nKeep going!',
           'trainer': 'I challenge you to a battle!',
           'lost': 'You lost...\nYour challenge ends here.',
           'won': 'You conquered the Battle Pyramid!\nYou received [VAR 0203 1,0] BP.',
           'yes': 'Yes', 'no': 'No'},
}
KEYS = ['intro', 'enter', 'box', 'resume', 'retire', 'retired', 'floor', 'not_yet', 'up', 'beaten', 'trainer', 'lost',
        'won', 'yes', 'no']
MSG = {key: k for k, key in enumerate(KEYS)}
LINE_BASE = pike.LINE_END
LINE_END = LINE_BASE + len(KEYS)
assert FLOORS_PER_CHALLENGE == 7 and len(TRAINER_NPCS) == TRAINERS


def lines(lang):
    """Text 637 lines of the Pyramid, from LINE_BASE, in one game language."""
    t = TEXTS[factory.LANG[lang]]
    return [t[key] for key in KEYS]


# --- shared script 5 -------------------------------------------------------------------------------------------

def say_routine(p, helpers):
    """pyramid_say(): line LINE_BASE + (WORK_MSG & 0xff) with WORK_ARG as number [VAR 0203 1,0]; with ASK set, a
    yes/no menu: GlobalSetParentParam(0, YES or NO; B = NO)."""
    r = factory.Routine(p, 'pyramid_say', ['msg', 'line', 'value', 'answer'])
    r.sysreq('WorkGet', WORK_MSG)
    r.store('msg')
    r.field(0, 8)
    r.add(LINE_BASE)
    r.store('line')
    r.sysreq('WorkGet', WORK_ARG)
    r.store('value')
    r.sysreq('WordSetNumber', 1, 'value', 4, 0)   # as pike_room
    r.set('answer', NO)
    r.call(helpers['msg'], 'line', 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.load('msg')
    r.const_alt(ASK)
    r.op('AND', 0)
    r.op('JZER', 'pyramid_say_close')
    r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
    r.sysreq('ListMenuAdd', LINE_BASE + MSG['yes'], YES, 0)
    r.sysreq('ListMenuAdd', LINE_BASE + MSG['no'], NO, 0)
    r.call(helpers['menu_run'])
    r.op('EQ_P_C_PRI', YES)
    r.op('JZER', 'pyramid_say_close')            # No or B
    r.set('answer', YES)
    r.p.label('pyramid_say_close')
    r.call(helpers['msg_close'], 0)
    r.sysreq('GlobalSetParentParam', 0, 'answer')
    r.op('ZERO_PRI', 0)
    r.ret()


def shared_cases():
    """(case value, routine, builder(p, helpers)) for factory.shared_program."""
    return [(GLOBAL_SAY, 'pyramid_say', say_routine)]


# --- zone scripts -------------------------------------------------------------------------------------------------

def _say(r, key, arg=None):
    if arg is not None:
        r.sysreq('WorkSet', WORK_ARG, arg)
    r.sysreq('WorkSet', WORK_MSG, MSG[key])
    r.sysreq('GlobalCall', GLOBAL_SAY)


def _ask(r, key, arg=None):
    """PRI = YES or NO."""
    if arg is not None:
        r.sysreq('WorkSet', WORK_ARG, arg)
    r.sysreq('WorkSet', WORK_MSG, MSG[key] | ASK)
    r.sysreq('GlobalCall', GLOBAL_SAY)
    r.sysreq('GlobalGetChildParam', 0)


def _change_map(r, zone, x, height, y, face):
    # Shared script 79 @724 (the ferry, reports/frontier.md §16): zone, x, height, y, facing, 0, 0, 1, 0.
    r.sysreq('_MapChangeCore', zone, x, height, y, face, 0, 0, 1, 0)


def dispatch(p, events):
    """Redirect the cases of the clone's main dispatcher (zone 517's CASETBL at 0x1220): event -> routine label;
    every other event to EMPTY. Keeps the donor's main and publics."""
    at = factory._index(p, f'L{p.script.main:x}')
    table = next(o for o in p.items[at:] if isinstance(o, Op) and o.op == OP['CASETBL'])
    cases = dict(zip(table.args[2::2], table.args[3::2]))
    if not set(events) <= set(cases):
        raise ValueError(f'zone 517 has no events {sorted(set(events) - set(cases))}')
    for event, stub in cases.items():
        start = factory._index(p, stub)
        call = next(o for o in p.items[start:] if isinstance(o, Op) and o.op == OP['CALL'])
        call.args = [events.get(event, EMPTY)]


def goto_floor_routine(p):
    """pyramid_goto_floor(): _MapChangeCore to floor ACTIVE (FLOORS alternate, odd floors in FLOORS[0])."""
    r = factory.Routine(p, 'pyramid_goto_floor', [])
    r.sysreq('WorkGet', ACTIVE)
    r.const_alt(1)
    r.op('AND', 0)
    r.op('JZER', 'pyramid_goto_even')
    _change_map(r, FLOORS[0], *FLOOR_ARRIVAL)
    r.op('JUMP', 'pyramid_goto_end')
    r.p.label('pyramid_goto_even')
    _change_map(r, FLOORS[1], *FLOOR_ARRIVAL)
    r.p.label('pyramid_goto_end')
    r.op('ZERO_PRI', 0)
    r.ret()


def end_challenge(r):
    """The challenge is over (lost or retired): ACTIVE = 0, WORK_ROUTE = 0, streak 0, BEATEN = 0, no Brandon
    pending (the symbols and the record stay)."""
    r.sysreq('WorkSet', ACTIVE, 0)
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.sysreq('WorkSet', STREAK, 0)
    r.sysreq('WorkSet', WORK_BEATEN, 0)
    r.sysreq('WorkSet', WORK_SUMMIT, 0)


def reception_routine(p):
    """pyramid_reception(): the lobby's receptionist (module docstring)."""
    r = factory.Routine(p, 'pyramid_reception', [f'flag{f}' for f in tower.SUPER_FLAGS] + ['x', 'floor'])
    t, end = 'pyramid_reception', 'pyramid_reception_end'
    r.call(TALK_START, -1)
    factory.busy_check(r, FACILITY, end)
    r.sysreq('WorkGet', ACTIVE)
    r.store('floor')
    r.op('JNZ', f'{t}_resume')

    _say(r, 'intro')
    _ask(r, 'enter')
    r.op('EQ_P_C_PRI', YES)
    r.op('JZER', end)
    r.sysreq('BattleInstWorkCreate')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    # The Maison's mode selection, as the Tower (tower.reception_routine): the party screen needs it.
    r.call(f'L{factory.MSG:x}', tower.MSG_MODE, 1, 0, 256, 0)
    r.call(f'L{factory.MSG_WAIT:x}')
    r.call(f'L{factory.MSG_CLOSE:x}', 0)
    for f in tower.SUPER_FLAGS:
        r.sysreq('FlagGet', f)
        r.store(f'flag{f}')
    r.call(tower.MODE_APP, 0, factory.WORK_SELECT_RESULT, factory.WORK_SELECT_TYPE, factory.WORK_SELECT_X,
           *(f'flag{f}' for f in tower.SUPER_FLAGS))
    r.sysreq('WorkGet', factory.WORK_SELECT_RESULT)
    r.op('JZER', f'{t}_cancel')                 # mode screen cancelled
    r.sysreq('WorkGet', factory.WORK_SELECT_TYPE)
    r.op('JNZ', f'{t}_cancel')                  # v1: Singles only
    r.sysreq('SetRank', 0)
    r.sysreq('WorkGet', factory.WORK_SELECT_X)
    r.store('x')
    r.sysreq('WorkSet', patch.PYRAMID_COUNT, 0)
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)   # pyramid_save acts on the delete below
    r.call(PARTY_SELECT, 'x')
    r.op('JZER', f'{t}_cancel')
    r.sysreq('BattleHouse_End')
    r.sysreq('BattleInstWorkDelete')            # pyramid_save: the three in PYRAMID_SEL, PYRAMID_COUNT = 3
    r.sysreq('WorkGet', patch.PYRAMID_COUNT)
    r.op('EQ_P_C_PRI', len(patch.PYRAMID_SEL))
    r.op('JNZ', f'{t}_chosen')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    _say(r, 'box')
    r.op('JUMP', end)
    r.p.label(f'{t}_chosen')
    r.sysreq('WorkSet', ACTIVE, 1)
    r.sysreq('WorkSet', WORK_BEATEN, 0)
    r.call(SAVE)                                # the save holds the challenge on floor 1
    r.op('JZER', f'{t}_go')                     # 0 = saved
    r.sysreq('WorkSet', ACTIVE, 0)              # not saved: nothing kept
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.op('JUMP', end)

    r.p.label(f'{t}_resume')
    _ask(r, 'resume', 'floor')
    r.op('EQ_P_C_PRI', YES)
    r.op('JZER', f'{t}_retire')
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
    r.p.label(f'{t}_go')
    r.call(TALK_END)
    r.call('pyramid_goto_floor')
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(f'{t}_retire')
    _ask(r, 'retire')
    r.op('EQ_P_C_PRI', YES)
    r.op('JZER', end)
    end_challenge(r)
    _say(r, 'retired')
    r.op('JUMP', end)

    r.p.label(f'{t}_cancel')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.sysreq('BattleHouse_End')
    r.sysreq('BattleInstWorkDelete')
    r.p.label(end)
    r.call(TALK_END)
    r.op('ZERO_PRI', 0)
    r.ret()


def battle_routine(p):
    """pyramid_battle(brain) -> IsWin: a floor battle (module docstring) with WORK_BRAIN = brain (0: an ordinary
    trainer; ROUTE + 8 * variant: Brandon, from brains_cro.s)."""
    r = factory.Routine(p, 'pyramid_battle', ['brain', 'win'])
    r.op('LOAD_P_S_PRI', 12)
    r.store('brain')
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)   # a save made on a floor holds it too; set again
    r.sysreq('WorkSet', brains.WORK_BRAIN, 'brain')
    r.sysreq('BattleInstWorkCreate')
    r.sysreq('SetRank', 0)
    r.sysreq('SetTrainer', 0)
    r.call(WAIT, 1)
    r.sysreq('StartBattle', 0, 1)
    for label, *args in AFTER_BATTLE:
        r.call(label, *args)
    r.sysreq('IsWin')
    r.store('win')
    r.sysreq('BattleInstWorkDelete')
    r.load('win')
    r.ret()


def trainer_routine(p):
    """pyramid_trainer(bit): the floor's trainer of BEATEN bit `bit` (module docstring); pyramid_trainer<k>() are
    the events' entries."""
    t = 'pyramid_trainer'
    r = factory.Routine(p, t, ['bit', 'beaten'])
    end = f'{t}_end'
    r.op('LOAD_P_S_PRI', 12)
    r.store('bit')
    r.call(TALK_START, -1)
    r.sysreq('WorkGet', ACTIVE)
    r.op('JZER', end)                            # no challenge (should not happen: the floors are reached by it)
    r.sysreq('WorkGet', WORK_BEATEN)
    r.store('beaten')
    r.load_alt('bit')
    r.op('AND', 0)
    r.op('JZER', f'{t}_fight')
    _say(r, 'beaten')
    r.op('JUMP', end)
    r.p.label(f'{t}_fight')
    _say(r, 'trainer')
    r.call('pyramid_battle', 0)
    r.op('JZER', f'{t}_lost')
    r.load('beaten')
    r.load_alt('bit')
    r.op('OR', 0)
    r.store('beaten')
    r.sysreq('WorkSet', WORK_BEATEN, 'beaten')
    r.p.label(end)
    r.call(TALK_END)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(f'{t}_lost')
    lost_and_leave(r)
    for k in range(TRAINERS):
        e = factory.Routine(p, f'pyramid_trainer{k}', [])
        e.call(t, 1 << k)
        e.op('ZERO_PRI', 0)
        e.ret()


def lost_and_leave(r):
    """A lost battle: the line, end_challenge, back to the lobby."""
    _say(r, 'lost')
    end_challenge(r)
    r.call(TALK_END)
    _change_map(r, *LOBBY_RETURN)
    r.op('ZERO_PRI', 0)
    r.ret()


def stairs_routine(p):
    """pyramid_stairs(): the floor's attendant (module docstring)."""
    t, end = 'pyramid_stairs', 'pyramid_stairs_end'
    r = factory.Routine(p, t, ['floor', 'streak', 'bp', 'variant'])
    r.call(TALK_START, -1)
    r.sysreq('WorkGet', ACTIVE)
    r.store('floor')
    r.op('JZER', end)
    r.sysreq('WorkGet', WORK_SUMMIT)
    r.store('variant')
    r.op('JNZ', f'{t}_summit')                   # floor already counted: Brandon is waiting
    _say(r, 'floor', 'floor')
    r.sysreq('WorkGet', WORK_BEATEN)
    r.op('EQ_P_C_PRI', (1 << TRAINERS) - 1)
    r.op('JNZ', f'{t}_cleared')
    _say(r, 'not_yet')
    r.op('JUMP', end)
    r.p.label(f'{t}_cleared')
    r.sysreq('WorkGet', STREAK)                   # one more floor on the streak and its record
    r.add(1)
    r.store('streak')
    r.sysreq('WorkSet', STREAK, 'streak')
    r.sysreq('WorkGet', RECORD)
    r.load_alt('streak')
    r.op('JSGEQ', f'{t}_record')                 # record >= streak
    r.sysreq('WorkSet', RECORD, 'streak')
    r.p.label(f'{t}_record')
    r.load('floor')
    r.const_alt(FLOORS_PER_CHALLENGE)
    r.op('JSGEQ', f'{t}_top')                    # floor >= 7
    r.sysreq('WorkSet', WORK_BEATEN, 0)
    r.load('floor')
    r.add(1)
    r.store('floor')
    r.sysreq('WorkSet', ACTIVE, 'floor')
    _say(r, 'up')
    r.call(TALK_END)
    r.call('pyramid_goto_floor')
    r.op('ZERO_PRI', 0)
    r.ret()

    r.p.label(f'{t}_top')                        # the floor is counted: Brandon at the summit when due
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
    r.call('brains_check')                       # unit = the streak just counted
    r.sysreq('WorkGet', brains.WORK_BRAIN)
    r.op('SHR_P_C_PRI', 3)
    r.store('variant')
    r.op('JZER', f'{t}_close')
    r.sysreq('WorkSet', WORK_SUMMIT, 'variant')  # pending, saved with the streak: no skipping, no second count

    r.p.label(f'{t}_summit')
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
    r.load('variant')
    r.op('SMUL_P_C', 8)
    r.add(ROUTE)
    r.store('bp')
    r.sysreq('WorkSet', brains.WORK_BRAIN, 'bp')
    r.call('brains_intro')
    r.call('pyramid_battle', 'bp')               # brains_cro.s: Brandon's trainer and exact team
    r.op('JZER', f'{t}_brain_lost')
    r.call('brains_won')                         # symbol, BRAIN_BONUS BP, line; WORK_BRAIN = 0
    r.sysreq('WorkSet', WORK_SUMMIT, 0)
    r.sysreq('WorkGet', STREAK)
    r.store('streak')

    r.p.label(f'{t}_close')                      # BP of challenge streak / 7 (1-based), last value repeated
    r.sysreq('WorkSet', WORK_BEATEN, 0)
    table = p.data_block('pyramid_bp', list(PYRAMID_BP))
    r.load('streak')
    r.op('MOVE_ALT', 0)
    r.const(FLOORS_PER_CHALLENGE)
    r.op('SDIV_ALT', 0)
    r.add(-1)
    r.const_alt(len(PYRAMID_BP) - 1)
    r.op('JSLEQ', f'{t}_index')
    r.const(len(PYRAMID_BP) - 1)
    r.p.label(f'{t}_index')
    r.cell(table)
    r.store('bp')
    r.call(ADD_BP, 'bp')
    _say(r, 'won', 'bp')
    r.sysreq('WorkSet', ACTIVE, 0)                # the streak goes on to the next challenge
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.call(TALK_END)
    _change_map(r, *LOBBY_RETURN)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(f'{t}_brain_lost')
    r.call('brains_lost')                        # Brandon's line; WORK_BRAIN = 0
    lost_and_leave(r)
    r.p.label(end)
    r.call(TALK_END)
    r.op('ZERO_PRI', 0)
    r.ret()


def symbols_talk_routine(p):
    """pyramid_symbols(): the lobby's other receptionist says the Pyramid's symbols (any time, also with another
    facility's challenge paused)."""
    r = factory.Routine(p, 'pyramid_symbols', [])
    r.call(TALK_START, -1)
    r.call('brains_symbols')
    r.call(TALK_END)
    r.op('ZERO_PRI', 0)
    r.ret()


def lobby_program(retail):
    """Zone 517's retail script as the Pyramid's lobby."""
    p = Program.from_script(retail)
    dispatch(p, {RECEPTION_EVENT: 'pyramid_reception', SYMBOLS_EVENT: 'pyramid_symbols'})
    reception_routine(p)
    symbols_talk_routine(p)
    brains.symbols_routine(p, FACILITY)
    goto_floor_routine(p)
    return battle_video.suppress(p)


def floor_program(retail):
    """Zone 517's retail script as a Pyramid floor."""
    p = Program.from_script(retail)
    dispatch(p, {**{2 + k: f'pyramid_trainer{k}' for k in range(TRAINERS)}, STAIRS_EVENT: 'pyramid_stairs'})
    trainer_routine(p)
    battle_routine(p)
    stairs_routine(p)
    goto_floor_routine(p)
    brains.check_routine(p, STREAK, 0)
    brains.intro_routine(p)
    brains.won_routine(p)
    brains.lost_routine(p)
    return battle_video.suppress(p)


def zone_scripts(retail):
    """{zone: built zone script bytes} of the lobby and the floors."""
    main = f'L{retail.main:x}'
    floor = floor_program(retail).build_script(main).build()
    return {LOBBY: lobby_program(retail).build_script(main).build(), **{z: floor for z in FLOORS}}


def plan_lines():
    """CTRMap-F5 plan lines (island_build.plan): each floor's NPCs and its exit to the lobby."""
    out = []
    for zone in FLOORS:
        out += [f'zone.{zone}.clearNpcs=1', f'zone.{zone}.clearTriggers=1',
                f'text.{zone}=619', f'zone.{zone}.loadBudget=2724608']
        out += [f'zone.{zone}.warp.{k}={k},{LOBBY},0' for k in range(FLOOR_WARPS)]
        npcs = [(m, 2 + k, x, y, f) for k, (m, x, y, f) in enumerate(TRAINER_NPCS)]
        npcs.append((STAIRS_NPC[0], STAIRS_EVENT, *STAIRS_NPC[1:]))
        for i, (model, script, x, y, face) in enumerate(npcs):
            out.append(f'zone.{zone}.npc.{i}={model},{model},{script},0,{x},{y},0,{face}')
    # Complete retail registry entries for the four Maison models, measured header area 214.
    out += [f'regdonor.{m}=214' for m in [*(n[0] for n in TRAINER_NPCS), STAIRS_NPC[0]]]
    return out


def check_floor(raw):
    """Guard the complete generated ZO, including entities, against the measured field buffer limit.

    A cave must not inherit interactive props, retail triggers or a way back into the story.
    """
    if len(raw) > ZO_LIMIT:
        raise ValueError(f'Pyramid floor ZO {len(raw)} exceeds {ZO_LIMIT}')
    files = zo_files(raw)
    entities = files[1]
    if tuple(entities[4:9]) != (0, TRAINERS + 1, FLOOR_WARPS, 0, 0):
        raise ValueError('Pyramid floor has unexpected props/NPCs/warps/triggers')
    start = 12 + (TRAINERS + 1) * 0x30
    if any(struct.unpack_from('<HH', entities, start + k * 0x18) != (LOBBY, 0)
           for k in range(FLOOR_WARPS)):
        raise ValueError('Pyramid floor exit does not lead to the lobby')
    if struct.unpack_from('<H', files[0], 6)[0] != 619:
        raise ValueError('Pyramid floor does not have the Maison helper texts')
    if Script.parse(files[2]).build() != files[2]:
        raise ValueError('Pyramid floor script does not round-trip')
    return len(raw)
