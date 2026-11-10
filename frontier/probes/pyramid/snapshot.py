"""Lab only: copy the emulator's save to a new work/frontier/lab/py_<name>.sav and log its facts."""
from pathlib import Path
import sys, json, struct, hashlib, shutil
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'faraway')]
import save_event as se
import save_fixture as sf
name = sys.argv[1]
out = ROOT / 'work/frontier/lab' / f'py_{name}.sav'
if out.exists():
    raise FileExistsError(out)
src = next((ROOT / 'work/azahar-lab/data/azahar-emu/sdmc').glob('**/00000001/main'))
shutil.copyfile(src, out)
d = out.read_bytes(); sf.inspect(d)
w = lambda n: se.work(d, n)
r = dict(file=str(out.relative_to(ROOT)), sha256=hashlib.sha256(d).hexdigest(), place=se.place(d), route=w(16438),
         pyramid=[w(n) for n in (16481, 16482, 16483)], sel=[w(n) for n in (16681, 16682, 16683)], count=w(16685),
         beaten=w(16686), tower=[w(n) for n in (16441, 16442, 16443)], factory=[w(n) for n in (16437, 16489, 16439)],
         palace=[w(n) for n in (16461, 16462, 16463)], maison=struct.unpack_from('<4H', d, 0x1bbc0),
         bp=struct.unpack_from('<H', d, 0x4230)[0], party_sha256=hashlib.sha256(d[0x14200:0x1481c]).hexdigest())
print(json.dumps(r))
with (ROOT / 'work/frontier/pyramid/v2/save-evidence.jsonl').open('a') as f:
    f.write(json.dumps(r) + '\n')
