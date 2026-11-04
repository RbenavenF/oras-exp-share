# Bitácora — Frente de Batalla

Entradas nuevas al final, con el formato de `frontier/PLAN.md` §8. No se reescriben
las entradas anteriores: si algo era falso, se corrige con una entrada nueva.

## 2026-11-01 — Claude Code (Opus 5.5) — F0: arranque del proyecto
Estado: hecho
Hecho:
- Evento de Mew (`faraway/`) en pausa, con los fallos conocidos anotados en
  `reports/faraway.md` §Pausa. El usuario lo dio por válido como prueba de concepto.
- Plan en `frontier/PLAN.md`: la Fábrica Batalla se construye como «Mansión Batalla
  con equipo de alquiler».
- `frontier/survey.py` (solo lectura) reproduce los hechos de PLAN §3:
  - datos de la Mansión en `a/1/8/2`–`a/1/8/5`, sin cambios en Repolished;
  - la zona 517 es la Mansión Batalla y su script llama a `BattleInstWorkCreate`,
    `SetTrainer`, `StartBattle`, `AddWinCount` y `PlayerSetBP`;
  - no existe ninguna nativa de script que pase un Pokémon de la caja al equipo.
- Protocolo de trazabilidad en `AGENTS.md` y PLAN §8.

Evidencia: `python frontier/survey.py --listings work/frontier/survey` (salida
resumida en PLAN §3; listados en `work/frontier/survey/zone516.lst` y `zone517.lst`).

Commits: ver `git log` (asuntos «Faraway Island: paused…» y «Battle Frontier: plan…»).

Decisiones:
- Se empieza por Nivel 50 Individual, colocado en la zona 517 mediante un NPC.
- Para el equipo de alquiler, la opción preferida es sustituir el equipo del combate y
  no el de la partida. Se confirma o descarta en F1.
- La opción de hacerlo solo con scripts queda descartada, porque no hay nativa
  caja→equipo.

Siguiente paso: F1.
1. Leer `work/frontier/survey/zone517.lst` desde la inscripción hasta `StartBattle`
   (0x1ee4) y documentar el flujo en `reports/frontier.md`.
2. Después, buscar dónde se implementan `BattleInstWorkCreate` y `StartBattle`.

## 2026-11-01 — Claude Code (Opus 5.5) — F1: mapa estático de la Mansión
Estado: en curso (F1 sin evidencia de ejecución)
Hecho:
- Flujo del script 517 documentado en `reports/frontier.md` §1: recepción `0x14f4`,
  modalidad `_CallTrialDownloadApp` `0x16fc`, selección `0x457c`, bucle `0x1e1c`
  con `StartBattle(0, 1)` en `0x1ee4`, victoria/derrota y PB (`0x3de4`).
- Tabla de nativas de campo localizada en `DllField.cro` (pares nombre→función
  relocados; bloque de la Mansión `0xf8b44`–`0xf8cd4`). Cada nativa de la Mansión
  resuelta hasta `code.bin` por los thunks `|static|` (§2).
- Estructura de trabajo de la instalación: 0xB90 bytes, offsets en §3 (índices
  elegidos en `+0x30`, número en `+0x48`, rango `+0x838`, tipo `+0x839`).
- Punto de inyección A localizado: `StartBattle` → `0x1e30b8` crea un `PokeParty`
  nuevo y `0x1e3d2c` copia en él los Pokémon elegidos; la partida no se escribe en
  ese camino. Fábrica de Pokémon desde un conjunto de 16 bytes: `0x1ef904`.
- Espacio: 2556 bytes a cero al final de `.text` (VA `0x579604`–`0x57A000`).
- Herramientas nuevas: `frontier/cro.py` (segmentos y relocaciones CRO),
  `frontier/disasm.py` (CRO por offset), `frontier/disasm_code.py` (code.bin por VA),
  `frontier/maison_map.py` (reproduce §2–§5 y comprueba hashes y palabras).
Evidencia: `python frontier/maison_map.py` → 50 nativas de la Mansión con su
función, 8/8 palabras de `code.bin` «ok», relleno 2556 bytes con 0 no nulos.
Desensamblados de `0x1e30b8`, `0x1e3d2c`, `0x1e3480`, `0x1e3aac`, `0x1e54a0`,
`0x1ef904` con `frontier/disasm_code.py`. Nada probado en ejecución.
Commits: ver `git log` («Battle Frontier F1: static map of the Battle Maison natives»).
Decisiones:
- Opción A (sustituir el equipo del combate) se mantiene como preferida: el
  análisis estático la respalda; falta confirmarla con gdb.
- El hook irá en el bucle de `0x1e3d2c` (fuente de los Pokémon), con código en el
  relleno de `.text` si se confirma que es ejecutable.
Siguiente paso:
1. Partida de laboratorio: copia en `work/frontier/` con 3+ Pokémon
   (`scripts/save_fixture.py`, clones) y warp de desarrollo a la zona 517
   (`faraway/dev_overlay.sh 517 <warp>`); medir si el script exige flags del Resort.
2. En Azahar con gdb: punto de ruptura en `0x1e3d2c` y `0x1e30b8`, leer
   `work+0x2C..0x4C`, comprobar que el equipo guardado no cambia tras el combate.
3. Comprobar que la VA `0x579604` es ejecutable (escribir un `bx lr` y llamarlo, o
   leer los permisos de la página desde gdb).

## 2026-11-01 — Claude Code (Opus 5.5) — F1: comprobación en Azahar; F1 cerrada
Estado: hecho
Hecho:
- Combate real de la Mansión (Individual, Normal) en Azahar con gdb; detalle en
  `reports/frontier.md` §6.
- Confirmado en ejecución: `BattleInstWorkCreate` → `0x1e5cd4` (trabajo en
  `0x08822544`), selección en `work+0x2C/+0x30/+0x48` (`[0,2,4]`, 3),
  `StartBattle(0,1)` → `0x1e30b8`, y `0x1e3d2c` llena un `PokeParty` nuevo con
  copias de los huecos elegidos.
- El equipo de la partida en memoria no cambia: volcados antes del combate, tras
  el resultado y de vuelta en el mostrador, los tres con el mismo SHA-256.
- El relleno de `.text` (`0x579604`–`0x57A000`) está mapeado y a cero.
- La Mansión funciona sin el Resort desbloqueado (warp de desarrollo); exige
  guardar antes del primer combate.
- PLAN: F1 marcada como hecha y riesgo de espacio actualizado (§7).
Evidencia: `work/frontier/lab/gdb-f1.log` (6 puntos de ruptura alcanzados),
`work/frontier/lab/party_{before,after,end}.bin` (SHA-256 `f7436e68…` los tres),
`work/frontier/lab/battleparty.bin`. Partida usada: `work/frontier/lab/main`
(SHA-256 `a74ddefd…`, copia de `work/partida-convertida/main`). Procedimiento:
`faraway/dev_overlay.sh 517 0`, `faraway/lab.sh work/frontier/lab/main
work/faraway/dev/overlay` con `use_gdbstub=true` (devuelto a `false` al acabar),
`faraway/gdbctl.sh start` cuando el puerto 24689 escucha, `faraway/walk.sh`.
Commits: ver `git log` («Battle Frontier F1: Battle Maison battle traced in Azahar»).
Decisiones:
- **Opción A elegida**: los alquileres se inyectan en `0x1e3d2c`, que construye el
  equipo del combate. La opción B (copia del equipo en la partida) queda descartada.
- Para crear los alquileres se reutilizará `0x1ef904` (conjunto de 16 bytes →
  `PokemonParam`), la misma función que usa la Mansión para el compañero de Multi.
Siguiente paso: F2 (datos de alquiler) y preparación de F3.
1. Contrastar con pret/pokeemerald `src/battle_factory.c` los niveles de alquiler
   por ronda y las reglas (3 de 6, cambio tras victoria) y anotarlos en PLAN §1.
2. `frontier/data.py`: leer `a/1/8/2`–`a/1/8/5` con comprobación de hash, agrupar
   los conjuntos por nivel de alquiler y generar las tablas; tests en `tests/`.
3. Para F3, desensamblar los argumentos de pila de `0x1ef904` (`[sp]`, `[sp+4]`)
   y cómo libera la Mansión el `PokemonParam` temporal (`0x1e35c4`, vtable +8).

## 2026-11-01 — Claude Code (Opus 5.5) — F2: datos de alquiler
Estado: hecho
Hecho:
- Reglas de la Fábrica contrastadas con pret/pokeemerald `731ad5bf`
  (`battle_factory.c`, `battle_factory_screen.c`, `frontier_util.c` y scripts de las
  salas) y anotadas en PLAN §1: 7 combates por ronda, 3 de 6 sin especie ni objeto
  repetidos, cambio tras cada victoria salvo la 7.ª, IV fijos por ronda, PB por ronda,
  jefe en 21/42 y rangos de alquiler por ronda.
- Medida la estructura de `maisonpkN`/`maisonpkS`: Normal = dos copias de 66 débiles
  y dos de 38 medios; Súper = cuatro niveles de las mismas 196 especies
  (`52k..52k+20` + `208+175k..382+175k`), más 4×20 legendarios en 908–987. Los
  entrenadores de cada tramo de racha de `0x1e3aac` eligen solo conjuntos de su nivel.
- `frontier/data.py`: lee los cuatro archivos con SHA-256, comprueba la reconstrucción
  idéntica y la estructura (`check_tiers`), define `RENTAL_LEVELS` y las constantes de
  Esmeralda, y escribe `rental_levels.bin` (formato en `reports/frontier.md` §7).
- `tests/test_frontier_data.py` (8 tests); `reports/frontier.md` §7; PLAN F2 hecha.
Evidencia: `python frontier/data.py --out work/frontier/data` → 4 archivos «sha256 ok,
unchanged rebuild identical», «tier structure ok», 8 niveles (66, 38, 38, 196×4, 784
conjuntos); `work/frontier/data/rental_levels.bin` (148 bytes) y `rentals.txt`.
`python -m pytest -q` → 45 passed (sin skips en los nuevos). Nada ejecutado en Azahar.
Commits: ver `git log` («Battle Frontier F2: rental levels from the Battle Maison sets»).
Decisiones:
- Nivel 50: ronda 1 = N 66–131 (la segunda copia del rango débil, la que usa la Mansión
  en rachas más altas), rondas 2–3 = las dos copias medias de Normal, rondas 4–7 = los
  cuatro niveles Súper, ronda 8+ = los cuatro juntos. Es ajustable en `RENTAL_LEVELS`.
- Los legendarios (S 908–987) quedan fuera de Nivel 50; se decidirá en F5 si entran en
  Nivel Libre (Esmeralda añade su «high tier» solo allí).
- IV de la ronda 9+: 31 (comportamiento `BUGFIX`), no los IV aleatorios del fallo retail.
Siguiente paso: F3 (prototipo de un combate con alquileres fijos).
1. Desensamblar `0x1ef904` (argumentos de pila `[sp]`, `[sp+4]`) y `0x1efc18` (carga
   de un conjunto: ¿acepta el archivo `0xb6`/`0xb8` como parámetro?) y cómo libera la
   Mansión el `PokemonParam` temporal (`0x1e35c4`, vtable +8).
2. Diseñar el hook en `0x1e3d2c`: en vez de `GetMemberPointer`+`AddMember` del equipo
   del jugador, construir 3 `PokemonParam` con `0x1ef904` desde conjuntos fijos y
   añadirlos con `AddMember` (`0x3b645c`); código en el relleno `0x579604`.
3. Generador del parche con comprobación de hash y bytes, y prueba en Azahar con gdb.

## 2026-11-01 — Claude Code (Opus 5.5) — F3: combate de la Mansión con 3 alquileres
Estado: hecho
Hecho:
- Desensamblados `0x1ef904` (conjunto → `PokemonParam`: argumentos de pila =
  habilidad, −1 al azar, y u16 en spec+0x1e, 0xFF), `0x1efc18` (carga de conjunto:
  heap, archivo, índice, salida) y el constructor del rival `0x1e4a94`, que usa los
  dos con `(set, 50, IV, heap, −1, 0xFF)`. Detalle en `reports/frontier.md` §8.
- `frontier/asm/rental_f3.s` + `frontier/f3_patch.py`: hook de 168 bytes en el relleno
  `0x579604` y desvío de la rama «equipo de la partida» de `0x1e3d2c` en `0x1e3d8c`.
  Crea `work+0x48` Pokémon de `maisonpkS` 208… (Venusaur, Charizard, Blastoise…),
  nivel 50, IV 31, los añade con `AddMember` y libera el temporal. Comprueba hashes,
  palabras del sitio y prólogos; `code.ips` = diferencia con el `code.bin` limpio
  (incluye Repolished).
- `tests/test_frontier_f3.py`: el sitio y el hook en Unicorn (5 tests).
- `faraway/lab.sh`: variable `CODE_IPS` para instalar otro `code.ips` en el laboratorio.
- PLAN: F3 hecha; riesgos de espacio, distribución del `code.ips` y formato actualizados.
Evidencia: `python frontier/f3_patch.py --out work/frontier/f3` → hook
`0x579604`–`0x5796ac`, `code.ips` 574 bytes (SHA-256 `f1bff00a…`). `python -m pytest -q`
→ 50 passed. Azahar con gdb (`work/frontier/lab/gdb-f3.log`): partida
`work/frontier/lab/main-maison` (`4f5a79c7…`); punto de ruptura en `0x579604` con
`work+0x30 = [0,2,4]`, `work+0x48 = 3`; en `0x1e3ddc` `r0 = 3` y el equipo del combate
con 3 miembros; en combate Venusaur/Charizard/Blastoise Nv. 50 con objeto
(`f3_battle_party.png`, `f3_battle_venusaur.png`); retirada y vuelta al mostrador.
Equipo de la partida en memoria idéntico (`f3_party_before.bin` = `f3_party_end.bin`,
`f7436e68…`) y bloque de equipo de la partida guardada tras la derrota
(`f3_after.sav`) idéntico al de `main-maison` (`d8e76518…`). `use_gdbstub` devuelto a
`false` (también hay que poner `use_gdbstub\default=false` para activarlo).
Commits: ver `git log` («Battle Frontier F3: Battle Maison battle with three rental Pokémon»).
Decisiones:
- El parche de `code.bin` se distribuirá como un `code.ips` completo (limpio → nuestro),
  porque Luma carga uno solo y Repolished ya ocupa ese archivo.
- Se mantiene la creación con `0x1ef904` (la del rival): da Pokémon válidos sin escribir
  PK6 a mano.
Sin probar: victoria con alquileres, apagar a mitad, otras modalidades, la Caja de
Combate con el parche y la consola.
Siguiente paso: F4 (Fábrica Nivel 50 Individual jugable). Empezar por:
1. Activación: el hook solo debe actuar en la Fábrica. Buscar cómo lee el código nativo
   un work/flag de script (`EventWork`; p. ej. desde una nativa conocida como
   `GetMyWinCount` o `_GetWork`) y medir works/flags libres con el método del evento
   de Mew (`reports/faraway.md` §Identificadores). El script dejará en works los 3
   índices de conjunto alquilados y el hook los leerá de ahí.
