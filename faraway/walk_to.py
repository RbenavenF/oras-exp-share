#!/usr/bin/env python3
"""Laboratory: walk the player to a tile with short D-pad taps, reading the position from RAM after each.

Usage: walk_to.py X Y [--face up|down|left|right] [--axis xy|yx]
Needs faraway/gdbctl.sh started. Position address: FARAWAY_POS_ADDR (default 0x8187bf4, measured).
"""
import argparse
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POS = os.environ.get('FARAWAY_POS_ADDR', '0x8187bf4')
KEY = {'up': 't', 'down': 'g', 'left': 'f', 'right': 'h'}


def gdb(*args):
    return subprocess.run([str(ROOT / 'faraway/gdbctl.sh'), *args], capture_output=True, text=True,
                          check=True, timeout=20).stdout


def position():
    try:
        gdb('halt')
        out = gdb('cmd', f'x/3fw {POS}')
    finally:
        gdb('run')
    for line in out.splitlines():
        if line.startswith('0x'):
            parts = line.split()
            return round((float(parts[1]) - 9) / 18, 2), round((float(parts[3]) - 9) / 18, 2)
    raise RuntimeError(f'No position in {out!r}')


def tap(direction, hold):
    key = KEY[direction]
    subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/azahar_lab.py'), 'input',
                    'keydown', key, 'sleep', str(hold), 'keyup', key], check=True)
    time.sleep(0.35)


def walk_to(x, y, axis='xy', hold=0.06, limit=60):
    for _ in range(limit):
        px, py = position()
        if (px, py) == (x, y):
            return px, py
        order = [('x', px, x), ('y', py, y)] if axis == 'xy' else [('y', py, y), ('x', px, x)]
        for name, now, goal in order:
            if now != goal:
                direction = ('right' if goal > now else 'left') if name == 'x' else ('down' if goal > now else 'up')
                tap(direction, hold if abs(goal - now) <= 1 else min(0.25, 0.06 * abs(goal - now)))
                break
    return position()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('x', type=float, nargs='?')
    parser.add_argument('y', type=float, nargs='?')
    parser.add_argument('--position', action='store_true', help='read the current tile without moving')
    parser.add_argument('--limit', type=int, default=60, help='maximum number of movement attempts')
    parser.add_argument('--face', choices=KEY)
    parser.add_argument('--axis', default='xy')
    args = parser.parse_args()
    if args.position:
        print('at', position())
        return
    if args.x is None or args.y is None:
        parser.error('X and Y are required unless --position is used')
    print('at', walk_to(args.x, args.y, args.axis, limit=args.limit))
    if args.face:
        tap(args.face, 0.03)
        print('facing', args.face)


if __name__ == '__main__':
    main()
