#!/usr/bin/env python3
"""Battle Frontier alpha package for Luma: Repolished 1.7.6 + v0.5 (held Exp. Share, DexNav streak) + the Frontier,
without the Mew event (user decision, 2026-11-11). Laid out as SD:/luma/titles/<title>/.

  python frontier/package.py [--output dist/oras-frontier-alpha-v0.3] [--replace] [--allow-dirty]
  python frontier/package.py checkpoint SAVE [--output dist/oras-frontier-checkpoint-test-v0.3] [--replace]

Steps (the first fails with any other dump, mod or base package):
1. Inputs: the ROM and Repolished files of reports/source-lock.json, the clean and Repolished code.bin
   (frontier/patch.py HASHES) and the v0.5 base package (dist/held-exp-share-v0.5, its manifest).
2. Build from the committed tree (HEAD; a dirty tree is refused unless --allow-dirty, recorded in the manifest):
   frontier/overlay.py over v0.5's romfs (no dev overlay: no Route 102 warp, no Mew harbor), full island.
3. Package = v0.5's mod files with the build's code.ips and romfs files on top; LEEME.txt; manifest.json with the
   SHA-256 of every file; a ZIP next to the folder, verified against the folder.

`checkpoint` copies a lab save (made with this package, reports/frontier.md §38) into Checkpoint's layout, refusing
any save whose SHA-256 is not CHECKPOINT_SAVE_SHA256. Outputs contain game data: dist/ and work/ only, never Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TITLE = '000400000011C400'
VERSION = 'oras-frontier-alpha-v0.3'
BASE_DIR = ROOT / 'dist/held-exp-share-v0.5'
SOURCE_LOCK = ROOT / 'reports/source-lock.json'
BUILD = ROOT / 'work/frontier/package/build'
# Romfs files the Frontier build must write (on top of v0.5): scripts, texts, maisonpkN, the island's zone/map/area
# archives and the patched CROs with their CRR. Measured from overlay.py's output, 2026-11-11; a/1/8/3 (maisontrN,
# the Brains' trainers) since F8-CEREBROS-BASE, measured 2026-11-13.
BUILD_FILES = {'a/0/1/3', 'a/0/1/4', 'a/0/2/9', 'a/0/3/9', 'a/0/4/0', 'a/1/3/7', 'a/1/8/2', 'a/1/8/3', 'DllBattle.cro',
               'DllField.cro', '.crr/static.crr', *(f'a/0/7/{k}' for k in range(1, 10)),
               *(f'a/0/8/{k}' for k in range(7))}
CHECKPOINT = 'oras-frontier-checkpoint-test-v0.3'
CHECKPOINT_FOLDER = 'FrenteTest-puerto-Calagua'
# work/frontier/pkg/saves/checkpoint_harbor.sav: saved by the game with the package at the Lilycove harbor (§38)
CHECKPOINT_SAVE_SHA256 = '5ddaa992c5aea98a3da1af80c1f2486b6d2db1690da0ae8be84abf2397edeffa'

README = """Omega Ruby Repolished + Repartir Exp. + racha DexNav + Frente de Batalla (alfa v0.3)

*** AVISO ANTES DE ACTUALIZAR DESDE LA v0.1 O LA v0.2 ***
La isla del Frente es un mapa NUEVO. Si tu partida está guardada en la isla o
dentro de un edificio del Frente, con la alfa anterior instalada vuelve a Calagua en
el ferry y GUARDA ALLÍ antes de instalar la v0.3. Una partida guardada en la isla
vieja aparece en la misma casilla del mapa nuevo, que puede ser mar o muro y
dejarte atrapado. Haz además copia con Checkpoint.

ESTADO
Alfa de prueba. Las siete instalaciones y sus Cerebros tienen pruebas en Azahar
(el emulador), con límites pendientes. El usuario confirmó que la v0.2 funciona en
su 3DS; la v0.3 NO está probada aún en consola. Haz copia de tu partida antes de
jugar (Checkpoint). No incluye el evento de Mew.

NUEVO EN LA v0.3
- La Isla del Frente tiene ahora la distribución del Frente de Batalla de
  Pokémon Esmeralda: el mismo contorno, caminos y escaleras, y cada instalación en
  el sitio de su edificio de Esmeralda, con la puerta en su casilla. El ferry llega
  al muelle del suroeste.
- Los edificios son AÚN PROVISIONALES: las mismas casas de la v0.2, colocadas en el
  hueco de su edificio de Esmeralda. Los árboles, vallas y adornos de Esmeralda se
  ven todavía como hierba o roca, y la escalera puede verse blanca.
