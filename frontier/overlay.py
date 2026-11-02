#!/usr/bin/env python3
"""Battle Factory build: the Battle Maison zone script (517) changes, its texts and the code.bin patch.

Current scope (F4, in progress):
- the receptionist's «Battle Factory» option (zone 517) and the draft of 6 rentals and choice of 3 in shared
  script 5 (a/0/2/9), with its texts in a new story text entry (frontier/factory.py);
- while the Factory is active (saved work patch.WORK_IV != 0) the Maison's party selection routine
  (script 517 0x457c, BattleHouse_CallPartySelectApp) is skipped and answers "accepted" (work 0x800C = 1),
  and the code.bin hook (frontier/patch.py) builds the battle party from the rentals.

Inputs come from --romfs, file by file, falling back to the Repolished baseline (the laboratory passes the
Faraway dev overlay's, which carries the Route 102 warp and v0.5's texts): a/0/1/3, checked by SHA-256 of its
zone 517 entry (only zone 517's script, ZO file 2, is replaced); a/0/2/9, checked by SHA-256 of entry 5;
the story texts a/0/7/9-a/0/8/6 (text 619 must have factory.TEXT_LINES lines and gets one; the archive must
have patch.TEXT_FACTORY entries and gets the new one) and the game texts a/0/7/1-8 (species and item names).
Output under work/: romfs/a/0/1/3, romfs/a/0/2/9, the eight story texts and code.ips.

Usage: python frontier/overlay.py --out work/frontier/build [--romfs DIR]
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from formats import (build_text, garc_entries, lz11_compress, lz11_decompress, rebuild_garc,  # noqa: E402
                     text_to_words, zo_build, zo_files)
from pawn import OP, Op, Program, Script  # noqa: E402
import build_patch  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import patch  # noqa: E402

ROMFS = ROOT / 'baseline/oras/repolished/romfs'
ZONES = ROMFS / 'a/0/1/3'
ZONE_MAISON = 517
# Zone 517's ZO container, decompressed: identical in ORAS 1.0, Repolished 1.7.6, v0.5 and the Faraway overlay.
ZONE_MAISON_SHA256 = 'bf788f5f6aec3d24c0d387b6a8bd93e08c5e84735f555bce9cf4042a33708a75'
SHARED = 'a/0/2/9'
SHARED_SHA256 = 'c033e5aada96b53d66521c09325cffe16b2bdf7e64971fec1d6d85dd95839605'  # entry 5, Repolished 1.7.6
PARTY_SELECT = 0x457C        # PROC: BattleHouse_CallPartySelectApp(arg, 0x800C), returns work 0x800C
WORK_SELECT_RESULT = 0x800C


def maison_script(script):
    """Zone 517 script with the Factory reception and the skip at the start of the party selection routine."""
    return maison_program(script).build_script(f'L{script.main:x}')


def maison_program(script):
    p = Program.from_script(script)
    entry = p.items.index(('label', f'L{PARTY_SELECT:x}'))
    if not (isinstance(p.items[entry + 1], Op) and p.items[entry + 1].op == OP['PROC']):
        raise ValueError('0x457c is not a routine start')
    body = Program(script)
    body.native_hashes = p.native_hashes   # share the native table
    body.sysreq('WorkGet', patch.WORK_IV)
    body.emit('JZER', 'factory_select_retail')
    body.sysreq('WorkSet', WORK_SELECT_RESULT, 1)
    body.emit('CONST_P_PRI', 1)
    body.emit('RETN', 0)
    body.label('factory_select_retail')
    p.items[entry + 2:entry + 2] = body.items
    factory.reception(p)
    return p


def rentals(game=ROMFS):
    """(sets by rank, slot table, level slot ranges, slot cells), checked."""
    sets = fd.check_tiers(fd.load(game))
    table, levels = factory.slots()
    factory.check_draws(sets, table, levels)
    return sets, table, levels, factory.slot_cells(sets, table)


def source(romfs, rel):
    path = Path(romfs) / rel
    return (path if path.exists() else ROMFS / rel).read_bytes()


def texts(romfs, sets, table):
    """{romfs path: story text archive}: the option line appended to text 619 and the new Factory text entry."""
    out = {}
    for lang, path in factory.STORYTEXT.items():
        data = source(romfs, path)
        if len(garc_entries(data)) != patch.TEXT_FACTORY:
            raise ValueError(f'{path}: expected {patch.TEXT_FACTORY} text entries')
        spec = {'path': path, 'texts': [{'entry': factory.TEXT_ZONE, 'line': factory.TEXT_LINES, 'append': True,
                                         'after': factory.OPTION[factory.LANG[lang]]}]}
        data = build_patch.guarded_texts(data, spec)
        lines = factory.lines_for(lang, source(romfs, factory.GAMETEXT[lang]), sets, table)
        words = [text_to_words(line) for line in lines]
        out[path] = rebuild_garc(data, {}, append=[build_text(words, [0] * len(words))])
    return out


def shared(romfs, zone_script, cells, levels):
    """(shared script archive, new shared script 5)."""
    data = source(romfs, SHARED)
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    raw = data[offset:offset + length]
    if hashlib.sha256(raw).hexdigest() != SHARED_SHA256:
        raise ValueError(f'{SHARED} entry {factory.SHARED_SCRIPT} differs from Repolished 1.7.6')
    retail = Script.parse(raw)
    if retail.build(pad=False) != raw:
        raise ValueError('shared script 5 does not round-trip')
    program = factory.shared_program(retail, zone_script, cells, levels)
    script = program.build_script(f'L{retail.main:x}').build(pad=False)
    return rebuild_garc(data, {(factory.SHARED_SCRIPT, 0): script}), script


def maison_retail(data):
    """(ZO files, retail script) of zone 517 from a zone archive, checked."""
    _, _, offset, length = garc_entries(data)[ZONE_MAISON]
    container = lz11_decompress(data[offset:offset + length])
    digest = hashlib.sha256(container).hexdigest()
    if digest != ZONE_MAISON_SHA256:
        raise ValueError(f'zone {ZONE_MAISON} differs from Repolished 1.7.6 ({digest[:16]}…)')
    files = zo_files(container)
    retail = Script.parse(files[2])
    if retail.build() != files[2]:
        raise ValueError('zone 517 script does not round-trip')
    return files, retail


def build(romfs=ROMFS):
    """{romfs path: archive} for a/0/1/3, a/0/2/9 and the story texts; (zone 517 script, shared script 5)."""
    sets, table, levels, cells = rentals()
    data = source(romfs, 'a/0/1/3')
    files, retail = maison_retail(data)
    offset = garc_entries(data)[ZONE_MAISON][2]
    files[2] = maison_script(retail).build()
    entry = next((e, s) for e, s, o, n in garc_entries(data) if o == offset)
    out = {'a/0/1/3': rebuild_garc(data, {entry: lz11_compress(zo_build(files))})}
    out[SHARED], script5 = shared(romfs, retail, cells, levels)
    out.update(texts(romfs, sets, table))
    return out, (files[2], script5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--romfs', type=Path, default=ROMFS)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game data)')
    archives, (zone_script, script5) = build(args.romfs)
    code, hook, _ = patch.build()
    if out.exists():
        shutil.rmtree(out)
    for path, blob in archives.items():
        (out / 'romfs' / path).parent.mkdir(parents=True, exist_ok=True)
        (out / 'romfs' / path).write_bytes(blob)
    clean = patch.CLEAN.read_bytes()
    (out / 'code.ips').write_bytes(patch.diff_ips(clean, code))
    container = len(zo_build(zo_files(lz11_decompress(next(
        archives['a/0/1/3'][o:o + n] for e, _, o, n in garc_entries(archives['a/0/1/3']) if e == ZONE_MAISON)))))
    story = archives[factory.STORYTEXT[7]]
    factory_text = next(n for e, _, o, n in garc_entries(story) if e == patch.TEXT_FACTORY)
    print(f'zone {ZONE_MAISON} script {len(zone_script)} bytes (ZO {container}); shared script '
          f'{factory.SHARED_SCRIPT} {len(script5)} bytes; text {patch.TEXT_FACTORY} (es) {factory_text} bytes; '
          f'hook {len(hook)} bytes; wrote {out}')


if __name__ == '__main__':
    main()
