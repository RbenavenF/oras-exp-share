"""Battle Frontier F6: the island zones, built with CTRMap-F5 (faraway/java/faraway/Build.java) on a staged copy.

First functional island (provisional geometry, reports/frontier.md §18):
- zone 209 «Isla del Frente»: clone of the Battle Resort harbor (212) with its own map and area. Its NPCs and
  triggers are dropped (Wally's arrival scene and family) and the ferry clerk comes back as NPC uid 0 running the
  harbor's own event 2 (GlobalCall 10430): from a zone that is neither Slateport nor Lilycove the ferry offers both,
  which is the way back. The pier's north warp is replaced by the plaza's Factory door (below). The harbor's script
  keeps events -1 (empty), 1 (arrival) and 2 (the clerk) and drops 3 (Wally's trigger). Event 1 runs on arrival:
  while work 16615 is 0 it plays Wally's first-visit scene, which moves NPCs 1-3 the island does not have (the game
  hangs, seen in Azahar); otherwise it jumps to 0x3f28: horn, fade-in, WorkSet(16707, 0). Without event 1 the screen
  stays white (also seen). The island's event 1 always takes the 0x3f28 path.
- zone 213: clone of the Battle Maison hall (517), the one that holds the Factory, with the Maison's story text
  (619) and the Factory-patched script; its exit (warp 0) leads back to the Factory door on the plaza. code.bin
  registers the Maison natives only in zones 448, 517 and 520 (per-zone native groups, frontier/patch.py
  ZONE_NATIVES): without 517's groups every event of the hall fails and the game hangs, so overlay.py passes CLONES
  to patch.build, which gives every clone its donor's groups.
- The exterior (F11-ISLA-CONSTRUCCION; island_rows, FACILITIES, faraway/java/ctrmap/tests/FrontierIsland.java):
  after the clones, the island's private map becomes 4x2 painted cells, the Emerald Frontier outside traced by
  frontier/island_layout.py at its OFFSET, with one provisional catalogue building per facility, its door on the
  facility's Emerald door tile and its swinging-door prop. The island's warps are replaced by one door warp per
  facility, in FACILITIES order, into its interior (whose exit, warp 0, comes back to it), and the ferry clerk moves to
  the pier beside island.ARRIVAL. Flat runs of identical floor tiles are merged losslessly (IslandFloors), map
  textures are kept in the world pack (§23) and the load budget must stay within ISLAND_BUDGET (retail Resort 211).
  The old v0.2 plaza (one painted cell over the cloned harbor, faraway/java/faraway/Plaza.java) is no longer built.
Both slots were chosen with CTRMap-F5's ZoneRepurposeScanner (empty, no incoming warps, no script or shared script
sends the player there; §18); both keep their placeholder entity scripts (517's is empty as well).

The staged copy holds the archives CTRMap reads (faraway/build.py STAGED), from --romfs file by file with the
Repolished baseline as fallback, with the overlay's own archives (zones 517/317 etc.) on top, so the clones inherit
the patched scripts. Only the zone archives may change; anything else is an error.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import build_patch  # noqa: E402
from formats import garc_entries, lz11_decompress, text_lines, words_to_text, zo_files  # noqa: E402
from pawn import OP, Op, Program, Script  # noqa: E402
import factory  # noqa: E402
import island  # noqa: E402
import island_layout  # noqa: E402
import pyramid  # noqa: E402
import dome_room  # noqa: E402

STAGED = ['a/0/1/4', 'a/0/3/9', 'a/0/4/0', 'a/0/7/3', 'a/0/8/1', 'a/0/1/3', 'a/0/2/3', 'a/1/3/7', 'a/0/2/1',
          'a/0/3/6', 'a/0/3/7', 'a/0/3/8', 'a/1/9/5', 'a/1/8/9', 'a/1/9/7', 'a/0/2/9', 'a/1/8/2', 'a/1/8/3',
          'a/1/8/4', 'a/1/8/5', 'a/1/8/6']          # as faraway/build.py: what CTRMap-F5's ORAS profile opens
ZONE_ARCHIVES = {'a/0/1/3', 'a/0/1/4', 'a/0/3/9', 'a/0/4/0', 'a/1/3/7', 'a/0/2/1'}

ZONE_ISLAND, ZONE_HALL = island.ZONE_ISLAND, 213
DONOR_ISLAND, DONOR_HALL = 212, 517
PLACE = 279                    # empty odd location-name slot in all 8 languages (277 is the Mew event's)
PLACE_TEXT = 90                # game text entry of location names
PLACE_NAME = {'es': 'Isla del Frente', 'en': 'Frontier Island'}
CLERK = (300, 300, 2, 0, 54, 34, 0, 2)   # model, MoveModel, event, flag, x, y, height, face: zone 212's NPC 0
ZONE_TOWER = 329              # the Tower's interior (frontier/tower.py; REPARTO.md; checked by frontier/zone_check.py)
ZONE_DOME = 456               # the Dome's interior (frontier/dome.py; idem, reports/frontier.md §26)
ZONE_PALACE = 340             # the Palace's interior (frontier/palace.py; idem, reports/frontier.md §27)
ZONE_PIKE = 458               # the Pike's interior (frontier/pike.py; idem, reports/frontier.md §28)
ZONE_ARENA = 457              # the Arena's interior (frontier/arena.py; idem, reports/frontier.md §29)
ZONE_PYRAMID = pyramid.LOBBY  # the Pyramid's lobby (140) and floors (141, 142) (frontier/pyramid.py; §30)
CLONES = {ZONE_ISLAND: DONOR_ISLAND, ZONE_HALL: DONOR_HALL,   # slot: donor of its map, area, entities and script
          ZONE_TOWER: DONOR_HALL, ZONE_DOME: dome_room.DONOR, ZONE_PALACE: DONOR_HALL,
          ZONE_PIKE: DONOR_HALL, ZONE_ARENA: DONOR_HALL, ZONE_PYRAMID: DONOR_HALL, **{z: pyramid.FLOOR_DONOR for z in pyramid.FLOORS}}
# Facility zones are added here by the integrator (frontier/REPARTO.md). Every clone gets the place name PLACE; one in
# KEEP_TEXT keeps its donor's story text (the Maison's 619 for a 517 clone); one in NATIVE_DONORS registers that
# zone's native groups instead of its donor's (a floor cloned from a cave that runs Maison battles needs 517's).
KEEP_TEXT = {ZONE_HALL, ZONE_TOWER, ZONE_DOME, ZONE_PALACE, ZONE_PIKE, ZONE_ARENA, *pyramid.ZONES}
NATIVE_DONORS = {ZONE_DOME: dome_room.NATIVE_DONOR, **{z: DONOR_HALL for z in pyramid.FLOORS}}


def native_donors():
    """slot: zone whose native groups it registers (patch.zone_natives)."""
    return {**CLONES, **NATIVE_DONORS}

# F11-ISLA-CONSTRUCCION (reports/diseno/isla-esmeralda.md §2-§3): the island is Emerald's Battle Frontier outside,
# traced tile by tile (frontier/island_layout.py) and painted 1:1 over 4x2 map cells at island_layout.OFFSET by
# CTRMap-F5 (faraway/java/ctrmap/tests/FrontierIsland.java). Each facility keeps today's provisional catalogue building
# (one distinct building each, among the cheapest catalogue houses besides the Gym, reports/frontier.md §24), now
# stamped with its door on the facility's Emerald door tile; the rest of the facility's hueco (island_layout.BUILDINGS,
# the definitive building's silhouette) is reserved rock, as are the huecos of the Pokemon Center, Mart, Ranking Hall,
# Scott's house, Exchange and lounges, which have no door. Left out: the Pokemon Center and the Mart as provisional
# buildings, the Pacifidlog stilt hut and Lanette's house (the game draws neither; §24).
FACILITY_BUILDINGS = {
    'Tower': 'Rustboro flat-roof house',
    'Dome': 'Fallarbor house',
    'Factory': 'Gym',
    'Pyramid': 'Dewford shingle house',
    'Pike': 'Route 124 treasure cabin',
    'Arena': 'Battle Resort thatched house',
    'Palace': 'Rustboro two-story house',
}


def map_tile(x, y):
    """ORAS map tile of an Emerald (trace) tile."""
    return x + island_layout.OFFSET[0], y + island_layout.OFFSET[1]


# facility: (catalogue building, its door's map tile x, y)
FACILITIES = {f: (name, *map_tile(*island_layout.DOORS[f])) for f, name in FACILITY_BUILDINGS.items()}
# Facilities whose building keeps the cut's passengers (shadow decals, terrain chips, sea planes around it).
PASSENGERS = set(FACILITY_BUILDINGS)
# Catalogue buildings the painter cuts and places but the game does not draw on the island (collision and door prop
# only; Azahar, reports/frontier.md §24). plan() refuses them.
NOT_DRAWN = {'Pacifidlog stilt hut', "Route 114 Lanette's house"}
# Plaza's "load budget": the area's world pack + prop pack + the map models of all the zone's regions, unpacked. The
# largest measured to load in Azahar with the old plaza; 2986112 and up hung there (reports/frontier.md §23). Still
# the bound of the facility interiors (dome_room, pyramid). Not the engine's limit.
LOAD_BUDGET = 2724608
ZO_LIMIT = pyramid.ZO_LIMIT    # the largest zone container measured to load (reports/frontier.md §11)
# The island's own bound (F11): the retail Battle Resort exterior, zone 211, measured with the same metric
# (reports/diseno/isla-esmeralda.md §2.1, reports/frontier.md F11 hito 2, frontier/probes/island/survey.sh). What the
# game ships loads on a console; the island has to stay at or below it.
ISLAND_BUDGET = 4192384
DOORS = {'Tower': (ZONE_TOWER, 0), 'Dome': (ZONE_DOME, 0), 'Factory': (ZONE_HALL, 0), 'Palace': (ZONE_PALACE, 0),
         'Pike': (ZONE_PIKE, 0), 'Arena': (ZONE_ARENA, 0), 'Pyramid': (ZONE_PYRAMID, 0)}   # facility: (zone, warp) its door leads to (island warps follow FACILITIES order)
# The ferry clerk (NPC 0) stands on the pier one tile west of where the ferry leaves the player (island.ARRIVAL).
CLERK_FACE = 3
CATALOGUE = ROOT / 'tools/CTRMap-F5/src/ctrmap/resources/oras_buildings.tsv'
# The reception (island_layout.DOORS ReceptionNorth/South) has no building yet: a one-tile passage crosses its hueco
# from the pier landing (stair at its south door) to the plaza (its north door), as in the F11 terrain prototype.
RECEPTION_PASSAGE = [(26, y) for y in range(61, 66)]


def catalogue(name):
    """(tiles wide, tiles high, door dx, door dy, door prop) of a CTRMap-F5 catalogue building."""
    for line in CATALOGUE.read_text().splitlines():
        f = line.split('\t')
        if len(f) > 11 and not line.startswith('#') and f[1] == name:
            tx0, ty0, tx1, ty1 = map(int, f[4:8])
            return tx1 - tx0 + 1, ty1 - ty0 + 1, int(f[9]), int(f[10]), f[11]
    raise ValueError(f'no catalogue building {name!r} in {CATALOGUE}')


def building_box(facility):
    """Inclusive map-tile box x0, y0, x1, y1 the facility's provisional building covers."""
    name, x, y = FACILITIES[facility]
    w, h, dx, dy, _ = catalogue(name)
    return x - dx, y - dy, x - dx + w - 1, y - dy + h - 1


