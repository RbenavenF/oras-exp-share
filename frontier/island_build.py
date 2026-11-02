"""Battle Frontier F6: the island zones, built with CTRMap-F5 (faraway/java/faraway/Build.java) on a staged copy.

First functional island (provisional geometry, reports/frontier.md §18):
- zone 209 «Isla del Frente»: clone of the Battle Resort harbor (212) with its own map and area. Its NPCs and
  triggers are dropped (Wally's arrival scene and family) and the ferry clerk comes back as NPC uid 0 running the
  harbor's own event 2 (GlobalCall 10430): from a zone that is neither Slateport nor Lilycove the ferry offers
  both, which is the way back. Walking north off the pier (warp 0) enters zone 213. The harbor's script keeps
  events -1 (empty), 1 (arrival) and 2 (the clerk) and drops 3 (Wally's trigger). Event 1 runs on arrival: while
  work 16615 is 0 it plays Wally's first-visit scene, which moves NPCs 1-3 the island does not have (the game
  hangs, seen in Azahar); otherwise it jumps to 0x3f28: horn, fade-in, WorkSet(16707, 0). Without event 1 the
  screen stays white (also seen). The island's event 1 always takes the 0x3f28 path.
- zone 213: clone of the Battle Maison hall (517), the one that holds the Factory, with the Maison's story text
  (619) and the Factory-patched script; its exit (warp 0) leads back to the pier.
Both slots were chosen with CTRMap-F5's ZoneRepurposeScanner (empty, no incoming warps, no script or shared
script sends the player there; §18); both keep their placeholder entity scripts (517's is empty as well).

The staged copy holds the archives CTRMap reads (faraway/build.py STAGED), from --romfs file by file with the
Repolished baseline as fallback, with the overlay's own archives (zones 517/317 etc.) on top, so the clones
inherit the patched scripts. Only the zone archives may change; anything else is an error.
"""
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
        f'clones={DONOR_ISLAND}:{ZONE_ISLAND},{DONOR_HALL}:{ZONE_HALL}',
        f'place.{ZONE_ISLAND}={PLACE}', f'place.{ZONE_HALL}={PLACE}',
        f'keeptext.{ZONE_HALL}=1',
        f'zones={ZONE_ISLAND},{ZONE_HALL}',
        f'zone.{ZONE_ISLAND}.clearNpcs=1', f'zone.{ZONE_ISLAND}.clearTriggers=1',
        f'zone.{ZONE_ISLAND}.warp.0=0,{ZONE_HALL},0',
        f'zone.{ZONE_ISLAND}.npc.0=' + ','.join(str(v) for v in CLERK),
        f'zone.{ZONE_HALL}.warp.0=0,{ZONE_ISLAND},0',
    ]
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
    text = log.read_text()
    for zone in (ZONE_ISLAND, ZONE_HALL):
        if f'zone {zone} cloned from' not in text:
            raise ValueError(f'Java build did not clone zone {zone}: {text}')
    out = dict(archives)
    for rel in STAGED:
        new = (game / rel).read_bytes()
        if new != staged[rel]:
            if rel not in ZONE_ARCHIVES:
                raise ValueError(f'Java build changed {rel}')
            out[rel] = new
    out.update(place_names(out, source))
    return out, text
