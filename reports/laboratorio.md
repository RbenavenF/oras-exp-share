# Laboratorio de Azahar — 2026-10-31

Perfil independiente en `work/azahar-lab/`, con copia del volcado, copia del
paquete generado y carpetas XDG propias. Los inputs y el perfil personal no
se usan para escribir. Xvfb, xdotool y libxdo se extrajeron de paquetes Debian
en `work/azahar-runtime/`; no se instalaron en el sistema. Azahar se ejecuta
desde la AppImage extraída, con renderizado por software llvmpipe.

`scripts/azahar_lab.py` prepara/inicia la sesión, captura su framebuffer,
envía controles y la detiene. Las acciones sobre X11 requieren autorización
fuera del sandbox; las capturas son lecturas de un archivo local. La sesión
queda registrada en `work/azahar-lab/session.json`.

Comprobado: arranque de Omega Ruby, aplicación de code.ips y sustituciones
LayeredFS en el log, introducción de Repolished y movimiento por Villa Raíz.
También se ha entrado en el primer combate y se ha registrado la carga de
DllBattle (`reports/azahar-loader.log`). Después se jugaron los cuatro combates de prueba (reserva, participante,
debilitado y sin objeto); ver `reports/estado.md`. Nada de esto valida una
consola real.

## Preparación y lectura de partidas

`scripts/save_fixture.py main` valida los 58 bloques del archivo ORAS y
descifra el equipo para imprimir especie, objeto, EXP, EV, nivel y HP.
Rechaza checksums de bloques o Pokémon incorrectos.

```bash
source scripts/env.sh
python scripts/save_fixture.py work/partida-base/main
python scripts/save_fixture.py work/partida-base/main \
  --sha256 HASH_OBTENIDO --scenario reserve --output work/prueba-reserva/main
```

Para una partida existente que ya tiene el Repartir Exp. como objeto clave:

```bash
python scripts/save_fixture.py ORIGEN/main --move-exp-share \
  --sha256 HASH_OBTENIDO --output work/partida-convertida/main
```

Solo mueve el objeto 216 de bolsillo; no toca el equipo.

El archivo de entrada debe ser una partida guardada con un Pokémon inicial.
La salida debe ser nueva y estar bajo `work/`. Las variantes `reserve`,
`participant`, `fainted` y `none` crean tres clones del primer Pokémon para
controlar la comparación: mismo nivel/EXP y cero EV, con el objeto 216 en el
slot correspondiente. Se conserva el original, se recalculan checksums y se
valida el resultado. Son datos artificiales para pruebas locales.

El lector ya se contrastó con el primer guardado completo de esta sesión:
58 checksums válidos, Torchic de nivel 5, 159 EXP y 1 EV de Ataque después
del primer combate. Las cuatro copias se generaron en `work/test-saves/`
con manifiesto de hashes y se usaron en los combates comparativos. El archivo inicial de selección de idioma no era suficiente.
Pruebas unitarias: cifrado/descifrado de las 32 variantes de orden de bloques,
conservación de estadísticas de equipo y rechazo de datos dañados.

Referencias primarias del formato consultadas en PKHeX:

- [Bloques y checksums](https://github.com/kwsch/PKHeX/blob/5bfb32305c8af70e5885f6ac0800e50b3867f197/PKHeX.Core/Saves/Blocks/BlockInfo3DS.cs).
- [Mapa de ORAS](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Saves/Access/SaveBlockAccessor6AO.cs).
- [Cifrado de Pokémon](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/Util/PokeCrypto.cs).
- [Campos PK6](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/PK6.cs).

El generador de partidas es independiente del generador del parche y no
instala partidas automáticamente.
