# Reparto del Frente de Batalla entre Claude Code y Codex

Lo leen las dos herramientas al empezar cada sesión, después de PLAN y de la bitácora (AGENTS.md). Se actualiza en el
mismo commit que cambia lo que describe.

## Normas

1. **Un turno a la vez.** Claude Code y Codex comparten la carpeta, `work/` (builds, partidas) y el único laboratorio
   de Azahar. Nunca escriben a la vez. Quien tiene el turno es el **integrador**: es el único que toca los ficheros
   compartidos y el laboratorio.
   - Ficheros compartidos: `frontier/island_build.py`, `frontier/patch.py`, `frontier/asm/rental.s`,
     `frontier/overlay.py`, `frontier/ids.py`, `frontier/factory.py`, `faraway/java/`, y los tests de esos ficheros.
2. **Al tomar el turno**: leer AGENTS.md, PLAN, las últimas entradas de la bitácora y este fichero; poner tu nombre y
   la hora en «Turno» y hacer commit antes de cambiar nada más.
3. **Al dejar el turno** (también si se acaban los créditos a mitad): entrada de bitácora (con «Estado: en curso» si
   queda a medias), «Turno» a «libre», tabla actualizada y commit. Sin ese commit, el turno no se ha soltado.
4. **Cada instalación tiene un único dueño.** Su código va en su módulo (`frontier/<instalación>.py`,
   `frontier/asm/<instalación>.s`, `tests/test_frontier_<instalación>.py`). Lo que necesite de los ficheros
   compartidos lo hace el integrador, o lo deja el dueño como lista en su entrada de bitácora.
5. **Zonas, works, flags y líneas de texto** se asignan aquí antes de usarlos, para que dos instalaciones no tomen el
   mismo. Una zona asignada está «por verificar» hasta que su dueño la verifica como en `reports/frontier.md` §18.
6. **Trabajo en paralelo**: solo de lectura (diseño, medidas estáticas). Si alguna vez hace falta escribir en paralelo,
   en un `git worktree` aparte, sin `work/` ni laboratorio, solo en el módulo propio; el integrador lo une después.
7. **Codex no lo lanza Claude**: lo abre el usuario y le dice qué instalación lleva. Los agentes de Claude solo se
   lanzan con el sí del usuario y el coste dicho (norma de CTRMap-F5).
8. **Modo automático**: `frontier/orch/frontier-orch auto` reparte las tareas de `frontier/orch/tasks.json` entre los
   dos, reanuda sin «continúa» y pasa la tarea al otro cuando uno agota su cuota (`frontier/orch/README.md`).
   Mientras corre, tiene el turno: no abras otra sesión que escriba.

## Turno

Claude Code, desde 2026-11-03 22:xx (arreglo del supervisor tras la caducidad de la sesión)

## Instalaciones

Diseños en `reports/diseno/`, hechos por agentes de solo lectura el 2026-11-03 (sus reglas de Esmeralda están sin
fijar a un commit de pokeemerald). Dueños confirmados por el usuario el 2026-11-03.

Decisiones del usuario (2026-11-03):
- Palacio y Arena: primero sin su mecánica especial (etapa A, como la Torre); la mecánica del motor, después.
- Tubo v1: los PP no se arrastran, los estados ignoran inmunidades y no hay salvajes (van a la v2).
- La tabla de PB de la Fábrica se revisa en el trabajo común.

| Instalación | Dueño | Estado | Interior (por verificar) | Diseño | Dificultad v1 (según su diseño) |
| --- | --- | --- | --- | --- | --- |
| Fábrica | Claude Code | hecha en la sala 213 (§19–§22) | 213 (clon de 517) | PLAN §1–§5 | — |
| Torre | Claude Code | diseño | 329 (clon de 517) | `torre.md` | baja-media, ~3 sesiones |
| Palacio | Claude Code | diseño | 340 (clon de 517) | `palacio.md` | A: baja-media, 1; B (IA): alta |
| Arena | Claude Code | diseño | 457 (clon de 517) | `arena.md` | A: media, 1–2; B (3 turnos): alta |
| Domo | Codex | diseño | 456 (clon de 517) | `domo.md` | media-alta, ~4 |
| Tubo | Codex | diseño | 379 vestíbulo, 380 sala (clones de 397) | `tubo.md` | media-alta, 4–6 |
| Pirámide | Codex | diseño | 140 vestíbulo, 141–142 pisos | `piramide.md` | alta, 4–6 + experimento |

