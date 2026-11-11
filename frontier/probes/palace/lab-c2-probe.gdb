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
# Build c-build (palace_ai.py): code.bin palace_ai_flags 0x579f78 (lr = CRO + 0x73260), arena_enter 0x579cec,
# IsWin 0x1e5664, StartBattle resume 0x1e33dc. CRO palace_moves 0xd7630: after rand 0xd767c, after nature
# 0xd7690, group drawn 0xd76cc, exit 0xd7734; final AI move 0xd78c (r1 move, r6 slot, r4 client).
pa = {'hp_pct': 0}   # pa['hp_pct'] = P: the next player entrant gets P % of its max HP (lab RAM fixture)
CL = {}; BASES = set(); CUR = {}
def p_start():
    w = reg('r4'); m = rd(w + 0x6c8)
    print('PALACE START a8=%x palace=%u arena=%u style=%u' % (m, m >> 30 & 1, m >> 31, rd(w + 0x621, 1)))
def p_flags():
    c = reg('r4'); base = reg('lr') - 0x73260
    CL[rd(c + 0x90, 1)] = c
    print('PALACE AIFLAGS client=%u thinker=%u cro=%x' % (rd(c + 0x90, 1), rd(c + 0x91, 1), base))
    if base not in BASES:
        BASES.add(base); CUR['base'] = base
        Hook('*%#x' % (base + 0xd767c), c_rand); Hook('*%#x' % (base + 0xd7690), c_nature)
        Hook('*%#x' % (base + 0xd76cc), c_group); Hook('*%#x' % (base + 0xd7734), c_exit)
        Hook('*%#x' % (base + 0xd78c), c_move); Hook('*%#x' % (base + 0xd7630), c_entry)
def c_entry(): CUR['filtered'] = False
def c_rand(): CUR['pct'] = reg('r0'); CUR['filtered'] = True
def c_nature(): CUR['nature'] = reg('r0')
def c_group():
    mon = reg('r5'); CUR['group'] = reg('r7')
    CUR['hp'] = (rd(mon + 0x10, 2), rd(mon + 0xe, 2))
    CUR['moves'] = [rd(mon + 0x11c + 14 * k, 2) for k in range(4)]
def c_exit():
    r6 = reg('r6'); usable = [rd(r6 + k, 1) for k in range(4)]
    if CUR.get('filtered'):
        hp, mx = CUR['hp']
        print('PALACE FILTER nature=%u pct=%u hp=%u/%u col=%s group=%u moves=%s kept=%s ret=%u' % (
            CUR['nature'], CUR['pct'], hp, mx, 'low' if hp <= mx // 2 else 'high', CUR['group'], CUR['moves'],
            usable, reg('r9')))
        CUR['kept'] = usable
    else:
        print('PALACE NOFILTER client=%x usable=%s ret=%u' % (reg('r4'), usable, reg('r9')))
    CUR['filtered'] = False
def c_move():
    c = reg('r4')
    print('PALACE MOVE client=%u thinker=%u slot=%u move=%u' % (rd(c + 0x90, 1), rd(c + 0x91, 1), reg('r6'), reg('r1')))
def p_enter():
    mon = reg('r5'); ident = rd(mon + 0x19, 1)
    print('PALACE ENTER id=%u mon=%x hp=%u/%u' % (ident, mon, rd(mon + 0x10, 2), rd(mon + 0xe, 2)))
    if ident < 6 and pa['hp_pct'] > 0:
        hp = max(1, rd(mon + 0xe, 2) * pa['hp_pct'] // 100); pa['hp_pct'] = 0
        wr(mon + 0x10, hp)
        c = mon - 0xd98
        if all(rd(c + k) == rd(mon + k) for k in (8, 0xc)): wr(c + 0x10, hp)
        print('PALACE ENTER lab: hp=%u on id=%u' % (hp, ident))
def p_result():
    print('PALACE ISWIN raw=%u' % rd(reg('r0') + 0x73c, 1))
Hook('*0x1e33dc', p_start); Hook('*0x579f78', p_flags); Hook('*0x579cec', p_enter); Hook('*0x1e5664', p_result)
end