- Nada más cambia: interiores, combates, reglas, Cerebros y textos son los de la
  v0.2. Sin Doble ni Nivel Libre (los menús siguen cerrados).

BASE EXACTA (no funciona con otra)
- Pokémon Rubí Omega europeo, versión 1.0, SIN la actualización 1.4. Si la tienes
  instalada, desinstálala desde Gestión de datos > Software descargable.
- Omega Ruby Repolished 1.7.6. Este paquete YA lo contiene: no instales Repolished
  aparte, sustituye su carpeta.
- Incluye la v0.5 de Repartir Exp. equipable y la racha de DexNav, sin cambios.

INSTALACIÓN CON LUMA
1. Lee el AVISO de arriba. Copia tu partida con Checkpoint. Apaga la consola y
   guarda una copia de la carpeta SD:/luma/titles/000400000011C400/ si ya tienes
   una (Repolished, v0.5, v0.2...).
2. Borra esa carpeta y copia en su lugar la de este paquete:
   SD:/luma/titles/000400000011C400/  (dentro: code.ips y romfs/).
   romfs/ incluye DllBattle.cro, DllField.cro y .crr/static.crr actualizados:
   no mezcles estos tres con los de otro mod ni con los de otra alfa.
3. Activa «Enable game patching» en Luma (SELECT al encender; START para guardar).
4. Inicia Rubí Omega. No hay que instalar una CIA ni editar la partida.
Para volver a la v0.2, la v0.5 o Repolished: guarda FUERA de la isla, apaga,
borra la carpeta y vuelve a copiar la que guardaste en el paso 1.

CÓMO LLEGAR AL FRENTE
1. Gana la Liga Pokémon (entrar en el Salón de la Fama).
2. Ve al puerto de Ciudad Calagua y habla con el marinero del muelle: te da el
   Pase del Frente (objeto clave). Solo lo da tras ganar la Liga, y una vez.
3. Habla con el empleado del ferry S.S. Marea (Calagua o Portual; pide el Ticket
   del Barco como siempre) y elige «Isla del Frente».
4. Llegas al muelle del suroeste. Sube hacia el norte para llegar a los
   edificios. El empleado del muelle te devuelve a Calagua. Se puede guardar en
   la isla.

LAS SIETE INSTALACIONES (Individual; base Nivel 50 y rango Normal, salvo lo indicado)
Solo se puede tener un desafío a medias a la vez: si dejas uno pausado, las demás
recepciones te piden terminarlo primero. Los alquileres no sustituyen tu equipo
guardado ni tu caja. Puede haber cambios normales del juego: curación, amistad,
recuerdos o cintas; los Pokémon por debajo del nivel 50 no suben hasta él.
Situación en la isla (la de Esmeralda) y edificio provisional entre paréntesis.
- Fábrica Batalla (oeste; gimnasio): eliges 3 Pokémon de alquiler de 6, rondas
  de 7 combates y tras cada victoria, salvo la séptima, puedes cambiar uno por uno
  del rival. PB de Esmeralda. Cerebro: Noland (combates 21 y 42). Sin Doble ni
  Nivel Libre ni cartel de récords.
- Torre Batalla (norte, en el centro; casa de tejado plano): tu equipo, combates
  seguidos como en la Mansión Batalla, con racha y PB propios. Cerebro: Anabel
  (combates 35 y 70). Textos y reglas de la Mansión.
- Palacio Batalla (sureste; casa de dos plantas): tus Pokémon eligen solos el
  movimiento según su naturaleza y sus PS. Cerebro: Spenser (combates 21 y 42).
  Límites: no hay «no obedece»; el rival no sigue su naturaleza; la presentación y
  la frase de derrota del entrenador esperan que pulses A.
- Arena Batalla (este; casa de paja): combates de 3 turnos; si los dos siguen en
  pie, juicio solo por Cuerpo. Mente y Técnica aún no están implementadas.
  Cambio prohibido mientras el Pokémon siga en pie. Cerebro: Greta (combates 28 y
  56). Textos de la Mansión. Su puerta está en lo alto de una escalera.
- Domo Batalla (noroeste; casa de Pueblo Pardal): torneos de 4 combates;
  inscribes 3 y eliges 2 antes de cada combate. Cerebro: Tucker (final de los
  torneos 5 y 10). Sin cuadro de torneo.
