# Pirámide Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code; no tocó ficheros ni el laboratorio. [medido] = está en el repo con su
fuente; [hipótesis] = sin medir. Las reglas de Esmeralda las leyó en pret/pokeemerald@master por la web
(`src/battle_pyramid.c`, `src/frontier_util.c`): hay que fijarlas a un commit, como PLAN §1.

## 1. Reglas de Esmeralda y v1

**Esmeralda**:
- **Pisos**: 7 por desafío (`FRONTIER_STAGES_PER_CHALLENGE`). Cuadrícula de 4×4 casillas
  (`NUM_PYRAMID_FLOOR_SQUARES`) con trazados sorteados (`layoutOffsets`); entrada y salida en casillas distintas.
- **Entrenadores y objetos**: 16 plantillas de piso (`sPyramidFloorTemplates`), 3–8 entrenadores y 2–7 objetos.
  Objetos de `sPickupItemsLvl50[ronda][10]`.
- **Racha**: `pyramidWinStreaks` +1 por piso; ronda = racha/7.
- **PB por desafío**: 5, 5, 6, 6, 7, 7… hasta 15 (`sBattlePointAwards`).
- **Brandon**: racha 21 y 70 (`sFrontierBrainStreakAppearances[PYRAMID] = {21,70,35,0}`).
- **Salvajes** por ronda (`sLevel50WildMonPointers`), nivel de la plantilla −5…+5; desde la racha 140, IV 15–31.
- **Oscuridad**: `pyramidLightRadius` crece hasta 120 (`PYRAMID_LIGHT_INCR_RADIUS`); no se vio qué la hace crecer.
- **Bolsa propia** con Hiperpoción y Éter (`InitPyramidBagItems`); sin objetos equipados (`CheckPartyIneligibility`).
- Sin curas entre combates (conocimiento del juego, no visto en la fuente).

**v1 propuesta**:
- vestíbulo con recepcionista: 3 con `BattleHouse_CallPartySelectApp`, guardar, al piso 1;
- 7 pisos con **trazado fijo** (mapa de una cueva retail clonada, sin pintar);
- 3–4 entrenadores fijos por piso; cada combate es **de la Mansión** (`SetTrainer` + `StartBattle(0,1)` + `IsWin`),
  copia del equipo a nivel 50, sin bolsa ni experiencia (§4);
- una «escalera» (NPC u objeto con script) hace `_MapChangeCore` al piso siguiente;
- racha por pisos, PB al llegar arriba y vuelta al vestíbulo al perder.

Fuera de la v1: oscuridad, salvajes, objetos del suelo, bolsa propia, PS persistentes y Brandon. Los salvajes por
casilla y `CallWildBattle` combaten con el equipo real de 6, a su nivel, con experiencia y bolsa, y dejan capturar;
los objetos no sirven sin PS persistentes.

## 2. Qué se reutiliza y qué falta

**Se reutiliza** [medido]:
- `Build.java cloneZone` (mapa y área propios, `keeptext`, `place`) y `editZone` (NPC con `regdonor.<modelo>`,
  warps, disparadores con condición de work);
- `scripts/pawn.py` (`Program.from_script`, `transplant`, `sysreq`, `build_script`), scripts sobre el retail del
  donante como `island_build.island_script`;
- `factory.HELPERS`, y `CHALLENGE`/`LOST` como modelo;
- `_MapChangeCore` por el ayudante `0x724` del compartido 79 (el del ferry, §16);
- `patch.zone_natives` (§19), `scripts/pawn_vm.py`, `build_patch.guarded_texts`, `frontier/ids.py`.

**Falta**:
1. **Máscara de nativas separada del donante geométrico**: hoy `CLONES` sirve para las dos cosas, y un piso clonado
   de una cueva necesita la máscara de 517 (bit 8).
2. **Selección persistente**: `work+0x30/+0x48` vive en el montón. Medir si sobrevive a `_MapChangeCore` y a guardar
   y cargar. Si no, una rama en `frontier/asm/rental.s` que tome los 3 índices de works guardados.
3. **Rival por racha propia**: `SetTrainer` → `0x1e3aac` usa la racha de la Mansión; ampliar `WORK_ROUTE`.
4. **Works y flags propios** que no choquen con los de la Fábrica (16410–16414, 16429, 16433–16435, 16437–16439).
5. **Warp de entrada del donante**: `Build.java` no borra warps; reasignarlo o taparlo.

## 3. Interior

**Zonas**: la v1 necesita 2 y conviene pedir 3:
- V (vestíbulo);
- P1 (piso al que se vuelve a entrar 7 veces con un work de piso; Esmeralda también usa un solo mapa);
- P2 por si volver a entrar en la misma zona falla [hipótesis]: se alternan P1/P2.

Reservar 2 más para trazados y la cima de Brandon.

