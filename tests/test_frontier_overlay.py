"""Battle Factory and Frontier Pass archive changes (frontier/overlay.py) on the local dump."""
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


def test_only_the_maison_and_harbor_scripts_change(built):
    import island
    before, (archives, _) = built
    after = archives['a/0/1/3']
    a, b = garc_entries(before), garc_entries(after)
    assert len(a) == len(b)
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if before[x[2]:x[2] + x[3]] != after[y[2]:y[2] + y[3]]]
    assert changed == [island.ZONE_HARBOR, fbuild.ZONE_MAISON]
    for zone in changed:
        _, _, offset, length = b[zone]
        files = zo_files(lz11_decompress(after[offset:offset + length]))
        old = zo_files(lz11_decompress(before[a[zone][2]:][:a[zone][3]]))
        assert files[:2] == old[:2] and files[3:] == old[3:] and files[2] != old[2]


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


def test_texts_append_the_option_the_refusal_and_the_factory_entry(built):
    from formats import text_lines, words_to_text
    import dome
    import pike
    import factory
    import island
    import brains
    import tower
    _, (archives, _) = built
    assert fbuild.harbor_lines(fbuild.ROMFS) == (30, 31)
    for lang, path in factory.STORYTEXT.items():
        code = factory.LANG[lang]
        after = archives[path]
        before = (fbuild.ROMFS / path).read_bytes()
        a, b = garc_entries(before), garc_entries(after)
        assert len(b) == len(a) + 1 == fp.TEXT_FACTORY + 1
        for x, y in zip(a, b):
            old, new = before[x[2]:x[2] + x[3]], after[y[2]:y[2] + y[3]]
            appended = {factory.TEXT_ZONE: [factory.OPTION[code], factory.BUSY[code], brains.LINE_SYMBOLS_OPTION[code]] + list(tower.LEVEL_TEXT[code]),
                        island.TEXT_HARBOR: island.SAILOR[code],
                        island.FERRY_TEXT: island.FERRY[code]}.get(x[0])
            if appended is None:
                assert old == new
                continue
            old_lines, new_lines = text_lines(old)[0], text_lines(new)[0]
            assert new_lines[:len(old_lines)] == old_lines
            assert [words_to_text(w) for w in new_lines[len(old_lines):]] == appended
        e = b[-1]
        lines = [words_to_text(w) for w in text_lines(after[e[2]:e[2] + e[3]])[0]]
        assert lines[:3] == factory.PICK[factory.LANG[lang]] and dome.LINE_BASE == factory.LINE_S + 784
        assert lines[dome.LINE_BASE:pike.LINE_BASE] == dome.lines(lang)     # the Dome's, after the Factory's
        assert lines[pike.LINE_BASE:pike.LINE_END] == pike.lines(lang)      # the Pike's, after the Dome's
        import pyramid
        assert pyramid.LINE_BASE == pike.LINE_END
        assert lines[pyramid.LINE_BASE:pyramid.LINE_END] == pyramid.lines(lang)   # the Pyramid's, after the Pike's
        import brains
        assert brains.line_base() == pyramid.LINE_END
        import factory_open as fo
        assert lines[pyramid.LINE_END:fo.LINE_BASE] == brains.lines(lang)
        sets, *_ = fbuild.rentals()
        assert lines[fo.LINE_BASE:] == fo.lines_for(lang, (fbuild.ROMFS / factory.GAMETEXT[lang]).read_bytes(), sets)
        assert len(lines) == fo.LINE_BASE + 44


def test_game_texts_rename_only_the_pass(built):
    import brains
    import factory
    import island
    from formats import text_lines, words_to_text
    _, (archives, _) = built
    for lang, path in factory.GAMETEXT.items():
        before, after = (fbuild.ROMFS / path).read_bytes(), archives[path]
        a, b = garc_entries(before), garc_entries(after)
        assert len(a) == len(b)
        for x, y in zip(a, b):
            old, new = text_lines(before[x[2]:x[2] + x[3]])[0], text_lines(after[y[2]:y[2] + y[3]])[0]
            diff = [k for k, (u, v) in enumerate(zip(old, new)) if u != v]
            key = next((k for k, entry in island.GAMETEXT_ITEM.items() if entry == x[0]), None)
            if x[0] == brains.TEXT_TRAINER_NAMES:          # the Brains' trainer names appended (brains.trainers())
                assert len(old) == brains.TRAINER_FIRST and diff == []
                assert [words_to_text(w) for w in new[len(old):]] == brains.trainer_names()
                continue
            assert len(old) == len(new) and diff == ([] if key is None else [island.ITEM_PASS])
            if key:
                assert words_to_text(new[island.ITEM_PASS]) == island.ITEM[factory.LANG[lang]][key]


def test_shared_archive_changes_scripts_5_and_79(built):
    import factory
    import island
    _, (archives, (_, script5)) = built
    before, after = (fbuild.ROMFS / fbuild.SHARED).read_bytes(), archives[fbuild.SHARED]
    a, b = garc_entries(before), garc_entries(after)
    assert len(a) == len(b)
    changed = [x[0] for x, y in zip(a, b) if before[x[2]:x[2] + x[3]] != after[y[2]:y[2] + y[3]]]
    assert changed == [factory.SHARED_SCRIPT, island.FERRY_SCRIPT]
    assert after[b[5][2]:b[5][2] + b[5][3]] == script5


def test_zone_container_stays_below_the_measured_limit(built):
    _, (archives, _) = built
    data = archives['a/0/1/3']
    _, _, offset, length = garc_entries(data)[fbuild.ZONE_MAISON]
    assert len(lz11_decompress(data[offset:offset + length])) <= 17248   # loads in Azahar (reports §11)
