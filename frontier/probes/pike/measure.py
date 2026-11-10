#!/usr/bin/env python3
"""Read-only Pike v2 cave/accessor survey. Run after source scripts/env.sh."""
import hashlib
import json
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

sys.path[:0] = [str(Path(__file__).resolve().parents[2])]
import patch

code = patch.REPOLISHED.read_bytes()
assert hashlib.sha256(code).hexdigest() == patch.HASHES[patch.REPOLISHED]
hook, symbols = patch.assemble()
print(json.dumps(dict(start=hex(patch.CAVE), limit=hex(patch.CAVE_END),
                      capacity=patch.CAVE_END - patch.CAVE, used=len(hook),
                      free=patch.CAVE_END - patch.CAVE - len(hook),
                      end=hex(patch.CAVE + len(hook)),
                      zero_input=not any(code[patch.CAVE-patch.BASE:patch.CAVE_END-patch.BASE])), indent=2))
md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
for start, size in [(0x1531c0, 0x60), (0x14f4f8, 0x54), (0x139c00, 0x11c)]:
    print(f'\n== {start:#x}')
    for ins in md.disasm(code[start-patch.BASE:start-patch.BASE+size], start):
        print(f'{ins.address:x} {ins.mnemonic} {ins.op_str}')
