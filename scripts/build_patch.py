#!/usr/bin/env python3
"""Build the experimental held Exp. Share overlay from the verified baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile

from formats import (apply_ips, build_text, check_file, garc_entries, read_ips, rebuild_garc, sha256,
                     text_lines, text_to_words, words_to_text)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'baseline/oras/repolished'


def guarded_writes(original, specification):
    if hashlib.sha256(original).hexdigest() != specification['sha256']:
        raise ValueError(f'Wrong SHA-256 for {specification["path"]}')
    result = bytearray(original)
    for write in specification.get('writes', []):
        offset = write['offset']
        before, after = bytes.fromhex(write['before']), bytes.fromhex(write['after'])
        if len(before) != len(after) or original[offset:offset + len(before)] != before:
            raise ValueError(f'Unexpected bytes at {specification["path"]}+{offset:#x}')
        result[offset:offset + len(after)] = after
    return bytes(result)


def guarded_texts(data, specification):
    """Replace or append text lines in a GARC; the GARC is rebuilt if a size changes."""
    if not specification.get('texts'):
        return data
    entries = {entry: (offset, length) for entry, sub, offset, length in garc_entries(data) if sub == 0}
    edited = {}
    for change in specification['texts']:
        entry = change['entry']
        if entry not in edited:
            offset, length = entries[entry]
            edited[entry] = text_lines(data[offset:offset + length])
        lines, flags = edited[entry]
        new = text_to_words(change['after'])
        if change.get('append'):
            if change['line'] != len(lines):
                raise ValueError(f'Unexpected line count at {specification["path"]} {entry}')
            lines.append(new)
            flags.append(0)
            continue
        old = lines[change['line']]
        if words_to_text(old) != change['before'] or text_to_words(change['before']) != old:
            raise ValueError(f'Unexpected text at {specification["path"]} {entry}:{change["line"]}')
        # Zero words after the terminator keep the original size when the text fits.
        lines[change['line']] = new + [0] * (len(old) - len(new))
    replacements = {}
    for entry, (lines, flags) in edited.items():
        blob = build_text(lines, flags)
        if text_lines(blob) != (lines, flags):
            raise ValueError(f'Text rebuild mismatch at {specification["path"]} {entry}')
        replacements[(entry, 0)] = blob
    if any(len(blob) != entries[entry][1] for (entry, _), blob in replacements.items()):
        return rebuild_garc(data, replacements)
    result = bytearray(data)
    for (entry, _), blob in replacements.items():
        offset, length = entries[entry]
        result[offset:offset + length] = blob
    return bytes(result)


def cro_hashes(data):
    code, size, initialized, data_size, name = struct.unpack_from('<5I', data, 0xB0)
    return [hashlib.sha256(data[start:end]).digest() for start, end in
            [(0x80, code), (code, code + size), (name, initialized),
             (initialized, initialized + data_size)]]


def rehash_cro(original, changed):
    if b''.join(cro_hashes(original)) != original[:0x80]:
        raise ValueError('Original CRO hashes do not match')
    return b''.join(cro_hashes(changed)) + changed[0x80:]


def update_crr(original, old_cro, new_cro):
    offset, count = struct.unpack_from('<II', original, 0x350)
    hashes = [original[offset + 32 * i:offset + 32 * (i + 1)] for i in range(count)]
    before = hashlib.sha256(old_cro[:0x80]).digest()
    after = hashlib.sha256(new_cro[:0x80]).digest()
    if hashes.count(before) != 1 or hashes != sorted(hashes):
        raise ValueError('Unexpected CRR hash table')
    hashes[hashes.index(before)] = after
    result = bytearray(original)
    result[offset:offset + 32 * count] = b''.join(sorted(hashes))
    # This updates hash membership, not Nintendo's RSA signature.
    return bytes(result)


def diff_ips(before, after):
    if len(after) < len(before):
        raise ValueError('IPS diffs cannot shrink a file')
    # Bytes past the original end are always written, so the file grows to its new size.
    differs = lambda i: i >= len(before) or before[i] != after[i]
    patch, index = bytearray(b'PATCH'), 0
    while index < len(after):
        if not differs(index):
            index += 1
            continue
        start = index
        while index < len(after) and differs(index) and index - start < 65535:
            index += 1
        if start == 0x454F46:
            start -= 1
        patch.extend(start.to_bytes(3, 'big'))
        patch.extend((index - start).to_bytes(2, 'big'))
        patch.extend(after[start:index])
    patch.extend(b'EOF')
    return bytes(patch)


def patched_assets():
    lock = json.loads((ROOT / 'reports/source-lock.json').read_text())
    manifest = json.loads((ROOT / 'baseline/oras/manifest.json').read_text())
    if manifest['source_lock_sha256'] != sha256(ROOT / 'reports/source-lock.json'):
        raise ValueError('Baseline provenance differs from source lock')
    # Every packaged Repolished file is checked, including the unchanged IPS.
    for entry in lock['mod_files']:
        check_file(ROOT / entry['path'], entry)
    spec = json.loads((ROOT / 'reports/held-exp-share-spec.json').read_text())
    changed, originals = {}, {}
    for entry in spec['patches']:
        relative = entry['path']
        check_file(BASE / relative, manifest['repolished'][relative])
        originals[relative] = (BASE / relative).read_bytes()
        changed[relative] = guarded_texts(guarded_writes(originals[relative], entry), entry)
    crr = 'romfs/.crr/static.crr'
    check_file(BASE / crr, manifest['repolished'][crr])
    originals[crr] = (BASE / crr).read_bytes()
    changed[crr] = originals[crr]
    for cro in sorted(path for path in changed if path.endswith('.cro')):
        changed[cro] = rehash_cro(originals[cro], changed[cro])
        changed[crr] = update_crr(changed[crr], originals[cro], changed[cro])
    return originals, changed


def build(output):
    originals, changed = patched_assets()
    lock = json.loads((ROOT / 'reports/source-lock.json').read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.patch-', dir=output.parent) as tmp:
        stage = Path(tmp)
        overlay = stage / 'mods' / lock['title_id'].upper()
        shutil.copytree(ROOT / lock['mod_root'] / 'romfs', overlay / 'romfs')
        shutil.copyfile(ROOT / lock['mod_root'] / 'code.ips', overlay / 'code.ips')
        metadata = {'status': 'experimental; validated in Azahar (reports/gameplay-validation.json) and on a Luma3DS console',
                    'title_id': lock['title_id'], 'source_lock_sha256': sha256(ROOT / 'reports/source-lock.json'),
                    'spec_sha256': sha256(ROOT / 'reports/held-exp-share-spec.json'),
                    'changes': [], 'overlay_files': {}}
        for relative, data in changed.items():
            destination = overlay / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            diff = diff_ips(originals[relative], data)
            if apply_ips(originals[relative], read_ips(diff)) != data:
                raise ValueError(f'IPS round-trip failed: {relative}')
            patch_path = stage / 'patches' / (relative + '.ips')
            patch_path.parent.mkdir(parents=True, exist_ok=True)
            patch_path.write_bytes(diff)
            metadata['changes'].append({'path': relative,
                'before_sha256': hashlib.sha256(originals[relative]).hexdigest(),
                'after_sha256': hashlib.sha256(data).hexdigest(), 'ips_size': len(diff)})
        for path in sorted(overlay.rglob('*')):
            if path.is_file():
                metadata['overlay_files'][str(path.relative_to(overlay))] = sha256(path)
        (stage / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (stage / 'LEEME.txt').write_text(
            'Prototipo experimental para Omega Ruby 1.0 + Repolished 1.7.6.\n'
            'Objeto 216: Repartir Exp., ahora en el bolsillo Objetos y sin interruptor global.\n'
            'Participantes: experiencia normal. Portadores en reserva: mitad calculada por el juego.\n'
            'Otras reservas: sin experiencia ni EV por reparto. EV del portador: completos.\n'
            'Al terminar el combate el portador muestra su propio mensaje de EXP.\n'
            'DexNav: la casilla del nivel de busqueda muestra nivel/racha (p. ej. 23/7).\n'
            'Varios portadores reciben reparto; no hay restriccion a un solo ejemplar.\n'
            'Entrega en la historia sin cambios: el evento original entrega el mismo objeto 216.\n'
            'Textos: descripcion (espanol e ingles) y explicacion al recibirlo (espanol).\n'
            'mods/ contiene el paquete local completo con Repolished; no se ha instalado automaticamente.\n'
            'patches/ contiene solo diferencias IPS sobre la base Repolished, no sobre el juego limpio.\n'
            'El generador comprueba hashes y bytes; IPS por si solo no valida la base.\n'
            'Se actualizan hashes CRO y la tabla CRR, no la firma RSA de Nintendo.\n'
            'Probado en Azahar 2126.2: portador en reserva, participante, debilitado y sin objeto.\n'
            'Probado en 3DS con Luma3DS. Sin probar combates dobles ni hordas.\n'
            'Consultar reports/estado.md y reports/ingenieria.md para pruebas y limites.\n')
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    print(f'Generated experimental patch: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/held-exp-share-v0.5')
    output = parser.parse_args().output.resolve()
    if not any(p in output.parents for p in [ROOT / 'dist', ROOT / 'work']):
        parser.error('Output must be inside dist/ or work/')
    if output.exists():
        parser.error('Output exists; choose another directory')
    build(output)


if __name__ == '__main__':
    main()
