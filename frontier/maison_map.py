#!/usr/bin/env python3
"""F1: map the Battle Maison natives to their code. Read-only; reproduces reports/frontier.md §Nativas.

- Finds the field-script native table in DllField.cro (pairs of relocated pointers: name, function).
- Resolves each Maison native's first calls through the CRO import thunks into code.bin (|static|).
- Checks the instruction words the F1 analysis relies on (party copy in StartBattle, set->Pokémon
  builder, work size) so a different dump fails loudly instead of giving wrong addresses.
- Measures the zero padding between the end of .text and the next page (candidate space for hooks).
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'frontier'))
from analyze_assets import CRO as StaticCRO  # noqa: E402
from cro import Cro  # noqa: E402
from formats import sha256  # noqa: E402

GAME = ROOT / 'baseline/oras/repolished'
CODE_BASE = 0x100000
# Repolished 1.7.6 baseline built by scripts/prepare_baseline.py (code.bin includes the mod's code.ips)
HASHES = {
    'romfs/DllField.cro': '23248ab0d170c2cc2b20d2bd4e7a70aeb4f57485b69b7b3d1b542958546c1455',
    'exefs/code.bin': '3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293',
}
MAISON = ('BattleInstWorkCreate', 'BattleInstWorkDelete', 'SetTrainer', 'StartBattle', 'GetRank', 'SetRank',
          'IsWin', 'IsBoss', 'AddWinCount', 'GetMyWinCount', 'BattleHouse_CallPartySelectApp',
          'BattleHouse_IsBattleBoxUsed', 'BattleHouse_End', '_CallTrialDownloadApp')
# (VA, expected word, meaning) — code.bin facts quoted in reports/frontier.md
CODE_FACTS = [
    (0x1E5CF0, 0xE3A00EB9, 'BattleInstWorkCreate: mov r0, #0xb90 (work size)'),
    (0x1E3D3C, 0xE5D20000, 'party build: ldrb r0, [r2] (selection.useBattleBox)'),
    (0x1E3D60, 0xE5901004, 'party build: ldr r1, [r0, #4] (selection index i)'),
    (0x1E3D94, 0xE5908014, 'party build: ldr r8, [r0, #0x14] (player party from game data)'),
    (0x1E3DB0, 0xE0840105, 'party build: add r0, r4, r5, lsl #2 (player-party loop)'),
    (0x1E3574, 0x03A010B6, 'trainer party: moveq r1, #0xb6 (maisonpkN = a/1/8/2)'),
    (0x1E3570, 0x13A010B8, 'trainer party: movne r1, #0xb8 (maisonpkS = a/1/8/4)'),
    (0x1E351C, 0xEB0030F8, 'multi partner: bl 0x1ef904 (set -> PokemonParam)'),
]


def word(data, va):
    return struct.unpack_from('<I', data, va - CODE_BASE)[0]


def native_table(cro):
    pointers = cro.pointer_at()
    kind = lambda off: (cro.segment_of(off) or (None, None))[1]
    string = lambda off: cro.data[off:cro.data.index(0, off)].decode('latin-1')
    table = {}
    for slot, target in sorted(pointers.items()):
        if kind(target) == 1 and slot + 4 in pointers and kind(pointers[slot + 4]) == 0:
            name = string(target)
            if name.isidentifier():
                table.setdefault(name, (slot, pointers[slot + 4]))
    return table


def first_calls(cro, imports, offset, limit=80):
    """Targets of the bl instructions of one CRO function, until its first return."""
    out = []
    for i in range(limit):
        ins = struct.unpack_from('<I', cro.data, offset + 4 * i)[0]
        if ins & 0x0F000000 == 0x0B000000 or ins >> 24 == 0xEA:  # bl, or b (tail call)
            delta = ((ins & 0xFFFFFF) ^ 0x800000) - 0x800000
            thunk = offset + 4 * i + 8 + 4 * delta
            out.append(f'{imports[thunk + 4]:#x}' if thunk + 4 in imports else f'cro:{thunk:#x}')
            if ins >> 24 == 0xEA and thunk + 4 in imports:
                break
        if ins in (0xE12FFF1E,) or ins & 0x0FFF8000 == 0x08BD8000:  # bx lr / pop {..pc}
            break
    return out


def main():
    for rel, expected in HASHES.items():
        if sha256(GAME / rel) != expected:
            sys.exit(f'{rel}: unexpected sha256 (not the Repolished 1.7.6 baseline)')
    field_path = GAME / 'romfs/DllField.cro'
    field = Cro(field_path.read_bytes())
    imports = {d['offset']: d['target'] + d['addend']
               for d in StaticCRO(field_path).static_imports(StaticCRO(GAME / 'romfs/static.crs'))}
    table = native_table(field)
    print(f'== Native table in DllField.cro: {len(table)} named entries')
    for name in MAISON:
        slot, func = table[name]
        print(f'{name:32s} slot {slot:#x} -> DllField.cro+{func:#x}; calls {", ".join(first_calls(field, imports, func))}')

    code = (GAME / 'exefs/code.bin').read_bytes()
    print('== code.bin facts')
    bad = 0
    for va, expected, meaning in CODE_FACTS:
        got = word(code, va)
        bad += got != expected
        print(f'{va:#x} {got:08x} {"ok " if got == expected else "BAD"} {meaning}')

    exheader = (GAME / 'exheader.bin').read_bytes()
    text_va, text_pages, text_size = struct.unpack_from('<III', exheader, 0x10)
    end, page_end = text_size, text_pages * 0x1000
    padding = code[end:page_end]
    print(f'== .text padding: code.bin {end:#x}-{page_end:#x} (VA {text_va + end:#x}-{text_va + page_end:#x}), '
          f'{len(padding)} bytes, {sum(1 for b in padding if b)} non-zero')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
