"""Frontier Pass, Lilycove sailor and ferry destination (frontier/island.py), run in scripts/pawn_vm.py.

Natives and every routine the code under test calls are stubbed: this checks the generated logic (menus, gates,
the item given, the arrival point), not GF's VM or the game (that is the Azahar test in reports/frontier.md).
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import island  # noqa: E402
import overlay  # noqa: E402
from formats import garc_entries, lz11_decompress, zo_files  # noqa: E402
from pawn import OP, Script, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

ZERO = lambda vm, a: 0  # noqa: E731


class Natives(dict):
    """Named stubs; any other native returns 0 (talk eyes, sounds, waits)."""

    def __init__(self, table, log):
        super().__init__({s32(gf_hash(name)): fn for name, fn in table.items()})
        self.log = log

    def __missing__(self, key):
        return ZERO


def stub_calls(script, labels, keep, special):
    """A stub for every CALL target except the labels in `keep`; `special`: {label: fn}."""
    targets = {ins.address + ins.args[0] for ins in decode(script.code) if ins.op == OP['CALL']}
    calls = {t: ZERO for t in targets if t not in {labels[k] for k in keep}}
    calls.update({labels[k]: fn for k, fn in special.items()})
    return calls


@pytest.fixture(scope='module')
def scripts():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    shared = (overlay.ROMFS / overlay.SHARED).read_bytes()
    ferry = overlay.shared_script(shared, island.FERRY_SCRIPT)
    shared10 = overlay.shared_script(shared, island.SHARED10)
    zones = overlay.ZONES.read_bytes()
    _, _, offset, length = garc_entries(zones)[island.ZONE_HARBOR]
    harbor = Script.parse(zo_files(lz11_decompress(zones[offset:offset + length]))[2])
    return ferry, shared10, harbor


@pytest.fixture(scope='module')
def ferry(scripts):
    retail = scripts[0]
    program = island.ferry_program(retail)
    labels = program.layout()
    script = program.build_script(f'L{retail.main:x}')
    assert Script.parse(script.build(pad=False)).build(pad=False) == script.build(pad=False)
    return script, labels


def sail(ferry, zone, has_pass, choice=None, yes=1, npc=0):
    script, labels = ferry
    items = {736: 1, island.ITEM_PASS: int(has_pass)}
    log = {'menu': [], 'msg': [], 'trip': []}
    natives = Natives({
        'ItemGetNum': lambda vm, a: items.get(a[0], 0),
        'FlagGet': lambda vm, a: int(a[0] == island.FLAG_CHAMPION),
        'ListMenuAdd': lambda vm, a: log['menu'].append((a[0], a[1])),
    }, log)
    calls = stub_calls(script, labels, [island.FERRY_MENU], {
        'Ld8': lambda vm, a: log['msg'].append(a[0]),
        'L7c8': lambda vm, a: 3 if choice is None else choice,
        'L260': lambda vm, a: yes,
        island.MAPCHANGE: lambda vm, a: log['trip'].append(tuple(a)),
    })
    VM(script, natives, calls).run(labels[island.FERRY_MENU], npc, zone)
    return log


@pytest.mark.parametrize('zone, retail', [(317, [(6, 0), (7, 1)]), (275, [(6, 0), (8, 2)])])
def test_the_pass_adds_the_island_in_lilycove_and_slateport(ferry, zone, retail):
    assert sail(ferry, zone, False)['menu'] == retail + [island.MENU_CANCEL]
    assert sail(ferry, zone, True)['menu'] == retail + [(island.LINE_ISLAND, island.MENU_ISLAND), island.MENU_CANCEL]


def test_other_harbors_keep_their_menu(ferry):
    assert sail(ferry, 212, True)['menu'] == [(7, 1), (8, 2), island.MENU_CANCEL]


def test_island_trip(ferry):
    log = sail(ferry, 317, True, island.MENU_ISLAND)
    assert island.LINE_ISLAND_GO in log['msg'] and island.RESORT_CONFIRM_LINE not in log['msg']
    assert log['trip'] == [(*island.ARRIVAL, 0)]
    declined = sail(ferry, 317, True, island.MENU_ISLAND, yes=0)
    assert declined['trip'] == [] and 13 in declined['msg']        # «Estaremos a tu disposición…»


def test_retail_trips_unchanged(ferry):
    assert sail(ferry, 317, True, 0)['trip'] == [(*island.RESORT_ARRIVAL, 0)]
    assert sail(ferry, 317, True, 1)['trip'] == [(216, 37, 56, 9, 1, 0)]     # Slateport, through the cabin


def harbor_run(scripts, base, champion, has_pass, event=None):
    ferry, shared10, _ = scripts
    lines = (30, 31)
    program = island.harbor_program(base, ferry, shared10, lines)
    labels = program.layout()
    script = program.build_script(f'L{base.main:x}')
    items = {island.ITEM_PASS: int(has_pass)}
    log = {'msg': [], 'give': [], 'retail': 0}

    def give(vm, a):
        log['give'].append(tuple(a))
        items[a[0]] = items.get(a[0], 0) + a[1]

    def retail(vm, a):
        log['retail'] += 1

    natives = Natives({
        'FlagGet': lambda vm, a: int(champion and a[0] == island.FLAG_CHAMPION),
        'ItemGetNum': lambda vm, a: items.get(a[0], 0),
    }, log)
    _, retail_label = island.sailor_target(island.Program.from_script(base), f'L{base.main:x}')
    calls = stub_calls(script, labels, ['frontier_sailor'], {
        'frmsg_d8': lambda vm, a: log['msg'].append(a[0]),
        f'frgive_{island.ev.GIVE_ROUTINE:x}': give,
        retail_label: retail,
    })
    vm = VM(script, natives, calls)
    if event is None:
        vm.run(labels['frontier_sailor'])
    else:
        vm.write(144, event)                     # the dispatcher reads the event id from data address 144
        vm.run(labels[f'L{base.main:x}'])
    return log


@pytest.mark.parametrize('champion, has_pass, given', [(False, False, False), (True, False, True), (True, True, False)])
def test_sailor_gives_the_pass_once_to_a_champion(scripts, champion, has_pass, given):
    log = harbor_run(scripts, scripts[2], champion, has_pass)
    if given:
        assert log['give'] == [(island.ITEM_PASS, 1, 1)] and log['msg'] == [30, 31] and log['retail'] == 0
    else:
        assert log['give'] == [] and log['msg'] == [] and log['retail'] == 1


def test_event_4_reaches_the_new_sailor(scripts):
    assert harbor_run(scripts, scripts[2], True, False, event=island.SAILOR_EVENT)['give'] == [(island.ITEM_PASS, 1, 1)]


def test_sailor_on_top_of_the_mew_harbor(scripts):
    """The Mew event's harbor (more cases, its own transplanted helpers) still gets the sailor."""
    sys.path.append(str(ROOT / 'faraway'))
    import event as ev
    ferry, shared10, harbor = scripts
    mew = ev.harbor_script(harbor, ferry, shared10)
    assert len(mew.code) > len(harbor.code)
    assert harbor_run(scripts, mew, True, False)['give'] == [(island.ITEM_PASS, 1, 1)]
    assert harbor_run(scripts, mew, True, False, event=ev.EV_GIVER)['give'] == []


