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

libre (último: Codex, 2026-11-13 20:43; cola revisada, lista para frontier-orch)

## Instalaciones

Actualización 2026-11-13 (prevalece sobre la foto del 11 de noviembre de la tabla):
F8 Cerebros de las siete instalaciones y F7-PAQUETE-V02 están done en tasks.json.
El usuario confirma que alfa v0.2 funciona en 3DS (confirmación general, sin matriz
completa de pruebas); F7-CONSOLA-MANSION queda cerrada. Se encolan seis tareas F9 y
diez F10, en ese orden y en cadena por sus ficheros compartidos. Véase orch/README.md.

Diseños en `reports/diseno/`, hechos por agentes de solo lectura el 2026-11-03 (sus reglas de Esmeralda están sin
fijar a un commit de pokeemerald). Dueños confirmados por el usuario el 2026-11-03.

Decisiones del usuario (2026-11-03):
- Palacio y Arena: primero sin su mecánica especial (etapa A, como la Torre); la mecánica del motor, después.
- Tubo v1: los PP no se arrastran, los estados ignoran inmunidades y no hay salvajes (van a la v2).
- La tabla de PB de la Fábrica se revisa en el trabajo común.

Decisión del usuario (2026-11-10): Palacio etapa B por la vía híbrida de `reports/frontier.md` §32 (interfaz
conservada, decisiones 3/5/6 por la IA), no por la conversión directa del cliente 0 ni por las alternativas 2 o 3.

Estado contrastado el 2026-11-11 con `frontier/orch/tasks.json`, la bitácora y las secciones citadas de
`reports/frontier.md`. «Hecha» se refiere a la etapa indicada y a su aceptación en Azahar; consola no probada.
F7-PAQUETE sigue en curso: la prueba del paquete exacto integrado se registra aparte.

| Instalación | Dueño | Estado y sección de `reports/frontier.md` | Interior verificado | Diseño | Pendiente |
| --- | --- | --- | --- | --- | --- |
| Fábrica | Claude Code | Nivel 50 Individual jugable: alquiler, intercambio, ronda, PB y racha propios, pausa y reanudación (§9–§15, §19–§22, corrección de works §25) | 213 (clon de 517) | PLAN §1–§5 | F5: Noland, símbolos, cartel de récords, Doble y Libre; rival aún generado por la Mansión |
| Torre | Claude Code | v1 hecha; equipo propio, ruta 2, PB, pausa, reanudación, derrota y exclusión mutua (§25; F6-TORRE done) | 329 (clon de 517) | `torre.md` | Jefe y tramos por encima de racha 19 sin probar; modalidades y textos propios |
| Palacio | Claude Code | A, B híbrida (IA decide) y C (naturaleza y PS eligen grupo de movimientos) hechas (§27, §33, §36; F6-PALACIO-A/B/C done) | 340 (clon de 517) | `palacio.md` | Textos del entrenador aún esperan A (aceptado por usuario); «No obedece» fuera de C |
| Arena | Claude Code (A); Codex (B) | A y B hechas: límite de 3 turnos, juicio por Cuerpo y cambio prohibido (§29, §31, aceptación y cierre de regresiones; F6-ARENA-A/B done) | 457 (clon de 517) | `arena.md` | Mente, Técnica, textos del árbitro y Greta |
| Domo | Codex | v1 hecha: torneo de 4 rondas, vista rival y 2 de 3 (§26); sala amplia, combate, pausa, guardar/cargar y salida aceptados (§37.1; F6-DOMO y F6-DOMO-SALA done) | 456 (clon visual de 365, nativas de 517; salida adaptada) | `domo.md` | Cuadro y simulación de otros participantes, Tucker, Doble/Libre y textos propios |
| Tubo | Codex | v1 y v2 hechas: PS/estados y PP persistentes, inmunidades y salas salvajes (§28, §35 hitos 5–6; F6-TUBO/V2 done) | 458 (clon de 517; 379 descartada) | `tubo.md` | Doble, Lucy, pantalla de selección; reproducir incidencia de reanudación de §35; salvajes con presentación de entrenador |
| Pirámide | Codex | v1 (Claude por relevo) y v2A hechas: siete pisos, cueva sin PC, vencidos no repiten combate tras recarga (§30, §34; F6-PIRAMIDE/V2A done) | 140 vestíbulo (clon de 517), 141–142 pisos (clones de 77) | `piramide.md` | Oscuridad, objetos/bolsa, PS persistentes, salvajes y Brandon; vencidos aún visibles |

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
(`work/frontier/lab/f6k_after_loss.sav`). Comprobación débil (ya estaban a 0). **Probado en el juego el 2026-11-04** (`reports/frontier.md` §25): una victoria de la Fábrica sube su racha por
la ruta 1 (16437 = 1, récord 1) y las de la Torre por la ruta 2, sin tocar la de la Mansión.

