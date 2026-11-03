# Torre Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code. No tocó ficheros del repositorio ni el laboratorio. Todo lo que no
cita una sección o un fichero del repo es hipótesis. Las reglas de Esmeralda las tomó de pret/pokeemerald
(`frontier_util.c`, `battle_tower.c`), en una copia descargada fuera del repo y sin hash de commit: hay que
verificarlas antes de fiarse.

## 1. Reglas de Esmeralda y qué entra en la v1

- **Modos**: Individual, Doble, Múltiple con compañero y Múltiple por enlace, cada uno en Nivel 50 o Nivel Libre
  (mínimo 60, `FRONTIER_MIN_LEVEL_OPEN`).
- **Equipo**: 3 en Individual y 4 en Doble; sin especies ni objetos repetidos y sin huevos. Prohibidos
  (`gFrontierBannedSpecies`): Mew, Mewtwo, Ho-Oh, Lugia, Celebi, Kyogre, Groudon, Rayquaza, Jirachi y Deoxys.
- **Rondas**: 7 combates; entre combates, continuar, pausar o retirarse. Racha y récord por modo y nivel.
- **PB** al ganar el 7.º (`sBattlePointAwards`): Torre Individual `min(ronda, 15)`, +10 contra Anabel.
- **Anabel**: `sFrontierBrainStreakAppearances[TOWER] = {35, 70, 35, 1}`, solo en Individual.

**v1 propuesta**:
- Individual, Nivel 50, rango Normal, con **el equipo propio**;
- racha y récord propios de la Torre;
- PB por ronda como en Esmeralda;
- pausa y reanudación como la Mansión.

Se aplaza: Doble y Múltiple, Nivel Libre (la Mansión siempre baja a 50, `0x1e3d2c`, §4), Anabel y símbolos (con el
Noland de F5), cartel de récords y textos propios. Desviación aceptada: prohibiciones y tope de nivel los de
`BattleHouse_CallPartySelectApp`, que baja a 50 en vez de rechazar; su lista de prohibidos no está medida.

**Aviso sobre la Fábrica (sin verificar)**: `data.BATTLE_POINTS` se queda en 9 desde la ronda 13. En la tabla de
Esmeralda la columna de la Fábrica sigue subiendo (9, 10, 10, 11, 11…), así que la Fábrica daría 1 PB de menos
desde la ronda 15.

## 2. Qué se reutiliza y qué falta

**Sin cambios**:
- flujo del script 517 (§1): recepción `L14f4`, menú `L1634`, desafío `L18f8(rango, tipo, x)`, bucle `0x1e1c`, PB
  `L3de4`/`L3f4c`, derrota `L2210`, limpieza `L1458`;
- pantalla de selección `0x457c` → `BattleHouse_CallPartySelectApp`; la Torre la conserva;
- nativas de la Mansión vía `patch.zone_natives`/`CLONES`;
- guardado `GlobalCall 2003`, menú continuar/pausar/guardar vídeo, guardado y carga en la sala clonada (§19);
- patrones de `factory.reception_routine` y `factory.battle_points`;
- `factory.Routine`, `_index`, etiquetas de `factory.*`, `overlay.maison_retail()`.

**Falta**:
1. **`tower.tower_program(retail517)`**, construido desde el 517 retail, no desde `maison_program`. Cambios:
   - `WorkSet(WORK_ROUTE, 0)` tras `BattleInstWorkCreate`;
   - en `L1634`, el 0 («Combatir») llama a `tower_reception`:
     - se niega si `WORK_IV ≠ 0` (Fábrica pausada);
     - si no, `WORK_ROUTE = 2`, `L18f8(0,0,0)` y la ruta a 0 al volver;
   - en `L3de4`, PB solo en múltiplos de 7, `TOWER_BP[ronda−1]` con tope 15, solo con `WORK_ROUTE == 2`.
2. **Racha propia en `code.bin`**. `FACTORY_SLOT` (`frontier/asm/rental.s`) desvía con cualquier ruta ≠ 0; hay que
   distinguir 1 → `SLOT_DELTA` (Fábrica, 16437/16439) y 2 → `SLOT_DELTA_TOWER` (dos works nuevos de
   `frontier/ids.py`, los asigna el integrador). Con `subeq`/`subne`, usando solo `ip` y banderas.
3. Puerta, clon y textos (§4).

## 3. Interior

**Donante 517**: la 213, clon de 517, combate y vuelve a sí misma (§19–§20). No sirve apuntar la Torre a la 213: su
salida es una sola. Clonar 517 en una zona nueva *T* con `keeptext.T=1`, `place.T=279` y `scripts/zoneT.bin`.
Tamaño estimado unos 15 KB, por debajo del ZO medido de 17.248 (hipótesis).