2. Ganar un combate con alquileres en Azahar y comprobar qué hace la Mansión después
   (racha, PB, guardado) con el equipo de la partida.
3. Flujo del NPC de la Fábrica sobre el script 517 (`faraway/event.py` como patrón):
   sorteo de 6 de `RENTAL_LEVELS` (en el script o en código nativo), elección de 3 con
   `ListMenu` y cambio tras la victoria.

## 2026-11-01 — Claude Code (Opus 5.5) — F4: activación de los alquileres por works guardados
Estado: en curso (F4: hecha la activación; falta el flujo de la Fábrica)
Hecho:
- `frontier/ids.py`: busca works guardados libres (scripts retail, datos de entidades,
  literales en `code.bin`/`static.crs`/CRO) y comprueba su valor en las partidas. 121
  libres; elegidos 16410 (estado = IV, 0 inactiva) y 16411–16413 (alquileres: bit 15
  Súper, bits 0–9 conjunto).
- Medido cómo lee el código un work guardado (`WorkGet` → `0x3fe118` → `0x11fa90`):
  `[[[work+0xB78]+0x1C]] + 0x13144 + 2·(N − 0x4000)`; confirmado en Azahar.
- Hook nuevo `frontier/asm/rental.s` (240 bytes): con 16410 = 0 hace lo del original;
  con 16410 ≠ 0 crea los alquileres de los works. `frontier/f3_patch.py` →
  `frontier/patch.py`, `rental_f3.s` → `rental.s`, `test_frontier_f3.py` →
  `test_frontier_patch.py` (7 tests: rama original, 5 recuentos, solo sitio y relleno);
  `tests/test_frontier_ids.py` (3 tests).
- `reports/frontier.md` §9 (y §8 apunta a los nombres nuevos); PLAN: F4 en curso.
Evidencia: `python frontier/ids.py`; `python frontier/patch.py --out work/frontier/patch`
(hook `0x579604`–`0x5796f4`, `code.ips` 655 bytes); `python -m pytest -q` → 55 passed.
Azahar (gdb): con `f4_active.sav` (`62e5b64c…`) salen Rattata N66, Mandibuzz S500 y
Slaking S907 Nv. 50 con los movimientos del conjunto; **victoria** (1 PB), combate 2 con
los alquileres reconstruidos, retirada; equipo de la partida en memoria `f7436e68…` y
bloque de equipo de la partida guardada `d8e76518…`, iguales que antes; works intactos.
Con `f3_after.sav` (works a 0) el hook pasa por la rama original y sale tu Torchic.
Logs `work/frontier/lab/gdb-f4-active.log` y `gdb-f4-inactive.log`; capturas `f4_*.png`.
`use_gdbstub` devuelto a `false`.
Commits: ver `git log` («Battle Frontier F4: rentals gated by saved works»).
Decisiones:
- El estado de la Fábrica vive en works guardados, no en el trabajo de la Mansión: así
  sobrevive al guardado obligatorio y a apagar la consola.
- Hallazgo: PID, sexo y habilidad de los alquileres se sortean en cada combate
  (Slaking macho en el 1, hembra en el 2). Esmeralda los guarda; habrá que fijarlos.
Siguiente paso (F4):
1. Fijar habilidad y sexo de cada alquiler: medir qué es el u16 de spec+0x1e de `0x1ef904`
   (¿sexo, 0xFF = al azar?) y si el PID depende de la semilla `IV+nivel+especie`
   (`0x10fc5c`); guardar habilidad (y sexo) en los bits 10–13 de 16411–16413.
2. Con la Fábrica activa, no usar la selección del jugador: el hook debe poner 3 fijo
   (el trabajo nace con `+0x48 = 0` si se salta `BattleHouse_CallPartySelectApp`), y la
   rama de la Caja de Combate (`+0x2C` ≠ 0) también debe ir a los alquileres.
3. Script: NPC de la Fábrica en la zona 517 sobre el script retail (patrón de
   `faraway/event.py`). Buscar en `oras_natives.tsv` una nativa de número aleatorio y
   cómo poner nombres de especie en un `ListMenu`; sortear 6 de `RENTAL_LEVELS`, elegir
   3, escribir los works y entrar al bucle de combate de la Mansión (`0x1e1c`) sin
   pasar por la selección de equipo. Racha y ronda propias en works libres (p. ej.
   16429–16430, 16433–16435), y poner 16410 = 0 al perder, retirarse o ganar la ronda.

## 2026-11-01 — Claude Code (Opus 5.5) — F4: habilidad fija y 3 alquileres siempre
Estado: en curso
Hecho:
- `0x1ef904` → `0x3b24c0` → `0x12bfe0` → `0x14ef5c` (creación del Pokémon desde la
  spec): `+0x1e` es el sexo (`0x14f7c8` lo escribe tal cual en los bits de género) y
  `+0x22` el índice de habilidad (0–2; `0x1ef904` pone uno al azar si recibe < 0).
- Hook: habilidad desde los bits 10–11 del work del alquiler (3 = al azar) y siempre 3
  alquileres con la Fábrica activa (no depende de la pantalla de selección). `ubfx` no
  existe en el ARM11 (ARMv6K): `as -mcpu=mpcore` lo rechaza, así que el generador ya
  protege de instrucciones v6T2.
- Tests del hook actualizados (habilidad 0, 1 y al azar; 3 alquileres con 0–6 elegidos).
- Natives: no hay número aleatorio en los scripts (ni en `oras_natives.tsv` ni en las
  769 nativas con nombre de `DllField.cro`; listado en `work/frontier/natives_dllfield.txt`);
  sí `_GetRealTimeToSecond`, `TimeCountStart/Get`, `GetSecond`. Para nombres de especie
  solo hay `WordSet*NickName` (equipo/caja) y `_SodateyaWordsetPokeName`.
Evidencia: `python frontier/patch.py --out work/frontier/patch` (244 bytes, `code.ips`
662 bytes); `python -m pytest -q` → 55 passed. **Sin probar en Azahar** este cambio.
Commits: ver `git log` («Battle Frontier F4: fixed rental ability, always three rentals»).
Decisiones:
- Sorteo de los 6 en el script: generador congruencial en Pawn sembrado con
  `_GetRealTimeToSecond` y un contador en un work libre.
- Nombres en el `ListMenu`: líneas generadas en el texto de la zona 517 (una por
  conjunto alquilable, «Especie (Objeto)»), solo en el paquete construido.
- Sexo al azar en cada combate: se acepta por ahora (solo afecta a Atracción/Rivalidad).
Siguiente paso (F4):
1. Leer el script 517 alrededor de `0x14f4` (recepción) y `0x1e1c` (bucle) y el patrón
   de `faraway/event.py` para ampliar un script retail; decidir dónde engancha el NPC de
   la Fábrica (NPC nuevo en la zona 517 o una opción nueva en el menú de la recepcionista).
2. Flujo: crear el trabajo (`BattleInstWorkCreate`), fijar tipo 0 y rango, sortear 6,
   elegir 3, escribir 16410–16413, guardar y entrar en el bucle `0x1e1c`; tras cada
   victoria ofrecer el cambio; poner 16410 = 0 al terminar.
3. Probar en Azahar el hook nuevo dentro de ese flujo.

## 2026-11-01 — Claude Code (Opus 5.5) — F4: la Mansión sin pantalla de selección con la Fábrica activa
Estado: en curso
Hecho:
- `frontier/build.py`: sustituye solo el script de la zona 517 (comprobando el SHA-256 del
  contenedor) e inserta al principio de `0x457c` el salto de `BattleHouse_CallPartySelectApp`
  si el work 16410 ≠ 0 (pone `0x800C = 1` y devuelve 1). Escribe `romfs/a/0/1/3` y el
  `code.ips`. `tests/test_frontier_build.py` (2 tests).
- Probado en Azahar el hook nuevo (habilidad fija, 3 alquileres) dentro del flujo real:
  sin pantalla de selección, `work+0x48 = 0` y aun así salen los 3 alquileres; Slaking con
  la habilidad 0 pedida (Ausente). Detalle en `reports/frontier.md` §10.
Evidencia: `python frontier/build.py --out work/frontier/build --zones
work/faraway/dev/overlay/romfs/a/0/1/3`; `CODE_IPS=work/frontier/build/code.ips
faraway/lab.sh work/frontier/lab/f4_active.sav work/frontier/build`; log
`work/frontier/lab/gdb-f4-noselect.log`; capturas `f4_noselect_party.png`,
`f4_slaking_ability.png`; partida tras la derrota `f4b_after.sav` (`76289ff9…`).
`python -m pytest -q` → 57 passed. `use_gdbstub` devuelto a `false`.
Commits: ver `git log` («Battle Frontier F4: skip the Maison party selection while the Factory is active»).
Decisiones:
- Se reutiliza el flujo de la Mansión desde la recepcionista; la pantalla de selección se
  salta en su propia rutina, no en el código nativo.
Problema abierto (no resuelto): tras esta prueba el equipo guardado cambió en 8 bytes de
recuerdos del PK6 (Beldum `0xA4`–`0xA8`, Shroomish `0xCC`); lo demás, igual. No está
aislado si es la mecánica de recuerdos del juego o el flujo sin pantalla.
Siguiente paso:
1. Aislar el cambio de recuerdos: repetir el recorrido (recepcionista → Individual →
   guardar → combate → retirada) con la `code.ips` de Repolished sin la Fábrica y con
   `f3_after.sav`/`main-maison`, y comparar el bloque de equipo. Si también cambia, es del
   juego (los recuerdos se actualizan solos) y se documenta; si no, buscar qué hace
   `BattleHouse_CallPartySelectApp` que el salto omite.
2. Seguir con el flujo de la Fábrica (opción en el menú de la recepcionista, sorteo
   congruencial, elección de 3, cambio tras la victoria, 16410 = 0 al terminar).

## 2026-11-01 — Claude Code (Opus 5.5) — Corrección: tests de la entrada anterior
Estado: en curso
Hecho: la entrada «F4: la Mansión sin pantalla de selección…» dice «57 passed», pero la
suite completa daba **55 passed, 2 errors**: `frontier/build.py` chocaba con
`faraway/build.py` (los dos se importan como `build`; `frontier/ids.py` carga el de
`faraway`). Renombrado a `frontier/overlay.py` y su test a
`tests/test_frontier_overlay.py`; `reports/frontier.md` §10 actualizado.
Evidencia: `python -m pytest -q` → 57 passed; `python frontier/overlay.py --out
work/frontier/build --zones work/faraway/dev/overlay/romfs/a/0/1/3` da el mismo script
(14456 bytes) y hook (244 bytes).
Commits: ver `git log` («Battle Frontier F4: rename the overlay builder (module clash)»).
Decisiones: ninguna nueva.
Siguiente paso: el de la entrada anterior (aislar el cambio de recuerdos y seguir con el
flujo de la Fábrica). Comando nuevo: `python frontier/overlay.py` en vez de `frontier/build.py`.

## 2026-11-01 — Claude Code (Opus 5.5) — F4: el cambio de recuerdos es del juego
Estado: en curso
Hecho: control sin parche (Repolished `code.ips`, script retail, overlay de desarrollo),
partida `f4_active.sav`, mismo recorrido con la pantalla de selección y combate perdido.
La partida guardada tras la derrota cambia `0xCC` (1→2) de Poochyena (hueco 2), un campo de
recuerdos del PK6, igual que en la prueba con la Fábrica (Beldum y Shroomish). Conclusión
en `reports/frontier.md` §10: es la mecánica de recuerdos del juego, no la Fábrica.
Evidencia: `work/frontier/lab/control_after.sav` (`bf647740…`), comparada con
`f4_active.sav` decodificando los 6 PK6 (`scripts/save_fixture.py`): solo el hueco 2
cambia, en `0xCC` y el checksum.
Commits: ver `git log` («Battle Frontier F4: memory-field change isolated to the retail game»).
Decisiones: el criterio «equipo de la partida idéntico» se entiende como especie, nivel,
experiencia, PS, movimientos, objetos, EV e IV; los campos de recuerdos los cambia el juego
retail y se aceptan. Si se quiere que la Fábrica no deje recuerdos en Pokémon que no
combatieron, es una mejora posterior (decisión del usuario).
Siguiente paso: flujo de la Fábrica (F4):
1. Opción «Fábrica Batalla» en el `ListMenu` de la recepcionista (`0x15a4`–`0x15f8`, línea
   de texto nueva en el texto 619 de la zona 517) que lleve a una rutina nueva.
2. Rutina: sorteo de 6 conjuntos de `RENTAL_LEVELS[ronda]` con un congruencial en Pawn
   (semilla `_GetRealTimeToSecond` + contador en un work libre; especies y objetos sin
   repetir), menú de 6 con líneas «Especie (Objeto)» generadas por conjunto, elegir 3,
   escribir 16410 (IV de la ronda) y 16411–16413 (con habilidad 0/1 al azar), y saltar a
   la rama de desafío Individual (`0x1768`/`0x18f8` con tipo 0).
3. Tras cada victoria, cambio de un alquiler por uno del rival (hay que saber qué conjuntos
   usó el rival: `work+0x0C` ficha del entrenador y lo que elige `0x1e4a94`).
4. Poner 16410 = 0 al perder, retirarse o terminar la ronda, y en la recepción normal.

## 2026-11-02 02:55 — Claude Code (Opus 5.5) — F4: inscripción en la Fábrica (elegir 3 de 6)
Estado: en curso
Hecho:
- `frontier/factory.py` (nuevo). La recepcionista de la zona 517 tiene la opción
  «Fábrica Batalla» (texto 619, línea 188). La opción llama a `GlobalCall(9771)`.
- El caso 9771 es nuevo en el script compartido 5 (`a/0/2/9`), un esqueleto retail.
  Hace el sorteo de 6 conjuntos del nivel de la ronda con un congruencial en Pawn,
  sembrado con `_GetRealTimeToSecond` y el work 16414, con especies y objetos distintos.
  Luego muestra tres menús «Especie (Objeto)» y escribe los works 16410–16413.
- Después, la zona hace `SetRank(0)` y llama al desafío `0x18f8` en Individual, sin la
  pantalla de modalidad.
- La opción «Combatir» y el caso 1 (`0x1458`) ponen 16410 = 0.
- `frontier/patch.py`: la fila de `GlobalCall` 9770–9779 (`0x587AA8`) apunta su texto a
  la entrada nueva 637. Ahí van los 3 avisos y una línea por conjunto (926) en cada
  idioma, generadas del volcado.
- `frontier/overlay.py` escribe `a/0/1/3`, `a/0/2/9` y los 8 textos de historia; `--zones`
  pasa a ser `--romfs`, que si falta un archivo usa la base.
