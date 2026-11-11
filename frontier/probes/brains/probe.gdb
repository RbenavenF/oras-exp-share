set pagination off
python
import gdb
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def reg(r): return int(gdb.parse_and_eval('$' + r))
class Hook(gdb.Breakpoint):
    def __init__(s, spec, fn, **kw):
        super().__init__(spec, **kw); s.fn = fn
    def stop(s):
        s.fn(); return False
# code.bin: 0x1e4a14 SetTrainer's «save id» (called from DllField 0x94f28: lr = CRO + 0x94f2c), IsWin 0x1e5664.
# DllField: 0x95048, just after StartBattle's core and brain_start (frontier/brains.py SITES).
B = {'base': None, 'work': None}
def works(w, n): return rd(rd(rd(rd(w + 0xb78) + 0x1c)) + 0x13144 + 2 * (n - 0x4000), 2)
def state(tag, w):
    print('BRAINS %s route=%u brain=%u symbols=%#x streak=%u record=%u active=%u' % (
        tag, works(w, 16438), works(w, 16730), works(w, 16729), works(w, 16441), works(w, 16443), works(w, 16442)))
def on_trainer():
    w = reg('r0'); B['work'] = w
    base = reg('lr') - 0x94f2c
    print('BRAINS TRAINER id=%u boss=%u rank=%u cro=%x' % (rd(w + 4), rd(w + 1, 1), rd(w + 0x838, 1), base))
    state('PRE', w)
    if B['base'] != base:
        B['base'] = base
        Hook('*%#x' % (base + 0x95048), on_started)
def on_started():
    w = B['work']; party = rd(w + 0x670); n = rd(party + 0x18, 1)
    print('BRAINS RIVAL trainer=%u members=%u' % (rd(w + 4), n))
    for k in range(n):
        m = rd(party + 4 * k); blk = rd(rd(m + 0xc) + 4)
        print('BRAINS MON %u lv=%u hp=%u/%u atk=%u def=%u spe=%u spa=%u spd=%u' % (
            k, rd(blk + 4, 1), rd(blk + 8, 2), rd(blk + 0xa, 2), rd(blk + 0xc, 2), rd(blk + 0xe, 2), rd(blk + 0x10, 2),
            rd(blk + 0x12, 2), rd(blk + 0x14, 2)))
def on_iswin():
    print('BRAINS ISWIN raw=%u' % rd(reg('r0') + 0x73c, 1))
    if B['work']: state('POST', B['work'])
Hook('*0x1e4a14', on_trainer)
Hook('*0x1e5664', on_iswin)
end
