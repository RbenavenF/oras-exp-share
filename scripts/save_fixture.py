#!/usr/bin/env python3
"""Inspect ORAS main saves and create a separate three-Pokemon test fixture.

Format references: PKHeX BlockInfo3DS, SaveBlockAccessor6AO, PokeCrypto, PK6.
Only local laboratory copies; output must be new and under work/.
"""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SIZE, META, PARTY, PKSIZE = 0x76000, 0x75E00, 0x14200, 0x104
# MyItem6AO pouches in block 1: (offset, slots); entries are u16 item, u16 count.
BAG, ITEMS, KEY = 0x400, (0x400, 400), (0xA40, 96)
EXP_SHARE = 216
PERMS = [tuple(map(int, row)) for row in (
    '0123 0132 0213 0312 0231 0321 1023 1032 '
    '2013 3012 2031 3021 1203 1302 2103 3102 '
    '2301 3201 1230 1320 2130 3120 2310 3210').split()]
PERMS += PERMS[:8]


def u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def crypt(data):
    result = bytearray(data)
    for start, end in [(8, 0xE8), (0xE8, PKSIZE)]:
        seed = u32(data, 0)
        for pos in range(start, end, 2):
            seed = (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
            struct.pack_into('<H', result, pos, u16(result, pos) ^ (seed >> 16))
    return result


def pk_checksum(data):
    return sum(struct.unpack_from('<112H', data, 8)) & 0xFFFF


def decode_pk(data):
    if len(data) != PKSIZE:
        raise ValueError('Expected a 260-byte party Pokemon')
    raw = crypt(data)
    result = bytearray(raw)
    for dest, source in enumerate(PERMS[(u32(data, 0) >> 13) & 31]):
        result[8 + dest * 56:8 + (dest + 1) * 56] = raw[8 + source * 56:8 + (source + 1) * 56]
    if u16(result, 4) != 0 or u16(result, 6) != pk_checksum(result):
        raise ValueError('Invalid Pokemon sanity/checksum')
    return result


def encode_pk(data):
    if len(data) != PKSIZE:
        raise ValueError('Expected a 260-byte party Pokemon')
    raw = bytearray(data)
    struct.pack_into('<H', raw, 6, pk_checksum(raw))
    result = bytearray(raw)
    for source, dest in enumerate(PERMS[(u32(data, 0) >> 13) & 31]):
        result[8 + dest * 56:8 + (dest + 1) * 56] = raw[8 + source * 56:8 + (source + 1) * 56]
    return crypt(result)


def blocks(data):
    if len(data) != SIZE or u32(data, META + 0x10) != 0x42454546:
        raise ValueError('Expected a decrypted ORAS main save (0x76000 bytes, BEEF footer)')
    offset = 0
    result = []
    for index in range(58):
        entry = META + 0x14 + index * 8
        length, block_id, checksum = struct.unpack_from('<IHH', data, entry)
        if block_id != index or length == 0 or offset + length > META:
            raise ValueError(f'Invalid block metadata: {index}')
        if binascii.crc_hqx(data[offset:offset + length], 0xFFFF) != checksum:
            raise ValueError(f'Invalid save checksum: block {index}')
        result.append((offset, length, entry + 6))
        offset = (offset + length + 0x1FF) & ~0x1FF
    if result[18][:2] != (PARTY, 0x61C):
        raise ValueError('Unexpected party block layout')
    return result


def pouch(data, pocket):
    offset, slots = pocket
    return [struct.unpack_from('<HH', data, offset + 4 * i) for i in range(slots)]


def write_pouch(output, pocket, entries):
    offset, slots = pocket
    entries = [entry for entry in entries if entry[0]]
    if len(entries) > slots:
        raise ValueError('Pouch is full')
    for i, (item, count) in enumerate(entries + [(0, 0)] * (slots - len(entries))):
        struct.pack_into('<HH', output, offset + 4 * i, item, count)


def move_exp_share(data):
    """Move item 216 from Key Items to Items, as the patched item data expects."""
    layout = blocks(data)
    key, items = pouch(data, KEY), pouch(data, ITEMS)
    held = [entry for entry in key if entry[0] == EXP_SHARE]
    if len(held) != 1:
        raise ValueError('Expected exactly one Exp. Share entry in Key Items')
    output = bytearray(data)
    write_pouch(output, KEY, [entry for entry in key if entry[0] != EXP_SHARE])
    existing = [entry for entry in items if entry[0]]
    if any(item == EXP_SHARE for item, _ in existing):
        existing = [(item, count + held[0][1] if item == EXP_SHARE else count) for item, count in existing]
    else:
        existing.append(held[0])
    write_pouch(output, ITEMS, existing)
    offset, length, checksum_offset = layout[1]
    if offset != BAG or not offset <= KEY[0] < ITEMS[0] + length:
        raise ValueError('Unexpected bag block layout')
    struct.pack_into('<H', output, checksum_offset, binascii.crc_hqx(output[offset:offset + length], 0xFFFF))
    changed = [i for i in range(len(data)) if data[i] != output[i]]
    if any(not (offset <= i < offset + length or i == checksum_offset or i == checksum_offset + 1) for i in changed):
        raise ValueError('Change outside the bag block')
    inspect(output)
    return bytes(output)


def inspect(data):
    blocks(data)
    count = data[PARTY + PKSIZE * 6]
    if count > 6:
        raise ValueError('Invalid party count')
    members = []
    for slot in range(count):
        pk = decode_pk(data[PARTY + slot * PKSIZE:PARTY + (slot + 1) * PKSIZE])
        members.append(dict(slot=slot + 1, species=u16(pk, 8), item=u16(pk, 10),
                            exp=u32(pk, 0x10), ev=list(pk[0x1E:0x24]), level=pk[0xEC],
                            hp=u16(pk, 0xF0), max_hp=u16(pk, 0xF2),
                            egg=bool(u32(pk, 0x74) & 0x40000000)))
    bag = {name: [entry for entry in pouch(data, pocket) if entry[0]]
           for name, pocket in [('items', ITEMS), ('key', KEY)]}
    return dict(sha256=hashlib.sha256(data).hexdigest(), valid_blocks=58, party=members, bag=bag)


def make_fixture(data, scenario):
    layout = blocks(data)
    if not data[PARTY + PKSIZE * 6]:
        raise ValueError('Save first needs a starter Pokemon')
    starter = decode_pk(data[PARTY:PARTY + PKSIZE])
    if not 1 <= u16(starter, 8) <= 721 or u32(starter, 0x74) & 0x40000000:
        raise ValueError('First party member must be a non-egg Pokemon')
    output = bytearray(data)
    for slot in range(3):
        pk = bytearray(starter)
        item = 216 if ((scenario in ('reserve', 'fainted') and slot == 1)
                       or (scenario == 'participant' and slot == 0)) else 0
        struct.pack_into('<H', pk, 10, item)
        struct.pack_into('<H', pk, 0xF0, 0 if scenario == 'fainted' and slot == 1 else u16(pk, 0xF2))
        struct.pack_into('<I', pk, 0xE8, 0)  # clear battle status
        pk[0x1E:0x24] = bytes(6)
        output[PARTY + slot * PKSIZE:PARTY + (slot + 1) * PKSIZE] = encode_pk(pk)
    # Empty party entries are encrypted PK6 records too. Raw zeros become
    # bad eggs when the game decrypts and rebuilds the party on load.
    output[PARTY + 3 * PKSIZE:PARTY + 6 * PKSIZE] = encode_pk(bytes(PKSIZE)) * 3
    output[PARTY + 6 * PKSIZE] = 3
    offset, length, checksum_offset = layout[18]
    struct.pack_into('<H', output, checksum_offset, binascii.crc_hqx(output[offset:offset + length], 0xFFFF))
    inspect(output)
    for slot in range(3, 6):
        empty = decode_pk(output[PARTY + slot * PKSIZE:PARTY + (slot + 1) * PKSIZE])
        if u16(empty, 8) != 0:
            raise ValueError('Generated unused party slot is not empty')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sha256', help='Required source hash for fixture generation')
    parser.add_argument('--scenario', choices=['reserve', 'participant', 'fainted', 'none'], default='reserve')
    parser.add_argument('--move-exp-share', action='store_true',
                        help='Keep the save as is; only move item 216 from Key Items to Items')
    args = parser.parse_args()
    data = args.source.read_bytes()
    before = inspect(data)
    if args.output:
        dest = args.output.resolve()
        if not dest.is_relative_to(ROOT / 'work') or dest == args.source.resolve():
            parser.error('Output must be a separate new file under work/')
        if args.sha256 != before['sha256']:
            parser.error('--sha256 must match the source save')
        result = move_exp_share(data) if args.move_exp_share else make_fixture(data, args.scenario)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(result)
        action = 'move-exp-share' if args.move_exp_share else args.scenario
        print(json.dumps(dict(source=before, action=action, output=inspect(result)), indent=2))
    else:
        print(json.dumps(before, indent=2))


if __name__ == '__main__':
    main()
