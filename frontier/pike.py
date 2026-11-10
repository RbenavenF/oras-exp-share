#!/usr/bin/env python3
"""Battle Pike (v2 in progress; reports/diseno/tubo.md): the zone script of
its interior (a clone of the Battle Maison hall) and its room routine in shared script 5.

Singles, Level 50, rank Normal, with three of the player's own Pokémon chosen on the Maison's screens (as the Tower,
frontier/tower.py). A round is ROOMS rooms; before each one the player picks one of three doors (left, centre,
right) after a hint about one of them (its category, as Emerald's sRoomTypeHints). Room types: single battle, hard
battle, full heal, partial heal (one or two Pokémon), status (Kirlia/Dusclops: one status for 1, 2 or 3 Pokémon by
room, Emerald's odds and type/ability immunities) and an empty NPC room. The battle rooms are the Maison's battles; HP and
status and PP carry over between them (code.bin hooks, frontier/asm/pike.s, by position in the battle party).
PP use two saved u16 works per fighter (two move slots per work), 0xffff for full; all healing rooms reset them.
The streak counts rooms (own streak and record by route 6); BP as Emerald
after each 14th room (data.FRONTIER_BP['pike']); the Maison's continue / rest / retire menu after each battle; a loss
ends the challenge. Out of v1 (user, 2026-11-03): wild Pokémon rooms; also double battles, Lucy, the selection
screen of Emerald.

Zone script: zone 517's **retail** script run as the Tower (tower.facility_program(retail, 'pike'): reception with
the mutual exclusion, mode and party screens, route, pause, loss, BP every tower.STAGES['pike'] = 14), plus:
- in the battle loop 0x1e1c, after AcmdListClear (before the rival is chosen and walks in): `pike_rooms`: with the
  Pike's route, a new challenge (streak 0) sets the HP works to full and the status works to 0; then GlobalCall
  GLOBAL_ROOM until a battle room: a non-battle room adds one to the streak (and the record) and draws the next; a
  hard battle sets rank Super (SetRank(1): the Maison's Super trainers and sets) for that battle;
- right after StartBattle: with the Pike's route, SetRank(0) again, before IsWin/AddWinCount (the streak route only
  covers rank Normal).

Shared script 5, GLOBAL_ROOM `pike_room` (text 637 lines from LINE_BASE, after the Dome's): the room number; room 14
is always a single battle (deviation: so every round ends through the Maison's win path and its BP); else the three
doors, the hint, the door menu and the room's effect on the works; GlobalSetParentParam(0, ROOM_BATTLE | ROOM_HARD |
ROOM_DONE).

Known deviations (design §1): one zone instead of a lobby and a three-path room (the doors are a menu); the room
number in the Maison's «next battle» line; the Maison's texts and party rules; toxic
is stored as poison (STATUS_VALUE, hypothesis); hard battles are the Maison's Super rank; on resuming, the player
picks the three again and the saved HP, status and PP apply by position (PP capped to the new moves' full PP).
V2 acceptance in Azahar and wild rooms are still pending.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from pawn import OP, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import dome  # noqa: E402
import factory  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402

FACILITY = 'pike'
ZONE = 458                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§28)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
PIKE_BP = fd.FRONTIER_BP[FACILITY]
ROOMS = tower.STAGES[FACILITY]   # NUM_PIKE_ROOMS
FIGHTERS = len(patch.PIKE_HP)
WORK_RNG = 16674                 # generator state between rooms (free per frontier/ids.py; REPARTO.md)
GLOBAL_ROOM = 9776
ROOM_BATTLE, ROOM_HARD, ROOM_DONE = 0, 1, 2

# Room types and hint categories (v1 subset of Emerald's; wild and double left out).
SINGLE, HEAL_FULL, NPC, STATUS, HEAL_PART, HARD = range(6)
TYPES = 6
PEOPLE, WHISPERING, NOSTALGIA, POKEMON = range(4)
CATEGORY = [PEOPLE, PEOPLE, WHISPERING, NOSTALGIA, NOSTALGIA, POKEMON]   # by room type
# Status room: Emerald's odds (percent) and the value written to the status work (the battle block's u32 status,
# PK6 +0xE8). Values: pml's sick enum (1 paralysis, 2 sleep, 3 freeze, 4 burn, 5 poison), hypothesis checked in
# Azahar (reports/frontier.md §28); toxic has no field value of its own there and is stored as poison.
STATUSES = ['toxic', 'freeze', 'paralysis', 'sleep', 'burn']
STATUS_ODDS = [35, 25, 20, 10, 10]
STATUS_VALUE = {'toxic': 5, 'freeze': 3, 'paralysis': 1, 'sleep': 2, 'burn': 4}
STATUS_TARGETS = [(4, 1), (9, 2), (ROOMS, 3)]   # rooms up to n: Pokémon affected
# pret/pokeemerald 731ad5bf src/battle_pike.c DoesType/AbilityPreventStatus.
# These are the Pike event's rules (including Ground vs paralysis), not a move's accuracy/type chart.
# Type/ability IDs below match ORAS. Native selectors measured in DllField+0x4e688:
# 6/7 -> 0x3b3b48/0x4d3204 (current types, including form/Multitype), 22 -> 0x4d1730 (actual ability).
STATUS_IMMUNE_TYPES = {'toxic': (3, 8), 'freeze': (15,), 'paralysis': (4, 13), 'sleep': (), 'burn': (10,)}
STATUS_IMMUNE_ABILITIES = {'toxic': (17,), 'freeze': (40,), 'paralysis': (7,), 'sleep': (15, 72), 'burn': (41,)}
SELECTED_SLOT = 256                          # pike_param: + position, real party or Battle Box selection

TEXTS = {
    'es': {'room': 'Sala [VAR 0203 1,0] de 14.',
           'last': '¡Última sala de la ronda!\nTe espera un combate.',
           'hints': [['Desde la puerta {} se oyen\nvoces de gente.',
                      'Desde la puerta {} llegan\nsusurros.',
                      'Desde la puerta {} llega\nun aire nostálgico.',
                      'Desde la puerta {} se percibe\nla presencia de un Pokémon.']],
           'doors': ['de la izquierda', 'central', 'de la derecha'],
           'door_names': ['Puerta izquierda', 'Puerta central', 'Puerta derecha'],
           'choose': '¿Qué puerta eliges?',
           'single': '¡Un Entrenador te reta a un combate!',
           'hard': '¡Un Entrenador muy fuerte te reta\na un combate!',
           'npc': 'En la sala solo hay una persona\nque te desea buena suerte.',
           'heal_full': '¡Una enfermera ha curado\na todo tu equipo!',
           'healed': ['Una enfermera ha curado\na tu primer Pokémon.',
                      'Una enfermera ha curado\na tu segundo Pokémon.',
                      'Una enfermera ha curado\na tu tercer Pokémon.'],
           'status_intro': '¡Un Pokémon salvaje ha usado un\nataque extraño contra tu equipo!',
           'immune': '¡Su tipo o habilidad lo protege\ndel estado!',
           'positions': ['primer', 'segundo', 'tercer'],
           'status': {'toxic': '¡Tu {} Pokémon ha sido\ngravemente envenenado!',
                      'freeze': '¡Tu {} Pokémon ha sido\ncongelado!',
                      'paralysis': '¡Tu {} Pokémon ha sido\nparalizado!',
                      'sleep': '¡Tu {} Pokémon se ha\nquedado dormido!',
                      'burn': '¡Tu {} Pokémon ha sido\nquemado!'}},
    'en': {'room': 'Room [VAR 0203 1,0] of 14.',
           'last': 'The last room of the round!\nA battle awaits you.',
           'hints': [['Voices of people can be heard\nfrom the {} door.',
                      'Whispers come from\nthe {} door.',
                      'A nostalgic air comes from\nthe {} door.',
                      'The presence of a Pokémon can be\nfelt from the {} door.']],
           'doors': ['left', 'centre', 'right'],
           'door_names': ['Left door', 'Centre door', 'Right door'],
           'choose': 'Which door will you choose?',
           'single': 'A Trainer challenges you to a battle!',
           'hard': 'A very strong Trainer challenges\nyou to a battle!',
           'npc': 'There is only someone here\nwho wishes you luck.',
           'heal_full': 'A nurse healed\nyour whole team!',
           'healed': ['A nurse healed\nyour first Pokémon.', 'A nurse healed\nyour second Pokémon.',
                      'A nurse healed\nyour third Pokémon.'],
           'status_intro': 'A wild Pokémon used a strange\nattack on your team!',
           'immune': 'Its type or Ability protects it\nfrom the status condition!',
           'positions': ['first', 'second', 'third'],
           'status': {'toxic': 'Your {} Pokémon was\nbadly poisoned!',
                      'freeze': 'Your {} Pokémon was\nfrozen solid!',
                      'paralysis': 'Your {} Pokémon was\nparalyzed!',
                      'sleep': 'Your {} Pokémon\nfell asleep!',
                      'burn': 'Your {} Pokémon was\nburned!'}},
}
LINE_BASE = dome.LINE_WON + 1
LINE_ROOM = LINE_BASE
LINE_LAST = LINE_BASE + 1
LINE_HINT = LINE_BASE + 2                      # + 3 * category + door
LINE_CHOOSE = LINE_HINT + 12
LINE_DOOR = LINE_CHOOSE + 1                    # + door
LINE_SINGLE, LINE_HARD, LINE_NPC, LINE_HEAL_FULL = (LINE_DOOR + 3 + k for k in range(4))
LINE_HEALED = LINE_DOOR + 7                    # + position
LINE_STATUS_INTRO = LINE_HEALED + 3
LINE_STATUS = LINE_STATUS_INTRO + 1            # + 5 * position + status
LINE_IMMUNE = LINE_STATUS + 3 * len(STATUSES)
LINE_END = LINE_IMMUNE + 1


def lines(lang):
    """Text 637 lines of the Pike, from LINE_BASE, in one game language."""
    t = TEXTS[factory.LANG[lang]]
    out = [t['room'], t['last']]
    out += [hint.format(door) for hint in t['hints'][0] for door in t['doors']]
    out += [t['choose'], *t['door_names'], t['single'], t['hard'], t['npc'], t['heal_full'], *t['healed'],
            t['status_intro']]
    out += [t['status'][s].format(pos) for pos in t['positions'] for s in STATUSES]
    out += [t['immune']]
    assert len(out) == LINE_END - LINE_BASE
    return out


# --- shared script 5 -------------------------------------------------------------------------------------------

def _say(r, helpers, line):
    r.call(helpers['msg'], line, 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)


def room_routine(p, helpers):
    """pike_room(): one room (module docstring); GlobalSetParentParam(0, ROOM_*)."""
    state = p.data_labels['factory_rng']
    category = p.data_block('pike_category', list(CATEGORY))
    names = ['room', 'healthy', 'cat', 'hint', 'door', 'type', 'value', 'count', 'start', 'status', 'result',
             'type0', 'type1', 'ability',
             *(f'{f}{k}' for f in ('hp', 'st', 't') for k in range(3))]
    r = factory.Routine(p, 'pike_room', names)
    end = 'pike_room_end'
    # Seed as the Factory's draft: real-time seconds + 32767 × the saved state.
    r.sysreq('WorkGet', WORK_RNG)
    r.op('SMUL_P_C', 0x7FFF)
    r.op('PUSH_PRI', 0)
    r.sysreq('_GetRealTimeToSecond')
    r.op('PALT', 0)
    r.op('ADD', 0)
    r.op('STOR_P_PRI', state)

    # room = streak % ROOMS (0-based)
    r.sysreq('WorkGet', STREAK)
    r.store('room')
    r.op('MOVE_ALT', 0)
    r.const(ROOMS)
    r.op('SDIV_ALT', 0)
    r.op('SMUL_P_C', ROOMS)
    r.load_alt('room')
    r.op('SUB_ALT', 0)
    r.store('room')
    r.add(1)
    r.store('value')
    r.sysreq('WordSetNumber', 1, 'value', 4, 0)   # as zone 517 at 0x3c3c, line «[VAR 0203 1,0]»
    _say(r, helpers, LINE_ROOM)
    r.set('result', ROOM_BATTLE)
    r.load('room')
    r.op('EQ_P_C_PRI', ROOMS - 1)
    not_last = r.new_label('notlast')
    r.op('JZER', not_last)
    _say(r, helpers, LINE_LAST)
    r.op('JUMP', end)
    r.p.label(not_last)

    # The team: HP and status works; healthy = alive and without status.
    r.set('healthy', 0)
    for k in range(FIGHTERS):
        r.sysreq('WorkGet', patch.PIKE_HP[k])
        r.store(f'hp{k}')
        r.sysreq('WorkGet', patch.PIKE_ST[k])
        r.store(f'st{k}')
        skip = r.new_label('nothealthy')
        r.load(f'hp{k}')
        r.op('JZER', skip)
        r.load(f'st{k}')
        r.op('JNZ', skip)
        r.load('healthy')
        r.add(1)
        r.store('healthy')
        r.p.label(skip)

    # Doors: the hinted one has a type of the hint's category; the others, any type of another category. The
    # status room needs a healthy Pokémon (Emerald). Rejection sampling over the six types.
    r.call('factory_rand', 3)
    r.store('hint')
    r.call('factory_rand', 4)
    r.store('cat')
    for d in range(3):
        again, other, ok = r.new_label(f'door{d}'), r.new_label(f'other{d}'), r.new_label(f'ok{d}')
        r.p.label(again)
        r.call('factory_rand', TYPES)
        r.store(f't{d}')
        r.op('EQ_P_C_PRI', STATUS)
        status_ok = r.new_label('statusok')
        r.op('JZER', status_ok)
        r.load('healthy')
        r.op('JZER', again)
        r.p.label(status_ok)
        r.load(f't{d}')
        r.cell(category)
        r.store('value')                         # the type's category
        r.load('hint')
        r.op('EQ_P_C_PRI', d)
        r.op('JZER', other)
        r.load('value')
        r.load_alt('cat')
        r.op('JNEQ', again)                      # hinted door: the hint's category
        r.op('JUMP', ok)
        r.p.label(other)
        r.load('value')
        r.load_alt('cat')
        r.op('JEQ', again)                       # other doors: another category
        r.p.label(ok)

    # Hint, then the door menu (B asks again).
    r.load('cat')
    r.op('SMUL_P_C', 3)
    r.load_alt('hint')
    r.op('ADD', 0)
    r.add(LINE_HINT)
    r.store('value')
    r.call(helpers['msg'], 'value', 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)
    ask = r.new_label('ask')
    r.p.label(ask)
    r.call(helpers['msg'], LINE_CHOOSE, 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
    for d in range(3):
        r.sysreq('ListMenuAdd', LINE_DOOR + d, d, 0)
    r.call(helpers['menu_run'])
    r.store('door')
    r.call(helpers['msg_close'], 0)
    r.load('door')
    r.const_alt(2)
    r.op('JSGRTR', ask)
    r.load('door')
    r.const_alt(0)
    r.op('JSLESS', ask)
    chosen = r.new_label('chosen')
    for d in range(3):
        nxt = r.new_label('pick')
        r.load('door')
        r.op('EQ_P_C_PRI', d)
        r.op('JZER', nxt)
        r.load(f't{d}')
        r.store('type')
        r.op('JUMP', chosen)
        r.p.label(nxt)
    r.p.label(chosen)

    handlers = {SINGLE: r.new_label('single'), HARD: r.new_label('hard'), NPC: r.new_label('npc'),
                HEAL_FULL: r.new_label('healfull'), HEAL_PART: r.new_label('healpart'), STATUS: r.new_label('status')}
    for kind, label in handlers.items():
        r.load('type')
        r.op('EQ_P_C_PRI', kind)
        r.op('JNZ', label)
    r.op('JUMP', end)                            # not reached

    r.p.label(handlers[SINGLE])
    _say(r, helpers, LINE_SINGLE)
    r.op('JUMP', end)
    r.p.label(handlers[HARD])
    _say(r, helpers, LINE_HARD)
    r.set('result', ROOM_HARD)
    r.op('JUMP', end)
    r.p.label(handlers[NPC])
    _say(r, helpers, LINE_NPC)
    r.set('result', ROOM_DONE)
    r.op('JUMP', end)

    r.p.label(handlers[HEAL_FULL])
    _say(r, helpers, LINE_HEAL_FULL)
    for k in range(FIGHTERS):
        r.sysreq('WorkSet', patch.PIKE_HP[k], patch.PIKE_FULL)
        r.sysreq('WorkSet', patch.PIKE_ST[k], 0)
        for pair in patch.PIKE_PP:
            r.sysreq('WorkSet', pair[k], patch.PIKE_FULL)
    r.set('result', ROOM_DONE)
    r.op('JUMP', end)

    # Partial heal: one or two Pokémon (start, start + 1), fully (also a fainted one).
    r.p.label(handlers[HEAL_PART])
    r.call('factory_rand', 2)
    r.add(1)
    r.store('count')
    r.call('factory_rand', 3)
    r.store('start')
    for j in range(2):
        if j:
            r.load('count')
            r.op('EQ_P_C_PRI', 1)
            r.op('JNZ', 'pike_room_healdone')
            r.load('start')
            r.add(1)
            r.store('start')
            r.const_alt(3)
            wrap = r.new_label('wrap')
            r.op('JSLESS', wrap)
            r.set('start', 0)
            r.p.label(wrap)
        healed = r.new_label('healed')
        for k in range(FIGHTERS):
            nxt = r.new_label('heal')
            r.load('start')
            r.op('EQ_P_C_PRI', k)
            r.op('JZER', nxt)
            r.sysreq('WorkSet', patch.PIKE_HP[k], patch.PIKE_FULL)
            r.sysreq('WorkSet', patch.PIKE_ST[k], 0)
            for pair in patch.PIKE_PP:
                r.sysreq('WorkSet', pair[k], patch.PIKE_FULL)
            _say(r, helpers, LINE_HEALED + k)
            r.op('JUMP', healed)
            r.p.label(nxt)
        r.p.label(healed)
    r.p.label('pike_room_healdone')
    r.set('result', ROOM_DONE)
    r.op('JUMP', end)

    # Status: one status (Emerald's odds) for up to `count` healthy Pokémon, from a random position on.
    r.p.label(handlers[STATUS])
    counted = r.new_label('counted')
    for last_room, n in STATUS_TARGETS:
        r.set('count', n)
        r.load('room')
        r.const_alt(last_room - 1)
        r.op('JSLEQ', counted)                   # room (0-based) <= last_room - 1
    r.p.label(counted)
    r.call('factory_rand', 100)
    r.store('value')
    drawn = r.new_label('drawn')
    bound = 0
    for s, (name, odds) in enumerate(zip(STATUSES, STATUS_ODDS)):
        bound += odds
        r.set('status', s)
        r.load('value')
        r.const_alt(bound - 1)
        r.op('JSLEQ', drawn)
    r.p.label(drawn)
    _say(r, helpers, LINE_STATUS_INTRO)
    r.call('factory_rand', 3)
    r.store('start')
    for j in range(FIGHTERS):
        done_j = r.new_label('target')
        r.load('count')
        r.op('JZER', done_j)
        for k in range(FIGHTERS):
            nxt = r.new_label('pos')
            r.load('start')
            r.op('EQ_P_C_PRI', k)
            r.op('JZER', nxt)
            r.load(f'hp{k}')
            r.op('JZER', done_j)                 # fainted
            r.load(f'st{k}')
            r.op('JNZ', done_j)                  # already has a status
            for var, selector in [('type0', 6), ('type1', 7), ('ability', 22)]:
                r.sysreq('PokePartyGetParam', SELECTED_SLOT + k, selector, 0)
                r.store(var)
            immune, counted_target = r.new_label('immune'), r.new_label('counttarget')
            for s, name in enumerate(STATUSES):
                other = r.new_label('st')
                r.load('status')
                r.op('EQ_P_C_PRI', s)
                r.op('JZER', other)
                for var, values in [('type0', STATUS_IMMUNE_TYPES[name]),
                                    ('type1', STATUS_IMMUNE_TYPES[name]),
                                    ('ability', STATUS_IMMUNE_ABILITIES[name])]:
                    for value in values:
                        r.load(var)
                        r.op('EQ_P_C_PRI', value)
                        r.op('JNZ', immune)
                r.sysreq('WorkSet', patch.PIKE_ST[k], STATUS_VALUE[name])
                _say(r, helpers, LINE_STATUS + len(STATUSES) * k + s)
                r.p.label(other)
            r.op('JUMP', counted_target)
            r.p.label(immune)
            _say(r, helpers, LINE_IMMUNE)
            r.p.label(counted_target)
            r.load('count')
            r.add(-1)
            r.store('count')
            r.op('JUMP', done_j)
            r.p.label(nxt)
        r.p.label(done_j)
        r.load('start')
        r.add(1)
        r.store('start')
        r.const_alt(3)
        wrap = r.new_label('swrap')
        r.op('JSLESS', wrap)
        r.set('start', 0)
        r.p.label(wrap)
    r.set('result', ROOM_DONE)

    r.p.label(end)
    r.op('LOAD_P_PRI', state)
    r.field(16, 16)
    r.store('value')
    r.sysreq('WorkSet', WORK_RNG, 'value')
    r.sysreq('GlobalSetParentParam', 0, 'result')
    r.op('ZERO_PRI', 0)
    r.ret()


def shared_cases():
    """(case value, routine, builder(p, helpers)) for factory.shared_program."""
    return [(GLOBAL_ROOM, 'pike_room', room_routine)]


# --- zone script --------------------------------------------------------------------------------------------------

def rooms_routine(p):
    """pike_rooms(): with the Pike's route, the rooms up to the next battle (module docstring)."""
    r = factory.Routine(p, 'pike_rooms', ['result', 'streak'])
    end = 'pike_rooms_end'
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.op('EQ_P_C_PRI', ROUTE)
    r.op('JZER', end)
    r.sysreq('WorkGet', STREAK)
    r.op('JNZ', 'pike_rooms_loop')
    for k in range(FIGHTERS):                    # a new challenge: a fresh team
        r.sysreq('WorkSet', patch.PIKE_HP[k], patch.PIKE_FULL)
        r.sysreq('WorkSet', patch.PIKE_ST[k], 0)
        for pair in patch.PIKE_PP:
            r.sysreq('WorkSet', pair[k], patch.PIKE_FULL)
    r.p.label('pike_rooms_loop')
    r.sysreq('GlobalCall', GLOBAL_ROOM)
    r.sysreq('GlobalGetChildParam', 0)
    r.store('result')
    r.op('EQ_P_C_PRI', ROOM_DONE)
    r.op('JNZ', 'pike_rooms_done')
    r.load('result')
    r.op('EQ_P_C_PRI', ROOM_HARD)
    r.op('JZER', end)
    r.sysreq('SetRank', 1)                       # hard battle: the Maison's Super rank, this battle only
    r.op('JUMP', end)
    r.p.label('pike_rooms_done')                 # a room without battle: one more room on the streak
    r.sysreq('WorkGet', STREAK)
    r.add(1)
    r.store('streak')
    r.sysreq('WorkSet', STREAK, 'streak')
    r.sysreq('WorkGet', RECORD)
    r.load_alt('streak')
    r.op('JSGEQ', 'pike_rooms_loop')             # record >= streak
    r.sysreq('WorkSet', RECORD, 'streak')
    r.op('JUMP', 'pike_rooms_loop')
    r.p.label(end)
    r.op('ZERO_PRI', 0)
    r.ret()


