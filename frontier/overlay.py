#!/usr/bin/env python3
"""Battle Frontier build: the Battle Maison (517) and Lilycove harbor (317) zone scripts, the shared scripts, their
texts and the code.bin patch.

Current scope:
- F4, the Battle Factory: the receptionist's «Battle Factory» option (zone 517) and the draft of 6 rentals and
  choice of 3 in shared script 5 (a/0/2/9), with its texts in a new story text entry (frontier/factory.py);
  while the Factory is active (saved work patch.WORK_IV != 0) the Maison's party selection routine (script 517
  0x457c, BattleHouse_CallPartySelectApp) is skipped and answers "accepted" (work 0x800C = 1), and the code.bin
  hook (frontier/patch.py) builds the battle party from the rentals;
- F6, the Battle Tower (frontier/tower.py) and the Battle Dome (frontier/dome.py: its cases 9773-9775 in shared
  script 5 and its lines after the Factory's in text 637) in their interiors (facility_scripts);
- F6, the Frontier Pass (frontier/island.py): item 701 renamed in the game texts, the Lilycove sailor (zone 317)
  hands it to a champion, and the ferry (shared script 79) offers «Isla del Frente» to its holder.

Inputs come from --romfs, file by file, falling back to the Repolished baseline (the laboratory passes the
Faraway dev overlay's, which carries the Route 102 warp, v0.5's texts and the Mew event's harbor): a/0/1/3,
checked by SHA-256 of its zone 517 entry (only the scripts of zones 517 and 317, ZO file 2, are replaced; zone
317 is checked by content, as it may carry the Mew event); a/0/2/9, checked by SHA-256 of entry 5 and by
content for entry 79; the story texts a/0/7/9-a/0/8/6 (text 619 must have factory.TEXT_LINES lines and gets
one; the archive must have patch.TEXT_FACTORY entries and gets the new one; 523 and 11 get lines appended) and
the game texts a/0/7/1-8 (species and item names read; item 701's name and description replaced).
Output under work/: romfs/a/0/1/3, romfs/a/0/2/9, the eight story and eight game texts, and code.ips.

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
                     text_lines, text_to_words, words_to_text, zo_build, zo_files)
from pawn import OP, Op, Program, Script  # noqa: E402
import build_patch  # noqa: E402
import data as fd  # noqa: E402
import dome  # noqa: E402
import factory  # noqa: E402
import island  # noqa: E402
import island_build  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402

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


def line_count(data, entry):
    _, _, offset, length = next(e for e in garc_entries(data) if e[0] == entry)
    return len(text_lines(data[offset:offset + length])[0])


def harbor_lines(romfs):
    """Story text 523 line numbers of the sailor's texts: appended after the lines already there (30 retail; more
    when the Mew event's harbor is underneath). Every language must agree, as the script uses one number."""
    counts = {line_count(source(romfs, path), island.TEXT_HARBOR) for path in factory.STORYTEXT.values()}
    if len(counts) != 1:
        raise ValueError(f'text {island.TEXT_HARBOR} has different line counts per language: {counts}')
    base = counts.pop()
    return tuple(range(base, base + len(island.SAILOR['en'])))


def texts(romfs, sets, table):
    """{romfs path: text archive}: story texts (the option line appended to text 619, the new Factory text entry,
    the sailor's lines in 523, the island destination in 11) and game texts (the pass's name and description)."""
    out = {}
    sailor = harbor_lines(romfs)
    for lang, path in factory.STORYTEXT.items():
        code = factory.LANG[lang]
        data = source(romfs, path)
        if len(garc_entries(data)) != patch.TEXT_FACTORY:
            raise ValueError(f'{path}: expected {patch.TEXT_FACTORY} text entries')
        spec = {'path': path, 'texts': [{'entry': factory.TEXT_ZONE, 'line': factory.TEXT_LINES, 'append': True,
                                         'after': factory.OPTION[code]},
                                        {'entry': factory.TEXT_ZONE, 'line': factory.LINE_BUSY, 'append': True,
                                         'after': factory.BUSY[code]}]}
        spec['texts'] += [{'entry': island.TEXT_HARBOR, 'line': line, 'append': True, 'after': text}
                          for line, text in zip(sailor, island.SAILOR[code])]
        spec['texts'] += [{'entry': island.FERRY_TEXT, 'line': island.FERRY_TEXT_LINES + k, 'append': True,
                           'after': text} for k, text in enumerate(island.FERRY[code])]
        data = build_patch.guarded_texts(data, spec)
        lines = factory.lines_for(lang, source(romfs, factory.GAMETEXT[lang]), sets, table)
        if len(lines) != dome.LINE_BASE:
            raise ValueError(f'text {patch.TEXT_FACTORY}: {len(lines)} Factory lines, the Dome expects {dome.LINE_BASE}')
        lines += dome.lines(lang)
        words = [text_to_words(line) for line in lines]
        out[path] = rebuild_garc(data, {}, append=[build_text(words, [0] * len(words))])
        game = factory.GAMETEXT[lang]
        g = source(romfs, game)
        changes = []
        for key, entry in island.GAMETEXT_ITEM.items():
            _, _, offset, length = next(e for e in garc_entries(g) if e[0] == entry)
            before = text_lines(g[offset:offset + length])[0][island.ITEM_PASS]
            changes.append({'entry': entry, 'line': island.ITEM_PASS, 'before': words_to_text(before),
                            'after': island.ITEM[code][key]})
        out[game] = build_patch.guarded_texts(g, {'path': game, 'texts': changes})
    return out


