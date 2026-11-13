#!/usr/bin/env python3
"""Lab-only F9 sentinel fixture and saved-copy comparison; never edits a source.

seed SOURCE SHA256 OUTPUT: writes a NEW file under work/ and OUTPUT.json.
check SAVED OUTPUT.json: verifies checksums, sentinels and the party block hash.
Use sentinels ONLY with alpha-v0.2: the banks contain artificial streaks/sets.
CONFIG uses valid packed modes/levels, but those modes are not enabled in v0.2.
This does not prove that every other retail event leaves these works untouched.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'frontier'), str(ROOT/'scripts'), str(ROOT/'faraway')]
import modes  # noqa: E402
import patch  # noqa: E402
import save_event as se  # noqa: E402
import save_fixture as sf  # noqa: E402


def party_hash(data):
    return hashlib.sha256(data[sf.PARTY:sf.PARTY+0x61c]).hexdigest()


def seed(source, sha256, destination):
    data = source.read_bytes()
    sf.blocks(data)
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError('source hash mismatch')
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT/'work') or destination == source.resolve():
        raise ValueError('destination must be a separate NEW file under work/')
    meta = destination.with_suffix(destination.suffix+'.json')
    if destination.exists() or meta.exists():
        raise ValueError('destination or metadata already exists')
    expected = {w:0x500+i for i,w in enumerate(modes.RESERVED)}
    expected.update({w:modes.pack_config(r,3 if r <= 2 else 1,100 if r == 1 else 73)
                     for r,w in modes.CONFIG.items()})
    expected.update({w:0 for w in patch.ACTIVE_WORK.values()})
    expected[patch.WORK_ROUTE] = 0
    fixture = se.edit(data, works=expected.items())
    report = dict(source_sha256=sha256, fixture_sha256=hashlib.sha256(fixture).hexdigest(),
                  party_sha256=party_hash(data), expected=expected)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(fixture)
    with meta.open('x') as stream:
        json.dump(report,stream,indent=2)
    return report


def check(saved, metadata):
    data = saved.read_bytes()
    sf.blocks(data)
    expected = {int(k):v for k,v in metadata['expected'].items()}
    wrong = {w:(se.work(data,w),v) for w,v in expected.items() if se.work(data,w) != v}
    party = party_hash(data)
    report = dict(sha256=hashlib.sha256(data).hexdigest(), valid_blocks=58,
                  works=len(expected), mismatches=wrong, party_sha256=party, place=se.place(data))
    if wrong or party != metadata['party_sha256']:
        raise ValueError(report)
    return report


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == 'seed':
        result = seed(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]))
    elif len(sys.argv) == 4 and sys.argv[1] == 'check':
        result = check(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text()))
    else:
        raise SystemExit(__doc__)
    print(json.dumps(result,indent=2))
