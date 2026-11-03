# Tubo Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code; no tocó ficheros ni el laboratorio. Solo ejecutó
`frontier/zone_natives.py` (lectura). Reglas de pret/pokeemerald `master` (no `731ad5bf`):
`include/constants/battle_pike.h`, `src/battle_pike.c`, `src/frontier_util.c` y el script de
`BattlePikeThreePathRoom`. Fijarlas contra `731ad5bf` antes de llevarlas a `frontier/data.py`.

## 1. Reglas y v1

**Esmeralda**:
- 3 Pokémon propios (`FRONTIER_PARTY_SIZE`); una ronda son `NUM_PIKE_ROOMS` = 14 salas.
- Entre salas no se cura: PS, PP y estado quedan en el equipo; solo las salas de curación los recuperan.
- Tipos de sala: SINGLE_BATTLE, HEAL_FULL, NPC, STATUS, HEAL_PART (cura 1–2), WILD_MONS, HARD_BATTLE, DOUBLE_BATTLE y
  BRAIN.
- **Pistas** (`sRoomTypeHints`): la categoría de una de las 3 puertas (`Random()%3`): PEOPLE = individual o cura
  total; WHISPERING = NPC o doble; NOSTALGIA = estado o cura parcial; POKEMON = salvaje o combate duro.
- **Puertas sin pista**: tipo uniforme al azar sin los de la categoría de la pista; se quitan el doble con menos de 2
  vivos y el estado si ninguno está sano.
- **Sala de estado** (Kirlia o Dusclops): tóxico 35 %, congelación 25 %, parálisis 20 %, sueño 10 %, quemadura 10 %;
  1 Pokémon hasta la sala 4, 2 hasta la 9 y 3 después; respeta inmunidades de tipo y habilidad.
- **Sala salvaje**: Seviper, Milotic y un tercero por tramo (Dusclops, Electrode, Breloom, Wobbuffet) a nivel
  50 − 4 o 50 − 5.
- **Lucy**: racha de salas 28 y 140, luego cada 56 (`{28, 140, 56, 1}`).
- **PB**: `sBattlePointAwards[racha/14 − 1]`, +10 con el cerebro; valores sin contrastar.

**v1 propuesta**:
- Nivel 50 Individual; equipo = los 3 primeros huecos;
- 14 salas por ronda con pista y contador;
- tipos: combate individual, combate duro, cura total, cura parcial, estado (5 estados con sus probabilidades, sin
  inmunidades) y sala NPC vacía;
- PS y estado persisten; los PP no (desviación);
- racha en salas, PB al acabar la ronda, derrota o retirada terminan.
- Fuera: salvaje, doble, Lucy y pantalla de selección.

## 2. Qué se reutiliza y qué falta

**Se reutiliza**:
- combate de la Mansión: `BattleInstWorkCreate`, `SetRank`, `SetTrainer`, `StartBattle(0,1)`, `IsWin`,
  `BattleInstWorkDelete`, `AddBtlTrainerObj`, `BattleInst_GetBattleStartMsgId`; la copia baja a nivel 50 (§4). Solo
  existen en zonas con el bit 8 (máscara de 517, §19) y no se pueden llamar desde un compartido (§11);
- nativas de los grupos por defecto (medido con `zone_natives.py`, bloques `0xf759c` y `0xf8234`): `CallWildBattle`,
  `_CallTrainerBattleCore`, `PokePartyRecoverAll`, `PokePartyGetParam`, `PokePartySetParam`. Que esos bloques
  estén en la máscara 0x243 de todas las zonas es hipótesis;
- `factory.Routine`, `factory.rand_routine` (LCG con reloj), `HELPERS` con `Program.transplant`, `ListMenuAdd`;
  patrón de `island_script` para recortar despachadores; no escribir scripts desde cero (`reports/faraway.md`);
- `Build.java`: `clones`, `place.N=279`, `zone.N.npc.i`, `zone.N.trigger.i=script,work,value,x,y,w,h,altura`.
  **`zone.N.warp.i` solo reapunta warps que ya existen; no los crea**;
- cambio de mapa por el ayudante `MAPCHANGE` del compartido 79, como el ferry (`island._island_case`).

**Falta**:
- **Conservar PS y estado**: la Mansión combate con una copia (equipo idéntico, §6). Dos ganchos ARM
  (`frontier/asm/pike.s`):
  - H1, en el constructor `0x1e3d2c`: con el Tubo activo, `work+0x30 = [0,1,2]`, `+0x48 = 3`, y tras la cola
    `0x1e3ddc` aplicar a cada copia los PS y el estado guardados en works;
  - H2, al acabar el combate, copiar PS y estado del equipo de combate a esos works.
  - Sitio de H2, campos de PS y estado de `PokemonParam` y si el recálculo de la cola conserva el daño: hipótesis;
    medir con gdb (vigilancia de `work+0x73C`).
- **Racha**: `SetTrainer` elige por la racha de Individual Normal; `WORK_ROUTE` = 2 a works del Tubo
  (`FACTORY_SLOT`); el script del Tubo no llama a `AddWinCount`.
- **Salvaje (v2)**: `CallWildBattle(fila)` usa una fila de la tabla estática (Mew: fila 29). Hipótesis: equipo real
  entero, experiencia y captura; medirlo o hacer otro gancho.
