import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from formats import IPSRecord, apply_ips, check_file, code_map, file_to_va, read_ips


def test_ips_normal_and_rle():
    patch = b'PATCH\x00\x00\x02\x00\x02AB\x00\x00\x06\x00\x00\x00\x03ZEOF'
    assert apply_ips(b'0123456789', read_ips(patch)) == b'01AB45ZZZ9'


@pytest.mark.parametrize('patch', [b'', b'PATCH', b'PATCH\0\0',
                                  b'PATCH\0\0\0\0\x04A',
                                  b'PATCH\0\0\0\0\0\0\x02',
                                  b'PATCHEOF\0\0\x04'])
def test_ips_rejects_truncation_and_resize(patch):
    with pytest.raises(ValueError):
        read_ips(patch)


def test_ips_rejects_overlap_and_growth():
    for records in [[IPSRecord(2, b'ab'), IPSRecord(3, b'z')], [IPSRecord(8, b'ab')]]:
        with pytest.raises(ValueError):
            apply_ips(bytes(9), records)


def test_hash_guard_rejects_same_length_change(tmp_path):
    path = tmp_path / 'input.bin'
    path.write_bytes(b'abc')
    expected = {'size': 3, 'sha256': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'}
    check_file(path, expected)
    path.write_bytes(b'abd')
    with pytest.raises(ValueError, match='identity mismatch'):
        check_file(path, expected)


def test_exheader_mapping_handles_noncontiguous_vas_and_bss():
    header = bytearray(0x400)
    for position, va, pages, size in [(0x10, 0x100000, 2, 0x1800),
                                     (0x20, 0x200000, 1, 0x100),
                                     (0x30, 0x300000, 1, 0x80)]:
        struct.pack_into('<III', header, position, va, pages, size)
    struct.pack_into('<I', header, 0x3C, 0x20)
    segments = code_map(header, 0x4000)
    assert file_to_va(0x2010, segments) == 0x200010
    assert segments[-1]['address'] == 0x300080
    assert segments[-1]['file_offset'] is None
    with pytest.raises(ValueError):
        code_map(header, 0x3FFF)


def test_local_baseline_and_import_resolution():
    """Local-only integration test; ROM fixtures are never committed."""
    import json
    from analyze_assets import CRO
    from formats import garc_entries
    root = Path(__file__).resolve().parents[1]
    base = root / 'baseline/oras'
    if not base.exists():
        pytest.skip('Run prepare_baseline.py with local inputs first')
    m = json.loads((base / 'manifest.json').read_text())
    clean = (base / 'clean/exefs/code.bin').read_bytes()
    patched = (base / 'repolished/exefs/code.bin').read_bytes()
    patch = root / 'inputs/repolished/Omega Ruby Repolished (ver. 1.7.6)/code.ips'
    assert apply_ips(clean, read_ips(patch.read_bytes())) == patched
    crs = CRO(base / 'repolished/romfs/static.crs')
    assert [s[0] for s in crs.segments[:3]] == [s['address'] for s in m['segments'][:3]]
    assert crs.segments[2][1] == m['segments'][2]['size'] + m['segments'][3]['size']
    bag = CRO(base / 'repolished/romfs/DllBag.cro')
    assert any(r['offset'] == 0x37C and r['target'] == 0x4E9F60
               for r in bag.static_imports(crs))
    data = (base / 'repolished/romfs/a/1/9/7').read_bytes()
    entries = garc_entries(data)
    assert len(entries) == 776
    assert entries[216] == (216, 0, 0x5B40, 36)
