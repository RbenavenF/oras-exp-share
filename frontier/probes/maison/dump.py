#!/usr/bin/env python3
"""Read-only ARM11 Luma dump check against the two published local packages.

Usage: python frontier/probes/maison/dump.py /path/crash_dump_00000000.dmp
Does not copy the dump, modify a package or assume that its stack contains heap data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
CRO_BASE = 0x6f3000  # measured for this incident, not a universal CRO address


def analyze(path):
    raw = path.read_bytes()
    header = struct.unpack_from('<10I', raw)
    magic1, magic2, version, processor, exception, size, nr, nc, ns, na = header
    if (magic1, magic2, processor, exception) != (0xdeadc0de, 0xdeadcafe, 11, 3):
        raise ValueError('Expected a Luma ARM11 data-abort dump')
    if size != len(raw) or size != 40 + nr + nc + ns + na or nr != 92 or nc < 4:
        raise ValueError('Unexpected dump section sizes')
    regs = struct.unpack_from('<23I', raw, 40)
    pc = regs[15]
    offset = pc - CRO_BASE
    code = raw[40+nr:40+nr+nc]
    # Luma stores the faulting ARM instruction as the last word of its code section.
    comparisons = {}
    for name, folder in (
        ('alpha-v0.1', 'dist/oras-frontier-alpha-v0.1/luma/titles/000400000011C400'),
        ('held-v0.5', 'dist/held-exp-share-v0.5/mods/000400000011C400'),
    ):
        cro = (ROOT / folder / 'romfs/DllBattle.cro').read_bytes()
        comparisons[name] = {
            'cro_sha256': hashlib.sha256(cro).hexdigest(),
            'fault_word': cro[offset:offset+4].hex(),
            'whole_code_window_matches': cro[offset-nc+4:offset+4] == code,
        }
    return {
        'dump_sha256': hashlib.sha256(raw).hexdigest(), 'size': size,
        'version': version, 'cro_base': hex(CRO_BASE), 'cro_offset': hex(offset),
        'registers': {name: hex(value) for name, value in
                      zip([f'r{k}' for k in range(13)] + ['sp', 'lr', 'pc', 'cpsr',
                           'dfsr', 'ifsr', 'far', 'fpexc', 'fpinst', 'fpinst2'], regs)},
        'code_window_bytes': nc, 'packages': comparisons,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path)
    print(json.dumps(analyze(parser.parse_args().dump), indent=2))
