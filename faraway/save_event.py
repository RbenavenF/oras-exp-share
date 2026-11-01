#!/usr/bin/env python3
"""Make laboratory save copies for the Faraway Island tests: event flags/works, position and bag items.

Layout (PKHeX SaveBlockAccessor6AO, EventWork6, Situation6): block 4 Situation at 0x1400 (zone at +0x02 and
+0xF4; X/Z/Y floats at +0x10 and mirrored at +0x104), block 19 EventWork at 0x14A00 (0x178 u16 works, then
0xD00 flags), block 1 bag at 0x400. Every touched block's checksum is recomputed and the result is
re-validated. Inputs are never modified; the output must be a new file under work/.
"""
import argparse
import binascii
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import save_fixture as sf  # noqa: E402

SITUATION, EVENTS = 0x1400, 0x14A00
WORK_BASE, WORK_COUNT, FLAG_OFFSET, FLAG_COUNT = 0x4000, 0x178, 0x2F0, 0xD00
POCKETS = {'items': sf.ITEMS, 'key': sf.KEY}


def block_of(layout, offset):
    for index, (start, length, checksum) in enumerate(layout):
        if start <= offset < start + length:
            return index
    raise ValueError(f'Offset {offset:#x} is in no block')


def flag(data, number):
    if not 0 <= number < FLAG_COUNT:
        raise ValueError(f'Flag {number} out of range')
    return data[EVENTS + FLAG_OFFSET + number // 8] >> (number % 8) & 1


def work(data, number):
    index = number - WORK_BASE
    if not 0 <= index < WORK_COUNT:
        raise ValueError(f'Work {number} out of range')
    return struct.unpack_from('<H', data, EVENTS + 2 * index)[0]


def place(data):
    zone = struct.unpack_from('<H', data, SITUATION + 2)[0]
    x, z, y = struct.unpack_from('<3f', data, SITUATION + 0x10)
    return dict(zone=zone, tile_x=x / 18, height=z, tile_y=y / 18)


def edit(data, flags=(), works=(), position=None, items=()):
    layout = sf.blocks(data)
    out = bytearray(data)
    touched = set()
    for number, value in flags:
        flag(out, number)
        offset = EVENTS + FLAG_OFFSET + number // 8
        out[offset] = (out[offset] & ~(1 << number % 8)) | (value << number % 8)
        touched.add(block_of(layout, offset))
    for number, value in works:
        work(out, number)
        struct.pack_into('<H', out, EVENTS + 2 * (number - WORK_BASE), value)
        touched.add(block_of(layout, EVENTS))
    if position:
        zone, x, height, y = position
        for base in (SITUATION + 0x02, SITUATION + 0xF4):
            struct.pack_into('<H', out, base, zone)
        for base in (SITUATION + 0x10, SITUATION + 0x104):
            struct.pack_into('<3f', out, base, x * 18 + 9, height, y * 18 + 9)
        touched.add(block_of(layout, SITUATION))
    for pocket, item, count in items:
        entries = [e for e in sf.pouch(out, POCKETS[pocket]) if e[0] and e[0] != item]
        sf.write_pouch(out, POCKETS[pocket], entries + [(item, count)])
        touched.add(block_of(layout, POCKETS[pocket][0]))
    for index in touched:
        start, length, checksum = layout[index]
        struct.pack_into('<H', out, checksum, binascii.crc_hqx(out[start:start + length], 0xFFFF))
    sf.blocks(bytes(out))
    return bytes(out)


def describe(data, numbers=(), works=()):
    info = sf.inspect(data)
    info['place'] = place(data)
    info['flags'] = {n: flag(data, n) for n in numbers}
    info['works'] = {n: work(data, n) for n in works}
    return info


def pair(text):
    key, value = text.split('=')
    return int(key), int(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--flag', action='append', type=pair, default=[], help='FLAG=0|1')
    parser.add_argument('--work', action='append', type=pair, default=[], help='WORK=VALUE')
    parser.add_argument('--place', help='ZONE,TILE_X,HEIGHT,TILE_Y')
    parser.add_argument('--item', action='append', default=[], help='POCKET:ITEM:COUNT')
    parser.add_argument('--show-flag', action='append', type=int, default=[])
    parser.add_argument('--show-work', action='append', type=int, default=[])
    args = parser.parse_args()
    data = args.source.read_bytes()
    shown_flags = args.show_flag + [n for n, _ in args.flag]
    shown_works = args.show_work + [n for n, _ in args.work]
    before = describe(data, shown_flags, shown_works)
    if not args.output:
        print(json.dumps(before, indent=1))
        return
    dest = args.output.resolve()
    if not dest.is_relative_to(ROOT / 'work') or dest == args.source.resolve():
        parser.error('Output must be a separate new file under work/')
    if args.sha256 != before['sha256']:
        parser.error('--sha256 must match the source save')
    position = None
    if args.place:
        zone, x, height, y = args.place.split(',')
        position = (int(zone), int(x), float(height), int(y))
    items = [(p, int(i), int(c)) for p, i, c in (spec.split(':') for spec in args.item)]
    result = edit(data, args.flag, args.work, position, items)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(result)
    print(json.dumps(dict(before=before, after=describe(result, shown_flags, shown_works)), indent=1))


if __name__ == '__main__':
    main()
