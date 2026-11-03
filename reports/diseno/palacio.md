# Palacio Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code; no tocó ficheros ni el laboratorio. Las reglas de Esmeralda las da
de memoria y hay que contrastarlas en pret/pokeemerald `731ad5bf` (PLAN §1). Las direcciones de `code.bin` salen de
lectura estática con `frontier/disasm_code.py` sobre el de Repolished; no se han ejecutado.

## 1. Reglas y primera versión

**Esmeralda** (de memoria; `ChooseMoveAndTargetInBattlePalace`, `PlayerChooseMoveInBattlePalace`):
- equipo propio, 3 en Individual, sin repetir especie ni objeto; Nivel 50 y Libre, Individual y Doble;
- el jugador no da órdenes, no cambia de Pokémon ni usa objetos;
- cada turno se sortea un grupo de movimientos (ataque, defensa, apoyo) con porcentajes por naturaleza, en dos
  columnas según PS por encima o por debajo del 50 %. El grupo de un movimiento sale de su potencia y objetivo; sin
  movimientos usables en el grupo se toma otro, y a veces «no obedece». El rival también actúa por naturaleza;
- rondas de 7; Spenser en los combates 21 y 42 (a contrastar); tabla de PB a contrastar.

**Primera versión**: Palacio Nivel 50 Individual con el equipo propio, en tres etapas.
- **A, sin tocar el motor**: inscripción, selección de 3 con la pantalla de la Mansión, 7 combates, racha propia, PB,
  pausa y derrota. El jugador aún da las órdenes. Es casi la Torre.
- **B**: la IA del juego decide por tus Pokémon, todavía sin naturaleza.
- **C**: se filtran los movimientos que la IA puede elegir con la tabla de naturalezas y PS.
- Fuera: Spenser (F5), Doble, Libre y que el rival use la naturaleza.

**¿Exige modificar el motor?** Sí: ningún script ni nativa de campo quita el control al jugador. Indicios (lectura
estática, sin ejecutar):
- `0x1e30b8` (StartBattle) elige el montador según `work+0x839`, tabla de saltos en `0x1e3158`: tipos 0–3 →
  `0x1e0634`; Multi sin comunicación (`work+0xAE1` = 0) → `0x1e1308`;
- estructura del combate en `work+0x620`: el montador Individual crea los equipos en `+0x4C` (jugador) y `+0x50`, y
  el objeto de entrenador (0x38 bytes, constructor `0x1f036c`) en `+0x70`; el de Multi añade `+0x54`/`+0x58` y
  `+0x74`/`+0x78`, llama a `0x1e3620`/`0x1e3480` con los índices 0–2 y pone `+0x49 = 3`. El índice 2 es el
  compañero de Multi (equipo desde `+0x5C`, §3–§4). Hipótesis: un equipo por cliente en `+0x4C+4k` y un entrenador
  en `+0x6C+4k`;
- `0x1e3620` escribe en el objeto de entrenador `+0xC = 7`, o `0x87` en Doble/Triple/Multi (`0x1e365c`–`0x1e367c`):
  probablemente las banderas de IA (byte AI de `TrainerData6.cs`). Hipótesis.

**Conclusión**: el motor ya tiene un cliente del lado del jugador controlado por IA (el compañero de Multi). La vía es
dar al cliente 0 un objeto de entrenador con IA 7 y localizar en `DllBattle.cro` dónde se decide que ese cliente es
la interfaz. Parchear el CRO ya se hizo en la v0.5 (`scripts/build_patch.py`, hashes y CRR).

**Alternativas más baratas**:
1. Etapa A sola: el Palacio sin su mecánica principal.
2. Ficha recortada por naturaleza, solo en `code.bin`: sobre la copia del equipo (§4) se sortea el grupo y se dejan
   solo esos movimientos; el jugador sigue pulsando. Hay que localizar los lectores de movimientos y naturaleza de
   `PokemonParam` (escritores `0x3b54d8` y `0x12c190` medidos en §8). Coste bajo-medio, pero no es «elige solo».
3. Truco de Multi (poca confianza): tu equipo al compañero de IA (`+0x54`) y el cliente 0 con un único Pokémon
   debilitado. Experimento de una sesión con gdb; cambia el formato a 2 contra 2 rivales.

## 2. Qué se reutiliza y qué falta

**Se reutiliza**: flujo de la Mansión (`L18f8`, `0x457c` con `BattleHouse_CallPartySelectApp`, bucle, `L2210`,
`L1458`, PB en `L3de4`/`L3f4c`); ajuste a nivel 50 de `0x1e3d2c`; patrones de `factory.py` (`Routine`,
`reception()`, `_clear`, `battle_points`); `pawn.Program.transplant`, `island_build.CLONES`, `patch.zone_natives`;
desvío de racha (`FACTORY_SLOT`, `STREAK_SITES`). Con `WORK_IV = 0` el gancho de alquiler sigue la rama retail y
entra el equipo propio.

**Falta**:
- works propios de `frontier/ids.py` (estado; racha `S` y récord `S+2`, consecutivos como pide el `assert` de
  `patch.py`), asignados por el integrador;
- generalizar `WORK_ROUTE` a un identificador por instalación con su `SLOT_DELTA` en `rental.s` (acordarlo con la
  Torre);
- texto «Palacio Batalla»: línea 189 del texto 619, tras la 188 de la Fábrica;
- para la etapa B, medir antes de escribir (§4).

## 3. Interior

