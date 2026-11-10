#!/usr/bin/env python3
"""Audit actual GDB observations from the assisted seven-floor Azahar run (§34)."""
import ast
from pathlib import Path
import re


def audit(root):
    battles = (root / 'gdb-before-reload.log').read_text() + (root / 'gdb-round.log').read_text()
    results = [(int(n), ast.literal_eval(s)) for n, s in re.findall(
        r'PYRAMID RESULT n=\d+ raw=(\d+) state=([^\n]+)', battles)]
    assert len(results) == 21 and all(n == 1 for n, _ in results)
    assert [s[16482] for _, s in results] == [n for n in range(1, 8) for _ in range(3)]
    assert [s[16686] for _, s in results] == [m for _ in range(7) for m in (0, 1, 3)]
    cleared = [(int(n), ast.literal_eval(s)) for n, s in re.findall(
        r'PYRAMID CLEARED (\d+) ([^\n]+)', (root / 'climb.log').read_text())]
    assert [n for n, _ in cleared] == list(range(1, 8))
    for n, s in cleared:
        assert (s[16481], s[16482], s[16483], s[16686], s[16438]) == (
            n, n + 1 if n < 7 else 0, n, 0, 7 if n < 7 else 0)
    return '21 victorias asistidas, tres por piso; máscaras 0/1/3; siete transiciones; final 7/0/7, ruta 0.'


if __name__ == '__main__':
    print(audit(Path('work/frontier/pyramid/v2')))
