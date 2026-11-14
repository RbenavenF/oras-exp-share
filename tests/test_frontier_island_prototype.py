"""The laboratory export keeps the reference's scale/height and changes only the reception corridor."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_layout as L

spec = importlib.util.spec_from_file_location('f11_prototype', ROOT / 'frontier/probes/island/build.py')
prototype = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prototype)


def test_export_preserves_trace_and_sea_padding_except_documented_reception_passage():
    rows = prototype.grids()
    assert len(rows) == 160 and all(len(row) == 160 for row in rows)
    for y in range(80):
        for x in range(160):
            c, h = rows[y][x], rows[80+y][x]
            if 16 <= x < 144 and 4 <= y < 76:
                ex, ey = x-16, y-4
                if ex == 26 and 61 <= ey <= 65:
                    assert c == ('=' if ey == 65 else ':') and h == '2'
                else:
                    assert (c, h) == (L.GRID[ey][ex], L.HEIGHT[ey][ex])
            else:
                assert (c, h) == ('~', '0')


def test_ferry_lands_on_dry_walkable_pier_in_southwest_cell():
    x, y = L.FERRY[0]+16, L.FERRY[1]+4
    rows = prototype.grids()
    assert (x//40,y//40) == (0,1)
    assert rows[y][x] == 'm' and rows[80+y][x] == '1'


def test_reception_passage_connects_ferry_to_all_eight_cells_at_walkable_heights():
    route_spec = importlib.util.spec_from_file_location('f11_route', ROOT / 'frontier/probes/island/route.py')
    route = importlib.util.module_from_spec(route_spec)
    route_spec.loader.exec_module(route)
    start = (L.FERRY[0]+16, L.FERRY[1]+4)
    for cy in range(2):
        for cx in range(4):
            steps = route.path(start, (cx,cy))
            assert steps[0] == start
            assert (steps[-1][0]//40,steps[-1][1]//40) == (cx,cy)
