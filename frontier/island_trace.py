#!/usr/bin/env python3
"""F11-ISLA-TRAZADO: traces Emerald's Battle Frontier outside into frontier/island_layout.py (reports/diseno/isla-esmeralda.md §1).

Sources (read only; nothing of them is copied into the repository but the per-tile classes this script derives):
- pret/pokeemerald 731ad5bf: data/layouts/BattleFrontier_Outside{West,East}/map.bin (metatile, collision bits),
  the tilesets' metatile_attributes.bin (behaviour: water, waterfall, doors) and the maps' warp_events;
- reports/diseno/referencias/frente-esmeralda.webp, the user's reference picture, 16 px per tile (colour of each
  tile: grass, sand, trees, cliffs, fences).

Rules, in order (the result is checked by tests/test_frontier_island_layout.py):
1. Hand-measured boxes from the picture (BUILDINGS, BEDS) and the doors from warp_events (DOORS, RESERVED).
2. Emerald's collision says walkable or blocked. Walkable: stairs (metatile 175/207, measured on the seven stair
   runs), the pier, sand, grass, light floor, else path. Blocked: water, trees, cliffs, fences, else decoration.
3. Left out by the user (2026-11-13): Artisan Cave (both mouths and the dirt yard below the west one) and the
   waterfall become cliff.
4. Water touching the map edge is sea, the rest is a pond.
5. Heights: the walkable areas split by the stairs, each one above the one south of its stairs (Emerald's stairs
   all climb north): the pier and the fisherman's landing 1, the plaza 2, Dome/Tower terrace, Pyramid and Arena 3;
   water 0. Every other tile takes the height of the nearest of those areas (ties: the higher), so a cliff band
   splits halfway between its top and its foot.

Needs Pillow (system python3) and a pokeemerald checkout at 731ad5bf:
    /usr/bin/python3 frontier/island_trace.py --emerald /path/to/pokeemerald
"""
import argparse
import collections
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICTURE = ROOT / 'reports/diseno/referencias/frente-esmeralda.webp'
OUT = ROOT / 'frontier/island_layout.py'
COMMIT = '731ad5bfd6e6f265508d0efcca0ba42f9dcf5881'
W, H, WEST = 128, 72, 56
STAIR_METATILES = {175, 207}       # the seven stair runs' metatiles (primary tileset), measured on the picture
GANGWAY = {(19, 68), (20, 68)}     # same metatile as the stairs: the ferry's gangway on the pier
# Hand-measured on the picture (16 px grid), inclusive tile boxes x0, y0, x1, y1.
BUILDINGS = {
    'Dome': (13, 5, 25, 16), 'DomeFront': (17, 17, 21, 17), 'Factory': (4, 30, 18, 37), 'FactoryTop': (8, 29, 14, 29), 'Pike': (40, 17, 45, 26),
    'Tower': (64, 0, 80, 14), 'Arena': (90, 23, 100, 29), 'Palace': (96, 50, 106, 55), 'Pyramid': (107, 5, 121, 14),
    'Reception': (23, 62, 29, 65), 'RankingHall': (88, 8, 95, 12), 'Exchange': (63, 24, 68, 28),
    'PokemonCenter': (58, 48, 61, 51), 'Mart': (50, 48, 53, 51), 'ScottsHouse': (43, 2, 45, 5),
    'Lounge1': (59, 41, 62, 44), 'Lounge2': (44, 41, 49, 44), 'Lounge3': (120, 28, 122, 31),
    'Lounge4': (52, 41, 55, 44), 'Lounge5': (77, 48, 82, 51), 'Lounge6': (60, 5, 62, 8), 'Lounge7': (4, 17, 6, 20),
    'Lounge8': (69, 48, 71, 51),
}
BEDS = [(7, 40, 8, 43), (14, 40, 15, 43), (17, 45, 21, 47), (31, 45, 40, 47), (71, 34, 75, 39), (74, 43, 82, 45)]
# Door tiles (warp_events, joined x = East x + 56): the seven facilities and the reception get a door; the others
# keep a reserved hueco without one (isla-esmeralda.md §1).
DOORS = {'Dome': (19, 17), 'Factory': (11, 38), 'Pike': (42, 27), 'Tower': (72, 14), 'Arena': (95, 29),
         'Palace': (101, 56), 'Pyramid': (114, 14), 'ReceptionNorth': (26, 61), 'ReceptionSouth': (26, 65)}
