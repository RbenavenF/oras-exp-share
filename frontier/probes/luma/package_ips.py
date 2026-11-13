#!/usr/bin/env python3
"""Lab only (F7-PAQUETE-V02): the code.ips a console with Luma3DS effectively runs for a built package, so Azahar can
run the EXACT package plus Luma's LayeredFS payload (frontier/luma.py). Reads PKG/luma/titles/<title>/code.ips,
checks it against PKG/manifest.json, applies it to the clean code.bin, writes Luma's payload and branches over it,
and writes OUT/code.ips (diff from the clean code.bin), OUT/code.bin (with Luma) and
OUT/package-code.bin (before Luma). Checks that the result matches the package
manifest's console_check. Never a release.

  python frontier/probes/luma/package_ips.py dist/oras-frontier-alpha-v0.2 --out work/frontier/pkg02/luma
  LUMA_IPS=work/frontier/pkg02/luma/code.ips frontier/probes/package/boot.sh SAVE dist/oras-frontier-alpha-v0.2
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'frontier'), str(ROOT / 'scripts')]
import luma  # noqa: E402
import package  # noqa: E402
import patch  # noqa: E402
from build_patch import diff_ips  # noqa: E402
from formats import apply_ips, read_ips  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('package', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    if not out.is_relative_to((ROOT / 'work').resolve()):
        p.error('--out must be under work/')
    manifest = json.loads((a.package / 'manifest.json').read_text())
    rel = f'luma/titles/{package.TITLE}/code.ips'
    ips = (a.package / rel).read_bytes()
    if hashlib.sha256(ips).hexdigest() != manifest['files'][rel]:
        sys.exit(f'{rel} differs from the package manifest')
    clean = patch.CLEAN.read_bytes()
    package_code = apply_ips(clean, read_ips(ips))
    code = luma.overlay(package_code)
    lab = diff_ips(clean, code)
    if apply_ips(clean, read_ips(lab)) != code:
        sys.exit('IPS round trip failed')
    check = package.console_check(a.package / rel)
    if check != manifest['console_check']:
        sys.exit('console_check differs from the package manifest')
    text = hashlib.sha256(code[:patch.CAVE_END - patch.BASE]).hexdigest()
    assert text == check['code_with_luma_sha256_text']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'package-code.bin').write_bytes(package_code)
    (out / 'code.bin').write_bytes(code)
    (out / 'code.ips').write_bytes(lab)
    print(f'{out}/code.ips SHA-256 {hashlib.sha256(lab).hexdigest()} (package code.ips + Luma payload at '
          f'{luma.AT:#x}; hooks at {patch.HOOKS:#x}: {check["hooks_first16"]})')


if __name__ == '__main__':
    main()
