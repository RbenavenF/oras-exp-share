"""Checks a Palace C GDB log (c2-probe.gdb): each FILTER's group against Emerald's table, and that the next move of
client 0 is in the kept set and of the drawn group (unless the group had no usable move)."""
import re, sys
sys.path.insert(0, 'frontier')
import palace_ai
groups = palace_ai.move_groups()
lines = open(sys.argv[1]).read().splitlines()
pending, n, bad, empty, cols = None, 0, 0, 0, {'high': 0, 'low': 0}
for line in lines:
    m = re.match(r'PALACE FILTER nature=(\d+) pct=(\d+) hp=(\d+)/(\d+) col=(\w+) group=(\d) moves=\[([\d, ]+)\] kept=\[([\d, ]+)\]', line)
    if m:
        nature, pct, hp, mx, col, group = int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5], int(m[6])
        moves = [int(x) for x in m[7].split(',')]; kept = [int(x) for x in m[8].split(',')]
        low = hp <= mx // 2
        odds = palace_ai.NATURE_ODDS[nature][2 if low else 0:][:2]
        want = 0 if pct < odds[0] else 1 if pct < odds[1] else 2
        assert (col == 'low') == low and group == want, line
        pending = (moves, kept, group); cols[col] += 1
        continue
    m = re.match(r'PALACE MOVE client=0 thinker=0 slot=(\d) move=(\d+)', line)
    if m and pending:
        moves, kept, group = pending; slot, move = int(m[1]), int(m[2])
        in_group = [k for k in range(4) if kept[k] and groups[moves[k]] == group]
        ok = kept[slot] == 1 and moves[slot] == move and (groups[move] == group or not in_group)
        n += 1; bad += not ok; empty += not in_group
        if not ok: print('MISMATCH', pending, line)
        pending = None
print(f'{n} decisions of client 0 checked, {bad} mismatches, {empty} with an empty drawn group (other groups kept); '
      f'columns {cols}')