def after_start_routine(p):
    """pike_after_start(): with the Pike's route, rank Normal again (after a hard battle)."""
    r = factory.Routine(p, 'pike_after_start', [])
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.op('EQ_P_C_PRI', ROUTE)
    r.op('JZER', 'pike_after_start_end')
    r.sysreq('SetRank', 0)
    r.p.label('pike_after_start_end')
    r.op('ZERO_PRI', 0)
    r.ret()


def _ops(p, build):
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    build(body)
    return body.items


BATTLE_LOOP = 'L1e1c'


def pike_program(retail):
    """Zone 517's retail script with the Pike (module docstring)."""
    p = tower.facility_program(retail, FACILITY)
    start = factory._index(p, BATTLE_LOOP)
    clear = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
                 and p.items[i].op == OP['SYSREQ_N'])
    if p.items[clear].args[0] != p.native('AcmdListClear'):
        raise ValueError('AcmdListClear not found at 0x1e38')
    p.items[clear + 1:clear + 1] = _ops(p, lambda b: b.call('pike_rooms'))
    at = factory._index(p, dome.BEFORE_BATTLE)
    battle = next(i for i in range(at, len(p.items)) if isinstance(p.items[i], Op)
                  and p.items[i].op == OP['SYSREQ_N'])
    if p.items[battle].args[0] != p.native('StartBattle'):
        raise ValueError('StartBattle not found after 0x1edc')
    p.items[battle + 1:battle + 1] = _ops(p, lambda b: b.call('pike_after_start'))
    rooms_routine(p)
    after_start_routine(p)
    return p


def zone_script(retail):
    """Built zone script bytes of the Pike's interior."""
    return pike_program(retail).build_script(f'L{retail.main:x}').build()