- `scripts/pawn_vm.py` (nuevo) es un intérprete Pawn mínimo para los tests.
- `frontier/lab_factory.py` (nuevo) espera al menú de la recepcionista y elige la Fábrica.
- `reports/frontier.md` §11 y PLAN (F4, y riesgo de tamaño del script de zona) actualizados.
Evidencia:
- `reports/frontier.md` §11. Capturas: `work/frontier/lab/f4c_menu.png`,
  `f4c_draft1.png`, `f4c_draft1_bottom.png`, `f4c_draft2.png`, `f4c_draft3.png`,
  `f4c_battle_party.png`, `f4c_cancel_menu.png` y `f4c_cancel_back.png`.
- Partida tras inscribirse: `work/frontier/lab/f4c_saved.sav` (`d534beaa…`), con
  16410 = 3 y 16411–16413 = N128 Boldore, N122 Drowzee y N96 Spinarak. En combate salen
  esos tres, Nv. 50.
- `python -m pytest -q` → 83 passed. `use_gdbstub` devuelto a `false`.
Commits: ver `git log` («Battle Frontier F4: Factory sign-up with a draft of 6 rentals»).
Decisiones:
- El script de la zona 517 no puede crecer mucho. Con un ZO de 21.428 bytes la zona se
  cuelga al cargar; con 17.248 carga. Por eso el sorteo y sus textos van a un script
  compartido con texto propio, sin tocar el texto de la zona salvo una línea.
- Desde el script hijo no se llaman nativas de la Mansión (`GetMyWinCount` colgó el
  juego): la zona pasa la racha en el work 16429.
- El nivel de alquiler sale de la racha de la Mansión (Individual Normal, compartida;
  desviación conocida) dividida entre 7.
- Sin aplicar todavía `PAST_RENTALS_RANK`, que hace que algunos alquileres salgan del
  nivel siguiente.
- Habilidad 0/1 al azar por alquiler.
Sin probar: que una derrota sola deje 16410 = 0 en Azahar (tras perder entré por
«Combatir», que también lo limpia; la lógica está en los tests), la pausa y la
reanudación, otros idiomas y consola.
Siguiente paso:
1. Tras cada victoria, ofrecer cambiar un alquiler por uno del último rival. Hace falta
   saber qué conjuntos usó el rival (`work+0x0C`, `0x1e4a94`) y pasarlos al hijo en
   works (p. ej. 16433–16435), sin llamar nativas de la Mansión desde él.
2. Cada 7 victorias, sorteo nuevo de 6 del nivel siguiente (en el bucle `0x1e1c`, tras
   `AddWinCount`).
3. Comprobar en Azahar la derrota sola, la pausa y la reanudación.

## 2026-11-02 13:10 — Claude Code (Opus 5.5) — Visión final: expansión con isla del Frente
Estado: en curso
Hecho:
- El usuario fija el destino del proyecto: una expansión tipo evento o DLC. Un objeto
  (u otra condición) desbloquea una zona nueva que es un clon del Frente Batalla de
  Esmeralda.
- PLAN §1 (visión), §5.6 (propuesta de ubicación: objeto clave, entrega, barco, isla
  clonada, interiores), F6 (isla, objeto y viaje) y «Después» (las 6 instalaciones
  restantes con dificultad estimada) actualizados.
Evidencia: mensaje del usuario en la sesión; sin mediciones nuevas.
Commits: ver `git log` («Battle Frontier: record the expansion-island goal in the plan»).
Decisiones:
- La Fábrica sigue desarrollándose dentro de la Mansión (F4–F5) como banco de pruebas, y
  se traslada a la isla en F6.
- Pendiente del usuario: nombre del objeto, quién lo entrega y cuándo, desde qué puerto
  se viaja y qué mapa sirve de base para la isla (§5.6).
Siguiente paso: el de la entrada anterior (cambio tras la victoria, sorteo cada 7
victorias, derrota, pausa y reanudación en Azahar).

## 2026-11-02 13:21 — Claude Code (Opus 5.5) — Decisiones del usuario sobre la isla del Frente
Estado: en curso
Hecho: PLAN §5.6 recoge lo que decidió el usuario.
- Objeto clave «Pase del Frente», tras ganar la Liga.
- Viaje en el **ferry** de Calagua (destino nuevo «Isla del Frente»), no en la barca.
- Activación: el mod hace de DLC. ORAS no tiene soporte de contenido descargable, así
  que la zona va siempre en el paquete y el pase la abre.
- Queda como propuesta quién entrega el pase (por defecto, un marinero del puerto de
  Calagua).
Evidencia: mensajes del usuario en la sesión; sin mediciones nuevas.
Commits: ver `git log` («Battle Frontier: user decisions for the Frontier island»).
Decisiones: las de arriba. El mapa base de la isla sigue abierto (candidato: exterior del
Resort Batalla).
Siguiente paso: el de la entrada «F4: inscripción en la Fábrica» (cambio tras la victoria,
sorteo cada 7 victorias, derrota, pausa y reanudación). Para F6 habrá que medir el flag de
campeón y el menú de destinos del ferry (script compartido 79).

## 2026-11-02 13:35 — Claude Code (Opus 5.5) — Propuestas de la isla aceptadas
Estado: en curso
Hecho: el usuario acepta las propuestas («propón algo y tira, lo mejoraremos»): entrega el
pase un marinero del puerto de Calagua con la Liga ganada; la isla es una zona nueva con la
geometría clonada del exterior del Resort Batalla. PLAN §5.6 actualizado.
Evidencia: mensaje del usuario en la sesión.
Commits: ver `git log` («Battle Frontier: island proposals accepted»).
Decisiones: zona nueva sí (como Isla Suprema); mapa 3D hecho a mano no (habría que modelar
terreno, texturas y colisiones y convertirlos al formato del juego; fuera de alcance por
ahora).
Siguiente paso: el de la entrada «F4: inscripción en la Fábrica».

## 2026-11-02 13:40 — Claude Code (Opus 5.5) — Distribución de la isla como en Esmeralda
Estado: en curso
Hecho: el usuario pide que, aunque los edificios y el aspecto sean de ORAS, la isla siga la
distribución del Frente de Esmeralda. PLAN §5.6 lo recoge, con la vía prevista: el catálogo
de edificios del fork de CTRMap-F5 (`oras_buildings*.tsv`, `MapPainter`, que recorta un
edificio retail y lo estampa en otro mapa).
Evidencia: lectura del catálogo, 58 entradas curadas y unas 3500 automáticas; sin
pruebas nuevas. No usado aún en el proyecto ni en consola.
Commits: ver `git log` («Battle Frontier: Emerald layout for the island»).
Decisiones: distribución original de Esmeralda con piezas de ORAS; interiores clonados por
ahora.
Siguiente paso: el de la entrada «F4: inscripción en la Fábrica». En F6, primero una prueba
pequeña: estampar un edificio con puerta en una zona clonada y entrar en él, en Azahar y
en consola.

## 2026-11-02 14:15 — Claude Code (Opus 5.5) — F4: intercambio tras la victoria y sorteo por ronda
Estado: en curso
Hecho:
- `frontier/asm/rental.s` `rival_hook` en `0x1e4b34` (constructor del rival): con la
  Fábrica activa copia los índices de conjunto del rival a los works 16433–16435.
- `frontier/factory.py`: tras cada victoria (`0x2264`), `factory_after_win`. Cada 7
  victorias hay sorteo nuevo (`GlobalCall 9771`, hasta elegir); si no, intercambio
  (`GlobalCall 9772`, `factory_swap`, dos menús).
- La derrota (`0x2210`) limpia 16410 antes del guardado de la Mansión.
- Texto 637 reorganizado: `maisonpkN` 0–207 completos para los rivales, más los Súper.
- `scripts/pawn_vm.py` admite `SUB_ALT`.
- `reports/frontier.md` §12 y PLAN F4 actualizados.
Evidencia:
- `reports/frontier.md` §12. Capturas `work/frontier/lab/f4d_*.png`.
- Partidas: `f4d_after_loss.sav` (`afa9cb02…`), `f4e_before_loss.sav` (`324e8690…`) y
  `f4e_after_loss.sav` (`d20c94ed…`, 16410 = 0).
- `python -m pytest -q` → 108 passed. `use_gdbstub` en `false`.
Commits: ver `git log` («Battle Frontier F4: swap after a win, new draft every round»).
Decisiones:
- El rival se sigue generando con la Mansión en rango Normal (trainers por racha), así
  que se puede tomar cualquier conjunto `maisonpkN` 0–207.
- Sin restricción de especie u objeto repetidos al tomar del rival (Esmeralda tampoco la
  aplica en el cambio, sin comprobar).
Sin probar en Azahar: el sorteo tras la 7.ª victoria, rechazar el intercambio, la pausa y la
reanudación, y nada en consola.
Siguiente paso:
1. Ronda completa en Azahar (7 victorias) para ver el sorteo nuevo. Para acelerar,
   partida con la racha de Individual Normal en 6, o probar en una partida editada.
2. Pausa y reanudación (caso 3 del despachador, `0x5b58`), con la Fábrica activa.
3. Racha propia de la Fábrica y PB por ronda de Esmeralda (ahora son los de la Mansión).
4. Después, F6: isla del Frente (objeto, ferry de Calagua, zona nueva).

## 2026-11-02 14:54 — Claude Code (Opus 5.5) — F4: ronda completa, pausa y reanudación
Estado: en curso
Hecho:
- Racha de Individual Normal localizada en la partida: `0x1BBC0` (actual) y `0x1BBC4`
  (récord), bloque 37.
- `factory_reception`: con la Fábrica activa (desafío pausado) no sortea y reanuda con
  los alquileres guardados.
- Probado en Azahar:
  - intercambio rechazado;
  - pausa (guarda la Fábrica y la racha);
  - reanudación con racha 6;
  - derrota en el combate 7 (Fábrica limpia);
  - victoria en el 7 → sorteo nuevo del nivel 2 con IV 6 → «combate número 8».
- `reports/frontier.md` §13; PLAN F4 actualizado.
Evidencia: `reports/frontier.md` §13. Partidas `work/frontier/lab/f4f_paused.sav`
(`02c6d7f3…`), `f4f_paused_streak6.sav` (`aa5b24b3…`), `f4g_after_loss.sav`
(`e0245289…`), `f4h_paused_streak6_legend.sav` (`2703fb2a…`) y
`f4h_paused_round2.sav` (`0c15ca2d…`). `python -m pytest -q` → 109 passed.
`use_gdbstub` en `false`.
Commits: ver `git log` («Battle Frontier F4: resume a paused Factory, full round tested»).
Decisiones:
- Las partidas de laboratorio se editan con la racha en `0x1BBC0` y con alquileres
  fuertes para llegar rápido a los casos.
- Desviación aceptada por ahora: el rival puede llevar especies que tiene el jugador.
Siguiente paso:
1. Racha propia de la Fábrica: ahora se comparte con Individual Normal de la Mansión, y
   «Combatir» la continúa con el equipo del jugador. Opción: guardar la racha de la
   Mansión al entrar en la Fábrica y restaurarla al salir, o usar works propios
   (16430…) y restaurar `0x1BBC0`.
2. PB por ronda de Esmeralda (3, 3, 4, … al ganar el 7.º) en lugar de los de la
   Mansión por combate.
3. Después, F6: isla del Frente.

## 2026-11-02 15:10 — Claude Code (Opus 5.5) — F4: PB por ronda
Estado: en curso
Hecho:
- `factory.battle_points` inserta en la rutina de PB de la Mansión (`0x3de4`) la regla
  de Esmeralda: con la Fábrica activa, PB solo en la 7.ª victoria de cada ronda
  (`data.BATTLE_POINTS`).
- Tests en el intérprete: 121 en total.
- En Azahar, la ronda 1 da 3 PB: los PB de la partida (`0x4230`) pasan de 1 a 4. El
  build anterior daba 1.
- `reports/frontier.md` §14 y PLAN F4.
Evidencia: `reports/frontier.md` §14; `work/frontier/lab/f4i_after_loss.sav`
(`d080c541…`). `python -m pytest -q` → 121 passed. `use_gdbstub` en `false`.
Commits: ver `git log` («Battle Frontier F4: Battle Points per round, as Emerald»).
Decisiones: los PB se dan con el mensaje retail de la Mansión.
Siguiente paso:
1. Racha propia de la Fábrica (sigue compartida con Individual Normal de la Mansión; ver
   la entrada anterior).
2. Luego, F6: isla del Frente. El Pase del Frente lo da un marinero del puerto de
   Calagua tras la Liga; destino en el ferry; zona nueva con la geometría del Resort.

## 2026-11-02 15:28 — Claude Code (Opus 5.5) — F4: racha propia de la Fábrica
Estado: en curso
Hecho:
- `code.bin`: los 4 accesores de la racha de Individual de la Mansión (`0x45cdc4`,
  `0x45cf14`, `0x45cfb8`, `0x45d03c`) se desvían a los works 16437 (racha) y 16439
  (récord) mientras el work 16438 = 1 y el rango es Normal (`rental.s`
  `FACTORY_SLOT`).
- Script: la Fábrica activa el desvío durante el desafío, empieza en racha 0 y lo limpia
  al volver y en cada recepción.
- `reports/frontier.md` §15 y PLAN F4.
Evidencia: `reports/frontier.md` §15. Partidas `work/frontier/lab/f4j_saved.sav`
(`becfbd96…`), `f4j_paused.sav` (`7195a65c…`) y `f4j_after_loss.sav` (`355e5928…`),
con la Mansión en 20/20 en las tres. `python -m pytest -q` → 128 passed.
`use_gdbstub` en `false`.
Commits: ver `git log` («Battle Frontier F4: the Factory keeps its own streak»).
Decisiones:
- Desvío en `code.bin` en lugar de copiar y restaurar la racha desde el script, porque
  cubre también los guardados que la Mansión hace dentro de su bucle.
- Límite aceptado: una partida guardada durante el desafío deja 16438 = 1 hasta la
  siguiente recepción.
Siguiente paso: F4 está completa para Nivel 50 Individual, salvo detalles:
- sexo del alquiler al azar en cada combate;
- el rival no excluye las especies del jugador;
- el rival sale de los tramos de entrenador de la Mansión, no del nivel de la ronda.
Propongo cerrar F4 y empezar F6 (isla del Frente), dejando esos detalles para F5. Primer
paso de F6:
1. medir el flag de campeón de la Liga;
2. medir el menú de destinos del ferry de Calagua (script compartido 79);
3. medir un hueco de objeto clave libre para el Pase del Frente (como el Mapa Viejo).

## 2026-11-02 15:50 — Codex — Revisión de EXP del portador participante
Estado: hecho
Hecho: a petición del usuario, revisado si el portador de Repartir Exp. recibe la
mitad cuando participa y gana. Conserva la experiencia normal; la mitad se aplica
al portador que no participa. Sin cambios en el parche.
Evidencia: ejecución con `source scripts/env.sh` y Python de
`scripts/validate_arm.py:execute(True, ...)`: portador participante → [100, 0, 0],
participante sin objeto → [100, 0, 0], portador en reserva → [100, 50, 0]; asserts
correctos. Relectura con `scripts/save_fixture.py:inspect` de las partidas
`participant` y `none` referenciadas en `reports/gameplay-validation.json`:
ambas dan [16, 0, 0], con objetos [216, 0, 0] y [0, 0, 0], respectivamente;
hashes antes/después coinciden con el informe. La rama participante evita la
comprobación del objeto (`reports/ingenieria.md`, salto a CRO +0x3265C).
No se ha jugado un combate nuevo ni probado la instalación del usuario en consola.
Commits: sin commit.
Decisiones: revisión puntual del mod entregado, sin cambiar las reglas de EXP.
Siguiente paso: retomar F6 según la entrada anterior: flag de campeón, menú del
ferry de Calagua y hueco de objeto para el Pase del Frente.