RESERVED = {'PokemonCenter': (59, 51), 'Mart': (51, 51), 'RankingHall': (91, 12), 'ScottsHouse': (44, 5),
            'Exchange': (66, 28), 'Lounge1': (60, 44), 'Lounge2': (45, 44), 'Lounge3': (121, 31),
            'Lounge4': (53, 44), 'Lounge5': (78, 51), 'Lounge6': (61, 8), 'Lounge7': (5, 20), 'Lounge8': (70, 51)}
CAVE = {(39, 55), (84, 7)}
CAVE_YARD = (36, 55, 42, 58)
ROCKS = (109, 15, 119, 26)         # brown inside the Pyramid's sand: its six boulders
PATHS = [(89, 30, 101, 32)]        # the Arena's wooden porch
PIER = (10, 65, 30, 68)            # the ferry pier, its railings and its brick face
HIGH_PONDS = [(90, 50), (110, 52)]  # the Palace's garden ponds (the waterfall fell from the east one): plaza height
LOW_PONDS = [(20, 32)]             # the inlet east of the Factory: a sea bay between cliffs
POND = 100                         # enclosed water up to this many tiles lies at its shore's height, not the sea's
FERRY = (19, 67)                   # warp MAP_BATTLE_FRONTIER_OUTSIDE_WEST, 19, 67 (Slateport/Lilycove harbors)
PIER_LEVEL, PLAZA_LEVEL, UPPER_LEVEL = 1, 2, 3


def u16s(path):
    data = Path(path).read_bytes()
    return struct.unpack(f'<{len(data) // 2}H', data)


def behaviours(emerald):
    names, i = {}, 0
    for line in (emerald / 'include/constants/metatile_behaviors.h').read_text().splitlines():
        m = re.match(r'\s*(MB_\w+)(\s*=\s*(\w+))?,', line)
        if m:
            i = int(m.group(3), 0) if m.group(3) else i
            names[i] = m.group(1)
            i += 1
    return names


