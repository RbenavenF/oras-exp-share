"""Bit-30 masks on every +0xa8 reader of code.bin and all CROs (run from the repo root; §33)."""
import sys, io, contextlib
from pathlib import Path
from pathlib import Path as _P; _H = _P(__file__).resolve().parent; sys.path[:0] = [str(_H), str(_H.parents[1])]
import audit_a8 as A
from cro import Cro
def only30(name, data, segs, offs, base=0):
    with contextlib.redirect_stdout(io.StringIO()):
        rep = A.audit(name, data, segs, offs, base)
    hits = {a: (t, u) for a, (t, u) in rep.items() if any(k == 'MASK30' for k, _ in u)}
    print(f'{name}: {len(rep)} reads +{[hex(o) for o in offs]}, MASK30 {len(hits)}')
    for a, (t, u) in sorted(hits.items()):
        print(f'  {a:x} {t} -> {[x for k, x in u if k == "MASK30"]}')
only30('code.bin +0xa8', Path('baseline/oras/repolished/exefs/code.bin').read_bytes(), [(0, 0x480000)], [0xA8], 0x100000)
paths = {p.name: p for p in Path('baseline/oras/repolished/romfs').glob('*.cro')}
paths.update({p.name: p for p in Path('dist/held-exp-share-v0.5/mods/000400000011C400/romfs').glob('*.cro')})
for n, p in sorted(paths.items()):
    c = Cro(p.read_bytes())
    only30(n, c.data, [(s, k) for s, k, t in c.segments if t == 0 and k], [0xA8])
