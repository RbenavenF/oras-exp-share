"""F10-PERSONALIDAD-DISENO: which retail zones can host a facility hall without moving its choreography.

Reads the per-zone floor maps of `faraway/run.sh Probe GAME WS floor N` (one file per zone, floorN.txt) and
work/frontier/island/zones.tsv, and prints the zones whose floor covers the Battle Maison tiles the facility scripts
use (517's Singles choreography x=19-23, y=12-25, and the receptionists' row at (17,24), (23,24), (17,25);
reports/frontier.md §37). 'flat' counts those tiles on the most common height bucket (18 units). The floor map is a
necessary check, not a sufficient one: the sampler sees collision heights, not barriers (§37.1), so a donor still
needs `Probe tuples` and a walk in Azahar. reports/diseno/personalidad.md §1.

Usage: python frontier/probes/personalidad/floor_fit.py FLOORS_DIR [--zones-tsv work/frontier/island/zones.tsv]
       [--all] [ZONE ...]
"""
import argparse
import collections
import re
from pathlib import Path

CORE = [(x, y) for x in range(19, 24) for y in range(12, 26)] + [(17, 24), (23, 24), (17, 25)]


def floor_rows(path):
    rows = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r'\s*(\d+) (\S+)$', line)
        if m:
            rows[int(m.group(1))] = m.group(2)
    return rows


def fit(rows):
    """(missing core tiles, tiles on the main height bucket, (x0, x1, y0, y1) of the floor or None)."""
    def at(x, y):
        return rows.get(y, '')[x:x + 1] or '#'
    core = [at(x, y) for x, y in CORE]
    levels = collections.Counter(c for c in core if c.isalpha())
    tiles = [(x, y) for y, row in rows.items() for x, c in enumerate(row) if c != '#']
    box = (min(t[0] for t in tiles), max(t[0] for t in tiles), min(t[1] for t in tiles), max(t[1] for t in tiles)) \
        if tiles else None
    return sum(c == '#' for c in core), (levels.most_common(1)[0][1] if levels else 0), box


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('floors', type=Path)
    ap.add_argument('zones', nargs='*', type=int)
    ap.add_argument('--zones-tsv', type=Path, default=Path('work/frontier/island/zones.tsv'))
    ap.add_argument('--all', action='store_true', help='list every zone, not only those missing at most 2 tiles')
    a = ap.parse_args()
    names = {}
    for line in a.zones_tsv.read_text().splitlines():
        p = line.split('\t')
        if len(p) > 3:
            names[int(p[0])] = ' '.join([p[1]] + [q for q in p[3:] if q.split('=')[0] in
                                                  ('area', 'matrix', 'npc', 'warp', 'trig', 'props')])
    zones = a.zones or sorted(int(re.sub(r'\D', '', f.name)) for f in a.floors.glob('floor*.txt'))
    for z in zones:
        rows = floor_rows(a.floors / f'floor{z}.txt')
        missing, flat, box = fit(rows)
        if a.all or a.zones or (rows and missing <= 2):
            span = f'x{box[0]}-{box[1]} y{box[2]}-{box[3]}' if box else 'no floor'
            print(f'{z}\t{names.get(z, "?")}\tmissing {missing}/{len(CORE)}\tflat {flat}/{len(CORE)}\t{span}')


if __name__ == '__main__':
    main()
