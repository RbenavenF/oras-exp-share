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


def test_ips_diff_can_grow_a_file():
    original = b'abc'
    changed = b'abd\0\0x'
    assert apply_ips(original, read_ips(diff_ips(original, changed))) == changed


CRO_CHANGES = {'romfs/DllBattle.cro': [(0x32630, 0x32648), (0x3264C, 0x32650)],
               'romfs/DllField.cro': [(0xAFC74, 0xAFC78), (0xF0400, 0xF046C)]}


def test_generated_cro_crr_and_item_integrity():
    root = Path(__file__).resolve().parents[1]
    if not (root / 'baseline/oras/manifest.json').exists():
        pytest.skip('Local baseline required')
    before, after = patched_assets()
    for name in before:
        if not name.startswith('romfs/a/0/7/'):
            assert len(before[name]) == len(after[name])
        assert apply_ips(before[name], read_ips(diff_ips(before[name], after[name]))) == after[name]
    crr = after['romfs/.crr/static.crr']
    start, count = struct.unpack_from('<II', crr, 0x350)
    hashes = [crr[start + 32 * i:start + 32 * (i + 1)] for i in range(count)]
    assert hashes == sorted(hashes)
    assert crr[:start] == before['romfs/.crr/static.crr'][:start]
    from analyze_assets import CRO
    for name, ranges in CRO_CHANGES.items():
        cro = after[name]
        assert b''.join(cro_hashes(cro)) == cro[:128]
        assert hashlib.sha256(cro[:128]).digest() in hashes
        assert hashlib.sha256(before[name][:128]).digest() not in hashes
        allowed = set(range(0x20, 0x40)).union(*(range(a, b) for a, b in ranges))
        assert all(a == b or i in allowed for i, (a, b) in enumerate(zip(before[name], cro)))
        # Patching a loaded module must not be overwritten by a relocation.
        module = CRO(root / 'baseline/oras/repolished' / name)
        for header in (0xF8, 0x128, 0x130):
            offset, count = module.unpack('<II', header)
            for i in range(count):
                target = module.resolve(module.unpack('<I', offset + i * 12)[0])
                assert not any(a <= target < b for a, b in ranges)
    # The DexNav routine lives in zero padding after the code segment, inside the hashed code region.
    field = CRO(root / 'baseline/oras/repolished/romfs/DllField.cro')
    text_start, text_size, _ = field.segments[0]
    code, code_size = field.unpack('<II', 0xB0)
    assert text_start + text_size <= 0xF0400 and 0xF046C <= field.segments[1][0]
    assert code <= 0xF0400 and 0xF046C <= code + code_size


def test_text_patches_only_change_target_lines():
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
        targets = {(t['entry'], t['line']): t['after'] for t in entry['texts']}
        edited = {index for index, _ in targets}
        old_entries, new_entries = garc_entries(old), garc_entries(new)
        assert [e[:2] for e in old_entries] == [e[:2] for e in new_entries]
        for (index, _, o1, l1), (_, _, o2, l2) in zip(old_entries, new_entries):
            if index not in edited:
                assert old[o1:o1 + l1] == new[o2:o2 + l2]
                continue
            a, b = text_lines(old[o1:o1 + l1]), text_lines(new[o2:o2 + l2])
            assert b[1][:len(a[1])] == a[1]
            for line, words in enumerate(b[0]):
                if (index, line) in targets:
                    assert words_to_text(words) == targets[index, line]
                else:
                    assert words == a[0][line]
