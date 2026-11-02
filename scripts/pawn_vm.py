"""Small Pawn 4.0 interpreter for tests: runs one routine of a built Script with stubbed natives and calls.

Covers only the opcodes the generated Battle Factory code uses (anything else raises), with the semantics
of Pawn's amx.c: data and stack share one cell-addressed memory (data at 0, stack growing down from the
top), PROC pushes FRM, RETN pops FRM, the return address and the argument byte count, SYSREQ_N pops its
arguments. It checks the logic of generated code, not GF's VM: what it shows still has to run in Azahar.
"""
from pawn import OPCODES, Program, decode

MASK = 0xFFFFFFFF


def s32(v):
    v &= MASK
    return v - (1 << 32) if v & 0x80000000 else v


class Stop(Exception):
    pass


class VM:
    def __init__(self, script, natives, calls=None, stack_cells=1024):
        """natives: {name hash (signed) -> fn(vm, args) -> int}; calls: {code address -> fn(vm, args) -> int}."""
        self.script = script
        self.code = {ins.address: ins for ins in decode(script.code)}
        self.natives = natives
        self.calls = calls or {}
        self.mem = {4 * k: s32(v) for k, v in enumerate(script.data)}
        self.top = 4 * (len(script.data) + stack_cells)
        self.steps = 0

    def read(self, address):
        if address % 4:
            raise ValueError(f'unaligned read {address:#x}')
        return self.mem.get(address, 0)

    def write(self, address, value):
        if address % 4:
            raise ValueError(f'unaligned write {address:#x}')
        self.mem[address] = s32(value)

    def push(self, value):
        self.stk -= 4
        self.write(self.stk, value)

    def pop(self):
        value = self.read(self.stk)
        self.stk += 4
        return value

    def run(self, address, *args, limit=200000):
        """Call the routine at `address` with `args`; returns PRI."""
        self.stk = self.frm = self.top
        for value in reversed(args):
            self.push(value)
        self.push(4 * len(args))
        self.push(-1)                     # return address: stop
        cip, pri, alt = address, 0, 0
        while True:
            self.steps += 1
            if self.steps > limit:
                raise RuntimeError('step limit')
            ins = self.code[cip]
            name, a = OPCODES[ins.op], ins.args
            nxt = cip + ins.size()
            arg = a[0] if a else 0
            if name == 'PROC':
                self.push(self.frm)
                self.frm = self.stk
            elif name == 'RETN':
                self.frm = self.pop()
                ret = self.pop()
                self.stk += 4 + self.pop()
                if ret == -1:
                    return pri
                nxt = ret
            elif name == 'CALL':
                target = cip + arg
                if target in self.calls:
                    n = self.read(self.stk)
                    params = [self.read(self.stk + 4 + 4 * k) for k in range(n // 4)]
                    self.stk += 4 + n
                    pri = s32(self.calls[target](self, params) or 0)
                else:
                    self.push(nxt)
                    nxt = target
            elif name == 'SYSREQ_N':
                index, size = a
                params = [self.read(self.stk + 4 * k) for k in range(size // 4)]
                self.stk += size
                pri = s32(self.natives[self.script.natives[index][1]](self, params) or 0)
            elif name == 'JUMP':
                nxt = cip + arg
            elif name == 'SWITCH':          # CASETBL count, default, (value, target)...: first match, else default
                table = self.code[cip + arg]
                targets = [t for _, t in Program._targets(table)]
                values = table.args[2::2]
                nxt = next((t for v, t in zip(values, targets[1:]) if s32(v) == pri), targets[0])
            elif name in ('JZER', 'JNZ', 'JEQ', 'JNEQ', 'JSLESS', 'JSLEQ', 'JSGRTR', 'JSGEQ'):
                taken = {'JZER': pri == 0, 'JNZ': pri != 0, 'JEQ': pri == alt, 'JNEQ': pri != alt,
                         'JSLESS': pri < alt, 'JSLEQ': pri <= alt, 'JSGRTR': pri > alt, 'JSGEQ': pri >= alt}[name]
                if taken:
                    nxt = cip + arg
            elif name in ('PUSH_P_C', 'PUSH_C'):
                self.push(arg)
            elif name == 'PUSH_P_S':
                self.push(self.read(self.frm + arg))
            elif name == 'PUSH_PRI':
                self.push(pri)
            elif name == 'PUSH_ALT':
                self.push(alt)
            elif name == 'PPRI':
                pri = self.pop()
            elif name == 'PALT':
                alt = self.pop()
            elif name == 'STACK_P':
                self.stk += arg
            elif name == 'LOAD_P_S_PRI':
                pri = self.read(self.frm + arg)
            elif name == 'LOAD_P_S_ALT':
                alt = self.read(self.frm + arg)
            elif name == 'STOR_P_S_PRI':
                self.write(self.frm + arg, pri)
            elif name == 'CONST_S':
                self.write(self.frm + a[0], a[1])
            elif name == 'ZERO_P_S':
                self.write(self.frm + arg, 0)
            elif name in ('CONST_P_PRI', 'CONST_PRI'):
                pri = s32(arg)
            elif name in ('CONST_P_ALT', 'CONST_ALT'):
                alt = s32(arg)
            elif name == 'ZERO_PRI':
                pri = 0
            elif name == 'LOAD_P_PRI':
                pri = self.read(arg)
            elif name == 'STOR_P_PRI':
                self.write(arg, pri)
            elif name == 'LOAD_I':
                pri = self.read(pri)
            elif name == 'MOVE_ALT':
                alt = pri
            elif name == 'MOVE_PRI':
                pri = alt
            elif name == 'ADD':
                pri = s32(pri + alt)
            elif name == 'SUB_ALT':
                pri = s32(alt - pri)
            elif name in ('ADD_P_C', 'ADD_C'):
                pri = s32(pri + arg)
            elif name == 'SMUL':
                pri = s32(pri * alt)
            elif name == 'SMUL_P_C':
                pri = s32(pri * arg)
            elif name == 'SDIV_ALT':
                if pri == 0:
                    raise ZeroDivisionError
                q = abs(alt) // abs(pri) * (1 if (alt < 0) == (pri < 0) else -1)
                pri, alt = s32(q), s32(alt - q * pri)
            elif name == 'AND':
                pri = s32(pri & alt)
            elif name == 'SHR_P_C_PRI':
                pri = s32((pri & MASK) >> arg)
            elif name == 'SHL_P_C_PRI':
                pri = s32(pri << arg)
            elif name in ('EQ_P_C_PRI', 'EQ_C_PRI'):
                pri = int(pri == s32(arg))
            else:
                raise NotImplementedError(f'{name} at {cip:#x}')
            cip = nxt