def test_island_script_keeps_arrival_and_clerk_without_the_scene():
    import island_build
    from pawn import decode as _decode
    zones = overlay.ZONES.read_bytes()
    _, _, offset, length = garc_entries(zones)[island_build.DONOR_ISLAND]
    donor = Script.parse(zo_files(lz11_decompress(zones[offset:offset + length]))[2])
    script = island_build.island_script(donor)
    tables = [i for i in _decode(script.code) if i.op == OP['CASETBL']]
    events = [sorted(t.args[2::2]) for t in tables]
    assert sorted(island_build.ISLAND_EVENTS) in events and sorted(island_build.DONOR_EVENTS) not in events
    # The arrival routine no longer branches on the Resort scene work: its first jump is unconditional.
    ins = _decode(script.code)
    k = next(i for i, x in enumerate(ins) if x.op == OP['PUSH_P_C'] and x.args == [island_build.WORK_RESORT_SCENE])
    assert ins[k + 4].op == OP['JUMP']
    assert Script.parse(script.build()).build() == script.build()


def test_every_island_clone_gets_its_donors_native_groups():
    """A clone runs its donor's script, so it needs the donor's native groups (the hall hung without the Maison's)."""
    import island_build
    import patch
    if not patch.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    assert f'clones={island_build.DONOR_ISLAND}:{island_build.ZONE_ISLAND},' \
           f'{island_build.DONOR_HALL}:{island_build.ZONE_HALL},' \
           f'{island_build.DONOR_HALL}:{island_build.ZONE_TOWER},' \
           f'{island_build.dome_room.DONOR}:{island_build.ZONE_DOME},' \
           f'{island_build.DONOR_HALL}:{island_build.ZONE_PALACE},' \
           f'{island_build.DONOR_HALL}:{island_build.ZONE_PIKE},' \
           f'{island_build.DONOR_HALL}:{island_build.ZONE_ARENA},' \
           f'{island_build.DONOR_HALL}:140,{island_build.pyramid.FLOOR_DONOR}:141,{island_build.pyramid.FLOOR_DONOR}:142\n' \
           in island_build.plan('s')
    code = bytearray(patch.REPOLISHED.read_bytes())
    patch.zone_natives(code, island_build.native_donors())
    mask = lambda zone: int.from_bytes(code[patch.ZONE_NATIVES - patch.BASE + 4 * zone:][:4], 'little')
    for slot, donor in island_build.native_donors().items():
        assert mask(slot) == mask(donor)
    assert all(mask(z) & patch.NATIVES_MAISON
               for z in (island_build.ZONE_HALL, island_build.ZONE_TOWER, island_build.ZONE_DOME,
                         island_build.ZONE_PALACE, island_build.ZONE_PIKE, island_build.ZONE_ARENA, 140, 141, 142))


