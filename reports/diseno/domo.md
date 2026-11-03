# Domo Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code; no tocó ficheros ni el laboratorio. «Medido» = sale del repo (se
cita la fuente). Solo ejecutó `frontier/disasm_code.py` (lectura) sobre `baseline/oras/repolished/exefs/code.bin`.
Las reglas de Esmeralda son **de memoria**: contrastarlas con pret/pokeemerald (`src/battle_dome.c`,
`src/frontier_util.c`) antes de fijar constantes, como PLAN §1.

## 1. Reglas y alcance de la v1

**Esmeralda** (de memoria): Nivel 50 o Libre, Individual o Doble; 3 propios sin especies ni objetos repetidos; torneo
de 16 (`DOME_TOURNAMENT_TRAINERS_COUNT`), 4 rondas; entre rondas, cuadro, ficha del rival (sus 3 y su estilo),
descanso o guardado; en cada combate eliges 2 de 3 y el rival elige 2 de los suyos según tu equipo; la racha cuenta
torneos; PB al ganar el torneo (`sBattlePointAwards`, sin contrastar); Tucker en la final de los torneos 5 y 10
(`{4, 9, 5, 0}`, sin contrastar).

**v1** (Nivel 50 Individual):
- se conserva: inscribir 3; 4 rondas con su nombre; ver los 3 del rival antes de elegir; elegir 2 de 3; rival con 2
  de sus 3 (al azar); pausa entre rondas; PB al ganar el torneo; racha y récord propios; la derrota termina;
- se omite: cuadro gráfico, simulación de los otros 14, ranking, estilo del rival, Tucker, Doble y Libre.

## 2. Qué se reutiliza y qué falta

**Se reutiliza** (medido):
- combate de la Mansión (§1, §4): `BattleInstWorkCreate`, `SetTrainer`, `StartBattle`, `IsWin`, bucle `0x1e1c`; el
  rival lo elige la Mansión según la racha, solo cambia su equipo;
- copia del equipo (§4): la partida no se toca;
- **medido en esta lectura**: tras el sitio del hook, el bucle original relee el número de elegidos (`work+0x48`, en
  `0x1e3da0`) y los índices (`work+0x30`, en `0x1e3db4`). Basta con escribir allí los 2 huecos elegidos en la rama
  inactiva de `rental_hook`;
- racha propia con `FACTORY_SLOT` (`rental.s`, §15), generalizada por valor de `WORK_ROUTE` (1 Fábrica, 2 Domo);
- de la Fábrica: `factory.Routine`, `_index`, `HELPERS`, `Program.transplant`; patrones de `reception_routine`,
  `after_win_routine` y `battle_points` (4 combates por ronda en vez de 7); `_clear` en `0x1458` y `0x2210`;
- datos de rivales: `factory.slots()`/`slot_cells()`, el bloque `factory_slots` del script 5 y las líneas «Especie
  (Objeto)» del texto 637 (`line_of`) para enseñar el equipo del rival;
- script compartido 5: la fila `GlobalCall` 9770–9779 apunta al texto 637 (§11); la Fábrica usa 9771 y 9772, quedan
  **9773–9779**. Mide 9.385 bytes; el mayor retail, 29.082 (§11);
- sala y nativas: clon de 517 como 213 (`CLONES`, `patch.zone_natives`, §19).

**Falta**:
- **(a) Forzar el equipo del rival (código)**. Medido en esta lectura: en `0x1e4b30` el constructor carga el archivo
  en `r2` (`ldr r2,[sp,#0xe0]`) justo antes del sitio de `rival_hook` (`0x1e4b34`, `ldrh r4,[r0,#4]`). Con el Domo
  activo, `rival_hook` pone `r4` = índice y `r2` = `0xb6`/`0xb8` según el bit 15 de un work (conjuntos Súper con
  rango Normal, sin probar). Riesgo: si dos conjuntos forzados repiten especie u objeto, el constructor vuelve a
  `0x1e4b24` para siempre; el script debe evitarlo.
