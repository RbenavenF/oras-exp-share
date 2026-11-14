"""Factory Open pools and Pawn range selection; reception is enabled separately.

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
LEGENDARY_POOL = tuple(('S', index) for index in sorted(i for ids in LEGENDARY_SETS.values() for i in ids))
LINE_BASE = 1134  # appended AFTER all existing shared text (REPARTO)
WORK_DRAFT_RENTS = 16471  # saved counter at the start of this round's draw
WORK_PENDING_RENT = 16673  # 0 none, 1 Singles 50, 2 Singles Open; consumed only on victory
OPEN_POOLS = (*STRONG_POOLS, tuple(x for pool in STRONG_POOLS for x in pool) + LEGENDARY_POOL)


def mark_rental(r):
    """Persist one pending rental, only for supported Singles CONFIG values."""
    done, open_ = r.new_label(r.name + '_rent_mark_done'), r.new_label(r.name + '_rent_mark_open')
    import modes
    r.sysreq('WorkGet', modes.CONFIG[1])
    r.op('EQ_P_C_PRI', 0x164)
    r.op('JNZ', open_)
    for config in (0, 50):
        next_ = r.new_label(r.name + '_rent_mark_next')
        r.sysreq('WorkGet', modes.CONFIG[1])
        r.op('EQ_P_C_PRI', config)
        r.op('JZER', next_)
        r.sysreq('WorkSet', WORK_PENDING_RENT, 1)
        r.op('JUMP', done)
        r.p.label(next_)
    r.op('JUMP', done)
    r.p.label(open_)
    r.sysreq('WorkSet', WORK_PENDING_RENT, 2)
    r.p.label(done)


def credit_rental(r):
    """Credit one successful rental to its mode bank, saturating the saved u16."""
    import modes
    done = r.new_label('rent_credit_done')
    for mode, configs in ((0, (0, 50)), (1, (0x164,))):
        next_, valid, saturated = (r.new_label('rent_credit_' + s) for s in ('next', 'valid', 'sat'))
        r.sysreq('WorkGet', WORK_PENDING_RENT)
        r.op('EQ_P_C_PRI', mode + 1)
        r.op('JZER', next_)
        for config in configs:
            r.sysreq('WorkGet', modes.CONFIG[1])
            r.op('EQ_P_C_PRI', config)
            r.op('JNZ', valid)
        r.op('JUMP', done)
        r.p.label(valid)
        r.sysreq('WorkGet', modes.FACTORY_RENTS[mode])
        r.const_alt(65535)
        r.op('JSGEQ', saturated)
        r.add(1)
        r.op('PUSH_PRI', 0)
        r.p.push(modes.FACTORY_RENTS[mode])
        r.p.emit('SYSREQ_N', 'WorkSet', 8)
        r.p.label(saturated)
        r.op('JUMP', done)
        r.p.label(next_)
    r.p.label(done)
    # A stale/corrupt mark must never be credited by a later unrelated win.
    r.sysreq('WorkSet', WORK_PENDING_RENT, 0)


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


def install_data(p, cells):
    """Extend only the private Pawn slot table; legacy slots/ranges stay identical."""
    import factory
    sets = fd.check_tiers(fd.load())
    check_mapping(sets)
    table, _ = factory.slots()
    if cells != factory.slot_cells(sets, table):
        raise ValueError('Open draft requires the guarded legacy slot table')
    complete = table + list(LEGENDARY_POOL)
    ranges = []
    for pool_ in OPEN_POOLS:
        first = complete.index(pool_[0])
        if tuple(complete[first:first + len(pool_)]) != pool_:
            raise ValueError('Open pool is not contiguous in private slot table')
        factory.check_draws(sets, complete, [(first, len(pool_))])
        ranges += [first, len(pool_)]
    p.data_block('factory_open_levels', ranges)
    return cells + factory.slot_cells(sets, LEGENDARY_POOL)


def select_range(r, position, rents):
    """Override first/count only for CONFIG=0x164. PRI level stays the IV round.

    `position` is 0..5 for replayed offers and 6..8 for Noland's own team. The
    latter uses the unpromoted round pool, as the reference opponent generator.
    `rents` names a local holding the snapshot, never the mutable live counter.
    """
    import modes
    done, capped = r.new_label(r.name + '_open_range_done'), r.new_label(r.name + '_open_range_cap')
    r.sysreq('WorkGet', modes.CONFIG[1])
    r.op('EQ_P_C_PRI', modes.pack_config(1, 1, 100))
    r.op('JZER', done)
    r.load('level')
    r.store('open_level')
    if position < fd.DRAFT_SIZE:
        promoted = r.new_label(r.name + '_open_promoted')
        # At most five promotions; exact GetNumPastRentalsRank boundaries.
        if position < 5:
            r.load(rents)
            r.const_alt((15, 22, 29, 36, 43)[position])
            r.op('JSLESS', promoted)
            r.load('open_level')
            r.add(1)
            r.store('open_level')
            r.p.label(promoted)
    r.load('open_level')
    r.const_alt(4)
    r.op('JSLEQ', capped)
    r.const(4)
    r.p.label(capped)
    r.store('open_level')
    for offset, name in ((0, 'first'), (1, 'count')):
        r.load('open_level')
        r.op('SMUL_P_C', 2)
        r.add(offset)
        r.cell(r.p.data_labels['factory_open_levels'])
        r.store(name)
    r.p.label(done)


def lines_for(lang, gametext, sets):
    from formats import garc_entries, text_lines, words_to_text
    def names(entry):
        _, _, at, size = next(e for e in garc_entries(gametext) if e[0] == entry)
        return [words_to_text(w) for w in text_lines(gametext[at:at + size])[0]]
    species, items = names(fd.TEXT_SPECIES), names(fd.TEXT_ITEMS)
    return [f'{species[sets[r][i]["species"]]} ({items[sets[r][i]["item"]]})'
            if sets[r][i]['item'] else species[sets[r][i]['species']]
            for r, i in LEGENDARY_POOL]
