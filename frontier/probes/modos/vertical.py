#!/usr/bin/env python3
"""F9 Tower Open Level lab copy and combined passive level probe.

seed SOURCE SHA256 OUTPUT: new work/ save, paused Open Level S=6, legacy S/R=12/20,
selected party candidates 73/55/41 (Metagross/Blaziken/Garchomp, including their
experience). Source is never changed. No RAM writes: the Brains probe's CRO assistance hook is removed.
The code.bin hooks observe construction and results only.
probe DIRECTORY: print GDB script, including live selector and level measurements.
"""
import binascii
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'faraway', 'frontier')]
import save_fixture as sf  # noqa: E402
import save_event as se  # noqa: E402
import modes  # noqa: E402
import patch  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def seed(source, sha256, destination):
    raw = source.read_bytes()
    layout = sf.blocks(raw)
    if digest(raw) != sha256 or se.place(raw)['zone'] != 329:
        raise ValueError('source hash or Tower zone mismatch')
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT / 'work') or destination == source.resolve():
        raise ValueError('destination must be a separate new work/ save')
    metadata = destination.with_suffix('.json')
    if destination.exists() or metadata.exists():
        raise ValueError('destination or metadata already exists')
    result = bytearray(raw)
    for i, (species, level) in enumerate(zip((376, 257, 445), (73, 55, 41))):
        start = sf.PARTY + i * sf.PKSIZE
        pk = sf.decode_pk(raw[start:start + sf.PKSIZE])
        if sf.u16(pk, 8) != species:
            raise ValueError('unexpected fixture species/growth curve')
        pk[0xEC] = level
        exp = (6 * level**3 // 5 - 15 * level**2 + 100 * level - 140
               if species == 257 else 5 * level**3 // 4)
        struct.pack_into('<I', pk, 0x10, exp)
        result[start:start + sf.PKSIZE] = sf.encode_pk(pk)
    # Retail reconstructs stats on the private battle copies; fixture party stats
    # retain the source's values. Hash comparison checks no further party edits.
    for start, length, checksum in layout:
        struct.pack_into('<H', result, checksum,
                         binascii.crc_hqx(result[start:start + length], 0xFFFF))
    streak, record = modes.bank(2, modes.SINGLE_OPEN)
    legacy, legacy_record = modes.bank(2, modes.SINGLE_50)
    works = {w: 0 for w in patch.ACTIVE_WORK.values()}
    works.update({patch.WORK_ROUTE: 0, patch.ACTIVE_WORK['tower']: 1,
                  # This fixture emulates a registered challenge, not a new-mode menu.
                  # The live probe verifies which slots are actually selected.
                  modes.CONFIG[2]: modes.selection_config(2, 1, (73, 55, 41)), streak: 6, record: 6,
                  legacy: 12, legacy_record: 20})
    result = se.edit(bytes(result), works=works.items())
    info = dict(source=str(source), source_sha256=sha256, sha256=digest(result), works=works,
                party_sha256=digest(result[sf.PARTY:sf.PARTY + 0x61C]),
                box_sha256=digest(result[0x33000:0x67AD0]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as f:
        f.write(result)
    with metadata.open('x') as f:
        json.dump(info, f, indent=2)
    return info


def probe(directory):
    here = Path(__file__).parent
    brain = runpy.run_path(str(here.parent / 'brains/lab_probe.py'))['script']
    live = runpy.run_path(str(here / 'live.py'))['script']
    # CROs are unloaded/reloaded at the same address. Software breakpoints
    # planted before a CRO loads can restore stale zero bytes over its code.
    b = brain(directory).replace(f"Hook({patch.battle_cro_runtime('arena_enter')},enter)\n", '').replace(
        "super().__init__('*%#x'%addr);",
        "super().__init__('*%#x'%addr, type=gdb.BP_HARDWARE_BREAKPOINT "
        "if addr >= 0x600000 else gdb.BP_BREAKPOINT);")
    l = live({}).replace(
        "super().__init__('*'+hex(a),internal=True)",
        "super().__init__('*'+hex(a),internal=True, type=gdb.BP_HARDWARE_BREAKPOINT "
        "if a >= 0x600000 else gdb.BP_BREAKPOINT)")
    return b + l + '''python
def level_config():
    return rd(mode_save+0x13144+2*(16573-0x4000),2)
def cap_in():
    print('OPEN CAP input=%u force=%u config=%x' %(reg('r0'),reg('r7'),level_config()))
def cap_out():
    print('OPEN CAP flags=%x force=%u config=%x' %(reg('cpsr'),reg('r7'),level_config()))
def make_level():
    print('OPEN MAKE level=%u lr=%x config=%x' %(reg('r1'),reg('lr'),level_config()))
Hook(0x1e3e00,cap_in)
Hook(0x1e3e04,cap_out)
Hook(0x1ef904,make_level)
end
'''


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == 'seed':
        print(json.dumps(seed(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])), indent=2))
    elif len(sys.argv) == 3 and sys.argv[1] == 'probe':
        print(probe(sys.argv[2]), end='')
    else:
        raise SystemExit(__doc__)