## 2026-11-02 19:47 — Codex — Encuentros de Senda Ígnea
Estado: hecho
Hecho: revisión puntual solicitada por el usuario. Añadido lector sin escritura
`scripts/inspect_encounters.py` y resultados en `reports/senda-ignea.md`.
Zona 85, lugar 288; encuentros en `a/0/1/3`, entrada 537 (EN), offset 0x4864.
En Repolished, normales: Numel 40 %, Grimer 30 %, Slugma 10 %, Torkoal 10 %,
Machop 5 %, Koffing 5 %. Hordas: Numel/Grimer/Slugma 60/35/5 %.
Evidencia: `source scripts/env.sh`;
`python scripts/inspect_encounters.py 'Senda Ígnea' > work/senda-ignea-encounters.json`.
Hashes validados contra manifiesto; comparación byte a byte del archivo de
baseline con inputs/repolished correcta; suma de pesos normales 100 % para ambas
versiones. Formato y pesos contrastados con CTRMap-F5 y pk3DS (rutas en el informe).
Sin prueba nueva en emulador/consola; desbloqueo y probabilidades DexNav no medidos.
Commits: sin commit.
Decisiones: analizar el paquete local 1.7.6 y comparar con el volcado limpio;
no cambiar encuentros. Repolished intercambia Grimer y Koffing respecto al original.
Siguiente paso: retomar F6: flag de campeón, menú del ferry de Calagua y hueco
de objeto para el Pase del Frente.

## 2026-11-02 20:31 — Codex — Cambios evolutivos de Repolished
Estado: hecho
Hecho: revisión solicitada por el usuario; lector `scripts/inspect_evolutions.py`
e informe completo `reports/evoluciones-repolished.md`. Comparadas 826 entradas:
38 distintas, correspondientes a 35 especies. Mega-evoluciones sin cambios de tabla.
Detectado Mienfoo con método 4 y argumento 65535, frente a nivel 50 original;
Pumpkaboo normal usa Piedra Noche o intercambio, otras formas nivel 30.
Evidencia: `source scripts/env.sh`;
`python scripts/inspect_evolutions.py > work/evolution-changes.json` ejecutado
correctamente. Hashes contra manifiesto y coincidencia con el paquete original
comprobados. Métodos y formas según pk3DS, fuentes y bytes en el informe.
No se ha probado ninguna evolución nueva en emulador/consola ni el comportamiento
del motor con el argumento anómalo de Mienfoo.
Commits: sin commit.
Decisiones: documentar los métodos exactos, incluidas las vías originales que
se conservan y las que se sustituyen; no modificar el juego en esta revisión.
Siguiente paso: si se solicita, investigar/corregir la evolución de Mienfoo sobre
una copia. Frente pendiente: F6 (flag de campeón, ferry y hueco del Pase del Frente).

## 2026-11-02 23:49 — Codex — Encuentros de Ruta 114
Estado: hecho
Hecho: consulta del usuario sobre Ruta 114 en Repolished 1.7.6. Zona 41,
lugar 230, paquete EN offset 0x20c8; las zonas 387–389 no tienen encuentros.
Hierba: Swablu 16–18 (35 %), Lombre 16–19 (20 %), Nuzleaf 16–19 (20 %),
Zangoose 17–19 (10 %), Seviper 17 (10 %), Surskit 19 (5 %).
Hordas: cinco Swablu 9 (95 %) o cinco Surskit 9 (5 %).
Surf: Marill 15 (50 %), Azumarill 20 (30 %) o 25 (1 %), Surskit 20 (15 %),
Masquerain 25 (4 %). Golpe Roca: Geodude, niveles 5/10/15/20.
Caña Vieja: Magikarp 10 (60 %) o 15 (5 %), Goldeen 5 (35 %).
Caña Buena: Magikarp/Goldeen/Barboach 25 (60/35/5 %).
Supercaña: Barboach 35/30/40 (60/35/5 %).
Especiales DexNav: Skorupi, Misdreavus y Tympole, nivel base 19; desbloqueo no medido.
Evidencia: `source scripts/env.sh`;
`python scripts/inspect_encounters.py 'Ruta 114' > work/ruta-114-encounters.json`.
Hashes comprobados por el lector. Pesos Surf/pesca contrastados con etiquetas
de `tools/pk3DS/pk3DS.WinForms/Subforms/Gen6/RSWE.Designer.cs` y su orden en RSWE.cs.
Porcentajes relativos al método. Sin prueba nueva en emulador/consola.
Commits: sin commit.
Decisiones: lectura de datos sin modificar el juego.
Siguiente paso: retomar F6 (flag de campeón, ferry y hueco del Pase del Frente).

## 2026-11-03 00:28 — Codex — Disponibilidad de otros iniciales
Estado: hecho
Hecho: revisión solicitada por el usuario. `reports/iniciales-repolished.md`
recoge la comparación: ninguna de las 54 especies de familias iniciales aparece
en los encuentros de las 536 zonas. Regalos y scripts sin cambios respecto al
original; Repolished no añade los dos iniciales de Hoenn no elegidos.
Evidencia: `inspect_encounters.inspect_location('repolished', '')` guardado en
`work/all-encounters.json`; filtro por nombres ES y rangos de Pokédex → 0 resultados.
Hashes verificados contra manifiesto. Comparación de DllField.cro, a/0/2/9 y
subarchivos de todas las zonas: solo cambian los encuentros de estas últimas.
Tabla de regalos leída según pk3DS. Condiciones originales de Abedul contrastadas
con Bulbapedia (enlace en el informe). Sin ejecución nueva de eventos.
Commits: sin commit.
Decisiones: distinguir otros iniciales de Hoenn de los regalos de otras regiones;
no considerar accesible un regalo solo porque exista un registro heredado.
Siguiente paso: retomar F6 (flag de campeón, ferry y hueco del Pase del Frente).

## 2026-11-03 01:03 — Codex — Encuentros de Cascada Meteoro
Estado: hecho
Hecho: consulta del usuario. Repolished, zonas 71–74. Normales: zona 71,
Zubat 16–19 (70 %), Lunatone/Solrock 16–18 (15 % cada uno); zonas 72–73,
Golbat 37–40 (70 %), Lunatone/Solrock 37–40 (15 % cada uno); zona 74,
Golbat 37–40 (45 %), Bagon 37–40 (35 %), Lunatone/Solrock 37–40 (10 % cada uno).
Hordas: Zubat 9 en zona 71, Zubat 20 en 72–73; en 74, Zubat 20 (95 %) o
Bagon 20 (5 %). Especiales DexNav: Deino/Druddigon/Clefairy, base 19 en 71,
40 en 72–74; condiciones de desbloqueo no medidas.
Surf: en 71 Zubat/Goldeen/Golbat (80/16/4 %); en 72–74
Golbat/Goldeen/Barboach (80/15/5 %). Pesca: Caña Vieja Magikarp/Goldeen
(65/35 %), Caña Buena Magikarp/Goldeen/Barboach (60/35/5 %); Supercaña
Barboach (100 %) en 71, Barboach/Whiscash (95/5 %) en 72–74.
Evidencia: `source scripts/env.sh`;
`python scripts/inspect_encounters.py 'Cascada Meteoro' > work/cascada-meteoro-encounters.json`.
Hashes validados por el lector; agregación por especie y assert de suma 100 %
en cada tabla normal correctos. EN offsets 0x3e3c/0x3f40/0x4044/0x4148.
Sin prueba nueva en Azahar/consola; no se han medido los requisitos de acceso a salas.
Commits: sin commit.
Decisiones: lectura sin modificar el juego; ningún inicial en estas tablas.
Siguiente paso: retomar F6 (flag de campeón, ferry y hueco del Pase del Frente).

## 2026-11-03 03:30 — Codex — Encuentros de Ruta 115
Estado: hecho
Hecho: consulta del usuario, Repolished zona 42, EN offset 0x21cc. Hierba:
Swablu 17–20 (40 %), Taillow 17–20 (40 %), Wingull 20 (10 %), Jigglypuff
18 (9 %) o 20 (1 %). Hordas: cinco Swablu al nivel 10 (100 %).
Surf: Tentacool 20/25 (65 %), Wingull 20 (30 %), Pelipper 25/30 (5 %).
Caña Vieja: Magikarp 10/15 (65 %), Tentacool 5 (35 %).
Caña Buena: Magikarp/Tentacool/Wailmer 25 (60/35/5 %).
Supercaña: Wailmer 30/35/40 (100 %). Especiales DexNav: Pidove, Misdreavus,
Clefairy, base 20; desbloqueo no medido. Sin banco de Golpe Roca.
Evidencia: `source scripts/env.sh`;
`python scripts/inspect_encounters.py 'Ruta 115' > work/ruta-115-encounters.json`.
Hashes comprobados por el lector; pesos por método según pk3DS, como en consultas
anteriores. Sin ejecución nueva en Azahar/consola.
Commits: sin commit.
Decisiones: lectura sin modificar el juego.
Siguiente paso: retomar F6 (flag de campeón, ferry y hueco del Pase del Frente).

## 2026-11-02 20:56 — Claude Code — F6: medidas del pase, el ferry y el puerto
Estado: hecho
Hecho: medidos los tres datos que pedía el paso anterior. Detalle en
`reports/frontier.md` §16.
- Flag de campeón: 2720 («Entered Hall of Fame»).
- Ferry: compartido 79, `GlobalCall(10430)`, texto 11. Son el menú por zona, los casos
  0/1/2, `0x724` = `_MapChangeCore` y 16707, que solo lee el camarote 216.
- Objeto: 701 (Pase TMV), con los mismos datos que el 442 del Mapa Viejo y sin usos en
  scripts.
- Puerto 317: el marinero es uid 2, caso 4, y el empleado uid 0, caso 5.
Evidencia: listados `work/frontier/survey/shared79.lst`, `zone317.lst` y `zone212.lst`;
búsquedas de operandos en los 1157 scripts, con control positivo (`ItemGetNum(457)`
encontrado); tabla `GlobalCall` fila 33 (`0x587888`) en `code.bin`; datos `a/1/9/7`.
Las listas de PKHeX se copian a `work/pkhex/`, sin versionar. Nada ejecutado en Azahar.
Commits: el de esta entrada. Incluye también, sin cambios, las tres entradas de Codex
anteriores (revisiones puntuales); sus archivos (`reports/senda-ignea.md`,
`reports/evoluciones-repolished.md` y `scripts/inspect_*.py`) siguen sin versionar porque
no son de esta sesión.
Decisiones:
- El pase lo da el marinero que ya existe en el puerto (uid 2), en vez de un NPC nuevo.
  Así no se tocan las entidades de la zona 317 ni el marinero del evento de Mew.
- El ferry ofrece «Isla del Frente» en Calagua y en Portual, como el S.S. Marea de
  Esmeralda, si llevas el objeto 701.
- El viaje es directo, como al Resort. Desde la isla, un empleado con uid 0 que llame a
  `GlobalCall(10430)` cae en la rama «otra zona» y ofrece Portual y Calagua sin tocar el
  ferry.
Siguiente paso: implementar el pase (texto del objeto, entrega del marinero) y el destino
nuevo del ferry; probarlo en Azahar con destino provisional, y después clonar la isla.

## 2026-11-02 21:11 — Claude Code — F6: Pase del Frente, marinero y destino nuevo del ferry
Estado: hecho (destino provisional)
Hecho:
- `frontier/island.py`:
  - el objeto 701 pasa a ser «Pase del Frente» / «Frontier Pass»;
  - el marinero de Calagua (zona 317, evento 4) lo da una vez a quien tiene el flag 2720;
  - el ferry (compartido 79) ofrece «Isla del Frente» en Calagua y Portual a quien
    lleva el pase, con un caso nuevo copiado del caso del Resort.
- Integrado en `frontier/overlay.py`: zonas 517+317, compartidos 5+79, textos 523 y 11,
  textos de juego 113–117.
- `scripts/pawn_vm.py` admite `SWITCH`.
- Tests nuevos en `tests/test_frontier_island.py`; actualizados los de
  `test_frontier_overlay.py`.
Evidencia:
- `python -m pytest -q tests` → 139 passed.
- Roturas a mano del menú, la llegada y el marinero: los tests fallan.
- Azahar, partida `f6_champion_ticket.sav` (`936975ed…`), `faraway/dev_overlay.sh 317 0` y
  `work/frontier/labroot`:
  - el marinero da el pase al Bolsillo Objetos Clave; la segunda vez dice la línea
    retail;
  - el menú del ferry muestra «Isla del Frente»; Sí lleva al muelle del Resort.
- Capturas `work/frontier/lab/f6_*.png`. Detalle en `reports/frontier.md` §17.
- No probado: guardar con el pase, Portual en el emulador, otros idiomas, consola.
Commits: el de esta entrada.
Decisiones:
- La zona 317 y el compartido 79 se modifican por contenido, no por hash, para
  convivir con el puerto del evento de Mew.
- Las líneas del marinero van al final del texto 523, con el número que toque.
- El viaje a la isla deja 16707 = 3, como el del Resort.
- La llegada es provisional, `island.ARRIVAL` = la del Resort.
- **Aviso para el laboratorio**: el warp de desarrollo apunta ahora al puerto de Calagua.
  Para volver a probar la Fábrica, `faraway/dev_overlay.sh 517 0` y regenerar la build.
Siguiente paso: la zona de la isla.
1. Elegir una zona libre con `ZoneRepurposeScanner`, como la 473/474 de Mew.
2. Clonarla del exterior del Resort (zona 212) con mapa y área propios, como hace
   `faraway/java/faraway/Build.java`. Nombre de lugar «Isla del Frente».
3. Poner un empleado de ferry con uid 0 que llame a `GlobalCall(10430)` para la vuelta.
4. Puerta de la Mansión → zona 517 (la Fábrica) de momento.
5. Cambiar `island.ARRIVAL` y probar ida y vuelta en Azahar.

## 2026-11-02 21:46 — Claude Code — F6: zona de la isla (209) y sala clonada (213)
Estado: en curso
Hecho:
- `frontier/island_build.py`: con CTRMap-F5 (`Build.java` del evento de Mew) clona 212
  → 209 «Isla del Frente» (empleado del ferry uid 0, script de 212 sin la escena de
  Blasco) y 517 → 213 (sala de la Mansión con la Fábrica, texto 619). Pone el nombre de
  lugar 279. Lo llama `overlay.py`; `--no-island` lo salta.