Donante 517, clonada como 213 (§19, §20, §22): `keeptext.P=1`, `place.P=279`, `scripts/zoneP.bin` construido desde
el 517 **retail** (no desde el de la Fábrica, por el límite ZO de 17.248, §11). Máscaras vía `CLONES`.

**Candidatas** (< 536; el agente ejecutó `python frontier/zone_natives.py`: las 46 «likely free» tienen la máscara
por defecto 0x243), sin mapa propio:
1. 340 (Mossdeep; área 146, compartida solo con 339);
2. 430 (Lavacalda; área 182, compartida con 429, máscara 0x2c3);
3. 329 (Calagua; área 141).

Descartadas: 502 (Bases Secretas, destinos calculados), 535 (vuelo), 477/530/532–534 (con mapa), mazmorras 119–180
(aviso del escáner), 379–381 (Ruta 110, posible Casa Trampa).

**Verificar** (como §18): ningún literal de P antes de un cambio de mapa en los 1157 listados; llamadas al compartido
35 con P como argumento; tablas de huida o teletransporte (hipótesis); que el área bifurcada no choque con 231 y
232; en Azahar, entrar, guardar, cargar y hablar con dos NPC.

## 4. Pasos

**Agente** (`frontier/palace.py`, `tests/test_frontier_palace.py`):
1. Constantes provisionales: works, `MENU_PALACE = 4`, línea de texto y tabla de naturalezas con su fuente.
2. `palace_program(retail517)`: entrada de menú; `palace_reception` (`SetRank(0)`, ruta = Palacio, reanudación si la
   racha > 0, `WORK_SELECT_TYPE = 0`, `call L18f8(0,0,0)` sin pantalla de modalidad pero con la de equipo);
   limpieza en `L2210`, `L1458` y en la opción 0; PB solo tras la 7.ª victoria; ruta a 0 tras
   `BattleInstWorkCreate`.
3. `palace_script()` para `zoneP.bin`, con ida y vuelta y tamaño ZO.
4. Etapa C: tabla de grupo por movimiento (2 bits) generada desde `a/1/8/9` (move, pk3DS `GARCReference`).

**Medición de la etapa B** (en el laboratorio cuando el integrador lo ceda):
- M1: volcar `work+0x620` en `0x1e3240`/`0x1e32a8` en un combate Individual y en un Multi con compañero; confirmar
  `+0x6C` nulo y `+0x74` con IA.
- M2: base de `DllBattle.cro` como en §6 y `rwatch` sobre `setup+0x74`, `+0x49` y `+0x6C` para localizar la
  creación de clientes.
- M3: con `set` de gdb, forzar el cliente 0 a IA sin construir nada; ver si el combate avanza sin entrada y si
  `IsWin` (`work+0x73C`) queda bien.
- M4: medir el relleno de `DllBattle.cro`, o saltar al hueco de `code.bin` con `ldr pc`.

**Integrador**:
- `island_build.py`: `CLONES[P] = 517`, `DOORS['Palace'] = (P, 0)`, P en `zones=`, `keeptext`/`place`, `zoneP.bin`;
  el warp 0 de cada interior debe apuntar al índice de su puerta en el orden de `FACILITIES` (hoy fijo a
  `…,209,0`).
- `patch.py`/`rental.s`: ruta por instalación; después, el gancho de la etapa B en el camino de la Mansión
  (`0x1e30b8`), condicionado al work del Palacio. El hueco es compartido: quedan unos 2060 de 2556 bytes.
- `overlay.py`: script del Palacio, línea de 619 y, en la etapa B, `DllBattle.cro` parcheado **encima del de la
  v0.5**.

## 5. Pruebas

**Suite** (`pawn_vm`): menú con la entrada; ruta y `18f8(0,0,0)`; la pantalla de selección no se salta; PB 0 en
1–6 y el de la tabla en el 7.º; limpieza al perder o cancelar y conservación al pausar; ZO ≤ 17.248; no toca los
works de la Fábrica; tabla de naturalezas de 25 filas. Integrador: Unicorn del desvío con ruta 2; ampliar los tests
de parche y de clones.

**Azahar**: puerta (31,69) desde (31,70) → P → vuelta; guardar y cargar en P; ronda con 3 propios a nivel 50,
victoria, pausa y reanudación, derrota con limpieza; rachas de la Mansión (`0x1BBC0`/`C4`) y de la Fábrica
(16437/16439) intactas; equipo idéntico (`save_fixture.py`, salvo los recuerdos del PK6, §10). Etapa B: combate sin
entrada, cambio automático, resultado correcto, la Fábrica y la Mansión con control manual, un combate de la
historia sin afectar, «Guardar vídeo».

## 6. Riesgos y estimación

- El cliente 0 puede llevar también la pantalla y la cola de mensajes; pasarlo a IA puede colgar o desincronizar.
- Los vídeos de combate graban la entrada: ocultar «Guardar vídeo».
- Parchear un CRO que ya parchea la v0.5.
- Guardar a mitad deja la ruta puesta (§15).
- Cláusulas de especie y objeto del selector de la Mansión, sin medir.
- Competencia por el hueco de `code.bin` y por las zonas.

Dudas para el usuario: si la etapa A sola, o la alternativa 2, vale como hito; si el rival debe usar la naturaleza.

| Etapa | Dificultad | Sesiones |
| --- | --- | --- |
| A | baja-media | 1 (casi la Torre) |
| B | alta e incierta | 2–4 de medición + 1–2 de parche |
| C | media | 1–2 |

Total: **alta**, 5–9 sesiones. Si M3 fracasa, la etapa B se replantea (alternativas 2 o 3).
