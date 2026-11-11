#!/usr/bin/env python3
"""Frontier Brains, common part (F8-CEREBROS-BASE, reports/diseno/cerebros.md §3; reports/frontier.md §39).

Appearance (pokeemerald 731ad5bf `sFrontierBrainStreakAppearances`, `GetFrontierBrainStatus`): with no symbol of
the facility the Brain comes at its silver unit, with silver only at its gold unit, with both at the silver unit
(silver team) and at the gold unit and every `period` after it (gold team). `due` is the reference; the zone script
runs the same rule (`check_routine`) before each rival is chosen, from the facility streak, so a resumed challenge
recomputes it. Facilities whose unit is not a battle (Dome, Pike, Pyramid) get their own adapter; BASE enables the
Tower initially; the Factory adapter also enables Noland (ENABLED).

Symbols: saved work WORK_SYMBOLS, two bits per route r at 2*(r-1): 0 none, 1 silver, 3 silver and gold (2 is
invalid and read as 3). Never cleared by a loss, a retirement or another challenge.

Zone script (517 clones run as the Tower, `install`):
- 0x2b98 (the rival is chosen and placed): first `brains_check` -> WORK_BRAIN = route + 8 * variant (1 silver,
  2 gold) or 0;
- 0x4338 (presentation), Singles: with a Brain, its intro line (text 637 through shared script 5 case GLOBAL_SAY)
  instead of the Maison trainer's start message;
- win, after AddWinCount, before IsBoss: `brains_won`: the symbol, BRAIN_BONUS BP (data.BRAIN_BONUS, through the
  Maison's 0x30 = PlayerSetBP + record), its line, WORK_BRAIN = 0. The round's BP follow as usual (0x3de4);
- lost battle (0x2210) and cleanup (0x1458): WORK_BRAIN = 0;
- 0x451c (the Maison's «boss streak?», used by its boss scene 0x5384 and the win menu 0x3c54): 0 on any Frontier
  route (`suppress_retail_boss`, also in the Maison script for the Factory and in the Dome).

Native (frontier/asm/brains_cro.s, DllField.cro padding, SITES): the chooser returns the Brain's trainer
(maisontrN entry TRAINER_FIRST + 2 * (route - 1) + variant - 1, class/name of TRAINERS), the load clears the Maison
boss flag on Frontier routes, and once the battle is set up the rival's three members are remade from the Brain's
row: set, IV, ability slot 0 and exact EV, in order. Noland uses the seeded rental sets, their EV masks,
Frustration instead of Return, friendship 0 and IV 15/31 (factory_brain.py). Without a Brain due, a Frontier route only differs from retail
in the boss: rank Normal from the 19th win draws trainers 70-109 instead of the Maison's boss (19) or trainer 0.
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from pawn import OP, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import patch  # noqa: E402

# Saved works (free per frontier/ids.py, 2026-11-11; frontier/REPARTO.md).
WORK_SYMBOLS = 16729       # 2 bits per route
WORK_BRAIN = 16730         # Brain of the coming battle: route + 8 * variant; 0 none
WORK_PYRAMID = 16731       # reserved for the Pyramid's summit (F8-CEREBRO-PIRAMIDE)
WORK_MSG = 16733           # line of text 637 for GLOBAL_SAY, from LINE_BASE
SILVER, GOLD = 1, 2
GLOBAL_SAY = 9778          # shared script 5 case (patch.GLOBAL_ROW 9770-9779; 9770-9777 taken)
BOSS_STREAK = 19           # rank Normal: 0x1e3aac returns the Maison's boss at 19 wins and trainer 0 above
LATE_FIRST, LATE_COUNT = 70, 40   # the 15-18 bracket of 0x1e3aac (0x1e4860(work, r1, 70, 40))

# (silver unit, gold unit, period after both), units counted from 1 (cerebros.md §1).
APPEARANCES = {'factory': (21, 42, 21), 'tower': (35, 70, 35), 'palace': (21, 42, 21), 'arena': (28, 56, 28),
               'dome': (5, 10, 5), 'pike': (28, 140, 56), 'pyramid': (21, 70, 35)}
ENABLED = ('factory', 'tower')
NAMES = {'factory': 'Noland', 'tower': 'Anabel', 'palace': 'Spenser', 'arena': 'Greta', 'dome': 'Tucker',
         'pike': 'Lucy', 'pyramid': 'Brandon'}
CLASSES = {'factory': 30, 'tower': 9, 'palace': 31, 'arena': 63, 'dome': 10, 'pike': 13, 'pyramid': 96}  # a/0/7/7 #21
SYMBOL = {'es': {'factory': 'Conocimiento', 'tower': 'Habilidad', 'palace': 'Ánimo', 'arena': 'Agallas',
                 'dome': 'Táctica', 'pike': 'Suerte', 'pyramid': 'Bravura'},
          'en': {'factory': 'Knowledge', 'tower': 'Ability', 'palace': 'Spirits', 'arena': 'Guts',
                 'dome': 'Tactics', 'pike': 'Luck', 'pyramid': 'Brave'}}
FACILITY = {'es': {'factory': 'la Fábrica Batalla', 'tower': 'la Torre Batalla', 'palace': 'el Palacio Batalla',
                   'arena': 'la Arena Batalla', 'dome': 'el Domo Batalla', 'pike': 'el Tubo Batalla',
                   'pyramid': 'la Pirámide Batalla'},
            'en': {'factory': 'the Battle Factory', 'tower': 'the Battle Tower', 'palace': 'the Battle Palace',
                   'arena': 'the Battle Arena', 'dome': 'the Battle Dome', 'pike': 'the Battle Pike',
                   'pyramid': 'the Battle Pyramid'}}

# Fixed teams (cerebros.md §7, pokeemerald 731ad5bf sFrontierBrainsMons) with ORAS ids, checked against the Spanish
# game text by tests/test_frontier_brains.py: species (98), moves (14), items (114), natures (51).
# EV in the source order HP, Atk, Def, Spe, SpA, SpD (also the Maison set's EV bit order, 0x1efb94).
SPECIES = {'ALAKAZAM': 65, 'ENTEI': 244, 'SNORLAX': 143, 'RAIKOU': 243, 'LATIOS': 381}
MOVES = {'THUNDER_PUNCH': 9, 'FIRE_PUNCH': 7, 'ICE_PUNCH': 8, 'DISABLE': 50, 'FIRE_BLAST': 126, 'CALM_MIND': 347,
         'RETURN': 216, 'ROAR': 46, 'BODY_SLAM': 34, 'BELLY_DRUM': 187, 'YAWN': 281, 'SHADOW_BALL': 247,
         'THUNDERBOLT': 85, 'REFLECT': 115, 'REST': 156, 'PSYCHIC': 94, 'RECOVER': 105, 'DRAGON_CLAW': 337,
         'CURSE': 174}
ITEMS = {'BRIGHT_POWDER': 213, 'LUM_BERRY': 157, 'QUICK_CLAW': 217, 'CHESTO_BERRY': 150}
NATURES = {'LONELY': 1, 'ADAMANT': 3, 'MODEST': 15}
TEAMS = {
    ('tower', SILVER): (24, [
        ('ALAKAZAM', 'BRIGHT_POWDER', 'MODEST', (106, 0, 152, 152, 100, 0),
         ('THUNDER_PUNCH', 'FIRE_PUNCH', 'ICE_PUNCH', 'DISABLE')),
        ('ENTEI', 'LUM_BERRY', 'LONELY', (100, 152, 152, 0, 100, 6), ('FIRE_BLAST', 'CALM_MIND', 'RETURN', 'ROAR')),
        ('SNORLAX', 'QUICK_CLAW', 'ADAMANT', (152, 152, 0, 0, 106, 100),
         ('BODY_SLAM', 'BELLY_DRUM', 'YAWN', 'SHADOW_BALL'))]),
    ('tower', GOLD): (31, [
        ('RAIKOU', 'LUM_BERRY', 'MODEST', (158, 0, 252, 100, 0, 0), ('THUNDERBOLT', 'CALM_MIND', 'REFLECT', 'REST')),
        ('LATIOS', 'BRIGHT_POWDER', 'MODEST', (252, 0, 252, 6, 0, 0), ('PSYCHIC', 'CALM_MIND', 'RECOVER', 'DRAGON_CLAW')),
        ('SNORLAX', 'CHESTO_BERRY', 'ADAMANT', (252, 252, 0, 0, 6, 0), ('CURSE', 'RETURN', 'REST', 'SHADOW_BALL'))]),
}
# maisonpkN entries of the Brains' sets (after the Pike's 217-222) and maisontrN entries of their trainers (after
# the 129 retail ones; gametext 154, the Normal Maison trainer names, gets one line per entry). By route and variant.
SET_FIRST = patch.PIKE_WILD_FIRST + 6      # 223
TRAINER_FIRST = 129
ROUTES = len(patch.STREAK_ROUTES)
TEXT_TRAINER_NAMES = 154                   # gametext: maisontrN names by trainer id (0x1e36b4, file 0x9a)


def route_of(facility):
    return patch.ROUTE[facility]


def trainer_id(facility, variant):
    return TRAINER_FIRST + 2 * (route_of(facility) - 1) + variant - 1


def set_index(facility, variant, k):
    return SET_FIRST + 6 * (route_of(facility) - 1) + 3 * (variant - 1) + k


def symbols_of(word, route):
    bits = (word >> (2 * (route - 1))) & 3
    return 3 if bits == 2 else bits


def due(facility, unit, symbols):
    """Brain variant (SILVER, GOLD) or 0 for the unit numbered `unit` (wins so far + 1) with `symbols` (0, 1, 3)."""
    silver, gold, period = APPEARANCES[facility]
    if symbols == 0:
        return SILVER if unit == silver else 0
    if symbols == 1:
        return GOLD if unit == gold else 0
    if unit == silver:
        return SILVER
    return GOLD if unit >= gold and (unit - gold) % period == 0 else 0


def won(word, route, variant):
    """Symbols work after winning a Brain battle of `variant` on `route`."""
    return word | ((1 if variant == SILVER else 3) << (2 * (route - 1)))


# --- data ---------------------------------------------------------------------------------------------------------

def pack_set(species, item, nature, evs, moves):
    """maisonpkN set (data.parse_set): EV bits of the stats the Brain trains (the native code then writes the exact
    values; the bits only matter if it does not run)."""
    mask = sum(1 << k for k, ev in enumerate(evs) if ev)
    return struct.pack('<5HBBHH', SPECIES[species], *(MOVES[m] for m in moves), mask, NATURES[nature], ITEMS[item], 0)


def sets():
    """{maisonpkN index: 16-byte set} of the enabled Brains."""
    out = {}
    for (facility, variant), (_, team) in TEAMS.items():
        for k, (species, item, nature, evs, moves) in enumerate(team):
            out[set_index(facility, variant, k)] = pack_set(species, item, nature, evs, moves)
    return out


def trainers():
    """{maisontrN index: entry} (class, count, the variant's three sets), contiguous from TRAINER_FIRST: every
    route and variant gets an entry, those not enabled with the enabled entry's shape but their facility class and
    the Tower's sets, so the file has no holes (they are never chosen: brains_check only marks ENABLED)."""
    out = {}
    for facility, route in patch.ROUTE.items():
        for variant in (SILVER, GOLD):
            source = facility if (facility, variant) in TEAMS else 'tower'
            ids = [set_index(source, variant, k) for k in range(3)]
            out[trainer_id(facility, variant)] = struct.pack('<5H', CLASSES[facility], len(ids), *ids)
    return out


def trainer_names():
    """Names of maisontrN TRAINER_FIRST.. in order (gametext TEXT_TRAINER_NAMES lines, every language)."""
    by_id = {trainer_id(f, v): NAMES[f] for f in patch.ROUTE for v in (SILVER, GOLD)}
    return [by_id[i] for i in sorted(by_id)]


def brain_rows():
    """brain_table bytes of brains_cro.s: per (route - 1) * 2 + variant - 1, u16 trainer (0 = no Brain), u8 IV, u8 0,
    3 x (u16 maisonpkN set, u8 EV[6] in pml order HP, Atk, Def, SpA, SpD, Spe)."""
    out = bytearray()
    for route in range(1, ROUTES + 1):
        facility = patch.STREAK_ROUTES[route][0]
        for variant in (SILVER, GOLD):
            if facility not in ENABLED:
                out += bytes(ENTRY)
                continue
            if facility == 'factory':
                out += struct.pack('<HBB', trainer_id(facility, variant), 15 if variant == SILVER else 31, 0)
                out += bytes(ENTRY - 4)  # dynamic sets in WORK_RIVAL; native preserves them across CODE_START
                continue
            iv, team = TEAMS[(facility, variant)]
            out += struct.pack('<HBB', trainer_id(facility, variant), iv, 0)
            for k, (_, _, _, evs, _) in enumerate(team):
                hp, atk, df, spe, spa, spd = evs
                out += struct.pack('<H6B', set_index(facility, variant, k), hp, atk, df, spa, spd, spe)
    return bytes(out)


ENTRY = 4 + 3 * 8

# --- text 637 -----------------------------------------------------------------------------------------------------

KEYS = ('intro_silver', 'intro_gold', 'won_silver', 'won_gold')


def lines(lang):
    """Text 637 lines of the Brains, from LINE_BASE: KEYS per route 1..7."""
    code = factory.LANG[lang]
    out = []
    for route in range(1, ROUTES + 1):
        f = patch.STREAK_ROUTES[route][0]
        name, symbol, place = NAMES[f], SYMBOL[code][f], FACILITY[code][f]
        if code == 'es':
            out += [f'Soy {name}, Cerebro del Frente\nde {place}.\n¡Demuéstrame lo que vales!',
                    f'Has vuelto a llegar hasta mí.\nSoy {name}. ¡Esta vez combatiré\ncon todas mis fuerzas!',
                    f'¡Has obtenido el Símbolo {symbol}\nde plata! Recibes {fd.BRAIN_BONUS} PB más.',
                    f'¡Has obtenido el Símbolo {symbol}\nde oro! Recibes {fd.BRAIN_BONUS} PB más.']
        else:
            out += [f"I'm {name}, Frontier Brain\nof {place}.\nShow me what you can do!",
                    f"You made it to me again.\nI'm {name}. This time I'll battle\nwith everything I have!",
                    f'You obtained the silver\n{symbol} Symbol! You get {fd.BRAIN_BONUS} more BP.',
                    f'You obtained the gold\n{symbol} Symbol! You get {fd.BRAIN_BONUS} more BP.']
    return out


def line_base():
    import pyramid
    return pyramid.LINE_END


# --- shared script 5 ----------------------------------------------------------------------------------------------

def say_routine(p, helpers):
    """brains_say(): text 637 line line_base() + WORK_MSG."""
    r = factory.Routine(p, 'brains_say', ['line'])
    r.sysreq('WorkGet', WORK_MSG)
    r.add(line_base())
    r.store('line')
    r.call(helpers['msg'], 'line', 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def shared_cases():
    return [(GLOBAL_SAY, 'brains_say', say_routine)]


# --- zone scripts -------------------------------------------------------------------------------------------------

def _ops(p, build):
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    build(body)
    return body.items


def _pow4(p):
    """Data block of 4 ** k, k = 0..ROUTES - 1 (the symbols' field of route k + 1), shared by the routines."""
    if 'brains_pow4' not in p.data_labels:
        p.data_block('brains_pow4', [4 ** k for k in range(ROUTES)])
    return p.data_labels['brains_pow4']


def check_routine(p):
    """brains_check(): WORK_BRAIN for the coming battle (module docstring); 0 when none."""
    r = factory.Routine(p, 'brains_check', ['route', 'unit', 'sym', 'silver', 'gold', 'variant'])
    rows = p.data_block('brains_rows', [x for route in range(1, ROUTES + 1) for x in (
        APPEARANCES[patch.STREAK_ROUTES[route][0]] if patch.STREAK_ROUTES[route][0] in ENABLED else (0, 0, 1))])
    none, sym1, both, gold_rep, found = (r.new_label(s) for s in ('none', 'sym1', 'both', 'gold', 'found'))
    r.sysreq('WorkSet', WORK_BRAIN, 0)
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.store('route')
    r.op('JZER', none)
    r.load('route')
    r.const_alt(ROUTES)
    r.op('JSGRTR', none)                    # route > ROUTES
    for k, name in enumerate(('silver', 'gold')):
        r.load('route')
        r.op('SMUL_P_C', 3)
        r.add(k - 3)
        r.cell(rows)
        r.store(name)
    r.load('silver')
    r.op('JZER', none)                      # not enabled
    r.sysreq('GetMyWinCount', 0, 0)         # the facility's streak (WORK_ROUTE set)
    r.add(1)
    r.store('unit')
    pow4 = _pow4(p)
    r.sysreq('WorkGet', WORK_SYMBOLS)
    r.op('MOVE_ALT', 0)
    r.load('route')
    r.add(-1)
    r.cell(pow4)
    r.op('SDIV_ALT', 0)                     # PRI = symbols / 4 ** (route - 1)
    r.field(0, 2)
    r.store('sym')
    r.set('variant', 0)
    r.load('sym')
    r.op('JNZ', sym1)
    r.load('unit')                          # no symbol: silver at the silver unit
    r.load_alt('silver')
    r.op('JNEQ', none)
    r.set('variant', SILVER)
    r.op('JUMP', found)
    r.p.label(sym1)
    r.load('sym')
    r.op('EQ_P_C_PRI', 1)
    r.op('JZER', both)
    r.load('unit')                          # silver only: gold at the gold unit
    r.load_alt('gold')
    r.op('JNEQ', none)
    r.set('variant', GOLD)
    r.op('JUMP', found)
    r.p.label(both)                         # both (or the invalid 2): silver team at silver, gold from gold on
    r.load('unit')
    r.load_alt('silver')
    r.op('JNEQ', gold_rep)
    r.set('variant', SILVER)
    r.op('JUMP', found)
    r.p.label(gold_rep)
    r.load('gold')
    r.load_alt('unit')
    r.op('JSGRTR', none)                    # gold > unit
    r.load('unit')
    r.load_alt('gold')
    r.op('SUB_ALT', 0)                      # PRI = unit - gold
    r.op('MOVE_ALT', 0)
    r.load('route')
    r.op('SMUL_P_C', 3)
    r.add(-1)
    r.cell(rows)                            # PRI = period
    r.op('SDIV_ALT', 0)                     # ALT = (unit - gold) % period
    r.op('MOVE_PRI', 0)
    r.op('JNZ', none)
    r.set('variant', GOLD)
    r.p.label(found)
    r.load('variant')
    r.op('SMUL_P_C', 8)
    r.load_alt('route')
    r.op('ADD', 0)
    r.store('variant')
    r.sysreq('WorkSet', WORK_BRAIN, 'variant')
    r.load('route')
    r.op('EQ_P_C_PRI', patch.ROUTE['factory'])
    r.op('JZER', none)
    r.load('unit')
    r.add(-1)
    r.store('unit')
    r.sysreq('WorkSet', factory.WORK_STREAK, 'unit')
    r.sysreq('GlobalCall', factory.GLOBAL_SWAP)
    r.p.label(none)
    r.op('ZERO_PRI', 0)
    r.ret()


def _brain_msg(r, extra):
    """WORK_MSG = 4 * (route - 1) + variant - 1 + extra from WORK_BRAIN (r.local 'b')."""
    r.load('b')
    r.const_alt(7)
    r.op('AND', 0)
    r.add(-1)
    r.op('SMUL_P_C', 4)
    r.store('m')
    r.load('b')
    r.op('SHR_P_C_PRI', 3)
    r.add(extra - 1)
    r.load_alt('m')
    r.op('ADD', 0)
    r.store('m')
    r.sysreq('WorkSet', WORK_MSG, 'm')
    r.sysreq('GlobalCall', GLOBAL_SAY)


def won_routine(p):
    """brains_won(): after a won battle with a Brain due on the current route: the symbol, the bonus BP, the line;
    WORK_BRAIN = 0."""
    r = factory.Routine(p, 'brains_won', ['b', 'route', 'm', 'sym'])
    done = r.new_label('done')
    r.sysreq('WorkGet', WORK_BRAIN)
    r.store('b')
    r.op('JZER', done)
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.store('route')
    r.load('b')
    r.const_alt(7)
    r.op('AND', 0)
    r.load_alt('route')
    r.op('JNEQ', done)
    r.load('b')                              # bits: 1 for silver, 3 for gold
    r.op('SHR_P_C_PRI', 3)
    r.op('SMUL_P_C', 2)
    r.add(-1)
    r.store('sym')
    r.load('route')
    r.add(-1)
    r.cell(_pow4(p))
    r.load_alt('sym')
    r.op('SMUL', 0)                          # PRI = bits << 2 * (route - 1)
    r.store('sym')
    r.sysreq('WorkGet', WORK_SYMBOLS)
    r.load_alt('sym')
    r.op('OR', 0)
    r.store('sym')
    r.sysreq('WorkSet', WORK_SYMBOLS, 'sym')
    r.call('L30', fd.BRAIN_BONUS)            # PlayerGetBP + n -> PlayerSetBP, RecordAdd(n, 34)
    _brain_msg(r, 2)
    r.p.label(done)
    r.sysreq('WorkSet', WORK_BRAIN, 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def intro_routine(p):
    """brains_intro() -> 1 when the coming rival is a Brain on this route (its line said), else 0."""
    r = factory.Routine(p, 'brains_intro', ['b', 'route', 'm'])
    none = r.new_label('none')
    r.sysreq('WorkGet', WORK_BRAIN)
    r.store('b')
    r.op('JZER', none)
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.store('route')
    r.load('b')
    r.const_alt(7)
    r.op('AND', 0)
    r.load_alt('route')
    r.op('JNEQ', none)
    _brain_msg(r, 0)
    r.const(1)
    r.ret()
    r.p.label(none)
    r.op('ZERO_PRI', 0)
    r.ret()


BOSS_CHECK = 'L451c'          # (rank, wins + 1) -> 1 at the Maison's boss battle (20 Normal, 50 Super)
CHOOSE = 'L2b98'              # chooses (SetTrainer through 0x132c) and places the rival
PRESENT = 'L4338'             # presentation: walk-in and the trainer's start message
START_MSG = 'BattleInst_GetBattleStartMsgId'


def suppress_retail_boss(p):
    """0x451c returns 0 while WORK_ROUTE is not 0 (any Frontier facility); the Maison's own (route 0) unchanged."""
    at = factory._index(p, BOSS_CHECK)
    if p.items[at + 1].op != OP['PROC'] or p.items[at + 2].op != OP['PUSH_P_C']:
        raise ValueError('0x451c is not the retail boss check')

    def guard(b):
        b.sysreq('WorkGet', patch.WORK_ROUTE)
        b.emit('JZER', 'brains_boss_retail')
        b.emit('ZERO_PRI', 0)
        b.emit('RETN', 0)
        b.label('brains_boss_retail')
    p.items[at + 2:at + 2] = _ops(p, guard)


def _after(p, label, native):
    """Index just after the first SYSREQ_N of `native` from `label`."""
    start = factory._index(p, label)
    h = p.native(native)
    return next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
                and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == h) + 1


def install(p):
    """The Brains in a zone 517 clone run as the Tower (tower.facility_program): module docstring."""
    suppress_retail_boss(p)
    at = factory._index(p, CHOOSE)
    if p.items[at + 1].op != OP['PROC']:
        raise ValueError('0x2b98 is not a routine start')
    p.items[at + 2:at + 2] = _ops(p, lambda b: b.call('brains_check'))
    # Presentation, Singles path: skip the Maison trainer's start message (0x4398-0x43c8) for the Brain's line.
    at = _after(p, PRESENT, START_MSG) - 1
    push = p.items[at - 1]
    if push.op != OP['PUSH_P_C'] or push.args != [0]:
        raise ValueError('0x4398 is not the start message of the presentation')
    end = next(i for i in range(at, len(p.items)) if isinstance(p.items[i], Op) and p.items[i].op == OP['CALL']
               and p.items[i].args == ['L32c']) + 1
    p.items.insert(end, ('label', 'brains_intro_done'))

    def intro(b):
        b.call('brains_intro')
        b.emit('JNZ', 'brains_intro_done')
    p.items[at - 1:at - 1] = _ops(p, intro)
    # Win, before IsBoss (its only call, 0x205c).
    h = p.native('IsBoss')
    calls = [i for i, o in enumerate(p.items) if isinstance(o, Op) and o.op == OP['SYSREQ_N'] and o.args[0] == h]
    if len(calls) != 1:
        raise ValueError(f'IsBoss called {len(calls)} times')
    p.items[calls[0]:calls[0]] = _ops(p, lambda b: b.call('brains_won'))
    # Lost battle (before anything is saved) and cleanup: just after the facility's own «challenge over» WorkSet.
    work_set = p.native('WorkSet')
    for label in (factory.LOST, factory.CLEANUP):
        at = factory._index(p, label)
        first = next(i for i in range(at, len(p.items)) if isinstance(p.items[i], Op)
                     and p.items[i].op == OP['SYSREQ_N'])
        if p.items[first].args[0] != work_set:
            raise ValueError(f'{label}: the facility\'s WorkSet is not its first native')
        p.items[first + 1:first + 1] = _ops(p, lambda b: b.sysreq('WorkSet', WORK_BRAIN, 0))
    check_routine(p)
    won_routine(p)
    intro_routine(p)
    return p


# --- native (DllField.cro) ----------------------------------------------------------------------------------------

ASM = ROOT / 'frontier/asm/brains_cro.s'
FIELD_TEXT_END, FIELD_RODATA = 0xF03F0, 0xF1000      # DllField.cro .text end, .rodata start (frontier/cro.py)
DEXNAV_END = 0xF046C                                 # v0.5 DexNav routine 0xf0400-0xf046c (reports/dexnav.md)
AT = 0xF0480
SITES = {0x94F04: ('brain_choose', 0x3678), 0x94F18: ('brain_load', 0x3680), 0x95044: ('brain_start', 0x36A0)}
CODE = {'CODE_CHOOSER': 0x1E3AAC, 'CODE_LOAD': 0x1E54A0, 'CODE_START': 0x1E30B8, 'CODE_PICK': 0x1E4860,
        'CODE_LOAD_SET': patch.FUNCTIONS['LOAD_SET'], 'CODE_MAKE_PARAM': patch.FUNCTIONS['MAKE_PARAM'],
        'CODE_EV_SET': 0x3B4B64, 'CODE_GET_MAX_HP': patch.FUNCTIONS['GET_MAX_HP'],
        'CODE_SET_HP': patch.FUNCTIONS['SET_HP'], 'CODE_COPY': 0x3B2444, 'CODE_FRIENDSHIP': 0x3B47EC}
# Prologue words of the code.bin functions it calls (Repolished 1.7.6 code.bin), checked by the tests.
CODE_HEADS = {0x1E3AAC: 0xE92D41F0, 0x1E54A0: 0xE92D43F0, 0x1E30B8: 0xE92D4FF7, 0x1E4860: 0xE92D41F0,
              0x3B47EC: 0xE590000C,
              0x3B4B64: 0xE92D47F0, 0x3B2444: 0xE92D4010, 0x1EFC18: 0xE92D4030, 0x1EF904: 0xE92D4FF0,
              0x153254: 0xE92D4070, 0x14F450: 0xE92D4070}


def bl(source, target):
    return struct.pack('<I', 0xEB000000 | (((target - source - 8) >> 2) & 0xFFFFFF))


def assemble():
    """(blob linked at AT with its tables filled, {symbol: DllField.cro file offset})."""
    constants = {'WORK_ROUTE': patch.WORK_ROUTE, 'WORK_BRAIN': WORK_BRAIN, 'ROUTES': ROUTES,
                 'BOSS_STREAK': BOSS_STREAK, 'LATE_FIRST': LATE_FIRST, 'LATE_COUNT': LATE_COUNT,
                 'ARCHIVE_NORMAL': 0xB6, 'ARCHIVE_SUPER': 0xB8, 'WORK_RIVAL': patch.WORK_RIVAL[0]}
    with tempfile.TemporaryDirectory() as tmp:
        obj, elf, binary = (Path(tmp) / n for n in ('b.o', 'b.elf', 'b.bin'))
        defs = [a for k, v in constants.items() for a in ('--defsym', f'{k}={v}')]
        subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, ASM], check=True)
        syms = [f'--defsym={k}={v:#x}' for k, v in CODE.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={AT:#x}', '-e', 'brain_choose', *syms, '-o', elf, obj],
                       check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        names = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
        symbols = {n: int(a, 16) for a, t, n in (line.split() for line in names.splitlines()) if t in 'Tt'}
        blob = bytearray(binary.read_bytes())
    if AT + len(blob) != symbols['brains_cro_end']:
        raise ValueError('brains_cro.s layout')
    streaks = struct.pack(f'<{ROUTES}H', *(2 * (patch.STREAK_ROUTES[r][1] - 0x4000) for r in range(1, ROUTES + 1)))
    for name, table in (('streak_offsets', streaks), ('brain_table', brain_rows())):
        at = symbols[name] - AT
        if any(blob[at:at + len(table)]) or symbols.get(name) is None:
            raise ValueError(f'{name}: reserved space is not empty')
        blob[at:at + len(table)] = table
    if symbols['brains_cro_end'] > FIELD_RODATA:
        raise ValueError('brains_cro.s does not fit before .rodata')
    return bytes(blob), symbols


def cro_writes():
    """guarded_writes entries for DllField.cro (patch.battle_cro composes them with the Pike's bridge)."""
    blob, symbols = assemble()
    return [*(dict(offset=site, before=bl(site, thunk).hex(), after=bl(site, symbols[name]).hex())
              for site, (name, thunk) in SITES.items()),
            dict(offset=AT, before=bytes(len(blob)).hex(), after=blob.hex())]


if __name__ == '__main__':
    blob, symbols = assemble()
    print(f'brains_cro.s at DllField.cro {AT:#x}-{AT + len(blob):#x} ({len(blob)} bytes); '
          f'{FIELD_RODATA - AT - len(blob)} left before .rodata')
    print(' '.join(f'{k}={v:#x}' for k, v in sorted(symbols.items(), key=lambda kv: kv[1])))
