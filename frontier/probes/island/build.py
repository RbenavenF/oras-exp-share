#!/usr/bin/env python3
"""F11 laboratory prototype. Reads the v0.2 package + its staged game; writes only work/f11/prototype.

No production builder changes. Run from repo: python frontier/probes/island/build.py
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import island_layout as L
import island
import overlay
from formats import rebuild_garc

OUT = ROOT / 'work/f11/prototype'
STAGE = ROOT / 'work/frontier/package/build-island/game'
PACKAGE = ROOT / 'work/frontier/pkg02/oras-frontier-alpha-v0.2/luma/titles/000400000011C400'
CP = ':'.join(str(ROOT / p) for p in ('work/faraway/classes', 'tools/CTRMap-F5/build/classes',
                                    'tools/CTRMap-F5/lib/jogl-all.jar', 'tools/CTRMap-F5/lib/gluegen-rt.jar'))
ARCHIVES = {'ZONE_DATA': 'a/0/1/3', 'AREA_DATA': 'a/0/1/4',
            'FIELD_DATA': 'a/0/3/9', 'MAP_MATRIX': 'a/0/4/0'}
TRIALS = ('world','props','lod','compact','names','animations','flatcollision','retailmodels','camera','coordinates')


def export_mod():
    """Export every changed archive; omitting AREA_DATA or FIELD_DATA invalidates a trial."""
    for rel in ARCHIVES.values():
        shutil.copyfile(OUT / 'game' / rel, OUT / 'mod/romfs' / rel)


def manifest():
    hashes = {str(p.relative_to(OUT / 'mod')): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (OUT / 'mod').rglob('*') if p.is_file()}
    (OUT / 'hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')


def verify_sources():
    """Reject a modified v0.2 package or an unverified staging fallback."""
    package_root = PACKAGE.parents[2]
    manifest = json.loads((package_root / 'manifest.json').read_text())
    if manifest['version'] != 'oras-frontier-alpha-v0.2':
        raise ValueError('Expected the accepted v0.2 package')
    baseline = json.loads((ROOT / 'baseline/oras/manifest.json').read_text())['repolished']
    hashes = {}
    for rel, expected in manifest['files'].items():
        actual = hashlib.sha256((package_root / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Package hash mismatch: {rel}')
        hashes[f'package/{rel}'] = actual
    for p in STAGE.rglob('*'):
        if not p.is_file() or (PACKAGE / 'romfs' / p.relative_to(STAGE)).exists():
            continue
        rel = p.relative_to(STAGE).as_posix()
        data = p.read_bytes()
        if rel == 'sound/sango_sound.bcsar' and not data:
            continue  # CTRMap staging sentinel, never installed in the mod.
        actual = hashlib.sha256(data).hexdigest()
        expected = baseline.get('romfs/' + rel, {})
        if actual != expected.get('sha256') or len(data) != expected.get('size'):
            raise ValueError(f'Staging fallback hash mismatch: {rel}')
        hashes[f'stage/{rel}'] = actual
    return hashes


def grids():
    rows = [['~'] * 160 for _ in range(80)]
    heights = [['0'] * 160 for _ in range(80)]
    for y in range(L.H):
        for x in range(L.W):
            rows[y + 4][x + 16] = L.GRID[y][x]
            heights[y + 4][x + 16] = L.HEIGHT[y][x]
    # No reception building in the prototype: a narrow corridor links its two doors.
    # One stair rises from pier level 1 to plaza level 2; the reference data stays untouched.
    for y in range(61, 66):
        rows[y + 4][26 + 16] = '=' if y == 65 else ':'
        heights[y + 4][26 + 16] = '2'
    return [''.join(r) for r in rows + heights]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', action='append', default=[], choices=TRIALS,
                        help='apply an isolated diagnostic variant, in this order; repeat for cumulative trials')
    args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'game').exists():
        raise SystemExit('Existing prototype; keep its evidence or remove only work/f11/prototype/game and ws before rebuild')
    sources = verify_sources()
    (OUT / 'config.json').write_text(json.dumps({'trials': args.trial}, indent=2)+'\n')
    (OUT / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n')
    shutil.copytree(STAGE, OUT / 'game')
    # The staging predates the package overlay (notably harbor NPCs/scripts).
    # Preserve the complete accepted package before replacing island geometry.
    shutil.copytree(PACKAGE / 'romfs', OUT / 'game', dirs_exist_ok=True)
    shutil.copytree(PACKAGE, OUT / 'mod', dirs_exist_ok=True)
    (OUT / 'grid.txt').write_text('\n'.join(grids()) + '\n')
    # Existing public Java APIs; compile the bridge without editing faraway/java or CTRMap.
    subprocess.run(['faraway/run.sh', 'Probe', str(OUT / 'game'), str(OUT / 'ws'), 'zones'],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['javac', '--release', '8', '-nowarn', '-cp', CP, '-d', str(ROOT / 'work/faraway/classes'),
                    *[str(ROOT / 'frontier/probes/island' / name) for name in ('TerrainPrototype.java','AreaTrial.java','CompactFloors.java')]], check=True)
    with (OUT / 'build.log').open('w') as log:
        subprocess.run(['java', '-Xmx4g', '-Djava.awt.headless=true', '-cp', CP, 'faraway.TerrainPrototype',
                        str(OUT / 'game'), str(OUT / 'ws'), str(OUT / 'grid.txt')], check=True, stdout=log, stderr=log)
    for trial in args.trial:
        with (OUT / 'build.log').open('a') as log:
            log.write('TRIAL '+trial+'\n'); log.flush()
            subprocess.run(['java', '-Xmx4g', '-Djava.awt.headless=true', '-cp', CP, 'faraway.AreaTrial',
                            str(OUT / 'game'), str(OUT / 'ws'), trial], check=True, stdout=log, stderr=log)
    export_mod()
    # Rebuild only ferry 79, preserving all other v0.2 shared scripts and its texts.
    shared = OUT / 'mod/romfs' / overlay.SHARED
    retail = overlay.shared_script((overlay.ROMFS / overlay.SHARED).read_bytes(), island.FERRY_SCRIPT)
    island.ARRIVAL = (209, L.FERRY[0] + 16, 1, L.FERRY[1] + 4, 2)
    script = island.ferry_program(retail).build_script(f'L{retail.main:x}').build(pad=False)
    shared.write_bytes(rebuild_garc(shared.read_bytes(), {(island.FERRY_SCRIPT, 0): script}))
    manifest()
    print((OUT / 'build.log').read_text())


if __name__ == '__main__':
    main()