def island_rows():
    """Class rows then height rows of the whole map (frontier/island_layout.py at OFFSET, sea around it), with the
    reception passage open and the hueco tiles under each provisional building painted as floor (the building's own
    footprint blocks them)."""
    w, h = island_layout.CELLS[0] * 40, island_layout.CELLS[1] * 40
    rows = [['~'] * w for _ in range(h)]
    heights = [['0'] * w for _ in range(h)]
    for y in range(island_layout.H):
        for x in range(island_layout.W):
            mx, my = map_tile(x, y)
            rows[my][mx], heights[my][mx] = island_layout.GRID[y][x], island_layout.HEIGHT[y][x]
    for x, y in RECEPTION_PASSAGE:
        mx, my = map_tile(x, y)
        rows[my][mx], heights[my][mx] = ('=' if y == RECEPTION_PASSAGE[-1][1] else ':'), '2'
    for facility in FACILITIES:
        x0, y0, x1, y1 = building_box(facility)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rows[y][x] == 'B':
                    rows[y][x] = '.'
    return [''.join(r) for r in rows + heights]


ISLAND_EVENTS = {-1, 1, 2}      # zone 212's events the island keeps: -1 empty, 1 arrival, 2 the ferry clerk
DONOR_EVENTS = {-1, 1, 2, 3}
WORK_RESORT_SCENE = 16615       # 0 until Wally's Battle Resort scene has played
ARRIVAL_EVENT, ARRIVAL_PLAIN = 1, 'L3f28'


