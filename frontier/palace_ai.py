"""Battle Palace stage C: nature-driven move groups for the AI of the player's Pokemon (reports/frontier.md §36).

Rules: pret/pokeemerald 731ad5bf.
- src/battle_gfx_sfx_util.c ChooseMoveAndTargetInBattlePalace: percent = Random() % 100; column 0 if HP is above
  half, column 1 if maxHP / 2 >= hp; group = attack if percent < odds[0], defense if < odds[1], else support; only
  moves of that group (with PP) go to the AI. If none, Emerald picks among the other groups (and may «not obey»,
  which is out of scope here): our AI keeps every usable move, which all belong to other groups.
- GetBattlePalaceMoveGroup: target SELECTED / USER_OR_SELECTED / RANDOM / BOTH / FOES_AND_ALLY -> support if
  power 0, else attack; DEPENDS / OPPONENTS_FIELD -> support; USER -> defense; anything else -> attack.
- src/battle_script_commands.c:855 gBattlePalaceNatureToMoveGroupLikelihood with PALACE_STYLE(atk, def, atkLow,
  defLow) = {atk, atk + def, atkLow, atkLow + defLow} (copied below, sha256 of that file e0847cd2…).

The group per move is generated from the ORAS move data (GARC a/1/8/9, pk3DS Move6: power 0x03, target 0x14,
MoveTarget enum) by mapping the Gen 6 targets to Emerald's: calibrated on moves 1-354, where it agrees with
GetBattlePalaceMoveGroup on Emerald's own data except for EMERALD_OVERRIDES (measured 2026-11-11 against
src/data/battle_moves.h of the same commit; §36).
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from formats import garc_entries, sha256  # noqa: E402

MOVES_GARC = ROOT / 'baseline/oras/repolished/romfs/a/1/8/9'
MOVES_GARC_SHA256 = '426aaeb0d3fd228acfaf103c496bfdd8fe9c97e58daacdb3c8d8dd573dc446cf'   # = retail ORAS 1.0
MOVE_SIZE, POWER, TARGET = 0x24, 0x03, 0x14
ATTACK, DEFENSE, SUPPORT = 0, 1, 2

# pk3DS MoveTarget (Gen 6) -> Emerald group. None: by power (0 support, else attack), as Emerald's
# SELECTED/USER_OR_SELECTED/RANDOM/BOTH/FOES_AND_ALLY.
TARGET_GROUP = {
    0: None,        # AnyExceptSelf      (Emerald SELECTED)
    1: None,        # AllyOrSelf         (USER_OR_SELECTED)
    2: DEFENSE,     # Ally               (Helping Hand: Emerald USER)
    3: None,        # Opponent
    4: None,        # AllAdjacent        (FOES_AND_ALLY)
    5: None,        # AllAdjacentOpponents (BOTH)
    6: DEFENSE,     # AllAllies          (Emerald USER)
    7: DEFENSE,     # Self               (USER)
    8: DEFENSE,     # All: weather, Haze (Emerald USER)
    9: None,        # RandomOpponent     (RANDOM)
    10: DEFENSE,    # SideAll            (Emerald USER)
    11: SUPPORT,    # SideOpponent       (OPPONENTS_FIELD)
    12: DEFENSE,    # SideSelf: Reflect  (Emerald USER)
    13: SUPPORT,    # Counter            (DEPENDS)
}
# Moves 1-354 whose Gen 6 target differs from Emerald's kind: Emerald's group wins.
EMERALD_OVERRIDES = {
    118: SUPPORT,   # Metronome     (Gen 6 Self, Emerald DEPENDS)
    176: DEFENSE,   # Conversion 2  (Gen 6 AnyExceptSelf, Emerald USER)
    214: SUPPORT,   # Sleep Talk    (DEPENDS)
    274: SUPPORT,   # Assist        (DEPENDS)
    277: SUPPORT,   # Magic Coat    (DEPENDS)
    289: SUPPORT,   # Snatch        (DEPENDS)
}

# gBattlePalaceNatureToMoveGroupLikelihood, PALACE_STYLE arguments (atk, def, atkLow, defLow), natures in index
# order Hardy..Quirky (the same order in Gen 6, PK6 0x1C).
EMERALD_STYLES = [
    (61, 7, 61, 7), (20, 25, 84, 8), (70, 15, 32, 60), (38, 31, 70, 15), (20, 70, 70, 22),
    (30, 20, 32, 58), (56, 22, 56, 22), (25, 15, 75, 15), (69, 6, 28, 55), (35, 10, 29, 6),
    (62, 10, 30, 20), (58, 37, 88, 6), (34, 11, 29, 11), (35, 5, 35, 60), (56, 22, 56, 22),
    (35, 45, 34, 60), (44, 50, 34, 6), (56, 22, 56, 22), (30, 58, 30, 58), (30, 13, 27, 6),
    (40, 50, 25, 62), (18, 70, 90, 5), (88, 6, 22, 20), (42, 50, 42, 5), (56, 22, 56, 22),
]
NATURE_ODDS = [(a, a + d, al, al + dl) for a, d, al, dl in EMERALD_STYLES]   # cumulative, as Emerald stores them
NATURES = len(NATURE_ODDS)

# DllBattle.cro (v0.5) file offsets.
SITE = 0xD468                     # `bl 0xe044` in the AI proc of command 3 (0xd0c8)
SITE_BEFORE = bytes.fromhex('f50200eb')   # bl 0xe044 (relative, no relocation)
TEXT_END, RODATA = 0xD7628, 0xD8000       # declared .text end and .rodata start; CRO code region 0x180-0xe7000
AT = 0xD7630                      # where palace_cro.s is linked (16-aligned, after .text)
CRO_FUNCTIONS = {'CRO_USABLE_MOVES': 0xE044, 'CRO_RAND': 0x490}
CODE_NATURE = 0x152F08            # code.bin CoreParam nature getter (decrypt, block A +0x14, encrypt)
ASM = ROOT / 'frontier/asm/palace_cro.s'


def moves(path=MOVES_GARC):
    """Move records of the WD pack in a/1/8/9 (622 for ORAS)."""
    if sha256(path) != MOVES_GARC_SHA256:
        raise ValueError(f'{path}: unexpected sha256 (not the ORAS 1.0 move data)')
    data = Path(path).read_bytes()
    _, _, offset, length = garc_entries(data)[0]
    pack = data[offset:offset + length]
    if pack[:2] != b'WD':
        raise ValueError('a/1/8/9 is not a WD pack')
    count = struct.unpack_from('<H', pack, 2)[0]
    offsets = struct.unpack_from(f'<{count + 1}I', pack, 4)
    return [pack[offsets[i]:offsets[i + 1]] for i in range(count)]


def group_of(record, move_id=None):
    if move_id in EMERALD_OVERRIDES:
        return EMERALD_OVERRIDES[move_id]
    group = TARGET_GROUP.get(record[TARGET])
    if group is None:
        return SUPPORT if record[POWER] == 0 else ATTACK
    return group


def move_groups(path=MOVES_GARC):
    return [group_of(record, move_id) for move_id, record in enumerate(moves(path))]


def pack_groups(groups):
    out = bytearray((len(groups) + 3) // 4)
    for move_id, group in enumerate(groups):
        out[move_id >> 2] |= group << (2 * (move_id & 3))
    return bytes(out)


def pack_odds():
    return bytes(b for row in NATURE_ODDS for b in row)


def assemble(groups=None):
    """(blob linked at AT with both tables filled, {symbol: CRO file offset})."""
    groups = move_groups() if groups is None else groups
    import palace_engine as pe
    constants = {'PALACE_RULE': pe.RULE, 'NATURES': NATURES, 'MOVES': len(groups), 'CODE_NATURE': CODE_NATURE}
    with tempfile.TemporaryDirectory() as tmp:
        obj, elf, binary = (Path(tmp) / n for n in ('c.o', 'c.elf', 'c.bin'))
        defs = [a for k, v in constants.items() for a in ('--defsym', f'{k}={v}')]
        subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, ASM], check=True)
        syms = [f'--defsym={k}={v:#x}' for k, v in CRO_FUNCTIONS.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={AT:#x}', '-e', 'palace_moves', *syms, '-o', elf, obj],
                       check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        names = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
        symbols = {n: int(a, 16) for a, t, n in (line.split() for line in names.splitlines()) if t == 'T'}
        blob = bytearray(binary.read_bytes())
    if symbols['palace_moves'] != AT or AT + len(blob) != symbols['palace_cro_end']:
        raise ValueError('palace_cro.s layout')
    for name, table in (('palace_nature_odds', pack_odds()), ('palace_move_groups', pack_groups(groups))):
        at = symbols[name] - AT
        if any(blob[at:at + len(table)]):
            raise ValueError(f'{name}: reserved space is not empty')
        blob[at:at + len(table)] = table
    if symbols['palace_cro_end'] > RODATA:
        raise ValueError('palace_cro.s does not fit before .rodata')
    return bytes(blob), symbols


def bl(source, target):
    return struct.pack('<I', 0xEB000000 | (((target - source - 8) >> 2) & 0xFFFFFF))


def cro_writes():
    blob, symbols = assemble()
    return [dict(offset=SITE, before=SITE_BEFORE.hex(), after=bl(SITE, symbols['palace_moves']).hex()),
            dict(offset=AT, before=bytes(len(blob)).hex(), after=blob.hex())]


def cro_ranges():
    blob, _ = assemble()
    return [(SITE, SITE + 4), (AT, AT + len(blob))]


if __name__ == '__main__':
    blob, symbols = assemble()
    groups = move_groups()
    print(f'palace_cro.s at DllBattle.cro {AT:#x}-{AT + len(blob):#x} ({len(blob)} bytes, code '
          f'{symbols["palace_nature_odds"] - AT}); padding {TEXT_END:#x}-{RODATA:#x} ({RODATA - TEXT_END} bytes), '
          f'{RODATA - AT - len(blob)} left after it')
    print('groups:', {name: groups.count(g) for name, g in (('attack', 0), ('defense', 1), ('support', 2))})
    print(' '.join(f'{k}={v:#x}' for k, v in sorted(symbols.items(), key=lambda kv: kv[1])))
