"""GF Pawn field scripts (Gen 6): container, cell compression, instruction decoding and a small assembler.

Format sources: CTRMap-F5 (GFLPawnScript, PawnInstruction, GfHash) and FireyFly's poketools; the opcode
numbering is Pawn 4.0's. Every encoder here is checked by re-encoding the retail scripts byte for byte
(tests/test_pawn.py).
"""
from dataclasses import dataclass, field
from pathlib import Path
import struct

# Pawn 4.0 opcodes in numeric order, as GF's VM numbers them.
OPCODES = '''NONE LOAD_PRI LOAD_ALT LOAD_S_PRI LOAD_S_ALT LREF_PRI LREF_ALT LREF_S_PRI LREF_S_ALT LOAD_I LODB_I
CONST_PRI CONST_ALT ADDR_PRI ADDR_ALT STOR_PRI STOR_ALT STOR_S_PRI STOR_S_ALT SREF_PRI SREF_ALT SREF_S_PRI
SREF_S_ALT STOR_I STRB_I LIDX LIDX_B IDXADDR IDXADDR_B ALIGN_PRI ALIGN_ALT LCTRL SCTRL MOVE_PRI MOVE_ALT XCHG
PUSH_PRI PUSH_ALT PICK PUSH_C PUSH PUSH_S PPRI PALT STACK HEAP PROC RET RETN CALL CALL_PRI JUMP JREL JZER JNZ
JEQ JNEQ JLESS JLEQ JGRTR JGEQ JSLESS JSLEQ JSGRTR JSGEQ SHL SHR SSHR SHL_C_PRI SHL_C_ALT SHR_C_PRI SHR_C_ALT
SMUL SDIV SDIV_ALT UMUL UDIV UDIV_ALT ADD SUB SUB_ALT AND OR XOR NOT NEG INVERT ADD_C SMUL_C ZERO_PRI ZERO_ALT
ZERO ZERO_S SIGN_PRI SIGN_ALT EQ NEQ LESS LEQ GRTR GEQ SLESS SLEQ SGRTR SGEQ EQ_C_PRI EQ_C_ALT INC_PRI INC_ALT
INC INC_S INC_I DEC_PRI DEC_ALT DEC DEC_S DEC_I MOVS CMPS FILL HALT BOUNDS SYSREQ_PRI SYSREQ_C FILE LINE SYMBOL
SRANGE JUMP_PRI SWITCH CASETBL SWAP_PRI SWAP_ALT PUSH_ADR NOP SYSREQ_N SYMTAG BREAK PUSH2_C PUSH2 PUSH2_S
PUSH2_ADR PUSH3_C PUSH3 PUSH3_S PUSH3_ADR PUSH4_C PUSH4 PUSH4_S PUSH4_ADR PUSH5_C PUSH5 PUSH5_S PUSH5_ADR
LOAD_BOTH LOAD_S_BOTH CONST CONST_S ICALL IRETN ISWITCH ICASETBL LOAD_P_PRI LOAD_P_ALT LOAD_P_S_PRI
LOAD_P_S_ALT LREF_P_PRI LREF_P_ALT LREF_P_S_PRI LREF_P_S_ALT LODB_P_I CONST_P_PRI CONST_P_ALT ADDR_P_PRI
ADDR_P_ALT STOR_P_PRI STOR_P_ALT STOR_P_S_PRI STOR_P_S_ALT SREF_P_PRI SREF_P_ALT SREF_P_S_PRI SREF_P_S_ALT
STRB_P_I LIDX_P_B IDXADDR_P_B ALIGN_P_PRI ALIGN_P_ALT PUSH_P_C PUSH_P PUSH_P_S STACK_P HEAP_P SHL_P_C_PRI
SHL_P_C_ALT SHR_P_C_PRI SHR_P_C_ALT ADD_P_C SMUL_P_C ZERO_P ZERO_P_S EQ_P_C_PRI EQ_P_C_ALT INC_P INC_P_S DEC_P
DEC_P_S MOVS_P CMPS_P FILL_P HALT_P BOUNDS_P PUSH_P_ADR SYSREQ_D SYSREQ_ND'''.split()
OP = {name: number for number, name in enumerate(OPCODES)}

