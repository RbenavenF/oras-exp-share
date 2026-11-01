#!/usr/bin/env python3
"""Build the Faraway Island expansion on top of the held Exp. Share / DexNav assets.

1. Stage a copy of the Repolished archives the zone tools read (hash-checked).
2. Assemble the event scripts (faraway/event.py) against the staged retail scripts.
3. Run faraway/java Build (CTRMap-F5): clone zones, give them their own map and area, place entities.
4. Apply texts, item data and the static encounter on top of the already-patched assets.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'faraway'))
from formats import check_file, garc_entries, lz11_decompress, text_lines, words_to_text, zo_files  # noqa: E402
from pawn import Script, listing, native_names  # noqa: E402
import event as ev  # noqa: E402
import build_patch  # noqa: E402

BASE = ROOT / 'baseline/oras/repolished'
# Archives the Java builder reads or writes (CTRMap-F5 OrasProfile paths).
STAGED = ['a/0/1/4', 'a/0/3/9', 'a/0/4/0', 'a/0/7/3', 'a/0/8/1', 'a/0/1/3', 'a/0/2/3', 'a/1/3/7', 'a/0/2/1',
          'a/0/3/6', 'a/0/3/7', 'a/0/3/8', 'a/1/9/5', 'a/1/8/9', 'a/1/9/7', 'a/0/2/9', 'a/1/8/2', 'a/1/8/3',
          'a/1/8/4', 'a/1/8/5', 'a/1/8/6']
# The Java build may change only these; anything else it touches is an error.
ZONE_ARCHIVES = {'a/0/1/3', 'a/0/1/4', 'a/0/3/9', 'a/0/4/0', 'a/1/3/7', 'a/0/2/1'}
GAMETEXT = {lang: f'romfs/a/0/7/{lang}' for lang in range(1, 9)}          # 1 JP kana .. 8 KO
STORYTEXT = {lang: f'romfs/a/0/{(78 + lang) // 10}/{(78 + lang) % 10}' for lang in range(1, 9)}
LANG = {1: 'en', 2: 'en', 3: 'en', 4: 'en', 5: 'en', 6: 'en', 7: 'es', 8: 'en'}  # text set used per language
TEXT_ENTRY = {'harbor': ev.TEXT_HARBOR, 'island': ev.TEXT_ISLAND, 'meadow': ev.TEXT_MEADOW}
ITEM_NAMES = {'es': ('Mapa Viejo', 'Mapas Viejos', 'Mapa[VAR 1101 254,256]s Viejo[VAR 1101 254,256]s'),
              'en': ('Old Sea Map', 'Old Sea Maps', 'Old Sea Map[VAR 1101 254,256]s')}
ITEM_DESCRIPTION = {
    'es': 'Un mapa antiquísimo que el mar arrastró hasta el\npuerto de Calagua. Señala una isla lejana.',
    'en': 'A faded sea chart that washed up in Lilycove\nHarbor. It shows the way to a faraway island.'}
PLACE_NAME = {'es': 'Isla Suprema', 'en': 'Faraway Island'}
STATIC_ENTRY = 0xF1B20 + 12 * ev.STATIC_MEW
STATIC_DEOXYS = bytes.fromhex('820100' '50' 'ffff' '8202' '57572200')  # retail row 29: Deoxys Lv 80
# Species 151, form 0, Lv 30, no item; RNG shiny, any gender/ability, legendary row type 2 (3 perfect IVs);
# battle field/background bytes copied from the Latios/Latias rows (also Lv 30 legends).
STATIC_MEW_BYTES = struct.pack('<HBBhH', ev.SPECIES_MEW, 0, 30, -1, 0x0100) + bytes.fromhex('3d3d0000')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stage(work):
    manifest = json.loads((ROOT / 'baseline/oras/manifest.json').read_text())
    game = work / 'game'
    if game.exists():
        shutil.rmtree(game)
    for rel in STAGED:
        check_file(BASE / 'romfs' / rel, manifest['repolished']['romfs/' + rel])
        (game / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE / 'romfs' / rel, game / rel)
    (game / 'sound').mkdir(exist_ok=True)
    (game / 'sound/sango_sound.bcsar').write_bytes(b'')
    return game


def zone_files(game, zone):
    data = (game / 'a/0/1/3').read_bytes()
    _, _, offset, length = garc_entries(data)[zone]
    return zo_files(lz11_decompress(data[offset:offset + length]))


def entity_script(entities):
    c = entities[4:9]
    offset = 12 + c[0] * 0x14 + c[1] * 0x30 + c[2] * 0x18 + c[3] * 0x18 + c[4] * 0x18
    return Script.parse(entities[offset:offset + struct.unpack_from('<I', entities, offset)[0]])


def add_mew_model(game, work):
    """Append the field Mew built from its battle model as MoveModels entry MOVEMODEL_MEW."""
    import mew_model
    from formats import lz11_compress, rebuild_garc
    manifest = json.loads((ROOT / 'baseline/oras/manifest.json').read_text())
    check_file(mew_model.POKEMON_MODELS, manifest['repolished']['romfs/a/0/0/8'])
    mm = mew_model.build(work / 'mew')
    archive = game / 'a/0/2/1'
    data = archive.read_bytes()
    if len(garc_entries(data)) != ev.MOVEMODEL_MEW:
        raise ValueError('MoveModels does not end where the Mew entry is expected')
    archive.write_bytes(rebuild_garc(data, {}, [lz11_compress(mm)]))


def compile_scripts(game, out):
    shared = (game / 'a/0/2/9').read_bytes()
    entries = garc_entries(shared)
    ferry, giver = (Script.parse(shared[entries[i][2]:entries[i][2] + entries[i][3]]) for i in (79, 10))
    harbor = zone_files(game, ev.ZONE_HARBOR)
    base = Script.parse(harbor[2])
    scripts = {
        f'zone{ev.ZONE_HARBOR}': ev.harbor_script(base, ferry, giver),
        f'zone{ev.ZONE_HARBOR}.ent': ev.harbor_entity_script(entity_script(harbor[1])),
        # The island zones keep their donors' retail scripts (Southern Island 214/215) and gain cases.
        f'zone{ev.ZONE_ISLAND}': ev.island_script(Script.parse(zone_files(game, 214)[2]), ferry, giver),
        f'zone{ev.ZONE_MEADOW}': ev.meadow_script(Script.parse(zone_files(game, 215)[2]), ferry, giver),
    }
    names = native_names(ROOT / 'tools/CTRMap-F5/src/ctrmap/resources/oras_natives.tsv')
    out.mkdir(parents=True, exist_ok=True)
    for name, script in scripts.items():
        raw = script.build()
        if Script.parse(raw).build() != raw:
            raise ValueError(f'Script {name} does not round-trip')
        (out / f'{name}.bin').write_bytes(raw)
        (out / f'{name}.lst').write_text(listing(script, names) + '\n')
    return scripts


def plan(work, scripts_dir):
    # The harbor's retail NPCs are 0-2; the event's giver and Briney must land on the indices the scripts use.
    if (ev.HARBOR_NPC_GIVER, ev.HARBOR_NPC_BRINEY) != (3, 4):
        raise ValueError('Harbor NPC indices changed')
    i, b = ev.ZONE_ISLAND, ev.ZONE_MEADOW
    lines = [
        f'scripts={scripts_dir}',
        f'clones=214:{i},215:{b}',
        f'place.{i}={ev.LOCATION_FARAWAY}', f'place.{b}={ev.LOCATION_FARAWAY}',
        f'zones={ev.ZONE_HARBOR},{i},{b}',
        # Registry entries are copied from the S.S. Tidal's area (104), where both models appear in retail.
        f'regdonor.{ev.MODEL_BRINEY}=104', f'regdonor.{ev.MODEL_PEEKO}=104', f'regdonor.{ev.MODEL_SAILOR}=104',
        # model,moveModel,script,spawnFlag,x,y,height,face
        f'zone.{ev.ZONE_HARBOR}.npc.0={ev.MODEL_SAILOR},{ev.MODEL_SAILOR},{ev.EV_GIVER},{ev.FLAG_HIDE_GIVER},22,24,0,1',
        f'zone.{ev.ZONE_HARBOR}.npc.1={ev.MODEL_BRINEY},{ev.MODEL_BRINEY},{ev.EV_BRINEY},{ev.FLAG_HIDE_BRINEY},19,24,0,1',
        f'zone.{i}.clearNpcs=1', f'zone.{i}.clearTriggers=1', f'zone.{i}.warp.0=0,{b},0',
        f'zone.{i}.npc.0={ev.MODEL_BRINEY},{ev.MODEL_BRINEY},{ev.EV_ISLAND_BRINEY},0,19,30,90,1',
        f'zone.{i}.npc.1={ev.MODEL_PEEKO},484,2000,0,18,30,90,1',
        f'zone.{b}.clearNpcs=1', f'zone.{b}.clearTriggers=1', f'zone.{b}.warp.0=0,{i},0',
        f'zone.{b}.npc.0={ev.MODEL_MEW},{ev.MOVEMODEL_MEW},{ev.EV_MEW},{ev.FLAG_MEW_CAPTURED},20,15,36,1',
        f'regnew.{ev.MODEL_MEW}=104,{ev.MODEL_PEEKO}',
    ]
    path = work / 'plan.properties'
    path.write_text('\n'.join(lines) + '\n')
    return path


def run_java(game, work, plan_path):
    ws = work / 'ws'
    if ws.exists():
        shutil.rmtree(ws)
    log = work / 'java.log'
    with log.open('w') as stream:
        subprocess.run([str(ROOT / 'faraway/run.sh'), 'Build', str(game), str(ws), str(plan_path)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    return log.read_text()


def text_edit(data, entry, changes, path):
    """changes: {line: text}; lines past the end are appended in order."""
    entries = garc_entries(data)
    _, _, offset, length = next(e for e in entries if e[0] == entry)
    lines, _ = text_lines(data[offset:offset + length])
    spec = {'path': path, 'texts': []}
    for line in sorted(changes):
        if line < len(lines):
            spec['texts'].append({'entry': entry, 'line': line, 'before': words_to_text(lines[line]),
                                  'after': changes[line]})
        else:
            spec['texts'].append({'entry': entry, 'line': line, 'append': True, 'after': changes[line]})
    return build_patch.guarded_texts(data, spec)


def apply_data(assets):
    """Texts, item and static encounter edits, applied on top of `assets` (romfs-relative path -> bytes)."""
    out = dict(assets)
    for lang in range(1, 9):
        texts = ev.TEXT
        code = LANG[lang]
        path = STORYTEXT[lang]
        data = out[path]
        for name, entry in TEXT_ENTRY.items():
            lines = texts[name][code]
            base_count = len(_lines(data, entry))
            start = ev.HARBOR_TEXT_BASE if name == 'harbor' else 0
            if base_count != start:
                raise ValueError(f'{path} entry {entry} has {base_count} lines, expected {start}')
            data = text_edit(data, entry, {start + k: line for k, line in enumerate(lines)}, path)
        out[path] = data
        gpath = GAMETEXT[lang]
        g = out[gpath]
        single, plural, counted = ITEM_NAMES[code]
        for entry, value in ((113, counted), (114, single), (115, plural), (116, single), (117, ITEM_DESCRIPTION[code])):
            g = text_edit(g, entry, {ev.ITEM_OLD_SEA_MAP: value}, gpath)
        g = text_edit(g, 90, {ev.LOCATION_FARAWAY: PLACE_NAME[code]}, gpath)
        out[gpath] = g
    cro = bytearray(out['romfs/DllField.cro'])
    before = bytes(cro[STATIC_ENTRY:STATIC_ENTRY + 12])
    if before != STATIC_DEOXYS:
        raise ValueError(f'Unexpected static encounter row {ev.STATIC_MEW}: {before.hex()}')
    cro[STATIC_ENTRY:STATIC_ENTRY + 12] = STATIC_MEW_BYTES
    out['romfs/DllField.cro'] = bytes(cro)
    return out


def _lines(data, entry):
    _, _, offset, length = next(e for e in garc_entries(data) if e[0] == entry)
    return text_lines(data[offset:offset + length])[0]


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip', action='append', default=[], help='laboratory bisection: harbor-scripts, harbor-npcs')
    args = parser.parse_args()
    work = ROOT / 'work/faraway/build'
    work.mkdir(parents=True, exist_ok=True)
    game = stage(work)
    scripts = work / 'scripts'
    compile_scripts(game, scripts)
    add_mew_model(game, work)
    if 'harbor-ent' in args.skip:
        (scripts / f'zone{ev.ZONE_HARBOR}.ent.bin').unlink()
    if 'harbor-scripts' in args.skip:
        for name in (f'zone{ev.ZONE_HARBOR}.bin', f'zone{ev.ZONE_HARBOR}.ent.bin'):
            (scripts / name).unlink()
    plan_path = plan(work, scripts)
    if 'harbor-npcs' in args.skip:
        plan_path.write_text(''.join(l for l in plan_path.read_text().splitlines(True)
                                     if not l.startswith(f'zone.{ev.ZONE_HARBOR}.npc')))
    print(run_java(game, work, plan_path))
    originals, assets = build_patch.patched_assets()
    changed = {}
    for rel in STAGED:
        new = (game / rel).read_bytes()
        if new != (BASE / 'romfs' / rel).read_bytes():
            if rel not in ZONE_ARCHIVES:
                raise ValueError(f'Java build changed {rel}')
            changed['romfs/' + rel] = new
    base = {**{k: v for k, v in assets.items()}}
    for path in list(GAMETEXT.values()) + list(STORYTEXT.values()) + ['romfs/DllField.cro']:
        if path not in base:
            base[path] = (BASE / path).read_bytes()
    data = apply_data(base)
    data.update(changed)
    # DllField changed again: rehash it and update its CRR entry over the already-updated table.
    old = assets.get('romfs/DllField.cro', (BASE / 'romfs/DllField.cro').read_bytes())
    data['romfs/DllField.cro'] = build_patch.rehash_cro(old, data['romfs/DllField.cro'])
    crr = assets.get('romfs/.crr/static.crr', (BASE / 'romfs/.crr/static.crr').read_bytes())
    data['romfs/.crr/static.crr'] = build_patch.update_crr(crr, old, data['romfs/DllField.cro'])
    overlay = work / 'overlay'
    if overlay.exists():
        shutil.rmtree(overlay)
    for rel, blob in data.items():
        (overlay / rel).parent.mkdir(parents=True, exist_ok=True)
        (overlay / rel).write_bytes(blob)
    print('overlay files:', len(data), sorted(data))


if __name__ == '__main__':
    main()
