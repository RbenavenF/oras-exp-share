# Frente de Batalla de Esmeralda en ORAS Repolished — plan

Proyecto principal desde el 2026-11-01. Primera instalación: **Fábrica Batalla**.
El evento de Mew (`faraway/`, `reports/faraway.md`) queda en pausa: era la prueba de
concepto de que se puede añadir contenido nuevo por LayeredFS, y lo ha demostrado
(funciona en consola, con fallos conocidos anotados allí).

Este documento es el punto de entrada para cualquier sesión, sea Claude Code o Codex.
La bitácora `frontier/BITACORA.md` dice en qué punto exacto está el trabajo.

## 0. Arranque de una sesión nueva

1. Lee `AGENTS.md` (reglas del repositorio), este plan y las **últimas entradas** de
   `frontier/BITACORA.md`.
2. `source scripts/env.sh`; `git log --oneline -15`; `git status`.
3. Si la última entrada de la bitácora dice «en curso», retoma su «Siguiente paso».
   No repitas mediciones que ya figuran en §3 o en la bitácora: compruébalas con
   `python frontier/survey.py` si dudas.
4. Antes de terminar la sesión, y en cada commit, añade una entrada a la bitácora
   (formato en §8). Si el contexto se agota a mitad de tarea, la entrada se escribe
   igualmente con estado «en curso».

Mensaje para abrir la conversación nueva (copiar tal cual):

> Seguimos con el Frente de Batalla en ORAS Repolished. Lee AGENTS.md,
> frontier/PLAN.md y las últimas entradas de frontier/BITACORA.md, y continúa
> por el siguiente paso pendiente. Deja trazabilidad en la bitácora en cada hito
> y antes de terminar, porque alterno entre Claude Code y Codex.

## 1. Objetivo

Reproducir la Fábrica Batalla de Pokémon Esmeralda dentro de ORAS Repolished 1.7.6,
encadenada con los mods ya entregados (Repartir Exp. equipable y racha DexNav, v0.5;
evento de Mew opcional). Después, el resto de instalaciones del Frente.

**Visión final (usuario, 2026-11-02)**: una expansión tipo evento o DLC. Un objeto, u
otra condición, desbloquea una zona nueva que sea un clon del Frente Batalla de
Esmeralda: una isla con sus edificios, a la que se llega como al evento de Mew (objeto
→ viaje → zona propia; `reports/faraway.md`). La Fábrica dentro de la Mansión (F4–F5)
es el banco de pruebas de las mecánicas; la ubicación definitiva es esa zona (F6). La
propuesta concreta y lo que falta decidir están en §5.6.

Reglas de la Fábrica que vamos a reproducir. Contrastadas el 2026-11-01 con
pret/pokeemerald `731ad5bf` (`src/battle_factory.c`, `src/battle_factory_screen.c`,
`src/frontier_util.c`, scripts de `BattleFactoryLobby`/`PreBattleRoom`/`BattleRoom`);
las constantes están en `frontier/data.py`:

- Modalidades Nivel 50 y Nivel Libre; Individual y Doble. Empezamos por **Nivel 50
  Individual**.
- El jugador no usa su equipo: elige **3 Pokémon de alquiler de entre 6** al azar.
  En los 6 no se repite especie ni objeto, y no sale Unown (`GenerateInitialRentalMons`).
- Una ronda son **7 combates** (`FRONTIER_STAGES_PER_CHALLENGE`). Tras cada victoria,
  salvo la 7.ª, se ofrece **cambiar uno** de los alquilados por uno de los 3 del rival
  derrotado, o no cambiar; los cambios se cuentan en la racha.
- Al acabar la ronda, los alquileres se devuelven y la siguiente empieza con 6 nuevos.
  El conjunto de alquiler depende de la ronda (`sInitialRentalMonRanges`): ronda 1 un
  rango débil, rondas 2–3 dos copias de un rango medio, rondas 4–7 cuatro copias del
  rango fuerte, ronda 8+ todas las copias fuertes juntas. Con 15/22/29/36/43 alquileres
  acumulados, 1–5 de los 6 salen del nivel de la ronda siguiente (`GetNumPastRentalsRank`).
