#!/usr/bin/env python3
"""F11 isolated landscape candidate; common builders are read, never edited.

source scripts/env.sh
python frontier/probes/island/landscape.py [--trees 40 --bushes 140 --fences 40]
Requires work/f11/finish/base/out[-island], built by overlay.py (see README).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_build
import island_layout
from island_build import garc_entries, lz11_decompress, zo_files

HERE = Path(__file__).resolve().parent
OUT = ROOT / 'work/f11/finish'
BASE = OUT / 'base'
CP = f'{ROOT}/work/faraway/classes:{ROOT}/tools/CTRMap-F5/build/classes:{ROOT}/tools/CTRMap-F5/lib/jogl-all.jar:{ROOT}/tools/CTRMap-F5/lib/gluegen-rt.jar'


def entry(blob, index):
    _, _, start, size = garc_entries(blob)[index]
    raw = blob[start:start + size]
    return lz11_decompress(raw) if raw[0] == 0x11 else raw


def trial_source(source):
    """Small, fail-closed integration seams; output is a reviewable diff in work/."""
    changes = {
        'byte[] donor = container.getFile(1);':
        'byte[] donor = IslandLandscape.paving(container.getFile(1));',
        'grid[y][x] = brush(rows.get(gy).charAt(gx));':
        'grid[y][x] = IslandLandscape.brush(rows.get(gy).charAt(gx), gx, gy);',
        '// one quad per run of identical flat tiles, before any building is stamped (IslandFloors: lossless)':
        'IslandLandscape.stairs(bc);\n\t\t\t\t// one quad per run of identical flat tiles, before any building is stamped (IslandFloors: lossless)',
        'int region = first + cy * CELLS_X + cx;':
        'out.append(IslandLandscape.decorate(bc, cx, cy, rows, stampNeeds, IslandLandscape.placements));\n'
        '\t\t\t\tIslandLandscape.preserve(bc, cx, cy);\n\t\t\t\tint region = first + cy * CELLS_X + cx;',
    }
    for old, new in changes.items():
        if source.count(old) != 1:
            raise ValueError(f'Builder changed; re-audit integration seam: {old}')
        source = source.replace(old, new)
    return source


def catalog_size(name):
    for file in (island_build.CATALOGUE, island_build.CATALOGUE.with_name('oras_buildings_auto.tsv')):
        for line in file.read_text().splitlines():
            a = line.split('\t')
            if len(a) >= 8 and a[1] == name:
                return int(a[6])-int(a[4])+1, int(a[7])-int(a[5])+1
    raise ValueError(f'No ORAS catalogue piece {name!r}')


def placements(trees, bushes, fences, small_trees=20, small_bushes=100):
    """Spread retail pieces over safe matching blocked footprints, with explicit caps for the load budget."""
    rows = island_build.island_rows()
    occupied = set()
    chosen = []
    for name, chars, cap, mode in [('Pokémon League structure (flower01)', 'p', 8, 'half'),
                                   ('Team Aqua Hideout structure (flag_01)', 'f', 6, 'half'),
                                   ('Roadside tree', 'T', trees, ''), ('Roadside tree', 'T', small_trees, 'half'),
                                   ('Bush', 'Tp', bushes, ''), ('Bush', 'Tp', small_bushes, 'half'),
                                   ('Iron fence (4-tile run)', 'f', fences, ''),
                                   ('Iron fence (4-tile run)', 'f', fences, '90')]:
        w, h = catalog_size(name)
        if mode == '90':
            w, h = h, w
        elif mode == 'half':
            w, h = (w+1)//2, (h+1)//2
        candidates = []
        for y in range(80 - h + 1):
            for x in range(160 - w + 1):
                footprint = {(xx, yy) for yy in range(y, y+h) for xx in range(x, x+w)}
                if x//40 != (x+w-1)//40 or y//40 != (y+h-1)//40:
                    continue
                if any(rows[yy][xx] not in chars or rows[80+yy][xx] != rows[80+y][x]
                       for xx, yy in footprint):
                    continue
                candidates.append((x, y, footprint))
        # Farthest-point sampling covers the island before filling dense patches.
        points = []
        while candidates and len(points) < cap:
            x, y, footprint = max(candidates, key=lambda q: min(
                ((q[0]-px)**2 + (q[1]-py)**2 for px, py in points), default=1))
            candidates.remove((x, y, footprint))
            if footprint & occupied:
                continue
            occupied.update(footprint)
            points.append((x, y))
            chosen.append(f'{name}|{x}|{y}' + (f'|{mode}' if mode else ''))
    return chosen


def gr_files(raw):
    assert raw[:2] == b'GR'
    return zo_files(b'ZO' + raw[2:])


def verify(before, after, log):
    """Actual packed GARCs: reject changed movement, scripts, entities, props or auxiliaries."""
    bz, az = [(p / 'a/0/1/3').read_bytes() for p in (before, after)]
    assert bz == az, 'Zone archive changed (doors/scripts/ferry)'
    assert len(entry(az, 209)) <= island_build.ZO_LIMIT
    # Our 4x2 rebuild appends eight regions; compare each cell against the source cell.
    # Read both actual matrices from the Java log; never assume source IDs are contiguous.
    old = garc_entries((before/'a/0/3/9').read_bytes())
    new = garc_entries((after/'a/0/3/9').read_bytes())
    assert len(new) == len(old)+8
    import re
    source_regions = json.loads(re.search(r'^source regions (\[.*\])$', log, re.M)[1])
    target_regions = json.loads(re.search(r'^landscape regions (\[.*\])$', log, re.M)[1])
    assert len(source_regions) == len(target_regions) == len(set(source_regions)) == len(set(target_regions)) == 8
    evidence = []
    for i, (src, dst) in enumerate(zip(source_regions, target_regions)):
        a = gr_files(entry((before/'a/0/3/9').read_bytes(), src))
        b = gr_files(entry((after/'a/0/3/9').read_bytes(), dst))
        assert len(a) == len(b) == 7
        for sub in (0, 2, 3, 4, 5, 6):
            assert a[sub] == b[sub], f'Cell {i}: GR[{sub}] changed'
        evidence.append({'cell':[i%4,i//4], 'tilemap':hashlib.sha256(a[0]).hexdigest(),
                         'collision':hashlib.sha256(a[2]).hexdigest()})
    return {'zone_archive_sha256':hashlib.sha256(az).hexdigest(), 'zo209_bytes':len(entry(az,209)),
            'unchanged_GR_subfiles':[0,2,3,4,5,6], 'source_regions': source_regions, 'target_regions': target_regions, 'cells':evidence}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--name', default='trial', help='isolated output name under work/f11/finish')
    ap.add_argument('--trees', type=int, default=40)
    ap.add_argument('--bushes', type=int, default=140)
    ap.add_argument('--small-trees', type=int, default=20)
    ap.add_argument('--small-bushes', type=int, default=100)
    ap.add_argument('--fences', type=int, default=40)
    args = ap.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Simple trial name required')
    if args.name == 'base':
        raise ValueError('The production baseline is reserved')
    if min(args.trees, args.bushes, args.small_trees, args.small_bushes, args.fences) < 0:
        raise ValueError('Scenery caps must be nonnegative')
    trial = OUT/args.name
    if trial.exists():
        shutil.rmtree(trial)
    trial.mkdir(parents=True)
    for part in ('game', 'ws'):
        shutil.copytree(BASE/'out-island'/part, trial/part)
    marker = trial/'ws/_original_garcs/taken-from.txt'
    marker.write_text(marker.read_text().replace(str(BASE/'out-island/game'), str(trial/'game')))
    source = ROOT/'faraway/java/ctrmap/tests/FrontierIsland.java'
    modified = trial_source(source.read_text())
    (trial/'FrontierIsland.java').write_text(modified)
    import difflib
    (trial/'integration.diff').write_text(''.join(difflib.unified_diff(source.read_text().splitlines(True),
        modified.splitlines(True), fromfile=str(source.relative_to(ROOT)), tofile=str(source.relative_to(ROOT)))))
    chosen = placements(args.trees, args.bushes, args.fences, args.small_trees, args.small_bushes)
    (trial/'placements.txt').write_text('\n'.join(chosen)+'\n')
    classes = trial/'classes'
    classes.mkdir()
    subprocess.run(['javac','--release','8','-nowarn','-cp',CP,'-d',str(classes),
                    str(trial/'FrontierIsland.java'),str(HERE/'IslandLandscape.java'),str(HERE/'LandscapeTrial.java')],check=True)
    with (trial/'build.log').open('w') as log:
        subprocess.run(['java','-Xmx4g','-Djava.awt.headless=true','-cp',f'{classes}:{CP}',
            'faraway.LandscapeTrial',str(trial/'game'),str(trial/'ws'),str(BASE/'out-island/plan.properties'),
            str(trial/'placements.txt')],stdout=log,stderr=subprocess.STDOUT,check=True)
    sources = {'git': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'builder': hashlib.sha256(source.read_bytes()).hexdigest(),
               'plan': hashlib.sha256((BASE/'out-island/plan.properties').read_bytes()).hexdigest(),
               'settings': vars(args),
               'base_archives': {rel: hashlib.sha256((BASE/'out-island/game'/rel).read_bytes()).hexdigest()
                                 for rel in island_build.ZONE_ARCHIVES}}
    (trial/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    text = (trial/'build.log').read_text()
    island_build.check_budget(text)
    assert 'outside the world pack: {}' in text
    proof = verify(BASE/'out-island/game',trial/'game',text)
    proof['budget'] = island_build.check_budget(text)
    proof['placements'] = chosen
    (trial/'movement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    shutil.copytree(BASE/'out',trial/'out')
    for rel in island_build.ZONE_ARCHIVES:
        shutil.copyfile(trial/'game'/rel,trial/'out/romfs'/rel)
    print(text[text.rfind('outside the world pack:'):])
    print(f'Preserved all movement data, ZO {proof["zo209_bytes"]} bytes; {len(chosen)} retail pieces')

if __name__ == '__main__':
    main()
