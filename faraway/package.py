#!/usr/bin/env python3
"""Package the locally validated Mew overlay with v0.5 in Luma's SD directory layout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TITLE = '000400000011C400'
README = """Omega Ruby Repolished + Repartir Exp. + racha DexNav + evento de Mew
Prototipo jugable. Base: Omega Ruby EUR 1.0, sin actualización, Repolished 1.7.6.
El evento de Mew está probado en Azahar; todavía no está validado en una 3DS.

INSTALACIÓN EN 3DS CON LUMA
1. Apaga la consola. Guarda una copia de tu partida y de la carpeta de mods actual.
2. Sustituye la carpeta del título por la incluida en este paquete:
   SD:/luma/titles/000400000011C400/
   Dentro deben quedar code.ips y romfs/. Se incluye romfs/.crr/static.crr.
   El paquete contiene Repolished, Repartir Exp., DexNav y Mew combinados.
3. Activa Enable game patching en Luma (SELECT al encender; START para guardar).
4. Inicia Rubí Omega sin actualización. No hay que instalar una CIA ni editar la partida.

ACTIVACIÓN DEL EVENTO
Completa el Episodio Delta. Ve al puerto de Ciudad Calagua y habla con el
marinero nuevo para recibir el Mapa Viejo. Habla con Arenque y acepta viajar.
En el claro de Isla Suprema, persigue a Mew: huye cuatro veces; al quedar
acorralado, habla con él para combatir contra Mew de nivel 30.
Si huyes del combate, sal del claro y vuelve para reintentarlo. Tras capturarlo
no reaparece. Este paquete no incluye el acceso de desarrollo desde Ruta 102.

ESTADO
Faltan el escenario definitivo (playa, hierba alta y escenas), las pruebas de
derrotar a Mew y perder todo el equipo, y la validación del evento en consola.
No contiene partidas, claves ni ROM completa. Contiene archivos derivados del
volcado local: úsalo localmente; estos archivos quedan excluidos de Git.
Nada se instala automáticamente. manifest.json registra los hashes del paquete.
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_files(directory, expected):
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != set(expected):
        raise ValueError(f'File set differs from validated manifest: {directory}')
    for rel, digest in expected.items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError(f'Unsafe manifest path: {rel}')
        if sha(directory / rel) != digest:
            raise ValueError(f'Hash mismatch: {directory / rel}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/oras-mew-luma-preview-v0.1')
    out = parser.parse_args().output.resolve()
    archive = out.parent / (out.name + '.zip')
    if not any(out.is_relative_to(ROOT / folder) for folder in ('dist', 'work')):
        parser.error('Output must be under dist/ or work/')
    if out.exists() or archive.exists():
        parser.error('Output directory and ZIP must both be new')
    base_dir = ROOT / 'dist/held-exp-share-v0.5'
    base = json.loads((base_dir / 'manifest.json').read_text())
    validation_path = ROOT / 'reports/faraway-validation.json'
    validation = json.loads(validation_path.read_text())
    if sha(ROOT / 'reports/source-lock.json') != base['source_lock_sha256']:
        raise ValueError('Base source lock changed')
    for rel, digest in validation['sources'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError(f'Validated source changed: {rel}')
    base_mod = base_dir / 'mods' / TITLE
    overlay = ROOT / 'work/faraway/build/overlay'
    checked_files(base_mod, base['overlay_files'])
    checked_files(overlay, validation['final_overlay_sha256'])
    expected = {**base['overlay_files'], **validation['final_overlay_sha256']}
    target = out / 'luma/titles' / TITLE
    for rel in sorted(expected):
        source = overlay / rel if rel in validation['final_overlay_sha256'] else base_mod / rel
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    checked_files(target, expected)
    (out / 'LEEME.txt').write_text(README, encoding='utf-8')
    (out / 'manifest.json').write_text(json.dumps({
        'title_id': TITLE, 'status': 'preview; Mew event validated in Azahar, pending 3DS test',
        'base_manifest_sha256': sha(base_dir / 'manifest.json'),
        'validation_report_sha256': sha(validation_path), 'development_warp': False,
        'files': {f'luma/titles/{TITLE}/{rel}': digest for rel, digest in sorted(expected.items())},
    }, indent=2) + '\n')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(out).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, path.read_bytes())
    with zipfile.ZipFile(archive) as z:
        for path in (p for p in out.rglob('*') if p.is_file()):
            if hashlib.sha256(z.read(path.relative_to(out).as_posix())).hexdigest() != sha(path):
                raise ValueError(f'ZIP verification failed: {path}')
    print(f'{archive}\n{len(expected)} mod files; SHA-256 {sha(archive)}')


if __name__ == '__main__':
    main()
