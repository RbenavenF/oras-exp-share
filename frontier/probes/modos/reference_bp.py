#!/usr/bin/env python3
"""Compare all PB rows against an existing local checkout's pinned Git object.

Does not download or change the checkout. No game data is embedded in the output.
Usage: python frontier/probes/modos/reference_bp.py /tmp/frontier-cerebros-pokeemerald
"""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import data as fd  # noqa: E402

REF = '731ad5bfd6e6f265508d0efcca0ba42f9dcf5881'
FACILITIES = ('tower', 'dome', 'palace', 'arena', 'factory', 'pike', 'pyramid')


def columns(source):
    body = source.split('static const u8 sBattlePointAwards[', 1)[1].split('};', 1)[0]
    rows = re.findall(r'\{\s*((?:\{[^{}]*\}\s*,?\s*){7})\}', body)
    if len(rows) != 30:
        raise ValueError(f'expected 30 PB rows, got {len(rows)}')
    singles = {f: [] for f in FACILITIES}
    doubles = {f: [] for f in ('tower', 'factory')}
    for row in rows:
        cells = re.findall(r'\{([^{}]*)\}', row)
        for facility, cell in zip(FACILITIES, cells):
            numbers = [int(n) for n in re.findall(r'\d+', cell)]
            singles[facility].append(numbers[0])
            if facility in doubles:
                doubles[facility].append(numbers[1])
    return singles, doubles


def verify(repo):
    source = subprocess.check_output(['git', '-C', str(repo), 'show', f'{REF}:src/frontier_util.c'], text=True)
    singles, doubles = columns(source)
    if singles != fd.FRONTIER_BP or doubles != fd.FRONTIER_BP_DOUBLES:
        raise ValueError('PB columns differ from fixed pokeemerald source')
    return {'commit': REF, 'rows': 30, 'singles': singles, 'doubles': doubles}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