Avisos sobre las zonas:
- Los diseños no coinciden en qué candidatas son seguras. El del Domo descarta 140–157, 329, 340 y 351–352 porque el
  código podría intercambiarlas; el del Palacio duda de 379–381 (posible Casa Trampa). Hipótesis sin medir: la
  verificación de §18 lo decide, y si una falla se toma otra de `work/frontier/island/repurpose.txt`.
- Reservas: 330–352 sin usar, 430, 458, 459, 119, 120, 2–4.

## Trabajo común del integrador antes de las instalaciones

Lo piden varios diseños. Va primero y lo hace quien tenga el turno:
1. ~~Salida de cada interior a su propia puerta~~ (hecho: `island_build.door_warp`, test
   `test_each_interior_exits_to_its_own_door`).
2. ~~Ruta de racha por valor~~ (hecho: `patch.STREAK_ROUTES`, tabla `slot_deltas` de `rental.s`; tests Unicorn
   `test_each_route_uses_its_facilitys_streak_and_record`). Una instalación pone `WORK_ROUTE` = `patch.ROUTE[...]`
   durante su desafío y 0 al salir; el script no llama a `AddWinCount` aparte.
3. ~~Registro de works~~ (hecho para racha, estado y récord; tabla de abajo). Los demás works, flags y líneas de
   texto se piden aquí y se apuntan en la tabla antes de usarlos.
4. ~~Clones genéricos~~ (hecho: `island_build.CLONES`, `KEEP_TEXT`, `NATIVE_DONORS`, `build(..., zone_scripts)`;
   test `test_facility_clones_are_generic`). Para añadir una zona: `CLONES[N] = donante`, `KEEP_TEXT` si conserva el
   texto 619, `NATIVE_DONORS[N] = 517` si su donante no es 517, y su script en `zone_scripts` desde `overlay.py`.
5. ~~Máscara de nativas aparte~~ (hecho: `island_build.native_donors()`, que `overlay.py` pasa a `patch.build`).
6. Exclusión mutua: **convención fijada** (`patch.ACTIVE_WORK`: el work «desafío a medias» de cada instalación; la
   Fábrica usa `WORK_IV`). La recepción de cada instalación se niega si el de otra no es 0. Se programa con la
   segunda instalación (la Torre), en la Fábrica y en ella a la vez, con su texto.
7. ~~Tabla de PB~~ (hecho: `data.FRONTIER_BP`, las siete columnas de pokeemerald `731ad5bf`; la Fábrica daba 9 PB
   en vez de 10–15 desde la ronda 15).

Probado en Azahar con el `code.bin` nuevo: una ronda de la Fábrica empieza, combate y termina en derrota sin
colgarse; después la racha de la Mansión, la de la Fábrica y los works de la Torre siguen a 0 y `WORK_IV` = 0
(`work/frontier/lab/f6k_after_loss.sav`). Comprobación débil (ya estaban a 0). **Sin probar en el juego**: una
victoria que suba la racha con la ruta nueva; la cubren los tests Unicorn y se mira en la primera ronda ganada de
la Torre.

## Works asignados

| Instalación | Ruta (`WORK_ROUTE`) | Racha | Desafío a medias | Récord | Otros |
| --- | --- | --- | --- | --- | --- |
| Fábrica | 1 | 16437 | 16410 (`WORK_IV`) | 16439 | 16411–16413 alquileres, 16433–16435 rival, 16438 ruta (común) |
| Torre | 2 | 16441 | 16442 | 16443 | |
| Palacio | 3 | 16461 | 16462 | 16463 | |
| Arena | 4 | 16465 | 16466 | 16467 | |
| Domo | 5 | 16473 | 16474 | 16475 | |
| Tubo | 6 | 16477 | 16478 | 16479 | |
| Pirámide | 7 | 16481 | 16482 | 16483 | |

Libres para pedir (según `python frontier/ids.py`, 2026-11-03): 16485–16487, 16493–16495, 16649–16651,
16653–16655, 16657–16659, 16661–16663, 16669–16671, 16673–16675 y más; 16665 y 16667 son del evento de Mew.
