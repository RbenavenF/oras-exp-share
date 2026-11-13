#!/usr/bin/env python3
"""Lab only (F7-CUEVA-LUMA): a package-shaped mod folder for frontier/probes/package/boot.sh, with the code.bin that
Azahar would run (`plain`) or the one a console with Luma3DS runs (`luma`: frontier/luma.py writes Luma's measured
LayeredFS payload over the start of the cave and its two branches; Azahar does not, so this is how the lab sees it).

v0.5's mod files + the romfs of frontier/overlay.py (run over v0.5's romfs, full island, as frontier/package.py does)
+ code.ips. Writes OUT/luma/titles/<title>/ and OUT/manifest.json (SHA-256 of each file, as package.py).
Never a release: package.py builds those. Usage:
  python frontier/probes/luma/lab_mod.py --build work/frontier/cueva/build --out work/frontier/cueva/mod-luma luma
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import luma  # noqa: E402
import package  # noqa: E402
import patch  # noqa: E402
from formats import apply_ips, read_ips  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('variant', choices=['plain', 'luma'])
    p.add_argument('--build', type=Path, required=True, help='overlay.py output (built here if missing)')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    build, out = a.build.resolve(), a.out.resolve()
    work = (ROOT / 'work').resolve()
    if not (build.is_relative_to(work) and out.is_relative_to(work)):
        p.error('--build and --out must be under work/')
    _, mod = package.check_base()             # v0.5's mod folder, checked against its manifest
    if not (build / 'code.ips').exists():
        package.build(mod, build)
    title = out / 'luma/titles' / package.TITLE
    shutil.rmtree(out, ignore_errors=True)
    sources = {rel: mod / rel for rel in package.files_of(mod)}
    sources.pop('code.ips', None)
    sources.update({f'romfs/{rel}': build / 'romfs' / rel for rel in package.files_of(build / 'romfs')})
    for rel, src in sources.items():
        (title / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, title / rel)
    clean = patch.CLEAN.read_bytes()
    code = apply_ips(clean, read_ips((build / 'code.ips').read_bytes()))
    if a.variant == 'luma':
        from build_patch import diff_ips
        code = luma.overlay(code)
        ips = diff_ips(clean, code)
        if apply_ips(clean, read_ips(ips)) != code:
            sys.exit('IPS round trip failed')
        (title / 'code.ips').write_bytes(ips)
    else:
        shutil.copyfile(build / 'code.ips', title / 'code.ips')
    files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(title.rglob('*')) if p.is_file()}
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (out / 'manifest.json').write_text(json.dumps(dict(variant=a.variant, commit=head, files=files), indent=1))
    print(f'{out}: {len(files)} files, code.ips sha256 {files[f"luma/titles/{package.TITLE}/code.ips"][:16]}…')


if __name__ == '__main__':
    main()