- Tubo Batalla (centro oeste; cabaña): salas con curas, estados, entrenadores y
  Pokémon salvajes; PS, estado y PP se arrastran entre salas. El veneno grave se
  guarda como veneno normal. Los combates fuertes usan rango Súper y los salvajes
  pueden estar por debajo del nivel 50; conservan la presentación de entrenador.
  Cerebro: Lucy (salas 28 y 140). Hay una incidencia de reanudación pendiente de
  reproducir: un desafío volvió a empezar de cero tras regresar al vestíbulo.
- Pirámide Batalla (noreste; casa de tejado azul): siete pisos de cueva con
  entrenadores. Cerebro: Brandon en la cima (tras los pisos 21 y 70). Sin
  oscuridad, objetos ni salvajes todavía.
Cerebros: el primero da el símbolo de plata y el segundo el de oro; con los dos,
vuelven a aparecer en las mismas rachas. Ganarle suma PB extra.
Comunes: sin Doble/Multi ni Nivel Libre; textos en español (los demás idiomas, en
inglés y sin revisar).
El paquete exacto se probó en Azahar simulando lo que Luma escribe en el código:
marinero, ferry, la isla nueva, un combate en cada una de las siete instalaciones
entrando y saliendo por su puerta, la Mansión Batalla original, un combate
salvaje con Repartir Exp. y DexNav, guardado y recarga en la isla y regreso a
Calagua. No se probaron con ese paquete las rondas completas ni los Cerebros (cada
uno se probó al hacerlo, con partidas editadas), el juicio de la Arena, el ferry
de Portual ni otros idiomas (reports/frontier.md).

NO PROBADO EN CONSOLA (solo en Azahar)
- La isla nueva de la v0.3: memoria de la consola con el mapa nuevo cargado (en
  el emulador no hay límite real), sus puertas y la llegada del ferry.
- Probado en consola: v0.5 (Repartir Exp. y DexNav); la v0.2 (confirmación
  general del usuario, sin una lista de pruebas completa); la v0.1 se colgaba.
Si algo se cuelga, apaga manteniendo POWER, restaura tu copia y anota dónde fue.
reports/consola-frente.md (en el repositorio) tiene el orden de pruebas y cómo
comprobar con el depurador de Luma que el código está en su sitio (manifest.json,
«console_check»).

CONTENIDO
No contiene partidas, claves ni la ROM. Contiene ficheros derivados del volcado
local: úsalo solo tú. manifest.json registra el SHA-256 de cada fichero y la base.
"""

CHECKPOINT_README = """Partida de prueba del Frente de Batalla (Rubí Omega EUR 1.0 + paquete {version})

QUÉ ES
Copia de laboratorio guardada por el propio juego en el puerto de Ciudad Calagua,
con la alfa v0.1 instalada y antes de pedir el pase: no tiene nada del Frente,
así que vale igual para {version} (la recorrida en Azahar con este paquete).
Procede de tu partida (Ruta 102), pasando por la de prueba del evento de Mew, con
cambios artificiales: flags 2720 (Liga ganada) y 2729 (Episodio Delta), Ticket del
Barco, y 5 Master Ball y 20 Ultra Ball. No tiene aún el Pase del Frente.
No sirve para seguir la historia: úsala solo para probar el Frente.
SHA-256 del fichero main: {sha}

ANTES DE NADA
1. Instala {version} en SD:/luma/titles/000400000011C400/ (su LEEME.txt).
2. En Checkpoint: Rubí Omega -> Backup de tu partida actual. Es la que restaurarás.

RESTAURAR ESTA PARTIDA
3. Con la consola apagada, copia la carpeta {folder}/ (con el fichero main) dentro
   de la carpeta de Rubí Omega de Checkpoint:
   SD:/3ds/Checkpoint/saves/<carpeta de Rubí Omega>/{folder}/main
4. En Checkpoint: Rubí Omega -> {folder} -> Restore. Confirma.
5. Inicia el juego y pulsa Continuar: apareces en el puerto de Calagua.
Qué probar y en qué orden: reports/consola-frente.md del repositorio.

