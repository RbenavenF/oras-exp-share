#!/usr/bin/env python3
"""Battle Frontier groundwork: reproduce the measured facts frontier/PLAN.md relies on. Read-only.

Reads the Repolished baseline (baseline/oras/repolished/romfs) and prints:
- the Battle Maison data archives (pk3DS GARCReference_AO numbers) with their entry counts and Repolished status;
- the zones whose header points to the Battle Resort story texts (ES storytext entry 615-634);
- the natives each Battle Maison zone script calls, and which retail scripts use the party/box natives.
With --listings DIR it also writes the disassembly of those zone scripts (DIR must be under work/).
"""
import argparse
import collections
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'faraway'))
from formats import garc_entries, sha256, text_lines, words_to_text  # noqa: E402
from pawn import Script, listing, native_names  # noqa: E402
import build as fb  # noqa: E402

GAME = ROOT / 'baseline/oras/repolished/romfs'
CLEAN = ROOT / 'baseline/oras/clean/romfs'
NATIVES = ROOT / 'tools/CTRMap-F5/src/ctrmap/resources/oras_natives.tsv'
MAISON_GARCS = {'a/1/8/2': 'maisonpkN', 'a/1/8/3': 'maisontrN', 'a/1/8/4': 'maisonpkS', 'a/1/8/5': 'maisontrS'}
STORYTEXT_ES = 'a/0/8/5'
ZONE_HEADER_TEXT = 6           # u16 story text id in the zone header (zone 317 -> 523, as faraway/event.py notes)
RESORT_TEXTS = range(615, 635)   # neighbours of 619 (Maison welcome); not all are Resort zones
PARTY_NATIVES = ('PokePartyAdd', 'PokePartyAddParam', 'PokePartySetParam', 'PokePartyToBox', 'BoxAddPoke')


def zones():
    count = len(garc_entries((GAME / 'a/0/1/3').read_bytes()))
    for zone in range(count):
        try:
            yield zone, fb.zone_files(GAME, zone)
        except ValueError:      # a few entries are not LZ11 zone containers
            continue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--listings', type=Path)
    args = parser.parse_args()
    names = native_names(NATIVES)

    print('== Battle Maison archives')
    for path, name in MAISON_GARCS.items():
        data = (GAME / path).read_bytes()
        same = sha256(GAME / path) == sha256(CLEAN / path)
        print(f'{path} {name}: {len(set(e[0] for e in garc_entries(data)))} entries, '
              f'{"unchanged by" if same else "CHANGED by"} Repolished')

    print('== Zones whose story text is 615-634 (ES first line)')
    story = (GAME / STORYTEXT_ES).read_bytes()
    entries = {e[0]: e for e in garc_entries(story)}
    resort = {}
    for zone, files in zones():
        text = struct.unpack_from('<H', files[0], ZONE_HEADER_TEXT)[0]
        if text in RESORT_TEXTS:
            _, _, offset, length = entries[text]
            lines = text_lines(story[offset:offset + length])[0]
            first = words_to_text(lines[0]).replace('\n', ' ')[:60] if lines else '(no lines)'
            resort[zone] = files
            print(f'zone {zone}: text {text} "{first}"')

    print('== Natives called by the Battle Maison scripts')
    for zone in (516, 517):
        lst = listing(Script.parse(resort[zone][2]), names)
        calls = collections.Counter(re.findall(r'SYSREQ\S*\s+([A-Za-z_0-9]+)', lst))
        maison = sorted(n for n in calls if n.startswith(('BattleHouse', 'BattleInst')) or n in (
            'StartBattle', 'SetTrainer', 'IsWin', 'AddWinCount', 'ClearWinCount', 'GetWinCount', 'GetMyWinCount',
            'IsBoss', 'GetRank', 'PlayerGetBP', 'PlayerSetBP', 'SetupAiPartner', 'SelectPartner'))
        print(f'zone {zone}: {len(lst.splitlines())} lines, {len(calls)} natives; facility natives: {maison}')
        if args.listings:
            out = args.listings.resolve()
            if not out.is_relative_to(ROOT / 'work'):
                parser.error('--listings must be under work/')
            out.mkdir(parents=True, exist_ok=True)
            (out / f'zone{zone}.lst').write_text(lst + '\n')

    print('== Retail uses of the party/box natives')
    uses = collections.Counter()
    for zone, files in zones():
        try:
            lst = listing(Script.parse(files[2]), names)
        except Exception:       # a script that does not decode is simply not counted
            continue
        for native in PARTY_NATIVES:
            uses[native, f'zone{zone}'] += len(re.findall(rf'\b{native}\b', lst))
    shared = (GAME / 'a/0/2/9').read_bytes()
    for entry, _, offset, length in garc_entries(shared):
        try:
            lst = listing(Script.parse(shared[offset:offset + length]), names)
        except Exception:
            continue
        for native in PARTY_NATIVES:
            uses[native, f'shared{entry}'] += len(re.findall(rf'\b{native}\b', lst))
    for native in PARTY_NATIVES:
        where = [f'{w}x{n}' for (k, w), n in sorted(uses.items()) if k == native and n]
        print(f'{native}: {", ".join(where) or "no retail use"}')
    box = sorted({v for v in names.values() if re.search(r'Box|Temoti', v)})
    print(f'box natives in the table: {box}')


if __name__ == '__main__':
    main()