- El ferry llega ahora a (209, 53, 2, 34, 2).
- `Build.java`: opción `keeptext.<zona>`. `Probe.java`: modo `repurpose`.
Evidencia:
- `reports/frontier.md` §18.
- `python -m pytest -q tests` → 140 passed. El test nuevo del script de la isla falla si
  se quita el cambio `JNZ` → `JUMP`.
- Azahar: ferry → isla, con control libre y el nombre en pantalla; el muelle lleva a la
  sala 213. Capturas `work/frontier/lab/f6c_*.png`.
Commits: el de esta entrada.
Decisiones:
- Zonas 209 y 213: libres según `ZoneRepurposeScanner` y la búsqueda de literales. Las
  473/474 quedan para Mew.
- Distribución provisional: muelle → sala, sin edificio. Lo visual se deja para después,
  como pidió el usuario.
**Fallo abierto**: en 213, hablar con la recepcionista de la Fábrica cuelga el juego.
- El juego queda en bucle dentro de un `printf`, que parece un aviso de error que no
  vuelve.
- En 517 funciona.
**Estado del laboratorio**:
- El warp de desarrollo apunta a la zona 213; `faraway/dev_overlay.sh 213 0` lo
  reconstruye.
- `use_gdbstub` vuelve a estar en `false`.
- Partida `work/frontier/lab/f6_pass.sav` (`333ebfc5…`).
Siguiente paso:
1. En 213, hablar con un NPC que no sea de la Mansión. Si cuelga cualquiera, el problema
   está en el clon (área o registro). Si solo cuelgan las recepcionistas, mirar qué
   comprueban las nativas de la Mansión (`BattleInstWorkCreate` `0x1e5cd4`, …) sobre
   la zona; empezar por los retornos de la pila `0x3dc308`, `0x3ffc54` y `0x50334c`.
2. Si la Mansión exige la zona 517, otra vía: la isla lleva a la 517 real. La salida de
   517 la elegiría un script según un work puesto al entrar desde la isla (disparador +
   `_MapChangeCore`), en vez del warp fijo a 516.
3. Probar la vuelta en ferry desde la isla y guardar en la isla.

## 2026-11-03 01:26 — Claude Code — F6: resuelto el cuelgue de la sala clonada
Estado: hecho (la F6 sigue en curso)
Hecho:
- Causa: `code.bin` registra las nativas por zona. En `0x587d58` hay una máscara por
  zona y el bit 8 (nativas de la Mansión) solo está en 448, 517 y 520. El script de 517 en
  213 cargaba sin 44 nativas y `amx_Exec` fallaba en cada evento, con cualquier NPC.
- `frontier/patch.py` `zone_natives`: cada clon toma la máscara de su donante, con
  comprobación de la tabla. `island_build.CLONES` sirve de lista de clones y de máscaras.
- `frontier/zone_natives.py`: inspección de solo lectura de la tabla y de un volcado AMX.
Evidencia:
- `reports/frontier.md` §19: direcciones, volcado gdb y capturas `f6e_*`.
- `python -m pytest -q tests` → 143 passed. Hay 3 tests nuevos y dos roturas a mano, que
  fallan.
- Azahar, en 213:
  - la recepcionista habla;
  - la Fábrica sortea alquileres, guarda y combate;
  - al perder se vuelve a 213.
- La partida guardada en 213 (`f6e_saved_213.sav`, `c013ad56…`) carga en 213.
- Salida al muelle; ferry de la isla → Portual.
Commits: el de esta entrada.
Decisiones:
- Descartado el campo `0x18` de la cabecera: con 213 = 12 seguía colgándose. El cambio se
  deshizo.
- Se mantiene la sala clonada 213. No hace falta llevar la isla a la 517 real (opción 2 del
  paso anterior).
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Sin probar todavía:
   - vuelta a Calagua desde la isla;
   - la entrada de la isla en el ferry de Portual;
   - ganar una ronda de la Fábrica en 213;
   - guardar desde el menú en el muelle 209.
2. Seguir la F6: distribución de Esmeralda con el catálogo de edificios de CTRMap,
   textos ES/EN y el paquete Luma encadenado con v0.5.

## 2026-11-03 03:1x — Claude Code — F6: ferris, guardado en el muelle y ronda ganada en la isla
Estado: hecho (la F6 sigue en curso)
Hecho: se probaron en Azahar los cuatro puntos pendientes de la entrada anterior.
- **Guardar desde el menú en el muelle 209**: guarda, y la partida carga en el muelle.
- **Isla → Calagua**: llega al puerto de Calagua.
- **Ferry de Portual**: ofrece «Isla del Frente» y lleva a la isla.
- **Ronda ganada en 213**:
  - victoria;
  - cambio de alquiler (Larvitar → Glameow);
  - el combate 2 empieza con Glameow.
No hubo cambios de código.
Evidencia: `reports/frontier.md` §20, con las capturas `work/frontier/lab/f6f_*` y la
partida `f6f_saved_pier.sav` (`91b41949…`).
Commits: el de esta entrada.
Decisiones:
- La isla queda funcional de punta a punta: ida y vuelta por ambos ferris, guardado, y
  Fábrica completa con victoria y cambio.
- Se pasa a la parte visual de la F6.
**Estado del laboratorio**:
- warp de desarrollo → 213, con `work/frontier/build` regenerado sobre él;
- `use_gdbstub` en `false`;
- lab parado.
Trampas anotadas en §20:
- `overlay.py` hereda el warp de desarrollo;
- la tecla B es `s`;
- las pulsaciones largas se repiten a 300 %.
Siguiente paso: seguir la F6.
1. Distribución de Esmeralda con el catálogo de edificios de CTRMap-F5. Primero medir
   qué modelos de edificio y qué zonas exteriores sirven de donante para un exterior con
   varias puertas: Fábrica y, más adelante, las otras instalaciones.
2. Textos ES/EN.
3. Paquete Luma encadenado con v0.5.
4. Plan de prueba en consola.

## 2026-11-03 05:xx — Claude Code — F6: plaza de la isla con la Fábrica enlazada y seis maquetas
Estado: hecho (la F6 sigue en curso)
Hecho:
- **Plaza**: la mitad sur del muelle de la isla (celda 0,1 de la zona 209) se repinta como
  explanada con 7 edificios del catálogo de CTRMap-F5, uno por instalación de Esmeralda.
  - Solo la Fábrica (el Gimnasio) tiene puerta: casilla (20,57) → sala 213. La salida de
    213 vuelve a la puerta.
  - Las otras seis son maquetas sin warp.
  - El warp del extremo norte del muelle a 213 desaparece.
- **Código**:
  - `faraway/java/ctrmap/tests/FrontierPlaza.java` (pinta y pone la puerta);
  - `faraway/java/faraway/Plaza.java` (lee el plan);
  - `island_build`: `FACILITIES`, `DOORS`, `PLAZA_RECT`, `AREA_LIMIT`, `check_area`.
  - El plan de la plaza se ejecuta tras la build de los clones.
- Laboratorio: `frontier/lab_plaza_base.py` y `frontier/lab_plaza.sh`, para probar variantes
  de plaza.
Evidencia:
- `reports/frontier.md` §21: tabla de 15 variantes y capturas `f6g_*`.
- `python -m pytest -q tests` → 145 passed. Hay 2 tests nuevos. Tres roturas a mano (guarda
  de área, prop de puerta, segunda puerta) fallan cada una en su test.
- **Azahar**: la isla carga; entrar y salir por la puerta de la Fábrica funciona; la
  maqueta no deja pasar; se vuelve al ferry.
Commits: el de esta entrada.
Decisiones:
- **Sin props de puerta**: con prop, la isla se cuelga al cargar (v3/v2 frente a v5/v7).
- **Límite de área**: el área de la isla debe quedar por debajo de 386.675 bytes (lo mayor
  medido que carga; desde 458.007 cuelga). Por eso solo hay tres modelos (Gimnasio y dos
  casas repetidas).
- Distribución provisional, aproximada a Esmeralda: la Torre al norte, tres edificios en
  medio y tres al sur. Los modelos, para más adelante.
- **Agentes por edificio**: plan en PLAN §6, «Después». Van en serie, con un integrador
  para los ficheros compartidos.
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` contiene la plaza;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Probar la partida completa por la puerta nueva: combate en 213 y guardar en la
   explanada.
2. Medir por qué cuelga el prop de puerta y cuál es el límite real del área. Sin eso, no
   hay modelos distintos por instalación.
3. Defectos visibles:
   - barandillas del muelle sobre la explanada;
   - cerca de la casa de Lavacalda en (33–34, 58).
4. Textos ES/EN, paquete Luma y plan de consola.

## 2026-11-03 06:xx — Claude Code — F6: ronda por la puerta de la Fábrica y guardado en la explanada
Estado: hecho (la F6 sigue en curso)
Hecho:
- Prueba de la partida completa con la build de `ea733e9`, sin cambios de código:
  - muelle → explanada → puerta de la Fábrica → sala 213;
  - inscripción en la Fábrica con la recepcionista de la derecha (hablándole desde 23,25);
  - combate 1 contra Gothorita y Kricketune, perdido; la limpieza devuelve el equipo
    propio;
  - salida a la explanada, guardado allí y recarga en (20,59) con control libre.
Evidencia:
- `reports/frontier.md` §22 y capturas `work/frontier/lab/f6h_*`.
- Partida `work/frontier/lab/f6h_saved_plaza.sav` (`00a9a98f…`).
- El final del combate no se capturó: se pulsó A de más. La derrota se deduce del
  equipo propio en el menú después (`f6h_party_after.png`).
Commits: el de esta entrada.
Decisiones:
- No se repite la victoria por la puerta nueva: la sala, el script y la zona son los de §20,
  donde ya se ganó y se hizo el intercambio.
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` contiene la plaza;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Medir por qué cuelga el prop de puerta y cuál es el límite real del área. Sin eso, no
   hay modelos distintos por instalación.
2. Defectos visibles:
   - barandillas del muelle sobre la explanada;
   - cerca de la casa de Lavacalda en (33–34, 58).
3. Textos ES/EN, paquete Luma y plan de consola.

## 2026-11-03 08:xx — Claude Code — F6: puertas animadas en la plaza; el cuelgue era una textura fuera del paquete del mapa
Estado: hecho (la F6 sigue en curso)
Hecho:
- **Causa medida del cuelgue** de §21, que corrige sus dos conclusiones:
  - el pintor de CTRMap-F5 da por presente una textura del edificio si está en el paquete
    de props del área (fichero 1) y no la copia al del mapa (fichero 11);
  - el juego solo busca las texturas del mapa en el fichero 11, y se cuelga.
  - La provoca el prop de puerta (`chip_mado_a`, `poke_gym_mado`) y también el paquete de
    props original del puerto (`c102_09_mado`, en v6, v10 y v12, sin props).
- **Arreglo en nuestro código** (CTRMap-F5 no se toca):
  - `FrontierPlaza.keepWorldTexturesInWorldPack` copia esas texturas al fichero 11 y se
    niega si alguna sigue faltando;
  - `Plaza` lo llama tras el pintado.
- **Cota nueva**: la de tamaño de área (386.675) queda refutada. `LOAD_BUDGET = 2724608`
  sobre la suma que imprime `Plaza` (paquete del mapa + props + modelos de las regiones).
  Sustituye a `AREA_LIMIT`/`check_area`.
- **Puertas**:
  - los siete edificios llevan su prop de puerta (sin `nodoorprop`);
  - `island_build` exige que se coloquen y que la copia de texturas se haya hecho.
- Nueva herramienta de solo lectura `faraway/java/faraway/WorldTextures.java`.
Evidencia:
- `reports/frontier.md` §23: tablas, partición del prop y fix11.
- **Azahar**: la isla carga con las puertas; se entra en 213 y se vuelve a (20,58); la
  maqueta no deja pasar (`f6i_*`).
- `python -m pytest -q tests` → 145 passed.
- **Roturas a mano**:
  - sin la copia de texturas, la build se niega nombrando las dos texturas;
  - dos mutaciones de `check_budget`: cada una falla su test.
Commits: el de esta entrada.
Decisiones:
- `LOAD_BUDGET` es lo mayor medido que carga, no el límite del motor: las áreas originales
  tienen paquetes mayores.
- La distribución sigue con tres modelos; ahora caben más distintos (v10f, con cuatro,
  carga).
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` contiene la plaza con puertas;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Elegir un edificio distinto por instalación dentro de `LOAD_BUDGET`. Medir con
   `lab_plaza.sh` y `WorldTextures`.
2. Por qué cuelgan v6 y v14, sin hueco de texturas y por encima de la cota.
3. Defectos visibles:
   - barandillas del muelle sobre la explanada;
   - cerca de la casa de Lavacalda en (33–34, 58).
4. Textos ES/EN, paquete Luma y plan de consola.
5. Avisar al autor de CTRMap-F5 del fallo de `missingIn` (solo si el usuario quiere).

## 2026-11-03 10:xx — Claude Code — F6: plaza fija con un edificio distinto por instalación
Estado: hecho (la F6 sigue en curso)
Hecho:
- **Coste de cada edificio** del catálogo medido sin emulador (`frontier/lab_building_costs.sh`).
- **Distribución fija** (`island_build.FACILITIES`), con un edificio distinto por instalación:
  - Torre: Férrica, tejado plano;
  - Domo: casa de Pardal;
  - Fábrica: Gimnasio;
  - Pirámide: casa de tejas de Azuliza;
  - Tubo: cabaña de la Ruta 124;
  - Arena: casa de paja del Resort;
  - Palacio: Férrica, dos plantas.
  - Presupuesto 2.665.344 bytes, por debajo de `LOAD_BUDGET`.
- **Edificios que no se dibujan**: la choza de Pacifidlog y la casa de Lanette se colocan
  pero el juego no las dibuja. `island_build.NOT_DRAWN` los rechaza, y `plan()` exige siete
  edificios distintos.
- **PLAN**: reparto entre agente e integrador para «un edificio por agente». El integrador
  asigna las zonas de interior y toca los ficheros compartidos; cada agente trabaja en su
  módulo.
Evidencia:
- `reports/frontier.md` §24: tabla de costes, tabla de puertas y frentes, capturas
  `work/frontier/lab/f6j_*`.
- **Azahar**: se ven los siete edificios; las seis maquetas bloquean desde su frente; la
  Fábrica entra y sale con la build definitiva.
- El área y las regiones de la build son idénticas byte a byte a las de la variante
  recorrida.
- `python -m pytest -q tests` → 146 passed. Las dos mitades de la guarda nueva fallan su
  test al romperlas a mano.
Commits: el de esta entrada.
Decisiones:
- Fuera el Centro Pokémon y la Tienda (se confundirían con los de verdad).
- Los modelos siguen siendo provisionales; lo fijo es el sitio y la puerta de cada
  instalación.
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` contiene la plaza fija;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Desplegar los agentes por edificio cuando el usuario dé el sí, con el número de agentes
   y el coste dichos antes (norma de CTRMap-F5). Plan en PLAN §6, «Después».
