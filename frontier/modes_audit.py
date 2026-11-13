#!/usr/bin/env python3
"""Read-only F9 allocation/space audit. Run after sourcing scripts/env.sh.

Measures the current assembled payloads, not historical cave figures. Retail
scan over-approximates literals and cannot prove absence of computed work uses.
Reservations are not evidence of runtime persistence.
"""
import hashlib
import json

import brains
from cro import Cro
import ids
import modes
import patch

# Existing assigned positions including holes/state, per REPARTO's works table.
# 16410-16414 abandoned; exclude the WHOLE suspected cleared block 0x4010-0x401f.
LEGACY_RANGES = (
    (16433, 16435), (16437, 16439), (16441, 16443), (16461, 16463),
    (16465, 16467), (16473, 16475), (16477, 16479), (16481, 16483),
    (16485, 16487), (16489, 16490), (16493, 16495),
    (16649, 16651), (16653, 16655), (16657, 16659), (16661, 16663),
    (16669, 16671), (16674, 16675), (16681, 16683), (16685, 16687),
    (16689, 16689), (16693, 16694), (16721, 16723), (16725, 16727),
    (16729, 16731), (16733, 16733),
)
LEGACY = {w for first, last in LEGACY_RANGES for w in range(first, last + 1)} | ids.KNOWN.keys()
EXCLUDED = set(range(0x4010, 0x4020)) | {16398, 16399, 16429, 16430}


def check_allocation(used):
    candidates = set(ids.WORKS) - used.keys() - LEGACY - EXCLUDED
    allocated = modes.RESERVED
    if len(allocated) != 35 or len(set(allocated)) != 35:
        raise ValueError('F9 must reserve exactly 35 distinct works')
    bad = set(allocated) - candidates
    if bad:
        raise ValueError(f'F9 work collision: {sorted(bad)}')
    return candidates


def measure_space():
    hook, _ = patch.assemble()
    battle, _ = patch.battle_cro_code()
    brain, _ = brains.assemble()
    # Same validated v0.5 input as patch.battle_cro, before F8 writes.
    path = patch.MOD_ROMFS / patch.FIELD_CRO
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != patch.FIELD_CRO_SHA256:
        raise ValueError('DllField.cro: expected patch.FIELD_CRO_SHA256 (v0.5)')
    cro = Cro(raw)
    if modes.FIELD_AT < brains.AT + len(brain) or modes.FIELD_END != brains.FIELD_RODATA:
        raise ValueError('F9 overlaps Brains or rodata')
    if any(raw[modes.FIELD_AT:modes.FIELD_END]) or len(raw) < modes.FIELD_END:
        raise ValueError('F9 cave is not zero padding')
    # Like DexNav/Brains, this is padding AFTER the text segment, within its
    # last mapped page. Do not claim it is part of the segment's logical size.
    text_start, text_size, kind = cro.segments[0]
    text_end = text_start + text_size
    if kind != 0 or not text_end <= modes.FIELD_AT < modes.FIELD_END <= (text_end + 0xFFF) & ~0xFFF:
        raise ValueError('F9 cave is outside the final text page padding')
    if any(modes.FIELD_AT <= target < modes.FIELD_END or modes.FIELD_AT <= source < modes.FIELD_END
           for target, _, source in cro.relocs):
        raise ValueError('F9 cave has an internal relocation')
    from build_patch import cro_hashes, update_crr
    if b''.join(cro_hashes(raw)) != raw[:0x80]:
        raise ValueError('DllField.cro: invalid segment hashes')
    crr = (patch.MOD_ROMFS / patch.CRR).read_bytes()
    if update_crr(crr, raw, raw) != crr:
        raise ValueError('DllField.cro: CRR membership check changed bytes')
    return {
        'code': {'start': patch.HOOKS, 'size': len(hook), 'end': patch.HOOKS + len(hook),
                 'free': patch.CAVE_END - patch.HOOKS - len(hook),
                 'luma_reserved': [patch.CAVE, patch.HOOKS]},
        'battle': {'start': patch.BATTLE_CRO_AT, 'end': patch.BATTLE_CRO_AT + len(battle),
                   'free': 0xD8000 - patch.BATTLE_CRO_AT - len(battle)},
        'brains': {'start': brains.AT, 'end': brains.AT + len(brain)},
        'f9_reserved': {'start': modes.FIELD_AT, 'end': modes.FIELD_END,
                        'size': modes.FIELD_END - modes.FIELD_AT, 'text_segment_end': text_end,
                        'sha256_input': hashlib.sha256(raw).hexdigest()},
    }


def main():
    used, scripts, code_files = ids.scan()
    candidates = check_allocation(used)
    saves = {}
    for label, path in ids.SAVES.items():
        if path.exists():
            raw = path.read_bytes()
            saves[label] = {'sha256': hashlib.sha256(raw).hexdigest(),
                            'nonzero': {w: ids.se.work(raw, w) for w in modes.RESERVED if ids.se.work(raw, w)}}
    print(json.dumps({'scripts': scripts, 'code_files': code_files, 'candidates': sorted(candidates),
                      'allocated': len(modes.RESERVED), 'remaining': sorted(candidates - set(modes.RESERVED)),
                      'save_observations': saves, 'space': measure_space(),
                      'runtime_persistence': 'NOT TESTED'}, indent=2))


if __name__ == '__main__':
    main()
