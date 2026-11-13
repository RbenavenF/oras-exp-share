#!/usr/bin/env python3
"""Read-only F9 static selector, streak and level evidence on the hashed baseline.

Callback execution and type-1 party selection still require a laboratory probe.
"""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
from disasm_code import disasm  # noqa: E402
from disasm import disasm as disasm_cro  # noqa: E402
from cro import Cro  # noqa: E402
import maison_map as mm  # noqa: E402
from formats import sha256  # noqa: E402
from analyze_assets import CRO as StaticCRO  # noqa: E402


def main():
    for rel, expected in mm.HASHES.items():
        if sha256(mm.GAME / rel) != expected:
            raise ValueError(f'{rel}: wrong baseline hash')
    code = (mm.GAME / 'exefs/code.bin').read_bytes()
    path = mm.GAME / 'romfs/DllField.cro'
    field = Cro(path.read_bytes())
    imports = {d['offset']: d['target'] + d['addend']
               for d in StaticCRO(path).static_imports(StaticCRO(mm.GAME / 'romfs/static.crs'))}
    print('DllField static imports used by the selector callback:')
    for thunk in (0x3870, 0x2898):
        print(f'{thunk:#x} -> code.bin {imports[thunk + 4]:#x}')
    for label, table in (('increment', 0x45CDB0), ('read', 0x45CF00),
                         ('clear', 0x45CFA4), ('record', 0x45D028)):
        print(f'{label}: type 0..4 table {table:#x}: ' +
              ', '.join(hex(v) for v in struct.unpack_from('<5I', code, table - mm.CODE_BASE)))
    for label, va, count in (
        ('increment dispatch and bodies', 0x45CD98, 78), ('read/clear/record', 0x45CEE8, 112),
        ('AddWinCount consumers', 0x1E2FB0, 65), ('SetRank and selector configuration', 0x1E567C, 65),
        ('private selection and level tail', 0x1E3D2C, 95), ('rival level', 0x1E4E60, 17),
    ):
        print(f'\n== {label}')
        print('\n'.join(disasm(code, va, count, stop=False)))
    for label, at, count in (
        ('GetMyWinCount: script argument order', 0x951A0, 17),
        ('SetTrainer: Singles and Doubles', 0x94EDC, 46),
        ('selector launch', 0x957FC, 77), ('selector callback', 0x96B00, 49),
    ):
        print(f'\n== DllField {label}')
        print('\n'.join(disasm_cro(field, at, count)))


if __name__ == '__main__':
    main()
