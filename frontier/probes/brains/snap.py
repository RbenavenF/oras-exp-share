#!/usr/bin/env python3
"""Lab only: snap.py NAME [SAVE] -> copy the lab save (or SAVE) to work/frontier/cerebros/factory/NAME.sav and print
its Brain/Factory facts (zone, works, BP at 0x4230 as frontier/probes/pyramid/snapshot.py, party hash)."""
from pathlib import Path
import sys, json, struct, hashlib, shutil
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'faraway')]
import save_event as se
name = sys.argv[1]
out = ROOT / 'work/frontier/cerebros/factory' / f'{name}.sav'
src = Path(sys.argv[2]) if len(sys.argv) > 2 else next((ROOT / 'work/azahar-lab/data/azahar-emu/sdmc').glob('**/00000001/main'))
if src.resolve() != out.resolve():
    assert not out.exists(), out
    shutil.copyfile(src, out)
d = out.read_bytes()
w = lambda n: se.work(d, n)
print(json.dumps(dict(file=str(out.relative_to(ROOT)), sha256=hashlib.sha256(d).hexdigest(), place=se.place(d),
                      route=w(16438), factory=[w(n) for n in (16437, 16489, 16439)], rentals=[w(n) for n in (16485, 16486, 16487)],
                      seed=w(16490), rival=[w(n) for n in (16433, 16434, 16435)], symbols=w(16729), brain=w(16730),
                      bp=struct.unpack_from('<H', d, 0x4230)[0], party_sha256=hashlib.sha256(d[0x14200:0x1481c]).hexdigest())))
