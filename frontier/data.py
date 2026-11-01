#!/usr/bin/env python3
"""F2: Battle Factory rental data, built from the Battle Maison archives of the dump.

Reads maisonpkN/maisontrN/maisonpkS/maisontrS (a/1/8/2-5) after checking their SHA-256, checks the tier
structure the rental levels rely on, and builds:
- RENTAL_LEVELS: set-index ranges per Factory round (Level 50), Emerald's sInitialRentalMonRanges recast
  onto the Maison tiers (frontier/PLAN.md §1);
- the Emerald constants the Factory uses (fixed IVs per round, Battle Points, Frontier Brain streaks);
- level_table(): the binary table the native code will read (layout below).

Only set indices and rules live in this file; the sets themselves are read from the dump at build time.
With --out DIR (under work/) it writes the binary table and a readable listing with species and items.
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from formats import garc_entries, rebuild_garc, sha256, text_lines, words_to_text  # noqa: E402

GAME = ROOT / 'baseline/oras/repolished/romfs'
# Unchanged by Repolished 1.7.6 (frontier/survey.py); pk3DS GARCReference_AO names.
ARCHIVES = {
    'maisonpkN': ('a/1/8/2', '7832eb86a4657ecf9756638c6a50cc32acebfbe1d6dff5f1b2d7d8270354ea4f'),
    'maisontrN': ('a/1/8/3', 'a4249c94149399b39fa91424b1e4e84c910f4f983c05ba758132e1555a4ffc04'),
    'maisonpkS': ('a/1/8/4', '46294e32f6fd9c6741cff487338def6c3f59d0ce9f8a24eb57cf7d1f11e20d57'),
    'maisontrS': ('a/1/8/5', '07aea7dc4d7ab54c55b2c955ae311b3d945d81f4ffe365fdfd84b496a6d62f33'),
}
# Archive numbers the game uses to open the set files (code.bin 0x1e3574 / 0x1e3570, reports/frontier.md §2)
ARCHIVE_ID = {'N': 0xB6, 'S': 0xB8}
GAMETEXT_ES = 'a/0/7/7'
TEXT_SPECIES, TEXT_ITEMS = 98, 114  # pk3DS TextReference GameText_AO
SPECIES_UNOWN = 201
SET_SIZE = 16

# Maison tiers (measured, checked by check_tiers): each is a list of (rank, first, last) set ranges.
# Super: four copies of the same 196 species, sets improving with the copy ("strong" pool).
SUPER_TIERS = [[('S', 52 * k, 52 * k + 20), ('S', 208 + 175 * k, 382 + 175 * k)] for k in range(4)]
# Normal: a weak pool (0-65, 66-131) and a mid pool (132-169, 170-207), two copies each.
NORMAL_TIERS = [[('N', 0, 65)], [('N', 66, 131)], [('N', 132, 169)], [('N', 170, 207)]]
# Maison trainers that pick only from one tier: the brackets of the trainer chooser at code.bin 0x1e3aac
# (Normal: streak 0-4 -> trainers 0-49, 5-9 -> 30-69, 10-14 -> 50-89, 15-18 -> 70-109; Super ×2 streak).
TRAINER_TIERS = [(0, 49), (50, 69), (70, 89), (90, 109)]

# Factory Level 50, round 1..7, then 8+ (index 7). Emerald (pokeemerald src/battle_factory.c,
# sInitialRentalMonRanges): 1 weak range, 2 copies of a mid range, 4 copies of the strong range, then
# all strong copies together. Maison equivalents: better weak copy, both mid copies, the four Super tiers.
RENTAL_LEVELS = [NORMAL_TIERS[1], NORMAL_TIERS[2], NORMAL_TIERS[3], *SUPER_TIERS,
                 [r for tier in SUPER_TIERS for r in tier]]

# Emerald constants (pokeemerald 731ad5bf).
STAGES_PER_ROUND = 7                                       # FRONTIER_STAGES_PER_CHALLENGE
LEVEL_50 = 50
# sFixedIVTable: (normal, last battle of the round). Index = round - 1, clamped (BUGFIX behaviour:
# retail reads past the table for round 9 and gets random IVs).
FIXED_IVS = [(3, 6), (6, 9), (9, 12), (12, 15), (15, 18), (21, 31), (31, 31), (31, 31)]
# sBattlePointAwards[][FRONTIER_FACILITY_FACTORY][FRONTIER_MODE_SINGLES], given when a round is won;
# index = round - 1, clamped; +10 after the Frontier Brain (frontier_util.c GiveBattlePoints).
BATTLE_POINTS = [3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9]
BRAIN_BONUS = 10
# sFrontierBrainStreakAppearances[FACTORY] = {21, 42, 21, 1}: battle 21 (silver), 42 (gold), then every 21.
BRAIN_BATTLES = (21, 42, 21)
# GetNumPastRentalsRank: rentals counted so far -> how many of the 6 rentals come from the next level.
PAST_RENTALS_RANK = [(15, 0), (22, 1), (29, 2), (36, 3), (43, 4)]  # (below, rank); 43+ -> 5
DRAFT_SIZE, PARTY_SIZE = 6, 3


def load(game=GAME):
    """{name: [entry bytes]} for the four Maison archives; refuses anything but the measured dump."""
    out = {}
    for name, (rel, expected) in ARCHIVES.items():
        path = Path(game) / rel
        if sha256(path) != expected:
            raise ValueError(f'{rel}: unexpected sha256 (not the Repolished 1.7.6 / ORAS 1.0 Maison data)')
        data = path.read_bytes()
        out[name] = [data[o:o + n] for _, _, o, n in garc_entries(data)]
    return out


def parse_set(raw):
    if len(raw) != SET_SIZE:
        raise ValueError(f'set must be {SET_SIZE} bytes')
    species, m1, m2, m3, m4, ev, nature, item, form = struct.unpack('<5HBBHH', raw)
    return {'species': species, 'moves': (m1, m2, m3, m4), 'evs': ev & 0x3F, 'nature': nature,
            'item': item, 'form': form}


def parse_trainer(raw):
    cls, count = struct.unpack_from('<HH', raw)
    if len(raw) < 4 + 2 * count:
        raise ValueError('trainer entry shorter than its set list')
    return {'class': cls, 'sets': struct.unpack_from(f'<{count}H', raw, 4)}


def indices(ranges):
    return [(rank, i) for rank, first, last in ranges for i in range(first, last + 1)]


def check_tiers(maison):
    """Assert the tier structure RENTAL_LEVELS is built on; returns the parsed sets per rank."""
    sets = {'N': [parse_set(s) for s in maison['maisonpkN']], 'S': [parse_set(s) for s in maison['maisonpkS']]}
    trainers = {'N': [parse_trainer(t) for t in maison['maisontrN']],
                'S': [parse_trainer(t) for t in maison['maisontrS']]}
    species = lambda tier: [sets[r][i]['species'] for r, i in indices(tier)]
    for tiers in (SUPER_TIERS, NORMAL_TIERS[0:2], NORMAL_TIERS[2:4]):
        first = species(tiers[0])
        assert all(species(t) == first for t in tiers), 'tier copies must list the same species in order'
        assert len(set(first)) == len(first) and 0 not in first and SPECIES_UNOWN not in first
    for rank, tiers in (('N', NORMAL_TIERS), ('S', SUPER_TIERS)):
        for (lo, hi), tier in zip(TRAINER_TIERS, tiers):
            allowed = {i for _, i in indices(tier)}
            used = {i for t in trainers[rank][lo:hi + 1] for i in t['sets']}
            assert used <= allowed, f'{rank} trainers {lo}-{hi} use sets outside their tier'
    return sets


def fixed_iv(round_no, last_battle=False):
    """Emerald GetFactoryMonFixedIV(challengeNum = round_no - 1), with the BUGFIX clamp."""
    return FIXED_IVS[min(round_no - 1, len(FIXED_IVS) - 1)][1 if last_battle else 0]


def battle_points(round_no, brain=False):
    """BP for winning round round_no (1-based)."""
    return BATTLE_POINTS[min(round_no - 1, len(BATTLE_POINTS) - 1)] + (BRAIN_BONUS if brain else 0)


def brain_battle(battle_no, symbols):
    """Frontier Brain status for overall battle battle_no (1-based): 'silver', 'gold' or None."""
    silver, gold, repeat = BRAIN_BATTLES
    if symbols == 0:
        return 'silver' if battle_no == silver else None
    if symbols == 1:
        return 'gold' if battle_no == gold else None
    if battle_no == silver:
        return 'silver'
    return 'gold' if battle_no == gold or (battle_no > gold and (battle_no - gold) % repeat == 0) else None


def rental_level(round_no):
    return RENTAL_LEVELS[min(round_no - 1, len(RENTAL_LEVELS) - 1)]


def past_rentals_rank(rents):
    return next((rank for below, rank in PAST_RENTALS_RANK if rents < below), 5)


def level_table():
    """Binary table for the native code, little endian:
    u16 level count; then per level u16 offset (bytes from table start) of its range list;
    each range list: u16 count, then count × (u16 archive id, u16 first set, u16 set count)."""
    head = struct.pack('<H', len(RENTAL_LEVELS))
    offset = len(head) + 2 * len(RENTAL_LEVELS)
    offsets, body = [], b''
    for level in RENTAL_LEVELS:
        offsets.append(offset + len(body))
        body += struct.pack('<H', len(level))
        body += b''.join(struct.pack('<HHH', ARCHIVE_ID[r], a, b - a + 1) for r, a, b in level)
    return head + struct.pack(f'<{len(offsets)}H', *offsets) + body


def read_level_table(blob):
    count = struct.unpack_from('<H', blob)[0]
    levels = []
    for off in struct.unpack_from(f'<{count}H', blob, 2):
        n = struct.unpack_from('<H', blob, off)[0]
        levels.append([struct.unpack_from('<HHH', blob, off + 2 + 6 * k) for k in range(n)])
    return levels


def names(game, index):
    data = (Path(game) / GAMETEXT_ES).read_bytes()
    entry = {e[0]: e for e in garc_entries(data)}[index]
    return [words_to_text(w) for w in text_lines(data[entry[2]:entry[2] + entry[3]])[0]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='write rental_levels.bin and rentals.txt here (under work/)')
    args = parser.parse_args()
    maison = load()
    for name, (rel, _) in ARCHIVES.items():
        data = (GAME / rel).read_bytes()
        assert rebuild_garc(data, {}) == data
        print(f'{rel} {name}: {len(maison[name])} entries, sha256 ok, unchanged rebuild identical')
    sets = check_tiers(maison)
    print('tier structure ok: Super 4×196 species-aligned, Normal 2×66 + 2×38, trainer brackets inside tiers')
    species, items = names(GAME, TEXT_SPECIES), names(GAME, TEXT_ITEMS)
    lines = []
    for n, level in enumerate(RENTAL_LEVELS, 1):
        picked = indices(level)
        kinds = {sets[r][i]['species'] for r, i in picked}
        ranges = ', '.join(f'{r} {a}-{b}' for r, a, b in level)
        label = f'round {n}' if n < len(RENTAL_LEVELS) else f'round {n}+'
        print(f'{label}: {ranges}: {len(picked)} sets, {len(kinds)} species, IV {fixed_iv(n)}/{fixed_iv(n, True)}')
        lines.append(f'== {label}: {ranges}')
        lines += [f'{r}{i:4d} {species[sets[r][i]["species"]]:12s} {items[sets[r][i]["item"]]}' for r, i in picked]
    if args.out:
        out = args.out.resolve()
        if not out.is_relative_to(ROOT / 'work'):
            parser.error('--out must be under work/ (the listing contains game data)')
        out.mkdir(parents=True, exist_ok=True)
        (out / 'rental_levels.bin').write_bytes(level_table())
        (out / 'rentals.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'wrote {out}/rental_levels.bin ({len(level_table())} bytes) and rentals.txt')


if __name__ == '__main__':
    main()
