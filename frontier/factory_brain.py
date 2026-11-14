"""Noland's random rental team (cerebros.md §2), shared-script adapter.

WORK_RNG stores the 16-bit seed at the start of the six-rental draw. Replaying
that draw recovers all six offered set IDs, including the three not selected.
Open uses factory_open.WORK_DRAFT_RENTS to replay the promotion at draft time.
GLOBAL_SWAP dispatches to this routine only while Noland is
pending; WORK_RIVAL holds its three encoded sets until StartBattle consumes them.
Old paused challenges predate this seed contract: finish them before testing it.
"""
import data as fd
import factory
import factory_open as fo
import patch


def draw(sets, seed, level, size=6, excluded=(), open_mode=False, rents=0):
    """Reference for the Pawn LCG/rejection draw; return (encoded sets, state)."""
    pool = fd.indices(fd.RENTAL_LEVELS[min(level, 7)])
    state, selected, species, items = seed & 0xFFFFFFFF, [], set(), set()
    for position in range(size):
        if open_mode:
            pool = fo.pool(level + 1) if size != 6 else fo.draft_pools(level + 1, rents)[position]
        while True:
            state = (state * factory.LCG_MUL + factory.LCG_ADD) & 0xFFFFFFFF
            rank, index = pool[(((state >> 16) & 0x7FFF) * len(pool)) >> 15]
            value = index | (patch.SUPER if rank == 'S' else 0)
            s = sets[rank][index]
            if (value in excluded or s['species'] == fd.SPECIES_UNOWN or s['species'] in species
                    or (s['item'] in items and (size == 6 or s['item'] != 0))):
                continue
            selected.append(value)
            species.add(s['species'])
            items.add(s['item'])
            break
    return selected, state


def team(sets, seed, streak, open_mode=False, rents=0):
    """Replay this round's six rentals, then draw Noland's trio from its range."""
    level = min(streak // 7, 7)
    rentals, state = draw(sets, seed & 0xFFFF, level, open_mode=open_mode, rents=rents)
    rival, _ = draw(sets, state, level, 3, rentals, open_mode=open_mode)
    return rentals, rival


def routine(p):
    """factory_brain(): replay six offers and draw three; no menus or clock reads."""
    state = p.data_labels['factory_rng']
    table = p.data_labels['factory_slots']
    levels = p.data_labels['factory_levels']
    r = factory.Routine(p, 'factory_brain', ['first', 'count', 'level', 'value', 'rents', 'open_level',
        *(f'{field}{k}' for field in ('cell', 'species', 'item', 'encoded') for k in range(9))])
    r.sysreq('WorkGet', factory.WORK_RNG)
    r.op('STOR_P_PRI', state)
    r.sysreq('WorkGet', factory.WORK_STREAK)
    r.op('MOVE_ALT', 0)
    r.const(7)
    r.op('SDIV_ALT', 0)
    cap = r.new_label('noland_cap')
    r.const_alt(7)
    r.op('JSLEQ', cap)
    r.const(7)
    r.p.label(cap)
    r.store('level')
    for offset, name in ((0, 'first'), (1, 'count')):
        r.load('level')
        r.op('SMUL_P_C', 2)
        r.add(offset)
        r.cell(levels)
        r.store(name)
    r.sysreq('WorkGet', fo.WORK_DRAFT_RENTS)
    r.store('rents')
    for k in range(9):
        fo.select_range(r, k, 'rents')
        again = r.new_label(f'noland_draw{k}')
        r.p.label(again)
        r.call('factory_rand', 'count')
        r.load_alt('first')
        r.op('ADD', 0)
        r.cell(table)
        r.store(f'cell{k}')
        r.field(11, 10)
        r.store(f'species{k}')
        r.op('EQ_P_C_PRI', fd.SPECIES_UNOWN)
        r.op('JNZ', again)
        r.load(f'cell{k}')
        r.field(21, 10)
        r.store(f'item{k}')
        r.load(f'cell{k}')
        r.field(0, 10)
        r.store(f'encoded{k}')
        normal = r.new_label('noland_normal')
        r.load(f'cell{k}')
        r.field(10, 1)
        r.op('JZER', normal)
        r.load(f'encoded{k}')
        r.add(patch.SUPER)
        r.store(f'encoded{k}')
        r.p.label(normal)
        for j in range(k):
            if k >= 6 and j < 6:
                r.load(f'encoded{k}')
                r.load_alt(f'encoded{j}')
                r.op('JEQ', again)
                continue
            r.load(f'species{k}')
            r.load_alt(f'species{j}')
            r.op('JEQ', again)
            no_item = r.new_label('noland_no_item')
            r.load(f'item{k}')
            if k >= 6:
                r.op('JZER', no_item)
            r.load_alt(f'item{j}')
            r.op('JEQ', again)
            r.p.label(no_item)
    for k, work in enumerate(patch.WORK_RIVAL):
        r.sysreq('WorkSet', work, f'encoded{k + 6}')
    r.op('ZERO_PRI', 0)
    r.ret()


def swap_dispatch(p):
    """Multiplex existing case 9772: a pending route-1 Brain requests its team."""
    import brains
    at = factory._index(p, 'factory_swap')
    b = factory.Program(p.script)
    b.native_hashes = p.native_hashes
    b.sysreq('WorkGet', patch.WORK_ROUTE)
    b.emit('EQ_P_C_PRI', patch.ROUTE['factory'])
    b.emit('JZER', 'factory_swap_menu')
    b.sysreq('WorkGet', brains.WORK_BRAIN)
    b.emit('EQ_P_C_PRI', 9)
    b.emit('JNZ', 'factory_swap_brain')
    b.sysreq('WorkGet', brains.WORK_BRAIN)
    b.emit('EQ_P_C_PRI', 17)
    b.emit('JZER', 'factory_swap_menu')
    b.label('factory_swap_brain')
    b.call('factory_brain')
    b.emit('RETN', 0)
    b.label('factory_swap_menu')
    p.items[at + 2:at + 2] = b.items
