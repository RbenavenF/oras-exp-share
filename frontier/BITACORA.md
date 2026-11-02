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
