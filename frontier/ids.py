#!/usr/bin/env python3
"""Find saved works (0x4000-0x4177) that nothing in the game uses, for the Battle Factory state. Read-only.

Same method as the Faraway Island identifiers (reports/faraway.md): a work counts as used if its number
appears as an operand in any retail script (zone, entity and shared; the listing over-approximates, every
numeric operand counts), as a u16 anywhere in a zone's entity data before its script (NPC, warps,
triggers), or as a code literal in code.bin, static.crs or any CRO (aligned 32-bit word, or an ARM
data-processing immediate). Works computed at run time (base + index) cannot be seen this way, so the
candidates also list their value in the user's save and in the laboratory saves.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'faraway')]
from formats import garc_entries  # noqa: E402
from pawn import Script, listing  # noqa: E402
import build as fb  # noqa: E402
import save_event as se  # noqa: E402

GAME = ROOT / 'baseline/oras/repolished'
WORKS = range(se.WORK_BASE, se.WORK_BASE + se.WORK_COUNT)
KNOWN = {16665: 'Mew event: progress', 16667: 'Mew event: hiding spot'}  # faraway/event.py
SAVES = {'user save': ROOT / 'inputs/save/main', 'lab (F3, in the Maison)': ROOT / 'work/frontier/lab/f3_after.sav'}
NUMBER = re.compile(r'(?<![@\w])-?\d+\b')


def scripts(romfs):
    """(name, Script, raw entity data before the script or b'') for every retail script."""
    shared = (romfs / 'a/0/2/9').read_bytes()
    for i, (_, _, offset, length) in enumerate(garc_entries(shared)):
        yield f'shared {i}', Script.parse(shared[offset:offset + length]), b''
    count = len(garc_entries((romfs / 'a/0/1/3').read_bytes()))
    for zone in range(count):
        try:
            files = fb.zone_files(romfs, zone)
        except ValueError:      # a few entries are not LZ11 zone containers
            continue
        entities = files[1]
        c = entities[4:9]
        head = 12 + c[0] * 0x14 + c[1] * 0x30 + c[2] * 0x18 + c[3] * 0x18 + c[4] * 0x18
        yield f'zone {zone} entities', fb.entity_script(entities), entities[:head]
        yield f'zone {zone}', Script.parse(files[2]), b''


def arm_immediate(ins):
    """Immediate of an ARM data-processing instruction with an immediate operand, else None."""
    if (ins >> 26) & 3 != 0 or not (ins >> 25) & 1 or (ins >> 28) == 0xF:
        return None
    rot = ((ins >> 8) & 0xF) * 2
    imm = ins & 0xFF
    return ((imm >> rot) | (imm << (32 - rot))) & 0xFFFFFFFF if rot else imm


def code_literals(paths):
    hits = {}
    wanted = set(WORKS)
    for path in paths:
        data = path.read_bytes()
        for off in range(0, len(data) - 3, 4):
            ins = struct.unpack_from('<I', data, off)[0]
            for value in (ins, arm_immediate(ins)):
                if value in wanted:
                    hits.setdefault(value, set()).add(path.name)
    return hits


def scan(game=GAME):
    romfs = game / 'romfs'
    used = {}
    total = 0
    for name, script, head in scripts(romfs):
        total += 1
        for token in NUMBER.findall(listing(script)):
            value = int(token)
            if value in WORKS:
                used.setdefault(value, set()).add(name)
        for off in range(0, len(head) - 1, 2):
            value = struct.unpack_from('<H', head, off)[0]
            if value in WORKS:
                used.setdefault(value, set()).add(f'{name} data')
    code = [game / 'exefs/code.bin', romfs / 'static.crs', *sorted(romfs.glob('*.cro'))]
    for value, where in code_literals(code).items():
        used.setdefault(value, set()).update(f'code {w}' for w in where)
    return used, total, len(code)


def main():
    used, scripts_seen, code_files = scan()
    saves = {label: path.read_bytes() for label, path in SAVES.items() if path.exists()}
    free = [w for w in WORKS if w not in used and w not in KNOWN]
    print(f'{scripts_seen} scripts, {code_files} code files; {len(used)} of {len(WORKS)} saved works used, '
          f'{len(free)} free (+{len(KNOWN)} taken by our mods)')
    runs, start = [], None
    for w in WORKS:
        if w in free and start is None:
            start = w
        if (w not in free or w == WORKS[-1]) and start is not None:
            end = w if w in free else w - 1
            runs.append((start, end))
            start = None
    for a, b in runs:
        values = {label: [se.work(d, w) for w in range(a, b + 1)] for label, d in saves.items()}
        nonzero = {label: v for label, v in values.items() if any(v)}
        print(f'free {a}-{b} ({b - a + 1}){"" if not nonzero else "  NON-ZERO in " + str(nonzero)}')


if __name__ == '__main__':
    main()