DEJARLO COMO ESTABA
En Checkpoint: Rubí Omega -> tu copia del paso 2 -> Restore.
"""


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def files_of(directory):
    return {p.relative_to(directory).as_posix(): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def checked_files(directory, expected):
    """The files under `directory` are exactly `expected` ({relative path: SHA-256})."""
    for rel in expected:
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError(f'Unsafe manifest path: {rel}')
    actual = files_of(directory)
    if set(actual) != set(expected):
        raise ValueError(f'File set differs from the manifest: {directory} '
                         f'(extra {sorted(set(actual) - set(expected))}, missing {sorted(set(expected) - set(actual))})')
    for rel, digest in expected.items():
        if actual[rel] != digest:
            raise ValueError(f'Hash mismatch: {directory / rel}')


def check_source_lock(lock_path=SOURCE_LOCK, root=ROOT, rom=True):
    """{path: SHA-256} of the locked inputs (ROM and Repolished files), each checked; raises on any difference."""
    lock = json.loads(Path(lock_path).read_text())
    entries = ([lock['rom']] if rom else []) + list(lock['mod_files'])
    checked = {}
    for entry in entries:
        path = Path(root) / entry['path']
        if not path.is_file():
            raise ValueError(f'Missing input: {entry["path"]}')
        if path.stat().st_size != entry['size'] or sha(path) != entry['sha256']:
            raise ValueError(f'Input differs from the source lock (another dump or mod?): {entry["path"]}')
        checked[entry['path']] = entry['sha256']
    return checked


def check_base(base_dir=BASE_DIR, lock_path=SOURCE_LOCK):
    """v0.5's manifest (built on this source lock) and its mod files; returns (manifest, its mod folder)."""
    base = json.loads((base_dir / 'manifest.json').read_text())
    if sha(lock_path) != base['source_lock_sha256']:
        raise ValueError('v0.5 was built on another source lock')
    mod = base_dir / 'mods' / TITLE
    checked_files(mod, base['overlay_files'])
    return base, mod


def check_code_inputs():
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
    import patch
    for path, expected in patch.HASHES.items():
        if sha(path) != expected:
            raise ValueError(f'{path.relative_to(ROOT)} differs (another dump or mod?)')
    return {str(path.relative_to(ROOT)): expected for path, expected in patch.HASHES.items()}


def git_state(allow_dirty):
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT,
                                    text=True).strip()
    if dirty and not allow_dirty:
        raise ValueError(f'Uncommitted changes (the package must come from a commit):\n{dirty}')
    return head, bool(dirty)


def build(mod, build_dir=BUILD):
    """frontier/overlay.py over v0.5's romfs, full island; returns its log."""
    run = subprocess.run([sys.executable, str(ROOT / 'frontier/overlay.py'), '--out', str(build_dir),
                          '--romfs', str(mod / 'romfs')], cwd=ROOT, capture_output=True, text=True)
    log = run.stdout + run.stderr
    (build_dir.parent / 'build.log').write_text(log)
    if run.returncode:
        raise ValueError(f'overlay.py failed:\n{log[-2000:]}')
    return log


def assemble(base_files, mod, build_dir):
    """{relative path in the title folder: source file}: v0.5's files, the build's on top."""
    built = {f'romfs/{rel}' for rel in files_of(build_dir / 'romfs')}
    if built != {f'romfs/{rel}' for rel in BUILD_FILES}:
        raise ValueError(f'Unexpected build output: {sorted(built ^ {f"romfs/{r}" for r in BUILD_FILES})}')
    sources = {rel: mod / rel for rel in base_files}
    sources.update({rel: build_dir / rel for rel in built})
    sources['code.ips'] = build_dir / 'code.ips'
    return sources


def console_check(code_ips):
    """What Luma's debugger must show on a console with this package (reports/consola-frente.md): Luma's LayeredFS
    payload at patch.CAVE (frontier/luma.py) and our first hook word at patch.HOOKS, with the built code.bin's bytes."""
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
    import luma
    import patch
    from formats import apply_ips, read_ips
    code = apply_ips(patch.CLEAN.read_bytes(), read_ips(Path(code_ips).read_bytes()))
    if any(code[patch.CAVE - patch.BASE:patch.HOOKS - patch.BASE]):
        raise ValueError(f'code.ips writes into Luma\'s reserve {patch.CAVE:#x}-{patch.HOOKS:#x}')
    on_console = luma.overlay(code)
    window = lambda at, n=16: on_console[at - patch.BASE:at - patch.BASE + n].hex()   # noqa: E731
    return {
        'luma_reserve': f'{patch.CAVE:#x}-{patch.HOOKS - 1:#x} (zeros in code.ips; Luma writes {patch.LUMA_PAYLOAD} bytes)',
        'luma_payload_at': f'{patch.CAVE:#x}', 'luma_payload_first16': window(patch.CAVE),
        'hooks_at': f'{patch.HOOKS:#x}', 'hooks_first16': window(patch.HOOKS),
        'luma_branches': {f'{site:#x}': on_console[site - patch.BASE:site - patch.BASE + 4].hex()
                          for site in sorted(luma.HOOKS)},
        'code_with_luma_sha256_text': hashlib.sha256(on_console[:patch.CAVE_END - patch.BASE]).hexdigest(),
    }


