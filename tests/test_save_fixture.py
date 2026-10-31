import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from save_fixture import (decode_pk, encode_pk, inspect, pk_checksum, make_fixture, move_exp_share,
                          PARTY, PKSIZE)


def test_party_crypto_preserves_all_shuffle_variants_and_party_stats():
    for shuffle in range(32):
        # Distinct contents in every block; party stats use a separate RNG reset.
        raw = bytearray((i * 7 + 31) & 255 for i in range(260))
        struct.pack_into('<IHH', raw, 0, shuffle << 13 | 1234, 0, 0)
        struct.pack_into('<H', raw, 6, pk_checksum(raw))
        encrypted = encode_pk(raw)
        assert encrypted != raw
        assert decode_pk(encrypted) == raw
        damaged = bytearray(encrypted)
        damaged[8] ^= 1
        with pytest.raises(ValueError, match='checksum'):
            decode_pk(damaged)


def test_invalid_save_and_party_are_rejected():
    with pytest.raises(ValueError, match='ORAS'):
        inspect(bytes(0x76000))
    with pytest.raises(ValueError, match='260-byte'):
        decode_pk(bytes(232))


def test_fixture_unused_slots_are_valid_encrypted_empty_records():
    source = Path(__file__).resolve().parents[1] / 'work/test-saves/starter-main'
    if not source.exists():
        pytest.skip('Requires the locally generated laboratory save')
    for scenario in ('reserve', 'participant', 'fainted', 'none'):
        result = make_fixture(source.read_bytes(), scenario)
        assert len(inspect(result)['party']) == 3
        for slot in range(3, 6):
            pk = decode_pk(result[PARTY + slot * PKSIZE:PARTY + (slot + 1) * PKSIZE])
            assert pk == bytes(PKSIZE)


def test_move_exp_share_only_changes_bag_pockets():
    source = Path(__file__).resolve().parents[1] / 'work/user-save-test/user-before-main'
    if not source.exists():
        pytest.skip('Requires a local save with the Exp. Share in Key Items')
    data = source.read_bytes()
    before, after = inspect(data), inspect(move_exp_share(data))
    assert after['party'] == before['party']
    assert [e for e in after['bag']['key'] if e[0] == 216] == []
    assert sorted(after['bag']['items']) == sorted(before['bag']['items'] + [(216, 1)])
    with pytest.raises(ValueError, match='exactly one'):
        move_exp_share(move_exp_share(data))
