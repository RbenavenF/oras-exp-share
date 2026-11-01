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