def write_zip(out):
    archive = out.parent / (out.name + '.zip')
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
    return archive


def fresh(out, replace, parser):
    """`out` (under dist/ or work/) and its ZIP, removed first with --replace."""
    out = out.resolve()
    archive = out.parent / (out.name + '.zip')
    roots = [(ROOT / folder).resolve() for folder in ('dist', 'work')]   # both may be symlinks (worktrees)
    if not any(out.is_relative_to(r) for r in roots) or out in roots:
        parser.error('Output must be a folder under dist/ or work/')
    if out.exists() or archive.exists():
        if not replace:
            parser.error(f'{out} or its ZIP exists (use --replace)')
        shutil.rmtree(out, ignore_errors=True)
        archive.unlink(missing_ok=True)
    return out


def package(args, parser):
    out = fresh(args.output, args.replace, parser)
    head, dirty = git_state(args.allow_dirty)
    inputs = {**check_source_lock(), **check_code_inputs()}
    base, mod = check_base()
    log = build(mod)
    sources = assemble(base['overlay_files'], mod, BUILD)
    target = out / 'luma/titles' / TITLE
    for rel, source in sorted(sources.items()):
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target / rel)
    (out / 'LEEME.txt').write_text(README, encoding='utf-8')
    files = {f'luma/titles/{TITLE}/{rel}': digest for rel, digest in files_of(target).items()}
    files['LEEME.txt'] = sha(out / 'LEEME.txt')
    manifest = {
        'title_id': TITLE, 'version': VERSION,
        'status': 'alpha; validated in Azahar only, also with Luma\'s payload simulated (reports/frontier.md §49, §50, '
                  '§52); v0.3 not yet run on a console (the user confirmed v0.2 runs on their 3DS)',
        'base': 'Omega Ruby EUR 1.0 without update + Repolished 1.7.6 + held-exp-share v0.5; no Mew event',
        'island': 'Emerald Battle Frontier layout (F11), provisional buildings; save outside the island before '
                  'updating',
        'git_commit': head, 'git_dirty': dirty,
        'inputs_sha256': inputs,
        'base_manifest_sha256': sha(BASE_DIR / 'manifest.json'),
        'build_romfs': sorted(BUILD_FILES), 'development_warp': False, 'mew_event': False,
        'console_check': console_check(sources['code.ips']),
        'files': dict(sorted(files.items())),
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = write_zip(out)
    print(''.join(line + '\n' for line in log.splitlines() if line.startswith('zone 517')), end='')
    print(f'{out}\n{len(files)} files (commit {head[:10]}{" dirty" if dirty else ""}); '
          f'ZIP {archive.name} SHA-256 {sha(archive)}')


def checkpoint(args, parser):
    save = args.save.resolve()
    digest = sha(save)
    if CHECKPOINT_SAVE_SHA256 is None or digest != CHECKPOINT_SAVE_SHA256:
        parser.error(f'{save}: SHA-256 {digest} is not the tested save ({CHECKPOINT_SAVE_SHA256})')
    if save.is_relative_to((ROOT / 'inputs').resolve()):
        parser.error('Never the original save')
    out = fresh(args.output, args.replace, parser)
    (out / CHECKPOINT_FOLDER).mkdir(parents=True)
    shutil.copyfile(save, out / CHECKPOINT_FOLDER / 'main')
    (out / 'LEEME.txt').write_text(CHECKPOINT_README.format(version=VERSION, sha=digest, folder=CHECKPOINT_FOLDER),
                                   encoding='utf-8')
    (out / 'manifest.json').write_text(json.dumps({
        'for_package': VERSION, 'save': f'{CHECKPOINT_FOLDER}/main', 'save_sha256': digest,
        'LEEME.txt': sha(out / 'LEEME.txt')}, indent=2) + '\n')
    print(f'{out}\nsave SHA-256 {digest}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / VERSION)
    parser.add_argument('--replace', action='store_true', help='remove an earlier output first')
    parser.add_argument('--allow-dirty', action='store_true', help='build with uncommitted changes (recorded)')
    cp = sub.add_parser('checkpoint', help='the Checkpoint test save')
    cp.add_argument('save', type=Path)
    cp.add_argument('--output', type=Path, default=ROOT / 'dist' / CHECKPOINT)
    cp.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    try:
        (checkpoint if args.command == 'checkpoint' else package)(args, parser)
    except ValueError as error:
        sys.exit(f'error: {error}')


if __name__ == '__main__':
    main()
