#!/usr/bin/env python3
"""F11-ISLA-CONSTRUCCION lab only: the mod a production island build runs as, for boot.sh.

    python frontier/probes/island/lab_mod.py [BUILD]      (BUILD: work/f11/build, made by
        python frontier/overlay.py --out work/f11/build/out --romfs dist/held-exp-share-v0.5/mods/000400000011C400/romfs)

Writes BUILD/mod = the v0.5 base mod (dist/held-exp-share-v0.5, checked against its manifest) with the build's romfs
files and code.ips on top, as frontier/package.py assembles a package, and BUILD/hashes.json. Then
`F11_OUT=BUILD bash frontier/probes/island/boot.sh SAVE` installs exactly that mod in this lane's laboratory.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'dist/held-exp-share-v0.5'
TITLE = '000400000011C400'


def main():
    build = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/f11/build'
    sys.path.insert(0, str(ROOT / 'frontier'))
    import package                       # frontier/package.py: v0.5's source lock and mod files, by hash
    package.check_base()
    mod = build / 'mod'
    if mod.exists():
        shutil.rmtree(mod)
    shutil.copytree(BASE / 'mods' / TITLE, mod)
    shutil.copytree(build / 'out/romfs', mod / 'romfs', dirs_exist_ok=True)
    shutil.copyfile(build / 'out/code.ips', mod / 'code.ips')
    hashes = {str(p.relative_to(mod)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(mod.rglob('*')) if p.is_file()}
    (build / 'hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(f'{mod}: {len(hashes)} files')


if __name__ == '__main__':
    main()
