#!/usr/bin/env python3
"""Lab-only walking to a reachable tile; read RAM coordinates, never write position."""
import argparse
import re
import subprocess
import time


def pos():
    subprocess.run(['faraway/gdbctl.sh', 'halt'], stdout=subprocess.DEVNULL, check=True)
    out = subprocess.check_output(['faraway/gdbctl.sh', 'cmd', 'x/3fw 0x8187bf4'], text=True)
    subprocess.run(['faraway/gdbctl.sh', 'run'], stdout=subprocess.DEVNULL, check=True)
    # A prompt can share the response line. Empty replies remain a lab error;
    # retry only after checking that no other driver is using the GDB FIFO.
    match = re.search(r'0x8187bf4:\s*([^\n]+)', out)
    if match is None:
        raise RuntimeError(f'No position in GDB response: {out!r}')
    x, height, y = map(float, match.group(1).split())
    return round((x - 9) / 18), round((y - 9) / 18)


def key(key):
    subprocess.run(['python', 'scripts/azahar_lab.py', 'input', 'keydown', key,
                    'sleep', '0.035', 'keyup', key], check=True)
    time.sleep(0.4)


def walk(x, y):
    for _ in range(7):
        current = pos()
        if current == (x, y):
            print('WALK at', current, flush=True)
            return
        dx, dy = x - current[0], y - current[1]
        k, n = (('h' if dx > 0 else 'f'), abs(dx)) if dx else (('g' if dy > 0 else 't'), abs(dy))
        for _ in range(n):
            key(k)
    raise RuntimeError(f'Could not walk to {(x, y)}; last {pos()} (dialogue or obstacle?)')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('x', type=int)
    p.add_argument('y', type=int)
    a = p.parse_args()
    walk(a.x, a.y)
