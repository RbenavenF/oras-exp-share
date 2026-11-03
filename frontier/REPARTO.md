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

## Turno

libre (último: Claude Code, 2026-11-03)

## Instalaciones

Diseños en `reports/diseno/`, hechos por agentes de solo lectura el 2026-11-03 (sus reglas de Esmeralda están sin
fijar a un commit de pokeemerald). Dueño provisional hasta que lo confirme el usuario.

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
2. Ruta de racha por valor en `rental.s`/`patch.py`: `WORK_ROUTE` 1 Fábrica, 2 Torre, 3 Palacio, 4 Arena…, cada uno
   con su `SLOT_DELTA` (works de racha y récord consecutivos).
3. Registro de works, flags y líneas de texto por instalación (en este fichero y en `frontier/ids.py`).
4. `island_build`: clones genéricos (lista de zonas, `keeptext`/`place`, `scripts/zone<N>.bin` y la comprobación
   `zone N cloned from` para cada clon).
5. Máscara de nativas separada del donante geométrico (`NATIVE_DONORS`), para el Tubo y la Pirámide.
6. Exclusión mutua: una recepción se niega si otra instalación tiene un desafío a medias (`WORK_IV` de la Fábrica,
   y los works de estado de las demás).
7. Comprobar la tabla de PB de la Fábrica contra pokeemerald: el diseño de la Torre dice que `data.BATTLE_POINTS` se
   queda en 9 desde la ronda 13 y Esmeralda sigue subiendo (sin verificar).
