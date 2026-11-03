#!/usr/bin/env python3
"""Laboratory only (reports/frontier.md §25): a copy of a save whose first three party members are turned into strong
level-100 Pokémon (the Maison lowers them to 50 and recalculates; Normal-rank trainers are then beatable), with
saved works set, so a Tower or Factory round can be won quickly in Azahar. Never part of a release.

Usage: python frontier/lab_tower.py SOURCE OUTPUT [--work N=V ...]
"""
import argparse
import binascii
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'faraway')]
import save_event as se  # noqa: E402
import save_fixture as sf  # noqa: E402

# species, EXP at level 100 (growth), ability, moves with PP. PK6 offsets (PKHeX PK6): 0x08 species, 0x10 EXP,
# 0x14 ability, 0x15 ability number, 0x1C nature, 0x1E EVs, 0x5A moves, 0x62 PP, 0x74 IVs, party 0xEC level.
TEAM = [
    (376, 1250000, 29, [(309, 10), (89, 10), (428, 15), (418, 30)]),     # Metagross: Meteor Mash, EQ, ...
    (257, 1059860, 66, [(394, 15), (370, 5), (413, 15), (89, 10)]),      # Blaziken: Flare Blitz, Close Combat
    (445, 1250000, 24, [(89, 10), (337, 15), (444, 5), (242, 15)]),      # Garchomp: EQ, Dragon Claw, ...
]


def strong(data):
    layout = sf.blocks(data)
    out = bytearray(data)
    for slot, (species, exp, ability, moves) in enumerate(TEAM):
        at = sf.PARTY + slot * sf.PKSIZE
        pk = sf.decode_pk(out[at:at + sf.PKSIZE])
        struct.pack_into('<H', pk, 0x08, species)
        struct.pack_into('<I', pk, 0x10, exp)
        pk[0x14], pk[0x15], pk[0x1C] = ability, 1, 13            # Jolly
        pk[0x1E:0x24] = bytes([4, 252, 0, 252, 0, 0])            # HP Atk Def Spe SpA SpD
        for k, (move, pp) in enumerate(moves):
            struct.pack_into('<H', pk, 0x5A + 2 * k, move)
            pk[0x62 + k] = pp
        ivs = struct.unpack_from('<I', pk, 0x74)[0]
        struct.pack_into('<I', pk, 0x74, (ivs & 0xC0000000) | 0x3FFFFFFF)
        pk[0xEC] = 100
        struct.pack_into('<I', pk, 0xE8, 0)
        out[at:at + sf.PKSIZE] = sf.encode_pk(pk)
    offset, length, checksum = layout[18]
    struct.pack_into('<H', out, checksum, binascii.crc_hqx(out[offset:offset + length], 0xFFFF))
    sf.inspect(bytes(out))
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--work', action='append', type=se.pair, default=[])
    args = parser.parse_args()
    dest = args.output.resolve()
    if not dest.is_relative_to(ROOT / 'work') or dest.exists():
        parser.error('output must be a new file under work/')
    data = se.edit(strong(args.source.read_bytes()), works=args.work)
    dest.write_bytes(data)
    print(se.describe(data, works=[w for w, _ in args.work]))


if __name__ == '__main__':
    main()
