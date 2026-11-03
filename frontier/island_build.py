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
- The plaza (PLAZA_*, faraway/java/ctrmap/tests/FrontierPlaza.java): after the clones, CTRMap-F5's map painter
  repaints part of the island's own map cell (cell 0,1: the south half of the pier and the sea around it) as a path
  square with one catalogue building per Emerald facility (FACILITIES). Composite Apply: tiles outside the square
  keep the harbor's sea and pier. The painter wires no door; Plaza replaces the island's warps with one door warp,
  the Factory's, into the hall 213 (whose exit, warp 0, comes back to it). The other six buildings are mocks with no
  warp. Every building keeps its swinging-door prop. After the paint, Plaza copies into the area's world pack any
  map-model texture only its prop pack holds (the painter counts those as present, and the island then hangs on
  load; reports/frontier.md §23), and prints the load budget, which must stay within LOAD_BUDGET. Walking south from
  the dock leads onto the square.
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
CLONES = {ZONE_ISLAND: DONOR_ISLAND, ZONE_HALL: DONOR_HALL}   # slot: donor; also the native groups each copies

PLAZA_RECT = (1, 0, 39, 38)    # cell-local tiles x0, y0, x1, y1 of the island's own cell (0,1) painted as path
# Emerald facility: (catalogue building, anchor x, y). Only the Factory has a door (into the hall 213). Two house
# models repeat: every distinct building carries its textures into the island's area and grows the load budget
# (below); a repeated model carries nothing new.
FACILITIES = {
    'Tower': ('Dewford shingle house', 16, 2),
    'Dome': ('Lavaridge house', 4, 13),
    'Factory': ('Gym', 16, 13),
    'Pyramid': ('Lavaridge house', 30, 13),
    'Pike': ('Dewford shingle house', 3, 25),
    'Arena': ('Lavaridge house', 17, 25),
    'Palace': ('Dewford shingle house', 28, 25),
}
# Plaza's "load budget": the island area's world pack + prop pack + the map models of all the island's regions,
# unpacked. The largest measured to load in Azahar; 2986112 and up hung (reports/frontier.md §23). A measured bound,
# not the engine's limit, which was not found: retail areas hold larger texture packs.
LOAD_BUDGET = 2724608
DOORS = {'Factory': (ZONE_HALL, 0)}   # facility: (zone, warp) its door leads to (island warps follow FACILITIES order)


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


def plan(scripts):
    lines = [
        f'scripts={scripts}',
        'clones=' + ','.join(f'{donor}:{slot}' for slot, donor in CLONES.items()),
        f'place.{ZONE_ISLAND}={PLACE}', f'place.{ZONE_HALL}={PLACE}',
        f'keeptext.{ZONE_HALL}=1',
        f'zones={ZONE_ISLAND},{ZONE_HALL}',
        f'zone.{ZONE_ISLAND}.clearNpcs=1', f'zone.{ZONE_ISLAND}.clearTriggers=1',
        f'zone.{ZONE_ISLAND}.npc.0=' + ','.join(str(v) for v in CLERK),
        f'zone.{ZONE_HALL}.warp.0=0,{ZONE_ISLAND},0',
        f'plaza.zone={ZONE_ISLAND}', 'plaza.rect=' + ','.join(map(str, PLAZA_RECT)),
        'plaza.heightof=0',            # the pier's warp: the painted square lies at the pier's ground
    ]
    for i, (facility, (name, x, y)) in enumerate(FACILITIES.items()):
        lines.append(f'plaza.building.{i}={name}|{x}|{y}')
        if facility in DOORS:
            lines.append(f'plaza.door.{i}=' + ','.join(map(str, DOORS[facility])))
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


def build(archives, source, work):
    """{romfs path: archive}: `archives` plus the zone archives the Java build changed and the place name.
    `source(rel)` reads an input archive; `work` is a scratch directory under work/."""
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
    (work / 'plan.properties').write_text(plan(scripts))
    log = work / 'java.log'
    with log.open('w') as stream:
        subprocess.run([str(ROOT / 'faraway/run.sh'), 'Build', str(game), str(work / 'ws'),
                        str(work / 'plan.properties')], stdout=stream, stderr=subprocess.STDOUT, check=True)
        subprocess.run([str(ROOT / 'faraway/run.sh'), 'Plaza', str(game), str(work / 'ws'),
                        str(work / 'plan.properties')], stdout=stream, stderr=subprocess.STDOUT, check=True)
    text = log.read_text()
    for zone in (ZONE_ISLAND, ZONE_HALL):
        if f'zone {zone} cloned from' not in text:
            raise ValueError(f'Java build did not clone zone {zone}: {text}')
    painted = f'Painted map applied to zone {ZONE_ISLAND}' in text
    if not painted or f'{len(FACILITIES)} door(s) left unwired' not in text:
        raise ValueError(f'the plaza was not painted: {text}')
    if 'Swinging-door prop(s) placed' not in text:
        raise ValueError(f'the plaza placed no door props: {text}')
    if 'world textures copied from the prop pack:' not in text:
        raise ValueError(f'Plaza did not keep the map textures in the world pack (§23): {text}')
    for i, facility in enumerate(f for f in FACILITIES if f in DOORS):   # Plaza adds door warps in building order
        name = FACILITIES[facility][0]
        if f'warp {i} door of {name} at tile' not in text:
            raise ValueError(f'the {facility} door was not linked: {text}')
    out = dict(archives)
    for rel in STAGED:
        new = (game / rel).read_bytes()
        if new != staged[rel]:
            if rel not in ZONE_ARCHIVES:
                raise ValueError(f'Java build changed {rel}')
            out[rel] = new
    check_budget(text)
    out.update(place_names(out, source))
    return out, text


def check_budget(text):
    """The load budget Plaza printed (its last such line); refuses one over LOAD_BUDGET or a log without one."""
    found = re.findall(r'^load budget (\d+) bytes', text, re.M)
    if not found:
        raise ValueError('Plaza printed no load budget')
    budget = int(found[-1])
    if budget > LOAD_BUDGET:
        raise ValueError(f'the island load budget is {budget} bytes, over the {LOAD_BUDGET} measured to load (§23)')
    return budget
