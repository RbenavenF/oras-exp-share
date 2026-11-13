"""F7-CUEVA-LUMA: our code.bin hooks must survive what Luma3DS writes at the start of the cave on a console.

frontier/luma.py has the payload measured on the user's 3DS (276 bytes at 0x579604 and two branches to it). These
tests build the final code.bin, put Luma's payload on top and check that no hook of ours points into Luma's reserve;
test_frontier_patch.py runs its Unicorn tests on that overlaid code.bin too (fixture `patched`).
"""
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import patch as fp  # noqa: E402
import luma  # noqa: E402

CONSOLE_TEXT = ROOT / 'work/frontier/consola/console-text.bin'


@pytest.fixture(scope='module')
def built():
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and arm-none-eabi binutils required')
    code, hook, _ = fp.build()
    return code, hook, fp.assemble()[1], luma.overlay(code)


def branch_target(word, site):
    assert (word >> 24) & 0x0E == 0x0A, f'{site:#x}: {word:08x} is not a branch'
    offset = word & 0xFFFFFF
    offset -= (offset & 0x800000) << 1
    return site + 8 + 4 * offset


def test_reserve_covers_lumas_payload():
    assert fp.LUMA_RESERVED >= max(0x140, fp.LUMA_PAYLOAD) and fp.LUMA_PAYLOAD == len(luma.PAYLOAD) == 276
    assert fp.HOOKS == fp.CAVE + fp.LUMA_RESERVED and luma.AT == fp.CAVE


def test_luma_lands_on_zero_bytes_and_leaves_our_code_intact(built):
    code, hook, _, console = built
    assert not any(code[fp.CAVE - fp.BASE:fp.HOOKS - fp.BASE])
    assert console[fp.HOOKS - fp.BASE:fp.HOOKS - fp.BASE + len(hook)] == hook
    changed = [i + fp.BASE for i, (a, b) in enumerate(zip(code, console)) if a != b]
    assert all(fp.CAVE <= va < fp.CAVE + len(luma.PAYLOAD) or va - va % 4 in luma.HOOKS for va in changed)
    original = fp.REPOLISHED.read_bytes()
    path = slice(luma.PATH - fp.BASE, luma.PATH - fp.BASE + luma.PATH_MAX)
    assert code[path] == original[path]          # Luma's "lf:" path area is not ours either


def code_sites(symbols):
    """{code.bin site: target} of every branch our patch writes outside the cave."""
    sites = {fp.SITE + 8: fp.HOOKS, fp.RIVAL_SITE: symbols['rival_hook'], fp.COUNT_SITE: symbols['dome_count'],
             fp.LEVEL_SITE: symbols['pike_level'], fp.BUILD_SITE: symbols['pike_build'],
             fp.ISWIN: symbols['pike_iswin'], fp.DELETE_SITE: symbols['pyramid_save'],
             fp.ae.START: symbols['arena_start'], fp.CAP_SITE: symbols['mode_cap']}
    return sites


def test_streak_tables_point_past_the_reserve_with_luma_applied(built):
    """F9: the Singles and Doubles entries of the four streak accessors' jump tables hold the modes.s stubs."""
    _, _, symbols, console = built
    for va, (stub, *_) in fp.STREAK_SITES.items():
        assert struct.unpack_from('<2I', console, va - fp.BASE) == (symbols[stub],) * 2
        assert fp.HOOKS <= symbols[stub] < fp.CAVE_END


def test_every_code_bin_hook_points_past_the_reserve_with_luma_applied(built):
    _, _, symbols, console = built
    for site, target in code_sites(symbols).items():
        word = struct.unpack_from('<I', console, site - fp.BASE)[0]
        assert branch_target(word, site) == target, hex(site)
        assert fp.HOOKS <= target < fp.CAVE_END, hex(site)


def test_nothing_in_our_code_reaches_into_the_reserve(built):
    """Branches and literal words of the linked hooks, and the code.bin addresses the CROs call."""
    import capstone
    _, hook, symbols, _ = built
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.skipdata = True
    for ins in md.disasm(hook, fp.HOOKS):
        if ins.mnemonic.split('.')[0].rstrip('eqnlgtshicvpmlo') in ('b', 'bl') and ins.op_str.startswith('#'):
            assert not fp.CAVE <= int(ins.op_str[1:], 16) < fp.HOOKS, f'{ins.address:#x} {ins.mnemonic} {ins.op_str}'
    for k in range(0, len(hook) - 3, 4):
        assert not fp.CAVE <= struct.unpack_from('<I', hook, k)[0] < fp.HOOKS, hex(fp.HOOKS + k)
    assert all(not fp.CAVE <= a < fp.HOOKS for a in symbols.values())
    import brains
    assert all(not fp.CAVE <= a < fp.CAVE_END for a in brains.CODE.values())
    field = fp.battle_cro()[fp.FIELD_CRO]
    pike = struct.unpack_from('<I', field, fp.PIKE_PARAM_SITE + 12)[0]
    assert pike == symbols['pike_param'] and fp.HOOKS <= pike < fp.CAVE_END


def test_battle_only_routines_moved_to_dllbattle(built):
    _, _, symbols, _ = built
    blob, cro_symbols = fp.battle_cro_code()
    moved = ('arena_enter', 'arena_switch', 'arena_turn_end', 'arena_judge', 'palace_ai_want', 'palace_ai_flags',
             'palace_dispatch')
    assert not set(moved) & set(symbols)
    assert all(fp.BATTLE_CRO_AT <= cro_symbols[n] < fp.BATTLE_CRO_AT + len(blob) for n in moved)
    assert fp.BATTLE_CRO_AT + len(blob) <= fp.pe.palace_ai.RODATA
    cro = fp.battle_cro()[fp.BATTLE_CRO]
    for site, (name, _) in {**fp.ae.SITES, **fp.pe.SITES}.items():
        words = struct.unpack_from('<4I', cro, site)
        assert words[0] == words[3] == fp.ae.NOP and words[2] == fp.ae.BRIDGE_RESUME
        assert branch_target(words[1], site + 4) == cro_symbols[name]
        assert (words[1] >> 24) == 0xEB


def test_assembly_fails_if_the_hooks_do_not_fit_after_the_reserve(monkeypatch):
    if not shutil.which('arm-none-eabi-as'):
        pytest.skip('arm-none-eabi binutils required')
    monkeypatch.setattr(fp, 'HOOKS', fp.CAVE_END - 0x100)
    with pytest.raises(ValueError, match='past the cave end'):
        fp.assemble()


@pytest.mark.skipif(not CONSOLE_TEXT.exists(), reason='console dump (work/frontier/consola) not present')
def test_overlay_matches_the_console_measurement():
    text = CONSOLE_TEXT.read_bytes()
    assert len(text) == fp.CAVE_END - fp.BASE
    assert text[fp.CAVE - fp.BASE:fp.CAVE - fp.BASE + len(luma.PAYLOAD)] == luma.PAYLOAD
    for site, target in luma.HOOKS.items():
        assert branch_target(struct.unpack_from('<I', text, site - fp.BASE)[0], site) == target
    original = fp.REPOLISHED.read_bytes()
    for site, offset in luma.SUBSTITUTED.items():
        assert original[site - fp.BASE:site - fp.BASE + 4] == luma.PAYLOAD[offset:offset + 4]