def island_script(donor):
    """Zone 212's script with its main dispatcher reduced to ISLAND_EVENTS and event 1 without Wally's scene."""
    p = Program.from_script(donor)
    main = f'L{donor.main:x}'
    start = p.items.index(('label', main))
    table = next(op for op in p.items[start:] if isinstance(op, Op) and op.op == OP['CASETBL'])
    cases = dict(zip(table.args[2::2], table.args[3::2]))
    if set(cases) != DONOR_EVENTS:
        raise ValueError(f'zone {DONOR_ISLAND}: unexpected events {sorted(cases)}')
    kept = [(v, cases[v]) for v in sorted(ISLAND_EVENTS)]
    table.args = [len(kept), table.args[1]] + [x for pair in kept for x in pair]
    # The arrival case stub calls the arrival routine; its head reads WORK_RESORT_SCENE and skips the scene if set.
    stub = [op for op in p.items[p.items.index(('label', cases[ARRIVAL_EVENT])):] if isinstance(op, Op)][:2]
    routine = stub[1].args[0]
    head = [op for op in p.items[p.items.index(('label', routine)):] if isinstance(op, Op)][:7]
    expected = [('PROC', None), ('STACK_P', [-4]), ('PUSH_P_C', [WORK_RESORT_SCENE]), ('SYSREQ_N', None),
                ('STOR_P_S_PRI', [-4]), ('LOAD_P_S_PRI', [-4]), ('JNZ', [ARRIVAL_PLAIN])]
    if stub[1].op != OP['CALL'] or any(op.op != OP[name] or (args is not None and op.args != args)
                                       for op, (name, args) in zip(head, expected)) \
            or head[3].args[0] != p.native('WorkGet'):
        raise ValueError(f'zone {DONOR_ISLAND}: arrival event does not start with the Resort scene check')
    head[6].op = OP['JUMP']
    return p.build_script(main)