- IV fijos por ronda (`sFixedIVTable`): 3, 6, 9, 12, 15, 21, 31, 31 (el último rival
  de la ronda usa el valor alto: 6, 9, 12, 15, 18, 31, 31, 31). En retail la ronda 9
  lee fuera de la tabla; usamos el comportamiento `BUGFIX` (31).
- Rivales: mismo rango que los alquileres de la ronda, sin especies de los 6
  alquileres del jugador. Primera versión: el rival lo genera la Mansión (§5.4).
- PB al ganar la ronda (7.º combate): 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9 por ronda
  (Individual), +10 si fue el jefe.
- Jefe (Noland): combate 21 (símbolo de plata) y 42 (oro); con los dos símbolos,
  en el 21, el 42 y cada 21 después (`sFrontierBrainStreakAppearances = {21, 42, 21, 1}`).
- Correspondencia con los datos de la Mansión (medida, `reports/frontier.md` §7):
  ronda 1 = `maisonpkN` 66–131, rondas 2–3 = `maisonpkN` 132–169 y 170–207,
  rondas 4–7 = los cuatro niveles de `maisonpkS`, ronda 8+ = los cuatro juntos.

Lo que no cambia: el equipo, la caja y la partida del jugador tienen que quedar
idénticos al salir, ganes, pierdas o apagues a mitad.

## 2. Reglas de trabajo (resumen; mandan `AGENTS.md` y el usuario)

- Commits por hito funcional, autor `rubenb114 <rubenb114@hotmail.com>`; el pie del
  mensaje identifica al agente (ver §8).
- Implementar, no solo proponer. No inventar identificadores, offsets, nativas ni
  resultados: todo dato lleva su fuente (script, comando o volcado).
- Nada se declara funcional sin evidencia de ejecución (Azahar o consola), guardada
  en `work/` y citada en `reports/`.
- `inputs/` y la partida original no se tocan; las pruebas usan copias en `work/`.
- No se suben ROM, ejecutables, partidas, claves ni datos extraídos del juego; los
  generadores leen el volcado en tiempo de construcción y comprueban hashes y bytes.
- Nada se instala en la consola automáticamente.
- Preguntar al usuario solo si falta un archivo, una credencial o una decisión
  imprescindible.

## 3. Hechos medidos (2026-11-01)

Reproducibles con `python frontier/survey.py [--listings work/frontier/survey]`.