def shared_script(data, index):
    _, _, offset, length = garc_entries(data)[index]
    raw = data[offset:offset + length]
    script = Script.parse(raw)
    if script.build(pad=False) != raw:
        raise ValueError(f'shared script {index} does not round-trip')
    return script


def shared(romfs, zone_script, cells, levels):
    """(shared script archive, new shared script 5): the Factory's draft and swap in 5, the ferry's island
    destination in 79."""
    data = source(romfs, SHARED)
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    raw = data[offset:offset + length]
    if hashlib.sha256(raw).hexdigest() != SHARED_SHA256:
        raise ValueError(f'{SHARED} entry {factory.SHARED_SCRIPT} differs from Repolished 1.7.6')
    retail = Script.parse(raw)
    if retail.build(pad=False) != raw:
        raise ValueError('shared script 5 does not round-trip')
    program = factory.shared_program(retail, zone_script, cells, levels, dome.shared_cases(levels))
    script = program.build_script(f'L{retail.main:x}').build(pad=False)
    ferry = shared_script(data, island.FERRY_SCRIPT)
    ferry_new = island.ferry_program(ferry).build_script(f'L{ferry.main:x}').build(pad=False)
    return rebuild_garc(data, {(factory.SHARED_SCRIPT, 0): script, (island.FERRY_SCRIPT, 0): ferry_new}), script


def harbor(romfs, data):
    """Zone 317 ZO files with the sailor who gives the pass (from the zone archive `data`)."""
    _, _, offset, length = garc_entries(data)[island.ZONE_HARBOR]
    files = zo_files(lz11_decompress(data[offset:offset + length]))
    retail = Script.parse(files[2])
    if retail.build() != files[2]:
        raise ValueError(f'zone {island.ZONE_HARBOR} script does not round-trip')
    shared_data = source(romfs, SHARED)
    ferry, shared10 = shared_script(shared_data, island.FERRY_SCRIPT), shared_script(shared_data, island.SHARED10)
    program = island.harbor_program(retail, ferry, shared10, harbor_lines(romfs))
    files[2] = program.build_script(f'L{retail.main:x}').build()
    return files


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


def facility_scripts(romfs=ROMFS):
    """{interior zone: zone script} of the facilities whose interior runs its own script (island_build.build)."""
    _, retail = maison_retail(source(romfs, 'a/0/1/3'))
    return {tower.ZONE: tower.zone_script(retail), dome.ZONE: dome.zone_script(retail)}


def build(romfs=ROMFS):
    """{romfs path: archive} for a/0/1/3, a/0/2/9 and the story texts; (zone 517 script, shared script 5)."""
    sets, table, levels, cells = rentals()
    data = source(romfs, 'a/0/1/3')
    files, retail = maison_retail(data)
    files[2] = maison_script(retail).build()
    zones = {}
    for zone, zone_files_ in ((ZONE_MAISON, files), (island.ZONE_HARBOR, harbor(romfs, data))):
        offset = garc_entries(data)[zone][2]
        zones[next((e, s) for e, s, o, n in garc_entries(data) if o == offset)] = lz11_compress(zo_build(zone_files_))
    out = {'a/0/1/3': rebuild_garc(data, zones)}
    out[SHARED], script5 = shared(romfs, retail, cells, levels)
    out.update(texts(romfs, sets, table))
    return out, (files[2], script5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--romfs', type=Path, default=ROMFS)
    parser.add_argument('--no-island', action='store_true', help='skip the CTRMap-F5 island zones (faster)')
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game data)')
    archives, (zone_script, script5) = build(args.romfs)
    if not args.no_island:
        archives, log = island_build.build(archives, lambda rel: source(args.romfs, rel),
                                           out.parent / (out.name + '-island'), facility_scripts(args.romfs))
        print(''.join(line + '\n' for line in log.splitlines() if line.startswith(('zone ', 'pack'))), end='')
    code, hook, _ = patch.build({} if args.no_island else island_build.native_donors())
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