def test_plaza_plan_links_the_tower_the_dome_the_factory_and_the_palace():
    """Seven facility buildings with their door props (§23), four door warps in FACILITIES order: the Tower's into
    329 (island warp 0), the Dome's into 456 (warp 1), the Factory's into 213 (warp 2) and the Palace's into 340
    (warp 3); each interior's exit comes back to its door."""
    import island_build
    lines = island_build.plan('s').splitlines()
    buildings = [line for line in lines if line.startswith('plaza.building.')]
    doors = [line for line in lines if line.startswith('plaza.door.')]
    assert len(buildings) == 7 and all(line.split('=', 1)[1].count('|') == 2 for line in buildings)
    factory, tower, dome, palace, pike, arena, pyramid = (
        list(island_build.FACILITIES).index(f) for f in ('Factory', 'Tower', 'Dome', 'Palace', 'Pike', 'Arena', 'Pyramid'))
    assert doors == [f'plaza.door.{tower}={island_build.ZONE_TOWER},0',
                     f'plaza.door.{dome}={island_build.ZONE_DOME},0',
                     f'plaza.door.{factory}={island_build.ZONE_HALL},0',
                     f'plaza.door.{pyramid}={island_build.ZONE_PYRAMID},0',
                     f'plaza.door.{pike}={island_build.ZONE_PIKE},0',
                     f'plaza.door.{arena}={island_build.ZONE_ARENA},0',
                     f'plaza.door.{palace}={island_build.ZONE_PALACE},0']
    assert buildings[palace].startswith(f'plaza.building.{palace}=Rustboro two-story house|28|25')
    assert buildings[dome].startswith(f'plaza.building.{dome}=Fallarbor house|')
    assert buildings[factory].startswith(f'plaza.building.{factory}=Gym|')
    assert not any(line.startswith(f'zone.{island_build.ZONE_ISLAND}.warp.') for line in lines)
    assert f'zone.{island_build.ZONE_TOWER}.warp.0=0,{island_build.ZONE_ISLAND},0' in lines
    assert f'zone.{island_build.ZONE_DOME}.warp.0=0,{island_build.ZONE_ISLAND},1,2' in lines
    assert f'zone.{island_build.ZONE_HALL}.warp.0=0,{island_build.ZONE_ISLAND},2' in lines
    assert f'zone.{island_build.ZONE_PYRAMID}.warp.0=0,{island_build.ZONE_ISLAND},3' in lines   # door (32,57)
    assert f'zone.{island_build.ZONE_PIKE}.warp.0=0,{island_build.ZONE_ISLAND},4' in lines
    assert f'zone.{island_build.ZONE_ARENA}.warp.0=0,{island_build.ZONE_ISLAND},5' in lines
    assert f'zone.{island_build.ZONE_PALACE}.warp.0=0,{island_build.ZONE_ISLAND},6' in lines
    assert [f'zone.{z}.warp.{k}={k},140,0' for z in (141, 142) for k in range(3)] == [l for l in lines if l.startswith(('zone.141.', 'zone.142.'))
                                                                       and '.warp.' in l]
    assert buildings[arena].startswith(f'plaza.building.{arena}=Battle Resort thatched house|17|25')
    assert all(f'keeptext.{z}=1' in lines
               for z in (island_build.ZONE_TOWER, island_build.ZONE_DOME, island_build.ZONE_PALACE,
                         island_build.ZONE_PIKE, island_build.ZONE_ARENA))


