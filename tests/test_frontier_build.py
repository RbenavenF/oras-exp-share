"""Battle Factory zone script changes (frontier/build.py) on the local dump."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import build as fbuild  # noqa: E402
import patch as fp  # noqa: E402
from formats import garc_entries, lz11_decompress, zo_files  # noqa: E402
from pawn import OP, Script, decode, gf_hash, s32  # noqa: E402


@pytest.fixture(scope='module')
def built():
    if not fbuild.ZONES.exists():
        pytest.skip('Local baseline required')
    return fbuild.ZONES.read_bytes(), fbuild.build()


def test_only_zone_517_changes(built):
    before, (after, _) = built
    a, b = garc_entries(before), garc_entries(after)
    assert len(a) == len(b)
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if before[x[2]:x[2] + x[3]] != after[y[2]:y[2] + y[3]]]
    assert changed == [fbuild.ZONE_MAISON]
    _, _, offset, length = b[fbuild.ZONE_MAISON]
    files = zo_files(lz11_decompress(after[offset:offset + length]))
    old = zo_files(lz11_decompress(before[a[fbuild.ZONE_MAISON][2]:][:a[fbuild.ZONE_MAISON][3]]))
    assert files[:2] == old[:2] and files[3:] == old[3:]


def test_party_select_checks_the_factory_state(built):
    _, (_, raw) = built
    script = Script.parse(raw)
    assert script.build() == raw
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    select = next(i for i, x in enumerate(ins) if x.op == OP['SYSREQ_N']
                  and names[x.args[0]] == s32(gf_hash('BattleHouse_CallPartySelectApp')))
    head = ins[select - 10:select]
    proc = max(i for i, x in enumerate(ins[:select]) if x.op == OP['PROC'])
    seq = ins[proc + 1:proc + 8]
    assert seq[0].args == [fp.WORK_IV] and names[seq[1].args[0]] == s32(gf_hash('WorkGet'))
    assert seq[2].op == OP['JZER']
    assert names[seq[5].args[0]] == s32(gf_hash('WorkSet')) and seq[6].op == OP['CONST_P_PRI']
    assert head  # the retail call is still there after the skip
