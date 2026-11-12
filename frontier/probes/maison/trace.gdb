# Passive F7-CONSOLA-MANSION trace for the published alpha v0.1.
# DllBattle base 0x6f3000 must be confirmed from the constructor instruction below.
set pagination off
set language c
python
import gdb

def rd(a, n=4):
    return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')

def reg(n):
    return int(gdb.parse_and_eval('$' + n))

class MaisonTrace(gdb.Breakpoint):
    def __init__(self, address, kind):
        super().__init__('*%#x' % address)
        self.kind = kind
    def stop(self):
        try:
            if self.kind == 'start':
                w = reg('r4')
                save = rd(rd(rd(w + 0xb78) + 0x1c))
                works = {n: rd(save + 0x13144 + 2*(n - 0x4000), 2)
                         for n in (16438, 16489, 16685)}
                print('MAISON START work=%#x style=%u works=%s' % (w, rd(w+0x839,1), works))
            elif self.kind == 'player':
                selection = reg('r2')
                print('MAISON PLAYER work=%#x selection=%#x count=%u slots=%s dest=%#x' %
                      (reg('r0'), selection, rd(selection+0x1c),
                       [rd(selection+4+4*k) for k in range(6)], reg('r3')))
            elif self.kind == 'tail':
                print('MAISON PLAYER TAIL count=%u party=%#x actual=%u' %
                      (reg('r0'), reg('r9'), rd(reg('r9')+0x18,1)))
            else:
                # Before ldr r2,[r4,#0xb8] in retail constructor 0x72f40.
                pc = reg('pc')
                assert rd(pc) == 0xe59420b8, 'unexpected CRO base/instruction'
                client = reg('r4')
                party = rd(client+0xb8)
                count = rd(party+0x18,1)
                print('MAISON CLIENT id=%u thinker=%u client=%#x party=%#x count=%u setup=%#x' %
                      (rd(client+0x90,1),rd(client+0x91,1),client,party,count,rd(rd(client)+0x10)))
                if count == 0:
                    print('MAISON EMPTY: stopped before retail null dereference; no memory modified')
                    gdb.execute('info registers')
                    return True
        except Exception as exc:
            print('MAISON TRACE ERROR', self.kind, str(exc))
            return True
        return False

MaisonTrace(0x1e33dc, 'start')
MaisonTrace(0x1e3d2c, 'player')
MaisonTrace(0x1e3ddc, 'tail')
MaisonTrace(0x76636c, 'client')
end
