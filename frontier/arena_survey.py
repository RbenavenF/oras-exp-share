#!/usr/bin/env python3
"""Read-only stage B measurements, with relocations (reports/frontier.md §31).

Run with scripts/env.sh loaded. No extracted bytes are written to the repository;
redirect the listing to work/frontier/arena/b-static.txt.
"""
import hashlib
from pathlib import Path
import struct

from cro import Cro
from disasm import disasm
from disasm_code import disasm as disasm_code

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'baseline/oras/repolished'


def zero_runs(cro, minimum=16):
    """Aligned zero runs excluding every internal relocation target word.

    This is a candidate filter, not proof that a run is unused or executable.
    In particular, a jump table is zero on disk but populated by the loader.
    """
    relocated = {target for target, _, _ in cro.relocs}
    start, size, _ = cro.segments[0]
    first = None
    for offset in range(start, start + size + 4, 4):
        zero = (offset < start + size and cro.data[offset:offset + 4] == bytes(4)
                and offset not in relocated)
        if zero and first is None:
            first = offset
        elif not zero and first is not None:
            if offset - first >= minimum:
                yield first, offset - first
            first = None


def handlers(cro, factory):
    """Known simple ARM event-table factories: count, relocated table pointer."""
    assert struct.unpack_from('<I', cro.data, factory)[0] & 0xFFFFFF00 == 0xE3A01000
    count = cro.data[factory]
    table = cro.pointer_at()[factory + 16]
    for index in range(count):
        row = table + index * 8
        yield row, struct.unpack_from('<I', cro.data, row)[0], cro.pointer_at()[row + 4]


def main():
    code = (GAME / 'exefs/code.bin').read_bytes()
    battle = Cro((GAME / 'romfs/DllBattle.cro').read_bytes())
    field = Cro((GAME / 'romfs/DllField.cro').read_bytes())
    for name, data in [('code.bin', code), ('DllBattle.cro', battle.data), ('DllField.cro', field.data)]:
        print(name, 'SHA256', hashlib.sha256(data).hexdigest())
    print('DllBattle segments', battle.segments)
    print('DllBattle zero candidates >=16, after excluding internal relocations:',
          [(hex(start), size) for start, size in zero_runs(battle)])
    for va, count in [(0x1E30B8, 32), (0x1E329C, 89), (0x3DA5CC, 51), (0x1DBD18, 83),
                      (0x3673BC, 118), (0x1E04F8, 8)]:
        print(f'\ncode.bin VA {va:#x}')
        print('\n'.join(disasm_code(code, va, count, stop=False)))
    print('\nDllField CallSakasaBattle (native table 0xf79a4 -> 0x559ac)')
    print('\n'.join(disasm(field, 0x559AC, 21, stop=False)))
    # The two ID-195 rows are in DIFFERENT registries. Only 0xde420 is in the
    # movement-ID registry (next to Mean Look 212 and Fake Out 252). Do not
    # confuse the other registry's ID 195 with the move Perish Song.
    for label, factory in [('move 252 Fake Out', 0xB707C), ('move 195 Perish Song', 0xB7F30),
                           ('move 212 Mean Look', 0xB60C8), ('ability 3 Speed Boost', 0xC94D0),
                           ('ability 23 Shadow Tag', 0xCA558), ('ability 71 Arena Trap', 0xCAC20)]:
        print(f'\n{label}: factory {factory:#x}')
        for row, event, handler in handlers(battle, factory):
            print(f'row {row:#x}, event {event:#x}, handler {handler:#x}')
            print('\n'.join(disasm(battle, handler, 130)))
    for offset, count in [(0x51394, 11), (0x6C51C, 16), (0x6D3A8, 33), (0x6749C, 17),
                          (0x78344, 77), (0x79458, 152), (0x1DACC, 113),
                          (0x72498, 21), (0x1CF44, 155), (0x1D19C, 46),
                          (0xA8554, 12)]:
        print(f'\nDllBattle file offset {offset:#x}')
        print('\n'.join(disasm(battle, offset, count, stop=False)))


if __name__ == '__main__':
    main()
