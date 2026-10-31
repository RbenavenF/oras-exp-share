import hashlib
import json
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_patch import cro_hashes, diff_ips, guarded_writes, patched_assets
from formats import apply_ips, read_ips


def test_byte_guard_rejects_wrong_preimage_even_with_correct_hash():
    original = b'abcdefgh'
    spec = {'path': 'fixture', 'sha256': hashlib.sha256(original).hexdigest(),
            'writes': [{'offset': 2, 'before': 'FFFF', 'after': '0000'}]}
    with pytest.raises(ValueError, match='Unexpected bytes'):
        guarded_writes(original, spec)


def test_ips_diff_round_trip_with_large_record():
    original = bytes(70001)
    changed = b'a' * 70000 + b'\0'
    assert apply_ips(original, read_ips(diff_ips(original, changed))) == changed
    assert diff_ips(original, original) == b'PATCHEOF'


def test_generated_cro_crr_and_item_integrity():
    root = Path(__file__).resolve().parents[1]
    if not (root / 'baseline/oras/manifest.json').exists():
        pytest.skip('Local baseline required')
    before, after = patched_assets()
    for name in before:
        assert len(before[name]) == len(after[name])
        assert apply_ips(before[name], read_ips(diff_ips(before[name], after[name]))) == after[name]
    cro = after['romfs/DllBattle.cro']
    assert b''.join(cro_hashes(cro)) == cro[:128]
    crr = after['romfs/.crr/static.crr']
    start, count = struct.unpack_from('<II', crr, 0x350)
    hashes = [crr[start + 32 * i:start + 32 * (i + 1)] for i in range(count)]
    assert hashes == sorted(hashes)
    assert hashlib.sha256(cro[:128]).digest() in hashes
    assert hashlib.sha256(before['romfs/DllBattle.cro'][:128]).digest() not in hashes
    assert crr[:start] == before['romfs/.crr/static.crr'][:start]
    spec = json.loads((root / 'reports/held-exp-share-spec.json').read_text())
    allowed = set(range(0x20, 0x40)) | set(range(0x32630, 0x32648)) | set(range(0x3264C, 0x32650))
    assert all(a == b or i in allowed for i, (a, b) in enumerate(zip(before['romfs/DllBattle.cro'], cro)))
    # Patching a loaded module must not be overwritten by a relocation.
    from analyze_assets import CRO
    module = CRO(root / 'baseline/oras/repolished/romfs/DllBattle.cro')
    for header in (0xF8, 0x128, 0x130):
        offset, count = module.unpack('<II', header)
        for i in range(count):
            tag = module.unpack('<I', offset + i * 12)[0]
            target = module.resolve(tag)
            assert not 0x32630 <= target < 0x32648 and not 0x3264C <= target < 0x32650


def test_text_patches_keep_layout_and_only_change_target_lines():
    root = Path(__file__).resolve().parents[1]
    if not (root / 'baseline/oras/manifest.json').exists():
        pytest.skip('Local baseline required')
    from formats import garc_entries, text_lines, words_to_text
    before, after = patched_assets()
    spec = json.loads((root / 'reports/held-exp-share-spec.json').read_text())
    for entry in spec['patches']:
        if 'texts' not in entry:
            continue
        old, new = before[entry['path']], after[entry['path']]
        assert len(old) == len(new) and garc_entries(old) == garc_entries(new)
        targets = {(t['entry'], t['line']): t['after'] for t in entry['texts']}
        for (index, _, offset, length) in garc_entries(old):
            a, b = text_lines(old[offset:offset + length])[0], text_lines(new[offset:offset + length])[0]
            for line, (x, y) in enumerate(zip(a, b, strict=True)):
                if (index, line) in targets:
                    assert words_to_text(y) == targets[index, line]
                else:
                    assert x == y