def door_warp(facility):
    """The island warp of a facility's door: Island adds one per door, in FACILITIES order (FrontierIsland.build)."""
    return [f for f in FACILITIES if f in DOORS].index(facility)


def plan(scripts):
    lines = [
        f'scripts={scripts}',
        'clones=' + ','.join(f'{donor}:{slot}' for slot, donor in CLONES.items()),
        *(f'place.{slot}={PLACE}' for slot in CLONES),
        *(f'keeptext.{slot}=1' for slot in CLONES if slot in KEEP_TEXT),
        'zones=' + ','.join(map(str, CLONES)),
        f'zone.{ZONE_ISLAND}.clearNpcs=1', f'zone.{ZONE_ISLAND}.clearTriggers=1',
        f'zone.{ZONE_ISLAND}.npc.0=' + ','.join(str(v) for v in CLERK),
        f'island.zone={ZONE_ISLAND}', f'island.grid={Path(scripts).parent / "island-grid.txt"}',
        f'island.clerk={island.ARRIVAL[1] - 1},{island.ARRIVAL[3]},{CLERK_FACE}',
    ]
    names = [name for name, _, _ in FACILITIES.values()]
    if len(set(names)) != len(names) or NOT_DRAWN & set(names):
        raise ValueError(f'island buildings must be distinct and drawn (not {sorted(NOT_DRAWN)}): {names}')
    for facility, (zone, _) in DOORS.items():   # each interior's exit (its warp 0) comes back to its own door
        lines.append(f'zone.{zone}.warp.0=0,{ZONE_ISLAND},{door_warp(facility)}'
                     + (',2' if zone == ZONE_DOME else ''))
    for i, (facility, (name, x, y)) in enumerate(FACILITIES.items()):   # zone -1: a building without a warp
        lines.append(f'island.building.{i}={name}|{x}|{y}|' + '|'.join(map(str, DOORS.get(facility, (-1, 0))))
                     + ('' if facility in PASSENGERS else '|nopassengers'))
    if ZONE_DOME in CLONES:
        lines += dome_room.plan_lines(LOAD_BUDGET)
    lines += pyramid.plan_lines()   # the Pyramid's floors: NPCs and exit to its lobby
    return '\n'.join(lines) + '\n'


