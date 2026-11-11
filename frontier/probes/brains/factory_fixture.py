#!/usr/bin/env python3
"""Create a Noland lab copy from a correctly paused Factory save (never inputs).

Usage: factory_fixture.py SOURCE --sha256 HASH --streak 20|41 --output work/NAME.sav
The source must already be paused in zone 213, not a challenge saved mid-battle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('faraway', 'frontier')]
import save_event as se
import data as fd
import factory_brain
import patch
import brains


def create(source, streak, seed=12345):
    assert se.place(source)['zone'] == 213, 'Source must be at the Factory reception'
    assert se.work(source, patch.WORK_IV), 'Source must have a paused Factory challenge'
    offers, rival = factory_brain.team(fd.check_tiers(fd.load()), seed, streak)
    works = {w: 0 for w in patch.ACTIVE_WORK.values()}
    works.update({patch.WORK_ROUTE: 0, patch.WORK_FSTREAK: streak,
                  patch.WORK_IV: 9 if streak == 20 else 21,
                  16490: seed, brains.WORK_SYMBOLS: 0 if streak == 20 else 1, brains.WORK_BRAIN: 0})
    works.update(zip(patch.WORK_SETS, offers[:3]))
    result = se.edit(source, works=works.items())
    info = dict(source_sha256=hashlib.sha256(source).hexdigest(),
                sha256=hashlib.sha256(result).hexdigest(), position=se.place(result),
                works=works, offers=offers, rival=rival)
    return result, info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--sha256', required=True)
    p.add_argument('--streak', type=int, choices=(20, 41), required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert a.output.resolve().is_relative_to(ROOT / 'work') and a.output.resolve() != a.source.resolve()
    source = a.source.read_bytes()
    assert hashlib.sha256(source).hexdigest() == a.sha256
    result, info = create(source, a.streak)
    info['source'] = str(a.source)
    with a.output.open('xb') as f:
        f.write(result)
    a.output.with_suffix('.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
