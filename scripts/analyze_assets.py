#!/usr/bin/env python3
"""Generate local analysis metadata and a synthetic ELF (never a game patch).

CRO layout reference: https://www.3dbrew.org/wiki/CRO0
GARC/item layout: tools/pk3DS/pk3DS.Core/{CTR/GARC.cs,Structures/Gen6/Item6.cs}
"""
import json
from pathlib import Path
import struct

from formats import check_file, garc_entries

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'baseline/oras'
OUT = ROOT / 'analysis'
CRO_BASE = 0x01000000  # Arbitrary analysis address, NOT a measured runtime address.


class CRO:
    def __init__(self, path):
        self.data = path.read_bytes()
        if self.data[0x80:0x84] != b'CRO0':
            raise ValueError(f'Not a CRO: {path}')
        offset, count = self.unpack('<II', 0xC8)
        self.segments = [self.unpack('<III', offset + i * 12) for i in range(count)]

    def unpack(self, fmt, offset):
        return struct.unpack_from(fmt, self.data, offset)

    def string(self, offset):
        return self.data[offset:self.data.index(0, offset)].decode('ascii')

    def resolve(self, tag):
        start, size, kind = self.segments[tag & 15]
        offset = tag >> 4
        if offset > size:
            raise ValueError('CRO segment reference out of bounds')
        return start + offset

    def static_imports(self, static):
        table, count = self.unpack('<II', 0xF0)
        reloc_start, reloc_count = self.unpack('<II', 0xF8)
        result = []
        for i in range(count):
            name, _, _, anonymous, num = self.unpack('<5I', table + 20 * i)
            if self.string(name) != '|static|':
                continue
            for j in range(num):
                symbol, relocation = self.unpack('<II', anonymous + j * 8)
                target = static.resolve(symbol)
                while True:
                    if not reloc_start <= relocation < reloc_start + reloc_count * 12:
                        raise ValueError('CRO import relocation outside table')
                    tag, kind, last, _, _, addend = self.unpack('<IBBBBI', relocation)
                    result.append(dict(offset=self.resolve(tag), type=kind, target=target, addend=addend))
                    relocation += 12
                    if last:
                        break
        return result


def relocate(data, offset, kind, target, addend, place):
    if kind == 0:
        return
    if kind in (2, 38):
        value = target + addend
    elif kind == 3:
        value = target + addend - place
    elif kind in (28, 29):
        delta = target + addend - place
        if target & 1 or delta % 4 or not -(1 << 25) <= delta < 1 << 25:
            raise ValueError('Unsupported CRO branch relocation')
        old = struct.unpack_from('<I', data, offset)[0]
        value = (old & 0xFF000000) | ((delta >> 2) & 0xFFFFFF)
    elif kind == 42:
        value = (target + addend - place) & 0x7FFFFFFF
    else:
        raise ValueError(f'Unsupported CRO relocation type {kind}')
    struct.pack_into('<I', data, offset, value & 0xFFFFFFFF)


def elf32(loads, entry):
    """ELF32/ARM program headers, preserving each segment's actual VA and BSS."""
    header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01' + bytes(9),
                         2, 40, 1, entry, 52, 0, 0x05000000, 52, 32, len(loads), 0, 0, 0)
    result = bytearray(header + bytes(32 * len(loads)))
    for i, (va, data, memsize, flags) in enumerate(loads):
        offset = (len(result) + 0xFFF) & ~0xFFF
        offset += va & 0xFFF
        result.extend(bytes(offset - len(result)))
        result.extend(data)
        struct.pack_into('<8I', result, 52 + i * 32, 1, offset, va, va,
                         len(data), memsize, flags, 0x1000)
    return result


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    root = BASE / 'repolished'
    for relative in ['exefs/code.bin', 'exheader.bin', 'romfs/static.crs',
                     'romfs/DllBattle.cro', 'romfs/DllBag.cro', 'romfs/a/1/9/7']:
        check_file(root / relative, manifest['repolished'][relative])
    OUT.mkdir(exist_ok=True)
    (OUT / 'code-map.json').write_text(json.dumps(manifest['segments'], indent=2) + '\n')
    static = CRO(root / 'romfs/static.crs')
    battle = CRO(root / 'romfs/DllBattle.cro')
    for name in ['DllBattle.cro', 'DllBag.cro']:
        cro = CRO(root / 'romfs' / name)
        (OUT / f'{name}.imports.json').write_text(json.dumps(cro.static_imports(static), indent=2) + '\n')
    items = []
    raw = (root / 'romfs/a/1/9/7').read_bytes()
    for item, sub, offset, length in garc_entries(raw):
        record = raw[offset:offset + length]
        if sub != 0 or length != 36:
            raise ValueError('Unexpected item record layout')
        packed = struct.unpack_from('<H', record, 8)[0]
        items.append(dict(id=item, offset=offset, raw=record.hex(), held_effect=record[2],
                          held_argument=record[3], pocket=(packed >> 7) & 15,
                          flag5=bool(packed & 32), flag6=bool(packed & 64), field_effect=record[10]))
    (OUT / 'items.json').write_text(json.dumps(items, indent=2) + '\n')
    code = (root / 'exefs/code.bin').read_bytes()
    loads = []
    for segment in manifest['segments'][:3]:
        offset, size = segment['file_offset'], segment['size']
        memsize = size + (manifest['segments'][3]['size'] if segment['name'] == 'data' else 0)
        loads.append((segment['address'], code[offset:offset + size], memsize,
                      {'text': 5, 'rodata': 4, 'data': 6}[segment['name']]))
    relocated = bytearray(battle.data)
    bss_offset = (len(relocated) + 0xFFF) & ~0xFFF
    segment_vas = [CRO_BASE + (bss_offset if kind == 3 else offset)
                   for offset, size, kind in battle.segments]
    for row in battle.static_imports(static):
        relocate(relocated, row['offset'], row['type'], row['target'], row['addend'], CRO_BASE + row['offset'])
    table, count = battle.unpack('<II', 0x128)
    for i in range(count):
        tag, kind, target_segment, _, _, addend = battle.unpack('<IBBBBI', table + i * 12)
        offset = battle.resolve(tag)
        relocate(relocated, offset, kind, segment_vas[target_segment], addend, CRO_BASE + offset)
    for i, (offset, size, kind) in enumerate(battle.segments):
        if not size:
            continue
        loads.append((segment_vas[i], b'' if kind == 3 else relocated[offset:offset + size], size,
                      {0: 5, 1: 4, 2: 6, 3: 6}[kind]))
    (OUT / 'repolished-battle.elf').write_bytes(elf32(loads, 0x100000))
    (OUT / 'elf-notes.json').write_text(json.dumps(dict(
        purpose='Analysis only; do not install this ELF', battle_synthetic_base=CRO_BASE,
        battle_bss_synthetic_offset=bss_offset,
        unresolved_modules=['DllContest', 'DllBackGround'],
        static_segments=static.segments, battle_segments=battle.segments), indent=2) + '\n')
    print(f'Analysis ELF and metadata: {OUT}')


if __name__ == '__main__':
    main()