2. Defectos visibles: tejado azul de la casa de Azuliza, barandillas del muelle.
3. Textos ES/EN, paquete Luma y plan de consola.

## 2026-11-03 11:xx — Claude Code — F6: diseños por instalación y reparto con Codex
Estado: hecho (la F6 sigue en curso)
Hecho:
- **Diseños**: seis agentes de diseño de solo lectura, con el sí del usuario. Uno por
  instalación: Torre, Domo, Pirámide, Tubo, Arena y Palacio. Sus informes están en
  `reports/diseno/*.md`; los copié yo, porque los agentes no escribieron en el repo.
  - Coste medido de los seis: unos 1,0 M de tokens (148–180 mil cada uno).
- **Fallo latente que señalaron cuatro diseños, arreglado**:
  - la salida de cada interior vuelve ahora a su propia puerta (`island_build.door_warp`);
  - antes estaba fijada al warp 0.
  - El plan actual tiene las mismas 21 líneas que antes, comparado con el de `HEAD`.
- **`frontier/REPARTO.md`**:
  - turno único de escritura y laboratorio;
  - dueño por instalación;
  - zonas asignadas por verificar;
  - trabajo común del integrador.
- `AGENTS.md`: leer REPARTO y tomar el turno al empezar.
Evidencia:
- `python -m pytest -q tests` → 147 passed.
- Romper `door_warp` a mano hace fallar `test_each_interior_exits_to_its_own_door`.
Commits: el de esta entrada.
Decisiones:
- **Reparto provisional, por confirmar con el usuario**:
  - Claude Code lleva las instalaciones que son un clon de 517 con equipo propio: Torre,
    Palacio y Arena.
  - Codex lleva las que necesitan zonas y ganchos nuevos: Domo, Tubo y Pirámide.
- Las reglas de Esmeralda de los diseños están sin fijar a un commit de pokeemerald; hay que
  contrastarlas antes de usarlas como constantes.
- Dos avisos de los diseños, sin verificar:
  - la tabla de PB de la Fábrica (posible 1 PB de menos desde la ronda 15);
  - el agente de la Torre descargó pokeemerald fuera del repo (en el directorio temporal de
    la sesión).
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` contiene la plaza fija;
- `use_gdbstub` en `false`;
- lab parado.
Siguiente paso:
1. Integrador: trabajo común de `REPARTO.md`, puntos 2–7 (ruta de racha por valor, registro
   de works, clones genéricos, máscara de nativas aparte, exclusión mutua, tabla de PB).
2. Torre (Claude Code), según `reports/diseno/torre.md`, empezando por verificar la zona
   329.
3. Codex, cuando el usuario lo abra: la instalación que le toque según `REPARTO.md`.

## 2026-11-03 13:xx — Claude Code — F6: trabajo común del integrador (racha por instalación, clones genéricos, PB)
Estado: hecho (la F6 sigue en curso)
Hecho:
- **Tabla de PB**: `data.FRONTIER_BP` tiene ya las siete columnas de pokeemerald `731ad5bf`,
  leídas con un parser y comprobadas contra la fuente. La Fábrica se cortaba en la ronda 13:
  daba 9 PB en vez de 10–15 desde la ronda 15.
- **Racha por instalación**:
  - `WORK_ROUTE` elige la instalación por su valor (`patch.STREAK_ROUTES`, tabla
    `slot_deltas` en `rental.s`);
  - los valores desconocidos dejan la racha de la Mansión;
  - cada instalación tiene su trío de works: racha, «desafío a medias» y récord
    (`REPARTO.md`).
- **Clones genéricos** en `island_build`: `CLONES`, `KEEP_TEXT`, `NATIVE_DONORS`,
  `native_donors()` y `build(..., zone_scripts)`.
- **Exclusión mutua**: queda fijada la convención (`patch.ACTIVE_WORK`); se programará con la
  Torre.
Evidencia:
- `python -m pytest -q tests` → 159 passed.
- **Roturas a mano** (cada una falla su test):
  - quitar la comprobación de rutas;
  - desplazar el índice de la tabla;
  - devolver solo `CLONES`;
  - aceptar el script de la isla.
- **Build**: el gancho pasa de 496 a 572 bytes; la sala, a ZO 15.748.
- **Azahar**: una ronda de la Fábrica con el `code.bin` nuevo empieza y acaba en derrota sin
  colgarse; las rachas siguen a 0 (`f6k_after_loss.sav`). Sin probar en el juego: una
  victoria que suba la racha (la cubren los tests Unicorn).
Commits: `07b36bd`, `79d8a40` y el de esta entrada.
Decisiones: la exclusión mutua se programa con la segunda instalación, porque antes no hay
nada que excluir ni manera de probarla.
**Estado del laboratorio**:
- warp de desarrollo → 213;
- `work/frontier/build` con el `code.bin` nuevo;
- `use_gdbstub` en `false`;
- lab parado.
- **Turno: libre.**
Siguiente paso:
1. Codex: Domo, Tubo o Pirámide según `REPARTO.md`.
2. Claude Code: Torre (`reports/diseno/torre.md`), con la exclusión mutua y una ronda ganada
   en Azahar.
Una sola herramienta a la vez.

## 2026-11-03 16:xx — Codex — Nivel de Trapinch con DexNav
Estado: hecho
Hecho: consulta del usuario, sin avanzar instalaciones ni cambiar el juego.
Trapinch en Ruta 111, zona 35: slots normales 5 y 6, niveles 20 y 22,
idénticos en limpio y Repolished. Aplicando la regla documentada del DexNav,
el máximo es 22 + 19 por racha + 10 por bonus = 51.
Evidencia: `source scripts/env.sh`; Python importando
`scripts/inspect_encounters.py:inspect_location`, para clean/repolished y
`Ruta 111`, filtrando species == Trapinch. Hashes comprobados por el lector.
Regla externa: https://bulbapedia.bulbagarden.net/wiki/DexNav, apartados
Chaining/Boost/Search Level: +1 por cinco encuentros, máximo +19 con 95–99,
reinicio cada 100; bonus +10 cada quinto encuentro o aleatorio (4 %).
El nivel de búsqueda mejora otras propiedades, no añade niveles directamente.
`reports/dexnav.md` confirma que v0.5 solo hace visible la racha.
No probado un Trapinch de nivel 51 en emulador/consola ni reanalizada la rutina
de niveles: el resultado combina la tabla local con la regla publicada.
Commits: 5daf5c3 toma de turno; cierre en el commit de esta entrada.
Decisiones: consulta documental; se devuelve el turno libre. Las fuentes
discrepan: Serebii redondea el máximo a +20/+30; se usa el detalle +19/+29
de Bulbapedia, coherente con contador 0–99 documentado en reports/dexnav.md.
Siguiente paso: Frente según REPARTO (Codex: Domo, Tubo o Pirámide; Claude:
Torre y exclusión mutua). No se inició ninguna instalación en esta consulta.

## 2026-11-03 14:xx — Claude Code — Orquestador frontier-orch (Claude y Codex sin «continúa»)
Estado: hecho
Hecho:
- Petición del usuario: dejarlo todo listo para lanzar una orden y que Claude y Codex trabajen
  solos, pasándose la tarea cuando uno agota su cuota.
- **`frontier/orch/frontier_orch.py`** (lanzador `frontier/orch/frontier-orch`):
  - comandos `auto`, `once`, `status` y `release`;
  - tareas en `tasks.json`: Torre, Domo, Palacio A, Tubo, Arena A y Pirámide, con dueño,
    diseño y criterios;
  - configuración en `config.json`; uso en `README.md`.
- **Qué hace**:
  - tiene el turno de REPARTO mientras corre;
  - reanuda en la misma sesión mientras la tarea siga abierta;
  - si un agente agota su cuota, lo deja en espera y relevo al otro con aviso de revisar el
    estado a medias;
  - pasa los tests cuando el agente marca `done`;
  - se para si la tarea queda `blocked`, sin progreso o al llegar a `max_runs`;
  - limpia el laboratorio tras cada ejecución.
Evidencia:
- `tests/test_frontier_orch.py` (14, con agentes falsos). `python -m pytest -q tests` → 173
  passed, más el test de `after_run`.
- **Roturas a mano**, cada una falla su test: sin espera tras el límite, sin freno por falta de
  progreso, sin aceptación.
- **Con las herramientas reales**, en un repositorio de prueba:
  - Claude 2.1.316 y Codex 0.166.0 hacen cada uno su tarea con commits, sin intervención, y
    el supervisor termina con «all tasks done»;
  - la primera prueba mostró que el sandbox de Codex deja `.git` en solo lectura (no podía
    hacer commit); arreglado con `writable_roots`;
  - la reanudación de Codex hace commit;
  - Codex arranca y para el laboratorio de Azahar (pantalla de título).
- **Sin probar con las herramientas reales**: un límite de uso verdadero y gdb desde el
  sandbox de Codex.
Commits: el de esta entrada.
Decisiones:
- Permisos: Claude `--permission-mode auto --permission-prompts none` (`-p` no admite
  bypass); Codex `workspace-write` con `.git` y la red abiertos.
- El supervisor, no el agente, decide el relevo; el agente puede morir sin escribir su
  resumen.
**Estado del laboratorio**: parado; `use_gdbstub` en `false`. **Turno: libre.**
Siguiente paso: que el usuario lance `frontier/orch/frontier-orch auto`. Empieza por F6-TORRE
(Claude).

## 2026-11-03 21:xx — Claude Code (Opus 5.5) — F6-TORRE: Torre v1 en código y exclusión mutua (frontier-orch)
Estado: en curso
Hecho:
- **Zona 329 comprobada sin emulador** (`frontier/zone_check.py`, salida en `work/frontier/tower/zone_check.txt`):
  máscara de nativas 0x243, sin warps de entrada, y sus dos literales en scripts no son zonas: el compartido 57
  (`0x77c`: `ItemAddCheck` y dos `FlagSet`, el 329 es un flag de objeto) y la zona 275 (`_CallTrainerBattleCore`,
  el 329 es un entrenador). Palabras alineadas = 329 en el código: 36, frente a 48 (209) y 45 (213), ya verificadas.
- **`frontier/tower.py`**: script de la zona 329 desde el 517 **retail** (sin la Fábrica): ruta 0 tras
  `BattleInstWorkCreate`; «Combatir» → `tower_reception` (rango Normal, ruta 2, racha nueva a 0, 16442 = 1 durante
  el desafío y después solo si la racha no es 0, ruta a 0 al volver); 16442 = 0 en la derrota (`0x2210`) y la
  limpieza (`0x1458`); PB de `data.FRONTIER_BP['tower']` cada 7 con ruta 2. Selección de equipo `0x457c` intacta.
  Script 14.892 bytes, ZO 15.684 (≤ 17.248).
- **Exclusión mutua** (`factory.busy_check`): la Torre y la Fábrica se niegan, sin tocar nada, si el
  `patch.ACTIVE_WORK` de otra instalación no es 0, con la línea nueva 189 del texto 619 (`factory.LINE_BUSY`).
- **Integración**: `island_build.CLONES[329] = 517`, `KEEP_TEXT`, `DOORS['Tower'] = (329, 0)` (la Torre es ahora el
  warp 0 de la isla y la Fábrica el 1, por `door_warp`); `overlay.facility_scripts()` pasa el script de 329.
Evidencia: `python -m pytest -q tests` → 199 passed (26 nuevos en `tests/test_frontier_tower.py`). Roturas a mano:
sin `busy_check` en la Fábrica falla `test_factory_refuses_while_the_tower_is_in_progress`; sin la comprobación de
racha tras el desafío falla `test_a_new_tower_challenge`. **No probado en Azahar todavía.**
Commits: el de esta entrada.
Decisiones: la línea de rechazo va en el texto 619, que comparten 517, 213 y 329; la Torre, al rechazar una
confirmación con un desafío pausado, lo deja pausado.
Siguiente paso: build con la isla (`python frontier/overlay.py --out work/frontier/build --romfs
work/faraway/dev/overlay/romfs`) y pruebas en Azahar de la tarea F6-TORRE.

## 2026-11-03 22:xx — Claude Code — frontier-orch: primera ejecución real y arreglo del relevo por sesión caducada
Estado: hecho (F6-TORRE sigue en curso)
Hecho:
- **Primera ejecución de `frontier-orch auto` lanzada por el usuario**, a las 21:00, sobre
  F6-TORRE:
  - Claude trabajó 37 minutos (165 turnos; coste equivalente 11,27 USD según su JSON) e hizo
    dos commits:
    - `9dc2dc8`: script de la Torre en la zona 329, exclusión mutua con la Fábrica e
      integración;
    - `bdae3b7`: selección de modo antes del desafío, visto en Azahar.
  - Luego caducó su sesión: «Failed to authenticate: OAuth session expired and could not be
    refreshed».
  - El supervisor lo trató como error normal, reintentó dos veces en un segundo y bloqueó la
    tarea por «2 ejecuciones sin cambios». No quedó nada a medias sin commit; el laboratorio,
    parado.
- **Arreglo del supervisor**:
  - una sesión caducada o sin login deja al agente fuera hasta el próximo `auto`, y el otro
    hereda la tarea con aviso de relevo;
  - si los dos están sin login, se para y lo dice;
  - `status` funciona con `auto` en marcha;
  - el registro de cada ejecución se escribe en directo (Claude con `stream-json`).
- F6-TORRE reabierta, con una nota de dónde se quedó; su sesión de Claude se conserva para
  reanudarla.
Evidencia:
- `work/orch/logs/20261103-210029-claude-F6-TORRE.log` y los dos de 21:37.
- `tests/test_frontier_orch.py` (24); `python -m pytest -q tests` → 212 passed.
- Romper el relevo por login hace fallar `test_an_expired_login_hands_over_and_keeps_that_agent_out`.
- `claude -p --output-format stream-json --verbose` real, interpretado bien por `parse`.
Commits: el de esta entrada.
**Estado del laboratorio**: parado; `use_gdbstub` en `false`. **Turno: libre.**
Siguiente paso: `frontier/orch/frontier-orch auto` otra vez. Claude reanuda F6-TORRE: build y
pruebas de Azahar.

## 2026-11-03 23:38 — Codex — F6-TORRE: auditoría del relevo y recuperación de pruebas
Estado: en curso
Hecho:
- Revisados `git status --short`, `git diff` y último commit (`bfe7d31`, toma de turno del supervisor).
  No hay cambios versionados a medias. Los cinco archivos sin seguimiento de consultas de encuentros,
  evoluciones e iniciales se conservan sin tocarlos. No se cambia REPARTO: el turno es del orquestador.
- Recuperado el hito `bdae3b7`: selección de modalidad antes de elegir equipo, texto de rechazo más corto y
  `lab_tower.py`. La sesión anterior sí llegó a jugar después de ese commit, aunque no escribió su entrada.
  Extracto de sus comandos/resultados: `work/frontier/tower/previous-transcript.txt` (sesión Claude
  `450b9107-992a-4571-9d30-063066c3155f`).
- Inspeccionadas con `save_event` las partidas originales del laboratorio anterior:
  `f6t_saved_329.sav` SHA256 `33bb1d0fae0a68699340624aabb6422750126bb5cf4743d437e1edde21992db7`
  (zona 329, racha/récord Torre 6, ruta 2, activo 1, PB 0) y `f6t_paused12.sav`
  SHA256 `df1b162bf818a9a27b9862646f297336fe4e36d7a57c7eed72db411934d2155a`
  (zona 329, racha/récord 12, ruta 2, activo 1, PB 1). Fábrica 16437 y Mansión 0x1BBC0 a cero.
  Evidencia heredada de seis victorias, incluido el final de ronda 7, y guardado al pausar; no se afirma
  que Codex haya jugado esos combates. El punto de partida fue una copia con racha editada a 6.
Evidencia:
- `source scripts/env.sh && python -m pytest -q tests`: 212 passed (9,93 s).
- Build completa ejecutada: `python frontier/overlay.py --out work/frontier/build --romfs
  work/faraway/dev/overlay/romfs`; registro `work/frontier/tower/build-codex.log`; 329 clonado de 517,
  área propia 233; hook 572 bytes.
Commits: `9dc2dc8`, `bdae3b7`; recuperación documental en el commit de esta entrada.
Decisiones: conservar la implementación y volver a probar los casos pendientes con la build recién generada.
Siguiente paso: reanudar `f6t_paused12.sav`, comprobar derrota, ambas salidas y exclusión en ambos sentidos;
victoria con la ruta 1 de la Fábrica. Documentar §25 y completar aceptación antes de marcar done.

## 2026-11-03 23:49 — Codex — F6-TORRE: reanudación, dos victorias, PB y pausa verificados
Estado: en curso
Hecho: cargada la partida pausada 12 en la build completa, elegidos los tres Pokémon propios y ganados los
combates 13 y 14. El 14 entrega 2 PB; se ofrece el 15. Pausa guardada con racha/récord 14, activo 1, ruta 2,
PB totales 3. Mansión y Fábrica conservan sus rachas a cero. Salida de la Torre medida en (19,47).
Añadido `reports/frontier.md` §25 con comprobación de zona, evidencia heredada y pruebas nuevas.
Evidencia: `work/frontier/lab/f6tc_tower_bp2.png`, `f6tc_next15.png`, `f6tc_tower_exit.png`;
`f6tc_paused14.sav` SHA256 `eb6d1fa2ce58e3dafaec9847d36b344bfecff622cf05ba9b46f8f7ee799d4eb9`;
lector/checksums y registro en `work/frontier/tower/snapshot.py`, `save-evidence.jsonl`.
`python -m pytest -q tests`: 212 passed (10,95 s), `work/frontier/tower/tests-round14.log`.
El bloque de Mansión es idéntico. El equipo conserva especies/objetos/movimientos/EXP/EV/IV; varían PS por cura
(en el ensayo anterior) y recuerdos del entrenador original (PK6 +0xCC–0xD0, fuente PKHeX enlazada en §25).
Commits: el de esta entrada; anterior `2951a31`.
Decisiones: no confundir los cambios retail de recuerdos/curación con una sustitución por alquileres.
El laboratorio requiere una terminal persistente en Codex: al cerrarse la llamada que lo inicia, termina su
namespace de procesos. No mandar Ctrl-C al shell del laboratorio: también lo cierra. Arranque/control/GDB/parada
van por el mismo `exec_command` interactivo. Se recargó `f6tc_paused14.sav` después de cerrar uno de esos shells.
Siguiente paso: completar derrota, rechazos en ambos sentidos y entrada/salida/victoria de Fábrica; aún no probado.

## 2026-11-04 02:xx — Claude Code (Opus 5.5) — F6-TORRE: derrota, exclusión en ambos sentidos, ruta 1 y works de la Fábrica movidos
Estado: hecho
Hecho:
- **Relevo revisado**: `git status`/`git diff` limpios tras Codex (`2951a31`, `6576e48`); solo los cinco archivos
  sin seguimiento de consultas ajenas, que no se tocan. Nada a medias.
- **Derrota en la Torre** (Azahar): desde `f6tc_paused14.sav`, reanudar, combate 15 y huir. Partida de la derrota:
  16441/16442/16443 = 0/0/14, PB 3, Mansión a cero.
- **Rechazos**: Torre con la Fábrica pausada → «Tienes un desafío a medias en otra instalación…» (texto corto
  completo). Fábrica con la Torre pausada ya visto en la sesión del 2026-11-03.
- **Fallo de la Fábrica encontrado y corregido**: entrar en 213 o 329 pone a 0 los works 16410–16413 (medido
  guardando desde el menú antes y después; recargar no los toca). Una Fábrica pausada se perdía al salir de la sala.
  `WORK_IV` → 16489, alquileres → 16485–16487, generador → 16490; `rental.s` lee los alquileres por debajo de
  `WORK_IV`; test nuevo que veta el bloque 0x4010–0x401F. REPARTO actualizado (tabla de works).
- **Ruta 1 en el juego**: con el arreglo, Fábrica pausada → plaza → 329 (rechazo) → 213: reanuda sin sorteo, gana el
  combate 1 y pausa con 16437 = 16439 = 1, Mansión a cero. Salida de 213 a (20,58); de 329 a (19,47).
- `reports/frontier.md` §25 completado.
Evidencia: `python -m pytest -q tests` → 213 passed. Partidas `work/frontier/lab/f6td_after_loss.sav` (`692f9d4a…`),
`f6td_factory_paused1.sav` (`bc3c35e7…`), `f6t_factory_paused2.sav` (`c70f4519…`); capturas `f6td_*.png`;
registros `work/frontier/tower/lab3.log`–`lab7.log`. Build `python frontier/overlay.py --out work/frontier/build
--romfs work/faraway/dev/overlay/romfs` (hook 580 bytes).
Commits: el de esta entrada.
Decisiones: mover el estado de la Fábrica en vez de reescribirlo al entrar (no se sabe qué código borra el bloque).
Las partidas antiguas con la Fábrica pausada en 16410 pierden ese desafío (no hay versión publicada con ellos).
Sin probar: consola; jefe de la Mansión en la Torre; reinicio sin guardar en 329.
**Estado del laboratorio**: parado; `use_gdbstub` en `false`.
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json` (F6-DOMO, Codex). Para Palacio y Arena (Claude),
copiar el patrón de `frontier/tower.py` (selección de modalidad incluida) y no usar works de 0x4010–0x401F.

