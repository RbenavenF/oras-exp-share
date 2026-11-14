#!/usr/bin/env python3
"""F11-ISLA-TRAZADO laboratory only: drives the 8-cell prototype in Azahar (frontier/probes/island/boot.sh first).
Useful from work/f11/saves/checkpoint_harbor.sav (copy of work/frontier/pkg/saves/checkpoint_harbor.sav, Lilycove
harbor, no pass yet): «drive.py NAME ferry sailor» gets the pass from the sailor and takes the ferry.
Inputs only, never writes RAM; the position is read from RAM by gdb (frontier/probes/package/circuit.py pos()).

    drive.py NAME ferry [sailor] the Lilycove sailor's pass (with «sailor») and the ferry to «Isla del Frente»
    drive.py NAME pos            prints the tile
    drive.py NAME walk X,Y ...   frontier/probes/pyramid/walk_to.py to each tile, a screenshot at each
    drive.py NAME route X,Y ... follows island_build.route around the island's obstacles
    drive.py NAME shot LABEL     screenshot to work/f11/proto/NAME/LABEL.png
    drive.py NAME keys K ...     presses keys (azahar_lab key names), 1.2 s apart
Every step is logged to work/f11/proto/NAME/walk.log with the tile.
"""
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier/probes/package'))
import circuit as c  # noqa: E402


def main():
    name, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    out = ROOT / 'work/f11/proto' / name
    if not name.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Simple evidence name required')
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'walk.log'

    def note(text):
        line = f'{time.strftime("%H:%M:%S")} {text}'
        print(line, flush=True)
        with log.open('a') as f:
            f.write(line + '\n')

    def shot(label):
        c.run('python', 'scripts/azahar_lab.py', 'screenshot')
        shutil.copyfile(ROOT / 'work/azahar-lab/screen.png', out / f'{label}.png')

    if cmd == 'pos':
        note(f'at {c.pos()}')
    elif cmd == 'shot':
        shot(args[0])
        note(f'shot {args[0]} at {c.pos()}')
    elif cmd == 'keys':
        c.keys(*args)
        note(f'keys {args} -> {c.pos()}')
    elif cmd in ('walk', 'route'):
        for xy in args:
            x, y = map(int, xy.split(','))
            try:
                if cmd == 'route':
                    steps = c.island_build.route(c.pos(), (x, y))
                    c.walk(*c.island_build.corners(steps))
                else:
                    c.walk((x, y))
                note(f'walk {x},{y} -> {c.pos()}')
            except RuntimeError as e:
                note(f'walk {x},{y} FAILED at {c.pos()}: {str(e)[-200:]}')
                shot(f'stuck_{x}_{y}')
                raise SystemExit(1)
            shot(f'at_{x}_{y}')
    elif cmd == 'ferry':
        note(f'harbor at {c.pos()}')
        if args[:1] == ['sailor']:              # checkpoint_harbor.sav has no pass yet: the sailor (circuit.py)
            c.walk((28, 24))                   # the sailor is NPC uid 2 at (29,24) (Probe entities 317)
            c.keys('h', 'a', pause=2.5)
            c.keys('a', 'a', 'a', pause=2.5)
            shot('sailor_pass')
            c.run('python', 'frontier/probes/package/to_field.py', '--max', '12')
            note(f'sailor: pass given, at {c.pos()}')
        c.walk((c.pos()[0], 26), (19, 26), (19, 25))   # row 26 first (row 24 is fenced); the ferry clerk is at (18,25) (circuit.py)
        c.keys('f', 'a', pause=2.5)
        c.keys('a', 'a', pause=2.5)
        c.keys('a', pause=2.5)
        shot('ferry_menu')
        c.keys('g', 'g', hold='0.06', pause=0.8)
        c.keys('a', pause=2.5)
        c.keys('a', pause=2.5)
        shot('ferry_yesno')
        c.keys('a', pause=15)
        c.run('python', 'frontier/probes/package/to_field.py', '--max', '12')
        shot('arrival')
        note(f'ferry: arrived at {c.pos()}')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