def test_each_interior_exits_to_its_own_door(monkeypatch):
    """Plaza numbers the island's door warps in FACILITIES order; an interior's exit must follow its door's number,
    not a fixed 0 (with the Tower or Dome open, the Factory's door is no longer warp 0)."""
    import island_build
    monkeypatch.setattr(island_build, 'DOORS', {'Factory': (island_build.ZONE_HALL, 0)})
    lines = island_build.plan('s').splitlines()
    assert f'zone.{island_build.ZONE_HALL}.warp.0=0,{island_build.ZONE_ISLAND},0' in lines
    monkeypatch.setattr(island_build, 'DOORS', {'Tower': (329, 0), 'Factory': (island_build.ZONE_HALL, 0),
                                                'Palace': (340, 0)})
    lines = island_build.plan('s').splitlines()
    exits = sorted(line for line in lines if f'.warp.0=0,{island_build.ZONE_ISLAND},' in line)
    assert exits == sorted([f'zone.329.warp.0=0,{island_build.ZONE_ISLAND},0',
                            f'zone.{island_build.ZONE_HALL}.warp.0=0,{island_build.ZONE_ISLAND},1',
                            f'zone.340.warp.0=0,{island_build.ZONE_ISLAND},2'])


def test_facility_clones_are_generic(monkeypatch, tmp_path):
    """A facility clone added to CLONES gets its place, its zones= entry, its story text if in KEEP_TEXT and its
    native donor if in NATIVE_DONORS; build() refuses a script for a zone that is not a facility clone."""
    import island_build
    monkeypatch.setattr(island_build, 'CLONES', {**island_build.CLONES, 329: 517, 143: 192})
    monkeypatch.setattr(island_build, 'KEEP_TEXT', {*island_build.KEEP_TEXT, 329})
    monkeypatch.setattr(island_build, 'NATIVE_DONORS', {143: 517})
    lines = island_build.plan('s').splitlines()
    assert f'zones={island_build.ZONE_ISLAND},{island_build.ZONE_HALL},329,{island_build.ZONE_DOME},' \
           f'{island_build.ZONE_PALACE},{island_build.ZONE_PIKE},{island_build.ZONE_ARENA},140,141,142,143' in lines
    assert {f'place.329={island_build.PLACE}', f'place.143={island_build.PLACE}', 'keeptext.329=1'} <= set(lines)
    assert 'keeptext.143=1' not in lines
    assert island_build.native_donors()[143] == 517 and island_build.native_donors()[329] == 517
    for stray in (island_build.ZONE_ISLAND, 600):
        with pytest.raises(ValueError, match='not facility clones'):
            island_build.build({}, None, tmp_path / 'w', {stray: b''})
    assert not (tmp_path / 'w').exists()          # refused before anything is staged


def test_plaza_buildings_are_distinct_and_drawn(monkeypatch):
    """§24: one distinct building per facility, none the game leaves undrawn; plan() refuses either mistake."""
    import island_build
    names = [name for name, _, _ in island_build.FACILITIES.values()]
    assert len(set(names)) == 7 and not island_build.NOT_DRAWN & set(names)
    repeated = dict(island_build.FACILITIES, Palace=island_build.FACILITIES['Tower'])
    monkeypatch.setattr(island_build, 'FACILITIES', repeated)
    with pytest.raises(ValueError, match='distinct and drawn'):
        island_build.plan('s')
    undrawn = dict(island_build.FACILITIES, Palace=('Pacifidlog stilt hut', 28, 25))
    monkeypatch.setattr(island_build, 'FACILITIES', undrawn)
    with pytest.raises(ValueError, match='distinct and drawn'):
        island_build.plan('s')


def test_island_load_budget_over_the_measured_one_is_refused():
    """§23: Plaza's last "load budget" line is checked against LOAD_BUDGET; a log without one is refused too."""
    import island_build
    line = 'load budget {} bytes: world pack 1, prop pack 2, models 3 (864 3)'
    log = '\n'.join([line.format(10 ** 7), 'pack ok', line.format(island_build.LOAD_BUDGET)]) + '\n'
    assert island_build.check_budget(log) == island_build.LOAD_BUDGET   # the last line counts
    with pytest.raises(ValueError, match='measured to load'):
        island_build.check_budget(log + line.format(island_build.LOAD_BUDGET + 1) + '\n')
    with pytest.raises(ValueError, match='no load budget'):
        island_build.check_budget('pack ok\n')