| Hecho | Valor | Fuente |
|---|---|---|
| Datos de la Mansión Batalla | `a/1/8/2` maisonpkN (999 conjuntos), `a/1/8/3` maisontrN (129 entrenadores), `a/1/8/4` maisonpkS (999), `a/1/8/5` maisontrS (217). Repolished no los cambia. | pk3DS `GARCReference_AO`; survey |
| Formato de un conjunto | 16 bytes: especie u16, 4 movimientos u16, bits de EV (6), naturaleza u8, objeto u16, forma u16 | pk3DS `Structures/Gen6/Maison6.cs` |
| Formato de entrenador | clase u16, número u16, lista de índices de conjunto u16 | idem |
| Zona de la Mansión | **517**: texto 619 («Bienvenido a la Mansión Batalla…»); script de 4129 líneas con todo el flujo | survey (cabecera de zona, u16 en +6) |
| Otras zonas del Resort | 516 (texto 620), 518–524 (casas y conserje del Resort), 211 (texto 625: «Una réplica de la Mansión Batalla de Kalos…» y «¡Luz verde para el proyecto Frente de Batalla!») | survey |
| Nativas de la Mansión (zona 517) | `BattleInstWorkCreate/Delete`, `BattleHouse_CallPartySelectApp`, `BattleHouse_IsBattleBoxUsed`, `SetTrainer`, `StartBattle`, `IsWin`, `AddWinCount`, `ClearWinCount`, `GetWinCount`, `GetMyWinCount`, `IsBoss`, `GetRank`, `PlayerGetBP`, `PlayerSetBP`, `BattleInst_GetBattleStartMsgId`, `BattleHouse_SetRibbon`, `BattleHouse_End`… | survey; nombres de CTRMap-F5 `oras_natives.tsv` |
| Orden en el script 517 | `PlayerSetBP` 0x4c, `SetTrainer` 0x13b0, `BattleInstWorkCreate` 0x1508, `GetRank` 0x1768, `StartBattle` 0x1ee4, `AddWinCount` 0x1f60, `IsBoss` 0x205c | `work/frontier/survey/zone517.lst` |
| Equipo por script | Existe `PokePartyToBox` (equipo→caja, 1 uso retail) y `BoxAddPoke`, pero **ninguna nativa devuelve un Pokémon de la caja al equipo**. `PokePartyAddParam` no tiene usos retail. | survey |
| Textos por script | Hay `WordSetItemName`, `WordSetWazaName`, `WordSetSeikakuName`, `WordSetTokuseiName`, `WordSetPokeTypeName`; **no hay** una nativa para el nombre de una especie arbitraria | `oras_natives.tsv` |
| Módulos con nombre relacionado (sin analizar) | `DllBattleHouseConnect.cro`, `DllBattlePartySelect.cro`, `DllPoke3Select.cro`, `DllTrialHouseResult.cro` | listado de RomFS |

Consecuencia del hecho «equipo por script»: **cambiar el equipo del jugador por
alquileres no se puede hacer solo con scripts**. Hace falta código nativo (§5).

## 4. Base disponible en el repositorio

- `scripts/pawn.py`: códec y ensamblador de scripts Pawn de GF (los 1157 scripts
  retail se reconstruyen byte a byte); trasplante de rutinas entre scripts.
- `faraway/event.py` y `faraway/build.py`: patrón probado para **ampliar un script
  retail con casos nuevos** (los scripts escritos desde cero se colgaban), textos ES/EN,
  objetos y combates estáticos.
- CTRMap-F5 (`tools/CTRMap-F5`) con nuestras clases en `faraway/java`: clonar zonas,
  NPC, warps, pintar el mapa. Zonas «???» libres usadas: 473/474 (Mew).
- `scripts/build_patch.py`: parcheo de CRO (`DllBattle.cro`) con actualización de
  hashes CRO y tabla CRR, comprobando bytes de entrada.
- Laboratorio: Azahar con gdb (`faraway/lab.sh`, `gdbctl.sh`), warps de desarrollo
  (`faraway/dev_overlay.sh`), lectura y escritura de partidas
  (`scripts/save_fixture.py`, `faraway/save_event.py`), Unicorn para ejecutar rutinas
  ARM sueltas (`scripts/validate_arm.py`).
- Trampas ya pagadas: ver `reports/faraway.md` §Errores y la memoria del proyecto
  (`publics` de script que se mueven, entradas de NPC completas, teletransporte por
  partida que cuelga, teclas del laboratorio).

## 5. Arquitectura propuesta

**Idea central: la Fábrica es la Mansión Batalla con equipo de alquiler.**
La Mansión ya resuelve lo difícil: elegir rival de `maisontr`, generar su equipo de
`maisonpk`, nivel 50, racha, PB, jefe y el combate en sí. Lo nuevo es:

1. **Equipo de alquiler.** Dos opciones; F1 decide con mediciones:
   - **A (preferida): sustituir el equipo del combate, no el de la partida.**
     La Mansión construye el equipo que entra en combate a partir de la selección
     (`BattleHouse_CallPartySelectApp` → trabajo de la instalación → `StartBattle`).
     Si en ese punto se cargan 3 Pokémon generados desde `maisonpk`, el equipo
     guardado nunca se toca y apagar a mitad no puede perder nada.
   - **B (alternativa): copia del equipo en un hueco libre de la partida y
     restauración**, con restauración forzada al cargar si la copia sigue marcada.
     Más riesgo: hay que demostrar que ningún camino deja el equipo perdido.
   - Descartada: solo scripts (no hay nativa caja→equipo, §3).