def place_names(archives, source):
    """Location name PLACE in every game text (on top of `archives`, else `source(rel)`)."""
    out = {}
    for lang, path in factory.GAMETEXT.items():
        data = archives.get(path) or source(path)
        _, _, offset, length = next(e for e in garc_entries(data) if e[0] == PLACE_TEXT)
        before = words_to_text(text_lines(data[offset:offset + length])[0][PLACE])
        if before.strip():
            raise ValueError(f'{path}: location name {PLACE} is not empty ({before!r})')
        out[path] = build_patch.guarded_texts(data, {'path': path, 'texts': [
            {'entry': PLACE_TEXT, 'line': PLACE, 'before': before, 'after': PLACE_NAME[factory.LANG[lang]]}]})
    return out


def build(archives, source, work, zone_scripts=None):
    """{romfs path: archive}: `archives` plus the zone archives the Java build changed and the place name.
    `source(rel)` reads an input archive; `work` is a scratch directory under work/. `zone_scripts` = {clone: script
    bytes} for facility zones (a clone without one keeps its donor's script); the island's is built here."""
    zone_scripts = dict(zone_scripts or {})
    stray = set(zone_scripts) - set(CLONES) | ({ZONE_ISLAND} & set(zone_scripts))
    if stray:
        raise ValueError(f'zone scripts for zones that are not facility clones: {sorted(stray)}')
    if work.exists():
        shutil.rmtree(work)
    game = work / 'game'
    staged = {}
    for rel in STAGED:
        staged[rel] = archives.get(rel) or source(rel)
        (game / rel).parent.mkdir(parents=True, exist_ok=True)
        (game / rel).write_bytes(staged[rel])
    (game / 'sound').mkdir()
    (game / 'sound/sango_sound.bcsar').write_bytes(b'')
    scripts = work / 'scripts'
    scripts.mkdir()                     # the hall keeps its donor's (Factory) script; the island gets its own
    zones = staged['a/0/1/3']
    _, _, offset, length = garc_entries(zones)[DONOR_ISLAND]
    donor = Script.parse(zo_files(lz11_decompress(zones[offset:offset + length]))[2])
    raw = island_script(donor).build()
    if Script.parse(raw).build() != raw:
        raise ValueError('island script does not round-trip')
    (scripts / f'zone{ZONE_ISLAND}.bin').write_bytes(raw)
    for slot, script in zone_scripts.items():
        if Script.parse(script).build() != script:
            raise ValueError(f'zone {slot} script does not round-trip')
        (scripts / f'zone{slot}.bin').write_bytes(script)
    (work / 'island-grid.txt').write_text('\n'.join(island_rows()) + '\n')
    (work / 'plan.properties').write_text(plan(scripts))
    log = work / 'java.log'
    with log.open('w') as stream:
        subprocess.run([str(ROOT / 'faraway/run.sh'), 'Build', str(game), str(work / 'ws'),
                        str(work / 'plan.properties')], stdout=stream, stderr=subprocess.STDOUT, check=True)
        subprocess.run([str(ROOT / 'faraway/run.sh'), 'Island', str(game), str(work / 'ws'),
                        str(work / 'plan.properties')], stdout=stream, stderr=subprocess.STDOUT, check=True)
    text = log.read_text()
    for zone in CLONES:
        if f'zone {zone} cloned from' not in text:
            raise ValueError(f'Java build did not clone zone {zone}: {text}')
    check_island_log(text)
    out = dict(archives)
    for rel in STAGED:
        new = (game / rel).read_bytes()
        if new != staged[rel]:
            if rel not in ZONE_ARCHIVES:
                raise ValueError(f'Java build changed {rel}')
            out[rel] = new
    for zone in pyramid.FLOORS:
        _, _, offset, length = garc_entries(out['a/0/1/3'])[zone]
        pyramid.check_floor(lz11_decompress(out['a/0/1/3'][offset:offset + length]))
    if ZONE_DOME in zone_scripts:
        _, _, offset, length = garc_entries(out['a/0/1/3'])[ZONE_DOME]
        dome_room.check_room(lz11_decompress(out['a/0/1/3'][offset:offset + length]),
                             zone_scripts[ZONE_DOME], ZONE_ISLAND, door_warp('Dome'))
    check_budget(text)
    _, _, offset, length = garc_entries(out['a/0/1/3'])[ZONE_ISLAND]
    size = len(lz11_decompress(out['a/0/1/3'][offset:offset + length]))
    if size > ZO_LIMIT:
        raise ValueError(f'the island ZO is {size} bytes, over the {ZO_LIMIT} measured to load (reports/frontier.md §11)')
    out.update(place_names(out, source))
    return out, text


