"""F11-ISLA-TRAZADO: the traced Emerald Frontier grid (frontier/island_layout.py, reports/diseno/isla-esmeralda.md §1)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_layout as L  # noqa: E402

# isla-esmeralda.md §1, joined coordinates (East x + 56), from pokeemerald 731ad5bf warp_events
EMERALD_DOORS = {'Dome': (19, 17), 'Factory': (11, 38), 'Pike': (42, 27), 'Tower': (72, 14), 'Arena': (95, 29),
                 'Palace': (101, 56), 'Pyramid': (114, 14), 'ReceptionNorth': (26, 61), 'ReceptionSouth': (26, 65)}
EMERALD_RESERVED = {'PokemonCenter': (59, 51), 'Mart': (51, 51), 'RankingHall': (91, 12), 'ScottsHouse': (44, 5),
                    'Exchange': (66, 28)}
CAVE_MOUTHS = [(39, 55), (84, 7)]          # Artisan Cave, West (39,55) and East (28,7): left out
WATERFALL = (90, 64, 107, 67)              # its tiles in OutsideEast: left out


def at(x, y):
    return L.GRID[y][x]


def neighbours(x, y):
    return [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < L.W and 0 <= y + dy < L.H]


def reach(start):
    seen, todo = {start}, [start]
    while todo:
        for j in neighbours(*todo.pop()):
            if j not in seen and at(*j) in L.WALKABLE:
                seen.add(j)
                todo.append(j)
    return seen


def test_grid_is_128_by_72_and_fits_4x2_cells():
    assert (L.W, L.H) == (128, 72) == (56 + 72, 72)
    assert len(L.GRID) == len(L.HEIGHT) == 72
    assert all(len(r) == 128 for r in L.GRID + L.HEIGHT)
    assert L.CELLS == (4, 2) and L.OFFSET == (16, 4)
    assert L.OFFSET[0] * 2 + L.W == 160 and L.OFFSET[1] * 2 + L.H == 80


def test_every_tile_has_a_class_of_the_legend():
    used = {c for r in L.GRID for c in r}
    assert used <= set(L.LEGEND), used - set(L.LEGEND)
    assert L.WALKABLE <= set(L.LEGEND)
    # every class the design (§2.2) names is drawn somewhere
    assert set('~w.:,sm=#Tpofx B+'.replace(' ', '')) <= used


def test_heights_are_levels_and_water_and_walkable_agree():
    assert all(c in '0123' for r in L.HEIGHT for c in r)
    for y in range(L.H):
        for x in range(L.W):
            if at(x, y) == '~':
                assert L.HEIGHT[y][x] == '0', (x, y)
    # the plaza, the pier and the upper terraces
    assert L.HEIGHT[45][26] == '2' and L.HEIGHT[66][19] == '1'
    assert L.HEIGHT[20][19] == '3' and L.HEIGHT[18][72] == '3' and L.HEIGHT[20][114] == '3'


def test_doors_are_emeralds_and_sit_on_a_building():
    assert L.DOORS == EMERALD_DOORS
    doors = {(x, y) for y in range(L.H) for x in range(L.W) if at(x, y) == '+'}
    assert doors == set(EMERALD_DOORS.values())
    for name, (x, y) in L.DOORS.items():
        assert any(at(*j) == 'B' for j in neighbours(x, y)), name
        assert any(at(*j) in L.WALKABLE - {'+'} for j in neighbours(x, y)), name


def test_reserved_huecos_have_no_door():
    for name, (x, y) in EMERALD_RESERVED.items():
        assert L.RESERVED_DOORS[name] == (x, y)
        assert at(x, y) == 'B', name


def test_facility_doors_are_reached_from_the_plaza_and_the_pier_from_the_ferry():
    plaza = reach((26, 45))
    for name, door in L.DOORS.items():
        if name != 'ReceptionSouth':
            assert door in plaza, name
    pier = reach(L.FERRY)
    assert at(*L.FERRY) == 'm' and L.DOORS['ReceptionSouth'] in pier
    assert not pier & plaza          # pier and plaza meet only through the reception's doors, as in Emerald


def test_no_cave_and_no_waterfall():
    for x, y in CAVE_MOUTHS:
        assert at(x, y) not in L.WALKABLE
    x0, y0, x1, y1 = WATERFALL
    assert all(at(x, y) in '#~' for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))


def test_the_sea_rings_the_island():
    # the Battle Tower is the only thing touching Emerald's top edge; the ORAS map adds 4 rows of sea above it
    assert {at(x, 0) for x in range(L.W)} == {'~', 'B'} and {x for x in range(L.W) if at(x, 0) == 'B'} == set(range(64, 81))
    assert all(at(x, L.H - 1) == '~' for x in range(L.W))
    assert all(at(0, y) == '~' or at(0, y) == '#' for y in range(L.H))