2. **Estado de la Fábrica en la partida**: modalidad, ronda, combate, racha, los 3
   índices de conjunto alquilados, los del último rival (para el cambio) y récords.
   Works y flags libres medidos con el método del evento de Mew (ningún script, NPC,
   entrada de PKHeX ni literal de código los usa; `reports/faraway.md` §Identificadores).
3. **Selección de 3 de 6 y cambio tras la victoria**: primera versión con `ListMenu`
   del script (los nombres de especie no tienen `WordSet`: o se escriben en el texto
   de la zona, o hace falta una nativa nueva). Más adelante, reutilizar una pantalla
   del juego si `DllPoke3Select` o `DllBattlePartySelect` encajan.
4. **Rival**: primera versión, la generación de la Mansión tal cual. Después, rival
   sacado del mismo nivel de alquiler que el jugador, como en Esmeralda.
5. **Código nuevo**: hay que medir dónde cabe (relleno o código muerto en
   `code.bin` o en un CRO, o ampliar con el exheader que acepte Luma; **ninguna de
   estas vías está comprobada todavía**). El parche se genera como hasta ahora:
   IPS/bytes con comprobación de hash y bytes de entrada.
6. **Ubicación**: primera versión, la opción «Fábrica Batalla» de la recepcionista de la
   zona 517, que usa las salas de la Mansión (hecho, `reports/frontier.md` §11).
   Destino (visión del usuario, §1): una zona de expansión desbloqueada por un objeto.
   Decidido por el usuario (2026-11-02):
   - **Objeto**: objeto clave nuevo «Pase del Frente», en un hueco de objeto libre, como
     el Mapa Viejo del evento de Mew.
   - **Cuándo**: tras ganar la Liga (hay que medir el flag de campeón).
   - **Viaje**: en el **ferry** de Calagua, no en la barca de Arenque: con el pase, el
     ferry ofrece un destino nuevo, «Isla del Frente», como el S.S. Marea de Esmeralda.
     El ferry retail es el script compartido 79 (`reports/faraway.md`).
   - **Entrega**: un marinero del puerto de Calagua, al hablarle con la Liga ganada
     (propuesta aceptada por el usuario; se puede cambiar más adelante).
   - **Activación**: el mod de Luma hace de DLC. La zona y los scripts van siempre en el
     paquete, y el pase decide si el ferry ofrece el destino. ORAS no tiene código para
     contenido descargable de verdad: un título de DLC aparte no lo leería nadie, así
     que no es una vía.
   - **Zona**: zona nueva propia (como Isla Suprema en el evento de Mew), con la geometría
     clonada del exterior del Resort Batalla (propuesta aceptada) y puertas a interiores
     clonados. Ya probado con
     CTRMap-F5: clonar zonas, mapa y área propios, entidades (`faraway/java`). Un mapa
     3D nuevo con el trazado de Esmeralda no es realista; se compone con mapas de ORAS.
   - **Distribución**: la del Frente de Esmeralda (petición del usuario, 2026-11-02): la
     Torre en el centro, las demás instalaciones alrededor y los caminos como en el
     original, con edificios y piezas de ORAS. Vía prevista: el catálogo de edificios del
     fork de CTRMap-F5 (`tools/CTRMap-F5/src/ctrmap/resources/oras_buildings*.tsv`,
     `MapPainter`). Ese catálogo recorta la geometría de un edificio retail del volcado
     y la estampa en otro mapa. **No usado aún en este proyecto ni probado en consola**
     (el evento de Mew solo pintó hierba). Hay que comprobar colisiones, puertas y
     memoria.
   - **Interiores**: la Fábrica y la Torre sobre clones de la Mansión (salas de
     combate); el resto, sobre interiores de ORAS que encajen.

