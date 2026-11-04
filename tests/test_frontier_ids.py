"""Free saved works (frontier/ids.py): the Factory's works stay unused by the retail game and our mods."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import ids  # noqa: E402
import patch as fp  # noqa: E402


def test_arm_immediate():
    assert ids.arm_immediate(0xE3A00901) == 0x4000          # mov r0, #0x4000
    assert ids.arm_immediate(0xE2822DC5) == 0x3140          # add r2, r2, #0x3140
    assert ids.arm_immediate(0xE5922000) is None             # ldr: not data processing


@pytest.fixture(scope='module')
def used():
    if not (ids.GAME / 'romfs/a/0/2/9').exists():
        pytest.skip('Local baseline required')
    return ids.scan()


def test_scan_sees_known_works(used):
    works, scripts, code = used
    assert scripts == 1157 and code > 100
    assert 16697 in works            # Briney's boat state (faraway/event.py)


def test_factory_works_are_free(used):
    import factory
    works, _, _ = used
    for number in (fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, fp.WORK_FSTREAK, fp.WORK_ROUTE, fp.WORK_FRECORD, factory.WORK_RNG,
                   factory.WORK_STREAK):
        assert number not in works and number not in ids.KNOWN


def test_no_frontier_work_in_the_block_cleared_on_entering_a_hall():
    """Entering 213 or 329 sets works 16410-16413 to 0 (Azahar, reports/frontier.md §25); the block they sit in,
    0x4010-0x401F, is kept off limits for state that must survive walking in and out of a facility."""
    import factory
    cleared = range(0x4010, 0x4020)
    state = [fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, fp.WORK_ROUTE, factory.WORK_RNG, factory.WORK_STREAK,
             *(s + k for _, s in fp.STREAK_ROUTES.values() for k in range(3)), *fp.ACTIVE_WORK.values()]
    assert not [w for w in state if w in cleared]
