# F7-CONSOLA-MANSION: dump the client-0 constructor stack (sp..sp+0x198, as a Luma dump) at CRO 0x7336c.
# Armed at StartBattle (0x1e33dc) -> allocator 0x12bad4 once DllBattle is loaded; passive, no writes.
python
import gdb
def rd(a, n=4):
    return int.from_bytes(gdb.selected_inferior().read_memory(a, n), 'little')
def reg(n):
    return int(gdb.parse_and_eval('$' + n))
hook = None
class Client(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*0x76636c', type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        gdb.execute('maintenance flush register-cache', to_string=True)
        try:
            r4 = reg('r4')
            ok = rd(reg('pc')) in (0xe59420b8, 0xe1200070) and rd(r4 + 0x90, 1) == 0
        except Exception:
            return False
        if ok:
            sp = reg('sp')
            print('STACKDUMP sp=%#x r4=%#x regs=%s' % (sp, r4, ' '.join('%08x' % reg('r%d' % i) for i in range(13))))
            print('STACKWORDS', ' '.join('%08x' % rd(sp + 4*i) for i in range(0x198 // 4)))
        return False
class Arm(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*0x12bad4', type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        global hook
        gdb.execute('maintenance flush register-cache', to_string=True)
        try:
            if rd(0x76636c) != 0xe59420b8:
                return False
        except gdb.MemoryError:
            return False
        if hook is None:
            hook = Client()
        else:
            hook.enabled = True
        self.enabled = False
        return False
arm = Arm()
arm.enabled = False
class Start(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*0x1e33dc', type=gdb.BP_HARDWARE_BREAKPOINT)
    def stop(self):
        arm.enabled = True
        if hook is not None:
            hook.enabled = False
        return False
Start()
end