## 6. Fases

Cada fase termina con commit, evidencia y entrada en la bitácora.

### F0 — Arranque (hecho, 2026-11-01)
Plan, bitácora, `frontier/survey.py`, pausa documentada del evento de Mew.

### F1 — Ingeniería inversa de la Mansión (hecho, 2026-11-01; `reports/frontier.md`)
- Leer el flujo del script 517: inscripción, elección de modalidad, selección de
  equipo, bucle de combates, victoria y derrota, guardado, PB. Documentarlo en
  `reports/frontier.md` con direcciones del listado.
- Localizar la implementación de las nativas `BattleInstWorkCreate`,
  `BattleHouse_CallPartySelectApp`, `SetTrainer` y `StartBattle` (tabla de nativas de
  campo; CTRMap-F5 da los hashes) y la estructura de trabajo de la instalación:
  dónde se guardan los 3 seleccionados, cómo se leen `maisontr`/`maisonpk`, cómo se
  rellena la configuración del combate.
- Partida de laboratorio con acceso a la Mansión: warp de desarrollo a la zona 517
  sobre una copia en `work/`. Si el script exige el Resort desbloqueado, primero
  medir qué flags mira. Si no basta, pedir al usuario una partida post-Delta.
- Medir el espacio disponible para código nuevo (§5.5).
- **Salida**: punto de inyección elegido (A o B) con evidencia de gdb en Azahar de un
  combate real de la Mansión.

### F2 — Datos de alquiler (hecho, 2026-11-01; `frontier/data.py`, `reports/frontier.md` §7)
- `frontier/data.py`: lee `maisonpk`/`maisontr` del volcado (con hash), define los
  niveles de alquiler por ronda y genera las tablas que use el código. Al repositorio
  solo van el generador y los índices, nunca los datos del juego.
- Tests: formato, rangos, reconstrucción idéntica del GARC sin cambios.

### F3 — Prototipo: un combate con equipo de alquiler (hecho, 2026-11-01; `reports/frontier.md` §8)
- Hook mínimo: un combate de la Mansión en el que el jugador lleva 3 alquileres fijos.
- **Salida**: combate jugado en Azahar; equipo de la partida idéntico antes y después
  (comparado con `save_fixture.py`).

### F4 — Fábrica Nivel 50 Individual jugable (en curso; ronda completa, intercambio, derrota, pausa, reanudación y PB por ronda y racha propia probados en Azahar, `reports/frontier.md` §9–§15)
- NPC, inscripción, elegir 3 de 6, 7 combates, cambio tras cada victoria, racha, PB,
  guardar y continuar entre combates, derrota y abandono.
- **Salida**: ronda completa en Azahar, más los casos: perder en el 1.º y el 7.º
  combate, cambiar y no cambiar, apagar a mitad y continuar, equipo intacto al final.

### F5 — Jefe, récords, Doble y Nivel Libre
Jefe en los combates 21 y 42 con símbolos, cartel de récords, el resto de modalidades.

### F6 — Isla del Frente: objeto, viaje, zona y Fábrica en su edificio (en curso; pase, marinero, ferry e isla 209 probados en Azahar; la sala clonada 213 se cuelga al hablar con la recepcionista, `reports/frontier.md` §16–§18)
- Objeto clave, su entrega, el viaje y la isla con el edificio de la Fábrica (§5.6),
  reutilizando lo del evento de Mew (`faraway/`). Textos ES/EN.
- Paquete Luma `dist/oras-frontier-…` encadenado con v0.5 (y Mew si se quiere).
- Partida de prueba para Checkpoint y plan de prueba en consola.

### Después: el resto del Frente
Estimación inicial, sin medir; se planifica cuando la Fábrica esté en consola:
- **Torre Batalla**: casi la Mansión tal cual, con tu equipo. Lo más fácil.
- **Domo Batalla**: torneo de 16 con cuadro. Combates de la Mansión, y el cuadro y el
  orden en script. Medio.
