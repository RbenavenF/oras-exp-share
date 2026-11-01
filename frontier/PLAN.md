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

Reglas de la Fábrica que vamos a reproducir (Esmeralda; **contrastar con
pret/pokeemerald `src/battle_factory.c` antes de fijar números**):

- Modalidades Nivel 50 y Nivel Libre; Individual y Doble. Empezamos por **Nivel 50
  Individual**.
- El jugador no usa su equipo: elige **3 Pokémon de alquiler de entre 6** al azar.
- Una ronda son **7 combates**. Tras cada victoria se puede **cambiar uno** de los
  alquilados por uno del equipo del rival derrotado.
- Al acabar la ronda, los alquileres se devuelven y la siguiente empieza con 6 nuevos.
  El conjunto de alquiler sube de nivel de dificultad con las rondas.
- Racha guardada; Puntos de Batalla (PB) como premio; jefe de la instalación
  (Esmeralda: Noland, combates 21 y 42) con símbolos de plata y oro.

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
6. **Ubicación**: primera versión, un NPC nuevo en la zona 517 que ofrece «Fábrica
   Batalla» y usa las salas de la Mansión. Al final, edificio propio en el Resort
   (zona clonada, puerta en el exterior), aprovechando el cartel «proyecto Frente de
   Batalla» del texto 625.

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

### F2 — Datos de alquiler
- `frontier/data.py`: lee `maisonpk`/`maisontr` del volcado (con hash), define los
  niveles de alquiler por ronda y genera las tablas que use el código. Al repositorio
  solo van el generador y los índices, nunca los datos del juego.
- Tests: formato, rangos, reconstrucción idéntica del GARC sin cambios.

### F3 — Prototipo: un combate con equipo de alquiler
- Hook mínimo: un combate de la Mansión en el que el jugador lleva 3 alquileres fijos.
- **Salida**: combate jugado en Azahar; equipo de la partida idéntico antes y después
  (comparado con `save_fixture.py`).

### F4 — Fábrica Nivel 50 Individual jugable
- NPC, inscripción, elegir 3 de 6, 7 combates, cambio tras cada victoria, racha, PB,
  guardar y continuar entre combates, derrota y abandono.
- **Salida**: ronda completa en Azahar, más los casos: perder en el 1.º y el 7.º
  combate, cambiar y no cambiar, apagar a mitad y continuar, equipo intacto al final.

### F5 — Jefe, récords, Doble y Nivel Libre
Jefe en los combates 21 y 42 con símbolos, cartel de récords, el resto de modalidades.

### F6 — Edificio propio, textos y paquete
- Zona clonada en el Resort y textos ES/EN.
- Paquete Luma `dist/oras-frontier-…` encadenado con v0.5 (y Mew si se quiere).
- Partida de prueba para Checkpoint y plan de prueba en consola.

### Después
Resto del Frente: Torre (≈ la Mansión), Palacio, Arena, Domo, Pirámide y Tubo.
Se planifican cuando la Fábrica esté en consola.

## 7. Riesgos y decisiones abiertas

- **Espacio para código nativo**: 2556 bytes a cero al final de `.text`
  (VA `0x579604`–`0x57A000`, `reports/frontier.md` §5), mapeados en Azahar. Falta
  ejecutar código allí y probarlo en consola; si no basta, medir otras vías.
- **Formato del Pokémon en memoria**: si el equipo del combate guarda los PK6 cifrados,
  hay que generar Pokémon válidos (checksum, PID), igual que hace la Mansión con los
  rivales; se intentará reutilizar su función.
- **Partida de laboratorio post-Delta**: la del usuario está en la Ruta 102. Primero
  se intenta con warp de desarrollo.
- **Conjuntos de Esmeralda o de ORAS**: empezamos con `maisonpk` (formato nativo y
  movimientos de 6.ª generación). Importar los conjuntos de Esmeralda es una decisión
  posterior del usuario.
- **Interfaz de alquiler**: `ListMenu` es suficiente para jugar, pero no enseña
  estadísticas; una pantalla propia es trabajo aparte.

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
