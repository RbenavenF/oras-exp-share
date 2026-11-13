"""F9 preparation: allocation, format rewards and real retail ARM dispatch.

Unicorn validates raw callback packets, not the selector UI or save persistence
in Azahar. No new mode is enabled by this milestone.
"""
import importlib.util
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import modes as m  # noqa: E402
import modes_audit as audit  # noqa: E402
import patch  # noqa: E402


def test_allocation_is_disjoint_from_legacy_and_does_not_consume_holes():
    assert len(m.RESERVED) == len(set(m.RESERVED)) == 42
    assert not set(m.RESERVED) & (audit.LEGACY | audit.EXCLUDED)
    assert len(m.NEW_BANKS) == 11
    assert all(m.bank(r, 0) == (s, s + 2) for r, (_, s) in patch.STREAK_ROUTES.items())
    assert len({w for r in range(1, 8) for mode in range(4) for w in (m.bank(r, mode) or ())}) == 36
    with pytest.raises(ValueError, match='collision'):
        audit.check_allocation({m.FACTORY_SET3: {'fake retail use'}})


@pytest.mark.parametrize('route', (0, 1, 2, 3, 4, 5, 6, 7, 8, 65535))
@pytest.mark.parametrize('mode', (0, 1, 2, 3, 4, 65535))
def test_bank_resolution_matrix(route, mode):
    expected = 1 <= route <= 7 and (mode in (0, 1) or (route <= 2 and mode in (2, 3)))
    assert m.valid(route, mode) == expected
    assert (m.bank(route, mode) is not None) == expected


@pytest.mark.parametrize('route', (1, 2))
def test_pb_formats_open_levels_and_saturation(route):
    singles = [m.battle_points(route, 0, r) for r in range(1, 31)]
    doubles = [m.battle_points(route, 2, r) for r in range(1, 31)]
    assert doubles == [min(15, n + 1) for n in singles]
    assert doubles == [m.battle_points(route, 3, r) for r in range(1, 31)]
    assert singles == [m.battle_points(route, 1, r) for r in range(1, 31)]
    assert m.battle_points(route, 2, 65535) == 15
    assert m.battle_points(route, 0, 65535, brain=True) == 25
    for args in ((route, 2, 1, True), (route, 0, 0), (0, 0, 1), (3, 2, 1), (route, 4, 1)):
        with pytest.raises(ValueError):
            m.battle_points(*args)


def test_local_allocation_and_current_space():
    if not patch.REPOLISHED.exists() or not (patch.MOD_ROMFS / patch.FIELD_CRO).exists():
        pytest.skip('Local baseline and v0.5 required')
    import ids
    used, _, _ = ids.scan()
    candidates = audit.check_allocation(used)
    assert candidates - set(m.RESERVED) == {16399}
    space = audit.measure_space()
    assert space['code']['free'] >= 0
    assert space['code']['luma_reserved'] == [0x579604, 0x579804]
    assert space['brains']['end'] <= m.FIELD_AT
    assert space['f9_reserved']['size'] == 1536


