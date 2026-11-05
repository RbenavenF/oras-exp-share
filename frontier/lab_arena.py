#!/usr/bin/env python3
"""Arena B lab fixture: Gengar/Blaziken/Garchomp with harmless moves, on a save COPY.

Use a paused Arena save under work/. The real save and inputs are never written.
The engine still builds/levels the selected party normally. Enemy moves are not
changed here (the live probe can replace its copied moves with Splash).
"""
import argparse
import binascii
from pathlib import Path
import struct

import lab_tower as lt

ROOT = Path(__file__).resolve().parents[1]


def fixture(data):
    original_team = lt.TEAM
    moves = [(150, 40), (182, 10), (105, 10), (45, 40)]
    try:
        lt.TEAM = [(94, 1059860, 26, moves), (257, 1059860, 66, moves), (445, 1250000, 24, moves)]
        out = bytearray(lt.strong(data))
    finally:
        lt.TEAM = original_team
    sf = lt.sf
    layout = sf.blocks(out)
    for slot, name in enumerate(('Gengar', 'Blaziken', 'Garchomp')):
        at = sf.PARTY + slot * sf.PKSIZE
        pk = sf.decode_pk(out[at:at + sf.PKSIZE])
        pk[0x40:0x5A] = name.encode('utf-16le').ljust(26, b'\0')
        ivs = struct.unpack_from('<I', pk, 0x74)[0]
        struct.pack_into('<I', pk, 0x74, ivs | 0x80000000)
        out[at:at + sf.PKSIZE] = sf.encode_pk(pk)
    offset, length, checksum = layout[18]
    struct.pack_into('<H', out, checksum, binascii.crc_hqx(out[offset:offset + length], 0xFFFF))
    sf.inspect(bytes(out))
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / 'work') or args.output.exists():
        parser.error('output must be a new file under work/')
    args.output.write_bytes(fixture(args.source.read_bytes()))
    print(lt.se.describe(args.output.read_bytes(), works=[16465, 16466, 16467, 16438]))


if __name__ == '__main__':
    main()
