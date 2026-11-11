"""Guards for the Dome's visual donor, independent of the native battle hooks."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import dome_room as room
import island_build
import overlay
from formats import zo_build


@pytest.fixture
def files():
    original, retail = overlay.maison_retail(overlay.source(overlay.ROMFS, 'a/0/1/3'))
    header = bytearray(original[0])
    struct.pack_into('<H', header, 6, room.TEXT)
    entities = bytearray(12 + len(room.NPCS) * 0x30 + 0x18)
    entities[5:7] = bytes([len(room.NPCS), 1])
    struct.pack_into('<HH', entities, 12 + len(room.NPCS) * 0x30, 209, 1)
    return [header, entities, overlay.dome.zone_script(retail), b'', b'\0' * 12]


def check(files):
    return room.check_room(zo_build(files), files[2], 209, 1)


def test_donor_is_distinct_but_script_natives_and_door_stay_the_same(files):
    assert island_build.CLONES[room.ZONE] == room.DONOR != 517
    assert island_build.native_donors()[room.ZONE] == 517
    plan = island_build.plan('s').splitlines()
    assert 'text.456=619' in plan
    assert 'zone.456.warp.0=0,209,1' in plan
    assert f'zone.456.loadBudget={island_build.LOAD_BUDGET}' in plan
    assert check(files) <= room.ZO_LIMIT


@pytest.mark.parametrize('damage,match', [('size', 'exceeds'), ('entities', 'unexpected'),
                                         ('exit', 'plaza door'), ('text', 'helper texts'),
                                         ('script', 'preserve its script')])
def test_rejects_broken_room(files, damage, match):
    script = bytes(files[2])
    if damage == 'size':
        files[3] = bytes(room.ZO_LIMIT)
    elif damage == 'entities':
        files[1][7] = 1
    elif damage == 'exit':
        struct.pack_into('<H', files[1], 12 + len(room.NPCS) * 0x30, 358)
    elif damage == 'text':
        struct.pack_into('<H', files[0], 6, 463)
    else:
        files[2] = b'bad'
    with pytest.raises(ValueError, match=match):
        room.check_room(zo_build(files), script, 209, 1)
