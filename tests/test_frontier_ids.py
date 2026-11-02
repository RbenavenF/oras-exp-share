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
    for number in (fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, factory.WORK_RNG, factory.WORK_STREAK):
        assert number not in works and number not in ids.KNOWN
