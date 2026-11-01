"""Disassemble a CRO function by file offset (ARM), annotating relocated literal pointers.

Usage: python frontier/disasm.py <cro> <hex offset> [count]
Stops at the first `pop {..pc}` / `bx lr` after `count` instructions at the latest.
"""
import struct
import sys
from pathlib import Path

import capstone

sys.path.insert(0, str(Path(__file__).parent))
from cro import Cro


def disasm(cro, start, count=200, stop=True):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    pointers = cro.pointer_at()
    out = []
    for ins in md.disasm(cro.data[start:start + 4 * count], start):
        note = ''
        if ins.mnemonic.startswith('ldr') and '[pc, #' in ins.op_str:
            lit = ins.address + 8 + int(ins.op_str.split('#')[1].rstrip(']'), 0)
            value = struct.unpack_from('<I', cro.data, lit)[0]
            note = f'  ; ={value:#x}' + (f' -> @{pointers[lit]:#x}' if lit in pointers else '')
        out.append(f'{ins.address:8x}  {ins.mnemonic:8s} {ins.op_str}{note}')
        if stop and (ins.mnemonic == 'bx' and ins.op_str == 'lr' or
                     ins.mnemonic.startswith('pop') and 'pc' in ins.op_str):
            break
    return out


if __name__ == '__main__':
    cro = Cro(Path(sys.argv[1]).read_bytes())
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    print('\n'.join(disasm(cro, int(sys.argv[2], 16), count)))
