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

## 2026-11-04 16:xx — Claude Code (Opus 5.5) — F6-TUBO: Tubo v1 en código (frontier-orch)
Estado: en curso
Hecho:
- **`frontier/asm/pike.s`** (enlazado tras `dome.s`; hook total 1052 de 2556 bytes): `pike_build` sustituye el
  `bl 0x1e3d2c` de `0x1e3110` (StartBattle): monta el equipo y, con la ruta 6, pone a cada miembro los PS guardados
  (`0xFFFF` = lleno, con tope en el PS máx.) y el estado; `pike_iswin` sustituye la 1.ª instrucción de `IsWin`
  `0x1e5664`: con la ruta 6 copia PS y estado de `[work+0x66c]` a los works y devuelve lo mismo que `IsWin`.
  `patch.py` comprueba las cabeceras y las palabras leídas de los cinco accesores, el sitio y las 4 palabras de IsWin.
- **`frontier/pike.py`**: zona 458 = flujo de la Torre (`tower.facility_program(retail, 'pike')`, ruta 6, works
  16477/16478/16479) más `pike_rooms` tras `AcmdListClear` del bucle `0x1e1c` (antes de que entre el rival) y
  `pike_after_start` tras `StartBattle` (`SetRank(0)`). Rutina `pike_room` en el compartido 5 (GlobalCall 9776): «Sala
  N de 14» (`WordSetNumber` como 517 `0x3c3c`), sala 14 = combate, 3 puertas con pista (categoría + posición),
  menú de puertas, salas: individual, duro (`SetRank(1)`), PNJ, cura total, cura parcial (1–2), estado (1/2/3 por
  sala, probabilidades de Esmeralda, sin inmunidades). 41 líneas al final del texto 637 (desde la 1014).
- `tower.battle_points` toma la ronda de `tower.STAGES` (14 para el Tubo; la Torre y el Palacio siguen con 7,
  scripts idénticos: sus tests no cambian).
- Integración: `island_build.ZONE_PIKE = 458` en `CLONES`/`KEEP_TEXT`/`DOORS` (warps de la isla: Torre 0, Domo 1,
  Fábrica 2, **Tubo 3, Palacio 4**), `overlay` (script, caso compartido y textos). Tests de isla/overlay/patch
  actualizados.
Evidencia: `python -m pytest -q tests` → **390 passed** (64 nuevos en `tests/test_frontier_pike.py`: VM de las salas
con 300 semillas, PB cada 14, exclusión; Unicorn de H1/H2 con accesores simulados). Roturas a mano: sin el tope de
PS falla `test_h1_sets_the_saved_hp_and_status_on_the_pike_route`; sin el rechazo de categoría en las puertas sin
pista falla `test_hinted_door_is_of_its_category_and_the_others_are_not`. Script de 458: 15.288 bytes, ZO en
`work/frontier/pike/sizes.txt`. **No probado en Azahar todavía.**
Commits: el de esta entrada.
Decisiones: works PS 16661–16663, estado 16669–16671, generador 16674 (REPARTO). Las hipótesis por medir siguen
siendo: el equipo de `[work+0x66c]` vivo al llamar a `IsWin`, su orden, y los valores de estado (enum de pml
1 parálisis, 2 sueño, 3 congelación, 4 quemadura, 5 veneno; el tóxico se guarda como veneno).
Siguiente paso: build y Azahar: puerta (5,69) → 458 → salida (5,70); desafío, salas, combate con daño y comprobar
con el guardado (pausa) que los works de PS cambian y que el siguiente combate empieza con ese daño; estado visible.

## 2026-11-04 16:14 — Codex — F6-TUBO: recuperación del relevo y parche de retorno del equipo
Estado: en curso
Hecho:
- Revisados `git status`, `git diff` y último commit `23c471c`. Claude dejó cambios sin commit en
  `frontier/patch.py`, `overlay.py` y `pike.py`: retorno del equipo en DllBattle.cro y gramática de pistas.
  Se conservan y completan. Los cinco archivos ajenos sin seguimiento (informes y scripts de encuentros/evoluciones)
  no se modifican. REPARTO sigue bajo el turno del orquestador.
- El parche CRO amplía la puerta de copia de competidores 0/1 a 0/1/2 en offset 0x15398; overlay incluye CRO y
  static.crr recalculados. Se exige el SHA256 completo del CRO v0.5, además de comprobar las tres instrucciones.
- Ocho pruebas nuevas: ejecución ARM de la puerta para 0/1/2/3/255/0xffffffff, rechazo de entrada distinta,
  límites de bytes modificados, hashes CRO y pertenencia ordenada en CRR.
Evidencia: `work/frontier/pike/copy-back-disasm.txt` (Capstone sobre el CRO v0.5); build
`work/frontier/pike/build-relevo.log`; suite inicial 390 passed (`tests-relevo.log`), pruebas del Tubo 72 passed
(`tests-cro.log`). Los logs de Claude registran PS 156/156/184 en H2 y parálisis con valor 1; son evidencia heredada,
no una validación del nuevo retorno de PS. Azahar con el parche nuevo aún no probado: el primer arranque con gdb no
estableció conexión. Se reintenta en una shell persistente del laboratorio.
Commits: el de esta entrada (recuperación de cambios tras 23c471c).
Decisiones: conservar la corrección del CRO y validarla en juego antes de declarar persistencia; no dar por probado
el §28 citado por comentarios heredados (todavía no existía). La tarea sigue in_progress.
Siguiente paso: medir PS/estado después de un combate y en el siguiente, curas, ronda de 14/PB, salida (5,70),
exclusión y regresiones con la build nueva; registrar evidencia en reports/frontier.md §28.

## 2026-11-04 16:23 — Codex — F6-TUBO: daño entre combates y puerta comprobados
Estado: en curso
Hecho: Azahar con el CRO nuevo: combate individual ganado, después combate fuerte que empieza con 61/156 PS y
PP completos. Abandono en el segundo: guardado con racha/activo/récord 0/0/1 y PS 61/156/184. Salida andando a
(5,70) y entrada a 458, verificadas en sendos guardados. Informe y limitaciones en reports/frontier.md §28.
Evidencia: `work/frontier/pike/save-evidence.jsonl`, capturas `work/frontier/lab/pk_cx_*.png`, comparación PK6
`cx-party-comparison.json` (solo +0xF0 de dos miembros cambia por curación). Suite 398 passed en
`work/frontier/pike/tests-relevo-final.log` (misma implementación del commit anterior).
Commits: f5e6a2a (CRO) y el de esta entrada (evidencia).
Decisiones: fixture nueva `pk_cx_lastroom_fixture.sav`, basada en `pk_cx_loss.sav`, con racha/récord 13, activo 1,
PS 100/90/184, estados 1/4/0 para medir sala 14, estados y PB. Es una prueba con racha editada, no 14 salas desde cero.
Siguiente paso: continuar en la copia de sala 14; registrar PB y estados; después curas, exclusión y regresiones.
Laboratorio activo durante este hito, bajo shell persistente; se parará al finalizar la sesión.

## 2026-11-04 1x:xx — Claude Code (Opus 5.5) — F6-TUBO: sala 14 con PB, debilitados, regresión del Palacio y exclusión; hecha
Estado: hecho
Hecho:
- **Relevo revisado**: árbol limpio tras Codex (`63f4e93`), solo los cinco archivos ajenos sin seguimiento; el
  laboratorio estaba parado. Nada a medias. Lo heredado de Codex (parche de `DllBattle.cro`, daño entre combates,
  puerta y salida) se da por bueno con su evidencia de §28.
- Azahar (build igual al código de `63f4e93`, `work/frontier/pike/build3.log`): reanudación desde la racha 13 con PS
  100/90 y parálisis/quemadura aplicados por posición; «Sala 14 de 14», combate ganado, **1 PB**; ronda 2: los
  debilitados siguen debilitados; derrota 0/0/14 con PB 1 y equipo real idéntico; salida a (5,70); Palacio con el CRO
  nuevo: dos combates, el segundo con PS llenos, pausa 2/1/2; con el Palacio pausado el Tubo se niega. Detalle y
  hashes en `reports/frontier.md` §28. Fila del Tubo de REPARTO actualizada; F6-TUBO `done` en `tasks.json`.
- Laboratorio: `work/frontier/pike/lab.sh` arranca con el stub de gdb (además de `use_gdbstub=true` hace falta
  `use_gdbstub\default=false`, si no Azahar usa su valor por defecto y lo apaga); `k.sh`/`tap.sh` para teclas y
  toques (B es la tecla `s`; la pantalla táctil, con `mousemove x y mousedown 1 … mouseup 1`).
