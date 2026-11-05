set pagination off
python
import gdb
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def reg(r): return int(gdb.parse_and_eval('$' + r))
def m1(tag):
    work = reg('r4'); s = work + 0x620
    print('M1 %s work=%x setup=%x type839=%u aE1=%u' % (tag, work, s, rd(work+0x839,1), rd(work+0xae1,1)))
    print('M1 %s +0..+0x80: %s' % (tag, ' '.join('%x' % rd(s+o) for o in range(0, 0x80, 4))))
    print('M1 %s +0x49=%u +0x48=%u' % (tag, rd(s+0x49,1), rd(s+0x48,1)))
    t = rd(s+0x70)
    if t: print('M1 %s trainer70: %s' % (tag, ' '.join('%x' % rd(t+o) for o in range(0, 0x38, 4))))
    gdb.execute('dump binary memory work/frontier/palace/b1-setup-%s.bin %d %d' % (tag, s, s + 0x218))
end
break *0x1e32ac
commands
silent
python m1('single')
continue
end
break *0x1e3244
commands
silent
python m1('multi')
continue
end
