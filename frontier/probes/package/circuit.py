#!/usr/bin/env python3
"""Lab only (F7-PAQUETE, reports/frontier.md §38): the whole alpha circuit on the EXACT package, from a save at the
Lilycove harbor with the League won (flag 2720) and the S.S. Ticket: sailor -> pass -> ferry -> island -> the seven
facilities, one battle each (the Pike: one room, then its battle) -> back to the plaza after each. On the island
(F11-ISLA-CONSTRUCCION) the walks to each door are computed over the island's own grid (island_build.route), so they
follow the doors' tiles in island_build.FACILITIES. Needs the lab
booted with frontier/probes/package/boot.sh and the passive probe (probe.py) sourced in GDB. Screenshots go to
work/frontier/pkg/shots/c_*.png and steps to work/frontier/pkg/circuit.log. Inputs only; never writes RAM.

Usage: circuit.py [--from STEP]   (STEP: sailor, ferry, factory, tower, arena, palace, pike, dome, pyramid)
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / 'work/frontier/pkg/circuit.log'
GDB = ROOT / 'work/faraway/gdb/out.log'
SHOTS = ROOT / 'work/frontier/pkg/shots'
HERE = 'frontier/probes/package'
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import island_build  # noqa: E402  (F11 island: door tiles and walks over the painted grid)


def log(text):
    line = f'{time.strftime("%H:%M:%S")} {text}'
    print(line, flush=True)
    with LOG.open('a') as f:
        f.write(line + '\n')


def run(*cmd, check=True, timeout=900):
    r = subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f'{cmd}: {r.stdout[-500:]} {r.stderr[-500:]}')
    return r.stdout


def keys(*ks, hold='0.08', pause=1.2):
    for k in ks:
        run('python', 'scripts/azahar_lab.py', 'input', 'keydown', k, 'sleep', hold, 'keyup', k)
        time.sleep(pause)


def shot(name):
    run('python', 'scripts/azahar_lab.py', 'screenshot')
    shutil.copyfile(ROOT / 'work/azahar-lab/screen.png', SHOTS / f'c_{name}.png')


def pos():
    run('faraway/gdbctl.sh', 'halt')
    out = run('faraway/gdbctl.sh', 'cmd', 'x/3fw 0x8187bf4')
    run('faraway/gdbctl.sh', 'run')
    m = re.findall(r'0x8187bf4:\s*([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)', out)
    x, _, y = map(float, m[-1])
    return round((x - 9) / 18), round((y - 9) / 18)


def walk(*points):
    for x, y in points:
        out = run('python', 'frontier/probes/pyramid/walk_to.py', str(x), str(y), timeout=200)
        if 'WALK at' not in out:
            raise RuntimeError(f'walk to {(x, y)}: {out}')


def to_door(facility):
    """Walk (island_build.route over the island's grid) to the doorstep of a facility's door."""
    _, x, y = island_build.FACILITIES[facility]
    walk(*island_build.corners(island_build.route(pos(), (x, y + 1))))


def enter(name):
    keys('t', hold='0.3', pause=5)
    p = pos()
    log(f'{name}: inside at {p}')
    shot(f'{name}_in')
    return p


def leave(name, inside_exit=(20, 31), approach=(20, 25)):
    run('python', f'{HERE}/to_field.py', '--max', '15')
    walk(approach, inside_exit)
    keys('g', hold='0.3', pause=6)
    p = pos()
    log(f'{name}: back on the plaza at {p}')
    shot(f'{name}_out')
    return p


def last(pattern):
    return [l for l in GDB.read_text(errors='replace').splitlines() if pattern in l][-1]


def battle(name, route):
    out = run(f'{HERE}/until.sh', 'FRONT START', check=False, timeout=600)
    if 'after' not in out:
        raise RuntimeError(f'{name}: no battle start: {out}')
    start = last('FRONT START')
    if f'16438={route} ' not in start:
        raise RuntimeError(f'{name}: route is not {route}: {start}')
    log(f'{name}: {start}')
    time.sleep(6)
    shot(f'{name}_battle')
    for n in range(6):                  # a win continues the challenge (A = continue): play on until a loss
        out = run('python', f'{HERE}/battle.py', '--max', '150', timeout=900)
        log(f'{name}: {out.strip().splitlines()[-1]}')
        if 'raw=1' not in out.splitlines()[-1]:
            return
        shot(f'{name}_win{n + 1}')
        run(f'{HERE}/until.sh', 'FRONT START', check=False, timeout=600)


def reception(menu_presses, factory=False):
    """At the right receptionist (23,25): talk, then the facility's own flow up to the battle."""
    keys('t', hold='0.04', pause=1)
    keys('a', 'a', 'a', pause=2.5)
    if factory:
        keys('g', 'g', 'g', hold='0.06', pause=0.6)
        keys('a', pause=3)
        return
    keys(*['a'] * menu_presses, pause=3)
    keys('a', 'h', 'a', 'a', 'g', 'a', 'a', pause=2)   # Torchic, Beldum, Cascoon; then «Vale» with A


def maison(name, route, menu_presses=9, factory=False):
    walk((20, 25), (23, 25))
    reception(menu_presses, factory)
    battle(name, route)


STEPS = ['sailor', 'ferry', 'factory', 'factory-out', 'tower', 'arena', 'palace', 'pike', 'dome', 'pyramid']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--from', dest='first', default='sailor', choices=STEPS)
    p.add_argument('--inside', action='store_true', help='already inside the first step\'s building, at its entrance')
    a = p.parse_args()
    skip = {a.first} if a.inside else set()

    def go(step):
        if step not in skip:
            to_door(step.capitalize())
            enter(step)
    todo = STEPS[STEPS.index(a.first):]
    SHOTS.mkdir(parents=True, exist_ok=True)
    log(f'circuit from {a.first}')
    if 'sailor' in todo:
        log(f'harbor: at {pos()}')
        keys('h', pause=1)
        keys('t', 'a', pause=2.5)
        shot('sailor_1')
        keys('a', 'a', 'a', pause=2.5)
        shot('sailor_pass')
        run('python', f'{HERE}/to_field.py', '--max', '12')
        log('sailor: pass given (shots c_sailor_*)')
    if 'ferry' in todo:
        walk((19, 26), (19, 25))                        # the ferry clerk is at (18,25)
        keys('f', 'a', pause=2.5)
        keys('a', 'a', pause=2.5)
        keys('a', pause=2.5)
        shot('ferry_menu')
        keys('g', 'g', hold='0.06', pause=0.8)
        keys('a', pause=2.5)
        keys('a', pause=2.5)
        shot('ferry_yesno')
        keys('a', pause=15)
        run('python', f'{HERE}/to_field.py', '--max', '12')
        log(f'ferry: arrived at {pos()}')
        shot('island_pier')
    if 'factory' in todo:
        go('factory')
        maison('factory', 1, factory=True)
    if 'factory' in todo or a.first == 'factory-out':
        leave('factory')
    if 'tower' in todo:
        go('tower')
        maison('tower', 2)
        leave('tower')
    if 'arena' in todo:
        go('arena')
        maison('arena', 4)
        leave('arena')
    if 'palace' in todo:
        go('palace')
        maison('palace', 3)
        leave('palace')
    if 'pike' in todo:
        go('pike')
        maison('pike', 6)
        leave('pike')
    if 'dome' in todo:
        go('dome')
        walk((16, 26), (23, 26))
        reception(9)
        battle('dome', 5)
        leave('dome', inside_exit=(16, 30), approach=(16, 26))
    if 'pyramid' in todo:
        go('pyramid')
        walk((20, 25), (23, 25))
        reception(8)
        out = run('python', f'{HERE}/to_field.py', '--max', '20')
        log(f'pyramid: floor at {pos()} ({out.strip()})')
        shot('pyramid_floor')
        try:
            walk((12, 8))
        except RuntimeError:
            pass                                        # stops under the first trainer
        keys('t', hold='0.04', pause=1)
        battle('pyramid', 7)
        run('python', f'{HERE}/to_field.py', '--max', '15')
        log(f'pyramid: back in the lobby at {pos()}')
        leave('pyramid')
    log('circuit done')


if __name__ == '__main__':
    main()
