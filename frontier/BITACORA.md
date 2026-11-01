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