- **Estados**: los aplica H1 desde un work, sin `PokePartySetParam`.

## 3. Interior

**Dos zonas**:
- **Vestíbulo**: clon de **397**, probablemente el interior retail de la cabaña (`oras_buildings.tsv:50` empareja
  `r124_bm_door01` con 397; `zones.tsv`: 1 NPC, 1 warp, área 178). Su warp 0 se reapunta a la puerta del Tubo; la
  recepcionista inscribe, da PB y lleva a la sala.
- **Sala**: sala de 3 caminos y de evento a la vez. Tres disparadores en la pared norte (`zone.N.trigger`); al elegir,
  fundido, sorteo y `MAPCHANGE` a la propia zona. El evento de llegada (como el 1 de 209) muestra el NPC de la sala
  por flag y ejecuta el evento. NPC: pistas, asistente, entrenador y un sustituto de Kirlia/Dusclops (no hay modelos
  de campo de esos Pokémon, sin medir). Donante preferido 397 con la máscara de 517; alternativa, otro clon de 517
  (máscara gratis, script grande que recortar, ZO §11).

**Candidatas** (< 536, máscara por defecto medida): **379/380/381** (Ruta 110; matriz 0; textos 200/199/198; área 165
compartida, que `AreaForker` separa); reserva **2/3/4** (Littleroot; áreas 4/5/6; textos 15/14/13).

**Verificar** (como §18): sin warps de entrada ni scripts que empujen su número; literales en scripts y código; que
su texto de historia no lo use otra zona (se reutilizaría para los textos del Tubo sin entrada 638); que no sea una
sala de la Casa Trampa a la que se llega andando (hipótesis para 379–381); su script de entidades; cargar, entrar y
salir en Azahar.

## 4. Pasos

**Agente**:
1. Medir (con turno de laboratorio): geometría y script de 397 (`Probe disasm`); H1/H2 y la estructura de PS y estado
   con gdb; si `SetTrainer`/`StartBattle` funcionan fuera de la Mansión con la máscara; cómo fija `0x18f8` el tipo en
   `+0x839`.
2. `frontier/pike.py`: constantes (works de estado, sala, racha, récord, PS ×3, estado ×3, pista, tipos de puerta,
   generador; flags de NPC); sorteo de Esmeralda (`ROOM_HINTS`, filtros); programas del vestíbulo y de la sala sobre
   el script de 397; textos ES/EN; `plan_lines()` y `NATIVE_DONORS = {sala: 517}` para el integrador.
3. `frontier/asm/pike.s` con H1/H2.
4. `tests/test_frontier_pike.py`.
5. Entrada de bitácora y lista de cambios para el integrador.

**Integrador**:
1. `DOORS['Pike'] = (vestíbulo, 0)`, `CLONES += {vestíbulo: 397, sala: 397}`, `zones=`/`place.`/disparadores/NPC,
   `zone<N>.bin`.
2. Índices de warp de la isla desde el orden de `FACILITIES`.
3. `patch.py`: `zone_natives` con `{**CLONES, **NATIVE_DONORS}`; ensamblar `pike.s` y comprobar sitios;
   `WORK_ROUTE` = 2; repartir el hueco (quedan unos 2060 de 2556).
4. `overlay.py`: textos del Tubo.
5. Actualizar los tests de la plaza y de clones.

## 5. Pruebas

**Suite** (`pawn_vm`): sorteo de salas y pistas (sin la categoría de la pista; filtros; reparto con muchas semillas);
afectados por estado según la sala; cura total y parcial; contador de 14, fin de ronda, PB, derrota y retirada;
limpieza y reanudación tras guardar en la sala. **Unicorn**: H1/H2 con el Tubo activo e inactivo; la Mansión y la
Fábrica sin cambios. **Plan**: líneas, warps, máscaras; reconstrucción idéntica; ZO ≤ 17.248.

**Azahar**: puerta (5,69) → vestíbulo → salida a (5,70); a la sala; 3 puertas y pista; combate perdido y ganado con
PS conservados en la siguiente sala; estado aplicado y visible; curas; guardar en la sala y recargar; ronda de 14 con
PB; equipo real idéntico al salir (`save_fixture.py`); Fábrica y plaza sin regresiones.

## 6. Riesgos y estimación

- Nativas de la Mansión fuera de su geometría (cámara, colocación del rival): pueden colgar o verse mal. Plan B, la
  sala como clon de 517.
- Equipo de combate ya liberado cuando corre H2, o formato del estado distinto del supuesto.
- Eventos propios del cazatesoros en el script de 397.
- Cambio de mapa a la misma zona sin probar.
- Los índices de warp se mueven al abrir otras instalaciones; hueco de código compartido; tabla de PB sin contrastar.

Dudas para el usuario: ¿selección de 3 en la v1 o los 3 primeros huecos? ¿Se aceptan las desviaciones (sin PP ni
inmunidades)? ¿Salvaje con el equipo real o en la v2?

**Estimación**: media-alta (el PLAN decía media) por H1/H2. v1: 4–6 sesiones (medidas 1–2, módulo y tests 2,
integración y Azahar 1–2). v2 (salvaje, doble, Lucy, selección): 3–4 más.
