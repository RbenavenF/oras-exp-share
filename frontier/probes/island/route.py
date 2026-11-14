#!/usr/bin/env python3
"""F11 lab: walk trace paths to all eight cells, reading coordinates; never writes RAM.

Run in the SAME live shell/namespace as boot.sh, after ferry arrival. No buildings exist here.
"""
from collections import deque
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier/probes/package'))
import circuit as c

spec = importlib.util.spec_from_file_location('prototype', Path(__file__).with_name('build.py'))
prototype = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prototype)
ROWS = prototype.grids()


def path(start, cell):
    queue = deque([start]); prev = {start: None}
    while queue:
        at = queue.popleft()
        if (at[0]//40, at[1]//40) == cell:
            steps = []
            while at is not None:
                steps.append(at); at = prev[at]
            return steps[::-1]
        x,y = at
        for nx,ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if not (0 <= nx < 160 and 0 <= ny < 80) or (nx,ny) in prev:
                continue
            if ROWS[ny][nx] not in prototype.L.WALKABLE:
                continue
            delta = abs(int(ROWS[80+ny][nx])-int(ROWS[80+y][x]))
            if delta and not (delta == 1 and '=' in (ROWS[ny][nx],ROWS[y][x]) and nx == x):
                continue
            prev[nx,ny] = at; queue.append((nx,ny))
    raise RuntimeError(f'No trace path from {start} to cell {cell}')


def corners(steps):
    for i in range(1,len(steps)):
        if i==len(steps)-1 or (steps[i][0]-steps[i-1][0],steps[i][1]-steps[i-1][1]) != (steps[i+1][0]-steps[i][0],steps[i+1][1]-steps[i][1]):
            yield steps[i]


def main():
    for cell in ((1,1),(1,0),(0,0),(2,0),(3,0),(3,1),(2,1)):
        start = c.pos()
        steps = path(start,cell)
        print('PLAN',start,'->',cell,'steps',len(steps)-1,flush=True)
        for point in corners(steps):
            c.walk(point)
            print('AT',c.pos(),flush=True)
        c.shot('f11_cell_%s_%s'%cell)
        print('CELL',cell,'at',c.pos(),flush=True)


if __name__ == '__main__':
    main()