def test_fixed_reference_all_thirty_rows_when_available():
    repo = Path('/tmp/frontier-cerebros-pokeemerald')
    if not (repo / '.git').exists():
        pytest.skip('Optional local pinned pokeemerald reference')
    spec = importlib.util.spec_from_file_location('modes_reference_bp',
                                                ROOT / 'frontier/probes/modos/reference_bp.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify(repo)['rows'] == 30


@pytest.fixture(scope='module')
def retail():
    if not patch.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    from formats import sha256
    assert sha256(patch.REPOLISHED) == patch.HASHES[patch.REPOLISHED]
    return patch.REPOLISHED.read_bytes()


def vm(code):
    pytest.importorskip('unicorn')
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn import arm_const as a
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(patch.BASE, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(patch.BASE, code)
    uc.mem_map(0x8000000, 0x40000)
    uc.reg_write(a.UC_ARM_REG_SP, 0x803F000)
    uc.reg_write(a.UC_ARM_REG_LR, 0x9000000)
    return uc, a


@pytest.mark.parametrize('kind', (0, 1))
@pytest.mark.parametrize('rank', (0, 1, 2, 255))
@pytest.mark.parametrize('count', (0, 9998, 9999))
def test_real_retail_singles_doubles_accessors_and_limits(retail, kind, rank, count):
    uc, a = vm(retail)
    base = 0x8000000
    current = base + 0x1C4 + 8 * kind + 2 * bool(rank)
    record = current + 4
    uc.mem_write(current, struct.pack('<H', count))
    uc.mem_write(record, struct.pack('<H', count))
    tables = ((0x45CDB0, 0x45CDC4, 0x45CDFC), (0x45CF00, 0x45CF14, 0x45CF24),
              (0x45CFA4, 0x45CFB8, 0x45CFC8), (0x45D028, 0x45D03C, 0x45D04C))
    for table, single, double in tables:
        assert struct.unpack_from('<2I', retail, table - patch.BASE) == (single, double)
    assert patch.word(retail, 0x45CDFC) == 0xE0801082
    for site in (0x45CF24, 0x45CFC8, 0x45D04C):
        assert patch.word(retail, site) == 0xE0800082

    def call(entry):
        for reg, value in ((a.UC_ARM_REG_R0, base), (a.UC_ARM_REG_R1, kind),
                           (a.UC_ARM_REG_R2, rank), (a.UC_ARM_REG_LR, 0x9000000)):
            uc.reg_write(reg, value)
        uc.emu_start(entry, 0x9000000, count=1000)
        assert uc.reg_read(a.UC_ARM_REG_PC) == 0x9000000
        return uc.reg_read(a.UC_ARM_REG_R0)

    assert call(0x45CEE8) == call(0x45D010) == count
    before = bytes(uc.mem_read(base, 0x200))
    call(0x45CD98)
    expected = min(9999, count + 1)
    assert call(0x45CEE8) == call(0x45D010) == expected
    after = bytes(uc.mem_read(base, 0x200))
    allowed = {offset + k for offset in (current - base, record - base) for k in range(2)}
    assert all(i in allowed for i, (x, y) in enumerate(zip(before, after)) if x != y)
    call(0x45CF8C)
    assert call(0x45CEE8) == 0
    assert call(0x45D010) == expected


@pytest.mark.parametrize('raw_rank', (0, 1, 2))
def test_setrank_really_does_not_validate(retail, raw_rank):
    uc, a = vm(retail)
    uc.reg_write(a.UC_ARM_REG_R0, 0x8000000)
    uc.reg_write(a.UC_ARM_REG_R1, raw_rank)
    uc.emu_start(0x1E567C, 0x9000000, count=10)
    assert bytes(uc.mem_read(0x8000838, 1)) == bytes([raw_rank])


@pytest.mark.parametrize('kind', (0, 1))
@pytest.mark.parametrize('selector_rank', (1, 2))
@pytest.mark.parametrize('packet_status,accepted', ((0, 0), (1, 0), (1, 1)))
def test_selector_callback_packets_and_auxiliary_x(retail, kind, selector_rank, packet_status, accepted):
    """Execute the real callback and configuration function with synthetic packets.

    status=0 leaves output works untouched; status=1 + acceptance=0 writes zeros
    without changing facility configuration. UI mapping remains unmeasured.
    """
    from formats import sha256
    from unicorn import UC_HOOK_CODE
    field_path = ROOT / 'baseline/oras/repolished/romfs/DllField.cro'
    assert sha256(field_path) == '23248ab0d170c2cc2b20d2bd4e7a70aeb4f57485b69b7b3d1b542958546c1455'
    uc, a = vm(retail)
    field_base = 0x10000000
    raw = field_path.read_bytes()
    uc.mem_map(field_base, (len(raw) + 0xFFF) & ~0xFFF)
    uc.mem_write(field_base, raw)
    task, app, holder, facility, ctx, engine, game, save = [0x8000000 + i * 0x1000 for i in range(8)]
    put = lambda at, value: uc.mem_write(at, struct.pack('<I', value))
    put(task + 4, app)
    uc.mem_write(task + 0xC, struct.pack('<3H', 0x800C, 0x800D, 0x800E))
    uc.mem_write(app, bytes([packet_status]))
    # +8 type, +9 selector rank encoding, +a accepted, +b auxiliary X.
    uc.mem_write(app + 8, bytes([kind, selector_rank, accepted, 7]))
    put(holder + 0x64, facility)
    put(ctx + 0x90, engine)
    put(facility + 0xB78, game)
    put(game + 0x1C, game + 4)
    put(game + 4, save)
    uc.mem_write(facility + 0x838, b'\xCC\xCC\xCC')
    writes, configurations = [], []

    def intercept(uc, address, size, _):
        r0, r1, r2, r3 = (uc.reg_read(reg) for reg in
                          (a.UC_ARM_REG_R0, a.UC_ARM_REG_R1, a.UC_ARM_REG_R2, a.UC_ARM_REG_R3))
        thunk = address - field_base
        if thunk == 0x3870:
            configurations.append((r0, r1, r2, r3))
            uc.reg_write(a.UC_ARM_REG_PC, 0x1E5684)
            return
        if thunk in (0x1040, 0x13D8):
            uc.reg_write(a.UC_ARM_REG_R0, ctx)
        elif thunk == 0x2898:
            writes.append((r1, r2))
        elif thunk != 0x2D8:
            return
        uc.reg_write(a.UC_ARM_REG_PC, uc.reg_read(a.UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, intercept)
    uc.reg_write(a.UC_ARM_REG_R0, task)
    uc.reg_write(a.UC_ARM_REG_R1, holder)
    uc.emu_start(field_base + 0x96B00, 0x9000000, count=1000)
    assert uc.reg_read(a.UC_ARM_REG_PC) == 0x9000000
    if packet_status == 0:
        assert writes == configurations == []
    elif accepted == 0:
        assert writes == [(0x800D, 0), (0x800E, 0), (0x800C, 0)]
        assert configurations == []
    else:
        assert writes == [(0x800D, kind), (0x800E, 7), (0x800C, 1)]
        assert configurations == [(facility, selector_rank, kind, 0)]
        assert bytes(uc.mem_read(facility + 0x838, 3)) == bytes([selector_rank - 1, kind, selector_rank])
        assert bytes(uc.mem_read(save + patch.MAISON_BASE + 0x1F4, 1)) == bytes([selector_rank - 1])
    if not configurations:
        assert bytes(uc.mem_read(facility + 0x838, 3)) == b'\xCC\xCC\xCC'
