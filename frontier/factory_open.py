"""Measured Factory Open pools; this module does not enable the reception.

Adaptation: keep Maison's four strong copies, add only the eleven legendary
species available in Emerald. Species/copy equivalence is not moveset equality.
The explicit IDs below are checked against the hash-guarded ORAS archives by
check_mapping and against pinned Emerald source by probes/modos/factory_reference.py.
"""
import data as fd

# National species -> four measured maisonpkS IDs, not a contiguous legendary range.
LEGENDARY_SETS = {
    144: (908, 928, 948, 968), 145: (909, 929, 949, 969),
    146: (910, 930, 950, 970), 243: (911, 931, 951, 971),
    244: (912, 932, 952, 972), 245: (913, 933, 953, 973),
    377: (914, 934, 954, 974), 378: (915, 935, 955, 975),
    379: (916, 936, 956, 976), 380: (922, 942, 962, 982),
    381: (923, 943, 963, 983),
}
# Emerald 850..869 are Dragonite/Tyranitar, NOT legendary species. Both already
# have four strong Maison copies, so their extra Emerald sets add no duplicate ID.
TAIL_STRONG_SETS = {149: (376, 551, 726, 901), 248: (377, 552, 727, 902)}
# Maison-only legendary species excluded: no equivalent species in fixed Emerald source.
EXCLUDED_LEGENDARIES = (638, 639, 640, 641, 642, 485, 488, 645, 486)
# These Emerald strong species have no member in the existing Maison strong tiers.
# Keep the delivered tier adaptation; do not silently substitute an evolution.
SOURCE_STRONG_EXCLUSIONS = (22, 36, 55, 85, 97, 112, 125, 126, 178, 200, 356, 362)
STRONG_POOLS = tuple(tuple(fd.indices(tier)) for tier in fd.SUPER_TIERS)
LEGENDARY_POOL = tuple(('S', index) for ids in LEGENDARY_SETS.values() for index in ids)
OPEN_POOLS = (*STRONG_POOLS, tuple(x for pool in STRONG_POOLS for x in pool) + LEGENDARY_POOL)


def check_mapping(sets):
    """Refuse missing, empty, changed-species or non-base-form equivalents."""
    for species, ids in {**LEGENDARY_SETS, **TAIL_STRONG_SETS}.items():
        if len(ids) != 4 or len(set(ids)) != 4:
            raise ValueError('each species needs four distinct measured copies')
        for index in ids:
            s = sets['S'][index]
            if s['species'] != species or s['form'] or not all(s['moves']):
                raise ValueError(f'S{index}: incompatible equivalent of species {species}')
    measured = {i for i, s in enumerate(sets['S']) if s['species'] in LEGENDARY_SETS}
    if measured != {i for ids in LEGENDARY_SETS.values() for i in ids}:
        raise ValueError('legendary mapping does not cover all compatible Maison copies')
    for pool in OPEN_POOLS:
        if len(pool) != len(set(pool)):
            raise ValueError('duplicate set in Open pool')
        if any(sets[r][i]['species'] in (0, fd.SPECIES_UNOWN, *EXCLUDED_LEGENDARIES) for r, i in pool):
            raise ValueError('incompatible species in Open pool')
    return OPEN_POOLS


def pool(round_no, promoted=False):
    """One-based round, clamp the next-range promotion at the last pool."""
    if type(round_no) is not int or round_no < 1:
        raise ValueError('round must be positive')
    return OPEN_POOLS[min(round_no - 1 + bool(promoted), len(OPEN_POOLS) - 1)]


def draft_pools(round_no, rents):
    """Six per-position pools; promotion changes sets, never the round's IV."""
    if type(rents) is not int or not 0 <= rents <= 0xFFFF:
        raise ValueError('rents must fit its saved u16 work')
    better = fd.past_rentals_rank(rents)
    return tuple(pool(round_no, k < better) for k in range(fd.DRAFT_SIZE))
