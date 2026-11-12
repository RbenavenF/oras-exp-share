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
        super().__init__('*%#x' % address, type=gdb.BP_HARDWARE_BREAKPOINT)
        self.kind = kind
    def stop(self):
        try:
            gdb.execute('maintenance flush register-cache', to_string=True)
            gdb.invalidate_cached_frames()
            if self.kind == 'start':
                arm.enabled = True
                if client_hook is not None:
                    client_hook.enabled = False
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
            elif self.kind == 'result':
                if client_hook is not None:
                    client_hook.enabled = False
                w = reg('r0')
                print('MAISON RESULT win=%u style=%u' % (rd(w+0x73c,1),rd(w+0x839,1)))
            else:
                # Before ldr r2,[r4,#0xb8] in retail constructor 0x72f40.
                pc = reg('pc')
                # During stop(), Azahar exposes its ARM BKPT marker. The arm
                # gate checked the original instruction before inserting it.
                assert pc == 0x76636c and rd(pc) in (0xe59420b8, 0xe1200070), \
                    'unexpected CRO instruction pc=%#x word=%#x' % (pc, rd(pc))
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

# Module loading replaces even Azahar's hardware breakpoint markers. Arm the
# CRO hook only once its constructor is called through the stable allocator.
client_hook = None
class MaisonArm(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*0x12bad4', type=gdb.BP_HARDWARE_BREAKPOINT)
        self.enabled = False
    def stop(self):
        global client_hook
        gdb.execute('maintenance flush register-cache', to_string=True)
        gdb.invalidate_cached_frames()
        try:
            if rd(0x76636c) != 0xe59420b8:
                return False   # DllField still occupies this range
        except gdb.MemoryError:
            return False       # CRO unloaded during transition
        if client_hook is None:
            client_hook = MaisonTrace(0x76636c, 'client')
        else:
            client_hook.enabled = True
        self.enabled = False
        print('MAISON ARM allocator_target=%#x instruction=%#x' % (reg('r1'), rd(0x76636c)))
        return False
arm = MaisonArm()
MaisonTrace(0x1e33dc, 'start')
MaisonTrace(0x1e3d2c, 'player')
MaisonTrace(0x1e3ddc, 'tail')
MaisonTrace(0x1e5664, 'result')
end
