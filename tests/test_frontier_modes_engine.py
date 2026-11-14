"""F9 engine (frontier/asm/modes.s) run in Unicorn on the built code.bin: the (route, M) streak banks behind the real
Maison accessors, the Open Level of the player's party tail and of the rivals, and the Tower reception's mode check
(pawn VM). Models the expected banks from frontier/modes.py; it is not a game test (Azahar: reports/modos-base.md).
"""
import functools
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
unicorn = pytest.importorskip('unicorn')
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

import modes as m  # noqa: E402
import patch as fp  # noqa: E402

SAVE, STACK, WORK, CTX, END = 0x0D000000, 0x09000000, 0x08000000, 0x0C000000, 0xDEAD0000
MAISON = SAVE + fp.MAISON_BASE
ENTRY = {'inc': 0x45CD98, 'get': 0x45CEE8, 'clear': 0x45CF8C, 'record': 0x45D010}


@functools.lru_cache(maxsize=None)
def built():
    if not fp.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    code, _, _ = fp.build()
    return code, fp.assemble()[1]


def work_address(number):
    return SAVE + fp.SAVE_WORKS + 2 * (number - 0x4000)


def machine(route, config=None, works=None):
    code, symbols = built()
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(fp.BASE, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(fp.BASE, code)
    for base, size in ((SAVE, 0x20000), (STACK - 0x10000, 0x10000), (WORK, 0x1000), (CTX, 0x1000), (END, 0x1000)):
        uc.mem_map(base, size)
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', CTX + 0x100))
    uc.mem_write(CTX + 0x100, struct.pack('<I', SAVE))
    uc.mem_write(work_address(fp.WORK_ROUTE), struct.pack('<H', route))
    if config is not None and route in m.CONFIG:
        uc.mem_write(work_address(m.CONFIG[route]), struct.pack('<H', config))
    if route in fp.STREAK_ROUTES:
        active = fp.ACTIVE_WORK[fp.STREAK_ROUTES[route][0]]
        uc.mem_write(work_address(active), struct.pack('<H', 1))
    for number, value in (works or {}).items():
        uc.mem_write(work_address(number), struct.pack('<H', value))
    uc.reg_write(A.UC_ARM_REG_SP, STACK - 0x100)
    return uc, symbols


def call(uc, entry, **regs):
    for name, value in {'lr': END, **regs}.items():
        uc.reg_write(getattr(A, f'UC_ARM_REG_{name.upper()}'), value)
    keep = [uc.reg_read(getattr(A, f'UC_ARM_REG_R{n}')) for n in range(4, 12)]
    uc.emu_start(entry, END, count=2000)
    assert uc.reg_read(A.UC_ARM_REG_PC) == END
    assert uc.reg_read(A.UC_ARM_REG_SP) == STACK - 0x100
    assert keep == [uc.reg_read(getattr(A, f'UC_ARM_REG_R{n}')) for n in range(4, 12)]
    return uc.reg_read(A.UC_ARM_REG_R0)


def every_bank():
    banks = {w for r in range(1, 8) for mode in range(4) for w in (m.bank(r, mode) or ())}
    return sorted(banks | set(m.CONFIG.values()) | {fp.WORK_ROUTE})


def expected_slot(route, config, kind, rank):
    """(streak, record) addresses the accessors must use: the mode's bank or the Maison's retail slot."""
    retail = MAISON + 0x1C4 + 8 * kind + 2 * bool(rank)
    unpacked = m.unpack_config(route, config) if route in m.CONFIG else None
    mode = config >> 8 if 0 <= config < 0x400 else None
    if rank or unpacked is None or mode >> 1 != kind:
        return retail, retail + 4
    assert unpacked[0] == mode
    streak, record = m.bank(route, mode)
    return work_address(streak), work_address(record)


CONFIGS = (0, 0x32, m.pack_config(2, 1, 73), m.pack_config(1, 1, 100), m.pack_config(2, 2, 50),
           m.pack_config(2, 3, 73), 0x400, 0x0500, 0xFFFF, 0x1FF, 0x100, 0x13B, 0x165, 0x31, 0x233, 0x300)


@pytest.mark.parametrize('route', (0, 1, 2, 3, 7, 8, 0xFFFF))
@pytest.mark.parametrize('config', CONFIGS)
@pytest.mark.parametrize('kind', (0, 1))
@pytest.mark.parametrize('rank', (0, 1, 2))
def test_accessors_use_the_mode_bank_or_the_retail_slot(route, config, kind, rank):
    streak, record = expected_slot(route, config, kind, rank)
    uc, _ = machine(route, config)
    fill = {a: 100 + i for i, a in enumerate(sorted({work_address(w) for w in every_bank()} - {
        work_address(fp.WORK_ROUTE), *(work_address(c) for c in m.CONFIG.values())}))}
    fill.update({MAISON + 0x1C4 + 2 * k: 200 + k for k in range(8)})
    fill.update({streak: 30, record: 40})
    for address, value in fill.items():
        uc.mem_write(address, struct.pack('<H', value))
    snapshot = lambda: (bytes(uc.mem_read(SAVE + fp.SAVE_WORKS, 0x400)), bytes(uc.mem_read(MAISON, 0x200)))
    args = dict(r0=MAISON, r1=kind, r2=rank)
    assert call(uc, ENTRY['get'], **args) == 30
    assert call(uc, ENTRY['record'], **args) == 40
    before = snapshot()
    call(uc, ENTRY['inc'], **args)
    assert call(uc, ENTRY['get'], **args) == 31 and call(uc, ENTRY['record'], **args) == 40
    for _ in range(9):
        call(uc, ENTRY['inc'], **args)
    assert call(uc, ENTRY['get'], **args) == 40 and call(uc, ENTRY['record'], **args) == 40
    call(uc, ENTRY['inc'], **args)
    assert call(uc, ENTRY['get'], **args) == 41 and call(uc, ENTRY['record'], **args) == 41   # new record
    call(uc, ENTRY['clear'], **args)
    assert call(uc, ENTRY['get'], **args) == 0 and call(uc, ENTRY['record'], **args) == 41
    after = snapshot()
    changed = {SAVE + fp.SAVE_WORKS + i for i, (x, y) in enumerate(zip(before[0], after[0])) if x != y}
    changed |= {MAISON + i for i, (x, y) in enumerate(zip(before[1], after[1])) if x != y}
    assert changed <= {streak, streak + 1, record, record + 1}


@pytest.mark.parametrize('count', (9998, 9999))
def test_mode_bank_saturates_as_retail(count):
    streak, record = m.bank(2, m.SINGLE_OPEN)
    uc, _ = machine(2, m.pack_config(2, 1, 73), {streak: count, record: count})
    call(uc, ENTRY['inc'], r0=MAISON, r1=0, r2=0)
    assert call(uc, ENTRY['get'], r0=MAISON, r1=0, r2=0) == call(uc, ENTRY['record'], r0=MAISON, r1=0, r2=0) == 9999


def test_old_saves_keep_their_level_50_streaks():
    """CONFIG 0 (a save made before F9) on every route: the M=0 works, S and S+2, as before."""
    for route, (_, streak) in fp.STREAK_ROUTES.items():
        uc, _ = machine(route, 0, {streak: 12, streak + 2: 34})
        assert call(uc, ENTRY['get'], r0=MAISON, r1=0, r2=0) == 12
        assert call(uc, ENTRY['record'], r0=MAISON, r1=0, r2=0) == 34


def test_reclaimed_increment_has_only_the_redirected_table_reference():
    """Fixed input: aligned pointers and direct ARM B/BL only; not a proof about arbitrary computed jumps."""
    if not fp.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    raw = fp.REPOLISHED.read_bytes()
    start, end = fp.MODE_LIVE, fp.MODE_LIVE + 4 * len(fp.MODE_LIVE_BEFORE)
    pointers, branches = [], []
    for i, (word,) in enumerate(struct.iter_unpack('<I', raw)):
        va = fp.BASE + 4 * i
        if start <= word < end:
            pointers.append((va, word))
        if word >> 28 != 15 and word & 0x0E000000 == 0x0A000000:
            delta = word & 0xFFFFFF
            delta -= (delta & 0x800000) << 1
            target = va + 8 + 4 * delta
            if start <= target < end and not start <= va < end:
                branches.append((va, target))
    assert pointers == [(0x45CDB4, start)] and branches == []
    code, symbols = built()
    assert struct.unpack_from('<I', code, 0x45CDB4 - fp.BASE)[0] == symbols['streak_inc']
    assert len(fp.mode_live_code(symbols)) == 40 <= end - start


@pytest.mark.parametrize('route', range(1, 8))
@pytest.mark.parametrize('active', (0, 1, 31, 65535))
def test_level_hooks_require_active_but_loss_still_clears_its_bank(route, active):
    config = m.pack_config(route, m.SINGLE_OPEN, 100 if route == 1 else 73)
    streak, record = m.bank(route, m.SINGLE_OPEN)
    legacy, legacy_record = m.bank(route, m.SINGLE_50)
    active_work = fp.ACTIVE_WORK[fp.STREAK_ROUTES[route][0]]
    uc, symbols = machine(route, config, {active_work: active, streak: 6, record: 12,
                                          legacy: 9, legacy_record: 20})
    assert call(uc, symbols['mode_level'], r0=WORK) == (config & 255 if active else 50)
    call(uc, symbols['mode_cap'], r0=100, r6=WORK)
    assert bool(uc.reg_read(A.UC_ARM_REG_CPSR) & (1 << 30)) == bool(active)
    if not active:
        assert struct.unpack('<H', uc.mem_read(work_address(m.CONFIG[route]), 2))[0] == config
    # LOST clears ACTIVE before GetMyWinCount and ClearWinCount: these must still use the Open bank.
    uc.mem_write(work_address(active_work), b'\0\0')
    assert call(uc, ENTRY['get'], r0=MAISON, r1=0, r2=0) == 6
    call(uc, ENTRY['clear'], r0=MAISON, r1=0, r2=0)
    assert call(uc, ENTRY['get'], r0=MAISON, r1=0, r2=0) == 0
    assert call(uc, ENTRY['record'], r0=MAISON, r1=0, r2=0) == 12
    assert struct.unpack('<H', uc.mem_read(work_address(legacy), 2))[0] == 9
    assert struct.unpack('<H', uc.mem_read(work_address(legacy_record), 2))[0] == 20


@pytest.mark.parametrize('config, level', [
    (0, 50), (0x32, 50), (m.pack_config(2, 1, 60), 60), (m.pack_config(2, 1, 73), 73), (m.pack_config(1, 1, 100), 100),
    (m.pack_config(2, 2, 50), 50), (m.pack_config(2, 3, 73), 73), (0x100, 50), (0x1FF, 50), (0x400, 50),
    (0xFFFF, 50)])
@pytest.mark.parametrize('route', (1, 2))
def test_mode_level(route, config, level):
    uc, symbols = machine(route, config)
    expected = m.unpack_config(route, config)
    assert call(uc, symbols['mode_level'], r0=WORK) == (expected[1] if expected else 50)
    uc, symbols = machine(0, None, {m.CONFIG[route]: config})
    assert call(uc, symbols['mode_level'], r0=WORK) == 50          # no route: retail


def cap(route, config, levels, r7=0):
    """Runs mode_cap for each member level from the party tail; (skips, CONFIG after)."""
    uc, symbols = machine(route, config)
    skips = []
    for level in levels:
        uc.reg_write(A.UC_ARM_REG_R6, WORK)
        call(uc, symbols['mode_cap'], r0=level, r6=WORK)
        cpsr = uc.reg_read(A.UC_ARM_REG_CPSR)
        z, n, v = cpsr >> 30 & 1, cpsr >> 31 & 1, cpsr >> 28 & 1
        le = z or n != v
        skips.append(bool(le and r7 == 0))     # cmple r7, #0; beq keep
    return skips, struct.unpack('<H', uc.mem_read(work_address(m.CONFIG[route]), 2))[0]


@pytest.mark.parametrize('levels, fixed', [((73, 55, 41), 73), ((41, 30, 12), 60), ((100, 99, 5), 100),
                                           ((60,), 60), ((61, 50), 61)])
def test_open_level_keeps_levels_and_fixes_l_from_the_selection(levels, fixed):
    skips, config = cap(2, m.pack_config(2, 1, 60), levels)
    assert skips == [True] * len(levels) and m.unpack_config(2, config) == (1, fixed)
    again, config2 = cap(2, config, (12, 13, 14))          # a later battle never lowers L
    assert again == [True] * 3 and config2 == config
    uc, symbols = machine(2, config)
    assert call(uc, symbols['mode_level'], r0=WORK) == fixed


@pytest.mark.parametrize('route, config', [(0, 0), (2, 0), (2, 0x32), (2, m.pack_config(2, 2, 50)), (8, 0),
                                           (2, 0xFFFF), (2, 0x400), (2, 0x100), (2, 0x1FF), (2, 0x13B),
                                           (2, 0x165), (1, 0x149), (1, 0x13C), (2, 0x31), (2, 0x233)])
def test_level_50_modes_keep_the_retail_cap(route, config):
    skips, after = cap(route, config, (73, 50, 49, 5)) if route in m.CONFIG else (None, None)
    if skips is None:
        uc, symbols = machine(route)
        skips = []
        for level in (73, 50, 49, 5):
            call(uc, symbols['mode_cap'], r0=level, r6=WORK)
            cpsr = uc.reg_read(A.UC_ARM_REG_CPSR)
            skips.append(bool((cpsr >> 30 & 1) or (cpsr >> 31 & 1) != (cpsr >> 28 & 1)))
    else:
        assert after == config                              # untouched
    assert skips == [False, True, True, True]               # above 50: lowered to 50 by the retail tail


def test_factory_open_level_is_100_for_rentals_and_rivals():
    config = m.pack_config(1, 1, 100)
    skips, after = cap(1, config, (100, 100, 100))
    assert skips == [True] * 3 and after == config
    uc, symbols = machine(1, config)
    assert call(uc, symbols['mode_level'], r0=WORK) == 100


def run_rival_level(route, config, wild=0):
    """pike_level at the rival builder's `mov r1, #50` (fp = facility work): r1 = the level; r2, r3 kept."""
    uc, symbols = machine(route, config, {fp.PIKE_WILD: wild})
    uc.reg_write(A.UC_ARM_REG_FP, WORK)
    call(uc, symbols['pike_level'], r2=0x22, r3=0x33, fp=WORK)
    assert uc.reg_read(A.UC_ARM_REG_R2) == 0x22 and uc.reg_read(A.UC_ARM_REG_R3) == 0x33
    return uc.reg_read(A.UC_ARM_REG_R1)


@pytest.mark.parametrize('route, config, wild, level', [
    (0, 0, 0, 50), (2, 0, 0, 50), (2, m.pack_config(2, 1, 73), 0, 73), (5, m.pack_config(5, 1, 60), 0, 60),
    (6, 0, fp.PIKE_WILD_FIRST, 46), (6, 0, fp.PIKE_WILD_FAR, 45),
    (6, m.pack_config(6, 1, 73), fp.PIKE_WILD_FIRST, 69), (6, m.pack_config(6, 1, 73), fp.PIKE_WILD_FAR, 68),
    (6, m.pack_config(6, 1, 100), 0, 100), (1, m.pack_config(1, 1, 100), 0, 100)])
def test_rival_level_composes_open_level_and_pike_wild_rooms(route, config, wild, level):
    assert run_rival_level(route, config, wild) == level


def test_rentals_use_the_mode_level():
    """The Factory's rental MAKE_PARAM gets mode_level: 50 in Level 50, 100 in Open Level."""
    sys.path.insert(0, str(ROOT / 'tests'))
    import test_frontier_patch as tp
    code, _ = built()
    for config, level in ((0, 50), (m.pack_config(1, 1, 100), 100)):
        _, calls, _ = tp.run(code, 3, 21, sets=(0x10, 0x8011, 0x412), route=1, works={m.CONFIG[1]: config})
        assert [c[2] for c in calls if c[0] == 'make'] == [level] * 3


def test_tower_reception_new_and_resumed_modes():
    """Tower reception (pawn VM): a new challenge resets CONFIG to 0 (Level 50, no menu yet); a paused one resumes
    with its persisted Singles mode; a corrupt or Doubles CONFIG starts a new Level 50 challenge."""
    sys.path.insert(0, str(ROOT / 'tests'))
    import test_frontier_tower as tt
    import overlay
    import tower
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    files, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = tower.tower_program(retail)
    built_script = (files, retail, program.build_script(f'L{retail.main:x}'), program.layout(), None, None)
    config = m.CONFIG[tower.ROUTE]

    def run(active, value, streak=6):
        result, works, log = tt.reception(built_script, tower_active=active, tower_streak=streak, streak_after=7,
                                          extra={config: value})
        seen = next(e for e in log if e[0] == 'challenge')[2]
        return seen[config], seen[tower.STREAK]

    assert run(0, m.pack_config(2, 1, 73)) == (0, 0)                     # new: Level 50, streak from 0
    for value in (0, 0x32, m.pack_config(2, 1, 60), m.pack_config(2, 1, 73), m.pack_config(2, 1, 100)):
        assert run(1, value) == (value, 6)                                 # resumed in its mode
    for value in (m.pack_config(2, 2, 50), m.pack_config(2, 3, 73), 0x13B, 0x165, 0x31, 0xFFFF, 0x100):
        assert run(1, value) == (0, 0)                                     # not resumable: new Level 50