El Tubo v2 reserva además slots virtuales 256–258 de `PokePartyGetParam`, solo con ruta 6:
consultan las posiciones inscritas (incluida Caja de Combate); slots retail sin cambios. Un puente
en `DllField.cro` 0x4e644 usa 104 bytes de la cueva común. Medida actual tras F7-CUEVA-LUMA: code.bin 0x579804–0x579eec, 276 bytes libres;
0x579604–0x579804 reservado a Luma (no reutilizar).

## Works asignados

| Instalación | Ruta (`WORK_ROUTE`) | Racha | Desafío a medias | Récord | Otros |
| --- | --- | --- | --- | --- | --- |
| Fábrica | 1 | 16437 | 16489 (`WORK_IV`) | 16439 | 16485–16487 alquileres, 16490 generador, 16433–16435 rival, 16438 ruta (común); 16410–16414 abandonados (el juego los borra al entrar en una sala, §25) |
| Torre | 2 | 16441 | 16442 | 16443 | |
| Palacio | 3 | 16461 | 16462 | 16463 | |
| Arena | 4 | 16465 | 16466 | 16467 | 16693–16694 reservados para PS iniciales de cada lado en B (§31) |
| Domo | 5 | 16473 | 16474 | 16475 | 16493–16495 inscritos, 16649–16650 combatientes (code.bin), 16651 racha para el script 5, 16653–16655 rival, 16657–16658 sets forzados (code.bin), 16659 generador; casos 9773–9775 del script 5; líneas 998–1013 del texto 637 |
| Tubo | 6 | 16477 | 16478 | 16479 | 16661–16663 PS, 16669–16671 estado (code.bin), 16674 generador; 16675 set salvaje (v2, code.bin; 0 = sin sala salvaje); 16721–16723 PP movimientos 1–2 y 16725–16727 PP 3–4 (v2, dos bytes por work, 0xffff = llenos); entradas 217–222 de maisonpkN (sets salvajes); caso 9776 del script 5; líneas 1014–1056 del texto 637 |
| Pirámide | 7 | 16481 | 16482 (piso actual) | 16483 | 16681–16683 selección y 16685 cuenta (code.bin), 16686 vencidos, 16687 línea, 16689 número; caso 9777 del script 5; líneas 1057–1071 del texto 637 |
| Cerebros (común) | — | — | — | — | 16729 símbolos (2 bits por ruta), 16730 Cerebro del combate (ruta + 8·variante), 16731 reservado a la cima de la Pirámide, 16733 línea para el caso 9778; caso 9778 del script 5; líneas 1072–1099 del texto 637 (4 por ruta) y 1100–1127 (derrota y consulta «Símbolos», 4 por ruta, F8-CEREBRO-FABRICA); línea 190 del texto 619 («Símbolos») y valor 5 del menú de recepción; maisonpkN 223–264 (6 por ruta, desde 223 + 6·(ruta−1)); maisontrN 129–142 añadidas (2 por ruta) y sus nombres en las líneas 129–142 del gametext 154 (8 idiomas); DllField.cro 0xf0480–0xf0978 (`brains_cro.s`; hasta 0xf08c0 en BASE, ampliado por Noland) y los `bl` de 0x94f04, 0x94f18 y 0x95044 (F8-CEREBROS-BASE, 2026-11-11) |

Libres para pedir (según `python frontier/ids.py`, 2026-11-03; 16485–16487 y 16489–16490 son de la Fábrica y 16493–16495,
16649–16651, 16653–16655 y 16657–16659 del Domo desde el 2026-11-04): 16661–16663, 16669–16671, 16673–16675 y más; 16665 y 16667 son del evento de Mew.

## Reservas del motor (Arena B, 2026-11-05)

Arena: bit 31 (`0x80000000`) del word `BattleSetup+0xa8`; se pondrá al final de StartBattle solo con ruta 4
y work 16466 activo. El bit sigue en validación (§31); no usarlo para Palacio B. Works 16693–16694 para PS
iniciales: libres según `python frontier/ids.py` (1157 scripts, 147 ficheros de código), reservados antes de usarlos.
La lógica del CRO irá en la cueva compartida de code.bin si cabe; hoy quedan 1284 bytes antes de añadir el juicio.

Palacio B (2026-11-10, F6-PALACIO-B): bit 30 (`0x40000000`) del mismo word `BattleSetup+0xa8`; `palace_start`
(encadenado tras `arena_start`) lo limpia y lo pone solo con ruta 3, work 16462 activo y estilo Individual. Ningún
lector de `+0xa8` con máscara que incluya el bit 30 en code.bin ni en las 145 CRO (`frontier/probes/palace/audit_a8.py`,
`reports/frontier.md` §33). El bit 31 sigue siendo de la Arena.

Palacio C (2026-11-11, F6-PALACIO-C): DllBattle.cro **0xd7630–0xd7868** (filtro y tablas, en el relleno a cero
0xd7628–0xd8000 de la región de código; quedaban 1944 bytes hasta 0xd8000; tras F7-CUEVA-LUMA, Arena/Palacio B ocupan
0xd7870–0xd7b84 y quedan 1148 bytes) y el `bl` de **0xd468**. No usa la cueva
de code.bin (`reports/frontier.md` §36).