- **(b) Rival con 2 Pokémon (código)**. Medido: en `0x1e3480`, la tabla de saltos de `+0x839` pone `r6 = 3` para
  Individual en `0x1e3548`; `r6` va como número a `0x1e4a94` y al bucle de `AddMember`. Un `bl` en `0x1e3548` que deje
  `r6 = 2` con el Domo activo (`lr`, `r0`–`r3` e `ip` libres ahí).
- **(c) Elegir 2 de 3**: no hay nativa del Domo.
  - Propuesta A: inscripción con menús propios con los motes (`WordSetTemotiMonsNickName`, en `oras_natives.tsv`,
    argumentos y `[VAR]` sin medir); comprobar huevo (`PokeTemotiIsEgg`) y repetidos (`PokePartyGetParam`, sin
    medir); guardar los 3 huecos en works y saltar `BattleHouse_CallPartySelectApp` como `overlay.maison_program` en
    `0x457c`; en cada ronda, 2 `ListMenu` de los 3 → work → el hook escribe `+0x30`/`+0x48 = 2`.
  - Alternativa B: probar `BattleHouse_CallPartySelectApp(4, 0x800C)` (modo Multi, el rival de Multi lleva 2, §1).
    Da la pantalla real, pero no limita a los 3 inscritos. `CallPokeSelect` también podría servir (sin medir).
- **(d) Torneo terminado**: tras la 4.ª victoria (racha % 4 = 0) salir del bucle por el camino de «Pausar» de
  `0x3b90` (por medir), conservando la racha; la siguiente recepción abre un torneo nuevo.
- **(e) Exclusión con la Fábrica**: una Fábrica pausada (`WORK_IV ≠ 0`) toma la rama de alquiler antes que el Domo.
  Cada recepción debe negarse si la otra instalación está a medias.

## 3. Interior

Donante 517: la única con todo el flujo de combate, probada como 213 (§19–§22). 448 y 520 registran las nativas pero
sus scripts no tienen el flujo; trasplantar el script de 517 a otro mapa rompería cámaras (`0x45d4`), NPC y
recorridos. La sala es igual que la de la Fábrica (decoración, más adelante).

Script propio `scripts/zone<N>.bin` (lo carga `Build.editZone` si la zona está en `zones=`): 517 **retail** más el
Domo, sin la Fábrica; ZO ≤ 17.248 (§11); lo grande al script 5.

**Candidatas** (`repurpose.txt`, < 536, `matrix=0`): **456** (Fallarbor Town); 457, 458, 459 (área 111, compartida
con los interiores 242, 243, 248 y 249). Descarta, por hipótesis de que el código las intercambia: 135–138, 140–157,
119–120, 178–180, 329, 340, 351–352, 534 y 535. Con ese criterio quedan cuatro candidatas para seis instalaciones:
asigna el integrador.

**Verificar** (como §18): ningún `PUSH` de N antes de un cambio de mapa en los 1157 scripts; ningún literal N en
`code.bin` o los CRO (`ids.code_literals`) ni tablas de zona a zona; máscara 0x243; en Azahar, entrar, salir, guardar
dentro y recargar.

## 4. Pasos

**Agente** (`frontier/dome.py`, `frontier/asm/dome.s`, tests):
1. Medir sin Azahar: `WordSetTemotiMonsNickName`, `PokePartyGetParam` y `CallPokeSelect` en sus usos retail
   (`pawn.listing`); el `[VAR]` del mote; la rama de pausa en `0x2290`/`0x3b90`; el sitio del bucle antes de
   `StartBattle` (`zone517.lst`); el umbral de `IsBoss` (`0x1e559c`); works libres con `python frontier/ids.py`.
2. `dome.zone_program(retail517)`: opción «Domo Batalla» en `0x14f4`; `dome_reception` (inscripción, reanudación,
   `WORK_ROUTE = 2`, `SetRank(0)`); saltar la app en `0x457c`; `GlobalCall` antes de cada combate; `after_win` (fin
   de torneo); PB en `0x3de4`; limpieza en `0x1458` y `0x2210`.
