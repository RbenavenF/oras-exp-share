"""F11 landscape trial: decoration never consumes movement or future building space."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('landscape_trial', ROOT / 'frontier/probes/island/landscape.py')
landscape = importlib.util.module_from_spec(spec)
spec.loader.exec_module(landscape)


def test_scenery_stays_in_matching_blocked_tiles_and_one_cell():
    rows = landscape.island_build.island_rows()
    original = landscape.island_layout.GRID
    occupied = set()
    pieces = landscape.placements(40, 140, 40)
    assert pieces
    categories = set()
    for line in pieces:
        name, x, y, *mode = line.split('|')
        x, y = int(x), int(y)
        w, h = landscape.catalog_size(name)
        if mode == ['90']:
            w, h = h, w
        elif mode == ['half']:
            w, h = (w+1)//2, (h+1)//2
        assert x//40 == (x+w-1)//40 and y//40 == (y+h-1)//40
        allowed = 'f' if 'fence' in name or 'flag' in name else 'p' if 'flower' in name else 'T' if 'tree' in name else 'Tp'
        categories.add(allowed)
        footprint = {(xx, yy) for yy in range(y, y+h) for xx in range(x, x+w)}
        assert not footprint & occupied
        occupied.update(footprint)
        for xx, yy in footprint:
            assert rows[yy][xx] in allowed
            assert rows[80+yy][xx] == rows[80+y][x]
    assert categories == {'T', 'Tp', 'p', 'f'}
    assert landscape.island_layout.GRID == original


def test_integration_refuses_builder_drift():
    source = (ROOT / 'faraway/java/ctrmap/tests/FrontierIsland.java').read_text()
    changed = landscape.trial_source(source)
    assert changed != source
    with pytest.raises(ValueError, match='re-audit'):
        landscape.trial_source(changed)


def test_gr_parser_rejects_another_container():
    with pytest.raises(AssertionError):
        landscape.gr_files(b'ZO' + bytes(126))
