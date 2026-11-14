#!/usr/bin/env python3
"""F11-ISLA-CONSTRUCCION lab only: walk the built island (frontier/island_build.py) from wherever the player stands to
each facility's doorstep, enter, check the interior, walk out and check the player is back on that doorstep; then
optionally back to the pier. Routes come from island_build.route over island_rows (the same grid the build paints).
Boot first: python frontier/probes/island/lab_mod.py; F11_OUT=work/f11/build bash frontier/probes/island/boot.sh SAVE.
Inputs only, never writes RAM; positions are read from RAM by gdb (circuit.pos). Log and screenshots in
work/f11/proto/NAME/ (doors.log, <facility>_in.png, <facility>_out.png).

    doors.py NAME [FACILITY ...] [--pier]      (default: all seven, west to east)
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'frontier/probes/package'), str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import circuit as c  # noqa: E402
import island  # noqa: E402
import island_build as ib  # noqa: E402

ORDER = ['Factory', 'Dome', 'Pike', 'Tower', 'Pyramid', 'Arena', 'Palace']
# Inside each interior: (tile in front of the exit, exit tile), as frontier/probes/package/circuit.py leave()
EXITS = {'Dome': ((16, 26), (16, 30))}
MAISON_EXIT = ((20, 25), (20, 31))
ROWS = ib.island_rows()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('name')
    p.add_argument('facilities', nargs='*', default=ORDER)
    p.add_argument('--pier', action='store_true', help='end on the pier beside the ferry clerk')
    a = p.parse_args()
    out = ROOT / 'work/f11/proto' / a.name
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'doors.log'

    def note(text):
        line = f'{time.strftime("%H:%M:%S")} {text}'
        print(line, flush=True)
        with log.open('a') as f:
            f.write(line + '\n')

    def shot(label):
        c.run('python', 'scripts/azahar_lab.py', 'screenshot')
        shutil.copyfile(ROOT / 'work/azahar-lab/screen.png', out / f'{label}.png')

    def go(goal):
        start = c.pos()
        steps = ib.route(start, goal, ROWS)
        note(f'walk {start} -> {goal}: {len(steps) - 1} steps, cells '
             f'{sorted({(x // 40, y // 40) for x, y in steps})}')
        for point in ib.corners(steps):
            c.walk(point)
        at = c.pos()
        if at != goal:
            raise SystemExit(f'not at {goal}: {at}')

    failed = []
    for facility in a.facilities:
        _, x, y = ib.FACILITIES[facility]
        go((x, y + 1))
        c.keys('t', hold='0.3', pause=5)
        c.run('python', 'frontier/probes/package/to_field.py', '--max', '6')
        inside = c.pos()
        shot(f'{facility.lower()}_in')
        note(f'{facility}: door ({x},{y}) -> inside at {inside}')
        approach, exit_tile = EXITS.get(facility, MAISON_EXIT)
        c.walk(approach, exit_tile)
        c.keys('g', hold='0.3', pause=6)
        c.run('python', 'frontier/probes/package/to_field.py', '--max', '6')
        back = c.pos()
        shot(f'{facility.lower()}_out')
        ok = back == (x, y + 1)
        note(f'{facility}: back at {back} ({"its doorstep" if ok else "NOT its doorstep " + str((x, y + 1))})')
        if not ok:
            failed.append(facility)
    if a.pier:
        go((island.ARRIVAL[1], island.ARRIVAL[3]))
        shot('pier')
        note(f'pier at {c.pos()}')
    note('DOORS ' + ('ok' if not failed else 'FAILED ' + ','.join(failed)))


if __name__ == '__main__':
    main()
