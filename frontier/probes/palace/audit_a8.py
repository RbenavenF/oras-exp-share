"""Static audit of the readers of BattleSetup+0xa8 that could see bit 30 (Palace B mark, reports/frontier.md §33).

For every `ldr rX, [rY, #OFF]` (OFF = 0xa8 in the CROs, 0x6c8 = work+0x620+0xa8 in code.bin) and every byte/halfword
read of its upper part (+0xab / +0xaa), follow rX forward (max 8 instructions, until a branch or its redefinition)
and classify each use:
  mask-safe   tst/and/bic with an immediate without bit 30
  MASK30      an immediate mask with bit 30
  copy        str/strd/mov to another register (followed no further: reported to be read by hand)
  WHOLE       any other use (cmp, shifts, register masks...): sees bit 30, reported
Also lists the calls to the variable-mask getter at DllBattle 0x5eaa0 with the r1 constant before them.
Usage: python -I audit_a8.py <code.bin> <romfs dir>   (output: text to stdout)
"""
import struct
import sys
from pathlib import Path

import capstone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cro import Cro  # noqa: E402

BIT = 0x40000000
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
md.detail = True
md.skipdata = True


def insns(data, start, length, base=0):
    return list(md.disasm(data[start:start + length], start + base))


def regs_read(ins):
    return {ins.reg_name(r) for r in ins.regs_access()[0]}


def regs_written(ins):
    return {ins.reg_name(r) for r in ins.regs_access()[1]}


def classify(seq, i, reg):
    uses = []
    for ins in seq[i + 1:i + 9]:
        try:
            read, written = regs_read(ins), regs_written(ins)
        except capstone.CsError:
            break
        if reg in read:
            imms = [op.imm for op in ins.operands if op.type == capstone.arm.ARM_OP_IMM]
            m = ins.mnemonic.split('.')[0]
            base = m.rstrip('s') if m not in ('tst', 'teq') else m
            for cond in ('eq', 'ne', 'cs', 'cc', 'mi', 'pl', 'hs', 'lo', 'hi', 'ls', 'ge', 'lt', 'gt', 'le'):
                if base.endswith(cond) and base[:-2] in ('tst', 'and', 'bic', 'mov', 'str', 'cmp', 'orr', 'ldr'):
                    base = base[:-2]
            if base in ('tst', 'and', 'bic') and imms and len(ins.operands) == (2 if base == 'tst' else 3):
                kind = 'MASK30' if imms[-1] & BIT else 'mask-safe'
            elif base in ('str', 'strd', 'stm', 'push', 'mov') and not imms:
                kind = 'copy'
            elif base in ('ldr', 'ldrb', 'ldrh') and ins.op_str.split(',')[0].strip() != reg:
                kind = 'base?'          # rX used as an address: +0xa8 of something else, not the setup word
            else:
                kind = 'WHOLE'
            uses.append((kind, f'{ins.address:x} {ins.mnemonic} {ins.op_str}'))
        if reg in written or ins.mnemonic.startswith(('b', 'pop')) and not ins.mnemonic.startswith('bic'):
            break
    return uses


def audit(name, data, segments, offsets, base=0):
    report = {}
    for start, length in segments:
        seq = insns(data, start, length)
        for i, ins in enumerate(seq):
            if ins.mnemonic.split('.')[0] not in ('ldr', 'ldrb', 'ldrh', 'ldrsb', 'ldrsh'):
                continue
            if len(ins.operands) != 2 or ins.operands[1].type != capstone.arm.ARM_OP_MEM:
                continue
            disp = ins.operands[1].mem.disp
            if ins.operands[1].mem.base == capstone.arm.ARM_REG_PC:
                continue
            m = ins.mnemonic
            hit = (m.startswith('ldr') and not m.startswith(('ldrb', 'ldrh', 'ldrsb', 'ldrsh', 'ldrd'))
                   and disp in offsets) or (m.startswith(('ldrb', 'ldrsb')) and disp in [o + 3 for o in offsets]) \
                or (m.startswith(('ldrh', 'ldrsh')) and disp in [o + 2 for o in offsets])
            if not hit:
                continue
            reg = ins.reg_name(ins.operands[0].reg)
            report[ins.address + base] = (f'{ins.mnemonic} {ins.op_str}', classify(seq, i, reg))
    counts = {}
    for addr, (text, uses) in sorted(report.items()):
        kinds = sorted({k for k, _ in uses}) or ['unused']
        for k in kinds:
            counts[k] = counts.get(k, 0) + 1
    print(f'== {name}: {len(report)} reads of {[hex(o) for o in offsets]}; per use kind: {counts}')
    for addr, (text, uses) in sorted(report.items()):
        kinds = {k for k, _ in uses}
        if kinds & {'MASK30', 'WHOLE', 'copy'} or not uses or text.startswith(('ldrb', 'ldrh', 'ldrsb', 'ldrsh')):
            print(f'  {addr:x} {text}')
            for k, u in uses:
                print(f'      {k:9} {u}')
    return report


def getter_calls(data, segments, getter):
    print(f'== calls to the variable-mask getter {getter:#x} (r1 set by the nearest mov before)')
    for start, length in segments:
        seq = insns(data, start, length)
        for i, ins in enumerate(seq):
            if ins.mnemonic in ('bl', 'b', 'blne', 'bleq', 'bne', 'beq') and ins.op_str == f'#{getter:#x}':
                r1 = '?'
                for prev in reversed(seq[max(0, i - 8):i]):
                    if prev.op_str.startswith('r1,') and prev.mnemonic.startswith(('mov', 'ldr', 'orr', 'lsl')):
                        r1 = f'{prev.mnemonic} {prev.op_str}'
                        break
                imm = r1.rsplit('#', 1)[-1] if '#' in r1 else None
                flag = ''
                if imm is None or not prev.mnemonic.startswith('mov'):
                    flag = 'VARIABLE'
                elif int(imm, 0) & BIT:
                    flag = 'MASK30'
                print(f'  {ins.address:x} {ins.mnemonic}  r1: {r1} {flag}')


def main(code_bin, romfs):
    code = Path(code_bin).read_bytes()
    text_size = struct.unpack_from('<I', code, 0) and None
    audit('code.bin (work+0x6c8)', code, [(0, 0x480000)], [0x6C8], base=0x100000)
    for cro_path in sorted(Path(romfs).glob('*.cro')):
        cro = Cro(cro_path.read_bytes())
        text = [(s, n) for s, n, kind in cro.segments if kind == 0 and n]
        if cro_path.name == 'DllBattle.cro':
            audit(cro_path.name, cro.data, text, [0xA8])
            getter_calls(cro.data, text, 0x5EAA0)
        else:
            rep = {}
            for s, n in text:
                for ins in insns(cro.data, s, n):
                    if (ins.mnemonic.startswith(('tst', 'and', 'bic', 'orr')) and '#0x40000000' in ins.op_str):
                        rep[ins.address] = f'{ins.mnemonic} {ins.op_str}'
            if rep:
                print(f'== {cro_path.name}: immediates with bit 30 alone (any field, not only +0xa8): {len(rep)}')
                for a, t in sorted(rep.items()):
                    print(f'  {a:x} {t}')


if __name__ == '__main__':
    main(*sys.argv[1:])
