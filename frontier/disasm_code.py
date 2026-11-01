"""Disassemble code.bin (ARM) by virtual address. Text VA = file offset + 0x100000.

Usage: python frontier/disasm_code.py <code.bin> <hex VA> [max instructions]
"""
import struct
import sys
from pathlib import Path

import capstone

BASE = 0x100000


def disasm(data, va, count=300, stop=True):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    out = []
    start = va - BASE
    for ins in md.disasm(data[start:start + 4 * count], va):
        note = ''
        if ins.mnemonic.startswith('ldr') and '[pc, #' in ins.op_str:
            lit = ins.address + 8 + int(ins.op_str.split('#')[1].rstrip(']'), 0)
            note = f'  ; ={struct.unpack_from("<I", data, lit - BASE)[0]:#x}'
        out.append(f'{ins.address:8x}  {ins.mnemonic:8s} {ins.op_str}{note}')
        if stop and (ins.mnemonic == 'bx' and ins.op_str == 'lr' or
                     ins.mnemonic.startswith('pop') and 'pc' in ins.op_str):
            break
    return out


if __name__ == '__main__':
    data = Path(sys.argv[1]).read_bytes()
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    print('\n'.join(disasm(data, int(sys.argv[2], 16), count)))
