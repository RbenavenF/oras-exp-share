#!/usr/bin/env python3
"""Extract the pinned local dump and apply the pinned Repolished package."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

from formats import apply_ips, check_file, code_map, file_to_va, read_ips, sha256

ROOT = Path(__file__).resolve().parents[1]


def inventory(directory):
    return {str(p.relative_to(directory)): {'size': p.stat().st_size, 'sha256': sha256(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()}


def verify(directory):
    expected = json.loads((directory / 'manifest.json').read_text())
    for name in ['clean', 'repolished']:
        actual = inventory(directory / name)
        if actual != expected[name]:
            raise ValueError(f'Baseline has changed: {name}')
    print(f'Verified: {directory}')


def build(output):
    lock = json.loads((ROOT / 'reports/source-lock.json').read_text())
    mod = ROOT / lock['mod_root']
    actual_mod_files = {str(p.relative_to(ROOT)) for p in mod.rglob('*') if p.is_file()}
    if actual_mod_files != {p['path'] for p in lock['mod_files']}:
        raise ValueError('Mod file list differs from source-lock.json')
    for entry in [lock['rom'], *lock['mod_files'], *lock['tools']]:
        check_file(ROOT / entry['path'], entry)
    rom = ROOT / lock['rom']['path']
    with rom.open('rb') as stream:
        header = stream.read(0x200)
        if header[0x100:0x104] != b'NCSD':
            raise ValueError('Expected NCSD')
        ncch_offset = struct.unpack_from('<I', header, 0x120)[0] * 0x200
        stream.seek(ncch_offset)
        ncch = stream.read(0x200)
    if ncch[0x100:0x104] != b'NCCH':
        raise ValueError('Expected NCCH')
    if f'{struct.unpack_from("<Q", ncch, 0x118)[0]:016x}' != lock['title_id']:
        raise ValueError('Unexpected title ID')
    if ncch[0x150:0x160].rstrip(b'\0').decode() != lock['product_code']:
        raise ValueError('Unexpected product code')
    if not ncch[0x18F] & 4:
        raise ValueError('This extraction pipeline expects the pinned decrypted dump')
    ctrtool = str(ROOT / 'tools/ctrtool/ctrtool')
    dstool = str(ROOT / 'tools/3dstool/3dstool')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.baseline-', dir=output.parent) as tmp:
        stage = Path(tmp)
        clean = stage / 'clean'
        clean.mkdir()
        romfs_image = stage / 'romfs.bin'
        subprocess.run([ctrtool, '--quiet', f'--exheader={clean / "exheader.bin"}',
                        f'--exefsdir={clean / "exefs"}', f'--romfs={romfs_image}', str(rom)], check=True)
        subprocess.run([dstool, '-x', '-t', 'romfs', '-f', str(romfs_image),
                        '--romfs-dir', str(clean / 'romfs')], check=True)
        check_file(clean / 'exefs/code.bin', lock['extracted']['code'])
        check_file(clean / 'exheader.bin', lock['extracted']['exheader'])
        clean_inventory = inventory(clean)
        if sum(p.startswith('romfs/') for p in clean_inventory) != 655:
            raise ValueError('Unexpected RomFS file count')
        repolished = stage / 'repolished'
        shutil.copytree(clean, repolished)
        original = (clean / 'exefs/code.bin').read_bytes()
        records = read_ips((mod / 'code.ips').read_bytes())
        expected_records = json.loads((ROOT / 'reports/repolished-ips-records.json').read_text())
        observed = [{'file_offset': r.offset,
                     'before': original[r.offset:r.offset + len(r.data)].hex(),
                     'after': r.data.hex()} for r in records]
        expected = [{key: row[key] for key in ['file_offset', 'before', 'after']}
                    for row in expected_records]
        if observed != expected:
            raise ValueError('Repolished IPS offsets or before/after bytes differ from pinned records')
        patched = apply_ips(original, records)
        (repolished / 'exefs/code.bin').write_bytes(patched)
        overlays = []
        for source in sorted((mod / 'romfs').rglob('*')):
            if source.is_file():
                relative = source.relative_to(mod)
                destination = repolished / relative
                if not destination.is_file():
                    raise ValueError(f'Overlay target absent in clean RomFS: {relative}')
                overlays.append({'path': str(relative), 'before': sha256(destination), 'after': sha256(source)})
                shutil.copyfile(source, destination)
        segments = code_map((clean / 'exheader.bin').read_bytes(), len(original))
        changes = [{'file_offset': r.offset, 'address': file_to_va(r.offset, segments),
                    'before': original[r.offset:r.offset + len(r.data)].hex(),
                    'after': r.data.hex()} for r in records]
        metadata = {'title_id': lock['title_id'], 'source_lock_sha256': sha256(ROOT / 'reports/source-lock.json'),
                    'segments': segments, 'ips_records': changes, 'romfs_overlays': overlays,
                    'clean_code_sha256': hashlib.sha256(original).hexdigest(),
                    'repolished_code_sha256': hashlib.sha256(patched).hexdigest(),
                    'clean': clean_inventory, 'repolished': inventory(repolished)}
        (stage / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        romfs_image.unlink()
        # The destination must be new; do not overwrite an earlier analysis baseline.
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    print(f'Created: {output}')
    print(f'Code SHA-256: {metadata["repolished_code_sha256"]}')
    print(f'{len(changes)} IPS records; {len(overlays)} RomFS overlays')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'baseline/oras')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if not any(parent in output.parents for parent in [ROOT / 'baseline', ROOT / 'work']):
        parser.error('Output must be inside baseline/ or work/')
    if args.verify_only:
        verify(output)
    elif output.exists():
        parser.error('Output already exists. Use --verify-only or a new output directory.')
    else:
        build(output)


if __name__ == '__main__':
    main()
