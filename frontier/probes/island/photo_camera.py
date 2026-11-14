#!/usr/bin/env python3
"""Create a disposable Azahar photo mod, changing ONLY area 229's AD[3].

source scripts/env.sh
python frontier/probes/island/photo_camera.py NAME --pitch -89 --distance 1000 --fov 110
F11_OUT=work/f11/finish/NAME bash frontier/probes/island/boot.sh work/f11/finish/plaza-final.sav

Never ship this mod. The production candidate and its evidence remain untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

from landscape import CP, OUT, ROOT, entry, garc_entries


def proof(source, target):
    """Reject any change beyond the private island's camera table."""
    before = {str(f.relative_to(source)): f for f in source.rglob('*') if f.is_file()}
    after = {str(f.relative_to(target)): f for f in target.rglob('*') if f.is_file()}
    assert before.keys() == after.keys(), 'Photo mod file set changed'
    changed = [name for name in before if before[name].read_bytes() != after[name].read_bytes()]
    assert changed == ['romfs/a/0/1/4'], changed
    old, new = (before[changed[0]].read_bytes(), after[changed[0]].read_bytes())
    assert len(garc_entries(old)) == len(garc_entries(new))
    areas = [i for i in range(len(garc_entries(old))) if entry(old, i) != entry(new, i)]
    assert areas == [229], areas

    def split(data):
        assert data[:2] == b'AD'
        count = struct.unpack_from('<H', data, 2)[0]
        offsets = struct.unpack_from(f'<{count + 1}I', data, 4)
        return [data[a:b] for a, b in zip(offsets, offsets[1:])]

    a, b = split(entry(old, 229)), split(entry(new, 229))
    assert len(a) == len(b)
    subfiles = [i for i in range(len(a)) if a[i] != b[i]]
    assert subfiles == [3], subfiles
    return dict(changed_mod_files=changed, changed_areas=areas, changed_AD_subfiles=subfiles)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('name')
    p.add_argument('--source', default='final')
    p.add_argument('--pitch', type=float, default=-89.9)
    p.add_argument('--distance', type=float, default=1000)
    p.add_argument('--fov', type=float, default=110)
    args = p.parse_args()
    for name in (args.name, args.source):
        if not name.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Simple workspace name required')
    source, target = OUT / args.source, OUT / args.name
    target.mkdir()  # Fail closed: never replace previous evidence or candidate.
    for part in ('game', 'ws', 'mod'):
        shutil.copytree(source / part, target / part)
    marker = target / 'ws/_original_garcs/taken-from.txt'
    marker.write_text(marker.read_text().replace(str(source / 'game'), str(target / 'game')))
    classes = target / 'classes'
    classes.mkdir()
    java = Path(__file__).with_name('PhotoCamera.java')
    subprocess.run(['javac', '--release', '8', '-nowarn', '-cp', CP, '-d', str(classes), str(java)], check=True)
    with (target / 'camera.log').open('w') as log:
        subprocess.run(['java', '-Xmx4g', '-Djava.awt.headless=true', '-cp', f'{classes}:{CP}',
                        'faraway.PhotoCamera', str(target / 'game'), str(target / 'ws'),
                        str(args.pitch), str(args.distance), str(args.fov)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copyfile(target / 'game/a/0/1/4', target / 'mod/romfs/a/0/1/4')
    measured = proof(source / 'mod', target / 'mod')
    hashes = {str(f.relative_to(target / 'mod')): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted((target / 'mod').rglob('*')) if f.is_file()}
    (target / 'hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    measured.update(settings=vars(args), source=str(source.relative_to(ROOT)),
                    helper_sha256=hashlib.sha256(java.read_bytes()).hexdigest(), photo_only=True)
    (target / 'camera-only-proof.json').write_text(json.dumps(measured, indent=2) + '\n')
    print(json.dumps(measured, indent=2))


if __name__ == '__main__':
    main()