def check_island_log(text):
    """What FrontierIsland must have printed: eight painted cells, every building stamped in its cell with its door
    prop, one door warp per facility with a door on its door tile, the clerk on the pier and no map texture outside
    the world pack (reports/frontier.md §23)."""
    cells = re.findall(r'^cell (\d),(\d) region (\d+) .* buildings (\d+) door props (\d+)', text, re.M)
    if sorted((int(x), int(y)) for x, y, *_ in cells) != [(x, y) for x in range(4) for y in range(2)]:
        raise ValueError(f'the island was not painted over its eight cells: {text}')
    if sum(int(c[3]) for c in cells) != len(FACILITIES) or sum(int(c[4]) for c in cells) != len(FACILITIES):
        raise ValueError(f'the island did not stamp {len(FACILITIES)} buildings with their door props: {text}')
    for facility in DOORS:
        name, x, y = FACILITIES[facility]
        if f'warp {door_warp(facility)} door of {name} at tile {x},{y} ' not in text:
            raise ValueError(f'the {facility} door was not linked on its tile {x},{y}: {text}')
    if len(re.findall(r'^warp \d+ door of ', text, re.M)) != len(DOORS):
        raise ValueError(f'the island has warps that are not facility doors: {text}')
    if f'clerk at tile {island.ARRIVAL[1] - 1},{island.ARRIVAL[3]} ' not in text:
        raise ValueError(f'the ferry clerk is not on the pier: {text}')
    if 'outside the world pack: {}' not in text:
        raise ValueError(f'the island draws with textures its world pack lacks (§23): {text}')


def check_budget(text, bound=None):
    """The load budget Island printed (its last such line); refuses one over ISLAND_BUDGET or a log without one."""
    bound = ISLAND_BUDGET if bound is None else bound
    found = re.findall(r'^load budget (\d+) bytes', text, re.M)
    if not found:
        raise ValueError('Island printed no load budget')
    budget = int(found[-1])
    if budget > bound:
        raise ValueError(f'the island load budget is {budget} bytes, over the {bound} of the retail Resort 211 (F11)')
    return budget


def steps_from(at, rows):
    """The tiles one step from `at` on the island map (island_rows): walkable classes only (island_layout.WALKABLE),
    and a change of height level only by one level up or down a stair ('=') walked north-south."""
    h = len(rows) // 2
    x, y = at
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if not (0 <= nx < len(rows[0]) and 0 <= ny < h) or rows[ny][nx] not in island_layout.WALKABLE:
            continue
        delta = abs(int(rows[h + ny][nx]) - int(rows[h + y][x]))
        if delta and not (delta == 1 and '=' in (rows[ny][nx], rows[y][x]) and nx == x):
            continue
        yield nx, ny


def route(start, goal=None, rows=None):
    """Shortest walk on the island map from `start` to `goal` (map tiles), as the list of tiles; raises if there is
    none. With no goal: {tile: previous tile} of everything reached. Used by the tests and the lab's circuit."""
    from collections import deque
    rows = rows or island_rows()
    queue, prev = deque([start]), {start: None}
    while queue:
        at = queue.popleft()
        if at == goal:
            steps = []
            while at is not None:
                steps.append(at)
                at = prev[at]
            return steps[::-1]
        for nxt in steps_from(at, rows):
            if nxt not in prev:
                prev[nxt] = at
                queue.append(nxt)
    if goal is None:
        return prev
    raise ValueError(f'no walk on the island from {start} to {goal}')


def corners(steps):
    """The turning points of a walk (and its end): what the lab's walker is given."""
    out = []
    for i in range(1, len(steps)):
        if i == len(steps) - 1 or (steps[i][0] - steps[i - 1][0], steps[i][1] - steps[i - 1][1]) != \
                (steps[i + 1][0] - steps[i][0], steps[i + 1][1] - steps[i][1]):
            out.append(steps[i])
    return out