**Donantes del piso** (`work/frontier/island/zones.tsv` [medido]): Cueva Espejismo 192 (0 NPC, 1 warp, 0
disparadores, 0 props), 195 (2 warps), 199 (3 warps); Desert Ruins 77 (sala de Regirock, 3 warps, 2 NPC); Granite
Cave 79 (5 warps, demasiados). Comprobar tamaño, suelo que se rompe o arena y número de warps.

**Donantes del vestíbulo**: 520 (casa del Resort con el grupo de nativas de la Mansión, §19; 4 NPC, 1 warp; leer su
script antes) o un clon de 517 como 213 (más pesado: ZO 15.472 de 17.248).

**Zonas libres** (< 536; `repurpose.txt` + `zones.tsv` + `work/all-encounters.json` [medido]):
- recomendadas: 140–144 (New Mauville), matriz 0, sin encuentros, 5 seguidas;
- alternativas: 178–180, 135–138, 119/120, 149/150/152/153/157 y 168;
- evitar: 151 (encuentros de surf y caña, que el clon conserva), 532/533 (matrices 428/429; 533 con encuentros).

**Verificar** (como §18): ningún warp ni script la alcanza (incluidos los destinos calculados de 35/46/71/74); su
texto (p. ej. 367–371) no lo usa otra zona ni `GlobalCall`; nombre de lugar; encuentros vacíos; máscara 0x243;
literales del número.

**Cota de carga**: `LOAD_BUDGET` (§23) es del área 231 pintada. Un piso sin pintar lleva copia de un área retail que
ya carga; si se pinta, hace falta otra medida.

## 4. Pasos

**Integrador**:
1. Asignar V, P1, P2, works, flags y lugar.
2. **Experimento 0 en Azahar** (decide el diseño): `StartBattle` desde un script que no sea el de 517 con la máscara
   copiada; si el trabajo de la instalación sobrevive a `_MapChangeCore` y a guardar/cargar; `_MapChangeCore` a la
   misma zona; un piso clonado con sus warps reasignados.
3. `island_build`: `CLONES` con V/P1:192/P2:195; un diccionario de máscaras `{V: 517, P1: 517, P2: 517}` para
   `patch.build`; `DOORS['Pyramid'] = (V, 0)`; el plan de NPC, disparadores y warps de `pyramid.plan_lines()`.
4. **Fallo latente**: `plan()` fija `zone.213.warp.0=0,209,0`, pero los warps de la isla siguen el orden de
   `FACILITIES` entre las que tienen puerta. Calcular el índice.
5. `patch.py`/`rental.s`: rama de índices desde works y ruta de racha (si el experimento 0 lo exige).
6. `overlay.py`: `pyramid.build(...)` para scripts y textos de V/P1/P2.

**Agente** (`frontier/pyramid.py`):
- script de V: `BattleInstWorkCreate`, `SetRank(0)`, selección, `GlobalCall 2003`, works de estado y
  `_MapChangeCore` a P1; al volver, PB, racha y limpieza;
- script de pisos: llegada (works de entrenador a cero, NPC visibles u ocultos), entrenador (combate de la Mansión,
  `IsWin`, marcar y ocultar), derrota (limpieza y vuelta a V), escalera (piso + 1; en el 7.º, a V con PB);
- textos ES/EN; constantes (works, flags, coordenadas, tabla de PB).

## 5. Pruebas

**Suite** (`tests/test_frontier_pyramid.py`, `pawn_vm`): inscripción aceptada y cancelada; orden de nativas;
victoria y derrota; escalera 1→7; PB 1–3 y repetición del último; racha y récord; abandono y reanudación; ida y
vuelta byte a byte; ZO ≤ 17.248; líneas del plan. Integrador: actualizar los tests de la plaza, de clones y de
parche, y Unicorn para la rama nueva.

**Azahar** (`f6h_saved_plaza.sav`): experimento 0; puerta → V → salida a (32,58); inscripción y combate en P1;
entrenador oculto; escalera y PB; derrota en el piso 1 y el 7; guardar en un piso y recargar; equipo y caja
idénticos (`save_fixture.py`).

## 6. Riesgos y estimación

- Trabajo de la instalación [hipótesis]: si no sobrevive, rama del hook; reordenar el equipo con el menú X dejaría
  índices mal (guardar y comparar el PID).
- Nativas de la Mansión fuera de 517, sin la colocación del rival (`0x2b98`): sin probar.
- Volver a entrar en la misma zona: sin medir.
- NPC genérico frente a entrenador de `maisontr`.
- v1 se aparta de Esmeralda: cura en cada combate, admite objetos, la Mansión no excluye especies (§13).
- La v2 es otra cosa: PS persistentes, objetos, «salvajes» como combates de la Mansión de 1 Pokémon (`0x1e34d0`),
  oscuridad (`CallFlashEffect` [hipótesis]) y Brandon.

**Estimación**: v1 **alta**, 4–6 sesiones del agente y 1–2 del integrador, más 1 de laboratorio para el experimento
0. Algo parecido a Esmeralda: 6–10 sesiones más.