- **Tubo Batalla**: salas con eventos (curas, combates, estados). Script y combates
  sueltos. Medio.
- **Arena Batalla**: 3 turnos y juicio por mente, técnica y cuerpo. Hay que tocar el
  motor de combate. Difícil.
- **Palacio Batalla**: el Pokémon elige solo sus movimientos según la naturaleza.
  Motor de combate o IA. Difícil.
- **Pirámide Batalla**: mazmorra con encuentros salvajes, objetos y oscuridad. Zona
  propia y mucho script. Lo más difícil.

## 7. Riesgos y decisiones abiertas

- **Espacio para código nativo**: 2556 bytes a cero al final de `.text`
  (VA `0x579604`–`0x57A000`, `reports/frontier.md` §5). El hook de F3 (168 bytes) se
  ejecuta allí en Azahar (§8); falta probarlo en consola. Alternativa ya probada en
  consola por v0.5: el relleno de texto de `DllField.cro` (DexNav,
  `reports/held-exp-share-spec.json`).
- **Distribución del parche de `code.bin`**: Luma carga un solo `code.ips` por título y
  Repolished ya usa uno; el nuestro se genera como diferencia con el `code.bin` limpio,
  así que lo sustituye y contiene los registros de Repolished (`f3_patch.py`).
- **Formato del Pokémon en memoria** (resuelto en F3): los alquileres se crean con la
  misma función que los rivales de la Mansión (`0x1ef904`), que genera un
  `PokemonParam` válido; se vieron y usaron en combate en Azahar.
- **Partida de laboratorio post-Delta**: la del usuario está en la Ruta 102. Primero
  se intenta con warp de desarrollo.
- **Conjuntos de Esmeralda o de ORAS**: empezamos con `maisonpk` (formato nativo y
  movimientos de 6.ª generación). Importar los conjuntos de Esmeralda es una decisión
  posterior del usuario.
- **Interfaz de alquiler**: `ListMenu` es suficiente para jugar, pero no enseña
  estadísticas; una pantalla propia es trabajo aparte.
- **Tamaño del script de zona** (medido, `reports/frontier.md` §11): el de la zona 517 ya
  es el mayor; con un contenedor ZO de 21.428 bytes la zona se cuelga al cargar y con
  17.248 carga. Lo grande de la Fábrica va al script compartido 5 (`GlobalCall` 9771) y
  a su texto propio (637). Desde ese script hijo no se llaman nativas de la Mansión
  (`GetMyWinCount` lo colgó): la zona le pasa lo que necesite en works.

## 8. Trazabilidad (relevo Claude Code ↔ Codex)

- `frontier/BITACORA.md`: entradas nuevas **al final**, nunca se reescriben las
  anteriores (se corrigen con otra entrada). Formato:

  ```
  ## AAAA-MM-DD HH:MM — <agente> — <título corto>
  Estado: hecho | en curso | bloqueado
  Hecho: qué se cambió o midió (archivos, funciones, direcciones).
  Evidencia: comandos ejecutados y resultados; rutas en work/ (capturas, logs, partidas con hash).
  Commits: <hash> <asunto> (o «sin commit»).
  Decisiones: qué se eligió y por qué; qué se descartó.
  Siguiente paso: la acción concreta con la que empieza la siguiente sesión.
  ```
- `<agente>` = `Claude Code (Opus 5.5)`, `Codex (<modelo>)`, etc.
- Hechos estables y medidos: también en `reports/frontier.md` (se crea en F1) con su
  fuente. La bitácora cuenta la historia; el informe recoge el estado.
- Pie de los commits: el de Claude Code, `Co-Authored-By: Claude …` y
  `Claude-Session: …`. Codex usa el suyo (`Co-Authored-By: Codex <…>`) o, si no tiene,
  una línea `Agent: Codex`.
- Nada de estado que solo viva en la memoria de un agente: lo que haga falta para
  continuar va a la bitácora o al plan.