# Opcodes whose single argument lives in the upper 16 bits of the opcode cell (CTRMap getHasCompressedArg).
PACKED = {0x09, 0x17, 0x19, 0x1B, 0x21, 0x22, 0x23, 0x24, 0x25, 0x2A, 0x2B, 0x2E, 0x2F, 0x30, 0x41, 0x42, 0x43,
          0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x59, 0x5A,
          0x5D, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x6B, 0x6C, 0x6F, 0x70, 0x71,
          0x74, 0x7A, 0x83, 0x84, 0x86, 0x89, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC,
          0xBD, 0xBE, 0xBF, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCF, 0xD0, 0xD1,
          0xD2, 0xD3, 0xD4, 0xA1, 0xA2, 0xA3, 0xA6, 0xA7, 0xAF, 0xB0, 0xB3, 0xB4, 0xCB, 0xCD, 0xA4, 0xA5, 0xA8,
          0xA9, 0xB1, 0xB2, 0xB5, 0xB6, 0xCC, 0xCE}
# Number of argument cells following an unpacked opcode (CTRMap getArguments); CASETBL is variable.
ARGC = {**{op: 1 for op in (0x01, 0x02, 0x05, 0x06, 0x0F, 0x10, 0x13, 0x14, 0x6D, 0x72, 0x03, 0x04, 0x07, 0x08,
                            0x11, 0x12, 0x15, 0x16, 0x6E, 0x9E, 0x73, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x18, 0x1A,
                            0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x26, 0x27, 0x28, 0x29, 0x2C, 0x2D, 0x34, 0x44, 0x45,
                            0x46, 0x47, 0x57, 0x58, 0x5B, 0x5C, 0x69, 0x6A, 0x75, 0x76, 0x77, 0x78, 0x79, 0x85,
                            0x31, 0x33, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40,
                            0x81, 0x7B)},
        **{op: 2 for op in (0x87, 0x8B, 0x8C, 0x8D, 0x9A, 0x9B, 0x9C, 0x9D, 0x8A)},
        **{op: 3 for op in (0x8E, 0x8F, 0x90, 0x91)},
        **{op: 4 for op in (0x92, 0x93, 0x94, 0x95)},
        **{op: 5 for op in (0x96, 0x97, 0x98, 0x99)}}
# Branches whose argument is relative to the instruction (CALL, JUMP, conditional jumps, SWITCH).
BRANCHES = {0x31, 0x33, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x81}
CASETBL = OP['CASETBL']
HEADER = 0x3C


def gf_hash(name):
    """Native-name hash the VM resolves natives by (CTRMap GfHash)."""
    h = 0
    for char in name.encode('ascii'):
        h = ((h * 0x83) ^ char) & 0xFFFFFFFF
    return h


def s32(value):
    value &= 0xFFFFFFFF
    return value - (1 << 32) if value & 0x80000000 else value


def decompress_cells(data, count):
    cells, value, started, pos = [], 0, False, 0
    while len(cells) < count:
        byte = data[pos]
        pos += 1
        bits = byte & 0x7F
        if not started:
            value = (-1 << 7 | bits) if bits & 0x40 else bits
            started = True
        else:
            value = (value << 7) | bits
        if byte & 0x80:
            continue
        cells.append(s32(value))
        started = False
    return cells, pos


def compress_cells(cells):
    out = bytearray()
    for cell in cells:
        value = s32(cell)
        groups = []
        while True:
            groups.append(value & 0x7F)
            value >>= 7
            if value in (0, -1) and (groups[-1] & 0x40) == (0x40 if value == -1 else 0):
                break
        groups.reverse()
        if len(groups) > 5:
            raise ValueError('Cell does not fit 32 bits')
        if len(groups) == 5:
            groups[0] &= 0x0F  # the fifth group carries only the top four bits, never sign extension
        out += bytes([g | 0x80 for g in groups[:-1]] + [groups[-1]])
    return bytes(out)


