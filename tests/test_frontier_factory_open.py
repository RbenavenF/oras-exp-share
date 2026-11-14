"""Open Factory range contract, measured equivalents and fixed-source audit.

No reception is enabled by this milestone; Pawn and Azahar acceptance follows
when the draft consumes these pools.
"""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'frontier/probes/modos')]
import data as fd
import factory
import factory_open as fo
import factory_reference as ref


@pytest.fixture(scope='module')
def sets():
    if not (fd.GAME / 'a/1/8/4').exists():
        pytest.skip('Local baseline required')
    return fd.check_tiers(fd.load())


def test_open_ranges_keep_four_strong_copies_and_add_only_compatible_legends(sets):
    pools = fo.check_mapping(sets)
    assert [len(p) for p in pools] == [196, 196, 196, 196, 828]
    assert pools[:4] == tuple(tuple(fd.indices(tier)) for tier in fd.SUPER_TIERS)
    assert set(pools[-1]) - set(x for p in pools[:4] for x in p) == set(fo.LEGENDARY_POOL)
    assert len({sets[r][i]['species'] for r, i in pools[-1]}) == 207
    assert len(fo.LEGENDARY_POOL) == 44
    for pool in pools:
        factory.check_draws(sets, list(pool), [(0, len(pool))])


def test_tail_strong_sets_are_deduplicated_not_extra_weight(sets):
    last = fo.pool(5)
    for species, ids in fo.TAIL_STRONG_SETS.items():
        assert all(sets['S'][i]['species'] == species for i in ids)
        assert all(last.count(('S', i)) == 1 for i in ids)
    excluded_ids = {i for i, s in enumerate(sets['S']) if s['species'] in fo.EXCLUDED_LEGENDARIES}
    assert len(excluded_ids) == 36
    assert not excluded_ids & {i for _, i in last}
    # In particular Latias/Latios resume at 922/923, after the excluded gen 5 IDs.
    assert ('S', 922) in last and ('S', 923) in last and ('S', 917) not in last


@pytest.mark.parametrize('field,value', [('species', 638), ('form', 1), ('moves', (0, 1, 2, 3))])
def test_mapping_rejects_changed_or_incompatible_equivalent(sets, field, value):
    changed = deepcopy(sets)
    changed['S'][922][field] = value
    with pytest.raises(ValueError, match='incompatible'):
        fo.check_mapping(changed)


def test_mapping_rejects_an_unmapped_compatible_copy(sets):
    changed = deepcopy(sets)
    changed['S'][917]['species'] = 380
    with pytest.raises(ValueError, match='cover all'):
        fo.check_mapping(changed)


@pytest.mark.parametrize('round_no', [1, 2, 3, 4, 5, 6, 8, 9, 100, 9363])
@pytest.mark.parametrize('rents,promoted', [(0, 0), (14, 0), (15, 1), (21, 1), (22, 2),
                                          (28, 2), (29, 3), (35, 3), (36, 4),
                                          (42, 4), (43, 5), (65535, 5)])
def test_promotion_is_per_position_and_clamps(round_no, rents, promoted):
    pools = fo.draft_pools(round_no, rents)
    assert len(pools) == 6
    assert pools[:promoted] == (fo.pool(round_no, True),) * promoted
    assert pools[promoted:] == (fo.pool(round_no),) * (6 - promoted)
    assert pools[-1] == fo.OPEN_POOLS[min(round_no - 1, 4)]
    if round_no >= 5:
        assert all(p == fo.OPEN_POOLS[-1] for p in pools)


@pytest.mark.parametrize('round_no', [-1, 0, 1.5, True])
def test_invalid_round(round_no):
    with pytest.raises(ValueError):
        fo.pool(round_no)


@pytest.mark.parametrize('rents', [-1, 65536, 1.5, True])
def test_invalid_saved_rents(rents):
    with pytest.raises(ValueError):
        fo.draft_pools(1, rents)


def test_reference_audit_against_pinned_git_objects():
    repo = Path('/tmp/frontier-cerebros-pokeemerald')
    if not (repo / '.git').exists() or not (fd.GAME / 'a/1/8/4').exists():
        pytest.skip('Local fixed-source checkout and baseline required; run factory_reference.py explicitly')
    result = ref.verify(repo)
    assert result['commit'] == ref.REF
    assert result['tail_850_881'][850] == {'species': 149, 'oras': (376, 551, 726, 901)}
    assert result['tail_850_881'][869]['species'] == 248
    assert result['tail_850_881'][870]['species'] == 144
    assert result['tail_850_881'][881]['species'] == 245
    assert len(result['source_sha256']) == 4
    assert len(result['mapping_372_881']) == 510
    assert len(result['unmapped_source_ids']) == 48
    assert all(not result['mapping_372_881'][i]['oras'] for i in result['unmapped_source_ids'])
