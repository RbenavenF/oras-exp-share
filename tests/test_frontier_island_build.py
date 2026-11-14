"""F11-ISLA-CONSTRUCCION: the island exterior built from the Emerald trace (frontier/island_build.py,
reports/diseno/isla-esmeralda.md §2-§3): doors on their tiles, buildings inside one cell and their hueco, the ferry
on the pier, every door reached on foot, and the checks on the Java build's log."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import island  # noqa: E402
import island_build as ib  # noqa: E402
import island_layout as L  # noqa: E402

ROWS = ib.island_rows()
H = len(ROWS) // 2


def at(x, y):
    return ROWS[y][x], ROWS[H + y][x]


def test_rows_are_the_trace_at_its_offset_with_sea_around():
    assert len(ROWS) == 160 and all(len(r) == 160 for r in ROWS)
    boxes = {(x, y) for f in ib.FACILITIES for x0, y0, x1, y1 in [ib.building_box(f)]
             for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    passage = {ib.map_tile(*t) for t in ib.RECEPTION_PASSAGE}
    for y in range(80):
        for x in range(160):
            ex, ey = x - L.OFFSET[0], y - L.OFFSET[1]
            if not (0 <= ex < L.W and 0 <= ey < L.H):
                assert at(x, y) == ('~', '0')
            elif (x, y) in passage:
                assert at(x, y) == ('=' if ey == 65 else ':', '2')
            elif (x, y) in ib.EDGE_STAIRS:
                assert at(x, y) == (':', '2') and at(x, y - 1) == ('=', '3')
            elif (x, y + 1) in ib.EDGE_STAIRS:
                pass
            elif (x, y) in boxes and L.GRID[ey][ex] == 'B':
                assert at(x, y) == ('.', L.HEIGHT[ey][ex])      # floor under the provisional building
            else:
                assert at(x, y) == (L.GRID[ey][ex], L.HEIGHT[ey][ex])


@pytest.mark.parametrize('facility', list(ib.FACILITIES))
def test_building_door_on_its_emerald_tile_inside_one_cell_and_its_hueco(facility):
    name, x, y = ib.FACILITIES[facility]
    assert (x, y) == ib.map_tile(*L.DOORS[facility]) and at(x, y)[0] == '+'
    x0, y0, x1, y1 = ib.building_box(facility)
    assert (x0 // 40, y0 // 40) == (x1 // 40, y1 // 40)               # stamped into one 40x40 cell
    w, h, dx, dy, prop = ib.catalogue(name)
    assert (x0 + dx, y0 + dy) == (x, y) and prop != '-'
    ex0, ey0 = x0 - L.OFFSET[0], y0 - L.OFFSET[1]
    for ty in range(ey0, ey0 + h):
        for tx in range(ex0, ex0 + w):
            if ty < L.DOORS[facility][1]:
                assert L.GRID[ty][tx] in 'BT', (facility, tx, ty)        # above the door row: inside the hueco
    front = at(x, y + 1)
    assert front[0] in L.WALKABLE and front[1] == at(x, y)[1]          # a doorstep at the door's level
    for other in ib.FACILITIES:
        if other != facility:
            a, b = ib.building_box(facility), ib.building_box(other)
            assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1], (facility, other)


def test_buildings_are_the_provisional_ones():
    assert ib.FACILITY_BUILDINGS == {
        'Tower': 'Rustboro flat-roof house', 'Dome': 'Fallarbor house', 'Factory': 'Gym',
        'Pyramid': 'Dewford shingle house', 'Pike': 'Route 124 treasure cabin',
        'Arena': 'Battle Resort thatched house', 'Palace': 'Rustboro two-story house'}
    assert set(ib.DOORS) == set(ib.FACILITIES)


def test_ferry_lands_on_the_pier_beside_the_clerk():
    zone, x, level, y, face = island.ARRIVAL
    assert zone == ib.ZONE_ISLAND and (x, y) == ib.map_tile(*L.FERRY) == (34, 73)
    assert at(x, y) == ('m', str(level)) and at(x - 1, y)[0] == 'm'      # the clerk stands west of the arrival
    assert (x // 40, y // 40) == (0, 1)


def test_reserved_huecos_have_no_door_and_stay_blocked():
    for name, (ex, ey) in L.RESERVED_DOORS.items():
        assert at(*ib.map_tile(ex, ey))[0] == 'B', name
    # the facility doors are the only doors: the reception's two are crossed by its passage until it has a building
    doors = {(x, y) for f, (_, x, y) in ib.FACILITIES.items()}
    assert {(x, y) for y in range(80) for x in range(160) if ROWS[y][x] == '+'} == doors
    assert {ib.map_tile(*L.DOORS[r]) for r in ('ReceptionNorth', 'ReceptionSouth')} <= \
        {ib.map_tile(*t) for t in ib.RECEPTION_PASSAGE}


@pytest.mark.parametrize('facility', list(ib.FACILITIES))
def test_every_door_is_walked_to_from_the_ferry_and_back(facility):
    _, x, y = ib.FACILITIES[facility]
    start = island.ARRIVAL[1], island.ARRIVAL[3]
    there = ib.route(start, (x, y + 1))
    assert there[0] == start and there[-1] == (x, y + 1)
    assert ib.route((x, y + 1), start)[-1] == start


def test_no_stair_ramp_crosses_a_cell_edge():
    """Every stair's lower (south) and upper (north) tiles are in its own cell: cells are painted one by one."""
    assert ib.EDGE_STAIRS == {(110, 39)}          # the Arena's, moved to (110,38)
    for y in range(80):
        for x in range(160):
            if ROWS[y][x] == '=':
                assert (y - 1) // 40 == y // 40 == (y + 1) // 40, (x, y)


