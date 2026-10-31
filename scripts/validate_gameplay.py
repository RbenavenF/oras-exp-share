#!/usr/bin/env python3
"""Recheck saved evidence from the four manually driven Azahar battles.

This reads the actual before/after saves; it does not drive or simulate battles.
The local saves and screenshots remain in ignored work/ directories.
"""
import json
from pathlib import Path

from build_patch import patched_assets
from formats import sha256
from save_fixture import inspect

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'work/test-saves/results'


def main():
    overlay = ROOT / 'work/azahar-lab/data/azahar-emu/load/mods/000400000011C400'
    _, patched = patched_assets()
    for relative, data in patched.items():
        if (overlay / relative).read_bytes() != data:
            raise ValueError(f'Tested overlay differs from generator: {relative}')
    cases = [
        ('reserve', ROOT / 'work/test-saves/route101-v2/reserve-main',
         [0, 216, 0], [24, 12, 0], [[1, 0, 0, 0, 0, 0]] * 2 + [[0] * 6], 'Wurmple', None),
        ('participant', RESULTS / 'participant-before-main',
         [216, 0, 0], [16, 0, 0], [[1, 0, 0, 0, 0, 0]] + [[0] * 6] * 2, 'Wurmple', 2),
        ('none', RESULTS / 'none-before-main',
         [0, 0, 0], [16, 0, 0], [[1, 0, 0, 0, 0, 0]] + [[0] * 6] * 2, 'Wurmple', 2),
        ('fainted', RESULTS / 'fainted-before-main',
         [0, 216, 0], [16, 0, 0], [[0, 1, 0, 0, 0, 0]] + [[0] * 6] * 2, 'Poochyena', 2),
    ]
    report = {
        'date': '2026-10-31', 'emulator': 'Azahar 2126.2',
        'method': 'Four actual single wild battles driven through the GUI; compare decrypted saved party data with valid save and PK6 checksums.',
        'title_id': '000400000011C400', 'base': 'Omega Ruby without update + Repolished 1.7.6',
        'tested_changed_assets': {relative: sha256(overlay / relative) for relative in patched},
        'cases': [],
        'menu_observations': ['Held item removed to Items pocket', 'GIVE action visible in Items pocket',
                              'Item equipped to participant through bag UI and persisted in save'],
        'limitations': ['Artificial three-Pokemon teams cloned from a new laboratory starter',
                        'First Wurmple level was not captured; comparison uses actual 24/12/0 gains',
                        'Egg, level-100 and EV-cap cases tested only through ARM fixtures',
                        'No doubles, hordes, multiplayer or console test',
                        'Original item description and story delivery unchanged',
                        'Software renderer showed graphical artifacts on models; gameplay continued'],
    }
    for name, source, items, expected_exp, expected_ev, foe, level in cases:
        after_path = RESULTS / f'{name}-after-main'
        before, after = inspect(source.read_bytes()), inspect(after_path.read_bytes())
        a, b = before['party'], after['party']
        assert len(a) == len(b) == 3, name
        assert [m['item'] for m in a] == [m['item'] for m in b] == items, name
        assert all(x['species'] == y['species'] == 255 for x, y in zip(a, b)), name
        exp = [y['exp'] - x['exp'] for x, y in zip(a, b)]
        ev = [[v - u for u, v in zip(x['ev'], y['ev'])] for x, y in zip(a, b)]
        assert exp == expected_exp, (name, exp)
        assert ev == expected_ev, (name, ev)
        if name == 'fainted':
            assert a[1]['hp'] == b[1]['hp'] == 0
        report['cases'].append(dict(name=name, opponent=foe, opponent_level_observed=level,
            before_path=str(source.relative_to(ROOT)), after_path=str(after_path.relative_to(ROOT)),
            before_sha256=before['sha256'], after_sha256=after['sha256'],
            held_items=items, exp_before=[m['exp'] for m in a], exp_after=[m['exp'] for m in b],
            exp_delta=exp, ev_delta=ev, hp_before=[m['hp'] for m in a], hp_after=[m['hp'] for m in b],
            levels_before=[m['level'] for m in a], levels_after=[m['level'] for m in b], passed=True))
        print(f'PASS Azahar {name}: EXP {exp}, EV {ev}')
    participant, none = report['cases'][1:3]
    assert participant['exp_delta'] == none['exp_delta']
    assert participant['ev_delta'] == none['ev_delta']
    report['participant_matches_no_item_control'] = True
    (ROOT / 'reports/gameplay-validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
