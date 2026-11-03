# Arena Batalla: diseño (agente de diseño, solo lectura, 2026-11-03)

Informe de un agente de diseño de Claude Code; no tocó ficheros ni el laboratorio. Reglas contrastadas con
pret/pokeemerald `master` por la web (`src/battle_arena.c`, `src/battle_main.c`, `src/battle_util.c`,
`data/battle_scripts_1.s`, `src/frontier_util.c`), sin fijar commit. Lo no medido va como **hipótesis**.

## 1. Reglas y primera versión

**Esmeralda**:
- Individual 3 contra 3 con los Pokémon propios, Nivel 50 o Libre.
- No se puede cambiar (`BATTLE_TYPE_ARENA`); Rugido y Relevo fallan (`jumpifbattletype BATTLE_TYPE_ARENA,
  BattleScript_ButItFailed`).
- **Límite de turnos**: `arenaTurnCounter` se pone a 0xFF al entrar cualquier Pokémon (`SwitchInClearSetData`) y sube
  cada turno; al final del turno, si vale 2 y los dos tienen PS > 0, se juzga (`HandleWishPerishSongOnTurnEnd`): el
  juicio llega tras 3 turnos de cada enfrentamiento.
- **Juicio**: Mente (+1 por movimiento con potencia; −1 por Protección, Detección, Aguante, Sorpresa); Técnica (+2
  supereficaz, −1 poco eficaz, −2 no afecta o falla, +1 neutro); Cuerpo (PS × 100 / PS al empezar). En cada
  categoría el mejor suma 2, empate 1 cada uno. El perdedor cae debilitado (`arenaopponentmonlost` /
  `arenaplayermonlost`); empate, los dos (`arenabothmonlost`).
- 7 combates por ronda; Greta en 28 y 56 (`sFrontierBrainStreakAppearances[ARENA] = {28, 56, 28, 1}`).
- PB en `sBattlePointAwards`: copiar la tabla a mano (la lectura automática del agente no es fiable).

**¿Hace falta tocar el motor?** Sí. Ninguna regla retail conocida de ORAS corta a los 3 turnos ni impide cambiar.
En el repo:
- las nativas `CallSakasaBattle` (combate inverso) y `PokePartyCheckSkyBattle` (`oras_natives.tsv`) prueban que la
  configuración admite reglas, pero ninguna es de turnos;
- el «Test de Combate» de Malvalona (zona 448, texto 575) puntúa con `TrialHouse_AddBtlResultPoint` y
  `TrialHouse_GetBtlResultFixPoint`: el motor guarda estadísticas del combate. Hipótesis: del combate entero,
  leídas después. Vale la pena leerlas antes de escribir contadores propios;
- hipótesis: el límite de tiempo de los combates por conexión juzga por Pokémon restantes y PS, pero va por tiempo y
  solo en conexión; no es base fiable.

**Primera versión en dos escalones**:
- **A, sin motor (media)**: la Mansión Individual Normal con tu equipo (3 con `BattleHouse_CallPartySelectApp`, el
  orden de elección es el de combate), racha propia, PB al ganar el 7.º, guardado, pausa y derrota. Es una Torre con
  números de Arena, pero monta puerta, interior, works y racha para el escalón B.
- **B, con motor (alta)**: límite de 3 turnos por enfrentamiento; **juicio solo por Cuerpo** (perdedor debilitado,
  empate los dos); cambio prohibido desde el menú.
- Más adelante: Mente y Técnica (enganches al uso de movimientos y a la eficacia), textos del árbitro, Greta (F5).
- Hipótesis útil: Canto Mortal (movimiento 195) ya debilita al final del turno tras una cuenta; su manejador da la
  forma de debilitar y quizá un contador visible.

## 2. Qué se reutiliza y qué falta

**Se reutiliza**:
- script de 517 (`work/frontier/survey/zone517.lst`, §1): desafío `0x18f8(rango, tipo, 0x800E)` sin
  `_CallTrialDownloadApp` como `factory.reception_routine`; bucle `0x1e1c`; derrota `0x2210`; menú tras ganar
  `0x2264`/`0x3b90`; PB `0x3de4` → `0x3f4c`; patrones de `factory.battle_points`, `factory._clear`/`reception`;
- clon de la sala (`island_build.CLONES` + `patch.zone_natives`, máscara 0x343 de 517, §19);
- hooks de racha (`rental.s` `FACTORY_SLOT`, §15), a **generalizar** (hoy una sola ruta: work 16438 →
  16437/16439);
- hueco de `code.bin` (2556 bytes, §5; el hook ocupa 496, §15) y `build_patch.py` para `DllBattle.cro` y su CRR;
- `pawn.Program.transplant`, `scripts/pawn_vm.py`.

No hace falta el hook de alquileres: con el work 16410 a 0 sigue la rama retail (§9).

**Falta medir en el motor, en orden** (ninguna dirección conocida):
1. **Cómo sabe el combate que es la Arena**: desensamblar `CallSakasaBattle` (hash `FEB567AE`, tabla de nativas de
   `DllField.cro`) para ver qué campo de reglas escribe. Precedente medido: `0x003674D4` escribe `+0x8C` de la
   configuración y `DllBattle.cro+0x3263C` lo lee (`reports/ingenieria.md`). En gdb, volcar `work+0x620` en
   `0x1e30b8` y buscar un bit libre; el hook de `code.bin` lo pondría con el work de la Arena ≠ 0.