def test_the_walk_crosses_into_all_eight_cells():
    reached = ib.route((island.ARRIVAL[1], island.ARRIVAL[3]))
    assert {(x // 40, y // 40) for x, y in reached} == {(x, y) for x in range(4) for y in range(2)}


def good_log():
    lines = [f'cell {x},{y} region {872 + y * 4 + x} model 1 collision 1 (painted 2, merged) buildings '
             f'{n} door props {n}' for (x, y), n in {(0, 0): 1, (1, 0): 1, (2, 0): 2, (3, 0): 1, (0, 1): 1, (1, 1): 0,
                                                       (2, 1): 1, (3, 1): 0}.items()]
    for facility in ib.DOORS:
        name, x, y = ib.FACILITIES[facility]
        lines.append(f'warp {ib.door_warp(facility)} door of {name} at tile {x},{y} z 36 -> zone 1 warp 0')
    lines += [f'clerk at tile {island.ARRIVAL[1] - 1},{island.ARRIVAL[3]} z 18.0 face 3', 'outside the world pack: {}',
              'load budget 3532544 bytes: world pack 1, prop pack 2, models 3 (872 3)']
    return '\n'.join(lines) + '\n'


def test_island_log_checks():
    ib.check_island_log(good_log())
    name, x, y = ib.FACILITIES['Arena']
    with pytest.raises(ValueError, match='Arena door was not linked'):
        ib.check_island_log(good_log().replace(f'at tile {x},{y} ', f'at tile {x},{y + 1} '))
    with pytest.raises(ValueError, match='lacks'):
        ib.check_island_log(good_log().replace('outside the world pack: {}', "outside the world pack: {a=true}"))
    with pytest.raises(ValueError, match='not facility doors'):
        ib.check_island_log(good_log() + 'warp 7 door of Gym at tile 1,1 z 0 -> zone 1 warp 0\n')
    with pytest.raises(ValueError, match='eight cells'):
        ib.check_island_log(good_log().replace('cell 3,1 ', 'cell 3,0 '))
    with pytest.raises(ValueError, match='clerk'):
        ib.check_island_log(good_log().replace('clerk at tile', 'clerk at tiles'))
    with pytest.raises(ValueError, match='door props'):
        ib.check_island_log(good_log().replace('buildings 2 door props 2', 'buildings 2 door props 1'))


def test_built_island_when_present():
    """The last local build (work/f11/build, python frontier/overlay.py): its Java log passes the checks and the island
    ZO fits the measured container limit. Skipped without a local build."""
    log = ROOT / 'work/f11/build/out-island/java.log'
    if not log.exists():
        pytest.skip('local build required')
    text = log.read_text()
    ib.check_island_log(text)
    assert ib.check_budget(text) <= ib.ISLAND_BUDGET