def emerald_tiles(emerald):
    head = subprocess.run(['git', '-C', str(emerald), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout
    if head.strip() != COMMIT:
        raise SystemExit(f'pokeemerald at {head.strip()!r}, expected {COMMIT}')
    names = behaviours(emerald)
    lay, ts = emerald / 'data/layouts', emerald / 'data/tilesets'
    west, east = u16s(lay / 'BattleFrontier_OutsideWest/map.bin'), u16s(lay / 'BattleFrontier_OutsideEast/map.bin')
    attrs = {'gen': u16s(ts / 'primary/general/metatile_attributes.bin'),
             'W': u16s(ts / 'secondary/battle_frontier_outside_west/metatile_attributes.bin'),
             'E': u16s(ts / 'secondary/battle_frontier_outside_east/metatile_attributes.bin')}
    out = {}
    for y in range(H):
        for x in range(W):
            side, v = ('W', west[y * WEST + x]) if x < WEST else ('E', east[y * (W - WEST) + x - WEST])
            mt = v & 0x3ff
            a = attrs['gen'][mt] if mt < 512 else attrs[side][mt - 512]
            out[x, y] = {'mt': mt, 'blocked': (v >> 10) & 3 != 0, 'beh': names.get(a & 0xff, hex(a & 0xff))}
    return out


def colours():
    from PIL import Image
    im = Image.open(PICTURE).convert('RGB')
    if im.size != (W * 16, H * 16):
        raise SystemExit(f'{PICTURE}: {im.size}, expected {(W * 16, H * 16)}')
    px = im.load()
    out = {}
    for y in range(H):
        for x in range(W):
            cols = [px[x * 16 + i, y * 16 + j] for j in range(16) for i in range(16)]

            def share(pred):
                return sum(1 for c in cols if pred(*c)) / len(cols)
            out[x, y] = {
                'water': share(lambda r, g, b: b > r + 50 and b > g + 30),
                'green': share(lambda r, g, b: g > r + 25 and g > b + 5),
                'dark': share(lambda r, g, b: g > r + 25 and g > b + 5 and g < 170),
                'brown': share(lambda r, g, b: r > g + 15 and g >= b - 5 and 90 < r < 220),
                'light': share(lambda r, g, b: min(r, g, b) > 185),
                'sand': share(lambda r, g, b: r > 180 and g > 150 and b < 150 and r > b + 50),
            }
    return out


def inside(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def components(cells):
    comp, n = {}, 0
    for k in sorted(cells):
        if k in comp:
            continue
        comp[k], todo = n, [k]
        while todo:
            x, y = todo.pop()
            for j in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if j in cells and j not in comp:
                    comp[j] = n
                    todo.append(j)
        n += 1
    return comp


def trace(emerald):
    em, col = emerald_tiles(emerald), colours()
    stairs = {k for k, t in em.items() if t['mt'] in STAIR_METATILES} - GANGWAY
    door_tiles = set(DOORS.values())
    g = {}
    for (x, y), t in em.items():
        c, k = col[x, y], (x, y)
        water = 'WATER' in t['beh'] and 'FALL' not in t['beh']
        if k in door_tiles:
            g[k] = '+'
        elif any(inside(b, x, y) for b in BUILDINGS.values()):
            g[k] = 'B'
        elif any(inside(b, x, y) for b in BEDS):
            g[k] = 'p'
        elif 'WATERFALL' in t['beh'] or k in CAVE or inside(CAVE_YARD, x, y):
            g[k] = '#'
        elif water or (t['blocked'] and c['water'] > 0.5):
            g[k] = '~'
        elif not t['blocked']:
            g[k] = (':' if any(inside(p, x, y) for p in PATHS) else '=' if k in stairs else 'm' if k in GANGWAY or inside(PIER, x, y)
                    else 's' if c['sand'] > 0.35 else '.' if c['light'] >= 0.25 and c['light'] + c['green'] >= 0.6
                    and c['green'] < 0.6 else ',' if c['green'] >= 0.5 else '.' if c['light'] > 0.45 else ':')
        elif inside(PIER, x, y):
            g[k] = '#' if c['brown'] > 0.3 else 'f' if c['light'] > 0.3 else '~'
        else:
            best = max(('water', 'dark', 'brown', 'light'), key=lambda f: c[f])
            g[k] = (('f' if c['light'] >= 0.1 else 'x') if c[best] < 0.2 else '~' if best == 'water' else 'T' if best == 'dark'
                    else ('o' if inside(ROCKS, x, y) else '#') if best == 'brown' else 'f')
    # walkable specks no one reaches (flag poles standing in the sea, beyond the fences): banners
    walk = components({k for k, v in g.items() if v in WALKABLE})
    size = collections.Counter(walk.values())
    for k, n in walk.items():
        if size[n] <= 4 and g[k] != '+':
            g[k] = 'f'
    # sea or pond; blue specks of a few tiles are painted things (arch pillars, windows), not water
    wet = components({k for k, v in g.items() if v == '~'})
    edge = {wet[k] for k in wet if k[0] in (0, W - 1) or k[1] in (0, H - 1)}
    size = collections.Counter(wet.values())
    for k, n in wet.items():
        if n not in edge:
            g[k] = 'w' if size[n] > 4 else 'x'
    return g, heights(g, em, stairs)


def heights(g, em, stairs):
    walk = {k for k, v in g.items() if v in WALKABLE and k not in stairs}
    comp = components(walk)
    size = collections.Counter(comp.values())
    plaza = comp[(26, 45)]
    level = {plaza: PLAZA_LEVEL, comp[FERRY]: PIER_LEVEL}
    # every stair run: the area north of it is one above the area south of it
    changed = True
    while changed:
        changed = False
        for x, y in stairs:
            n = s = None
            for d in range(1, 4):
                n = comp.get((x, y - d)) if n is None else n
                s = comp.get((x, y + d)) if s is None else s
            if n is None or s is None:
                continue
            if s in level and n not in level:
                level[n], changed = level[s] + 1, True
            elif n in level and s not in level:
                level[s], changed = level[n] - 1, True
    seeds = {k: level[c] for k, c in comp.items() if c in level and size[c] > 3}
    ponds = components({k for k, v in g.items() if v == 'w'})
    big = {n for n, c in collections.Counter(ponds.values()).items() if c > POND} | {ponds[k] for k in LOW_PONDS}
    big -= {ponds[k] for k in HIGH_PONDS}
    for k, v in g.items():
        if v == '~' or (v == 'w' and ponds[k] in big):
            seeds[k] = 0
    for name, box in BUILDINGS.items():      # a building stands at its door's (or its front's) height
        x0, y0, x1, y1 = box
        front = [(x, y1 + 1) for x in range(x0, x1 + 1)] + [(x, y0 - 1) for x in range(x0, x1 + 1)]
        level_at = [seeds[f] for f in front if f in seeds and g[f] in WALKABLE]
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                seeds[x, y] = max(level_at, default=PLAZA_LEVEL)
    for k in stairs:
        north = min((seeds[(k[0], k[1] - d)] for d in range(1, 4) if (k[0], k[1] - d) in seeds), default=None)
        seeds[k] = north if north is not None else PLAZA_LEVEL
    h = dict(seeds)
    frontier = list(seeds)
    while frontier:            # breadth first: nearest seed wins, ties to the higher
        nxt = {}
        for x, y in frontier:
            for j in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if j in g and j not in h:
                    nxt[j] = max(nxt.get(j, 0), h[(x, y)])
        h.update(nxt)
        frontier = list(nxt)
    return h


WALKABLE = set('.:,sm=+')


def write(g, h):
    grid = '\n'.join(''.join(g[x, y] for x in range(W)) for y in range(H))
    hgt = '\n'.join(''.join(str(h[x, y]) for x in range(W)) for y in range(H))
    doors = ''.join(f'    {k!r}: {v},\n' for k, v in DOORS.items())
    reserved = ''.join(f'    {k!r}: {v},\n' for k, v in RESERVED.items())
    buildings = ''.join(f'    {k!r}: {v},\n' for k, v in BUILDINGS.items())
    OUT.write_text(f'''"""Emerald's Battle Frontier outside traced tile by tile (F11-ISLA-TRAZADO; reports/diseno/isla-esmeralda.md).

Generated by frontier/island_trace.py from pret/pokeemerald {COMMIT[:8]} (map.bin collision, behaviours,
warp_events) and reports/diseno/referencias/frente-esmeralda.webp (16 px per tile). Do not edit by hand: change the
tracer's boxes and run it again. Emerald coordinates: x 0-55 is BattleFrontier_OutsideWest, 56-127 is
OutsideEast (its x + 56); the ORAS map is 4x2 cells (160x80) with this grid at OFFSET and sea around it.
"""
W, H = {W}, {H}
CELLS = (4, 2)                  # ORAS map cells of 40x40 tiles
# Where the trace sits on the ORAS map: (15, 6), not centred (16, 4), so that no provisional facility building
# (frontier/island_build.py FACILITIES) straddles a cell edge: a building is stamped into one 40x40 cell (F11).
OFFSET = (15, 6)
LEGEND = {{
    '~': 'mar', 'w': 'estanque (agua rodeada de tierra)', '.': 'suelo de baldosa clara', ':': 'camino',
    ',': 'hierba / cesped', 's': 'arena (recinto de la Piramide)', 'm': 'muelle', '=': 'escalera (sube al norte)',
    '#': 'acantilado', 'T': 'arbol / seto', 'p': 'parterre', 'o': 'roca', 'f': 'valla / banderin',
    'x': 'decoracion que bloquea (farola, letrero, estatua)', 'B': 'hueco de edificio', '+': 'puerta',
}}
WALKABLE = set('.:,sm=+')
# Facility and reception doors (warp_events): the island warps go here.
DOORS = {{
{doors}}}
# Huecos reserved without a door (isla-esmeralda.md §1): the tile Emerald's door is on.
RESERVED_DOORS = {{
{reserved}}}
# Building huecos, inclusive tile boxes x0, y0, x1, y1 (hand-measured on the picture).
BUILDINGS = {{
{buildings}}}
FERRY = {FERRY}             # where Emerald's ferry leaves the player (warp ... OUTSIDE_WEST, 19, 67)
GRID = """
{grid}
"""[1:-1].split('\\n')
# Height level per tile: 0 water, 1 pier and landing, 2 plaza, 3 upper terraces (Dome/Tower, Pyramid, Arena).
HEIGHT = """
{hgt}
"""[1:-1].split('\\n')
''')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--emerald', type=Path, required=True)
    args = ap.parse_args()
    g, h = trace(args.emerald)
    write(g, h)
    print(OUT, collections.Counter(g.values()).most_common())


if __name__ == '__main__':
    main()