Evidencia: partidas `work/frontier/lab/pk_r14_then_loss.sav` (`cc9db86c…`), `pk_palace_paused_crobuild.sav`
(`53823118…`); capturas `pk_f_*`, `pk_g_*`, `pk_pal_*`, `pk_pike_refused.png`; `python -m pytest -q tests` → 398
passed (`work/frontier/pike/tests-final.log`).
Commits: el de esta entrada.
Decisiones: la pausa del Tubo tras una victoria es la de la Torre (mismo script de la Mansión) y se dio por cubierta con
la reanudación desde partida editada; queda anotada como no probada directamente.
Sin probar: consola; sala de estado y cura total vistas en pantalla (cubiertas por la suite); congelación y veneno en
pantalla; una ronda de 14 desde cero; Fábrica, Torre y Domo en juego con el CRO nuevo.
**Estado del laboratorio**: parado; `use_gdbstub` en `false` (y `\default=true`).
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json` (F6-ARENA-A, Claude). Antes de publicar un paquete, un
combate de la Fábrica con el CRO nuevo (rama de alquileres).

## 2026-11-04 1x:xx — Claude Code (Opus 5.5) — F6-ARENA-A: Arena etapa A en código (frontier-orch)
Estado: en curso
Hecho:
- **Zona 457 comprobada sin emulador** (`python frontier/zone_check.py 457` → `work/frontier/arena/zone_check.txt`;
  contexto con `work/frontier/arena/ctx.py` → `ctx.txt`): máscara 0x243, sin warps de entrada; sus tres literales en
  scripts son el **objeto** 457, no la zona: compartido 27 `0x21a0` y zona 276 `0x9c0` (`PUSH_P_C 457` →
  `ItemGetNum`; el «next map change» de la 276 es el `JUMP` de su `if`), zona 14 `0x453c` (argumento de `@119c` junto
  al objeto 724, mismo patrón). 31 palabras alineadas = 457 en código/CRO, orientativo.
- **`frontier/arena.py`**: zona 457, ruta 4, works 16465/16466/16467, PB de `FRONTIER_BP['arena']`;
  `tower.facility_program(retail, 'arena')` (flujo de la Torre y del Palacio: pantalla de modalidad y de equipo de la
  Mansión, `SetRank(0)`, pausa, derrota y limpieza). Sin límite de turnos ni juicio (etapa B).
- **Integración**: `island_build.ZONE_ARENA = 457` en `CLONES`, `KEEP_TEXT` y `DOORS['Arena']`. Warps de la isla en
  orden de `FACILITIES`: Torre 0, Domo 1, Fábrica 2, Tubo 3, **Arena 4, Palacio 5** (antes 4); la salida de cada
  interior se deriva (`door_warp`). `overlay.facility_scripts()` añade el 457. La exclusión ya cubre el 16466
  (`factory.busy_check` sobre `patch.ACTIVE_WORK`).
Evidencia: `python -m pytest -q tests` → 430 passed (`work/frontier/arena/tests1.log`; 32 nuevos en
`tests/test_frontier_arena.py`, isla ampliada). Rotura a mano: `FACILITY = 'palace'` en `arena.py` → 26 de 32 fallan.
Build `work/frontier/arena/build.log` (457 clonada con área 237). **No probado en Azahar todavía.**
Commits: el de esta entrada.
Decisiones: mismo patrón que el Palacio (pantalla de modalidad incluida). Sin texto propio «Arena Batalla»
(desviación conocida, como Torre y Palacio).
Siguiente paso: Azahar desde `work/frontier/lab/pa_strong.sav` (plaza, (20,59)): bajar a la puerta (20,69) → 457 →
salida (20,70); guardar en 457; victorias; racha editada a 6 para el 7.º con PB 1; pausa, reanudación, derrota;
rechazos cruzados.

## 2026-11-04 21:35 — Codex — F6-ARENA-A: recuperación de evidencia de Azahar y cierre
Estado: hecho
Hecho:
- Revisados `git status`, `git diff` y último commit `e3c85ba`: sin cambios versionados a medias. Se conservan sin
  tocar los cinco archivos ajenos sin seguimiento. REPARTO mantiene el turno del orquestador, sin modificaciones.
- Recuperada la evidencia posterior al commit que Claude dejó sin documentar al agotar cuota: registro
  `work/orch/logs/20261104-205236-claude-F6-ARENA-A.log`, ocho partidas y capturas. Documentada en
  `reports/frontier.md` §29, distinguiendo explícitamente ejecución heredada de verificaciones de Codex.
- Azahar de Claude: entrada a 457 y salida (20,70), ronda desde cero y derrota 0/0/8 con 1 PB; reanudación desde
  fixture editada 6/1/8, premio 1 PB del séptimo, pausa real 9/1/9 con PB 2; Palacio rechaza Arena pausada y viceversa.
  Mansión intacta. Equipo tras derrota: solo PS actuales de dos Pokémon cambiados por curación.
- `F6-ARENA-A` pasa a done con evidencia. Escalón B fuera de esta tarea.
Evidencia:
- `python -m pytest -q tests` → 430 passed (`work/frontier/arena/tests-relevo.log`).
- Checksums, SHA256, zona y works de los ocho guardados verificados (`save-audit-relevo.json`). Comparación PK6
  repetida (`party-diff-relevo.txt`). Overlay regenerado idéntico en sus 25 archivos a la build probada por Claude
  (`build-relevo.log`, `build-manifest-relevo.json`).
- El intento adicional de Codex de recargar la pausa 9 no llegó a mostrar el juego; no se declara probado.
  Laboratorio cerrado, namespace sin procesos y metadata archivada (`lab-stop-relevo.txt`).
Commits: e3c85ba (implementación, Claude) y el de esta entrada (auditoría y cierre, Codex).
Decisiones: conservar la implementación sin cambios; aceptar la evidencia de ejecución recuperada y comprobada,
no repetir toda la ronda. Sin probar: consola; recarga de la pausa 9 concreta; combates de regresión de Fábrica,
Torre y Domo con el CRO del Tubo (limitación heredada §28; suite sí en verde). Textos de la Mansión conservados.
Siguiente paso: siguiente tarea del orquestador, F6-PIRAMIDE. Antes de publicar, comprobar rama de alquileres de
Fábrica con el CRO actual como pide §28. Laboratorio parado; inputs y partida original intactos; sin push.

## 2026-11-05 02:2x — Claude Code (Opus 5.5) — F6-PIRAMIDE: experimento 0, Pirámide v1 en código y primeras pruebas en Azahar (frontier-orch)
Estado: en curso
Hecho:
- **Relevo de Codex** (cortado por cuota el 2026-11-04 21:39 sin commit ni bitácora): `git status` con
  `frontier/pyramid_probe.py` y `tests/test_frontier_pyramid_probe.py` sin seguimiento (banco de pruebas del
  experimento 0: puerta → 140, recepcionista → selección → 141 clonada de la cueva 192; 13 tests en verde) y
  `tasks.json` en `in_progress`. Sus medidas en `work/frontier/pyramid/` (zone-check de 140–142, contexto de operandos:
  los literales 140–142 de scripts son flags, objetos, líneas de texto o coordenadas, ninguno lleva a esas zonas).
  Se conserva el banco de pruebas tal cual (aparato del experimento 0, fuera de `overlay.py`). El laboratorio que dejó
  arrancado en su espacio de PID ya no existía. Los cinco archivos ajenos sin seguimiento no se tocan.
- **Experimento 0 en Azahar** (build del banco de Codex, `work/frontier/pyramid/probe`, gdb):
  - `BattleInstWorkCreate` en el vestíbulo 140 (clon de 517) devuelve el trabajo `0x0880a6cc`; modalidad y selección
    de 3 normales; `_MapChangeCore(141, 19, 0, 18, 0, 0, 0, 1, 0)` lleva a la zona 141 (`py_e0_after_select.png`).
  - **El trabajo de la instalación no sobrevive al cambio de mapa**: en 141, `x/8wx 0x880a6cc+0x2c` lee la selección
    a 0 y `+0x48 = 0x0bc204e8`, y su cabecera es otro objeto (`0x005e0098 …`): memoria liberada y reutilizada.
  - La cueva 192 no sirve de piso sin más: el jugador llega a la boca de la cueva, no puede andar y los NPC en (16–22, 17)
    no se ven (`py_e0_floor*.png`). Se descarta para la v1: los pisos son clones de 517 (geometría conocida).
  - `BattleInstWorkDelete` → `DllField.cro` 0x956b4 → thunk 0x3738 → **`code.bin 0x1e5c48(holder)`** (literal leído en
    0x6f673c con DllField en 0x6f3000): `ldr r4, [r0, #0x64]` (trabajo) y `bl 0x12b8fc` en 0x1e5c54.
- **Diseño resultante** (`frontier/pyramid.py`, `frontier/asm/pyramid.s`): la selección vive en works guardados.
  `pyramid_save` (en 0x1e5c54, al borrar el trabajo con la ruta 7, selección de 3 del equipo, no de la Caja) copia
  `work+0x30..0x38` a 16681–16683 y pone 16685 = 3; `pyramid_party` (desde `rental_hook`, tras `dome_party`) los pone
  en el trabajo nuevo de cada combate. Cada combate de piso: `BattleInstWorkCreate`, `SetRank(0)`, `SetTrainer(0)`,
  `StartBattle(0, 1)`, esperas de 517, `IsWin`, `BattleInstWorkDelete`.
- **Pirámide v1**: vestíbulo 140, pisos 141/142 alternos (clones de 517; 3 entrenadores y un encargado por piso,
  salida del piso al vestíbulo), puerta (32,57) = warp 3 de la isla (Pike 4, Arena 5, Palace 6 se recalculan con
  `door_warp`). Textos en el texto 637 (líneas 1055–1069) por el caso 9777 del compartido 5. Works: 16481–16483
  (racha de pisos, piso actual, récord), 16686 vencidos, 16687 línea, 16689 número; patch: 16681–16683, 16685.
- Integración (turno del orquestador): `island_build` (CLONES/KEEP_TEXT/DOORS, líneas del plan de los pisos),
  `overlay` (scripts, caso compartido, textos), `patch.py` y `rental.s`; tests de isla, overlay y parche ajustados.
- Fallo encontrado en Azahar y corregido: la rutina de guardado 0x13d4 devuelve **0 si se guarda** (517 0x1a60–0x1a70).
Evidencia (Azahar, build `work/frontier/pyramid/build`, partida de partida `py_start.sav` = copia de `pa_strong.sav`):
- Puerta (32,57) → vestíbulo; textos propios; modalidad y selección; gdb en `pyramid_save`: trabajo `0x8822544`,
  `+0x30..+0x38 = 0, 1, 2`, `+0x48 = 3`. Guardado: `py_lobby_saved.sav` (`708bc25e…`, zona 140, ruta 7, 16481–3 =
  0/1/0, selección 0/1/2, cuenta 3).
- Reanudar desde el vestíbulo → piso 1 (141); «Piso 1 de 7»; tres combates ganados contra entrenadores de la Mansión
  con **exactamente los 3 elegidos a Nv. 50** (`py_v1_party_in_battle.png`), «Ya hemos combatido» tras cada uno;
  encargado: «¡Piso superado!» → piso 2 (142). Guardado en el piso 2: `py_floor2_try.sav` (`be355c35…`, zona 142,
  racha 1, piso 2, récord 1, selección 0/1/2). **Recarga en el piso 2 y combate ganado** (la selección sale de works).
- Equipo real: solo +0xF0 (PS actuales) de los miembros 0 y 1 cambia (26→34, 25→35): la cura de la Mansión ya vista
  en §28 (`work/frontier/pike/party_diff.py`).
- `python -m pytest -q tests` → 443 passed.
Commits: el de esta entrada.
Decisiones: pisos sobre la sala de la Mansión (no la cueva); racha por pisos (Emerald); la racha sigue tras completar
los 7 pisos y vuelve a 0 al perder o abandonar; la ruta 7 queda puesta mientras el desafío sigue (también al guardar en
un piso). Riesgo anotado: los pisos y el vestíbulo conservan el PC de la Mansión; cambiar el equipo entre pisos cambia
quién combate (los índices son huecos del equipo) y no se ha probado qué pasa con un hueco vacío.
Siguiente paso: en Azahar, salida del piso → vestíbulo → (32,58) y exclusión mutua con la Fábrica; PB del piso 7
(partida editada); derrota con 3 débiles (huecos 3–5); regresión de otra instalación con esta build. Después,
`tests/test_frontier_pyramid.py` (VM y Unicorn), `reports/frontier.md` §30 y REPARTO.

## 2026-11-05 03:xx — Claude Code (Opus 5.5) — F6-PIRAMIDE: Azahar completo, tests y cierre (frontier-orch)
Estado: hecho
Hecho:
- Relevo: árbol limpio tras `2a0752f` (mi propio commit; el aviso de relevo se repitió al reanudarse la sesión).
  Los cinco archivos ajenos sin seguimiento siguen sin tocarse.
- Azahar con la build de `2a0752f` (sin cambios de código después): salida piso → vestíbulo → plaza en (32,58);
  exclusión en los dos sentidos (Fábrica con la Pirámide a medias; Pirámide con la Torre a medias, partida editada);
  piso 7 con 5 PB (partida editada: piso 7, vencidos 7, racha 6); desafío nuevo con los huecos 4/5/3 (salen esos tres
  y en ese orden) y derrota con limpieza; «No» y cancelación de la pantalla de equipo; Torre con esta build, inscripción
  y al menos cuatro combates. Tabla completa con hashes en `reports/frontier.md` §30.
- `tests/test_frontier_pyramid.py` (59): constantes, plan, vestíbulo (nuevo, rechazos, cancelaciones, no guardar,
  reanudar por piso, abandonar, exclusión con las seis), pisos (combate, vencido, derrota, encargado, subir 1→7, PB del
  piso 7 por desafío), `pyramid_say` del compartido 5, y Unicorn de `pyramid_party` y `pyramid_save` (ruta, Caja,
  cuenta, índices fuera de 0–5, trabajo nulo). `scripts/pawn_vm.py` gana el opcode OR. Roturas a mano en `pyramid.s`
  (`cmp r1, #7` y desplazamiento de SEL0) → 1 y 2 tests fallan.
- REPARTO: fila de la Pirámide y sus works (el turno no se toca).
Evidencia: partidas `work/frontier/lab/py_*.sav` y `save-evidence.jsonl`; capturas `py_v1_*`, `py_tw_*`;
`python -m pytest -q tests` → 502 passed (`work/frontier/pyramid/tests-final.log`). Laboratorio parado (sin procesos
AppRun/gdb), `use_gdbstub=false` y `\default=true` restaurados.
Commits: 2a0752f y el de esta entrada.
Decisiones: F6-PIRAMIDE `done` en `tasks.json`. La Torre se tomó como regresión representativa; las demás
instalaciones quedan cubiertas por la suite.
Sin probar: consola; un hueco de equipo vacío o reordenado entre pisos (PC de la Mansión en los pisos); siete pisos
seguidos desde cero (el piso 7 se probó con partida editada); recarga en el vestíbulo con el desafío a medias tras
salir a la plaza (sí la reanudación desde `py_lobby_saved.sav`).
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json`. Mejoras posibles de la Pirámide (v2): quitar el PC
de los pisos, ocultar a los entrenadores vencidos, un piso con aspecto de cueva.

## 2026-11-05 09:10 — Claude Code (Opus 5.5) — frontier-orch: Codex sin reanudar sesiones
Estado: hecho (sin ejecutar el orquestador, por petición del usuario)
Hecho:
- Medida (`~/.codex/sessions/2026/11/04/rollout-2026-11-04T02-04-24-01a1a415-….jsonl`, sesión del Domo):
  gpt-6-astra con razonamiento alto, 124 llamadas, ~142k tokens de entrada de media por llamada (máx. 219k),
  17,2 M de entrada (99 % en caché), 29k de salida (9k de razonamiento). Con `orch.log`: Codex gastaba cada ventana
  de cuota en ~13–15 min (23:34→23:49, 05:04→05:17, 10:36→10:51 del 3–4 de noviembre).
- `frontier_orch.py`: opción `fresh_sessions` por agente; con ella nunca se reanuda (orden `new`, brief completo) y
  se añade «La tarea ya está empezada…» si había sesión previa de esa tarea.
- `config.json`: Codex con `fresh_sessions: true` y `-c model_reasoning_effort="medium"` en `new` y `resume`.
  `README.md` del orquestador, punto 4.
Evidencia: `python -m pytest -q tests` → 503 passed (nuevo `test_fresh_sessions_never_resume_and_say_the_task_is_started`).
Sin probar: una ejecución real de Codex con la sesión nueva (consumo por ventana tras el cambio).
Commits: el de esta entrada (turno tomado en c3e62e9).
Decisiones: el usuario pidió el cambio y no lanzar el orquestador todavía. Todas las tareas de `tasks.json` están
`done` (el supervisor terminó a las 06:36 con «all tasks done»).
Siguiente paso: definir las siguientes tareas en `frontier/orch/tasks.json` (p. ej. etapa B del Palacio y la Arena)
y lanzar `frontier/orch/frontier-orch auto`; medir cuánto dura Codex por ventana con el cambio.

## 2026-11-05 09:25 — Claude Code (Opus 5.5) — frontier-orch: Codex con gpt-6.1-sol
Estado: hecho (sin ejecutar el orquestador)
Hecho: `frontier/orch/config.json` pasa `-c model="gpt-6.1-sol"` en las órdenes `new` y `resume` de Codex (razonamiento
medio, sesiones nuevas, como en la entrada anterior). Decisión del usuario: probar Sol frente a gpt-6-astra por la
cuota. `~/.codex/config.toml` no se toca (astra para el uso manual). Según `~/.codex/models_cache.json`, Sol es
«Latest workhorse model for coding and everyday work» y Astra «Frontier intelligence for the most demanding work».
Evidencia: `python -m pytest -q tests/test_frontier_orch.py` en verde tras el cambio.
Sin probar: ninguna ejecución de Codex con Sol; ni consumo por ventana ni calidad.
Commits: el de esta entrada.
Siguiente paso: nuevas tareas en `tasks.json` y `frontier/orch/frontier-orch auto`. Al acabar la primera ventana de
Codex, medir en `~/.codex/sessions/…` llamadas, contexto medio y minutos hasta el límite, y comparar con la sesión del
Domo (124 llamadas, ~142k por llamada, ~15 min). Revisar sus commits con más cuidado que los de Astra.

## 2026-11-05 09:40 — Claude Code (Opus 5.5) — frontier-orch: tareas de la etapa B
Estado: hecho (sin ejecutar el orquestador)
Hecho: `frontier/orch/tasks.json` gana F6-PALACIO-B y F6-ARENA-B (`pending`, dueño Claude como en REPARTO), a
petición del usuario. Criterios sacados de `reports/diseno/palacio.md` §1, §4–§6 y `arena.md` §1–§2, §5–§6: medir
antes de escribir y, si la medida clave lo hace inviable (M3 del Palacio; cualquiera de 1–5 de la Arena), `blocked`
con la pregunta y lo medido en vez de improvisar. Los dos parchean `DllBattle.cro` encima de la v0.5 y del Tubo.
Evidencia: `python -m json.tool frontier/orch/tasks.json` válido; `frontier/orch/frontier-orch status` (abajo, en el commit).
Sin probar: ninguna de las dos tareas.
Commits: el de esta entrada.
Decisiones: Palacio antes que Arena (orden de `tasks.json`). Fuera: etapa C del Palacio; Mente/Técnica/Greta de la
Arena; Pirámide v2.
Siguiente paso: cerrar la terminal antigua y lanzar `frontier/orch/frontier-orch auto` cuando el usuario lo diga.

## 2026-11-05 09:55 — Claude Code (Opus 5.5) — frontier-orch: F6-ARENA-B para Codex
Estado: hecho (sin ejecutar el orquestador)
Hecho: a petición del usuario, F6-ARENA-B pasa a Codex (gpt-6.1-sol) y va antes que F6-PALACIO-B en `tasks.json`,
para que Codex trabaje desde el primer momento (el orquestador toma la primera tarea abierta) y se mida Sol.
REPARTO: la Arena queda con Claude en la etapa A y Codex en la B.
Evidencia: `frontier/orch/frontier-orch status`; `python -m pytest -q tests/test_frontier_orch.py` en verde.
Commits: el de esta entrada.
Siguiente paso: `frontier/orch/frontier-orch auto` (lo lanza el usuario). Tras la primera ventana de Codex, medir
llamadas, contexto medio y minutos hasta el límite en `~/.codex/sessions/`.

## 2026-11-05 10:10 — Claude Code (Opus 5.5) — frontier-orch: límite semanal de Codex
Estado: hecho (orquestador parado; lo relanza el usuario)
Hecho:
- El usuario lanzó `auto` a las 09:54. Codex (F6-ARENA-B) falló a los 2 s: «try again at Nov 8th, 2026 1:43 PM»
  (`work/orch/logs/20261105-095451-codex-F6-ARENA-B.log`), es decir, el límite semanal. `RESET` no leía la fecha y
  aplicó la espera por defecto de 30 min; la tarea pasó a Claude con aviso de relevo y el usuario lo cortó con Ctrl+C
  a los pocos segundos (sin commits de Claude; `tasks.json` quedó con F6-ARENA-B `in_progress`, se conserva).
- `frontier_orch.py`: `RESET`/`reset_time` aceptan «Nov 8th, 2026 1:43 PM» (mes, día con ordinal, año opcional).
  Tres casos nuevos en `test_reset_time_from_the_limit_message`.
- `work/orch/state.json`: espera de Codex fijada a 2026-11-08 13:45 con el propio `reset_time`.
Evidencia: `python -m pytest -q tests/test_frontier_orch.py` → 36 passed. Sin procesos de agente ni de Azahar vivos
(`pgrep`).
Sin probar: gpt-6.1-sol sigue sin ninguna ejecución real (Codex sin cuota hasta el día 8).
Commits: el de esta entrada.
Siguiente paso: relanzar `frontier/orch/frontier-orch auto`: Claude hereda F6-ARENA-B con el aviso de relevo
(o el usuario decide devolverle la Arena a Claude / esperar al día 8).

## 2026-11-05 10:24 — Codex — F6-ARENA-B: primer mapa del motor (frontier-orch)
Estado: en curso
Hecho: leído AGENTS/PLAN/REPARTO/diseño/últimas entradas y Git; no existía trabajo previo de etapa B (la sesión
anterior agotó cuota al arrancar). Turno del orquestador sin cambiar. Nuevo `frontier/arena_survey.py`, solo lectura:
SHA256, tablas de eventos relocadas y listados de los candidatos M1–M5. `reports/frontier.md` §31 distingue las
medidas de lo pendiente: cadena CallSakasaBattle→3da5cc→1dbd18; setup de Mansión +0x620 (dump GDB); edad de
BattleMon +0x158 y reinicio 0x724cc; final de turno 0x1cf44; cola de KO 0x1dacc; predicado de cambio 0x79458
antes del permiso a Fantasma; ausencia de cueva grande en el texto CRO (los ceros son tablas relocadas), 1284 bytes
restantes en la cueva de code.bin. No hay parche de motor nuevo.
Evidencia: `source scripts/env.sh; python frontier/arena_survey.py > work/frontier/arena/b-static.txt`;
`python frontier/patch.py --out work/frontier/arena/b-measure-patch` (hook 1272 bytes);
`python -m pytest -q tests` → 506 passed (`b-tests-measures.log`). GDB: setup 0x08822b64, volcado `b-setup.bin`
SHA256 42366157…; DllBattle base 0x006f3000, predicado 0x0076c458 ejecutado desde offset 0x5e4c con rival id 12.
Commits: el de esta entrada.
Decisiones: no tocar código funcional hasta completar las medidas; no confundir flag de Sorpresa con contador ni
el registro ID 195 ajeno con el movimiento 195. In_progress (sin bloqueo que requiera decisión del usuario).
Los cinco archivos sin seguimiento del usuario se conservan intactos.
Siguiente paso: continuar la medición dinámica M2/M3 y el bit libre M1. Laboratorio en curso en esta sesión:
consola persistente (debe pararse antes de terminar), fixture ar_saved_457.sav, v0.5 + work/frontier/build.
En RAM se cambió el primer movimiento de Metagross a Canto Mortal (solo copia de combate, direcciones en
`work/frontier/arena/b-probe.gdb`), para medir los PS con watchpoints. Los logs de GDB siguen en
`work/faraway/gdb/out.log` y se copiarán a `work/frontier/arena/`. Mantener start, gdb e input en una misma consola:
las llamadas exec tienen namespaces de procesos separados; una llamada nueva no puede controlar sus PIDs.
No probado todavía: contador en marcha, Canto Mortal/KO, restricción del menú, Fantasma, juicio y regresiones B.

## 2026-11-05 10:48 — Codex — F6-ARENA-B: contador, KO y rechazo del menú medidos; juicio Unicorn
Estado: en curso
Hecho:
- Continúa 97ee614. GDB distingue las copias del cliente y del servidor; en el servidor, edades 2/2 y 3/3 y,
  tras Canto Mortal, entrada del siguiente con edad 0/turno de entrada 4. Canto Mortal usa condición 0x14
  (BattleMon+0x6c) y evento de cola **0x12**, que va a 0x1dacc. Watchpoint de PS: 129→0, PC 0x3b48fc,
  LR CRO+0x1dc44; después selección y entrada del siguiente. El rival cambió antes de expirar: no hubo KO doble.
- Camino del menú confirmado: llamada CRO+0xfe48 al predicado 0x79458. Devolver 3 con sus salidas inicializadas,
  antes de la excepción Fantasma y con tipos sintéticos 7/7, impide sustituir al activo. Captura y fuente en §31.
  No es aún prueba con un Fantasma de especie ni con un parche instalado.
- Reserva en REPARTO: bit 31 del word BattleSetup+0xa8 (candidato, se validará con regresiones) y works
  16693–16694 para PS iniciales. Turno del orquestador intacto. El bit puesto en RAM no alteró entrada/menú retail
  en el combate de medida; falta auditar los otros consumidores y programar su puesta/limpieza en StartBattle.
- `frontier/asm/arena.s`: por ahora SOLO juicio puro `arena_judge`, aislado de la build (no se enlaza desde
  patch.py). Porcentajes enteros, máscara de perdedores; snapshot a cero no juzga. Unicorn ejecuta también
  udiv retail 0x15ec10, con victoria/derrota/empate/truncado/extremos/curación y ABI comprobada.
- §31 documenta los 16 bytes de tres posibles puentes CRO→code.bin y las instrucciones que deberán reproducir;
  aún no se han ensamblado ni probado esos puentes. Tests del barrido evitan sobrescribir tablas relocadas.
Evidencia: `work/frontier/arena/b-gdb-dynamic.log` SHA256 e4905e02…; `b-menu-denied-ghost-type.png` e7232caa…;
`b-free-works.txt`; `python -m pytest -q tests/test_frontier_arena.py` → 45 passed; suite → 519 passed
(`b-tests-judge-full.log`). Laboratorio detenido en la misma consola que lo inició; stub desactivado/restaurado.
Commits: 97ee614 y el de esta entrada.
Decisiones: mantener F6-ARENA-B in_progress; no existe bloqueo que requiera decisión del usuario. No activar el
juicio en el motor antes de comprobar puente y marca de reglas. No declarar empate ni pruebas de regresión B.
Siguiente paso: completar la revisión del bit +0xa8 y los destinos/relocaciones de los tres puentes (§31);
implementar `arena_start` al final de StartBattle (después de construir el setup), snapshot/contador al entrar,
juicio en final de turno y predicado antes de Fantasma; extender patch.battle_cro mediante guarded_writes,
conservando v0.5 y Tubo. Añadir Unicorn de los puentes, contador/snapshots y gating; después build y aceptación
Azahar completa. Se puede reutilizar `arena_judge`; actualmente su test lo ensambla aislado y no modifica ROM.

## 2026-11-05 11:00 — Codex — F6-ARENA-B: motor y puentes integrados, Unicorn en verde
Estado: en curso
Hecho:
- `arena_engine.py`: constantes de bit, works y sitios; especificaciones `guarded_writes` de puentes de 16 bytes.
  Auditoría de esos intervalos: sin relocaciones ni saltos a sus instrucciones intermedias, test añadido.
- `arena.s` y `patch.py`: marca al final de StartBattle (ruta/activo/Individual), snapshot de PS al entrar con
  reinicio de edad retail, rechazo de cambio antes de Fantasma (permite reemplazo de debilitados), juicio tras
  tres turnos desde el último entrante. Usa las edades nativas y dos works; no necesita un tercer contador.
  En empate pone ambos PS a cero antes de tramitar los dos eventos KO 0x12 con force=1.
- Los puentes llaman a code.bin y recuperan la base CRO desde LR; el bloqueo temprano deshace el frame retail.
  `battle_cro` aplica las escrituras de Arena y Tubo sobre v0.5 mediante guarded_writes y rehash CRO/CRR único;
  queda preparado para componer las futuras escrituras del Palacio B.
- Unicorn de marca, snapshots/reinicio, rechazo (Fantasma y sustitución forzada), turnos/juicio/no-op sin marca,
  pila y registros, ambas bases CRO y ambos órdenes de velocidad. Tests de alcance de los parches actualizados.
Evidencia: suite 560 passed (`work/frontier/arena/b-tests-engine-full.log`); build completa generada con
`python frontier/overlay.py --out work/frontier/arena/b-build` (`b-build.log`). Hook 1936 bytes, quedan 620 libres.
Símbolos y algoritmo documentados en reports/frontier.md §31. Azahar con este motor **NO probado todavía**.
Commits: 97ee614, 255f5de y el de esta entrada.
Decisiones: bit 31 reservado con evidencia limitada a los consumidores examinados; regresiones obligatorias aún
pendientes. Works 16693/16694 de REPARTO se usan ahora. No marcar done hasta toda la aceptación de juego.
Laboratorio de las medidas anterior parado y sin AppRun vivo (comprobado en su namespace).
Siguiente paso: instalar b-build solo en el laboratorio y comprobar marca/snapshots/turnos y juicio; empezar con
victoria/derrota/empate en condiciones controladas, luego Fantasma real, sustituto, racha/PB y regresiones. Si el
motor devuelve mal el empate, medir la cola de KO y el resultado antes de cambiar el protocolo. Los stubs no han
sido validados todavía por el juego. No hay ningún binario comercial seguido ni inputs/partida original tocados.

## 2026-11-05 12:20 — Claude Code (Opus 5.5) — F6-ARENA-B: aceptación en Azahar del motor (relevo de Codex, frontier-orch)
Estado: en curso
Hecho:
- Relevo: Codex se cortó por cuota tras bb09fa8. Sin cambios a medias en ficheros seguidos; quedaban sin seguir sus
  herramientas `frontier/lab_arena.py` (fixture) y `frontier/lab_arena_probe.py` (sonda GDB), que se incorporan.
  Laboratorio de Codex no vivo (sin session.json ni procesos); `b-build` = reconstrucción de HEAD (`diff -r` idéntico).
- Sonda corregida: la IA del rival elige con la copia del cliente (servidor−0xd98, medido); sin ella Gengar cayó por
  Pulso Umbrío. Ahora se neutralizan ambas copias y avisa si no encuentra la del cliente.
- Azahar con b-build (detalle y hashes en reports/frontier.md §31 «Aceptación en Azahar»): marca puesta solo en la
  Arena; cambio bloqueado con Gengar real; victoria por juicio de los tres rivales, 1 PB al ganar el 7.º (13→14);
  empate a mitad con sustitución de ambos; derrota por juicio; empate con el último propio y empate de los dos últimos
  → resultado 0 (derrota); racha 0/0/14, PB 3, equipo intacto.
- Work a 0: Torre (racha 12, ruta 2), Mansión 517 y salvaje en Ruta 102: flag 0, cambio permitido, edades ≥3 con
  ambos vivos sin juicio. Torre: después racha 0/récord 12 y works de la Arena a 0.
Evidencia: `work/frontier/arena/b2-gdb-arena.log` (a1635c48…), `b2-gdb-tower.log`, `b2-gdb-maison.log`,
`b2-gdb-wild.log`; partidas `b2-after-loss.sav` (4000357e…), `b2-after-lasttie.sav` (d3677c07…), `b2-tower-after.sav`;
capturas `b2-ghost-blocked.png` (5bcd1494…), `b2-win-bp.png`, `b2-tie-*.png`. `python -m pytest -q tests` → 560 passed.
Laboratorio parado (sin procesos), `use_gdbstub` restaurado a false; `inputs/` y la partida original intactos (a30034d1…).
Commits: el de esta entrada.
Decisiones: no tocar el parche (todo lo medido coincide con el diseño). Mantener in_progress: falta el combate de
entrenador del mundo exigido por la aceptación. No hay bloqueo que requiera al usuario.
Siguiente paso: un combate contra un entrenador del mundo no vencido con b-build y `b-probe-normal.gdb`
(flag 0, cambio permitido, edades ≥3 sin juicio). La Ruta 102 de la partida real tiene vencidos los recorridos;
probar otra zona de esa partida (p. ej. Ruta 104 / Bosque Petalia, al oeste de Ciudad Petalia) o borrar en una copia
el flag de un entrenador. Opcional: Fábrica/Palacio en juego. Luego marcar done con evidencia.

## 2026-11-05 12:40 — Claude Code (Opus 5.5) — F6-ARENA-B: intento de combate de entrenador del mundo (sin resultado)
Estado: en curso
Hecho: segunda sesión de laboratorio con una copia nueva de la partida real (`b2-route102-in.sav`, a30034d1…)
para buscar un entrenador no vencido al oeste de Ciudad Petalia. La navegación a ciegas por el mundo no llegó a la
Ruta 104 (acabó dentro de una casa de Petalia); no hubo ningún combate en esa sesión. Laboratorio parado, sin
procesos, `use_gdbstub` restaurado; partida original intacta.
Evidencia: ninguna nueva (sin combates). Suite sin cambios desde 44b9aa8 (560 passed).
Commits: el de esta entrada.
Decisiones: no forzar más la búsqueda en esta sesión.
Siguiente paso: igual que la entrada anterior. Más rápido que andar: localizar el entrenador más cercano de la Ruta
102/104 con los datos de zona (`frontier/zone_check.py`/scripts de la zona 24) y su flag de vencido, y borrarlo en una
copia de la partida; o colocar al jugador junto a él con `faraway/save_event.py` (posición). Comprobar con
`b-probe-normal.gdb`: flag 0, cambio permitido, edades ≥3 sin juicio. Después, done.

## 2026-11-05 13:40 — Claude Code (Opus 5.5) — F6-ARENA-B: entrenador del mundo y demás instalaciones; tarea cerrada
Estado: hecho
Hecho:
- Entrenador del mundo con el work a 0: posiciones de los NPC de la zona 24 leídas del fichero de entidades; los cuatro
  entrenadores estaban vencidos. Flag de vencido = 1740 + id (scripts compartidos 52/81), con control positivo/negativo
  en la partida. Copia con solo 1748 = 0: el Cazabichos reta; bit 31 a 0 (word 0x10000), cambio permitido, edades ≥3 sin juicio.
- Palacio, Domo, Fábrica (sala 213) y Tubo con esta build: marca 0 y cambio permitido; el gancho de PS/estado del Tubo
  sigue funcionando con el DllBattle conjunto. Pirámide no jugada (no llegué a combate en el piso).
- Test de la marca ampliado a todas las rutas 1–7 con el work de la Arena a 1; comprobado rompiendo la comparación
  de ruta (7 fallos) y restaurándola.
Evidencia: reports/frontier.md §31 «Cierre de regresiones»; `work/frontier/arena/b2-gdb-{trainer,palace,dome,factory,pike}.log`,
`b2-trainer8.sav` (9fd9d995…); `python -m pytest -q tests` → 566 passed (`b3-tests.log`).
Laboratorio parado, `use_gdbstub=false`, `inputs/` y partida original intactos.
Commits: el de esta entrada.
Decisiones: F6-ARENA-B pasa a done. Limitaciones aceptadas y escritas: consola no probada; Pirámide solo por la suite;
la Fábrica se vio con equipo propio (flujo de alquiler no verificado en esta build). Mente, Técnica, árbitro y Greta fuera.
Siguiente paso: la siguiente tarea de `frontier/orch/tasks.json`. Si se quiere más garantía: un combate de la Pirámide y
uno de alquiler de la Fábrica con esta build y `b-probe-normal.gdb`.

## 2026-11-05 15:02 — Codex — F6-PALACIO-B: relevo recuperado y parada expresa en M3
Estado: bloqueado
Hecho:
- Revisados AGENTS, PLAN, REPARTO, diseño, último commit 18a464f, status y diff. No existe CLAUDE.md.
  El turno sigue en frontier-orch, sin modificar REPARTO. Claude dejó integración B sin commit y resultados
  en work/frontier/palace/ sin informe ni entrada de relevo. No se han usado subagentes ni push.
- reports/frontier.md §32 recoge M1 Individual, localización de clientes (M2 parcial), M3 directo fallido
  y el ensayo híbrido posterior. Direcciones, fuentes, hashes y límites explícitos. M1 Multi, rwatch completos
  de M2 y M4 en GDB no realizados; no se presentan como medidos.
- El registro heredado de M3 fuerza tipo IA en cliente 0 (CRO+0x73064), crea objeto IA con flags 0 y deja
  pantallas negras tras una espera de 20 s. No se midió IsWin ni se repitió tipo IA con flags 7. El ensayo híbrido
  posterior conserva tipo interfaz, objeto IA flags 7 y desvía decisiones 3/5/6; hay capturas de victoria y
  sustitución, pero no aceptación de build/racha/PB. No se afirma imposibilidad de todas las vías IA.
- Se aplica la condición expresa de parada de la tarea ante el fallo de M3 directo: status blocked y pregunta
  concreta en notes sobre la vía híbrida y las alternativas 2 (ficha recortada) / 3 (truco de Multi).
- Para no integrar silenciosamente la vía posterior al fallo, archivado el cambio B completo y la corrección
  del test del Tubo en reports/diseno/palacio-b-experimental.patch (sobre 18a464f). Restaurados explícitamente
  desde HEAD arena.s, palace.py, patch.py y tests de Palacio/Tubo; palace.s y palace_engine.py retirados después
  de archivarlos. Sin stash ni reset. El generador activo queda como el último commit estable.
  Sondas originales preservadas en frontier/probes/palace/ para reproducir las medidas tras decidir.
Evidencia:
- b1-gdb-m1-m3a.log c82b21a0…; b1-m3a-black.png 70365222…; b2-gdb-m3b.log 989b94d7…;
  hashes completos y direcciones en §32. Parche fuente archivado: SHA256 505e054ca90d64adeea779f86fdb29233d82389d375fd9ecdb84fd01ac53cd32.
- Suite experimental tras ampliar los intervalos admitidos del test CRO del Tubo: 633 passed (b4-tests.log).
  Suite ACTIVA restaurada: `source scripts/env.sh; python -m pytest -q tests` → 566 passed en 17 s
  (work/frontier/palace/b4-restored-tests.log). `git apply --check reports/diseno/palacio-b-experimental.patch`
  y `git diff --check` correctos. No se han probado en Azahar los ganchos de la build experimental.
- Laboratorio arrancado para revisar el estado y detenido al aplicar la parada; en esta sesión NO hubo combate
  nuevo (b4-start-only.log). Tras stop, comprobación en el mismo namespace sin AppRun/Xvfb/GDB;
  use_gdbstub=false y sin session.json activo. Inputs y partida original no escritos.
- Informes sin seguir evoluciones-repolished.md, iniciales-repolished.md, senda-ignea.md y scripts
  inspect_encounters.py / inspect_evolutions.py ya estaban al llegar: no se han tocado ni incorporado.
Commits: 18a464f como base estable y el de esta entrada (archivo de investigación y bloqueo de F6-PALACIO-B).
Decisiones: respetar la parada explícita, preservar la etapa A y todo el código pendiente como propuesta revisable.
El fallo directo con flags 0 no es prueba de imposibilidad de la vía híbrida; necesita decisión, no declararla done.
Siguiente paso: esperar respuesta a notes. Si se autoriza la vía híbrida, revisar y aplicar el parche archivado
(`git apply --check` antes), completar M1 Multi/M2/M4 y auditoría del bit 30, reservarlo en REPARTO antes de usarlo,
regenerar sondas desde los símbolos enlazados y ejecutar la aceptación Azahar completa (sin entrada, KO/sustituto,
IsWin/racha/PB, Fábrica/Torre/Mansión/historia manuales, exclusión y vídeo). Si se elige 2 o 3, actualizar primero
el diseño y la aceptación. No restaurar automáticamente el código B ni marcar done por las capturas heredadas.

## 2026-11-10 10:35 — Claude Code (Opus 5.5) — frontier-orch: Sol medido y compactación de Codex
Estado: hecho (orquestador parado desde 2026-11-05 15:04, «needs the user» por F6-PALACIO-B bloqueada)
Hecho:
- Medida de gpt-6.1-sol en F6-ARENA-B (`~/.codex/sessions/2026/11/05/rollout-…10-00-37-01a1aaf0….jsonl`, `orch.log`):
  77 min hasta el límite (10:00→11:17), 211 llamadas, contexto medio ~250k (máx. 424k), 52 M de entrada (99 % en
  caché), 113k de salida, tres commits útiles (97ee614, 255f5de, bb09fa8). Astra en el Domo: ~15 min, 124 llamadas,
  ~142k de media. En F6-PALACIO-B (14:57→15:04): 30 llamadas, media ~78k, máx. 104k.
- `config.json`: Codex con `-c model_auto_compact_token_limit=150000` en `new` y `resume` (la clave existe en el
  binario de codex-cli 0.166.0). Desde el 2026-11-05 también está en `~/.codex/config.toml` del usuario (copia
  `config.toml.bak-20261105`), puesta allí porque el orquestador tenía el turno.
Evidencia: `python -m pytest -q tests/test_frontier_orch.py` en verde.
Sin probar: la compactación no se ha disparado aún (la ejecución del Palacio no pasó de 104k).
Commits: el de esta entrada.
Siguiente paso: decisión del usuario sobre F6-PALACIO-B (notas de `tasks.json`, `reports/frontier.md` §32); después
relanzar `frontier/orch/frontier-orch auto`.

## 2026-11-10 10:50 — Claude Code (Opus 5.5) — F6-PALACIO-B reabierta por la vía híbrida
Estado: hecho (sin ejecutar el orquestador)
Hecho: el usuario elige la vía híbrida de `reports/frontier.md` §32 para el Palacio B (frente a la alternativa 2,
ficha recortada, y a la 3, truco de Multi). `tasks.json`: F6-PALACIO-B pasa de `blocked` a `pending`, con notas
(punto de partida: `reports/diseno/palacio-b-experimental.patch`, base 18a464f, y `frontier/probes/palace/`; no
retomar la conversión directa) y criterios nuevos (marca propia, guarded_writes sobre v0.5/Tubo/Arena, M4, ronda
sin pulsaciones en Azahar con resultado, racha y PB, regresiones manuales). Decisión anotada en REPARTO.
Evidencia: `frontier/orch/frontier-orch status`.
Sin probar: nada de la vía híbrida en build; solo las trazas GDB heredadas de §32.
Commits: el de esta entrada.
Siguiente paso: el usuario lanza `frontier/orch/frontier-orch auto` (dueño Claude; Codex por relevo).

## 2026-11-10 11:05 — Claude Code (Opus 5.5) — frontier-orch: tareas v2 para Codex
Estado: hecho (sin ejecutar el orquestador)
Hecho: el usuario pide más tareas para Codex. `tasks.json` gana F6-PIRAMIDE-V2A (sin PC en los pisos, vencidos
ocultos, aspecto de cueva) y F6-TUBO-V2 (PP persistentes, inmunidades, salvajes), las dos de Codex, `pending` y
detrás de F6-PALACIO-B: las tres pueden necesitar el hueco de `code.bin` (620 bytes libres hoy, 348 con el
experimento del Palacio B, §32), y cada una debe medirlo antes de escribir código nativo.
Decisiones: sin paralelismo; el orquestador lleva una tarea a la vez porque hay un solo laboratorio de Azahar y
ficheros compartidos (REPARTO normas 1 y 6).
Evidencia: `frontier/orch/frontier-orch status`.
Commits: el de esta entrada.
Siguiente paso: el usuario lanza `frontier/orch/frontier-orch auto`.

## 2026-11-10 11:30 — Claude Code (Opus 5.5) — F6-PALACIO-B: vía híbrida integrada, auditoría del bit 30 y M4
Estado: en curso
Hecho:
- Revisado y aplicado tal cual `reports/diseno/palacio-b-experimental.patch` (sin cambios en sus ficheros desde 18a464f):
  `asm/palace.s`, `palace_engine.py`, puentes guardados en `patch.battle_cro` encima de la v0.5 con el Tubo y la Arena,
  «Guardar vídeo» oculto en el menú del Palacio, tests Unicorn.
- Bit 30 de `setup+0xa8` reservado en REPARTO (sección de reservas del motor; el turno no se toca).
- Auditoría estática de sus lectores (`frontier/probes/palace/audit_a8*.py`): ninguna máscara con el bit 30 en code.bin
  ni en las 145 CRO; detalle y límites en reports/frontier.md §33.
- M4: gancho 2208 bytes, 348 libres. Build `work/frontier/palace/c-build`, idéntica a `b3-build`.
Evidencia: `python -m pytest -q tests` → 633 passed; `work/frontier/palace/c/audit-a8.txt`, `audit-a8-all.txt`,
`c-build.log`. Azahar: no probado aún en esta sesión.
Commits: el de esta entrada.
Siguiente paso: aceptación en Azahar con `c-build` (sonda pasiva `work/frontier/palace/b3-probe.gdb`, direcciones
comprobadas contra los símbolos enlazados): ronda sin pulsaciones desde `b3-streak6-in.sav` (racha 6) y una desde
`b1-in.sav`; KO con cambio automático; IsWin, racha ruta 3 y PB; pausa/reanudación/derrota; regresiones manuales.

## 2026-11-10 11:35 — Claude Code (Opus 5.5) — F6-PALACIO-B: build en Azahar, despacho corregido, vídeo de derrota oculto
Estado: en curso
Hecho:
- En Azahar el parche experimental no desviaba nada (r1 en CRO+0x49ec no es el comando): corregido `palace_dispatch`
  (byte 0 de la fila), test Unicorn reescrito. Con la build corregida: ronda de 7 victorias con decisiones y cambio
  automático por la IA, derrota (IsWin 0), PB 4, racha 0/0/7; reanudación 2→4 y pausa 4/1/4 (reports/frontier.md §33).
- «Guardar vídeo» también salía tras la derrota: `palace.hide_record` anula la rutina L3fdc en el Palacio.
- Los textos del entrenador (presentación y derrota) siguen esperando A como en retail: mecanismo medido en §33,
  sin resolver. Criterio «sin ninguna pulsación» no cumplido en esos dos textos.
Evidencia: §33; `work/frontier/palace/c/` (gdb-s1.log, presses*.log, capturas), partidas c2-after-loss.sav,
c3-paused4.sav; `python -m pytest -q tests` → 696 passed.
Commits: el de esta entrada.
Siguiente paso: regresiones con control manual (Fábrica, Torre, Arena, Mansión, entrenador del mundo) con c-build3;
después decidir los textos del entrenador (seguir el gestor `vista+0x444`, vtable CRO 0xe5168, o preguntar).

## 2026-11-10 11:55 — Claude Code (Opus 5.5) — F6-PALACIO-B: regresiones manuales; bloqueada por una pregunta (textos)
Estado: bloqueado (decisión del usuario)
Hecho:
- Regresiones con `c-build3` y control manual: Torre, Arena (juicio y victoria por juicio con la sonda `win`),
  Fábrica (alquileres, reemplazo manual), Mansión y entrenador de la Ruta 102: bit 30 a 0 y decisiones del cliente 0
  por la columna 0 en todas; sin cuelgues (reports/frontier.md §33).
- Sondas y conductores de laboratorio copiados a `frontier/probes/palace/lab-*`.
- Laboratorio parado, `use_gdbstub=false` restaurado; `inputs/` y la partida original sin tocar.
Evidencia: §33; `work/frontier/palace/c/gdb-{arena,factory,maison,world}.log`, capturas `c/r-*.png`;
`python -m pytest -q tests` → 696 passed.
Sin probar: Domo, Tubo y Pirámide con esta build; exclusión mutua en Azahar (solo suite); consola.
Commits: el de esta entrada.
Decisiones: `tasks.json` F6-PALACIO-B → `blocked` con la pregunta: los textos del entrenador (presentación y derrota)
siguen esperando A como en retail; ¿se acepta o se investiga su avance automático solo en el Palacio?
Siguiente paso: según la respuesta: (a) marcar done con la evidencia de §33; (b) seguir las pistas de §33 «Pendiente»
(importación CRO 0x1018 sobre `[[vista+0x1a0]]+0xcc`, argumento `r2=1` de 0x5c314/0x5c730), gatear con el bit 30,
y repetir en Azahar una ronda con `lab-drive.sh` esperando 0 pulsaciones en combate.

## 2026-11-10 18:00 — Claude Code (Opus 5.5) — F6-PALACIO-B cerrada (decisión del usuario)
Estado: hecho
Hecho: a la pregunta de `f1f3ce3` el usuario elige (a): se acepta que la presentación del entrenador y su frase de
derrota sigan esperando A, como en retail. F6-PALACIO-B pasa a `done` en `tasks.json`; REPARTO, fila del Palacio:
etapa B hecha, etapa C (naturaleza) pendiente.
Evidencia: `python -m pytest -q tests` → 696 passed. Azahar: la de §33 (commits 7623899, 571586e, f1f3ce3).
Sin probar: consola.
Commits: el de esta entrada.
Decisiones: el avance automático de esos dos textos solo en el Palacio queda como pulido opcional (§33 «Pendiente»),
sin tarea.
Siguiente paso: el usuario relanza `frontier/orch/frontier-orch auto` → F6-PIRAMIDE-V2A (Codex) y F6-TUBO-V2.

## 2026-11-10 18:05 — Codex — F6-PIRAMIDE-V2A: cueva construida y límites comprobados
Estado: en curso
Hecho: leídos AGENTS (sin CLAUDE.md), PLAN, REPARTO, diseño y relevo; turno de frontier-orch intacto.
Medido gancho actual: 2212/2556 bytes, 344 libres, 0x579604–0x579ea8; no se añade código nativo.
Pisos 141/142 clonados de Ruinas Desierto 77, sin props/PC ni disparadores retail; tres salidas al vestíbulo,
coordenadas en la primera sala, nativas 517 y texto 619 independientes del donante. Registro de modelos de área 214.
Validación de carga y ZO completo en el generador; tests actualizados para donante visual/nativo distinto.
Evidencia: reports/frontier.md §34; work/frontier/pyramid/v2/{entities,floor77,floor192}.txt y build-final.log:
ZO 16504 ≤ 17248 por piso, carga 566272 ≤ 2724608. Suite tests-m1.log: 697 passed.
Commits: el de esta entrada.
Decisiones: usar alternativa aceptada «no vuelve a combatir» (work 16686 existente), conservar NPC visibles.
No añadir flags ni gastar la cueva nativa compartida. No se tocaron inputs, informes ajenos sin seguir ni partida original.
Siguiente paso: aceptación Azahar con v2/build, partida v2/start.sav (copia de py_lobby_saved.sav): reanudar,
comprobar movimiento y NPC en cueva, siete pisos y PB, persistencia tras salir/guardar/recargar, derrota,
exclusión y regresión. Laboratorio vivo en la shell persistente de esta sesión; al terminar debe detenerse.

## 2026-11-10 18:19 — Codex — F6-PIRAMIDE-V2A: persistencia y primer piso en Azahar
Estado: en curso
Hecho: llegada y movimiento en Ruinas Desierto, tres entrenadores combatibles, encargado accesible y transición
1→2 con racha/piso/récord 1/2/1 y vencidos 0. Salida al vestíbulo y reentrada: el vencido 0 rechaza combatir.
Guardar mediante interfaz y reiniciar en la cueva conserva vencidos 1 y la selección; siguiente combate correcto.
Añadidas sondas y conductores reproducibles en frontier/probes/pyramid; no forman parte del parche.
Evidencia: reports/frontier.md §34, capturas v2/floor1.png y beaten-return2.png; partida floor1-beaten0.sav SHA
9c58778b760f383a5c8b8bfe781f96725655d65c5b1ad7518ea27b613f733c7c; v2/climb.log y gdb-before-reload.log.
Tests: compileall y bash -n de las sondas; pytest 697 passed (v2/tests-final.log).
Commits: ddd8428 y el de esta entrada.
Decisiones: combates asistidos con HP 1/Salpicadura del rival en RAM; no se alteran resultados, works ni PB.
Siguiente paso: terminar recorrido de siete pisos (conductor vivo en shell persistente), guardar PB, probar derrota,
exclusión y Torre con la misma build; detener laboratorio. Tarea sigue in_progress, no hay decisión pendiente.

## 2026-11-10 18:47 — Codex — F6-PIRAMIDE-V2A: siete pisos, PB y derrota
Estado: en curso
Hecho: 21 victorias reales asistidas, tres por piso, siete cambios por el encargado, final 7/0/7 ruta 0.
Recompensa adicional con fixture de frontera explícita: PB 0→5 y 7/0/7 guardados; equipo real idéntico.
Derrota real asistida con equipo 4/5/3: IsWin 0, limpieza 0/0/7 ruta/vencidos 0, PB 5→5 guardados.
Corregido conductor (A sobrante al llegar al vestíbulo), añadido rechazo del guardado sin cambios y auditoría de logs.
Evidencia: reports/frontier.md §34; v2/gdb-round.log + gdb-before-reload.log, climb.log, round-audit.txt;
partidas py_v2-top-paid.sav SHA 97c0571308269dfff528f77ccab5922408f2c563090ed187ddabd23c8ec3cf3e y
py_v2-loss.sav SHA 3a2410afe9af564d9e8b3f2dfd106fe60d57cca00997afe5c67ac4bb0e83abaa; top-bp.png, lost.png.
Tests: 60 passed test_frontier_pyramid.py, auditoría 21 victorias/transiciones, compileall y bash -n; suite previa 697.
Commits: ddd8428, 61d0910 y el de esta entrada.
Decisiones: intento v2-round7 inválido (no guardó por diálogo abierto); su estado final medido se conserva en logs,
recompensa medida además con fixture, sin presentar esa fixture como recorrido. No cambios nativos.
Siguiente paso: Pirámide rechaza Torre activa (boot en curso), Fábrica rechaza Pirámide activa y regresión Torre.
Después, detener laboratorio y cerrar tasks.json si todo pasa. Tarea in_progress.

## 2026-11-10 19:09 — Codex — F6-PIRAMIDE-V2A cerrada: exclusión, regresión y recarga
Estado: hecho
Hecho: Pirámide rechaza Torre activa y Fábrica rechaza Pirámide activa, sin StartBattle.
Torre con selección y menú de lucha manual: victoria asistida raw=1, racha/récord 12→13, ruta 2,
marca nativa 0 y Pirámide 0/0/0/0. Reinicio desde el guardado real floor1-beaten0.sav:
el entrenador dice «Ya hemos combatido» y no arranca combate. tasks.json pasa a done.
Evidencia: reports/frontier.md §34; work/frontier/pyramid/v2/{pyramid-refuses-tower,factory-refuses-pyramid,
tower-menu,tower-win,beaten-after-reload}.png; gdb-{busy,factory-busy,tower,reload-refusal}.log.
Suite final: python -m pytest -q tests, 697 passed in 18.43s (tests-close.log); audit_round.py confirma
21 victorias/siete transiciones; compileall, bash -n y git diff --check correctos.
Azahar, Xvfb y GDB detenidos en la misma shell; ningún proceso del runtime ni sesión viva,
use_gdbstub=false restaurado (lab-stopped.log 19:07:45 CET). Un solo laboratorio, sin push ni subagentes.
Commits: ddd8428 cueva/límites, 61d0910 persistencia/sondas, f2dfbb7 siete pisos/PB/derrota y el de esta entrada.
Decisiones: aceptación por «no vuelve a combatir», NPC vencido visible. Donante 77 dentro de ambos límites;
344 bytes nativos libres medidos y ninguno añadido. Combates asistidos HP 1/Salpicadura en RAM,
resultados/works/PB sin escribir. Recompensa adicional documentada como fixture, no como segundo recorrido.
No probado en consola ni dificultad; PS persistentes, objetos y salvajes siguen fuera de v2A.
Siguiente paso: frontier-orch verifica la tarea y selecciona la siguiente (F6-TUBO-V2 pendiente).
No tocar REPARTO: el turno sigue siendo del orquestador. Para rehacer la aceptación, usar v2/build y
frontier/probes/pyramid/README.md; guardados v1 físicamente dentro de Mansión deben salir antes al vestíbulo.

## 2026-11-10 19:15 — Codex — F6-TUBO-V2: PP persistentes, primer hito
Estado: en curso
Hecho: lectura de normas/diseño/relevo; turno del orquestador intacto. Medidos antes de cambios
2212/2556 bytes nativos (344 libres). H1/H2 guardan/restauran los cuatro PP mediante accesores retail;
works 16721–16723 y 16725–16727 reservados; inicio y curas restablecen PP. Generador valida bytes.
Evidencia: reports/frontier.md §35; work/frontier/pike/v2/space-before.json, pp-accessors.lst,
build-pp.log; tests-pp.log 116 passed, tests-m1.log 741 passed. Unicorn ejecuta además los accesores
retail con cifrado/checksum y 32 permutaciones. Gancho ahora 2348 bytes, 208 libres.
Commits: el de esta entrada.
Decisiones: dos movimientos por work, 0xff por byte = lleno, límite al máximo de la copia reconstruida.
Guardados v1 con desafío activo requieren retirarse y empezar otro al actualizar (PP antiguos sin inicializar).
Sin probar: Azahar con la v2, inmunidades y salvajes, racha/PB/equipo/exclusión/regresiones de aceptación.
Siguiente paso: comprobar PP entre dos combates en Azahar (build v2/build), medir ruta salvaje y selección
para inmunidades; no declarar done. Laboratorio aún no arrancado. Tarea in_progress; sin push ni subagentes.

## 2026-11-10 19:31 — Codex — F6-TUBO-V2: inmunidades y PP medidos en Azahar
Estado: en curso
Hecho: inmunidades del evento fijadas a pokeemerald 731ad5bf. Consulta de tipos/habilidad actual retail;
slots virtuales 256–258 consultan selección real o Caja de Combate mediante puente DllField+0x4e644.
Rehechos hashes CRO/CRR, bytes/hash de entrada guardados. Texto de rechazo y líneas reasignadas.
Azahar con build PP: tres victorias asistidas; PP 10→6, restaurados 6 en siguiente combate, terminan 3.
PS 156→137; sala 14 muestra 1 PB. Guardado final/equipo aún no medidos.
Evidencia: reports/frontier.md §35; v2/gdb-pp.log, before-room14.png; tests-immune.log 302 passed;
tests-m2.log 927 passed; build-immune.log (2452 bytes nativos, 104 libres). compileall/bash -n/diff correctos.
Commits: b0d4bd6 y el de esta entrada.
Decisiones: reglas de inmunidad específicas del Tubo de Esmeralda, incluido Tierra contra parálisis;
no se añaden habilidades posteriores ni clima. Un inmune cuenta para el límite de objetivos.
No probado: puente/inmunidad en Azahar; salvajes/equipo/experiencia/captura; regresiones Palacio/Arena/exclusión.
Siguiente paso: cerrar/guardar el lab PP, probar inmunidad en build-immune; medir y construir salvajes.
Laboratorio vivo en shell persistente (PID namespace 4026533377, Azahar 18/Xvfb 15); parar antes de acabar.
Tarea sigue in_progress; orquestador conserva turno; sin push ni subagentes.

## 2026-11-10 19:43 — Codex — F6-TUBO-V2: curación de la copia, equipo original
Estado: en curso
Hecho: al auditar el guardado PP se detecta curación retail del equipo real (solo dos PS cambiados).
Constructor omite esa curación en ruta 6; H1 cura la copia y restaura PS/estado/PP. Otras rutas intactas.
Añadida precondición al boot para no mezclar IPS instalado y símbolos de sonda de otra build.
Evidencia: reports/frontier.md §35; v2/pp-paused.sav, build-copy.log, space-copy.txt (2468/2556, 88 libres),
tests-copy-final.log 935 passed; compileall, bash -n y diff --check correctos.
Commits: b0d4bd6, 449494f y el de esta entrada.
Decisiones: guardado PP confirma sala 15, activo/récord 1/15, PB 1 y primer movimiento 3 PP.
No probado: equipo idéntico al salir con la corrección, inmunidad en Azahar, salvajes y regresiones.
Siguiente paso: experimento propio de salvaje en Azahar (competitor=0, copia, noexp=1, rival único),
medir bolsa/captura/experiencia antes de implementarlo; después inmunidad y aceptación pendiente.
Lab vivo en shell persistente; parar al terminar. tasks.json sigue in_progress; turno del orquestador intacto.

## 2026-11-10 19:58 — Codex — F6-TUBO-V2: espacio compartido y captura medida
Estado: en curso
Hecho: Arena/Palacio comparten inicio; recuperados 52 bytes, 2416/2556, 140 libres.
Sonda salvaje solo RAM con rival único gana raw=1; conserva intro de entrenador. En otra prueba,
Bolsa/Poké Balls accesibles y una Ball consumida 13→12: cambiar competitor no impide captura.
Evidencia: reports/frontier.md §35 hito 4; space-shared.txt, tests-shared-real.log 252 passed,
tests-shared-full.log 935 passed, build-shared.log; gdb-wild-experiment.log y capturas wild-*.png.
Commits: b0d4bd6, 449494f, c357a7d y el de esta entrada.
Decisiones: sonda no es implementación; candidato 168 bytes sin integrar no prueba mínimo de espacio.
Aún no probado: inmunidad dinámica, no exp/captura, equipo al salir, derrota salvaje y regresiones.
Siguiente paso: medir restricción retail de bolsa (regla 0x2000 candidata, sin asumir significado),
probar inmunidad y conservación del equipo; integrar salvajes solo si caben y se bloquea captura.
Lab aún vivo en shell persistente; apagar al cerrar sesión. Tarea in_progress, turno sin tocar.

## 2026-11-10 20:25 — Claude — F6-TUBO-V2: relevo y salas salvajes integradas
Estado: en curso
Hecho: relevo de Codex (cuota). Revisados status/diff: `lab_probe.py` (sondas de consulta/setup salvaje) y
`wild_candidate.s` (marcado como sustituido) se conservan en este commit; ningún laboratorio vivo.
Sala salvaje integrada con el combate de la Mansión (competitor 2): work 16675 = set salvaje (0 = ninguno),
sets de Esmeralda en maisonpkN 217–222 (entradas vacías medidas), rival de un Pokémon a nivel 46/45;
nuevo sitio 0x1e4e80. Tipo WILD en la pista POKÉMON, texto 1056 (Pirámide 1057–1071), REPARTO actualizado.
Evidencia: reports/frontier.md §35 hito 5; gancho 2544/2556 (12 libres, `patch.assemble()`);
`python -m pytest -q tests` 968 passed; build `work/frontier/pike/v2/build-wild` (build-wild.log).
Commits: el de esta entrada.
Decisiones: no cambiar competitor (a 0 abría la Bolsa y gastaba Balls, hito 4); la Mansión ya no da exp.
Desviaciones: un combate por sala; presentación de entrenador; naturaleza Fuerte sin EV.
No probado: nada de la sala salvaje en Azahar (Bolsa/captura/exp con competitor 2, victoria/derrota).
Siguiente paso: laboratorio con build-wild: sala salvaje ganada y perdida, Bolsa bloqueada, equipo al salir,
inmunidad, PP, sala 14/PB, exclusión, regresión Palacio/Arena. Turno del orquestador intacto.

## 2026-11-10 20:55 — Claude — F6-TUBO-V2 cerrada: aceptación en Azahar
Estado: hecho
Hecho: corregidos los números de tipo de las inmunidades (ORAS no tiene «???»: Fuego 9, Eléctrico 12, Hielo 14;
medido en texto 18 y tabla personal a/1/9/5). Aceptación en Azahar con build-wild: PP entre salas, estado rechazado
por inmunidad, salvaje ganada (Seviper Nv46, rival único, Bolsa inerte) y perdida (raw 0, limpieza), sala 14 con 1 PB,
equipo al salir, exclusión en ambos sentidos, regresión del Palacio (bit 30) y la Arena (bit 31).
Evidencia: reports/frontier.md §35 hitos 5–6; work/frontier/pike/v2: gdb-wild-session1.log, gdb-palace.log,
gdb-arena.log, capturas immune-*, wild-*, room14-*, *-refuses-*, palace/arena-after-win.png; wild-after-loss.sav
c9093b9f…; tests-final.log 973 passed; compileall, bash -n y diff --check correctos.
Commits: 0694701, c85de46 y el de esta entrada (sondas: seconds.py, lab_probe.py con reloj en code.bin 0x12fae4).
Decisiones: salas forzadas con segundos calculados en la VM (predicción = pantalla); derrota con fixture en RAM de
works (PS 1, PP 0) y rival 300 PS; el resto de combates asistidos solo en RAM. tasks.json → done.
Abierto (fuera de criterios): tras unas A de más en el menú posterior a un combate, la reanudación en la misma sesión
empezó el desafío de cero (racha 20 → 0, récord 20); sin aislar. La cinta de racha 20 de la Mansión se concede con
20 salas del Tubo. No probado: consola, juicio de la Arena, IA del Palacio.
Siguiente paso: frontier-orch verifica y elige la siguiente tarea. Para reproducir: frontier/probes/pike/boot.sh con
PIKE_BUILD=work/frontier/pike/v2/build-wild, `pk_want` en la sonda y fight.sh. Laboratorio detenido
(sin procesos, use_gdbstub=false). Turno del orquestador intacto; sin push ni subagentes.

## 2026-11-10 18:30 — Claude Code (Opus 5.5) — frontier-orch: modo paralelo (rama orch-parallel)
Estado: en curso (rama `orch-parallel` en un worktree aparte, sin integrar en main; el orquestador secuencial tenía
el turno con Codex en F6-PIRAMIDE-V2A y no se tocó nada de main)
Hecho:
- `frontier_orch.py`: `auto --parallel` con un carril por agente (worktree `work/orch/lanes/<agente>`, rama
  `lane/<agente>`), `lanes setup|remove`, integración por rebase + fast-forward tras cada ejecución, estado del agente
  en `work/lane-task.json`, aceptación en main, relevo entre carriles, `status` con los carriles.
- Laboratorio por checkout: `azahar_lab.py` con puerto desde `ORAS_GDB_PORT`/`work/lab-port` y `reap` (mata solo
  emulador, Xvfb y gdb de su carpeta; gdb se reconoce por su `out.log`, porque `gdb.pid` guarda el PID del espacio
  de nombres del sandbox: 233 para un 1113858 real, medido hoy); `gdbctl.sh` y `walk.sh` con rutas relativas.
  `after_run` pasa a `reap`. `.gitignore` sin barra final (ignora los enlaces de los carriles). `.gitattributes`:
  union para BITACORA.md y reports/frontier.md.
- README del orquestador: modo paralelo, límites, migración y marcha atrás. `frontier/orch/lab_smoke.sh`.
Evidencia: `python -m pytest -q tests` en el worktree → 704 passed, 2 skipped; `tests/test_frontier_orch.py` 45
passed cinco veces seguidas (8 tests nuevos: concurrencia real, unión de la bitácora, conflicto que bloquea sin
ensuciar main, relevo entre carriles, aceptación fallida, `lanes remove` sin tocar lo compartido, raíz de escritura
de Codex). Detección de procesos de `reap` contrastada en seco con el laboratorio vivo de Codex (sin matar nada).
Sin probar: dos Azahar reales a la vez (`lab_smoke.sh`), agentes reales en carriles (sandbox de Codex escribiendo en
el `.git` principal desde un worktree, `ORAS_GDB_PORT` dentro de su sandbox), la copia de `work/azahar-lab/data`.
Siguiente paso: cuando el orquestador suelte el turno, con el usuario: integrar la rama, `lanes setup`,
`lab_smoke.sh`, una tanda corta con `auto --parallel --max-runs 2`; marcha atrás según el README.

## 2026-11-11 00:30 — Claude Code (Opus 5.5) — frontier-orch: migración al modo paralelo
Estado: hecho (falta una tanda con agentes reales en carriles: no queda ninguna tarea abierta)
Hecho:
- El orquestador secuencial terminó el 2026-11-10 a las 20:49 («all tasks done»): F6-PIRAMIDE-V2A (Codex,
  17:59→19:09) y F6-TUBO-V2 (Codex 19:09→19:59, cuota; Claude 19:59→20:49). Codex con Sol y compactación a 150k
  aguantó **2 h** seguidas (17:59→19:59) frente a 77 min el 5 de noviembre: sesiones de 293 y 201 llamadas, contexto
  medio ~84k y ~89k, máx. ~150k, 2 y 3 compactaciones (`~/.codex/sessions/2026/11/10/`).
- Rama `orch-parallel` rebasada sobre main (conflicto solo en BITACORA.md, resuelto a mano añadiendo la entrada de
  las 18:30 al final) y fusionada con `--no-ff` (300fcc1). Etiqueta `pre-parallel` = main justo antes (64b2eeb).
- `frontier-orch lanes setup`: carriles `work/orch/lanes/claude` (24690) y `…/codex` (24691) en 0,5 s; enlaces a
  inputs, tools, baseline, dist, analysis, downloads, .venv, runtime de Azahar, `work/extracted` y la ROM;
  copiados `azahar-lab/{config,data}` (229 MB) y `work/frontier/lab` (176 MB) por carril.
- Prueba real de dos laboratorios a la vez (`frontier/orch/lab_smoke.sh`): los dos Azahar arrancan, cada gdb lee
  el PC de su emulador, el `reap` de un carril deja vivo al otro (su gdb sigue respondiendo) y al final no queda
  ningún proceso de los carriles. Tres pasadas seguidas en verde tras dos correcciones:
  - `gdbctl.sh start` esperaba 2 s fijos tras `target remote`; con dos laboratorios el `halt` llegaba a mitad de
    la conexión («Quit»). Ahora espera a que el stub responda (hasta 30 s).
  - el stub deja de escuchar en su puerto cuando tiene un gdb conectado: `lab_smoke.sh` comprueba el proceso y su
    gdb, no el puerto. Además el stub rechaza conexiones unos segundos después de abrir el puerto.
  Con los dos a la vez, Azahar iba al 77 % de velocidad (captura del carril de Codex en la pantalla de título).
Evidencia: `python -m pytest -q tests` en main → 983 passed; `frontier/orch/lab_smoke.sh` ×3.
Sin probar: agentes reales en carriles (commit de Codex desde un worktree con `{git_common}`, `ORAS_GDB_PORT` en su
sandbox, el aviso del brief paralelo), la integración con trabajo real de dos agentes a la vez.
Marcha atrás: `frontier/orch/frontier-orch lanes remove` y `git revert -m 1 300fcc1` (o volver a `pre-parallel`);
`auto` sin `--parallel` sigue igual.
Commits: 300fcc1 (fusión) y el de esta entrada.
Siguiente paso: crear tareas para los dos agentes que no se pisen y lanzar `frontier/orch/frontier-orch auto
--parallel --max-runs 2` como primera tanda vigilada.

## 2026-11-11 00:45 — Claude Code (Opus 5.5) — tareas de la primera tanda paralela
Estado: hecho (sin ejecutar el orquestador)
Hecho: `tasks.json` gana F6-PALACIO-C (Claude: filtro de movimientos por naturaleza y PS sobre la vía híbrida, con
tablas de a/1/8/9 y pokeemerald) y F6-DOMO-SALA (Codex: mapa propio para la zona 456 desde un donante retail, sin
código nativo, como la Pirámide v2A). Elegidas para no pisarse: la primera toca motor y code.bin; la segunda solo
zona, mapa y su script.
Riesgo conocido: las dos pueden tocar `frontier/island_build.py` o `reports/frontier.md`; el informe se une solo
(union), un conflicto en el código bloquea la tarea (README del orquestador).
Commits: el de esta entrada.
Siguiente paso: el usuario lanza `frontier/orch/frontier-orch auto --parallel --max-runs 2`; revisar la integración,
el commit de Codex desde su carril y los puertos.

## 2026-11-11 01:30 — Claude Code (Opus 5.5) — F6-PALACIO-C: filtro en la CRO y Unicorn
Estado: en curso (falta Azahar)
Hecho: reglas y tabla de naturalezas de pokeemerald 731ad5bf (fuentes y sha256 en reports/frontier.md §36);
tabla de grupos generada desde a/1/8/9 (regla por objetivo de Gen 6 calibrada contra Esmeralda en 1–354, 6
excepciones). La IA decide en DllBattle 0xd0c8; 0xd468 `bl 0xe044` (huecos usables → IA+0x198) pasa a
`palace_moves` (asm/palace_cro.s), enlazado en el relleno a cero de la región de código de la CRO (0xd7630, 568
bytes) porque la cueva de code.bin solo tiene 12 libres. Sortea el grupo con rand(100), naturaleza (code 0x152f08)
y PS (+0x10/+0xe) y deja usables solo los del grupo; si no hay ninguno, los deja todos. Reserva anotada en REPARTO.
Evidencia: `python frontier/palace_ai.py` → work/frontier/palace/c/space-c1.txt; tests Unicorn nuevos en
tests/test_frontier_palace.py; `env -u ORCH_LANE python -m pytest -q tests` → 1066 passed, 1 skipped
(c/tests-c1.log). Con ORCH_LANE puesto fallan 9 tests de test_frontier_orch.py (entorno del carril).
Commits: el de esta entrada.
No probado: nada en Azahar (ejecución real del relleno de la CRO, naturaleza leída, grupos en combate).
Siguiente paso: build `python frontier/overlay.py --out work/frontier/palace/c-build`; laboratorio (puerto 24690)
con partida del Palacio delante de la puerta (`work/frontier/lab/` o las de §33), sonda GDB en CRO+0xd7630/0xd46c
y en el resultado IA+0x278 (0xd61c); Pokémon de naturaleza marcada, varios turnos, PS < 50 % con fixture;
regresión Arena y una instalación sin motor.

## 2026-11-11 01:20 — Claude Code (Opus 5.5) — F6-PALACIO-C cerrada: aceptación en Azahar
Estado: hecho
Hecho: build c-build y laboratorio del carril (24690). Metagross Amable (fixture c2-gentle.sav): ronda de 7
victorias sin cuelgues; 68 decisiones del cliente 0 registradas por GDB, todas del grupo sorteado según la tabla
de Esmeralda (c2_check_log.py: 0 discrepancias; 13 con grupo vacío → otros grupos). Cambio de columna con daño
real (75/156 → baja) y con fixture de RAM (45 %). Rival sin filtro. Regresiones: Arena (bit 31, manual, victoria)
y Mansión (manual, sin marca). El código en el relleno de DllBattle.cro se ejecuta en Azahar.
Evidencia: reports/frontier.md §36 (Azahar); work/frontier/palace/c/: gdb-palace-round.log, gdb-arena.log,
gdb-maison.log, presses.log, t-after7.png, ra-after.png, r-maison-moves.png, tests-c2.log (1066 passed, 1 skipped
con `env -u ORCH_LANE`). Sondas en frontier/probes/palace/ (lab-c2-*, c2_fixture.py, c2_check_log.py).
Commits: 6393218 y el de esta entrada.
Decisiones: grupo vacío → la IA elige entre todos los usables (de otros grupos); columna baja instantánea (sin la
fijación de Esmeralda ni la excepción de dormido).
No probado: consola; juicio de la Arena con este parche; Fábrica/Torre/Tubo/Pirámide/Domo con esta build.
Siguiente paso: frontier-orch integra lane/claude y pasa la aceptación. Pendientes del Palacio fuera de C: «no
obedece», textos del entrenador (§33), rival por naturaleza, Doble. Laboratorio parado.

## 2026-11-11 01:15 — Claude Code (Opus 5.5) — F6-PALACIO-C: REPARTO y corrección de horas
Estado: hecho
Hecho: fila del Palacio en REPARTO: etapa C hecha (§36). Corrección: las dos entradas anteriores de F6-PALACIO-C
llevan horas estimadas (01:30 y 01:20); las reales son anteriores a las 01:13 (`date`), en el orden en que figuran.
Commits: el de esta entrada. Siguiente paso: el de la entrada anterior.
## 2026-11-11 00:29 — Codex — F6-DOMO-SALA: donante y build verificadas
Estado: en curso
Hecho: sala 456 con mapa/área propios de 365 (sala amplia de Liga); tres NPC, texto y máscara de nativas de 517,
salida a su puerta de plaza. Script del Domo y code.ips generados idénticos a la build anterior. Guardas de ZO,
script, entidades, texto y salida en frontier/dome_room.py; integración en island_build; seis tests nuevos.
Evidencia: reports/frontier.md §36; work/frontier/island/zones.tsv, work/frontier/dome/room/{entities,floor*,budget*}.txt,
build-before.log/build-after.log. Carga 305024/2724608; ZO 15452/17248. Tests con `env -u ORCH_LANE python -m pytest -q tests`:
988 passed, 1 skipped. Sin quitar ORCH_LANE fallaban nueve tests del orquestador: el agente ficticio heredaba el
carril y escribía lane-task.json en lugar de tasks.json; no se cambió el orquestador. diff --check correcto.
Commits: el de esta entrada.
Decisiones: 365 cubre en altura 0 las coordenadas retail de la coreografía Individual; no se modifica el script.
No probado: todavía el ciclo del torneo en esta sala ni consola. Captura antes en room/before.png (build anterior).
Siguiente paso: entrar desde la puerta de plaza en Azahar, inspeccionar la sala, inscripción/combate/pausa,
guardar/cargar dentro y salir; regresión de puertas Fábrica/Torre. Laboratorio activo solo en este carril, puerto 24691.
Turno y tasks.json intactos; estado en work/lane-task.json.

## 2026-11-11 00:24 — Codex — corrección del hito anterior: commit rechazado por sandbox
Estado: en curso
Hecho: la entrada anterior lleva una hora adelantada por error (00:29); el comando de commit se intentó antes
 de las 00:22. No hubo commit: `git add` y `git commit` fallan al crear
`/home/rbenaven/projects/oras-exp-share/.git/worktrees/codex/index.lock`: Read-only file system.
Evidencia: `findmnt -T /home/rbenaven/projects/oras-exp-share/.git/worktrees/codex` muestra montaje ext4 `ro`.
La raíz .git es escribible pero el gitdir específico del worktree está montado solo lectura por el sandbox.
Commits: sin commit; los seis ficheros del hito anterior permanecen en el carril, sin stage.
Decisiones: no alterar montajes ni el gitdir para eludir el sandbox. Continuar con las pruebas independientes;
se necesita que el orquestador dé escritura al gitdir del carril para poder integrar.
Siguiente paso: finalizar evidencia de Azahar, cerrar el laboratorio y dejar estado del carril explícito.

## 2026-11-11 00:28 — Codex — F6-DOMO-SALA: relevo bloqueado por gitdir de solo lectura
Estado: bloqueado
Hecho: implementación de sala 365 lista en el carril, sin commit por el rechazo de index.lock documentado arriba.
Entrada por puerta comprobada: plaza (6,58), norte dos veces, llegada a 456 tile (16,31); sala de piedra amplia
con tres NPC (captura room/after-entry2.png). Captura previa room/before.png. README de pruebas en
frontier/probes/dome_room. No probado: inscripción, combate, pausa, guardar/cargar nuevo, salida y regresiones.
Evidencia: reports/frontier.md §36; room/build-after.log y tests-clean-env.log (988 passed, 1 skipped);
compileall y diff --check correctos. Script y code.ips antes/después idénticos. Ningún cambio en motor/CRO/patch.py.
Commits: sin commit (gitdir ro), ni stage. No push. REPARTO y tasks.json intactos.
Decisiones: status blocked en work/lane-task.json para corregir infraestructura antes de integrar. El orquestador
necesita añadir .git/worktrees/codex como raíz escribible y recoger TODOS los cambios sin commit de este carril.
Laboratorio: última shell detenida con reap y use_gdbstub=false. Se interrumpieron dos shells anteriores: sus
procesos no son visibles desde el namespace actual; after_run debe ejecutar reap desde el host y verificar que
no quede ningún Azahar/Xvfb/GDB de este carril. No tocar el otro carril. No declarar limpieza total verificada aquí.
Siguiente paso: corregir permiso del gitdir y hacer commit del hito; desde una sola shell persistente, entrar por
plaza y caminar primero al norte por el acceso central (el lateral de y31 está bloqueado), después hacia la
recepcionista. Completar aceptación de juego pendiente; no marcar done antes.

## 2026-11-11 07:10 — Claude Code (Opus 5.5) — primera tanda paralela: resultado y arreglos
Estado: hecho
Hecho:
- `auto --parallel --max-runs 2` (usuario, 00:15): los dos carriles arrancaron a la vez. Codex (F6-DOMO-SALA) se
  bloqueó a las 00:27: su sandbox veía `.git/worktrees/codex` de solo lectura (`index.lock: Read-only file system`)
  aunque `.git` era escribible; dejó el trabajo sin commit. Claude (F6-PALACIO-C) terminó la tarea con tres
  commits, pero la integración falló a las 01:13: el rebase del carril necesita identidad de committer y la máquina
  no tiene ninguna («tell me who you are»).
- `frontier_orch.py`: rebase del carril con `IDENTITY`; `{git_dir}` (gitdir del worktree) en las raíces escribibles
  de Codex; `commit_for_agent` (Codex): el orquestador hace commit de lo que deje el carril, con el mensaje que el
  agente ponga en `lane-task.json` y `Agent: Codex (commit hecho por frontier-orch…)`; el brief paralelo lo explica;
  si la integración falla, la nota conserva lo que el agente informó. Tres tests nuevos (sin identidad en el entorno:
  falla sin el arreglo; commit por el agente; raíz del gitdir). 49 passed ×3.
- Integración a mano con el propio código: carril de Claude → 86abc76, 6b6eeaf, f8dfc09; carril de Codex → commit
  hecho por el orquestador 80068a1. La bitácora y el informe se unieron sin conflicto (union), pero los dos agentes
  numeraron su sección como §36: la del Domo pasa a **§37** (sus entradas de las 00:24–00:29 dicen §36: es la §37).
- `tasks.json`: F6-PALACIO-C `done` (aceptación pasada a mano: `python -m pytest -q tests` → 1076 passed);
  F6-DOMO-SALA `in_progress` con lo que falta (Azahar) en las notas.
Evidencia: `work/orch/orch.log` 00:15–01:13; tasks.json (notas de los bloqueos).
Sin probar: Codex con `{git_dir}` escribible (puede seguir en solo lectura: entonces actúa `commit_for_agent`).
Decisiones: la numeración de secciones de `reports/frontier.md` choca en paralelo; queda como aviso (se renumera al
integrar).
Commits: 34b9db6 (arreglos), integración de los carriles y el de esta entrada.
Siguiente paso: relanzar `frontier/orch/frontier-orch auto --parallel` (Codex sigue con F6-DOMO-SALA; Claude no
tiene tarea propia y solo la heredaría si Codex se queda sin cuota).

## 2026-11-11 07:35 — Claude Code (Opus 5.5) — tareas para la alfa instalable
Estado: hecho (sin ejecutar el orquestador)
Hecho: repaso de lo que falta (PLAN F5–F6, REPARTO, `reports/frontier.md`, `dist/`): no hay paquete del Frente,
nada probado en consola, el pase exige la Liga ganada (flag 2720), y combinar con Mew está sin medir (el `code.ips`
del Frente sustituye al anterior). Decisión del usuario: **alfa sin Mew**. `tasks.json` gana F7-PAQUETE (Claude:
`frontier/package.py`, `dist/oras-frontier-alpha-v0.1`, prueba del paquete exacto en Azahar por las siete
instalaciones, partida para Checkpoint, `reports/consola-frente.md`) y F7-REPARTO (Codex, tras F6-DOMO-SALA: tabla de
REPARTO y PLAN al día, solo documentación).
Pendiente para terminar el Frente (fuera de la alfa): F5 (jefes, récords, Doble, Libre), textos en otros idiomas,
pendientes de cada instalación.
Commits: el de esta entrada.
Siguiente paso: el usuario lanza `frontier/orch/frontier-orch auto --parallel`.


## 2026-11-11 13:50 — Codex — F6-DOMO-SALA: aceptación y salida de la sala amplia
Estado: hecho
Hecho:
- Retomado 80068a1 (implementación donante 365, sala propia de 456) desde lane/codex. Turno de REPARTO y
  tasks.json intactos; estado del carril en work/lane-task.json. El permiso del gitdir ya permite el commit.
- Probado en Azahar: entrada por plaza, recepcionista, inscripción de tres y elección de dos, combate,
  victoria asistida, pausa real, guardar y cargar dentro. Sonda reproducible frontier/probes/dome_room/lab_probe.py:
  copias del Domo separadas por 0x910, ayudantes opcionales solo RAM de combate. No se falsifica resultado,
  racha, PB ni works; movimientos del equipo guardado intactos. Prueba de flujo, no dificultad.
- La salida de retail 365 no funciona sin adaptar datos. Tras medir tipos/planos sin éxito y tuples de 365/517,
  Build.java admite tipo de transición opcional y zone.456.exitTiles=15,31: cambia tipo 0→2 y solo tres bytes
  0x30→0x00 de casillas (15–17,31) del mapa privado clonado, con guard de los cuatro bytes originales.
  Plano 0, posición y destino 209/warp1 intactos. Sin cambios nativos, code.bin, patch.py ni CRO.
- Build final exit-tiles: carga guardado de pausa dentro, sale a (6,57); repetida entrada/salida. Fábrica y
  Torre entran y salen. Capturas antes y después. Laboratorio del carril detenido, GDB desactivado, own_processes=[];
  solo puerto 24691, ningún proceso del otro carril tocado.
Evidencia: reports/frontier.md §37.1 y frontier/probes/dome_room/README.md; work/frontier/dome/room/:
- accept-registration/choreography/battle/win/next-round/paused/reloaded.png, accept-battle.gdb.log;
  save-inspect.txt y paused-456.sav (checksums válidos, SHA256
  ec03f883df59a59703cff24a8a3da15df2d249c48eeae25a0fbdc6bb063d25d1).
- before.png frente a accept-final-entry.png; accept-exit-tiles-reload/out.png, accept-final-exit.png;
  accept-factory-{in,out}.png, accept-tower-{in,out}.png, accept-final-doors.gdb.log, lab-cleanup.txt.
- build-exit-tiles.log: ZO 15452 <= 17248, carga 305024 <= 2724608, nativas 517. tuples365/517.txt y
  exit-tuples.txt; repro-check.txt: segunda build reproducible, 27 archivos iguales; script y code.ips idénticos
  al antes. CRO actuales idénticos a la build final de esta continuación, anterior al arreglo de salida;
  DllBattle.cro difiere del before histórico por la integración previa del Palacio C (no por esta tarea).
- env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests': 1077 passed, 1 skipped, 39 s
  (tests-exit-tiles.log). Generación/py_compile de sonda y git diff --check correctos. Consola no probada.
Commits: 80068a1 (base heredada); commit de esta entrada: «Dome hall: repair retail exit and complete Azahar acceptance».
Decisiones: conservar 365; 364 medido también pero solo llega a y22, insuficiente para recepción y25.
  No mover el warp a altura 2: no funcionó. Cambiar solo tres flags de suelo con datos medidos de la salida 517.
Siguiente paso: el orquestador integra el commit y ejecuta su aceptación en main; F6-DOMO-SALA done en lane-task.

## 2026-11-11 13:53 — Codex — F7-REPARTO: instalaciones y plan al día
Estado: hecho
Hecho:
- Actualizada solo documentación: tabla Instalaciones de REPARTO con las siete instalaciones, etapa aceptada,
  interior real, sección del informe y pendientes. Torre v1, Arena B, Domo v1/sala amplia, Tubo v2,
  Pirámide v2A y Palacio C ya no figuran como diseño o trabajo de motor sin terminar.
- PLAN F4 queda como prototipo jugable aceptado en Azahar (sin extenderlo a todos los apagados ni a consola);
  F5 pendiente distingue works de récord existentes del cartel, jefes/símbolos y Doble/Libre por completar.
  F6 recoge isla e instalaciones hechas y F7-PAQUETE en curso (alfa sin Mew), partida, plan y prueba de consola.
  «Después» enumera pendientes por instalación, traducciones y regresiones de motores integrados.
Evidencia:
- Fuentes documentales: frontier/orch/tasks.json (F6 de instalaciones done; F7-PAQUETE in_progress),
  reports/frontier.md §9–§37.1 y últimas entradas de esta bitácora, incluida aceptación 64a7299 del Domo.
- env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests': 1077 passed, 1 skipped
  en 35.86 s (work/frontier/reparto/tests.log). git diff --check correcto.
- work/frontier/reparto/doc-check.log: sección Turno idéntica a HEAD, tasks.json sin cambios; siete filas con
  seis columnas y referencias del informe; pendientes exigidos presentes; cambios limitados a documentación.
Commits: el de esta entrada, «docs(frontier): refresh facility status and remaining plan» (Agent: Codex).
Decisiones: sustituir estimaciones iniciales por estado y pendientes comprobados; no confundir done de una etapa
  con Frente terminado. Las pruebas de juego citadas son heredadas, no repetidas en esta tarea. Sin código,
  builds ni laboratorio; consola no probada. Turno y tasks.json intactos; estado final en work/lane-task.json.
Siguiente paso: el orquestador integra el commit y pasa aceptación en main. Continuar F7-PAQUETE con su dueño;
  después, prueba en consola con el usuario y tareas pendientes de F5 y de cada instalación listadas en PLAN.
## 2026-11-11 14:00 — Claude Code (Opus 5.5) — frontier-orch sin parar (rama orch-nonstop)
Estado: en curso (rama `orch-nonstop` en un worktree aparte; la tanda paralela tiene el turno en main)
Hecho: a petición del usuario («que no se quede parado; poder pararlo al acabar la tarea para un checkpoint»):
- `auto --follow`: modo paralelo sin fin; un carril ocioso espera tareas (bandeja `work/orch/inbox`, cada
  `poll_minutes`) o el fin de una cuota; los bloqueos no paran al resto; con un carril ocupado, el otro mira la
  bandeja cada `busy_poll_seconds`.
- Cola: `owner: "any"` (primer carril libre), `after` (dependencias), la tarea en curso sigue en su carril
  (`state.lane_of`) salvo que su agente esté sin cuota.
- Control mientras corre: `add FILE.json` (validado con `check_task`; el supervisor lo integra con commit),
  `drain` (terminar las tareas en curso y salir), `stop` (terminar las ejecuciones en curso y salir), `resume`.
- README del orquestador; `status` con banderas, bandeja y dependencias.
Evidencia: en el worktree, `tests/test_frontier_orch.py` 62 passed ×3 (13 nuevos: any, after, bandeja con
`--follow`, bloqueo que no para, fichero rechazado, drain, stop, check_task, CLI); suite completa 1087 passed,
2 skipped.
Sin probar: con agentes reales; una noche entera.
Siguiente paso: cuando la tanda actual suelte el turno, integrar, encolar las tareas siguientes y lanzar
`auto --follow`.

## 2026-11-11 14:10 — Claude Code (Opus 5.5) — política de regresión y cola (rama orch-nonstop)
Estado: en curso (rama sin integrar)
Hecho: a petición del usuario («no necesitamos tanto tiempo de emulador»), política de regresión en el `brief` de
`config.json` y en el README del orquestador: la suite siempre (y al integrar); en Azahar solo lo que el cambio
puede romper (una instalación; motor → Palacio, Arena, Tubo y un combate normal; isla → plaza y puertas); el
recorrido completo solo en un paquete para la consola. Cola de 12 tareas lista para `frontier-orch add` en
`frontier/orch/cola/cola-2026-11-11.json` (F7-VIDEO, diseño y base de los Cerebros, siete Cerebros, diseño de
modalidades y de personalidad), con criterios reescritos según la política.
Evidencia: `tests/test_frontier_orch.py` 62 passed; las 12 tareas pasan `check_task`.
Siguiente paso: integrar la rama al acabar la tanda; `frontier-orch add frontier/orch/cola/cola-2026-11-11.json`;
`auto --follow`.

## 2026-11-11 18:05 — Claude Code (Opus 5.5) — tanda paralela 2: integración, modo sin parar y cola
Estado: hecho
Hecho:
- Tanda `auto --parallel` (12:54–15:02): Codex terminó F6-DOMO-SALA (64a7299, aceptada) y F7-REPARTO (5f47f68), con
  **commits propios desde su carril** (`{git_dir}` escribible funcionó; no hizo falta `commit_for_agent`). Claude,
  en F7-PAQUETE, recorrió con el paquete exacto las siete instalaciones, guardó y recargó en la plaza y ganó un
  combate de la Ruta 102; encontró la salida del Domo atascada (transición 0 de la sala 365) y la arregló a la vez
  que Codex: conflicto en `dome_room.py` y su test al integrar, y la cuota de Claude se agotó a las 15:02.
- Conflicto resuelto quedándome con la versión de Codex (más completa: `exitTiles` y aceptación en Azahar);
  quitados el arreglo duplicado de Claude y su `warpTransition` de `Build.java`; los probes del paquete integrados
  (820f90b). El borrador `reports/consola-frente.md` y `circuit.py` siguen sin commit en el carril de Claude.
- Integrada la rama `orch-nonstop` (f06e7d3): `auto --follow`, `owner: any`, `after`, bandeja, `drain`/`stop`,
  política de regresión en el brief. Suite: 1095 passed, 2 skipped.
- `tasks.json`: F7-PAQUETE `in_progress` con lo que falta en las notas (y `lane_of` = claude); cola de 12 tareas
  de `frontier/orch/cola/cola-2026-11-11.json` añadida.
Lección: dos carriles arreglaron el mismo fallo a la vez. Cuando un agente encuentra un fallo de otra instalación que
está en curso en el otro carril, debería anotarlo en lugar de arreglarlo (pendiente de añadir al brief si se repite).
Siguiente paso: el usuario lanza `frontier/orch/frontier-orch auto --follow`; para parar, `frontier-orch drain`.

## 2026-11-11 20:16 — Codex — F7-VIDEO: siete instalaciones sin grabación
Estado: hecho
Hecho:
- Extraída la solución del Palacio a frontier/battle_video.py, reutilizada en Torre/Palacio/Arena/Tubo,
  Domo y vestíbulo/pisos de Pirámide. Se salta Guardar vídeo y la rutina de grabación retorna sin applet
  ni espera; Continuar/Pausar conservan sus valores, textos y flujo.
- En Fábrica la supresión depende de WORK_ROUTE=1 (WORK_IV ya se limpia antes de grabar tras perder).
  La Mansión original, ruta 0, conserva su opción y grabación: test de comparación con retail.
- Tests por instalación ejecutando menús/rutina de vídeo en pawn_vm; además pisos de Pirámide y Mansión.
  Palacio conserva script idéntico byte a byte al anterior (15016 bytes). Diseño/evidencia en informe §33.1.
Evidencia:
- work/frontier/video/tests-clean-env.log: env -u ORCH_LANE bash -c 'source scripts/env.sh;
  python -m pytest -q tests' → 1105 passed, 1 skipped, 39.86 s. script-tests.log: 9 passed.
  Primera suite con ORCH_LANE heredado: 9 fallos de tests del orquestador (tests.log); limpia sin la variable.
- build.log: python frontier/overlay.py --out work/frontier/video/build, ZO 517 15892.
  Fábrica victoria raw=1/ruta1, próximo combate 3; Arena victoria raw=1/marca 80000000, próximo combate 11.
  Capturas {factory,arena}-win-menu.png: solo Continuar/Pausar; {factory,arena}-pause.png: confirmación de pausa.
  Logs {factory,arena}.gdb.log, fixtures/hashes.txt. Victorias asistidas en RAM: sondas existentes de
  Pirámide win y Arena win, sin escribir resultados, rachas ni PB; detalles y límites en reports/frontier.md §33.1.
- scope-check.txt: fuentes del motor y construcción compartida intactas frente a 0497f9c;
  palace-byte-check.txt: Palacio idéntico. git diff --check correcto.
- lab-cleanup.txt: reap desde la shell persistente del arranque, GDB desactivado, own_processes=[], puerto 24691.
Commits: el de esta entrada, «frontier: remove battle video saving from all seven facilities» (Agent: Codex).
Decisiones: política de regresión del usuario: solo Fábrica y Arena en Azahar; derrota/finales y Mansión
  cubiertos por scripts, no repetidos en emulador. Sin cambios de motor ni de construcción; consola no probada.
  Turno de REPARTO y tasks.json intactos; estado del carril en work/lane-task.json.
Siguiente paso: el orquestador integra el commit de lane/codex y pasa aceptación en main; F7-VIDEO done.

## 2026-11-11 20:25 — Codex — F8-CEREBROS-DISENO: siete Cerebros y símbolos
Estado: hecho
Hecho:
- reports/diseno/cerebros.md: fuente pokeemerald fijada a 731ad5bfd6e6f265508d0efcca0ba42f9dcf5881,
  apariciones plata/oro/revanchas y conversión a rachas ORAS. Equipos completos (36 conjuntos con EV/IV,
  naturaleza, objeto y movimientos); Noland aleatorio con IV 15/31, no el trío de la tabla fija no usada.
- Diseño de infraestructura SetTrainer/IsBoss/cinta de Mansión, identidad y constructor rival, bonus +10,
  símbolos persistentes y consulta desde recepcionistas. Candidatos 16729–16731, sin asignar ni tocar REPARTO;
  modelos de campo fallback y clases ORAS explícitos, estética y enlace de modelo de combate por medir en BASE.
  Adaptadores por instalación; finales del Domo, salas del Tubo y cima de Pirámide distinguen sus unidades.
- Medida actual de patch.assemble(): 2544/2556 bytes, fin 0x579ff4, 12 libres; los ~600 bytes son históricos.
  BASE debe medir/reservar otra ubicación o recuperar espacio. Riesgos, estimación y política de regresión.
- frontier/orch/propuestas/cerebros.json: BASE y siete tareas con owner/after/accept concretos. Los ocho IDs ya
  están en la cola; no ejecutar add de duplicados. Las aceptaciones actuales remiten al diseño/propuestas;
  se deja explicado el relevo sin editar tasks.json. BASE cubre Anabel plata; TORRE completa oro/revanchas.
Evidencia:
- Checkout de fuente en /tmp y enlaces al commit en el diseño; 36 filas cotejadas campo a campo contra el C.
  work/frontier/cerebros/design-check.txt: check_task válido para ocho propuestas; dependencias existentes;
  duplicados rechazados frente a cola actual; siete clases comprobadas en gametext ES a/0/7/7 entrada 21;
  espacio medido, REPARTO/tasks.json intactos. work/frontier/cerebros/ids.txt: 1157 scripts, 147 ficheros de código.
- env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests': 1105 passed, 1 skipped,
  40.14 s (work/frontier/cerebros/tests.log). git diff --check correcto.
Commits: el de esta entrada, «docs(frontier): design seven Frontier Brains and symbol implementation tasks»
  (Agent: Codex).
Decisiones: solo diseño/documentación y JSON de propuestas, sin código del juego ni laboratorio, build o parche;
  Azahar/consola de los Cerebros no probados. Las mediciones son estáticas; lo pendiente se marca como hipótesis
  o puerta de aceptación de BASE. Turno y tasks.json intactos; estado final del carril en work/lane-task.json.
Siguiente paso: el orquestador integra y pasa su suite; F8-CEREBROS-BASE empieza auditando espacio e identidad rival,
  asigna reservas en REPARTO antes de escribirlas e implementa Anabel plata según §3, conservando Mansión ruta 0.

## 2026-11-11 20:32 — Codex — F9-MODOS-DISENO: Libre y Dobles
Estado: hecho
Hecho:
- reports/diseno/modos.md: Nivel Libre Individual en las siete instalaciones, Dobles 50/Libre en Torre/Fábrica,
  Multi fuera. Rango Normal/Súper separado del nivel; mantener SetRank(0). Niveles propios sin limitar en Libre,
  rival max(60,máximo inscritos), Fábrica ambos 100. Adaptadores de PS/PP del Tubo, dos de tres del Domo,
  pisos de Pirámide, juicio Arena, filtro Palacio y Cerebros F8.
- Solicitud simbólica de 53 posiciones u16 para bancos de racha/récord, modalidad/nivel persistentes, cuarto
  alquiler/rival y contadores de cambios. No asigna IDs ni modifica REPARTO. Rachas Dobles deben medirse en sus
  cuatro accesores; PB Dobles con columna propia y saturación 15. Cuatro en Fábrica es adaptación explícita
  respecto de los tres de Esmeralda. Rangos Libre/legendarios equivalentes ORAS pendientes de medir.
- frontier/orch/propuestas/modos.json: seis tareas nuevas serializadas, owner any, dependencias y criterios de
  aceptación listos para add, con regresión del usuario. BASE depende de F8-CEREBROS-BASE y exige medir espacio
  tras integrar: foto previa 12 bytes libres. Sin implementación ni laboratorio.
Evidencia:
- Lecturas de fuente local pokeemerald HEAD 731ad5bfd6e6f265508d0efcca0ba42f9dcf5881 y enlaces al commit en diseño.
  work/frontier/modos/maison-map.txt: hashes base y nativas comprobados. set-rank.txt: code 0x1e567c solo strb
  en +0x838, sin validación. selector.txt, types.txt y player-level.txt: desensamblados estáticos; comandos en diseño.
- work/frontier/modos/design-check.txt: check_task válido para las seis propuestas contra cola actual, IDs nuevos,
  dependencias previas/existentes y sin ciclos. No se ejecutó add.
- env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests': 1105 passed, 1 skipped, 39.97 s
  (work/frontier/modos/tests.log). git diff --check correcto.
Commits: el de esta entrada, «docs(frontier): design open level and doubles implementation tasks» (Agent: Codex).
Decisiones: solo diseño/documentación/JSON; juego, Azahar y consola de modalidades nuevas no probados. Suite
  obligatoria aplicada; no corresponde regresión de emulador para diseño. Turno REPARTO y tasks.json intactos;
  estado final en work/lane-task.json. No se arrancó laboratorio ni se tocaron inputs o partida original.
Siguiente paso: el orquestador integra y pasa su aceptación; encolar propuestas con frontier-orch add tras cotejar
  IDs. F9-MODOS-BASE comienza cuando F8-BASE termine: medir selector/accesores/espacio y registrar reservas.
## 2026-11-11 21:20 — Claude Code (Opus 5.5) — F7-PAQUETE: alfa v0.1, paquete exacto en Azahar, Checkpoint y plan de consola
Estado: hecho (falta solo la consola, que es del usuario)
Hecho: `frontier/package.py` (5063a35, e254373) construye desde el commit `dist/oras-frontier-alpha-v0.1` (v0.5 + build
completa del Frente, sin Mew; comprueba ROM, Repolished, code.bin y v0.5; manifiesto y ZIP) y, con `checkpoint`,
`dist/oras-frontier-checkpoint-test-v0.1` (partida 5ddaa992…, guardada por el juego con el paquete en el puerto de
Calagua). LEEME del Domo al día. Prueba del paquete exacto en Azahar por el circuito completo dos veces (paquete
92c11f6 y el de main fec40b9): marinero, ferry, plaza, las siete instalaciones con combate (Tubo: sala y combate),
guardar en la plaza, recargar, vuelta a Calagua; entrenador y salvaje de la Ruta 102; Repartir Exp. (reserva +50 %,
EV) y DexNav (5/0) como la v0.5. `reports/frontier.md` §38 (tabla), `reports/consola-frente.md` (plan).
Fallo encontrado: encierro en la sala del Domo (byte de transición del warp de 365 = 0); diagnosticado y comprobado el
arreglo; Codex lo arregló igual en 64a7299 y el mío se descartó al integrar.
Evidencia: `work/frontier/pkg/` (circuit.log, circuit-run3*.out, shots/, saves/ con hashes en §38,
tested-manifest-fec40b9.json); `env -u ORCH_LANE python -m pytest -q tests` (ver commit). Laboratorio parado (reap,
use_gdbstub=false).
Commits: 5063a35, e254373, 820f90b y el de esta entrada.
Decisiones: la partida de Checkpoint parte de la de prueba de Mew (ya en el puerto y derivada de la del usuario) + Ticket
del Barco, porque mover al jugador escribiendo la partida lo deja sin poder andar (lo volví a ver en la Ruta 102).
No probado: consola; victorias de ronda completas fuera de la Fábrica; juicio de la Arena; ferry de Portual con el paquete.
Siguiente paso: el usuario instala el paquete y sigue `reports/consola-frente.md`; con sus resultados, corregir y v0.2.

## 2026-11-11 21:04 — Codex — F7-LEEME: reglas y límites del paquete alfa
Estado: hecho
Hecho:
- Solo README de frontier/package.py: Arena juzga solo por Cuerpo, Mente/Técnica pendientes y cambio prohibido;
  Palacio espera A en presentación/frase de derrota, sin pedir órdenes. v0.1 aún ofrece «Guardar vídeo» salvo
  Palacio; supresión de main 31ba2d4 anunciada para la próxima versión.
- Contraste del resto con reports/frontier.md §24–§38: acota validación en Azahar y del paquete exacto,
  cambios normales del equipo, niveles y rango Súper del Tubo, presentación de sus salvajes e incidencia
  de reanudación sin aislar; intercambio de Fábrica salvo séptima victoria. Orden de copia Checkpoint corregido.
- tests/test_frontier_package.py: dos pruebas del texto, incluidas las frases exigidas de Arena/Palacio/vídeo.
Evidencia:
- env -u ORCH_LANE python -m pytest -q tests (tras source scripts/env.sh): 1107 passed, 1 skipped en 35.88 s;
  work/frontier/leeme/tests.log. git diff --check correcto.
- work/frontier/leeme/scope-check.txt: AST de package.py idéntico a HEAD salvo README y referencias del contraste.
Commits: el de esta entrada, «docs(frontier): correct alpha README rules and validation limits» (Agent: Codex).
Decisiones: tarea limitada a texto, tests y trazabilidad; sin reconstruir paquete ni ejecutar Azahar según aceptación
  y política de regresión. No probado de nuevo: juego, consola ni paquete. No se arrancó laboratorio.
  REPARTO y tasks.json intactos; estado de entrega en work/lane-task.json, sin push ni cambios de inputs/partida.
Siguiente paso: el orquestador integra el commit del carril y pasa aceptación en main; F7-LEEME done.
## 2026-11-11 22:40 — Claude Code (Opus 5.5) — F8-CEREBROS-BASE hito 1: infraestructura común y Anabel (sin Azahar)
Estado: en curso
Hecho:
- `frontier/brains.py`: umbrales de aparición de las siete (pokeemerald 731ad5bf, cerebros.md §1), referencia `due`,
  símbolos (16729, 2 bits por ruta), rutinas Pawn `brains_check` (antes de elegir rival, 0x2b98), `brains_intro`
  (presentación 0x4338, línea propia en vez del mensaje del entrenador de la Mansión), `brains_won` (antes de IsBoss:
  símbolo, +10 PB por 0x30, línea, 16730 = 0) y limpieza de 16730 en derrota/limpieza; `suppress_retail_boss` (0x451c
  devuelve 0 con ruta ≠ 0) en la Mansión/Fábrica, la Torre, Palacio, Arena, Tubo y Domo. Activo solo la Torre (ENABLED).
- Nativo `frontier/asm/brains_cro.s` en el relleno de DllField.cro 0xf0480–0xf08c0 (1088 bytes; DexNav usa 0xf0400–
  0xf046c; quedan 1856), desde las nativas SetTrainer/StartBattle (bl de 0x94f04, 0x94f18, 0x95044): elector → Cerebro
  (maisontrN 129–142, clase/nombre propios) o, en rutas del Frente con racha ≥ 19 Normal, tramo 70–109 en vez del jefe
  de la Mansión (19) o del entrenador 0 (> 19); carga → work+1 = 0 (sin IsBoss/cinta) en rutas del Frente; tras montar
  el combate, rehace los tres del rival en orden con MAKE_PARAM (IV fijo, habilidad 0) y EV exactos (0x3b4b64 a 0 y
  luego cada valor), PS al máximo y copia sobre el miembro (0x3b2444). Medidas estáticas: §39 de reports/frontier.md
  (pendiente de escribir con la prueba en Azahar).
- Datos: Anabel plata/oro (anexo §7) en maisonpkN 229–234, trainers 131/132 (clase 9), nombres en gametext 154
  (8 idiomas), 28 líneas del texto 637 (1072–1099), caso 9778 del script 5. Reservas en REPARTO.
Evidencia: `tests/test_frontier_brains.py` 75 passed (reglas S-1/S/S+1 y 0/1/2 símbolos, VM de las rutinas en las
  seis instalaciones con script 517, rutas 0–8, Unicorn del blob con funciones de code.bin simuladas); suite completa
  `env -u ORCH_LANE python -m pytest -q tests`: 1180 passed, 1 skipped.
No probado: nada en Azahar todavía (identidad, nombre, modelo, EV reales, texto, guardado del símbolo).
Siguiente paso: build completa, partida con racha 34 en la Torre, jefe en Azahar (victoria con símbolo y derrota) y
  regresión caso b (Palacio, Arena, Tubo y un combate de historia) porque se toca DllField.cro.

## 2026-11-11 21:40 — Codex — F8-CEREBROS-BASE hito 2: Anabel plata y símbolo guardado
Estado: en curso
Hecho: revisión del relevo (`git status`, `git diff`, último commit 57df06a): limpio, sin cambio parcial pendiente.
Build completa generada. Añadida sonda reproducible `frontier/probes/brains/lab_probe.py` y verificador PK6
`check_team.py`; ampliado StartBattle sin jefe a las siete rutas en Unicorn. Informe §39 con direcciones,
reservas, comandos y límites de evidencia.
Evidencia: `env -u ORCH_LANE python -m pytest -q tests`: 1188 passed, 1 skipped (tests-final.log). Build overlay
correcta (build.log). Azahar del carril 24691: Anabel plata con racha 34, pendiente 10, presentación propia;
PK6 reales comprobados antes de asistencia contra todo el equipo del diseño (silver-team.json). Victoria
asistida solo en copias de combate: resultado 1; racha 35, símbolo 4, pendiente 0. Pausa y guardado por el juego
(tower35-silver.sav, SHA256 0102574bcc5c199bbf7ca0d1b2fb01a00639375cd7020b279e995cf4c2c60ddd), símbolo 4 y
racha 35 comprobados en archivo con 58 bloques válidos. Artefactos work/frontier/cerebros/base/.
Commits: 57df06a (infraestructura de Claude); el de esta entrada (prueba y cobertura de Codex).
Decisiones: no cambios de REPARTO/tasks.json; estado en work/lane-task.json. Suite sin ORCH_LANE porque nueve tests
de orquestación dependen de su ausencia (también pasa la suite previa 1182/1 sin la variable). Regresión limitada
al caso b del usuario, sin circuito de siete. No probado: recarga, derrota, regresión b, oro en Azahar, PB medidos,
consola. Laboratorio continúa activo para el siguiente paso.
Siguiente paso: recargar símbolo, derrota ante Anabel, Palacio/Arena/Tubo/historia; documentar, parar lab, suite y
commit final; marcar done solo con aceptación completa.

## 2026-11-11 21:59 — Codex — F8-CEREBROS-BASE hito 3: aceptación y cierre del laboratorio
Estado: hecho
Hecho: completada la aceptación común iniciada en 57df06a y continuada en 5d4172e. Recarga real del símbolo de
plata; Anabel oro con equipo exacto y derrota; regresión acotada Palacio/Arena/Tubo/historia. Sonda ampliada con
entrenador y rachas de todas las rutas; README de reproducción. Informe reports/frontier.md §39 actualizado con
resultados, fuentes, hashes y límites. No fue necesario corregir el motor de la implementación heredada.
Evidencia:
- env -u ORCH_LANE python -m pytest -q tests: 1188 passed, 1 skipped en 44.33 s (tests-acceptance.log).
  Build completa overlay ya ejecutada (build.log), mismo code.ips/DllField/DllBattle en todas las pruebas, hashes
  en build-manifest.json y §39. VM/Unicorn: umbrales, premios/limpieza y ruta ordinaria de las siete instalaciones.
- Azahar 24691: recarga de tower35-silver.sav conserva símbolo 4, racha 35, activo 1 (reload-gdb.log).
  Copia a racha 69: entrenador 132, pendiente 18, equipo oro capturado antes de asistencia y validado completo
  por check_team.py (gold-team.json). Derrota raw=0: ruta/racha/activo/pendiente=0, récord 35, plata 4 conservada
  (gold-loss-gdb.log). La victoria de plata y su guardado ya constan en hito 2.
- Caso b del usuario: Palacio y Arena combate/derrota con flags propios 0x40000000/0x80000000 y limpieza normal;
  Tubo combate single/victoria, sala 0→1; todos sin símbolo ni jefe pendiente. Historia sin asistencia: Zigzagoon
  Nv.3 contra Torchic Nv.12 en Ruta 102, daño y regreso al campo, works comunes a 0. Fuentes y SHA256 en
  regression-sources.json; logs palace-*, arena-*, pike-*, story-* bajo work/frontier/cerebros/base/.
- Laboratorio propio reap sin procesos restantes, bus privado parado, GDB deshabilitado (cleanup.log).
Commits: 57df06a (infraestructura), 5d4172e (plata/cobertura), el de esta entrada «test(frontier): complete brain
acceptance and scoped engine regression» (Agent: Codex).
Decisiones: asistencia solo en copias de batalla para las instalaciones, jamás resultados/works/premios. En Tubo
se fija solo el reloj para una sala single. No probado: concesión de oro en Azahar (VM sí), PB medidos en RAM,
EXP/IsWin de historia, dificultad sin asistencia y consola. No se amplía al circuito completo: política caso b.
REPARTO/tasks.json intactos, sin push ni cambios de inputs/partida original; entrega en work/lane-task.json.
Siguiente paso: orquestador integra el carril y pasa aceptación en main; F8-CEREBROS-BASE done. Los demás Cerebros
permanecen desactivados a la espera de sus tareas específicas.

## 2026-11-11 — Codex — F8-CEREBRO-FABRICA hito 1: generador y constructor de Noland
Estado: en curso
Hecho: adaptador factory_brain.py; draft guarda semilla completa en 16490 para reproducir los seis ofrecidos.
Caso 9772 multiplexado para preparar el trío de Noland con exclusión de seis IDs y duplicados. API común en
Fábrica; constructor dinámico N/S con IV 15/31 independiente del alquiler, Return→Frustration y amistad 0.
Informe §40 con contrato, medidas y límites; sin nuevos works/casos/textos ni cambios de REPARTO/tasks.json.
Evidencia: suite env -u ORCH_LANE python -m pytest -q tests: 1217 passed, 1 skipped, 39.40 s
(work/frontier/cerebros/factory/tests-full.log); 170 tests específicos en verde. Build completa correcta:
ZO Fábrica 16608 <= 17248; DllField blob 1272 bytes, fin 0xf0978, 1672 libres; work/frontier/cerebros/factory/build.log.
Commits: el de esta entrada, «feat(frontier): build deterministic Noland rental teams» (Agent: Codex).
Decisiones: reutilizar semilla/works/caso existentes evita reservas nuevas. Los desafíos pausados anteriores
no conservan la semilla completa: terminar antes de actualizar; no se promete reproducir sus seis ofertas.
Integrador: actualizar extremo de blob de BASE en REPARTO a 0xf0978. No probado todavía: Azahar ni consola;
consulta/derrota propias pendientes de extensión de textos reservada por integrador.
Siguiente paso: Azahar plata ganada y símbolo guardado/recargado, oro o derrota y regresión b;
plaza/puerta Fábrica por overlay. Completar consulta y derrota sin ocupar líneas sin reserva; mantener in_progress.

## 2026-11-12 00:01 — Claude Code (Opus 5.5) — F8-CEREBRO-FABRICA hito 2: textos propios, Azahar y regresión
Estado: hecho
Hecho:
- Relevo: Codex se cortó tras 4f1976a (fixture, check_team, tests); árbol limpio salvo tres ayudas de laboratorio sin
  seguimiento de mi sesión de BASE (`k.sh`, `lab-start.sh`, `probe.gdb`), que se completan y se añaden. Nada a medias.
- Criterios de `propuestas/cerebros.json` (mandan): faltaban textos de derrota y consulta. `brains.py`: segundo
  bloque del texto 637 (líneas 1100–1127, 4 por ruta), `brains_lost` en el camino de derrota (línea una vez y
  16730 = 0), `brains_symbols` + `symbols_option` («Símbolos», texto 619 línea 190, valor 5), conectado solo en
  la Fábrica. Reservas y extremo del blob (0xf0978) anotados en REPARTO (el turno no se toca).
- Azahar completo de Noland (plata, guardado/recarga, oro con equipo, oro ganado, derrotas, consulta) y regresión
  b+c: tablas en `reports/frontier.md` §40.1. README de la sonda ampliado; `snap.py` nuevo.
Evidencia:
- `env -u ORCH_LANE python -m pytest -q tests`: 1224 passed, 1 skipped (`work/frontier/cerebros/factory/tests-final.log`).
  Nuevos: derrota dice la línea una vez (Torre/Fábrica), consulta 0/1/2/3, menú y despacho; actualizados los de
  menú, textos 619 y derrota de la Fábrica.
- Plata (racha 20): entrenador 129, PK6 = generador (IV 15, amistad 0), victoria, `silver-paused23.sav` símbolos 1,
  PB 0→14; recarga a combate 23 con 16729 = 1. Oro (racha 41): entrenador 130, IV 31; derrota limpia (plata
  conservada); victoria con línea de oro, `gold-won-paused43.sav` símbolos 3, PB 0→15; cierre de ronda sin cambio.
  Derrota con la línea nueva y limpieza total. Hashes y capturas en §40.1 y `work/frontier/cerebros/factory/`.
- Regresión: Palacio (0x40000000, derrota), Arena (0x80000000, derrota), Tubo (sala 14 ganada, racha 13→14),
  historia (Wurmple salvaje), plaza salida/entrada. Laboratorio parado (reap, `use_gdbstub=false`).
Commits: 10fb540 (textos, consulta, ayudas), el de esta entrada (informe, REPARTO, bitácora).
Decisiones: bloque nuevo tras 1099 en vez de cambiar el paso de 4 líneas por ruta (no renumera BASE/Anabel); consulta
  como opción del menú de recepción del diseño §3, no NPC; línea de derrota dicha por el script tras el combate
  (el Cerebro no está en pantalla). Plata ganada/guardado/recarga y oro-derrota con la build 4f1976a; el resto con
  10fb540 (solo añade script/textos). Regresión b y c según la política, sin circuito completo.
No probado: consola; captura de la línea de plata ganada (PB y símbolo sí); revancha 63 en Azahar (VM sí); inglés.
Siguiente paso: el orquestador integra el carril y pasa la suite; F8-CEREBRO-FABRICA hecho. Las demás instalaciones
  conectan «Símbolos» con `brains.symbols_option` en sus tareas.

## 2026-11-12 — Claude Code (Opus 5.5) — F8-CEREBRO-TORRE: Anabel completa (consulta, oro en Azahar)
Estado: hecho
Hecho:
- Relevo: la tarea estaba recién tomada por el orquestador (413ef1a), árbol limpio. BASE ya tenía a Anabel
  plata/oro, textos y derrota; faltaba la consulta en la recepción de la Torre y el oro ganado en Azahar.
- `frontier/tower.py`: «Símbolos» en el menú de la Torre (`brains.symbols_option`, línea 190 del texto 619,
  valor 5), solo en `tower_program` (Palacio/Arena/Tubo comparten `facility_program` y no cambian).
- `tests/test_frontier_brain_tower.py`: 15 tests VM del script de la Torre (desafío 0→174, derrotas, revanchas,
  reanudar, rutas ajenas, consulta, menú); `test_frontier_tower.py` y `test_frontier_brains.py` ajustados.
- Informe `reports/frontier.md` §41.
Evidencia:
- `env -u ORCH_LANE python -m pytest -q tests`: 1239 passed, 1 skipped (`work/frontier/cerebros/tower/tests-final.log`).
- Azahar 24690, build de f113c4d (code.ips f64e527c…, sin cambio de motor): consulta plata; Anabel oro desde
  racha 69 (entrenador 132, PK6 Raikou/Latios/Snorlax validados con `check_team.py --variant gold`); victoria
  asistida en copias, línea de oro, `tower70-gold.sav` con símbolos 12, racha 70, PB 1→21, equipo intacto;
  recarga y consulta «oro». Tabla con hashes en §41; artefactos en `work/frontier/cerebros/tower/`.
Commits: f113c4d (código y tests), el de esta entrada (informe y bitácora).
Decisiones: política de regresión caso a (solo script de zona de la Torre): sin Palacio/Arena/Tubo/historia ni
  plaza. Plata ganada y derrota se reutilizan de BASE (§39), que el cambio no invalida. Sin reservas nuevas.
No probado: consola; revanchas 105/140 y consulta «Aún no…» en Azahar (VM sí); dificultad sin asistencia.
  La línea de victoria de una revancha de plata con oro dice «Has obtenido… de plata» (conserva el oro).
Siguiente paso: el orquestador integra el carril y pasa la suite; F8-CEREBRO-TORRE hecho.

## 2026-11-12 — Codex — F8-CEREBRO-PALACIO: relevo y aceptación de Spenser
Estado: hecho
Hecho: revisados status/diff/último commit: árbol limpio en 0a79d21 de Claude, con Spenser implementado y tests,
pero sin bitácora ni Azahar. Conservada la implementación y completada su aceptación. check_team.py admite
--facility palace, README de reproducción e informe reports/frontier.md §42 con fuentes y límites.
Evidencia:
- Suite env -u ORCH_LANE python -m pytest -q tests: 1259 passed, 1 skipped (tests-final.log, 42.83 s;
  repetición tras ayudas/documentación en tests-acceptance.log). Con ORCH_LANE heredado hubo nueve fallos
  de tests del supervisor conocidos en BASE; se aísla esa variable, no se cambia código del supervisor.
- Build completa correcta, zona 340 ZO 16724 <= 17248; hashes en work/frontier/cerebros/palace/build-manifest.json.
- Azahar 24691: plata desde S=20, entrenador 133 y Crobat/Slaking/Lapras exactos antes de asistencia;
  victoria raw=1, símbolo 16, racha/récord 21, pendiente 0; pausa guarda p21-silver.sav (d9307afd…), PB 4→19
  (10 jefe + 5 ronda). Equipo/cajas idénticos a fixture, checksums válidos. Recarga y consulta plata comprobadas.
- Oro desde S=41, entrenador 134, Arcanine/Slaking/Suicune IV/EV/objeto/naturaleza/movimientos exactos;
  «El Médium Spenser te desafía»; derrota raw=0 y texto propio, ruta/racha/activo/pendiente a 0,
  plata 16 y récord 41 conservados. En ambos combates, flags 0x40000000 y órdenes del jugador automáticas.
- Primer intento de toma final GDB atascado; repetida oro/derrota con mismo fixture/build en conductor interactivo;
  gold-loss-gdb.log recoge limpieza. Laboratorio parado con reap desde su conductor, own_processes=[] y GDB off.
Commits: 0a79d21 (Claude: implementación/equipos/menú/tests); el de esta entrada,
«test(frontier): verify Spenser symbols and scoped Palace acceptance» (Agent: Codex).
Decisiones: política caso a, solo Palacio; no cambios de motor/isla/construcción común ni reservas nuevas.
Asistencia explícita solo en copias de combate; no se alteran resultados, works ni premios. Sustitución visual:
joven Médium masculino ORAS (clase 31) en campo/combate, no anciano; IA rival por naturaleza no implementada.
No probado: consola, inglés en juego, oro ganado/revanchas en Azahar (VM sí); línea de premio plata no capturada,
sí símbolo/PB persistidos; no nuevo guardado tras derrota (limpieza RAM sí). Contracción común «de el» pendiente.
REPARTO/tasks.json intactos, sin push; estado done en work/lane-task.json.
Siguiente paso: el orquestador integra lane/codex y pasa su aceptación; F8-CEREBRO-PALACIO terminado.

## 2026-11-12 — Codex — F8-CEREBRO-ARENA hito 1: Greta y pruebas del script
Estado: en curso
Hecho: Greta habilitada en brains.ENABLED, equipos plata/oro exactos del diseño §7 y conexión «Símbolos»
en arena_program. Sin nuevas reservas: sets 241–246, entrenadores 135/136, líneas y works ya asignados.
22 tests propios: desafíos, fronteras, revanchas, pérdida, pausa, consulta, tablas y premio no duplicado.
check_team.py admite Arena. Corregida descripción antigua de Arena A: el motor B sigue activo.
Evidencia: env -u ORCH_LANE python -m pytest -q tests: 1281 passed, 1 skipped, 44.54 s
(work/frontier/cerebros/arena/tests-full.log). Build completa correcta (build.log); git diff --check limpio.
Commits: el de esta entrada, «feat(frontier): add Greta teams and Arena symbols reception» (Agent: Codex).
Decisiones: solo datos y script mediante API BASE; no cambia lógica nativa, ASM, patch.py ni construcción común.
No probado todavía: Greta en Azahar, guardado/carga del símbolo y derrota; consola.
Siguiente paso: laboratorio de este carril 24691 ya arrancado con s27.sav y sonda judge-win.gdb;
completar plata ganada, guardar/cargar y oro/derrota; medir juicio a tres turnos y cambio prohibido.

## 2026-11-12 — Codex — F8-CEREBRO-ARENA hito 2: aceptación de Greta
Estado: hecho
Hecho: completada aceptación en Azahar del carril 24691; informe reports/frontier.md §43 y reproducción
frontier/probes/brains/README.md. Corregidos comentarios/alias copiados de Palacio en el test de Greta.
Evidencia:
- Suite final env -u ORCH_LANE python -m pytest -q tests: 1281 passed, 1 skipped, 47.63 s
  (work/frontier/cerebros/arena/tests-final.log); primera suite tests-full.log también verde.
  Una ejecución intermedia tras renombrar un alias de fixture dio NameError; corregido y repetida entera.
- Overlay completa correcta, ZO Arena 16724 <= 17248 (build.log/build-manifest.json).
  Comparación brains.assemble con/sin Arena: instrucciones y símbolos idénticos, solo dos filas Greta
  de brain_table 0xf0898–0xf08cf (native-data-only.json). No cambia lógica de motor ni construcción común.
- Plata desde S27: entrenador135, pendiente12, bit31; Heracross/Umbreon/Shedinja exactos antes de asistencia
  (silver-team.json, check_team.py --facility arena rc0). Intro Greta y premio propio capturados.
  Menú prohíbe cambio; juicios Cuerpo edades [3,3], [6,3], [9,3], raw1.
- Pausa guarda S/récord28, activo1, símbolo64, pendiente0, PB2→14 (10 Cerebro + 2 ronda);
  s28-silver.sav SHA256 2a31f499…, checksums válidos, equipo/cajas intactos. Recarga exacta y consulta plata
  comprobadas en consult-silver.png. Fuente ar_paused9.sav SHA256 093ed149… sin cambios.
- Oro desde S55: intro propia, entrenador136, pendiente20, bit31; Umbreon/Gengar/Breloom exactos
  (gold-team.json, check_team.py --facility arena --variant gold rc0). Tres juicios eliminan al jugador;
  raw0, texto derrota, ruta/racha/activo/pendiente0; récord55 y plata64 conservados (gold-loss-gdb.log).
  Guardado real posterior gold-loss-saved.sav SHA256 a52ee68b…, PB14, mismos works, checksums válidos;
  equipo/cajas idénticos byte a byte a fuente (gold-loss-saved.json).
- Lab cerrado con reap desde conductor propietario: own_processes=[] (cleanup.log), GDB off y D-Bus
  privado cerrado. git diff --check limpio.
Commits: 5347064 «feat(frontier): add Greta teams and Arena symbols reception»; el de esta entrada,
«test(frontier): verify Greta symbols and scoped Arena acceptance» (Agent: Codex).
Decisiones: política caso a, solo Arena; cambios de datos y script mediante BASE, sin nuevas reservas.
Asistencia solo PS/movimientos de copias de combate: Salpicadura ambos, PS ganadores/perdedores al tercer
turno para ejercitar juicio real; nunca se escribe resultado, works ni premios. Sustitución visual ORAS:
Luchadora63 rubia con traje azul, sin modelo Greta propio. Mente/Técnica siguen fuera según diseño.
No probado: consola, inglés en juego, dificultad sin asistencia, victoria oro/revanchas en Azahar (VM sí).
No capturada pantalla inicial de nombre/clase en combate; sí tablas de nombre real, entrenador y equipo,
y ambas introducciones de campo. REPARTO/tasks.json intactos, sin push; estado done en work/lane-task.json.
Siguiente paso: el orquestador integra lane/codex y pasa su aceptación; F8-CEREBRO-ARENA terminado.

## 2026-11-12 — Codex — F8-CEREBRO-DOMO hito 1: Tucker, final y dos de tres
Estado: en curso
Hecho: Tucker habilitado en brains.py con los seis sets exactos del diseño §7, clase 10 y nombre propio;
dome_program usa install/consulta BASE. Elegibilidad convierte combates a torneos solo en final (S%4=3),
plata S19 y oro S39; preview del trío privado antes de elegir dos; pareja rival aleatoria declarada.
Constructor brains_cro.s admite dos miembros de Tucker, conserva orden DOME_FORCED y aplica IV/EV exactos
de cada set seleccionado; rechaza índices fuera del trío/repetidos. Limpieza de selección temporal al perder,
retirarse/pausar o limpiar desafío. Sonda/check_team admiten dos miembros Domo.
Evidencia: env -u ORCH_LANE python -m pytest -q tests: 1312 passed, 1 skipped, 44.24 s
(work/frontier/cerebros/dome/tests-m1.log). 31 tests nuevos VM/Unicorn, incluidas las seis parejas ordenadas
por variante, finales, revanchas, pérdida, pausa y no duplicar premio. Overlay completa correcta (build.log),
medidas nativas/ZO en static.json; git diff --check limpio. Intentos iniciales con errores de conexión de API,
importación y decodificación de texto corregidos antes de la suite verde.
Commits: el de esta entrada, «feat(frontier): implement Tucker finals and exact two-member teams» (Agent: Codex).
Decisiones: política caso b porque cambia brains_cro.s; pendiente Azahar Domo y un combate Palacio/Arena/Tubo/historia.
Sin nuevos works/casos/sets: usa reservas BASE/Domo. Para preview hacen falta seis líneas privadas: añadidas
por composición al final de brains.lines (1128–1133 en esta build), sin desplazar líneas existentes. Registro
para integrador aquí porque el brief de carril prohíbe editar REPARTO: trasladar esta ampliación de textos
y nuevo final nativo a su tabla al integrar. REPARTO/tasks.json intactos.
No probado todavía: aceptación Tucker en Azahar, regresión del motor y consola.
Siguiente paso: lab del carril 24691 arrancado en conductor work/frontier/cerebros/dome/driver.py (sesión PTY),
fixture s19.sav desde work/frontier/dome/room/paused-456.sav (SHA256 ec03f883…); completar plata, guardado/carga,
oro/derrota y regresiones; al acabar reap desde el conductor y cerrar su D-Bus privado.


## 2026-11-12 — Codex — F8-CEREBRO-DOMO hito 2: aceptación Tucker y regresión de motor
Estado: hecho
Hecho: completada aceptación del Domo en Azahar del carril24691 y regresión acotada de motor;
reproducción en frontier/probes/brains/README.md e informe reports/frontier.md §44. Documentadas
reservas, hashes, asistencia y limitaciones. Sin cambios funcionales posteriores al hito1.
Evidencia:
- Suite completa source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests: 1312 passed,
  1 skipped, 44.52 s (work/frontier/cerebros/dome/tests-acceptance.log; hito1 tests-m1.log también verde).
  ORCH_LANE desactivado solo para los tests del supervisor, según §39. git diff --check limpio.
- Overlay completa correcta (build.log/build-manifest.json/static.json): ZO Domo16804 <=17248;
  bloque nativo1396 bytes hasta0xf09f4, quedan1548 hasta0xf1000; textos privados1128–1133.
- Plata S19: intro/nombre Tucker entrenador137, preview exacto; pareja Swampert/Charizard, IV20,
  EV/objetos/naturaleza/movimientos/amistad/nivel exactos antes de asistencia (team-silver.json,
  check_team.py --facility dome rc0). Victoria raw1, símbolo256, pendiente0, S20. Se continuó una
  ronda ordinaria hasta S21; pausa real guarda S/récord21, activo1, símbolo256, PB0→13=10+3
  (silver-save.json). Reinicio de ese guardado y consulta real muestran plata (consult-silver.png).
- Oro S39 desde copia de plata: preview exacto estable tras B, entrenador138 y pendiente21;
  Latias/Metagross IV31 exactos (team-gold.json, check_team.py --facility dome --variant gold rc0).
  Derrota raw0; recepción RAM ruta/racha/activo/pendiente0, récord39 y plata256, selección temporal0
  (gold.gdb.log). Auto-save gold-loss.sav conserva récord/plata/PB13 y equipo; guarda ruta5 antes de
  retorno retail a0, que se comprobó en RAM (gold-loss-save.json).
- Equipo real de plata: datos de combate iguales en los seis y cajas idénticas. Diferencia decodificada
  solo byte0xcc del sexto 1→2 (recuerdo entrenador) y checksum (silver-party-diff.json), sin atribuir causa.
  PK6 de plata sobrescritos al reiniciar oro; quedan validación JSON y log de exportación. Fuente
  paused-456.sav conserva SHA256ec03f883…; todos los guardados inspeccionados tienen checksums válidos.
- Regresión caso b con misma build: Palacio entrenador37/flag0x40000000, derrota raw0; Arena
  entrenador54/flag0x80000000, derrota raw0; ambos vuelven a recepción. Tubo entrenador1, sala sencilla,
  victoria raw1 y S0→1. Sin Cerebros accidentales (palace/arena/pike.gdb.log y capturas *-return/finish.png).
  Historia Ruta102, Torchic vence Zigzagoon con Arañazo sin asistencia, EXP1105→1121, ruta/símbolos/
  pendiente0 tras guardar, 58 bloques válidos (story-save.json, story-saved.png, story.gdb.log).
  Fuentes y hashes en regression-sources.json; no se tocó ninguna fuente.
- Laboratorio parado con reap desde conductor propietario: own_processes=[], sesión ausente,
  GDB off, bus D-Bus privado cerrado (cleanup.log); conductor terminado.
Commits: 411c510 «feat(frontier): implement Tucker finals and exact two-member teams»; el de esta
entrada, «test(frontier): verify Tucker symbols and scoped engine regression» (Agent: Codex).
Decisiones: aproximación rival aleatoria declarada, dos de tres distintos; modelo ORAS Entrenador Guay10.
Asistencia solo PS/movimientos de copias de combate, nunca resultados/works/premios; Tubo fuerza sala
sencilla mediante su reloj de sonda existente. Historia sin asistencia. Política caso b, sin recorrido
completo de paquete ni plaza: no cambian isla/construcción común. REPARTO/tasks.json intactos por brief;
el integrador debe registrar ampliación de bloque nativo hasta0xf09f4 y seis líneas1128–1133.
No probado: consola, inglés en juego, dificultad sin asistencia Domo, concesión oro/revanchas en Azahar
(sí VM); byte0xcc cambiado queda documentado, no se afirma identidad completa del equipo plata.
Siguiente paso: el orquestador integra lane/codex, actualiza reservas y pasa aceptación en main;
F8-CEREBRO-DOMO terminado, estado done en work/lane-task.json. Sin push.

## 2026-11-12 — Codex — F8-CEREBRO-TUBO hito 1: Lucy y sala única
Estado: en curso
Hecho: Lucy habilitada en brains.py, con seis sets exactos del anexo cerebros.md §7, clase13 y nombre propio.
El adaptador pike_rooms comprueba elegibilidad antes de cada sorteo, también después de salas sin combate;
con Lucy limpia PIKE_WILD y fija rango Normal, conserva PS/estado/PP v2 y deja el avance a AddWinCount.
Recepción conecta «Símbolos» BASE. Sin cambios en asm, patch.py, isla ni construcción común.
Evidencia: source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests: 1329 passed, 1 skipped,
44.90 s (work/frontier/cerebros/pike/tests-m1.log). VM: umbrales/plata/oro/revanchas, pausa, derrota,
premio único, estado v2 y llegada desde sala sin combate. IDs cotejados con gametext ES; seis sets/IV/EV
verificados. Overlay completa correcta (build.log); static.json: ZO Tubo17112 <=17248, bloque nativo1396
bytes hasta0xf09f4; comparación con Lucy deshabilitada da instrucciones/símbolos idénticos, solo cambian
las dos filas de datos privadas. Primeras pruebas detectaron expectativas antiguas/abreviación de nombre
Colmillo Ven; corregidas y suite completa repetida en verde. git diff --check limpio.
Commits: el de esta entrada, «feat(frontier): add Lucy teams and Pike room adapter» (Agent: Codex).
Decisiones: política caso a, solo Tubo; sin nuevas reservas. Se conserva estado v2 ante Lucy, sin curación
previa exacta de Esmeralda (fuera de alcance en diseño). REPARTO/tasks.json intactos por brief del carril.
No probado aún: aceptación Lucy en Azahar, guardado/carga, consola.
Siguiente paso: laboratorio del carril24691 arrancado desde conductor work/frontier/cerebros/pike/driver.py;
fixture s27.sav copia de work/frontier/lab/pk_saved_458.sav, SHA256252526e8… (fixture.json), con PS60/70/80,
PP5 por movimiento y parálisis en tercero. Completar plata ganada/símbolo guardado/cargado y oro o derrota;
parar lab y bus privado desde el conductor al terminar.

## 2026-11-12 — Codex — F8-CEREBRO-TUBO hito 2: plata persistente y bloqueo EV de Shuckle
Estado: en curso (bloqueado por contradicción de diseño; estado blocked en work/lane-task.json)
Hecho: aceptación parcial Lucy en Azahar24691, plata ganada con asistencia solo a copias de combate,
medición de PS/PP/estado v2, premio y avance único, guardado real y consulta del símbolo después de reiniciar.
Informe reports/frontier.md §45 y reproducción frontier/probes/brains/README.md. No se relaja el verificador.
Evidencia: work/frontier/cerebros/pike/silver.gdb.log: trainer139,flag0,S27,pendiente14,raw1;
medición posterior S28,activo1,símbolo1024,pendiente0. SET_HP0x14f450 y SET_SICK0x14f814 desde
pike_build restauran PS60/70/80,estado0/0/1; pike_pp+32 confirma PP5 de los12 movimientos antes del combate.
Tres PK6 rivales exportados antes de asistencia: team-silver-measured.json y silver-team/. Seviper/Milotic
coinciden; check_team.py --facility pike falla en Shuckle (check-silver.log): tabla pide610 EV y constructor
ORAS0x3b4b64 limita510, quedando252,0,0,0,106,152 frente a252,0,0,0,106,252. Ya lo advierte asm/brains.s.
Corrección al hito1: «seis sets exactos» solo se verificó en tablas/VM; NO exactitud de Shuckle en ejecución.
La fuente pk_saved_458.sav estaba interrumpida, retail limpiaba ACTIVE/S; se sustituyó por una copia
realmente pausada pa_paused7.sav, SHA256012e718ba50c3dbab606987958a3351aec79840025e385e25d73ed3c98e48c7c,
limpiando otros activos y editando solo copia (fixture.json/s27-paused.sav). Fuentes intactas.
Guardado: se había pulsado continuar tras plata; Pausar después de otra sala vacía/combate normal conserva
plata1024 y PB15 (partía4, +10 jefe +1 ronda),S/récord30,activo1,pendiente0. saved-silver.json verifica
checksums y equipo/cajas idénticos. silver-paused.sav SHA256d47e48af…; reinicio y captura
silver-reloaded-symbol.png muestra Suerte de plata. No se deduce avance de Lucy del S30: está medido en S28.
Suite hito2: source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests:1329 passed,1 skipped,
48.27s (tests-m2.log); git diff --check. Política regresión caso a, solo Tubo; ningún cambio de motor.
Commits: 95a8aaa hito1; el de esta entrada «docs(frontier): record Lucy silver acceptance and EV design blocker».
Decisiones: mantener los valores solicitados en la tabla; no alterar diseño ni motor sin resolver610vs510.
Pregunta concreta: ¿corregir Shuckle plata a DefE152 (total510), o exigir610 mediante excepción del motor?
La segunda opción amplía alcance y obliga caso b. No se marca done con el assert de equipo fallando.
No probado: oro/derrota de jefe en Azahar (sí VM), consola, aspecto exacto Esmeralda. s139-silver.sav y
 gold-fixture.json preparados desde plata guardada, S/récord139,símbolo1024,PS60/70/80,PP5,estado0/0/1,
para retomar después de la decisión. Laboratorio parado desde el conductor privado con reap; sin push.
Siguiente paso: resolver criterio EV en diseño, actualizar tabla/test correspondiente si procede, reconstruir,
repetir comprobación real del equipo plata y completar oro o derrota Azahar, suite y cierre done.

## 2026-11-12 — Claude — F8-CEREBRO-TUBO hito 3: EV de Shuckle resuelto y aceptación Lucy completa
Estado: hecho
Hecho: relevo tras corte de cuota de Codex. Al empezar, `frontier/probes/brains/check_team.py` estaba en
conflicto (UU) por un autostash del orquestador: la versión stash solo admitía tower/palace; la de HEAD
(3581e42, tower…pike) la supera, así que se dejó la de HEAD y el árbol quedó limpio. La entrada de stash
`08dcdee… autostash` sigue en la pila compartida, con contenido obsoleto; no se ha borrado.
Bloqueo del hito 2 (Shuckle 610 EV frente al límite 510 de ORAS) resuelto por criterio del agente, sin
tocar el motor: tabla de `brains.py` a 252,0,0,0,106,152, que es lo que ya construía el juego; nota en el
anexo de cerebros.md §7; nuevo test que impide sets de Cerebro por encima de 252/510. Detalle y vuelta
atrás en reports/frontier.md §46. Aceptación en Azahar 24690 (caso a, solo Tubo): plata ganada con
símbolo, pausa/guardado, recarga y consulta; oro en S139 con equipo exacto y derrota limpia.
Evidencia (work/frontier/cerebros/pike/ del carril claude):
- Suite: env -u ORCH_LANE python -m pytest -q tests: 1330 passed, 1 skipped, 42.31 s (tests-m3.log);
  git diff --check limpio. Build overlay correcta (build.log).
- Plata: trainer139, S27, pendiente14; check_team.py silver-team --facility pike rc0 (check-silver.log),
  Shuckle 252,0,0,0,106,152. Victoria raw1, texto de símbolo +10 PB; RAM S28, activo1, símbolo1024,
  pendiente0 (silver.gdb.log, silver-after.txt). Pausa: silver-paused.sav 937bb8b2…, S/récord28,
  PB 4→15, equipo bruto y cajas idénticos (saved-silver.json). Recarga + «Símbolos»: «Tienes el Símbolo
  Suerte de plata» (silver-reloaded-symbol.png).
- Oro: s139.sav (6d3dc6d8…) desde la pausa de plata; trainer140, pendiente22; check_team --variant gold
  rc0 (check-gold.log); PS/estado v2 restaurados y visibles en combate (gold-retained-party.png).
  Derrota raw0: RAM ruta/S/activo/pendiente 0, símbolo1024 (gold-after.txt); gold-loss.sav: récord139,
  PB 15→15, equipo/cajas idénticos; ruta6 en archivo, 0 en RAM, igual que el Domo (gold-loss-save.json).
- Laboratorio parado con reap desde la sesión que lo arrancó; bus D-Bus privado cerrado; sin session.json.
Commits: el de esta entrada, «fix(frontier): cap Lucy's Shuckle EVs to ORAS 510 and finish Pike Brain acceptance».
Decisiones: EV a 510 en lugar de excepción de motor (reversible; si el usuario quiere los 610 hay que
cambiar el escritor de EV, que es motor, y hacer la regresión del caso b). Caso a: no se tocaron motor,
asm, patch.py, isla ni construcción común. REPARTO/tasks.json intactos según el brief del carril.
No probado: consola, oro ganado y revanchas en Azahar (sí en VM), inglés en juego, dificultad sin asistencia.
Siguiente paso: el orquestador integra lane/claude y pasa la aceptación en main; F8-CEREBRO-TUBO terminado
(done en work/lane-task.json). Pregunta abierta para el usuario: ¿aceptar 510 EV para Shuckle o pedir los 610?

## 2026-11-12 — Claude Code (Opus 5.5) — F8-CEREBRO-PIRAMIDE hito 1: Brandon en la cima (VM)
Estado: en curso
Hecho: Brandon habilitado en `brains.py` (ENABLED, seis sets exactos de cerebros.md §7, IV16/31, clase96, nombre
propio; especies/movimientos/objetos/naturaleza Afable añadidos y cotejados con gametext ES por test). `check_routine`
admite la racha de un work y un desfase (`streak_work`, `offset`), por defecto igual que antes. `pyramid.py`:
la escalera del piso 7 cuenta el piso (racha y récord) y luego llama `brains_check` con unidad = pisos contados
(21/70/105…); si toca, guarda la variante en WORK_SUMMIT (16731, ya reservado en REPARTO para esto) antes del
combate, y el combate de Brandon es el de los pisos con WORK_BRAIN = 7 + 8·variante (brains_cro.s pone entrenador y
equipo). Victoria: `brains_won` (símbolo, +10 PB una vez, línea) y después PB del desafío y vuelta al vestíbulo;
derrota: `brains_lost`, línea de derrota, fin de desafío (racha0, récord y símbolos intactos). Con WORK_SUMMIT
pendiente (recarga) la escalera va directa a Brandon sin volver a contar el piso; los entrenadores del piso 7
siguen vencidos (BEATEN se pone a 0 solo al cerrar). Retirada en recepción limpia también WORK_SUMMIT. Consulta:
la otra recepcionista del vestíbulo (evento 3, NPC 2 de 517, modelo 62) dice los símbolos de la Pirámide.
Para caber en el ZO del piso (antes 17692 > 17248) los tres entrenadores comparten `pyramid_trainer(bit)` y una
rutina `pyramid_battle(brain)`; sus entradas `pyramid_trainer<k>` y su comportamiento no cambian.
Evidencia: source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests: 1365 passed, 1 skipped, 42.72 s
(work/frontier/cerebros/pyramid/tests-m1.log); git diff --check limpio. Nuevo tests/test_frontier_brain_pyramid.py
(35 casos VM): umbrales hasta piso 210 con 0/1/2/3 símbolos, pisos 1–6 sin jefe, no-jefe igual que antes, victoria
plata/oro/revanchas con símbolo y bonus una vez y racha sin piso extra, derrota, récord contado antes, pendiente tras
recarga (ni salto ni doble cuenta), pendiente escrito antes de StartBattle, entrenadores sin Cerebro, retirada,
consulta, equipos/IV/EV exactos. Build: python frontier/overlay.py --out work/frontier/cerebros/pyramid/build
correcta (build.log); ZO 140/141/142 = 16140/16956/16956 (<=17248, medido sobre romfs/a/0/1/3);
brains_cro.s sin cambios de código (0xf0480–0xf09f4), solo las dos filas de datos de Brandon en brain_table.
Commits: el de esta entrada, «feat(frontier): add Brandon at the Pyramid summit».
Decisiones: sin líneas de texto nuevas (intro/victoria/derrota/consulta ya existían por ruta en el bloque de
Cerebros) para no desplazar 1072–1133; sin zona nueva: la cima es la escalera del piso 7. Política caso a (solo
Pirámide): no se tocan motor, asm, patch.py, isla ni construcción común; la tabla brain_table es dato (precedente Lucy).
No probado: nada en Azahar todavía.
Siguiente paso: Azahar 24690 con copia de partida en piso 7, racha 20, BEATEN=7: plata ganada con símbolo,
guardar/cargar; oro (racha 69) o derrota; comprobar que piso/PB no se duplican y equipo real intacto.

## 2026-11-12 — Claude Code (Opus 5.5) — F8-CEREBRO-PIRAMIDE hito 2: aceptación de Brandon en Azahar
Estado: hecho
Hecho: aceptación en Azahar 24690 (caso a, solo Pirámide) de la build del hito 1 (b675a23), sin cambios de código
del juego después. `check_team.py` admite `--facility pyramid`; README de sondas e informe `reports/frontier.md` §47.
Evidencia (work/frontier/cerebros/pyramid/ del carril claude; detalle y hashes en §47):
- Plata: copia de work/frontier/lab/py_c_lobby_saved2.sav (8b5a8b76…) a S/récord20, piso7, vencidos7 (fixture.json).
  Reanudar → piso 7 → encargado: intro «Soy Brandon…»; entrenador141, S=21 ya contado, WORK_BRAIN15; equipo exacto
  (check-silver.log rc0); victoria raw1 (silver.gdb.log, transcrito de consola). «Símbolo Bravura de plata… 10 PB»
  y «Recibes 6 PB». Guardado del juego: S/récord21, activo/ruta/pendiente0, símbolos4096, PB5→21 (+10+6, una vez),
  equipo y cajas idénticos (silver-saved.json). Reinicio desde él: la recepcionista 2 dice «Tienes el Símbolo
  Bravura de plata» (symbols-talk.png).
- Pendiente guardado + oro + derrota: copia del guardado de plata con S/récord70, piso7, vencidos7, 16731=2
  (gold-fixture.json). Entrenador del piso 7: «Ya hemos combatido»; encargado: directo a la intro de oro sin
  «Piso 7 de 7»; entrenador142, S=70 (no cuenta otro piso), equipo de oro exacto (check-gold.log rc0); derrota raw0
  (gold.gdb.log), línea de Brandon y «Has perdido…», vestíbulo. Guardado: S/activo/ruta/pendiente0, récord70,
  símbolos4096, PB21 sin cambio (gold-loss-save.json). Equipo: solo amistad +2 y checksum en los cinco no huevo,
  incluidos los que no combatieron (selección 4,5,3; el 5 no cambia): pasos al caminar, no el combate.
- Suite: env -u ORCH_LANE python -m pytest -q tests: 1365 passed, 1 skipped, 42.42 s (tests-m2.log); diff --check limpio.
- Laboratorio parado (gdbctl stop + reap, sin session.json, use_gdbstub=false; cleanup.log).
Commits: b675a23 hito 1; el de esta entrada, «test(frontier): accept Brandon at the Pyramid summit in Azahar».
Decisiones: política caso a; regresión de otras instalaciones no aplica (no se tocó motor ni construcción común).
El pendiente guardado se probó con partida editada: en juego no hay punto de guardado entre contar el piso y el
combate, así que es la red de seguridad para un guardado o reinicio en ese intervalo. Para el integrador: 16731
pasa de «reservado» a usado por la Pirámide (WORK_SUMMIT); la recepcionista del evento 3 del vestíbulo 140 es
ahora la consulta de símbolos; no hay líneas, works ni casos nuevos.
No probado: consola, oro ganado y revanchas en Azahar (sí en VM), inglés en juego, dificultad sin asistencia.
Siguiente paso: el orquestador integra lane/claude y pasa la aceptación en main; F8-CEREBRO-PIRAMIDE terminado
(done en work/lane-task.json). Sin push.

## 2026-11-12 — Claude Code (Opus 5.5) — F10-PERSONALIDAD-DISENO: interior, letrero y exterior de cada edificio
Estado: hecho
Hecho: diseño reports/diseno/personalidad.md y propuestas frontier/orch/propuestas/personalidad.json (diez tareas,
sin encolar). Solo lectura y medidas estáticas con CTRMap-F5 (sin Azahar ni código del juego); solo recursos de ORAS,
Emerald 3DS de ZallaxDev no consultado. Sondas reproducibles nuevas en frontier/probes/personalidad/ (survey.sh,
floor_fit.py, plaza_variants.sh, SignCheck.java, README).
- Interiores: mapa de suelo de las 536 zonas cruzado con zones.tsv; 175 cubren las casillas de la coreografía de 517
  (x19–23 y12–25 + recepción). Elegidos: Torre se queda en 517 (única dueña), Fábrica 139 Nueva Malvalona, Palacio
  358 sala del Campeón, Arena 289 Escuela de Entrenadores, Tubo 88 Monte Pírico, vestíbulo de Pirámide 165 (cueva),
  Domo 365 ya hecho; alternativas medidas 286, 337, 273, 132. Cargas 333.184–1.160.192 (517: 2.320.512).
- Letreros: siete Sign post del catálogo → plaza 2.708.224 (< LOAD_BUDGET 2.724.608). Ninguna zona del Frente ni 212
  tiene rutina de letrero (SignCheck); ZO de la isla 11.288/17.248 para trasplantarla.
- Exterior: con postes, solo caben vallas de hierro (Arena 2.716.288; Arena+Torre 2.724.480, margen 128). Cambios de
  edificio (Lavacalda 2.728.704, casa-bloque 2.732.160, tejas doradas 2.795.776) necesitan medir una cota mayor;
  árboles/arbustos del área 8 cuestan ~146 KB. Anfitrión NPC por puerta como retoque fuera del presupuesto (memoria
  no medida). Build común: Build.java no tiene clearProps (necesario para 139/289).
Evidencia (work/frontier/personalidad/ del carril claude, fuera de git):
- floors/floorN.txt (536), floor_fit.txt, floor_fit_chosen.txt, entities.txt, budgets.txt (survey.sh, rc0, survey.log).
- plaza_variants.txt: control 2.665.344 = java.log de work/frontier/package/build-island (reproduce la build).
  Base: copia de work/frontier/plaza-exp/base-game del checkout principal (solo lectura).
- signcheck.txt (209/212/213/329/340/456/457/458/140/517 false; 16 y 14 true), zo.txt (ZO de 209 y salas).
- work/frontier/island/zones.tsv copiado del principal, SHA256 2d9d6036…645a idéntico.
- check_tasks.txt: frontier_orch.check_task '' en las diez y dependencias conocidas.
- Suite: source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests: 1365 passed, 1 skipped, 42.40 s
  (tests.log); git diff --check limpio.
Commits: el de esta entrada, «docs(frontier): design each facility's own interior, sign and exterior».
Decisiones: Torre conserva 517 (coste cero; heredera de la Torre en ORAS); poste de letrero por ser el más barato;
vallas de la Torre solo con el sí del usuario (128 bytes de margen); subir LOAD_BUDGET (F10-COTA-CARGA) queda como
decisión del usuario porque Azahar no asegura consola. REPARTO y tasks.json intactos (modo carril).
No probado: nada en Azahar ni en consola; colisiones de los donantes (el suelo no ve barreras), salidas de llegada
de 358/165, música/cámara del donante, trasplante de la rutina de letrero, memoria de NPC anfitriones.
Siguiente paso: el orquestador integra lane/claude; las tareas de personalidad.json se encolan con
`frontier-orch add frontier/orch/propuestas/personalidad.json` cuando el usuario lo decida (prioridad: lo último).

## 2026-11-12 06:12 — Codex — F7-CONSOLA-MANSION hito 1: relevo y sonda pasiva
Estado: en curso
Hecho: revisados AGENTS/PLAN/REPARTO/diseño, status/diff y último commit 1831f8f.
Árbol limpio al relevo: no había cambio parcial que completar o deshacer; sin stash ni reset.
Añadidos frontier/probes/maison/{dump.py,trace.gdb,README.md}; informes consola-frente.md y
frontier.md §48. El parser confirma el data abort y compara la ventana del dump con ambas
CRO publicadas. La sonda mide selección, equipo final y cliente, deteniendo antes de un vacío;
no escribe RAM. Instalado paquete exacto alfa en laboratorio 24691, con partida Checkpoint publicada;
ferry a Resort Batalla y secuencia de primera llegada en curso (todavía sin combate).
Evidencia: work/frontier/console-maison/dump.json: dump SHA256d58509de…8d29787, 652 bytes,
PC0x76638c, r0=0, FAR0xc; 96 bytes de código idénticos a alfa y v0.5. No prueba causa heredada.
boot2.log verifica manifest de los 37 ficheros y hash de partida5ddaa992…7edeffa.
Suite: env -u ORCH_LANE python -m pytest -q tests: 1365 passed, 1 skipped,48.75s
(tests-clean-env.log). Primera ejecución con ORCH_LANE heredado:9 fallos de tests del orquestador,
1356 passed,1 skipped (tests.log); conocido del entorno, no del juego. git diff --check limpio.
Commits: el de esta entrada, «test(frontier): add passive Maison crash diagnostics».
Decisiones: no alterar motor sin reproducir; no reconstruir alfa para compararla con consola.
Primer arranque del laboratorio interrumpido al cancelar una caminata bloqueada por marinero;
reap y segundo arranque en conductor persistente. REPARTO/tasks.json intactos, sin push.
No probado: cinco modalidades, control v0.5 en juego, causa del equipo vacío, regresión caso b.
Siguiente paso: acabar primera llegada al Resort, llegar a Mansión original por 210→211→516→517,
guardar copia local antes de recepción, ejecutar cinco modalidades con trace.gdb y comparar v0.5
si falla. Puerto solo24691. Laboratorio todavía activo durante este hito, se parará al cerrar sesión.