## 2026-11-04 04:xx — Claude Code (Opus 5.5) — F6-DOMO: Domo v1 en código (frontier-orch, relevo de Codex)
Estado: en curso
Hecho:
- **Relevo**: Codex se cortó por límite de uso sin dejar nada de F6-DOMO (sin commits; `git diff` solo traía
  `tasks.json` en `in_progress`, del orquestador). Los cinco archivos sin seguimiento de consultas ajenas no se tocan.
- **Zona 456** comprobada sin emulador (`frontier/zone_check.py 456` → `work/frontier/dome/zone_check.txt`): máscara
  0x243, sin warps entrantes; sus dos operandos están en el compartido 35 (`0x1728`, `0x1750`, `PUSH_P_C 456` sin
  cambio de mapa detrás); 30 palabras alineadas = 456 (frente a 48 y 45 de 209 y 213).
- **Medido** (para no depender de la pantalla de la Mansión):
  - `PokePartyGetParam(hueco, param, 0)`: tabla de saltos de `DllField.cro` `0x4e618` → param 0 especie
    (`0x1532d8`, bloque A +0), 12 objeto (`0x4d2454`, bloque A +2), 8 huevo.
  - `CallPokeSelect(1, 0x800C, 0, 1)` en 17 de 23 usos retail; 6 = cancelado.
  - `WordSetTemotiMonsNickName(buffer, hueco)`; etiqueta del mote `[VAR 0102 n]` (texto 85). Los menús admiten
    `WordSet` (retail: `WordSetItemName` → `ListMenuAdd`, compartido 40 `0x1084`).
  - Constructor del rival `0x1e4a94`: archivo en `r2` (`[sp,#0xe0]` = su `r1`, abierto en `0x1e4b48`); repite sin
    límite si se repite especie dentro del equipo (`0x1e4bdc`), hasta 50 veces por objeto; en Individual
    (`0x1e35f0`) no hay listas de exclusión. Tamaño del rival Individual: `mov r6,#3` en `0x1e3548`.
  - Menú tras ganar (`0x2290` → `0x3b90`): 0 seguir, 1 guardar y descansar, 2 retirarse.
- **`frontier/asm/dome.s`** (enlazado tras `rental.s`, hook 736 bytes): `dome_party` (desde la rama retail de
  `rental_hook`: con la ruta 5, `work+0x30/0x34` = 16649/16650 y `+0x48` = 2), `dome_rival` (desde `rival_hook`:
  ranuras 0–1 = 16657/16658, `r2` = 0xb6/0xb8) y `dome_count` (`bl` en `0x1e3548`: 2 con la ruta 5).
- **`frontier/dome.py`**: script de 456 desde el 517 retail (como la Torre): recepción `dome_reception`
  (exclusión, ruta 5, inscripción por GlobalCall 9773 también al reanudar, desafío `0x18f8(0,0,0)`), salto de
  `0x457c` con la ruta 5, `dome_before_battle` en `0x1edc` (GlobalCall 9774), ACTIVE = 0 en `0x2210`/`0x1458`,
  PB tras cada final (`FRONTIER_BP['dome']`, con la línea del campeón, GlobalCall 9775). Script compartido 5:
  `dome_entry` (3 × pantalla del equipo, sin huevos ni especie/objeto repetidos), `dome_round` (ronda, 3 conjuntos
  del rival del nivel de la Fábrica por torneos ganados, vista previa, 2 de 3 por mote, B vuelve a la vista previa,
  2 forzados al azar) y `dome_won`. Textos: 16 líneas al final del 637 (998–1013).
- **Integración**: `CLONES[456] = 517`, `KEEP_TEXT`, `DOORS['Dome'] = (456, 0)` (warps de la isla: Torre 0, Domo 1,
  Fábrica 2); `overlay.facility_scripts`; `factory.shared_program(..., extra)`; `Routine.new_label` con el nombre de
  la rutina (las etiquetas chocaban). Works en REPARTO.
Evidencia: `python -m pytest -q tests` → 288 passed (75 nuevos en `tests/test_frontier_dome.py`: VM y Unicorn).
Roturas a mano: sin `moveq r6` falla `test_rival_party_size[5-2]`; sin `bl dome_party` falla
`test_dome_route_selects_its_two_fighters`; sin `busy_check` fallan 6 de exclusión. Script de 456: 14.996 bytes,
ZO 15.788. **No probado en Azahar todavía.**
Commits: el de esta entrada.
Decisiones: inscripción propia con `CallPokeSelect` (no la app de la Mansión: no se puede leer qué eligió); el
torneo no sale al vestíbulo tras la final: sigue el menú de la Mansión (seguir = torneo siguiente, descansar,
retirarse); la racha cuenta combates (torneos = racha / 4); al reanudar se vuelve a inscribir.
Siguiente paso: build con la isla y Azahar: puerta (6,56) → 456 → salida (6,57); Fábrica por su nuevo warp 2;
inscripción, vista previa, 2 contra 2 (gdb en el hook), torneo de 4 con PB; derrota; pausa y reanudación; exclusión.

## 2026-11-04 05:11 — Codex — F6-DOMO: relevo auditado y dos contra dos medido en Azahar
Estado: en curso
Hecho: revisados git status, diff y último commit (2326b25). No hay código a medias; solo tasks.json
con in_progress, que se conserva. Los cinco archivos ajenos sin seguimiento no se tocan.
Build repetida, entrada por la puerta del Domo, recepción, inscripción de tres, guardado en 456,
vista previa y elección de dos probados. GDB confirma exactamente los dos huecos elegidos y dos
rivales pertenecientes a los tres anunciados. Añadido reports/frontier.md §26.
Evidencia: pytest 288 passed (work/frontier/dome/tests-codex.log); build-codex.log;
trace.gdb/gdb-teams.log: jugador count=2 slots=2,0; rival r6=2, N108/N79 de 108,79,83.
dc_registered.sav SHA256 3294aa93b5c3fe83df3c79f0e40815fa6cd4be2ac68d783ad8957cb580472fcf.
Capturas dc_* en work/frontier/lab; snapshot.py y save-evidence.jsonl en work/frontier/dome.
Commits: 2326b25 (implementación heredada); el de esta entrada (validación parcial).
Decisiones: mantener el turno del orquestador. La sesión de Claude llegó más lejos que su entrada:
comandos recuperados en work/frontier/dome/previous-commands.txt, pero se han repetido las pruebas.
Las cuatro rondas y dos combatientes contrastados con pokeemerald 731ad5bf (fuente en §26).
Siguiente paso: ganar el torneo en el laboratorio activo (shell persistente de esta sesión), probar
pausa/recarga, derrotas, salida, exclusión y regresiones; tareas aún in_progress. El laboratorio
se parará antes de terminar la sesión. No probado todavía lo enumerado como pendiente en §26.

## 2026-11-04 10:xx — Claude Code — frontier-orch: noche sin vigilancia, F6-TORRE hecha, arreglo de esperas
Estado: hecho (F6-DOMO sigue en curso)
Hecho:
- **Noche del 3 al 4 con `frontier-orch auto`** (25 ejecuciones de agente; registros en
  `work/orch/logs/`):
  - Claude estaba en su límite de 5 horas a las 23:34 y Codex heredó F6-TORRE; trabajó hasta
    su propio límite (`2951a31`, `6576e48`).
  - Claude volvió a la 1:35 y la terminó (`c8fbd29`). Aceptada con la suite. Las pruebas de
    Azahar están en `reports/frontier.md` §25 y en `evidence` de `tasks.json`; incluyen la
    racha por ruta de la Fábrica, que estaba pendiente.
  - F6-DOMO: código (`2326b25`, Claude) y entrada, inscripción y 2 contra 2 en Azahar
    (`0c8eb59`, Codex).
  - A las 5:17 el supervisor salió solo. Con los dos agentes en espera, cada espera contaba
    como ejecución y agotó `max_runs` (40). tmux se cerró con él y su último mensaje se
    perdió.
- **Arreglo**:
  - las esperas no cuentan en `max_runs`;
  - la espera dura hasta la hora que imprime el aviso (Claude «resets 6:30am», Codex «try
    again at 10:04 AM»), más 2 minutos;
  - el supervisor escribe su salida en `work/orch/orch.log`;
  - el patrón de límite reconoce «hit your 5-hour limit» aunque no llegue el 429 (en las
    ejecuciones reales llegó).
Evidencia:
- `tests/test_frontier_orch.py` (32); `python -m pytest -q tests` → 296 passed.
- **Roturas a mano** (cada una falla su test):
  - contar las esperas;
  - ignorar la hora de reposición;
  - quitar el patrón nuevo.
Commits: el de esta entrada.
**Estado del laboratorio**: parado. **Turno: libre.**
Siguiente paso: relanzar `frontier-orch auto`. F6-DOMO, con aviso de relevo de Codex.

