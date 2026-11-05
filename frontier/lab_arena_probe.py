#!/usr/bin/env python3
"""Generate a GDB lab probe using the current linked Arena symbols.

normal is read-only; win/loss/tie replace the enemy's copied moves with Splash
and control HP at judgement. Only marked Arena setups are modified. These are
controlled engine tests, not an unassisted playthrough or part of the patch.
"""
import argparse
from pathlib import Path

import arena_engine as ae
import patch

ROOT = Path(__file__).resolve().parents[1]


def script(mode):
    _, symbols = patch.assemble()
    prelude = '''set pagination off
set language c
python
import gdb
ar_mode = MODE
ar_base = globals().get('ar_base', 0)
ar_player = globals().get('ar_player', 0)
CLIENT_DELTA = 0xd98
ar_enemy = globals().get('ar_enemy', 0)
def ar_reg(name):
    return int(gdb.parse_and_eval('$' + name))
def ar_read(addr, size=4):
    return int.from_bytes(gdb.selected_inferior().read_memory(addr, size), 'little')
def ar_write(addr, value, size=2):
    gdb.selected_inferior().write_memory(addr, value.to_bytes(size, 'little'))
def ar_context(server):
    setup = ar_read(ar_read(server + 4) + 0x10)
    save = ar_read(ar_read(setup + 0x7c))
    return setup, save
def ar_harmless(mon):
    # The AI picks its move from the CLIENT copy of the enemy (measured 2026-11-05: server
    # 0x8207168, client 0x82063d0, same words +8/+0xc; Garchomp 0x8206f24/0x820618c). Write
    # Splash to both copies; the client copy is only touched if its identity words match.
    copies = [mon]
    client = mon - CLIENT_DELTA
    if all(ar_read(client + k) == ar_read(mon + k) for k in (8, 0xc)):
        copies.append(client)
    for copy in copies:
        for slot in range(4):
            for offset in (0x116, 0x11c):
                ar_write(copy + offset + slot * 14, 150)
                ar_write(copy + offset + slot * 14 + 2, 40, 1)
    if len(copies) == 1:
        print('ARENA WARN client copy not found for %x' % mon)
def ar_enter():
    global ar_base, ar_player, ar_enemy
    mon, server = ar_reg('r5'), ar_reg('r4')
    ar_base = ar_reg('lr') - 0x724c8
    setup, save = ar_context(server)
    ident, hp = ar_read(mon + 0x19, 1), ar_read(mon + 0x10, 2)
    if ident < 12:
        ar_player = mon
    else:
        ar_enemy = mon
        if ar_mode != 'normal' and ar_read(setup + 0xa8) & 0x80000000:
            ar_harmless(mon)
    print('ARENA ENTRY id=%u mon=%x server=%x cro=%x hp=%u flag=%x' %
          (ident, mon, server, ar_base, hp, ar_read(setup + 0xa8)))
def ar_end():
    server = ar_reg('r6')
    setup, save = ar_context(server)
    ordered = ar_read(server + 0x1254)
    count = ar_read(ordered + 0x6e, 1)
    if count != 2:
        print('ARENA END active count=%u flag=%x' % (count, ar_read(setup + 0xa8)))
        return
    mons = [ar_read(ordered), ar_read(ordered + 4)]
    mons.sort(key=lambda m: ar_read(m + 0x19, 1))
    ages = [ar_read(m + 0x158, 2) for m in mons]
    initial = [ar_read(save + 0x13144 + 2 * (w - 0x4000), 2) for w in (16693,16694)]
    marked = bool(ar_read(setup + 0xa8) & 0x80000000)
    # Entry processing can reload moves AFTER the snapshot hook. Reapply at
    # the turn boundary so the following AI command sees the harmless moves.
    if marked and ar_mode != 'normal':
        ar_harmless(mons[1])
    if marked and all(ar_read(m+0x10,2) for m in mons) and all(initial):
        if ar_mode in ('win', 'loss', 'tie'):
            hp = list(initial)
            if min(ages) >= 3:
                if ar_mode == 'win': hp[1] = 1
                if ar_mode == 'loss': hp[0] = 1
            for mon, value in zip(mons, hp): ar_write(mon + 0x10, value)
    print('ARENA END global=%u ages=%s hp=%s initial=%s flag=%x mode=%s' %
          (ar_read(server+0x14), ages, [ar_read(m+0x10,2) for m in mons],
           initial, ar_read(setup+0xa8), ar_mode))
def ar_ko():
    if ar_base and ar_reg('lr') == ar_base + 0x1dc44:
        print('ARENA KO mon=%x hpP=%u hpE=%u lr=%x' %
              (ar_reg('r4'), ar_read(ar_player+0x10,2), ar_read(ar_enemy+0x10,2), ar_reg('lr')))
def ar_start():
    work = ar_reg('r4')
    print('ARENA START work=%x flag=%x style=%u' %
          (work, ar_read(work+0x6c8), ar_read(work+0x621,1)))
def ar_judge():
    print('ARENA JUDGE args=%s' % [ar_reg('r%u' % i) for i in range(4)])
def ar_result():
    work = ar_reg('r0')
    print('ARENA RESULT raw=%u work=%x' % (ar_read(work+0x73c,1), work))
end
'''.replace('MODE', repr(mode))
    hooks = [(ae.START + 4, 'ar_start'), (symbols['arena_enter'], 'ar_enter'),
             (symbols['arena_turn_end'], 'ar_end'), (symbols['arena_judge'], 'ar_judge'),
             (0x3B48FC, 'ar_ko'), (symbols['pike_iswin'], 'ar_result')]
    return prelude + ''.join(f'break *{address:#x}\ncommands\nsilent\npython {name}()\ncontinue\nend\n'
                             for address, name in hooks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--mode', choices=['normal', 'win', 'loss', 'tie'], default='normal')
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/')
    args.out.write_text(script(args.mode))
    print(args.out)


if __name__ == '__main__':
    main()
