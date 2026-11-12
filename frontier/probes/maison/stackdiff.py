#!/usr/bin/env python3
"""F7-CONSOLA-MANSION: compare a Luma ARM11 dump's stack with a STACKWORDS line of stack.gdb (Azahar).

Usage: stackdiff.py DUMP.dmp GDB_LOG. Prints every word and marks the differences. Read-only.
Heap model (measured 2026-11-12, reports/frontier.md §48): client 0 of a Singles battle is allocated after
0x488 bytes per Pokémon of both sides (two 0x244 objects each): 6 -> 0x820d9ac, 4 -> 0x820d09c.
"""
import struct
import sys

HEADER, CLIENT_6 = 0x28, 0x820D9AC


def dump_stack(path):
    b = open(path, 'rb').read()
    magic = struct.unpack_from('<2I', b)
    if magic != (0xDEADC0DE, 0xDEADCAFE):
        sys.exit('not a Luma dump')
    regsz, codesz, stsz = struct.unpack_from('<3I', b, 0x18)
    return struct.unpack_from(f'<{stsz // 4}I', b, HEADER + regsz + codesz)


def main():
    con = dump_stack(sys.argv[1])
    line = [l for l in open(sys.argv[2], errors='replace') if 'STACKWORDS' in l][-1].split('STACKWORDS', 1)[1]
    lab = [int(x, 16) for x in line.split()]
    diff = 0
    for i, (c, a) in enumerate(zip(con, lab)):
        mark = '' if c == a else '  <<'
        diff += c != a
        print(f'{4 * i:#5x} {c:08x} {a:08x}{mark}')
    client = con[0x24 // 4]
    print(f'differences: {diff}; dump client {client:#x}: {6 - (CLIENT_6 - client) / 0x488:.1f} Pokémon in the battle (both sides)')


if __name__ == '__main__':
    main()
