"""Battle Factory rental data (frontier/data.py): rules, table layout and, with the local dump, the tiers."""
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import data as fd  # noqa: E402
from formats import garc_entries, rebuild_garc  # noqa: E402


def test_parse_set_matches_pk3ds_layout():
    raw = struct.pack('<5HBBHH', 409, 457, 89, 157, 182, 0xC0 | 0x22, 7, 158, 0)
    s = fd.parse_set(raw)
    assert s == {'species': 409, 'moves': (457, 89, 157, 182), 'evs': 0x22, 'nature': 7, 'item': 158, 'form': 0}
    with pytest.raises(ValueError):
        fd.parse_set(raw[:-1])


def test_parse_trainer():
    assert fd.parse_trainer(struct.pack('<HH3H', 64, 3, 940, 946, 961)) == {'class': 64, 'sets': (940, 946, 961)}
    with pytest.raises(ValueError):
        fd.parse_trainer(struct.pack('<HH', 2, 1))


def test_emerald_rules():
    assert [fd.fixed_iv(r) for r in range(1, 10)] == [3, 6, 9, 12, 15, 21, 31, 31, 31]
    assert fd.fixed_iv(1, last_battle=True) == 6 and fd.fixed_iv(6, last_battle=True) == 31
    # pokeemerald 731ad5bf sBattlePointAwards, Factory singles: round 15 gives 10, rounds 25+ give 15
    assert [fd.battle_points(r) for r in (1, 2, 3, 13, 14, 15, 20, 25, 30, 99)] == [3, 3, 4, 9, 9, 10, 12, 15, 15, 15]
    assert all(len(column) == 30 for column in fd.FRONTIER_BP.values())
    assert fd.battle_points(3, brain=True) == 14
    assert fd.brain_battle(21, 0) == 'silver' and fd.brain_battle(42, 0) is None
    assert fd.brain_battle(42, 1) == 'gold' and fd.brain_battle(21, 1) is None
    assert [b for b in range(1, 120) if fd.brain_battle(b, 2)] == [21, 42, 63, 84, 105]
    assert [fd.past_rentals_rank(n) for n in (0, 14, 15, 22, 42, 43, 200)] == [0, 0, 1, 2, 4, 5, 5]
    assert fd.rental_level(1) == fd.RENTAL_LEVELS[0] and fd.rental_level(30) == fd.RENTAL_LEVELS[-1]


def test_level_table_round_trip():
    blob = fd.level_table()
    levels = fd.read_level_table(blob)
    assert len(levels) == len(fd.RENTAL_LEVELS) == 8
    for packed, level in zip(levels, fd.RENTAL_LEVELS):
        assert packed == [(fd.ARCHIVE_ID[r], a, b - a + 1) for r, a, b in level]
    assert levels[3] == [(0xB8, 0, 21), (0xB8, 208, 175)]
    assert sum(n for _, _, n in levels[-1]) == 4 * 196


def test_levels_do_not_overlap_within_a_level():
    for level in fd.RENTAL_LEVELS:
        picked = fd.indices(level)
        assert len(picked) == len(set(picked)) >= fd.DRAFT_SIZE


@pytest.fixture(scope='module')
def maison():
    if not (fd.GAME / 'a/1/8/4').exists():
        pytest.skip('Local baseline required')
    return fd.load()


def test_dump_tiers_and_counts(maison):
    assert {k: len(v) for k, v in maison.items()} == {'maisonpkN': 999, 'maisontrN': 129,
                                                       'maisonpkS': 999, 'maisontrS': 217}
    sets = fd.check_tiers(maison)
    for level in fd.RENTAL_LEVELS:
        assert all(sets[r][i]['species'] not in (0, fd.SPECIES_UNOWN) for r, i in fd.indices(level))
        assert all(sets[r][i]['moves'][0] for r, i in fd.indices(level))


def test_dump_garcs_rebuild_identically():
    if not (fd.GAME / 'a/1/8/4').exists():
        pytest.skip('Local baseline required')
    for rel, _ in fd.ARCHIVES.values():
        data = (fd.GAME / rel).read_bytes()
        assert rebuild_garc(data, {}) == data
        assert all(n == fd.SET_SIZE for _, _, _, n in garc_entries(data)) == rel.endswith(('2', '4'))


def test_load_refuses_other_data(tmp_path):
    for rel, _ in fd.ARCHIVES.values():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b'not the dump')
    with pytest.raises(ValueError, match='unexpected sha256'):
        fd.load(tmp_path)