## 2026-11-04 10:37 — Codex — F6-DOMO: recuperación tras el segundo corte de cuota
Estado: en curso
Hecho: revisados status/diff y último commit 0a18607 (turno del orquestador). Árbol versionado limpio;
solo cinco archivos ajenos sin seguimiento. Los commits posteriores a 0c8eb59 arreglan el supervisor,
no el Domo. No hay cambios de código a medias que revertir. Recuperadas y documentadas en §26 la
victoria 1, pausa 1/1/1 sin PB, salida a (6,57), entrada en Fábrica por warp 2 y rechazo por Domo pausado.
Evidencia: dc_paused1.sav SHA256 9b741a581ac2e0cb1f4c3d83a33e5850ca1f721c534814f282dadb5972c4801b;
work/frontier/dome/save-evidence.jsonl, compare-round1.json, gdb-teams.log; capturas dc_exit,
dc_factory_refused y dc_fight2. Suite actual: 296 passed (tests-relevo.log).
Commits: 0c8eb59; el de esta entrada (recuperación documental).
Decisiones: continuar desde dc_resume_changed.sav (pausa real tras una victoria, orden del equipo
cambiado y bloque de Mansión 20/20 como fixture; generador resume_fixture.py). La ronda 2 de la
sesión anterior no terminó. El laboratorio anterior estaba parado; se abre uno nuevo en shell persistente.
Siguiente paso: completar rondas 2–4, guardar pausa antes de la final para probar también derrota;
validar derrota en primera ronda, equipo, Mansión 20/20, exclusión inversa y regresiones de Fábrica/Torre.

## 2026-11-04 10:44 — Codex — F6-DOMO: reanudación con equipo cambiado y pausa antes de la final
Estado: en curso
Hecho: recargado en 456 dc_resume_changed.sav, inscrito 1,2,0 y elegidos 1,0; GDB y guardado
confirman el orden nuevo. Ganadas las rondas 2 y 3; guardada una pausa real antes de la final.
Evidencia: dc_paused3.sav SHA256 b86d33b81ade525f63844b3af0d1ca79d53d54b84ba89c9187c6898510cc500a,
racha/activo/récord 3/1/3, PB 0, Mansión 20/20. compare-rounds23.json: bloques de equipo y Mansión
idénticos al fixture. GDB cuenta dos por bando en ambos combates. Capturas de_* y §26 del informe.
Suite de esta sesión sin cambios de código posteriores: 296 passed (tests-relevo.log).
Commits: b1a2b48; el de esta entrada.
Decisiones: bifurcar las pruebas desde la pausa 3 para probar derrota y victoria en la final sin
editar la racha. Laboratorio activo durante la sesión; se parará al terminar.
Siguiente paso: reanudar, perder la final, guardar/comparar; recargar dc_paused3.sav y ganarla para
validar PB. Después primera derrota, exclusión inversa y regresiones de Fábrica/Torre. Tarea in_progress.

## 2026-11-04 10:51 — Codex — F6-DOMO: derrotas en primera ronda y final comprobadas
Estado: en curso
Hecho: abandono confirmado dentro del combate final y, tras inscribir un desafío nuevo, dentro de
la primera ronda. Ambas ramas guardan racha/activo/récord 0/0/3 y PB 0. No se forzó el resultado por GDB.
Evidencia: dc_loss_final.sav (e2f91280…), dc_loss1_done.sav (711876fc…), hashes completos en §26;
compare-loss-final.json y compare-loss1.json: equipo completo y bloque de Mansión idénticos antes/después;
Mansión 20/20. Suite de esta sesión 296 passed; no hay cambios de código posteriores.
Commits: 85743ba; el de esta entrada.
Decisiones: dc_loss1.sav era una captura prematura y no es evidencia de derrota; documentado en §26.
Se recarga ahora la pausa real dc_paused3.sav para ganar la final.
Siguiente paso: final ganada y PB; exclusión inversa, regresiones de Fábrica/Torre; parar laboratorio,
completar evidence/status de la tarea solo si todo pasa. Tarea in_progress.

## 2026-11-04 1x:xx — Claude Code (Opus 5.5) — F6-DOMO: final ganada con PB, exclusión inversa, Fábrica sin regresión; hecha
Estado: hecho
Hecho:
- **Relevo revisado**: árbol limpio tras Codex (`f5f3b65`), solo los cinco archivos ajenos sin seguimiento; el código del
  Domo no cambió desde `2326b25` (solo el supervisor). Nada a medias.
- Azahar (build repetida): desde `dc_paused3.sav`, final ganada; `df_paused6.sav` con racha/activo/récord 6/1/6, PB 0 → 1
  (solo la final), Mansión 20/20. Salida a (6,57). Torre se niega con el Domo pausado; Domo se niega con la Fábrica
  pausada; la Fábrica reanuda por su warp 2 y combate con alquileres (GDB: rama de alquileres con 3, rival de 3).
  Detalle y hashes en `reports/frontier.md` §26.
Evidencia: capturas `work/frontier/lab/df_*`; `df_paused6.sav` `959b7fa8…`; `python -m pytest -q tests` → 296 passed
(`work/frontier/dome/tests-final.log`).
Commits: el de esta entrada (tarea F6-DOMO `done` en `frontier/orch/tasks.json`).
Decisiones: la línea del campeón no se fotografió (pulsaciones de más); se da por buena la rama por el PB del guardado.
Sin probar: consola; jefe de la Mansión en la racha del Domo; reinicio sin guardar en 456.
**Estado del laboratorio**: parado; `use_gdbstub` en `false`.
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json` (F6-PALACIO-A, Claude).

## 2026-11-04 1x:xx — Claude Code (Opus 5.5) — F6-PALACIO-A: Palacio etapa A en código (frontier-orch)
Estado: en curso
Hecho:
- **Zona 340 comprobada sin emulador** (`python frontier/zone_check.py 340` → `work/frontier/palace/zone_check.txt`;
  contexto con `work/frontier/palace/ctx.py` y `ctx2.py`): máscara 0x243, sin warps de entrada; sus cinco literales
  en scripts no son zonas: compartido 57 `0xd10` (tabla de `@77c`, objeto y flags, como el 329), zonas 214/244/316
  (argumento de rutinas que empiezan por `MdlAcmdInit`, animación de modelo) y zona 444 `0x23bc` (`@30`: `FlagSet`
  1740 + N, un entrenador). Palabras alineadas = 340: 58 (209: 48, 213: 45).
- **`frontier/tower.py` generalizado**: `reception_routine`, `battle_points` y `facility_program(retail, facility)`
  toman la instalación (ruta, works y PB de `patch`/`data`, etiquetas con su nombre); `tower_program` llama a
  `facility_program(retail, 'tower')`. El script de la Torre sale **idéntico byte a byte** al de `HEAD` (comparado
  con el módulo anterior, 15.040 bytes).
- **`frontier/palace.py`**: zona 340, ruta 3, works 16461/16462/16463, PB de `FRONTIER_BP['palace']`; el flujo de la
  Torre (pantalla de modalidad y de equipo de la Mansión, `SetRank(0)`, racha nueva a 0, pausa, derrota y limpieza).
  El jugador sigue dando las órdenes (etapa A).
- **Integración**: `island_build.ZONE_PALACE = 340` en `CLONES`, `KEEP_TEXT` y `DOORS['Palace']` (warp 3 de la isla,
  último en `FACILITIES`; Torre 0, Domo 1 y Fábrica 2 no cambian); `overlay.facility_scripts()` añade el 340. La
  exclusión ya cubría el 16462 en todas las recepciones (`factory.busy_check` recorre `patch.ACTIVE_WORK`).
Evidencia: `python -m pytest -q tests` → 326 passed (30 nuevos en `tests/test_frontier_palace.py`, tests de isla
ampliados). Rotura a mano: construir el Palacio con la instalación `tower` → 25 de 30 fallan. **No probado en Azahar
todavía.**
Commits: el de esta entrada.
Decisiones: se reutiliza la pantalla de modalidad aunque el diseño proponía saltarla: la Torre midió que sin ella el
selector rechaza a todos (§25). Sin línea de texto «Palacio Batalla» (la Torre tampoco la tiene; desviación conocida).
Siguiente paso: build (`python frontier/overlay.py --out work/frontier/build --romfs work/faraway/dev/overlay/romfs`)
y en Azahar: puerta (31,69) → 340 → (31,70); guardar/cargar en 340; ronda de 7 con PB 4; pausa, reanudación,
derrota; rechazos cruzados; Fábrica/Torre sin regresión.

## 2026-11-04 11:5x — Claude Code (Opus 5.5) — F6-PALACIO-A: Palacio etapa A probado en Azahar; hecha
Estado: hecho
Hecho:
- Build completa (`work/frontier/palace/build.log`): 340 clonada de 517 con área 235, texto 619, lugar 279.
- Azahar (detalle, capturas y hashes en `reports/frontier.md` §27): puerta (31,69) → 340 → salida (31,70); menú sin
  Fábrica; modalidad y 3 Pokémon propios; guardado en 340 con ruta 3; victorias 1–2 desde cero y pausa 2/1/2 sin PB;
  desde la racha 6 editada, combate 7 con «4 PB» y pausa 7/1/7 (PB 4); reanudación y derrota en el 8: 0/0/7. Mansión a
  cero y Torre/Fábrica/Domo sin tocar en todas las partidas. Exclusión: la Fábrica se niega con el Palacio pausado; el
  Palacio se niega con la Torre pausada; la Torre, en la misma build, reanuda leyendo su racha (ruta 2).
- REPARTO: fila del Palacio actualizada. `frontier/orch/tasks.json`: F6-PALACIO-A `done` con su evidencia.
Evidencia: partidas `work/frontier/lab/pa_*.sav` (`save-evidence.jsonl`), capturas `work/frontier/lab/pa_*.png` y
`work/frontier/palace/r7/`, `loss/`; registros `work/frontier/palace/lab1.log`–`lab3.log`; `python -m pytest -q tests`
→ 326 passed (`work/frontier/palace/tests-final.log`).
Commits: 5473973 (código) y el de esta entrada.
Decisiones: las pruebas siguen el patrón de la Torre (racha editada para llegar al 7.º combate). El texto sigue siendo
el de la Mansión («Mansión Batalla»); una línea propia del Palacio queda para cuando haya textos por instalación.
Sin probar: consola; ronda de 7 entera desde cero; jefe de la Mansión en la racha del Palacio; reinicio sin guardar en
340; el Domo rechazando con el Palacio pausado en el juego (sí en la suite).
**Estado del laboratorio**: parado; `use_gdbstub` en `false`.
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json` (F6-TUBO, Codex). Para la Arena etapa A (Claude):
`tower.facility_program(retail, 'arena')` con su zona (457, verificar con `zone_check.py`) y su puerta (20,69); las
etapas B (motor) de Palacio y Arena, cuando se creen como tareas, empiezan por las mediciones M1–M4 de `palacio.md` §4.

## 2026-11-04 15:xx — Claude Code (Opus 5.5) — F6-TUBO: medidas y plan (frontier-orch; relevo de mi propia sesión cortada)
Estado: en curso
Hecho:
- **Relevo**: la sesión anterior (Claude) se cortó por límite de uso sin cambios en el árbol (solo `tasks.json` en
  `in_progress`, del orquestador, y los cinco archivos ajenos sin seguimiento). Solo había medido; lo recojo aquí.
- **Medido en `code.bin` (Repolished; `frontier/disasm_code.py`, `work/frontier/pike/getparam.py`)**:
  - `StartBattle` → `0x1e30b8`: crea el `PokeParty` temporal (r5), lo rellena con `bl 0x1e3d2c` en **`0x1e3110`**
    (`r3` = el party) y después el montaje Individual `0x1e0634` lo **copia** (`0x3b6428`) en el parámetro de combate:
    `work+0x620+0x4c` = equipo del jugador, `+0x50` = rival. El temporal se destruye en `0x1e32c8`.
  - `PokeParty`: punteros a miembros en `+0`…`+0x14`, número (u8) en `+0x18` (`0x3b5d34`, `0x3b6150`).
  - `0x3b5d34` (`PARTY_PREPARE` de `rental.s`) es **`PokePartyRecoverAll`** (nativa `DllField.cro 0x4f868`): la
    Mansión cura el equipo real antes de copiarlo. Por miembro, `0x139c00` (RecoverAll) sobre `core = [param+0xc]`.
  - Accesores del bloque de combate (`[core+4]`; descifrado `0x168ec0`, cifrado `0x168e50`): `GET_HP 0x153174`
    (+8), `GET_MAX_HP 0x153254` (+0xa), `SET_HP 0x14f450(core, hp)`, `SET_SICK 0x14f814(core, v)` (+0, u32),
    `GET_SICK 0x4d22e4` (+0). Corresponde al PK6 +0xE8 (estado), +0xF0 (PS), +0xF2 (PS máx.).
  - `PokePartySetParam` no tiene PS ni estado (solo IV, amistad, EV…): hacen falta ganchos ARM.
  - `IsWin` = `0x1e5664` (`ldrb r0,[r0,#0x73c]`, 4 instrucciones, hoja).
- **Zona**: 379 descartada (la zona 159 la empuja antes de un cambio de mapa, `0xb08`); 341–350 tienen warps de
  entrada (zonas 19/20). **458**: sin warps de entrada, 0 operandos en scripts, máscara 0x243
  (`work/frontier/pike/zone_check.txt`).
Decisiones (plan de la v1, desviaciones del diseño a documentar):
- **Una sola zona, clon de 517 (458)**, como Torre/Palacio, en vez de vestíbulo + sala clonados de 397: las salas son
  un bucle de script antes de cada combate con menú de 3 puertas (izquierda, centro, derecha) y una pista con su
  posición. Evita la geometría nueva, los disparadores y el cambio de mapa a la misma zona (riesgos del diseño §6).
- Equipo: pantalla de modalidad + selección de la Mansión (flujo de la Torre); ruta 6.
- Ganchos: H1 sustituye el `bl 0x1e3d2c` de `0x1e3110`: tras montar el temporal, con la ruta 6 aplica PS (0xFFFF =
  lleno, tope PS máx.) y estado guardados por posición. H2 en `IsWin`: con la ruta 6 copia PS y estado de
  `[work+0x66c]` a los works (**hipótesis por medir con gdb**: que ese equipo siga vivo y con el daño al leer
  `IsWin`, y la codificación del estado).
- Works propuestos: PS 16661–16663, estado 16669–16671, racha para el hijo 16673, generador 16674; texto 637 desde
  la línea 1014; GlobalCall 9776.
- Combate duro = `SetRank(1)` para ese combate (Súper), `SetRank(0)` tras `StartBattle`; la sala 14 siempre es combate
  (así el PB va por la rutina de la Mansión, 14 salas por ronda).
Evidencia: comandos y salidas arriba; nada ejecutado en Azahar.
Commits: el de esta entrada.
Siguiente paso: `frontier/pike.py` + `frontier/asm/pike.s` + tests; luego gdb (H2 y estado) en Azahar.
