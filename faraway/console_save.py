#!/usr/bin/env python3
"""Lay out the Mew-event test save for restoring with Checkpoint on a 3DS.

The save is not edited here. It was written by the game itself in Azahar: postdelta-route102.main (a copy of
inputs/save with flags 2720/2729 and laboratory balls) taken to the Lilycove harbour through the development
warp, then saved from the in-game menu one tile north of the door. This script only checks that file (hash,
the 58 block checksums, zone, flags, works, key items) and copies it as Checkpoint expects a backup:
<backup folder>/main. The output stays under dist/ or work/, both excluded from Git.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'faraway'))
sys.path.insert(0, str(ROOT / 'scripts'))
import save_event as se  # noqa: E402
import save_fixture as sf  # noqa: E402

SOURCE = ROOT / 'work/faraway/console-test/harbor-ready.main'
SOURCE_SHA256 = 'e97f367403c87e720d70fd32218178da3213294638d4fe9ceea6c443caba66c4'
BACKUP = 'MewTest-puerto-Calagua'
EXPECTED_FLAGS = {2720: 1, 2729: 1, 3026: 0, 3031: 0, 3034: 0}
EXPECTED_WORKS = {16665: 0, 16667: 0}
README = """Partida de prueba del evento de Mew (Rubí Omega EUR 1.0 + paquete oras-mew-luma-preview v0.1 o posterior)

QUÉ ES
Copia de laboratorio guardada por el propio juego en el puerto de Ciudad Calagua,
junto al marinero que entrega el Mapa Viejo. Procede de tu partida de inputs/save
(Ruta 102, 0 medallas) con estos cambios artificiales:
- Flags 2720 (Salón de la Fama) y 2729 (Episodio Delta completado) activados.
- 5 Master Ball y 20 Ultra Ball en la Mochila.
No sirve para seguir la historia: úsala solo para probar el evento.

ANTES DE NADA
1. Instala el paquete oras-mew-luma-preview en SD:/luma/titles/000400000011C400/
   y activa "Enable game patching" en Luma. Juego sin actualización.
2. Abre Checkpoint, elige Rubí Omega y haz Backup de tu partida actual.
   Esa copia es la que restaurarás al terminar.

RESTAURAR ESTA PARTIDA
3. Con la consola apagada, copia la carpeta {backup}/ (con el archivo main dentro)
   a la carpeta que Checkpoint creó para Rubí Omega en el paso 2:
   SD:/3ds/Checkpoint/saves/<carpeta de Rubí Omega>/{backup}/main
   (es la carpeta donde ya está tu copia del paso 2).
4. En Checkpoint: Rubí Omega -> {backup} -> Restore. Confirma.
5. Inicia el juego y pulsa Continuar. Apareces en el puerto de Calagua.

QUÉ PROBAR (anota lo que pase en cada paso)
a. Habla con el marinero de delante: "Ruben ha obtenido un Mapa Viejo".
   Al terminar aparece el capitán Arenque a la izquierda.
b. Habla otra vez con el marinero: no debe dar un segundo mapa.
c. Habla con Arenque, responde Sí: viaje a Isla Suprema (nombre abajo).
d. Entra al claro. Mew dice "¡Miu!" y huye 4 veces al acercarte.
   Acorralado ("¡Mew no tiene adónde huir!"), habla con él: combate Nv. 30.
e. Prueba huir (el equipo es de nivel 6-12; Mew puede debilitarlo): sal del claro
   y vuelve, Mew debe estar otra vez. Después captúralo con una Master Ball.
f. Guarda, apaga, vuelve a cargar: Mew no reaparece. Arenque te lleva de vuelta
   a Calagua y puede volver a llevarte a la isla.

DEJARLO COMO ESTABA
En Checkpoint: Rubí Omega -> tu copia del paso 2 -> Restore.
Para quitar el mod, borra SD:/luma/titles/000400000011C400/ (o restaura la carpeta
de mods que tenías).

Probado en Azahar: la partida carga en el puerto con el paquete (sin warp de
desarrollo), el marinero entrega el mapa y aparece Arenque. Aún no probada en 3DS.
"""


def check(data):
    sf.blocks(data)    # raises on any of the 58 block checksums
    where = se.place(data)
    if where['zone'] != 317:
        raise ValueError(f'Save is not in the Lilycove harbour: {where}')
    flags = {n: se.flag(data, n) for n in EXPECTED_FLAGS}
    works = {n: se.work(data, n) for n in EXPECTED_WORKS}
    if flags != EXPECTED_FLAGS or works != EXPECTED_WORKS:
        raise ValueError(f'Unexpected event state: {flags} {works}')
    bag = sf.inspect(data)['bag']
    if any(item == 442 for item, _ in bag['key']):
        raise ValueError('The Old Sea Map is already in the bag')
    return where, bag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/oras-mew-checkpoint-test-v0.1')
    out = parser.parse_args().output.resolve()
    if not any(out.is_relative_to(ROOT / folder) for folder in ('dist', 'work')):
        parser.error('Output must be under dist/ or work/')
    if out.exists():
        parser.error('Output directory must be new')
    data = SOURCE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError(f'Unexpected save: {SOURCE}')
    where, bag = check(data)
    (out / BACKUP).mkdir(parents=True)
    shutil.copyfile(SOURCE, out / BACKUP / 'main')
    if (out / BACKUP / 'main').read_bytes() != data:
        raise ValueError('Copy verification failed')
    (out / 'LEEME.txt').write_text(README.format(backup=BACKUP), encoding='utf-8')
    print(f'{out / BACKUP / "main"}\nzone {where["zone"]} tile ({where["tile_x"]}, {where["tile_y"]}); '
          f'bag {bag}; SHA-256 {SOURCE_SHA256}')


if __name__ == '__main__':
    main()
