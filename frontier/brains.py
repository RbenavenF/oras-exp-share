#!/usr/bin/env python3
"""Frontier Brains, common part (F8-CEREBROS-BASE, reports/diseno/cerebros.md §3; reports/frontier.md §39).

Appearance (pokeemerald 731ad5bf `sFrontierBrainStreakAppearances`, `GetFrontierBrainStatus`): with no symbol of
the facility the Brain comes at its silver unit, with silver only at its gold unit, with both at the silver unit
(silver team) and at the gold unit and every `period` after it (gold team). `due` is the reference; the zone script
runs the same rule (`check_routine`) before each rival is chosen, from the facility streak, so a resumed challenge
recomputes it. Facilities whose unit is not a battle (Dome, Pike, Pyramid) get their own adapter; BASE enables the
Tower initially; the adapters also enable Noland, Spenser, Greta, Tucker, Lucy and Brandon (ENABLED).

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
row: set, IV, ability slot 0 and exact EV, in order. Tucker instead uses the two distinct DOME_FORCED sets
selected from his previewed trio, in that order. Noland uses the seeded rental sets, their EV masks,
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
ENABLED = ('factory', 'tower', 'palace', 'arena', 'dome', 'pike', 'pyramid')
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
SPECIES = {'ALAKAZAM': 65, 'ENTEI': 244, 'SNORLAX': 143, 'RAIKOU': 243, 'LATIOS': 381,
           'CROBAT': 169, 'SLAKING': 289, 'LAPRAS': 131, 'ARCANINE': 59, 'SUICUNE': 245,
           'HERACROSS': 214, 'UMBREON': 197, 'SHEDINJA': 292, 'GENGAR': 94, 'BRELOOM': 286,
           'SWAMPERT': 260, 'SALAMENCE': 373, 'CHARIZARD': 6, 'METAGROSS': 376, 'LATIAS': 380, 'SEVIPER': 336, 'SHUCKLE': 213, 'MILOTIC': 350, 'STEELIX': 208, 'GYARADOS': 130,
           'REGIROCK': 377, 'REGICE': 378, 'REGISTEEL': 379, 'ARTICUNO': 144, 'ZAPDOS': 145, 'MOLTRES': 146}
MOVES = {'THUNDER_PUNCH': 9, 'FIRE_PUNCH': 7, 'ICE_PUNCH': 8, 'DISABLE': 50, 'FIRE_BLAST': 126, 'CALM_MIND': 347,
         'RETURN': 216, 'ROAR': 46, 'BODY_SLAM': 34, 'BELLY_DRUM': 187, 'YAWN': 281, 'SHADOW_BALL': 247,
         'THUNDERBOLT': 85, 'REFLECT': 115, 'REST': 156, 'PSYCHIC': 94, 'RECOVER': 105, 'DRAGON_CLAW': 337,
         'CURSE': 174,
         'CONFUSE_RAY': 109, 'DOUBLE_TEAM': 104, 'TOXIC': 92, 'FLY': 19, 'EARTHQUAKE': 89, 'SWAGGER': 207,
         'BRICK_BREAK': 280, 'ICE_BEAM': 58, 'HORN_DRILL': 32, 'PROTECT': 182, 'OVERHEAT': 315,
         'EXTREME_SPEED': 245, 'HYPER_BEAM': 63, 'BLIZZARD': 59, 'SURF': 57, 'BITE': 44,
         'MEGAHORN': 224, 'ROCK_TOMB': 317, 'ENDURE': 203, 'REVERSAL': 179, 'FAINT_ATTACK': 185,
         'AERIAL_ACE': 332, 'DOUBLE_EDGE': 38, 'HYPNOSIS': 95, 'DREAM_EATER': 138, 'DESTINY_BOND': 194,
         'SPORE': 147, 'FOCUS_PUNCH': 264, 'GIGA_DRAIN': 202, 'HEADBUTT': 29, 'COUNTER': 68, 'ROCK_SLIDE': 157, 'MIRROR_COAT': 243, 'METEOR_MASH': 309, 'CRUNCH': 242, 'POISON_FANG': 305, 'SANDSTORM': 201,
         'SLUDGE_BOMB': 188, 'EXPLOSION': 153, 'SCREECH': 103, 'DRAGON_DANCE': 349,
         'SUPERPOWER': 276, 'ANCIENT_POWER': 246, 'METAL_CLAW': 232, 'IRON_DEFENSE': 334, 'AMNESIA': 133,
         'THUNDER': 87, 'WATER_PULSE': 352, 'DETECT': 197, 'DRILL_PECK': 65, 'LIGHT_SCREEN': 113, 'SAFEGUARD': 219}
ITEMS = {'BRIGHT_POWDER': 213, 'LUM_BERRY': 157, 'QUICK_CLAW': 217, 'CHESTO_BERRY': 150,
         'SCOPE_LENS': 232, 'WHITE_HERB': 214, 'KINGS_ROCK': 221, 'SALAC_BERRY': 203, 'LEFTOVERS': 234, 'FOCUS_BAND': 230}
NATURES = {'HARDY': 0, 'LONELY': 1, 'ADAMANT': 3, 'HASTY': 11, 'MODEST': 15, 'QUIET': 17, 'JOLLY': 13, 'CALM': 20, 'BRAVE': 2, 'BOLD': 5,
           'MILD': 16}
TEAMS = {
    # Pyramid / Brandon (F8-CEREBRO-PIRAMIDE), cerebros.md §7.
    ('pyramid', SILVER): (16, [
        ('REGIROCK', 'QUICK_CLAW', 'ADAMANT', (152, 152, 0, 0, 106, 100),
         ('EXPLOSION', 'SUPERPOWER', 'EARTHQUAKE', 'ANCIENT_POWER')),
        ('REGISTEEL', 'LEFTOVERS', 'ADAMANT', (152, 152, 0, 0, 6, 200),
         ('EARTHQUAKE', 'METAL_CLAW', 'TOXIC', 'IRON_DEFENSE')),
        ('REGICE', 'CHESTO_BERRY', 'MODEST', (106, 0, 152, 0, 100, 152), ('ICE_BEAM', 'AMNESIA', 'THUNDER', 'REST'))]),
    ('pyramid', GOLD): (31, [
        ('ARTICUNO', 'SCOPE_LENS', 'MILD', (6, 0, 252, 252, 0, 0), ('BLIZZARD', 'WATER_PULSE', 'AERIAL_ACE', 'REFLECT')),
        ('ZAPDOS', 'LUM_BERRY', 'MILD', (6, 0, 252, 252, 0, 0), ('THUNDER', 'DETECT', 'DRILL_PECK', 'LIGHT_SCREEN')),
        ('MOLTRES', 'BRIGHT_POWDER', 'MILD', (6, 0, 252, 252, 0, 0),
         ('FIRE_BLAST', 'HYPER_BEAM', 'AERIAL_ACE', 'SAFEGUARD'))]),
    # Pike / Lucy (F8-CEREBRO-TUBO), cerebros.md §7.
    ('pike', SILVER): (16, [
        ('SEVIPER', 'QUICK_CLAW', 'BRAVE', (252, 0, 252, 0, 6, 0),
         ('SWAGGER', 'CRUNCH', 'POISON_FANG', 'GIGA_DRAIN')),
        # Emerald gives Shuckle 252,0,0,0,106,252 (610 EV); ORAS's EV setter 0x3b4b64 caps the total at 510, so the
        # last stat (SpD) is 152 in game. Table follows the game (reports/frontier.md §46, BITACORA 2026-11-12).
        ('SHUCKLE', 'CHESTO_BERRY', 'BOLD', (252, 0, 0, 0, 106, 152), ('TOXIC', 'SANDSTORM', 'PROTECT', 'REST')),
        ('MILOTIC', 'LEFTOVERS', 'MODEST', (152, 0, 100, 0, 152, 106), ('ICE_BEAM', 'MIRROR_COAT', 'SURF', 'RECOVER'))]),
    ('pike', GOLD): (31, [
        ('SEVIPER', 'FOCUS_BAND', 'BOLD', (252, 0, 0, 0, 252, 6),
         ('SWAGGER', 'CRUNCH', 'SLUDGE_BOMB', 'GIGA_DRAIN')),
        ('STEELIX', 'BRIGHT_POWDER', 'BRAVE', (252, 0, 0, 0, 6, 252),
         ('EARTHQUAKE', 'ROCK_SLIDE', 'EXPLOSION', 'SCREECH')),
        ('GYARADOS', 'CHESTO_BERRY', 'ADAMANT', (252, 6, 0, 0, 0, 252), ('DRAGON_DANCE', 'RETURN', 'ROAR', 'REST'))]),
    ('dome', SILVER): (20, [
        ('SWAMPERT', 'FOCUS_BAND', 'BRAVE', (152, 152, 106, 0, 100, 0), ('SURF', 'EARTHQUAKE', 'ICE_BEAM', 'COUNTER')),
        ('SALAMENCE', 'LUM_BERRY', 'ADAMANT', (152, 152, 106, 100, 0, 0),
         ('EARTHQUAKE', 'BRICK_BREAK', 'DRAGON_CLAW', 'AERIAL_ACE')),
        ('CHARIZARD', 'WHITE_HERB', 'QUIET', (100, 152, 106, 152, 0, 0),
         ('OVERHEAT', 'ROCK_SLIDE', 'AERIAL_ACE', 'EARTHQUAKE'))]),
    ('dome', GOLD): (31, [
        ('SWAMPERT', 'LEFTOVERS', 'BRAVE', (252, 252, 6, 0, 0, 0), ('SURF', 'EARTHQUAKE', 'ICE_BEAM', 'MIRROR_COAT')),
        ('METAGROSS', 'QUICK_CLAW', 'BRAVE', (252, 252, 6, 0, 0, 0), ('PSYCHIC', 'METEOR_MASH', 'EARTHQUAKE', 'PROTECT')),
        ('LATIAS', 'CHESTO_BERRY', 'MODEST', (252, 0, 252, 6, 0, 0), ('THUNDERBOLT', 'PSYCHIC', 'CALM_MIND', 'REST'))]),
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
    # Palace / Spenser (F8-CEREBRO-PALACIO)
    ('palace', SILVER): (16, [
        ('CROBAT', 'BRIGHT_POWDER', 'ADAMANT', (152, 0, 0, 152, 100, 106),
         ('CONFUSE_RAY', 'DOUBLE_TEAM', 'TOXIC', 'FLY')),
        ('SLAKING', 'SCOPE_LENS', 'HARDY', (152, 152, 0, 106, 100, 0),
         ('EARTHQUAKE', 'SWAGGER', 'SHADOW_BALL', 'BRICK_BREAK')),
        ('LAPRAS', 'QUICK_CLAW', 'QUIET', (0, 0, 252, 0, 106, 152), ('ICE_BEAM', 'HORN_DRILL', 'CONFUSE_RAY', 'PROTECT'))]),
    ('palace', GOLD): (31, [
        ('ARCANINE', 'WHITE_HERB', 'HASTY', (6, 252, 252, 0, 0, 0), ('OVERHEAT', 'EXTREME_SPEED', 'ROAR', 'PROTECT')),
        ('SLAKING', 'SCOPE_LENS', 'HARDY', (6, 252, 0, 252, 0, 0), ('HYPER_BEAM', 'EARTHQUAKE', 'SHADOW_BALL', 'YAWN')),
        ('SUICUNE', 'KINGS_ROCK', 'HASTY', (252, 0, 252, 6, 0, 0), ('BLIZZARD', 'SURF', 'BITE', 'CALM_MIND'))]),
    # Arena / Greta (F8-CEREBRO-ARENA)
    ('arena', SILVER): (20, [
        ('HERACROSS', 'SALAC_BERRY', 'JOLLY', (106, 152, 0, 152, 0, 100),
         ('MEGAHORN', 'ROCK_TOMB', 'ENDURE', 'REVERSAL')),
        ('UMBREON', 'LEFTOVERS', 'CALM', (152, 0, 100, 0, 152, 106),
         ('BODY_SLAM', 'CONFUSE_RAY', 'PSYCHIC', 'FAINT_ATTACK')),
        ('SHEDINJA', 'BRIGHT_POWDER', 'ADAMANT', (0, 252, 6, 252, 0, 0),
         ('SHADOW_BALL', 'RETURN', 'CONFUSE_RAY', 'AERIAL_ACE'))]),
    ('arena', GOLD): (31, [
        ('UMBREON', 'CHESTO_BERRY', 'CALM', (252, 0, 0, 0, 252, 6),
         ('DOUBLE_EDGE', 'CONFUSE_RAY', 'REST', 'PSYCHIC')),
        ('GENGAR', 'LEFTOVERS', 'MODEST', (252, 0, 252, 0, 6, 0),
         ('PSYCHIC', 'HYPNOSIS', 'DREAM_EATER', 'DESTINY_BOND')),
        ('BRELOOM', 'LUM_BERRY', 'JOLLY', (6, 252, 0, 252, 0, 0),
         ('SPORE', 'FOCUS_PUNCH', 'GIGA_DRAIN', 'HEADBUTT'))]),
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
# Second block, after the 4 * ROUTES lines of KEYS (added by F8-CEREBRO-FABRICA, so the lines above keep their numbers):
# the Brain's line when it wins (the player lost) and the receptionist's answer to «Symbols» by the route's symbols.
MORE_KEYS = ('lost', 'symbol_none', 'symbol_silver', 'symbol_gold')
MORE = len(KEYS) * ROUTES     # first line of MORE_KEYS from line_base()
LINE_SYMBOLS_OPTION = {'es': 'Símbolos', 'en': 'Symbols'}   # reception menu entry (text 619, factory.LINE_SYMBOLS)
MENU_SYMBOLS = 5              # its menu value (retail 0-3, the Factory's 4)


def lines(lang):
    """Text 637 lines of the Brains, from LINE_BASE: KEYS per route 1..7, then MORE_KEYS per route 1..7."""
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
    for route in range(1, ROUTES + 1):
        f = patch.STREAK_ROUTES[route][0]
        name, symbol, place = NAMES[f], SYMBOL[code][f], FACILITY[code][f]
        if code == 'es':
            out += [f'¡Buen combate! Pero aún te queda\nmucho por aprender. Te espero\nde nuevo en {place}.',
                    f'Aún no tienes el Símbolo {symbol}\nde {place}.',
                    f'Tienes el Símbolo {symbol} de plata\nde {place}.',
                    f'Tienes el Símbolo {symbol} de oro\nde {place}.']
        else:
            out += [f'A good battle! But you still have\nmuch to learn. I will be waiting\nfor you at {place}.',
                    f"You don't have the {symbol} Symbol\nof {place} yet.",
                    f'You have the silver {symbol} Symbol\nof {place}.',
                    f'You have the gold {symbol} Symbol\nof {place}.']
    import dome
    return out + dome.brain_preview_lines(lang)


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


def check_routine(p, streak_work=None, offset=1):
    """brains_check(): WORK_BRAIN for the coming battle (module docstring); 0 when none. The unit is the facility's
    streak (GetMyWinCount, or saved work `streak_work`) + `offset`: the Pyramid calls it after counting the floor."""
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
    if streak_work is None:
        r.sysreq('GetMyWinCount', 0, 0)     # the facility's streak (WORK_ROUTE set)
    else:
        r.sysreq('WorkGet', streak_work)
    if offset:
        r.add(offset)
    r.store('unit')
    ordinary = r.new_label('battle_unit')
    r.load('route')
    r.op('EQ_P_C_PRI', patch.ROUTE['dome'])
    r.op('JZER', ordinary)
    # Dome appearance units are tournaments: only their fourth battle is eligible.
    r.load('unit')
    r.op('MOVE_ALT', 0)
    r.const(4)
    r.op('SDIV_ALT', 0)
    r.store('unit')
    r.op('MOVE_PRI', 0)                  # remainder
    r.op('JNZ', none)
    r.p.label(ordinary)
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


def lost_routine(p):
    """brains_lost(): on the lost-battle path, the Brain's line when it was due on the current route; WORK_BRAIN = 0."""
    r = factory.Routine(p, 'brains_lost', ['b', 'route', 'm'])
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
    r.load('route')                          # MORE + 4 * (route - 1) + 0
    r.op('SMUL_P_C', 4)
    r.add(MORE - 4)
    r.store('m')
    r.sysreq('WorkSet', WORK_MSG, 'm')
    r.sysreq('GlobalCall', GLOBAL_SAY)
    r.p.label(done)
    r.sysreq('WorkSet', WORK_BRAIN, 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def symbols_routine(p, facility):
    """brains_symbols(): the receptionist says which of `facility`'s symbols the player has (2 read as 3)."""
    route = route_of(facility)
    r = factory.Routine(p, 'brains_symbols', ['s'])
    one = r.new_label('one')
    r.sysreq('WorkGet', WORK_SYMBOLS)
    if route > 1:
        r.op('SHR_P_C_PRI', 2 * (route - 1))
    r.const_alt(3)
    r.op('AND', 0)
    r.store('s')
    r.op('SHR_P_C_PRI', 1)
    r.op('JZER', one)
    r.const(2)                               # 2 or 3: gold
    r.store('s')
    r.p.label(one)
    r.load('s')
    r.add(MORE + 4 * (route - 1) + 1)
    r.store('s')
    r.sysreq('WorkSet', WORK_MSG, 's')
    r.sysreq('GlobalCall', GLOBAL_SAY)
    r.op('ZERO_PRI', 0)
    r.ret()


def symbols_option(p, facility, line):
    """«Symbols» in a zone 517 clone's reception menu (text 619 line `line`, value MENU_SYMBOLS), before the last
    entry («Nothing»); choosing it says brains_symbols and goes back to the menu, as the information options."""
    start, native = factory._index(p, 'L14f4'), p.native('ListMenuAdd')
    adds = [i for i in range(start, factory._index(p, factory.RECEPTION_RESULT)) if isinstance(p.items[i], Op)
            and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == native]
    last = adds[-1]
    first = last
    while not (isinstance(p.items[first - 1], Op) and p.items[first - 1].op == OP['SYSREQ_N']):
        first -= 1                           # back to the last entry's first push
    p.items[first:first] = _ops(p, lambda b: b.sysreq('ListMenuAdd', line, MENU_SYMBOLS, 0))
    at = factory._index(p, factory.RECEPTION_RESULT)

    def dispatch(b):
        b.emit('LOAD_P_S_PRI', -12)
        b.emit('EQ_P_C_PRI', MENU_SYMBOLS)
        b.emit('JZER', 'brains_symbols_not_chosen')
        b.call('brains_symbols')
        b.emit('CONST_S', factory.RECEPTION_AGAIN, 1)
        b.emit('JUMP', factory.RECEPTION_NEXT)
        b.label('brains_symbols_not_chosen')
    p.items[at + 1:at + 1] = _ops(p, dispatch)
    symbols_routine(p, facility)
    return p


BOSS_CHECK = 'L451c'         # (rank, wins + 1) -> 1 at the Maison's boss battle (20 Normal, 50 Super)
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
    for label, ops in ((factory.LOST, lambda b: b.call('brains_lost')),
                       (factory.CLEANUP, lambda b: b.sysreq('WorkSet', WORK_BRAIN, 0))):
        at = factory._index(p, label)
        first = next(i for i in range(at, len(p.items)) if isinstance(p.items[i], Op)
                     and p.items[i].op == OP['SYSREQ_N'])
        if p.items[first].args[0] != work_set:
            raise ValueError(f'{label}: the facility\'s WorkSet is not its first native')
        p.items[first + 1:first + 1] = _ops(p, ops)
    check_routine(p)
    won_routine(p)
    intro_routine(p)
    lost_routine(p)
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
        'CODE_SET_HP': patch.FUNCTIONS['SET_HP'], 'CODE_COPY': 0x3B2444, 'CODE_FRIENDSHIP': 0x3B47EC,
        'CODE_WIN_GET': 0x45CEE8}          # Maison GetWinCount(base, type, rank): through F9's mode banks