**Candidatas** (`repurpose.txt`, < 536, sin mapa según `zones.tsv`):
- 329 (Lilycove, área 141);
- 340 (Mossdeep, área 146);
- 430 (Lavaridge, área 182).

De reserva: 119, 120 y 456–459 (estas cuatro comparten el área 111). Descartadas: 2–4 (literales por todas partes);
477, 502, 530, 532–535 (con matriz, Base Secreta o «Soaring», destinos calculados en los compartidos 35/46/71/74).

**Qué verificar** (como §18):
- sin warps de entrada;
- ningún script retail la empuja antes de un cambio de mapa;
- máscara de nativas 0x243;
- campo «parent» tras `ZoneCloner.cloneIntoSlot`;
- en Azahar: carga, NPC, guardar y cargar.

## 4. Pasos

**Integrador**:
1. Asignar *T* y los works de la Torre (registro de zonas y works por instalación).
2. `island_build.py`, **error latente**: Plaza numera los warps de la isla en el orden de `FACILITIES` entre las que
   tienen puerta, pero `plan()` fija `zone.213.warp.0=0,209,0`. Con la Torre en `DOORS`, la Torre sería el warp 0
   y la salida de la Fábrica llevaría a la Torre. Derivar `door_warp(f)`. Además: `CLONES[T]=517`,
   `zones=209,213,T`, `keeptext.T`/`place.T`, `scripts/zoneT.bin` y comprobar `zone T cloned from`.
3. `overlay.py`: pasar el retail de `maison_retail()` a `tower.zone_script()`.
4. `rental.s` y `patch.py`: ruta por valor, `WORK_TSTREAK`/`WORK_TRECORD`, `CONSTANTS['SLOT_DELTA_TOWER']`.

**Agente** (`frontier/tower.py`, `tests/test_frontier_tower.py`):
5. Verificar la zona asignada.
6. `tower_program`, `tower_reception_routine`, `tower_battle_points`, `TOWER_BP`, copiando el patrón de `factory`
   sin editar `factory.py`.
7. Medir sin emulador dónde decide la Mansión el jefe (`work+0x001`, `0x1e559c`) y los tramos de `0x1e3aac` con
   racha ≥ 19 en Normal.
8. Entrada de bitácora con la lista de cambios para el integrador.

## 5. Pruebas

**Suite**:
- `tower_program` se reconstruye idéntico y su ZO no pasa de 17.248;
- sin «Fábrica Batalla» (4 `ListMenuAdd`), `0x457c` intacto;
- con `pawn_vm`:
  - `WORK_IV ≠ 0` → rechazo;
  - la ruta vale 2 solo durante el desafío;
  - PB en las rachas 7/14/98/105/112 → 1/2/14/15/15; 6 y 13 → nada;
- Unicorn: los accesores de racha por ruta (2 Torre, 1 Fábrica, 0 retail);
- isla: cada interior sale a su puerta y *T* recibe el bit de la Mansión.

**Azahar**:
- puerta (19,46) → *T* → salida a (19,47), y regresión de la Fábrica;
- recepción → selección con el equipo propio → combate; bloque de equipo `0x14200` intacto;
- ronda de 7 desde una racha editada a 6: PB = 1 y la Mansión (`0x1BBC0`) intacta;
- pausa y reanudación; derrota (racha 0, récord conservado); rechazo con Fábrica pausada;
- reinicio sin guardar a mitad; guardar y cargar en *T*;
- racha 19: quién sale en el combate 20.

## 6. Riesgos

1. Numeración de los warps de la isla (paso 2): falla seguro si no se corrige.
2. El hook de alquiler mira `WORK_IV`; con una Fábrica pausada la Torre combatiría con alquileres. v1: negarse en el
   script; después, condicionar el hook a ruta ≠ 2.
3. Guardar a mitad de desafío deja la ruta en 2 hasta la siguiente recepción (como §15).
4. El jefe de la Mansión (`BattleHouse_SetRibbon`, `PokeDiarySet`, posible desbloqueo de Súper) podría salir en la
   Torre con la racha desviada. Hipótesis: en Normal sale en el combate 20.
5. Dificultad con rachas largas en Normal (entrenadores 70–109), sin medir; la alternativa Súper obliga a desviar
   también el rango 1. Lo decide el usuario.
6. Los textos dicen «Mansión Batalla» (texto 619); uno propio necesita la entrada 638 y que `Build.java` acepte otro
   texto para el clon.
7. Choque de works o zonas entre agentes; un solo laboratorio.
8. Doble necesita los accesores de racha del tipo 1, sin medir.

**Estimación**: dificultad baja-media, unas 3 sesiones (agente; integrador con puertas, clon y ASM; pruebas en
Azahar). Una cuarta para textos propios o Doble.
