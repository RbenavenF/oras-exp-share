"""Native F9 enrollment API on the exact built Field/code.bin (not Azahar).

Real slot accessor, mocked level getter; exercises source selection, atomic
CONFIG commit and read-only resume. No callback is connected by this milestone.
"""
import functools
import struct

import pytest

from test_frontier_modes_engine import A, CTX, END, SAVE, STACK, WORK, call, machine, work_address
import modes as m
import patch as fp
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE

FIELD, SOURCES = 0x10000000, 0x11000000
PARTY, BOX, DESCRIPTOR = SOURCES, SOURCES + 0x100, WORK + 0x2C


@functools.lru_cache(maxsize=1)
def field():
    return fp.battle_cro()[fp.FIELD_CRO], m.assemble_selection()[1]


def enrollment(route=2, mode=1, flags=1, box=0, levels=(73, 41, 7),
               slots=None, count=None, config=0x149, rank=0, kind=None, descriptor=DESCRIPTOR,
               null_slot=None, setrank=None):
    uc, _ = machine(route, config)
    data, symbols = field()
    uc.mem_map(FIELD, (len(data) + 0xFFF) & ~0xFFF)
    uc.mem_write(FIELD, data)
    uc.mem_map(SOURCES, 0x1000)

    def put(at, value):
        uc.mem_write(at, struct.pack('<I', value))

    put(CTX + 0x100 + 0x14, PARTY)
    put(WORK + 0xB84, BOX)
    uc.mem_write(WORK + 0x838, bytes([rank, mode // 2 if kind is None and mode < 4 else kind or 0]))
    uc.mem_write(DESCRIPTOR, bytes([box]))
    slots = list(range(len(levels))) if slots is None else slots
    put(DESCRIPTOR + 0x1C, len(slots) if count is None else count)
    for i, slot in enumerate(slots):
        put(DESCRIPTOR + 4 + 4 * i, slot & 0xFFFFFFFF)
    if setrank is not None:
        for work, slot in zip(m.DOME_ENTRANTS, slots):
            uc.mem_write(work_address(work), struct.pack('<H', slot & 0xFFFF))
        # The previous Dome battle has reduced the live descriptor to two.
        put(DESCRIPTOR + 0x1C, 2)
        uc.mem_write(DESCRIPTOR, b'\x01')
    source = BOX if box == 1 else PARTY
    for owner in (PARTY, BOX):
        for i in range(6):
            param = owner + 0x200 + 4 * i
            put(owner + 4 * i, 0 if null_slot == i else param)
            # The other source is deliberately all 100: scanning the full
            # party, instead of the effective selection, gives a wrong max.
            put(param, levels[i] if owner == source and i < len(levels) else 100)
    writes, getters = [], []

    def observe_write(uc, access, at, size, value, _):
        if not STACK - 0x10000 <= at < STACK:
            writes.append((at, size, value))

    def level_getter(uc, at, size, _):
        if at != m.SELECTION_CODE['CODE_GET_LEVEL']:
            return
        assert uc.reg_read(A.UC_ARM_REG_SP) % 8 == 0
        param = uc.reg_read(A.UC_ARM_REG_R0)
        getters.append(param)
        uc.reg_write(A.UC_ARM_REG_R0, struct.unpack('<I', uc.mem_read(param, 4))[0])
        uc.reg_write(A.UC_ARM_REG_PC, uc.reg_read(A.UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    uc.hook_add(UC_HOOK_CODE, level_getter)
    result = (call(uc, FIELD + symbols['mode_setrank'], r0=WORK, r1=0, r4=setrank)
              if setrank is not None else
              call(uc, FIELD + symbols['mode_register'], r0=WORK, r1=mode, r2=descriptor, r3=flags))
    return result, writes, getters


@pytest.mark.parametrize('route', range(1, 8))
@pytest.mark.parametrize('mode', range(4))
@pytest.mark.parametrize('box', (0, 1))
@pytest.mark.parametrize('levels', ((50, 41, 7, 60), (73, 41, 7, 60), (5, 6, 7, 100)))
def test_new_native_registration_uses_effective_inscription(route, mode, box, levels):
    levels = levels[:4 if mode >= 2 else 3]
    result, writes, getters = enrollment(route, mode, box=box, levels=levels)
    if not m.valid(route, mode):
        assert (result, writes, getters) == (0xFFFFFFFF, [], [])
        return
    expected = m.selection_config(route, mode, levels)
    assert result == expected
    assert writes == [(work_address(m.CONFIG[route]), 2, expected)]
    assert len(getters) == (0 if route == 1 else len(levels))
    owner = BOX if box else PARTY
    assert getters == ([] if route == 1 else [owner + 0x200 + 4 * i for i in range(len(levels))])


@pytest.mark.parametrize('route', (0, 1, 2, 5, 7, 8, 65535))
@pytest.mark.parametrize('config', (0, 50, 0x13C, 0x149, 0x164, 0x232, 0x349, 0x100, 0x400, 0xFFFF))
@pytest.mark.parametrize('mode', (0, 1, 2, 3, 4))
def test_resume_is_read_only_and_never_revisits_any_source(route, config, mode):
    result, writes, getters = enrollment(route, mode, flags=3, config=config, descriptor=0xFFFFFFFF)
    decoded = m.unpack_config(route, config)
    expected = config if decoded is not None and decoded[0] == mode else 0xFFFFFFFF
    assert result == expected
    assert writes == getters == []


@pytest.mark.parametrize('flags', (0, 2, 4, 5, 0xFFFFFFFF))
def test_cancel_or_unknown_flags_cannot_write_or_dereference_selection(flags):
    assert enrollment(flags=flags, descriptor=0xFFFFFFFF) == (0xFFFFFFFF, [], [])


@pytest.mark.parametrize('kwargs', (
    {'box': 2}, {'count': 0}, {'count': 2}, {'count': 4},
    {'slots': (0, 0, 2)}, {'slots': (0, 1, 6)}, {'slots': (0, 1, -1)},
    {'levels': (73, 41, 0)}, {'levels': (73, 41, 101)},
    {'rank': 1}, {'kind': 1}, {'mode': 4}, {'descriptor': 0}, {'null_slot': 2},
))
def test_invalid_selection_leaves_config_untouched_even_if_last_member_fails(kwargs):
    result, writes, _ = enrollment(**kwargs)
    assert result == 0xFFFFFFFF and writes == []


def test_nonconsecutive_selection_ignores_high_unselected_members():
    result, writes, getters = enrollment(levels=(73, 41, 100, 7), slots=(0, 1, 3))
    assert result == 0x149 and len(writes) == 1 and len(getters) == 3


def test_dome_descriptor_includes_third_entrant_before_two_fighter_reduction():
    assert enrollment(route=5, levels=(41, 7, 99))[0] == 0x163
    assert enrollment(route=5, levels=(41, 7), count=2)[:2] == (0xFFFFFFFF, [])


@pytest.mark.parametrize('levels,expected', [((41, 7, 99), 0x163), ((41, 7, 50), 0x13C),
                                          ((73, 55, 41), 0x149), ((41, 7, 100), 0x164)])
def test_dome_setrank_builds_three_entrant_descriptor_without_live_work_write(levels, expected):
    result, writes, getters = enrollment(route=5, levels=levels, setrank=m.REGISTER + 1)
    assert result == expected and len(getters) == 3
    assert writes == [(work_address(m.CONFIG[5]), 2, expected)]


def test_dome_setrank_resume_keeps_l_without_reading_replacement_entry():
    assert enrollment(route=5, levels=(100, 99, 98), setrank=m.REGISTER + 5)[0:3] == (0x149, [], [])


@pytest.mark.parametrize('slots', ((0, 0, 2), (0, 1, 6)))
def test_dome_setrank_invalid_third_entrant_cannot_commit(slots):
    assert enrollment(route=5, slots=slots, setrank=m.REGISTER + 1)[:2] == (0xFFFFFFFF, [])


def test_factory_never_reads_descriptor_or_real_party():
    for mode in range(4):
        result, writes, getters = enrollment(route=1, mode=mode, descriptor=0xFFFFFFFF)
        assert result == m.selection_config(1, mode, ())
        assert writes == [(work_address(m.CONFIG[1]), 2, result)] and getters == []


def test_field_payload_is_guarded_rehashed_and_only_the_setrank_call_is_redirected():
    from build_patch import cro_hashes
    data, _ = field()
    blob, _ = m.assemble_selection()
    assert data[m.FIELD_AT:m.FIELD_AT + len(blob)] == blob
    assert len(blob) <= m.FIELD_END - m.FIELD_AT
    assert b''.join(cro_hashes(data)) == data[:0x80]
    import brains
    _, symbols = m.assemble_selection()
    assert m.cro_writes() == [dict(offset=m.FIELD_AT, before=bytes(len(blob)).hex(), after=blob.hex()),
                              dict(offset=m.SETRANK_SITE, before=brains.bl(m.SETRANK_SITE, m.SETRANK_THUNK).hex(),
                                   after=brains.bl(m.SETRANK_SITE, symbols['mode_setrank']).hex())]
    assert data[m.SETRANK_SITE:m.SETRANK_SITE + 4] == brains.bl(m.SETRANK_SITE, symbols['mode_setrank'])
    # the native keeps the script argument in r4 across the call (0x95e44 uxth r4, r0; pops it at 0x95e68)
    raw = (fp.MOD_ROMFS / fp.FIELD_CRO).read_bytes()
    assert raw[0x95E44:0x95E48] == bytes.fromhex('7040ffe6') and raw[0x95E64:0x95E6C] == bytes.fromhex('0000a0e31080bde8')
    code = fp.build()[0]
    original = fp.REPOLISHED.read_bytes()
    assert code[0x1D8968 - fp.BASE:0x1D8978 - fp.BASE] == original[0x1D8968 - fp.BASE:0x1D8978 - fp.BASE]



@pytest.mark.parametrize('arg, mode, flags', [(0x100, 0, 1), (0x101, 1, 1), (0x105, 1, 3), (0x104, 0, 3),
                                               (0x103, 3, 1)])
def test_setrank_argument_maps_to_registration(arg, mode, flags):
    """SetRank(0x100 + M + 4*resume) -> mode_register(work, M, work+0x2c, accepted | resume<<1)."""
    seen = []
    data, symbols = field()

    def run():
        uc, _ = machine(2, 0x149)
        uc.mem_map(FIELD, (len(data) + 0xFFF) & ~0xFFF)
        uc.mem_write(FIELD, data)

        def stop(uc, at, size, _):
            if at == FIELD + symbols['mode_register']:
                seen.append(tuple(uc.reg_read(getattr(A, f'UC_ARM_REG_R{n}')) for n in range(4)))
                uc.reg_write(A.UC_ARM_REG_R0, 0x1234)
                uc.reg_write(A.UC_ARM_REG_PC, uc.reg_read(A.UC_ARM_REG_LR))
            elif at == FIELD + m.SETRANK_THUNK:
                seen.append('retail')
                uc.reg_write(A.UC_ARM_REG_PC, uc.reg_read(A.UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE, stop)
        return call(uc, FIELD + symbols['mode_setrank'], r0=WORK, r1=1, r4=arg)
    run()
    assert seen == [(WORK, mode, WORK + 0x2C, flags)]


@pytest.mark.parametrize('arg, expected', [(0, ['retail']), (1, ['retail']), (0xFF, ['retail']), (0x108, []),
                                           (0xFFFF, [])])
def test_setrank_keeps_retail_and_ignores_unknown_arguments(arg, expected):
    seen = []
    data, symbols = field()
    uc, _ = machine(2, 0x149)
    uc.mem_map(FIELD, (len(data) + 0xFFF) & ~0xFFF)
    uc.mem_write(FIELD, data)

    def stop(uc, at, size, _):
        if at == FIELD + symbols['mode_register']:
            seen.append('register')
        elif at == FIELD + m.SETRANK_THUNK:
            seen.append('retail')
            assert uc.reg_read(A.UC_ARM_REG_R0) == WORK and uc.reg_read(A.UC_ARM_REG_R1) == 1
            uc.reg_write(A.UC_ARM_REG_PC, uc.reg_read(A.UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE, stop)
    call(uc, FIELD + symbols['mode_setrank'], r0=WORK, r1=1, r4=arg)
    assert seen == expected