2. **Contador de turnos desde la entrada**: el manejador de Sorpresa (movimiento 252) o de Impulso (habilidad 3) en
   `DllBattle.cro`, con `frontier/cro.py`; alternativa, diferencias de RAM por turno con gdb.
3. **Final de turno y forma de debilitar**: el manejador de Canto Mortal, medido en un combate de la Mansión con un
   punto de vigilancia sobre los PS (getter 0xD → `u16[Pokémon+0x10]`, `ingenieria.md`).
4. **Prohibir el cambio**: la comprobación de «no puede escapar» de Mal de Ojo (212), Sombra Trampa (23) y Trampa
   Arena (71). Hipótesis: en la 6.ª generación los Fantasma las esquivan; el hook debe ir antes de esa excepción.
5. **Espacio**: relleno de texto de `DllBattle.cro` con `cro.py`; si no hay, la lógica en el hueco de `code.bin`
   llamada desde el CRO con `ldr ip,=dir; blx ip`.

## 3. Interior

Donante 517 clonada como 213, con el texto 619 y su propio `zone<Z>.bin` (517 retail con los cambios de la Arena).
Alternativa: 448 (Test de Combate), con el grupo de la Mansión (§19) pero otro flujo (5 combates, `TrialHouse_*`).

**Candidatas** (`repurpose.txt`, < 536): preferida **457** (Verdanturf; área 111, matrix 0, sin NPC); reservas 456,
458, 459 (también área 111), 340, 329 y 351. Descartadas: 502 (Base Secreta), 135–138 y 178–180 (hipótesis: la marea
de la Cueva Cardumen y los pisos del Pilar Celeste podrían cambiar de zona por código), 535 (vuelo), 534 (matrix 430),
2–4 (posibles escenas de historia).

**Verificar** (como §18): ningún script de los 1157 empuja su número antes de un cambio de mapa; literales en
`code.bin` y CRO; destinos calculados de 35/46/71/74; máscara 0x243; sin encuentros ni datos de vuelo (hipótesis);
en Azahar, entrar, hablar, guardar dentro, recargar y salir.

## 4. Pasos

**Agente** (`frontier/arena.py`, `tests/test_frontier_arena.py`):
1. `arena_program(retail517)`: recepción «Arena Batalla» (work de la Arena y de la ruta, `0x18f8(0, 0, 0)` con la
   pantalla de selección); limpieza en `0x2210`, en el caso 1 y en la opción 0; reanudación; PB por ronda.
2. ZO ≤ 17.248 (§11) y reconstrucción idéntica.
3. Textos ES/EN.
4. Fase B: `frontier/asm/arena.s`, generador de parches de `DllBattle.cro` con `guarded_writes` y medidas M1–M5 en
   `reports/frontier.md`.

**Integrador**:
1. `DOORS['Arena'] = (Z, 0)`; el índice de su warp en la isla depende del orden de `FACILITIES` (derivarlo).
2. `CLONES[Z] = 517`; en el plan, `zone.Z.warp.0=0,209,<índice>`, `place.Z=279`, `keeptext.Z=1` y Z en `zones=`.
3. Escribir `scripts/zone<Z>.bin` y generalizar el bucle `for zone in (ZONE_ISLAND, ZONE_HALL)` a todos los clones.
4. Works nuevos de `frontier/ids.py`; segunda ruta de racha en `rental.s`.
5. Líneas del texto 619 tras la de la Fábrica (`LINE_OPTION` 188).
6. Fase B: el bit de reglas en `StartBattle` y el `DllBattle.cro` encima del de la v0.5.

## 5. Pruebas

**Suite** (`pawn_vm`): recepción, rechazo y cancelación; racha desde 0 y reanudada; PB solo en el 7.º; limpieza en
la derrota; la Mansión y la Fábrica sin cambios; el plan con dos puertas. **Unicorn**: ruta doble de la racha; hooks
del motor con funciones simuladas (juicio con victoria, derrota y empate; contador reiniciado al entrar).

**Azahar**: puerta (20,69) → Z → vuelta a (20,70); la recepcionista habla; combate con 3 y equipo intacto
(`save_fixture`, §8); racha separada (§15); PB; pausa, reanudación y derrota; guardar en la explanada. Fase B: juicio
con victoria, derrota y empate; cambio bloqueado (también con un Fantasma); el siguiente entra tras el juicio; con el
work a 0, nada cambia en un combate salvaje, uno de entrenador y la Mansión.

## 6. Riesgos y estimación

- Motor de la 6.ª generación sin explorar: puede no haber sitio limpio para el contador o para debilitar.
- Encadenar con el `DllBattle.cro` de la v0.5 y la firma del CRR en consola.
- Ida y vuelta, Voltiocambio, Cola Dragón, Llave Giro, Relevo, Tarjeta Roja y Botón Escape siguen cambiando:
  desviación conocida en la primera versión.
- Racha desviada si se guarda a mitad (§15); interior igual que la sala de la Fábrica; texto del árbitro sin
  localizar; Greta depende de F5.

**Estimación**: escalón A media, 1–2 sesiones; escalón B alta, 3–6 sesiones (la mitad midiendo); Mente, Técnica,
textos y Greta, 2–3 más.