@dataclass
class Script:
    """A parsed script: header words, prefix tables, the bytes between them and the code, and decoded cells."""
    magic: int
    version: int
    min_version: int
    flags: int
    defsize: int
    headroom: int
    main: int
    tables: list  # six lists of defsize/4-tuples: publics, natives, libraries, publicvars, tags, names
    rest: bytes
    code: list  # cells before the data section
    data: list  # cells of the data section (movement lists etc.)

    @property
    def natives(self):
        return self.tables[1]

    @classmethod
    def parse(cls, raw):
        (length, magic, version, min_version, flags, defsize, code_start, data_start, heap_start, allocated,
         main, *offsets) = struct.unpack_from('<IHBBHHIIIII7I', raw)
        if magic != 0xF1E0 or defsize != 8 or offsets[0] != HEADER:
            raise ValueError('Not a GF Pawn script')
        tables = []
        for start, end in zip(offsets, offsets[1:]):
            tables.append([struct.unpack_from('<2i', raw, start + i * 8) for i in range((end - start) // 8)])
        cells, used = decompress_cells(raw[code_start:length], (heap_start - code_start) // 4)
        if code_start + used != length or any(raw[length:]) or len(raw) - length >= 4:
            raise ValueError('Unexpected script tail')
        split = (data_start - code_start) // 4
        return cls(magic, version, min_version, flags, defsize, allocated - heap_start, main, tables,
                   raw[offsets[-1]:code_start], cells[:split], cells[split:])

    def build(self, pad=True):
        """Zone scripts are stored padded to four bytes; shared-archive entries are not."""
        offsets = [HEADER]
        for table in self.tables:
            offsets.append(offsets[-1] + 8 * len(table))
        code_start = offsets[-1] + len(self.rest)
        heap_start = code_start + 4 * (len(self.code) + len(self.data))
        body = compress_cells(self.code + self.data)
        length = code_start + len(body)
        out = bytearray(struct.pack('<IHBBHHIIIII7I', length, self.magic, self.version, self.min_version,
                                    self.flags, self.defsize, code_start, heap_start - 4 * len(self.data),
                                    heap_start, heap_start + self.headroom, self.main, *offsets))
        for table in self.tables:
            for entry in table:
                out += struct.pack('<2i', *entry)
        out += self.rest + body
        if pad:
            out += bytes(-len(out) % 4)
        return bytes(out)

    def native_index(self, name, add=False):
        wanted = s32(gf_hash(name))
        for index, (_, value) in enumerate(self.natives):
            if value == wanted:
                return index
        if not add:
            raise KeyError(name)
        self.natives.append((0, wanted))
        return len(self.natives) - 1


@dataclass
class Instruction:
    address: int
    op: int
    args: list = field(default_factory=list)

    @property
    def name(self):
        return OPCODES[self.op]

    def size(self):
        if self.op in PACKED:
            return 4
        if self.op == CASETBL:
            return 4 * (3 + 2 * self.args[0])
        return 4 * (1 + ARGC.get(self.op, 0))


def decode(cells):
    """Split code cells into instructions; branch and case targets stay relative, as stored."""
    result, index = [], 0
    while index < len(cells):
        cell, address = cells[index], index * 4
        op = cell & 0x7FFF
        if op >= len(OPCODES):
            raise ValueError(f'Unknown opcode {op:#x} at {address:#x}')
        if op in PACKED:
            if cell & 0x8000:
                raise ValueError(f'Unexpected bits in packed cell {cell:#x} at {address:#x}')
            args = [cell >> 16]
            index += 1
        elif op == CASETBL:
            count = cells[index + 1]
            args = cells[index + 1:index + 3 + 2 * count]
            index += 3 + 2 * count
        else:
            if cell != op:
                raise ValueError(f'Unexpected bits in opcode cell {cell:#x} at {address:#x}')
            argc = ARGC.get(op, 0)
            args = cells[index + 1:index + 1 + argc]
            index += 1 + argc
        result.append(Instruction(address, op, list(args)))
    return result


def encode(instructions):
    cells = []
    for ins in instructions:
        if ins.op in PACKED:
            if not -0x8000 <= ins.args[0] < 0x8000:
                raise ValueError(f'{ins.name} argument {ins.args[0]} does not fit a packed cell')
            cells.append(s32((ins.args[0] << 16) | ins.op))
        else:
            cells.append(ins.op)
            cells.extend(ins.args)
    return cells


# Opcodes that address the global data section; their operand is a data address, not a constant.
DATA_OPS = {OP[n] for n in ('LOAD_PRI LOAD_ALT LREF_PRI LREF_ALT STOR_PRI STOR_ALT SREF_PRI SREF_ALT INC DEC ZERO '
                            'PUSH PUSH2 PUSH3 PUSH4 PUSH5 LOAD_BOTH LOAD_P_PRI LOAD_P_ALT LREF_P_PRI LREF_P_ALT '
                            'STOR_P_PRI STOR_P_ALT SREF_P_PRI SREF_P_ALT PUSH_P ZERO_P INC_P DEC_P').split()}


@dataclass
class Op:
    """An instruction whose branch targets are label names (str) instead of offsets."""
    op: int
    args: list


class Program:
    """Symbolic, relocatable form of a script: labels, instructions, and the data section.

    Branches are stored as label names, so code can be inserted or appended anywhere and every
    CALL, JUMP, SWITCH and CASETBL is recomputed when the program is built.
    """

    def __init__(self, script):
        self.script = script
        self.items = []  # Op or ('label', name)
        self.data = list(script.data)
        self.data_labels = {}
        self.native_hashes = [h for _, h in script.natives]
        self.publics = []  # (label, name hash); a fresh program publishes nothing

    @classmethod
    def from_script(cls, script, prefix='L'):
        program = cls(script)
        publics = {address for address, _ in script.tables[0]}
        program.items = program._symbolic(script, decode(script.code), prefix, {script.main} | publics)
        # Public functions are named code addresses the engine calls by hash: they move with the code.
        program.publics = [(f'{prefix}{address:x}', name) for address, name in script.tables[0]]
        return program

    @staticmethod
    def _targets(ins):
        """(argument index, absolute target) for each branch operand of an instruction."""
        if ins.op in BRANCHES:
            return [(0, ins.address + ins.args[0])]
        if ins.op == CASETBL:
            # Each target is relative to the cell just before it: the count cell for the default,
            # the case value for each case.
            result = [(1, ins.address + 4 + ins.args[1])]
            for k in range(ins.args[0]):
                result.append((3 + 2 * k, ins.address + 12 + 8 * k + ins.args[3 + 2 * k]))
            return result
        return []

    def _symbolic(self, script, instructions, prefix, keep):
        starts = {ins.address for ins in instructions}
        wanted = set()
        for ins in instructions:
            for _, target in self._targets(ins):
                if target not in starts:
                    raise ValueError(f'Branch into the middle of an instruction at {ins.address:#x}')
                wanted.add(target)
        items = []
        for ins in instructions:
            if ins.address in wanted or ins.address in keep:
                items.append(('label', f'{prefix}{ins.address:x}'))
            args = list(ins.args)
            for index, target in self._targets(ins):
                args[index] = f'{prefix}{target:x}'
            items.append(Op(ins.op, args))
        return items

    def native(self, value):
        """Index of a native (by name or signed hash), added to the table if missing."""
        wanted = s32(gf_hash(value)) if isinstance(value, str) else s32(value)
        if wanted not in self.native_hashes:
            self.native_hashes.append(wanted)
        return self.native_hashes.index(wanted)

    def label(self, name):
        self.items.append(('label', name))

    def emit(self, name, *args):
        op = OP[name]
        if op == OP['SYSREQ_N'] and isinstance(args[0], str):
            args = (self.native(args[0]),) + args[1:]
        self.items.append(Op(op, list(args)))

    def sysreq(self, native, *pushed):
        """Push arguments (last argument first, as the compiler does) and call a native."""
        for value in reversed(pushed):
            self.push(value)
        # A native is named by its name or by its (signed) hash, never by a table index.
        self.items.append(Op(OP['SYSREQ_N'], [self.native(native), 4 * len(pushed)]))

    def call(self, target, *pushed):
        for value in reversed(pushed):
            self.push(value)
        self.emit('PUSH_P_C', 4 * len(pushed))
        self.emit('CALL', target)

    def push(self, value):
        if isinstance(value, tuple) and value[0] == 'local':
            self.emit('PUSH_P_S', value[1])
        elif -0x8000 <= value < 0x8000:
            self.emit('PUSH_P_C', value)
        else:
            self.emit('PUSH_C', value)

    def data_block(self, name, cells):
        self.data_labels[name] = 4 * len(self.data)
        self.data.extend(cells)
        return self.data_labels[name]

    def transplant(self, source, entry, prefix, yield_label=None):
        """Copy the routine at `entry` of another script and every routine it calls.

        Routines are delimited by PROC. A CALL to the source's yield stub (address 4) is redirected
        to `yield_label`. Code that addresses the source's data section is refused.
        """
        instructions = decode(source.code)
        procs = sorted(ins.address for ins in instructions if ins.op == OP['PROC'])
        by_address = {ins.address: ins for ins in instructions}
        todo, seen = [entry], set()
        while todo:
            start = todo.pop()
            if start in seen:
                continue
            seen.add(start)
            end = next((p for p in procs if p > start), len(source.code) * 4)
            for address in sorted(a for a in by_address if start <= a < end):
                ins = by_address[address]
                if ins.op in DATA_OPS:
                    raise ValueError(f'Routine {start:#x} addresses source data at {address:#x}')
                if ins.op == OP['CALL']:
                    target = address + ins.args[0]
                    if target == 4 and yield_label:
                        continue
                    todo.append(target)
        chunk = [by_address[a] for a in sorted(by_address) if any(
            s <= a < next((p for p in procs if p > s), len(source.code) * 4) for s in seen)]
        natives, starts = {}, {ins.address for ins in chunk}
        branched = {t for i in chunk for _, t in self._targets(i)}
        items = []
        for ins in chunk:
            if ins.address in seen or ins.address in branched:
                items.append(('label', f'{prefix}{ins.address:x}'))
            args = list(ins.args)
            for index, target in self._targets(ins):
                if ins.op == OP['CALL'] and target == 4 and yield_label:
                    args[index] = yield_label
                elif target not in starts:
                    raise ValueError(f'Routine branches outside the copied closure at {ins.address:#x}')
                else:
                    args[index] = f'{prefix}{target:x}'
            if ins.op == OP['SYSREQ_N']:
                args[0] = natives.setdefault(args[0], self.native(source.natives[args[0]][1]))
            items.append(Op(ins.op, args))
        self.items.extend(items)
        return f'{prefix}{entry:x}'

    def layout(self):
        address, labels = 0, {}
        for item in self.items:
            if isinstance(item, tuple):
                if item[1] in labels:
                    raise ValueError(f'Duplicate label {item[1]}')
                labels[item[1]] = address
            else:
                address += Instruction(address, item.op, item.args).size()
        return labels

    def build_script(self, main_label):
        labels = self.layout()
        instructions, address = [], 0
        for item in self.items:
            if isinstance(item, tuple):
                continue
            args = list(item.args)
            ins = Instruction(address, item.op, args)
            if item.op in BRANCHES:
                args[0] = labels[args[0]] - address
            elif item.op == CASETBL:
                args[1] = labels[args[1]] - (address + 4)
                for k in range(args[0]):
                    args[3 + 2 * k] = labels[args[3 + 2 * k]] - (address + 12 + 8 * k)
            for index, value in enumerate(args):
                if isinstance(value, str):
                    raise ValueError(f'Unresolved operand {value} in {OPCODES[item.op]}')
            instructions.append(Instruction(address, item.op, args))
            address += ins.size()
        script = Script(self.script.magic, self.script.version, self.script.min_version, self.script.flags,
                        self.script.defsize, self.script.headroom, labels[main_label],
                        [list(t) for t in self.script.tables], self.script.rest, encode(instructions),
                        list(self.data))
        script.tables[0] = [(labels[label], name) for label, name in self.publics]
        script.tables[1] = [(0, h) for h in self.native_hashes]
        return script


def native_names(tsv_path):
    """Signed hash -> name, from a "HASH<TAB>NAME" table such as CTRMap-F5's oras_natives.tsv."""
    names = {}
    for line in Path(tsv_path).read_text(encoding='utf-8').splitlines():
        if '\t' in line:
            value, name = line.split('\t', 1)
            names.setdefault(s32(int(value, 16)), name.strip())
    return names


def listing(script, names=None):
    """Readable disassembly with absolute branch targets and native names."""
    names = names or {}
    lines = []
    for ins in decode(script.code):
        args = list(ins.args)
        targets = dict(Program._targets(ins))
        text = []
        for index, value in enumerate(args):
            if index in targets:
                text.append(f'@{targets[index]:x}')
            elif ins.op == OP['SYSREQ_N'] and index == 0:
                text.append(names.get(script.natives[value][1], f'native{value}'))
            else:
                text.append(str(value))
        marker = '>' if ins.address == script.main else ' '
        lines.append(f'{marker}{ins.address:5x}  {ins.name} {", ".join(text)}')
    return '\n'.join(lines)
