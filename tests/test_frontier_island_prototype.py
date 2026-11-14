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
            ox, oy = L.OFFSET
            if ox <= x < ox + L.W and oy <= y < oy + L.H:
                ex, ey = x-ox, y-oy
                if ex == 26 and 61 <= ey <= 65:
                    assert c == ('=' if ey == 65 else ':') and h == '2'
                else:
                    assert (c, h) == (L.GRID[ey][ex], L.HEIGHT[ey][ex])
            else:
                assert (c, h) == ('~', '0')


def test_ferry_lands_on_dry_walkable_pier_in_southwest_cell():
    x, y = L.FERRY[0]+L.OFFSET[0], L.FERRY[1]+L.OFFSET[1]
    rows = prototype.grids()
    assert (x//40,y//40) == (0,1)
    assert rows[y][x] == 'm' and rows[80+y][x] == '1'


def test_reception_passage_connects_ferry_to_all_eight_cells_at_walkable_heights():
    route_spec = importlib.util.spec_from_file_location('f11_route', ROOT / 'frontier/probes/island/route.py')
    route = importlib.util.module_from_spec(route_spec)
    route_spec.loader.exec_module(route)
    start = (L.FERRY[0]+L.OFFSET[0], L.FERRY[1]+L.OFFSET[1])
    for cy in range(2):
        for cx in range(4):
            steps = route.path(start, (cx,cy))
            assert steps[0] == start
            assert (steps[-1][0]//40,steps[-1][1]//40) == (cx,cy)


def test_trial_export_replaces_stale_area_and_geometry_as_well_as_zone_and_matrix(tmp_path, monkeypatch):
    import hashlib
    import json
    monkeypatch.setattr(prototype, 'OUT', tmp_path)
    paths = ('a/0/1/3', 'a/0/1/4', 'a/0/3/9', 'a/0/4/0')
    for rel in paths:
        src, dst = tmp_path/'game'/rel, tmp_path/'mod/romfs'/rel
        src.parent.mkdir(parents=True, exist_ok=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(('new '+rel).encode())
        dst.write_bytes(b'stale archive')
    prototype.export_mod()
    prototype.manifest()
    hashes = json.loads((tmp_path/'hashes.json').read_text())
    for rel in paths:
        expected = ('new '+rel).encode()
        assert (tmp_path/'mod/romfs'/rel).read_bytes() == expected
        assert hashes['romfs/'+rel] == hashlib.sha256(expected).hexdigest()
