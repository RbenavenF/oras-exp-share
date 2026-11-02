"""Battle Factory zone script and text changes (frontier/overlay.py) on the local dump."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import overlay as fbuild  # noqa: E402
import patch as fp  # noqa: E402
from formats import garc_entries, lz11_decompress, zo_files  # noqa: E402
from pawn import OP, Script, decode, gf_hash, s32  # noqa: E402


@pytest.fixture(scope='module')
def built():
    if not fbuild.ZONES.exists():
        pytest.skip('Local baseline required')
    return fbuild.ZONES.read_bytes(), fbuild.build()


def test_only_zone_517_changes(built):
    before, (archives, _) = built
    after = archives['a/0/1/3']
    a, b = garc_entries(before), garc_entries(after)
    assert len(a) == len(b)
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if before[x[2]:x[2] + x[3]] != after[y[2]:y[2] + y[3]]]
    assert changed == [fbuild.ZONE_MAISON]
    _, _, offset, length = b[fbuild.ZONE_MAISON]
    files = zo_files(lz11_decompress(after[offset:offset + length]))
    old = zo_files(lz11_decompress(before[a[fbuild.ZONE_MAISON][2]:][:a[fbuild.ZONE_MAISON][3]]))
    assert files[:2] == old[:2] and files[3:] == old[3:]


def test_party_select_checks_the_factory_state(built):
    _, (_, (raw, _)) = built
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


def test_texts_append_the_option_and_the_factory_entry(built):
    from formats import text_lines, words_to_text
    import factory
    _, (archives, _) = built
    for lang, path in factory.STORYTEXT.items():
        after = archives[path]
        before = (fbuild.ROMFS / path).read_bytes()
        a, b = garc_entries(before), garc_entries(after)
        assert len(b) == len(a) + 1 == fp.TEXT_FACTORY + 1
        for x, y in zip(a, b):
            old, new = before[x[2]:x[2] + x[3]], after[y[2]:y[2] + y[3]]
            if x[0] != factory.TEXT_ZONE:
                assert old == new
                continue
            old_lines, new_lines = text_lines(old)[0], text_lines(new)[0]
            assert len(old_lines) == factory.TEXT_LINES and new_lines[:-1] == old_lines
            assert words_to_text(new_lines[-1]) == factory.OPTION[factory.LANG[lang]]
        e = b[-1]
        lines = [words_to_text(w) for w in text_lines(after[e[2]:e[2] + e[3]])[0]]
        assert lines[:3] == factory.PICK[factory.LANG[lang]] and len(lines) == factory.LINE_SLOTS + 926


def test_shared_archive_changes_only_script_5(built):
    import factory
    _, (archives, (_, script5)) = built
    before, after = (fbuild.ROMFS / fbuild.SHARED).read_bytes(), archives[fbuild.SHARED]
    a, b = garc_entries(before), garc_entries(after)
    assert len(a) == len(b)
    changed = [x[0] for x, y in zip(a, b) if before[x[2]:x[2] + x[3]] != after[y[2]:y[2] + y[3]]]
    assert changed == [factory.SHARED_SCRIPT]
    assert after[b[5][2]:b[5][2] + b[5][3]] == script5


def test_zone_container_stays_below_the_measured_limit(built):
    _, (archives, _) = built
    data = archives['a/0/1/3']
    _, _, offset, length = garc_entries(data)[fbuild.ZONE_MAISON]
    assert len(lz11_decompress(data[offset:offset + length])) <= 17248   # loads in Azahar (reports §11)
