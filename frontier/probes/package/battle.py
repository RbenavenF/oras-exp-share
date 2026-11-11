#!/usr/bin/env python3
"""Lab only: play battles by pressing A (Fight -> first move, texts) until the passive probe logs one more
`FRONT RESULT` (or PATTERN). When a fainted Pokémon's page is on the touch screen (its big green panel), it goes back
to the party list and taps the next party panel, then A (Switch). Usage: battle.py [--pattern P] [--max N]"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
from lab_factory import Png  # noqa: E402

LOG = ROOT / 'work/faraway/gdb/out.log'
PANELS = [(680, 500), (520, 555), (680, 555), (520, 610), (680, 610), (520, 500)]


def lab(*args):
    subprocess.run(['python', 'scripts/azahar_lab.py', 'input', *args], cwd=ROOT, check=True, capture_output=True)


def key(k, pause=2.0):
    lab('keydown', k, 'sleep', '0.08', 'keyup', k)
    time.sleep(pause)


def tap(x, y):
    lab('mousemove', str(x), str(y), 'mousedown', '1', 'sleep', '0.2', 'mouseup', '1')
    time.sleep(1.5)


def pixel(img, x, y):
    r = img.row(y)
    return tuple(r[x * img.bpp:x * img.bpp + 3])


def detail_page():
    subprocess.run(['python', 'scripts/azahar_lab.py', 'screenshot'], cwd=ROOT, check=True, capture_output=True)
    img = Png(str(ROOT / 'work/azahar-lab/screen.png'))
    r, g, b = pixel(img, 500, 600)
    return g > 170 and r < 80 and b < 120 and pixel(img, 470, 560) == (185, 185, 185)


def count(pattern):
    return LOG.read_text(errors='replace').count(pattern)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pattern', default='FRONT RESULT')
    p.add_argument('--max', type=int, default=200)
    a = p.parse_args()
    n0, nxt = count(a.pattern), 0
    for i in range(a.max):
        if count(a.pattern) > n0:
            print(f'after {i} presses:', [l for l in LOG.read_text(errors='replace').splitlines()
                                          if a.pattern in l][-1])
            return
        key('a')
        if i % 8 == 7:
            tap(680, 535)                     # second move (the first may have no PP left); else «Fight»
        if i % 3 == 2 and detail_page():
            key('a', 2.5)                     # Switch, if this one can fight
            tries = 0
            while detail_page() and tries < len(PANELS):
                key('s', 1.2)                 # close the «no strength left» text
                key('s', 1.5)                 # back to the list
                tap(*PANELS[nxt % len(PANELS)])
                nxt += 1
                tries += 1
                key('a', 2.5)
            print(f'switch handled at press {i} ({tries} taps)', flush=True)
    sys.exit(f'no {a.pattern} after {a.max} presses')


if __name__ == '__main__':
    main()