# Prologue words of the code.bin functions it calls (Repolished 1.7.6 code.bin), checked by the tests.
CODE_HEADS = {0x1E3AAC: 0xE92D41F0, 0x1E54A0: 0xE92D43F0, 0x1E30B8: 0xE92D4FF7, 0x1E4860: 0xE92D41F0,
              0x3B47EC: 0xE590000C, 0x45CEE8: 0xE3520000,
              0x3B4B64: 0xE92D47F0, 0x3B2444: 0xE92D4010, 0x1EFC18: 0xE92D4030, 0x1EF904: 0xE92D4FF0,
              0x153254: 0xE92D4070, 0x14F450: 0xE92D4070}


def bl(source, target):
    return struct.pack('<I', 0xEB000000 | (((target - source - 8) >> 2) & 0xFFFFFF))


def assemble():
    """(blob linked at AT with its tables filled, {symbol: DllField.cro file offset})."""
    constants = {'WORK_ROUTE': patch.WORK_ROUTE, 'WORK_BRAIN': WORK_BRAIN, 'ROUTES': ROUTES,
                 'BOSS_STREAK': BOSS_STREAK, 'LATE_FIRST': LATE_FIRST, 'LATE_COUNT': LATE_COUNT,
                 'ARCHIVE_NORMAL': 0xB6, 'ARCHIVE_SUPER': 0xB8, 'WORK_RIVAL': patch.WORK_RIVAL[0],
                 'DOME_FORCED': patch.DOME_FORCED[0], 'MAISON_TO_WORKS': patch.CONSTANTS['MAISON_TO_WORKS']}
    code = {**CODE, 'CODE_MODE_LEVEL': patch.assemble()[1]['mode_level']}   # F9 (frontier/asm/modes.s)
    with tempfile.TemporaryDirectory() as tmp:
        obj, elf, binary = (Path(tmp) / n for n in ('b.o', 'b.elf', 'b.bin'))
        defs = [a for k, v in constants.items() for a in ('--defsym', f'{k}={v}')]
        subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, ASM], check=True)
        syms = [f'--defsym={k}={v:#x}' for k, v in code.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={AT:#x}', '-e', 'brain_choose', *syms, '-o', elf, obj],
                       check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        names = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
        symbols = {n: int(a, 16) for a, t, n in (line.split() for line in names.splitlines()) if t in 'Tt'}
        blob = bytearray(binary.read_bytes())
    if AT + len(blob) != symbols['brains_cro_end']:
        raise ValueError('brains_cro.s layout')
    for name, table in (('brain_table', brain_rows()),):
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
