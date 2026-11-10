set pagination off
python
import gdb
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def wr(a, v, n=2): gdb.selected_inferior().write_memory(a, v.to_bytes(n, 'little'))
def reg(r): return int(gdb.parse_and_eval('$' + r))
class Hook(gdb.Breakpoint):
    def __init__(s, spec, fn, **kw):
        super().__init__(spec, **kw); s.fn = fn
    def stop(s):
        s.fn(); return False
pa = {'low': 0}      # pa['low'] = N: the next N player entrants get 1 HP (lab RAM only)
def p_start():       # 0x1e33dc (ARENA_START_RESUME): r4 work
    w = reg('r4'); m = rd(w + 0x6c8)
    print('PALACE START work=%x a8=%x palace=%u arena=%u style=%u' % (w, m, m >> 30 & 1, m >> 31, rd(w + 0x621, 1)))
CL = {}
def p_flags():       # palace_ai_flags+0x20: r6 final flags
    c = reg('r4'); CL[rd(c + 0x90, 1)] = c; print('PALACE AIFLAGS client=%u thinker=%u flags=%x' % (rd(c + 0x90, 1), rd(c + 0x91, 1), reg('r6')))
last = {}
def p_dispatch():    # palace_dispatch returns: r2 row (byte 0 = command), r3 column
    c = reg('r4')
    if reg('pc') != 0x579ea4 and reg('cpsr') & (1 << 30): return    # bxne not taken: a later return prints
    print('PALACE DISPATCH client=%u thinker=%u cmd=%u col=%u' % (rd(c + 0x90, 1), rd(c + 0x91, 1), rd(reg('r2'), 1), reg('r3')))
def cstate():
    for i, c in sorted(CL.items()):
        print('CLIENT %u at %x: +92=%u +1e0=%x +1e4=%x +1e8=%x +22=%x +9f=%x' % (i, c, rd(c + 0x92, 1), rd(c + 0x1e0), rd(c + 0x1e4), rd(c + 0x1e8), rd(c + 0x22, 1), rd(c + 0x9f, 1)))
def p_enter():       # arena_enter: r5 entrant, r4 server
    mon = reg('r5'); ident = rd(mon + 0x19, 1)
    print('PALACE ENTER id=%u mon=%x hp=%u' % (ident, mon, rd(mon + 0x10, 2)))
    if ident < 6 and pa['low'] > 0:
        pa['low'] -= 1
        wr(mon + 0x10, 1)
        c = mon - 0xd98
        if all(rd(c + k) == rd(mon + k) for k in (8, 0xc)): wr(c + 0x10, 1)
        print('PALACE ENTER lab: hp=1 on id=%u' % ident)
def p_result():
    print('PALACE RESULT raw=%u' % rd(reg('r0') + 0x73c, 1))
Hook('*0x1e33dc', p_start); Hook('*0x579e4c', p_flags); [Hook('*%#x' % a, p_dispatch) for a in (0x579e78, 0x579e8c, 0x579ea4)]
Hook('*0x579b4c', p_enter); Hook('*0x579998', p_result)
end
