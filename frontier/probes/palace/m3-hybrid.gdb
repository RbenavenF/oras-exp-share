set pagination off
source frontier/probes/palace/m1.gdb
python
import gdb
CRO = 0x6f3000
CLIENT0 = 0x820d9ac
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def reg(r): return int(gdb.parse_and_eval('$' + r))
class Hook(gdb.Breakpoint):
    def __init__(s, spec, fn, **kw):
        super().__init__(spec, **kw); s.fn = fn
    def stop(s):
        s.fn(); return False
ROWS = {}
def table_cmd(i): return rd(CRO + 0xdbc68 + i * 0x1c)
def c_ctor_type():           # 0x731f4: r0 = client+0x91 just loaded
    cid = rd(reg('r4') + 0x90, 1)
    if cid == 0 and m3_mode == 'hybrid':
        gdb.execute('set $r0 = 1'); print('M3 CTOR client 0: AI object requested, thinker stays %u' % rd(reg('r4')+0x91,1))
def c_ai_flags():            # 0x732c0: r6 = AI flags for the new AI object
    cid = rd(reg('r4') + 0x90, 1)
    print('M3 AIFLAGS client=%u flags=%x' % (cid, reg('r6')))
    if cid == 0 and m3_mode == 'hybrid':
        gdb.execute('set $r6 = 7')
def c_ai_obj():              # 0x73304: r0 = AI object
    print('M3 AIOBJ client=%u obj=%x ai=%x flags=%x' % (rd(reg('r4')+0x90,1), reg('r4'), reg('r0'), rd(reg('r0')+0xc)))
def c_dispatch():            # 0x49f0 / 0x7668: r0 = row, r3 = thinker column
    r4, row = reg('r4'), reg('r0')
    cid, cmd = rd(r4 + 0x90, 1), table_cmd(row)
    forced = cid == 0 and m3_mode == 'hybrid' and cmd in (3, 5, 6)
    if forced: gdb.execute('set $r3 = 1')
    print('M3 DISPATCH pc=%x client=%u cmd=%u col=%u%s' % (reg('pc') - CRO, cid, cmd, reg('r3'), ' (forced AI)' if forced else ''))
hooks = []
def arm():
    pc, v = reg('pc'), rd(CLIENT0 + 0x3c)
    if v == 0 and CRO <= pc < CRO + 0xe0000:
        for h in hooks: h.delete()
        hooks[:] = [Hook('*%#x' % (CRO + 0x731f4), c_ctor_type), Hook('*%#x' % (CRO + 0x732c0), c_ai_flags),
                    Hook('*%#x' % (CRO + 0x73304), c_ai_obj), Hook('*%#x' % (CRO + 0x49f0), c_dispatch),
                    Hook('*%#x' % (CRO + 0x7668), c_dispatch)]
        print('M3 armed (client 0 allocated, pc=%x)' % pc)
Hook('*(int*)%#x' % (CLIENT0 + 0x3c), arm, type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE)
m3_mode = 'hybrid'
end
