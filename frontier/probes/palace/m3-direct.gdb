python
import gdb
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def reg(r): return int(gdb.parse_and_eval('$' + r))
def m3_ctor():
    cid, typ = reg('r8'), reg('r6')
    print('M3 CTOR client=%u obj=%x type=%u lr_base=%x' % (cid, reg('r4'), typ, rd(reg('sp')+0x58,4)))
    if cid == 0 and m3_mode == 'ai':
        gdb.execute('set $r6 = 1')
        print('M3 CTOR client 0 forced to AI')
def m3_ai():
    print('M3 AIOBJ client=%u obj=%x ai=%x flags=%x' % (rd(reg('r4')+0x90,1), reg('r4'), reg('r0'), rd(reg('r0')+0xc)))
end
python m3_mode = 'ai'
break *0x766064
commands
silent
python m3_ctor()
continue
end
break *0x766304
commands
silent
python m3_ai()
continue
end