3. `dome.shared_parts(p, helpers, cells, levels)`, casos 9773–9775: inscripción; sorteo de los 3 del rival sin
   repetir especie ni objeto, nivel según torneos ganados; vista previa y elección de 2; orden de works para que los
   2 del rival vayan primero.
4. `dome.s`: rama Domo de `rental_hook`, `rival_hook` forzado, número de rivales en `0x1e3548`, `FACTORY_SLOT` por
   valor de ruta.
5. Entrada de bitácora y lista de cambios para el integrador.

**Integrador**:
- `island_build`: `DOORS['Dome'] = (N, 0)`, `CLONES[N] = 517`, `zones=…,N`, `keeptext.N=1`, `place.N=279`,
  `scripts/zoneN.bin`. **Importante** (medido en `FrontierPlaza.linkDoors`): los warps se numeran en el orden de
  `FACILITIES`; el Domo pasa a ser el warp 0 y la Fábrica el 1, y la salida de 213 tendría que ser
  `zone.213.warp.0=0,209,1`. Calcularlo desde el orden; reescribir `test_plaza_plan_links_only_the_factory`.
- `patch.py`: ensamblar `dome.s`; sitio `0x1e3548`; extensiones de `rival_hook` y de la rama inactiva; works y delta
  de racha del Domo.
- `overlay.py`: línea de opción en el texto 619 (189); líneas del Domo al final del 637; componer el script 5 de la
  Fábrica más el del Domo; pasar el script de la zona a `island_build`.
- `factory.reception_routine`: negarse si el Domo está a medias.

## 5. Pruebas

**Suite**: `tests/test_frontier_dome.py` con `pawn_vm` (inscripción con rechazo de huevos y repetidos y cancelación;
sorteo del rival sin repeticiones, nivel por torneos, estable al reanudar; elección de 2; fin de torneo cada 4; PB
solo al final; limpieza al perder, conservación al pausar; exclusión con la Fábrica; la Mansión intacta con el Domo
inactivo). Unicorn: rama Domo escribe `+0x30`/`+0x48 = 2` y la inactiva no cambia; rivales 3→2 solo con el Domo;
`rival_hook` forzado con el Domo y copia de la Fábrica intacta; ruta 0/1/2. Overlay e isla: reconstrucción idéntica,
ZO ≤ 17.248, plan y warps, máscara de N, works libres (`test_frontier_ids`). Romper a mano cada guarda.

**Azahar**: puerta del Domo y salida a (6,57); **repetir la Fábrica**, que cambia de número de warp; la
recepcionista habla; inscripción → vista previa → elección, con exactamente los 2 elegidos contra 2 de los 3 vistos
(gdb en el hook, `r6 = 2`); 4 rondas, PB y racha, con `main-maison-maison20` la Mansión sigue en 20/20; perder en la
ronda 1 y en la final con el bloque de equipo idéntico (`save_fixture.py`); pausar, recargar, reanudar y cambiar el
equipo durante la pausa; exclusión con la Fábrica; guardar dentro de N.

## 6. Riesgos y estimación

- Bucle sin fin del constructor si se repiten los conjuntos forzados.
- El jefe de la Mansión con la racha desviada: el forzado podría sustituir su equipo o aparecer donde no toca.
- `[VAR]` del mote y nativas del equipo sin medir; sin la app de la Mansión no se aplican sus vetos.
- Cambiar el equipo durante una pausa: guardar las especies y anular si no coinciden.
- Salir del bucle al terminar el torneo; límites del texto 637 y del script 5; margen del ZO.
- Cada puerta nueva renumera los warps.
- Espacio de código: 496 de 2.556 bytes usados; el Domo añade unos 200 (estimación).
- Constantes de Esmeralda sin contrastar; nada en consola.

**Dificultad**: media-alta (más que la «media» del PLAN), por los dos sitios de código nuevos y el rival forzado.
**Sesiones**: unas 4 (±1).
