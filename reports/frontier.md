# Frente de Batalla — estado medido

Hechos estables del proyecto (PLAN §8). La historia de cada sesión está en
`frontier/BITACORA.md`. §1–§5 salen de lectura estática; §6 recoge lo comprobado en
Azahar con gdb (2026-11-01). Nada se ha comprobado en consola.

Reproducción:

```bash
source scripts/env.sh
python frontier/survey.py --listings work/frontier/survey   # datos, zonas y listado del script 517
python frontier/maison_map.py                               # nativas -> código, comprobación de palabras, relleno
python frontier/disasm_code.py baseline/oras/repolished/exefs/code.bin 1e3d2c 120
python frontier/disasm.py baseline/oras/repolished/romfs/DllField.cro 9500c
```

`maison_map.py` exige los SHA-256 de la base Repolished 1.7.6
(`DllField.cro` `23248ab0…`, `code.bin` `3999d658…`) y comprueba las palabras de
instrucción citadas abajo; con otro volcado falla en lugar de dar direcciones falsas.

## 1. Flujo del script de la Mansión (zona 517)

Direcciones del listado `work/frontier/survey/zone517.lst`.

| Dirección | Qué hace |
|---|---|
| `0x110c` | Despachador (`CASETBL` en `0x1220`, casos −1 y 1–11). Caso 1 → `0x1458` (limpieza: `ClearWinCount`, `BattleHouse_End`), caso 2 → `0x14f4` (recepción). |
| `0x14f4` | Recepción: `BattleInstWorkCreate` (`0x1508`), menú de 4 opciones (mensajes 53, 54, 74, 55). |
| `0x16fc` | Opción 0: `_CallTrialDownloadApp` (9 argumentos: flags 385–389 y los works `0x800C`, `0x800D`, `0x800E`). Es la pantalla de elegir modalidad: `0x800C` ≠ 0 si se acepta. |
| `0x1768` | `GetRank` y llamada a `0x18f8(rango, work 0x800D, work 0x800E)`. |
| `0x18f8` | Desafío: racha (`GetMyWinCount`), confirmación (`0x36e4`; mensaje según tipo 0–4 y rango), compañero en Multi (`0x338c`), **selección de equipo** `0x457c` → `BattleHouse_CallPartySelectApp(arg, 0x800C)` (`0x458c`), guardado (`GlobalCall 2003`), `RecordAdd 71`, flags 385–389 por tipo, y bucle `0x1e1c`. |
| `0x1e1c` | Bucle de combate: `0x2b98` (elige rival con `SetTrainer` vía `0x132c` y lo coloca), `0x4338` (presentación), **`StartBattle(0, 1)`** en `0x1ee4`, `IsWin` (`0x1f40`). |
| `0x1f60` | Victoria: `AddWinCount`, `IsBoss` (`0x205c`; jefe → `BattleHouse_SetRibbon`, `PokeDiarySet`, `0x264c`), si no, PB por tramo de racha en `0x3de4` (llama a `0x30`: `PlayerGetBP`+`PlayerSetBP` en `0x4c`). |
| `0x2210` | Derrota: `0x533c`, récord `0x3fdc` (`SaveBattleRecord`), `ClearWinCount`. |
| `0x2290` | Tras la victoria, menú de continuar / guardar / retirarse (`0x3b90`); vuelve a `0x1e28`. |

Tipos de combate (`0x800D`, byte de trabajo `+0x839`): 0 Individual, 1 Doble,
2 Triple, 3 Rotación, 4 Multi. El número de Pokémon del rival por tipo sale de la
tabla de saltos en `code.bin` `0x1e34d0`: 3, 4, 6, 4 y 2.

## 2. Nativas → código

La tabla de nativas de campo está en `DllField.cro` (rodata): pares de punteros
relocados *nombre → función*. El bloque de la Mansión va de `0xf8b44` a `0xf8cd4`
(50 entradas). Cada nativa lee el trabajo de la instalación en
`[[ctx+0xC]+0x64]` y llama a `code.bin` por los *thunks* de importación `|static|`.

| Nativa | Función en `DllField.cro` | Llama en `code.bin` |
|---|---|---|
| `BattleInstWorkCreate` | `+0x9569c` | `0x1e5cd4`: reserva **0xB90 bytes** y guarda el puntero en `[ctx+0xC]+0x64` |
| `SetTrainer(tipo)` | `+0x94edc` | `0x1e3aac` (elige entrenador por racha), `0x1e54a0` (carga su ficha de `maisontr`), `0x1e4a14` (guarda el id en `+0xB88`) |
| `StartBattle(a, b)` | `+0x9500c` | `0x1e30b8(work, a≠0, b≠0)` |
| `BattleHouse_CallPartySelectApp(modo, work)` | `+0x95c40` | crea el proceso de la pantalla de selección (0x2C bytes) |
| `GetRank` | `+0x95e20` | lee `work+0x838` (0 Normal, 1 Súper) |
| `IsWin` / `IsBoss` / `AddWinCount` | `+0x95df0` / `+0x95e08` / `+0x94f94` | `0x1e5664` / `0x1e5674` / `0x1e2fb0` |

Los archivos de la Mansión se abren por número: `0xb6`/`0xb7` = `a/1/8/2`/`a/1/8/3`
(Normal), `0xb8`/`0xb9` = `a/1/8/4`/`a/1/8/5` (Súper); la elección depende de `+0x838`
(`0x1e3568`, `0x1e54b8`).

## 3. Estructura de trabajo (0xB90 bytes; parcial)

| Offset | Tipo | Uso (fuente) |
|---|---|---|
| `+0x001` | u8 | jefe en el siguiente combate (`0x1e559c`) |
| `+0x004 + 4·n` | u32 | id del entrenador rival *n* (`0x1e54b4`) |
| `+0x00C + 4·n` | ptr | ficha del entrenador *n* leída de `maisontr` (`0x1e551c`) |
| `+0x02C` | u8 | la selección viene de la Caja de Combate (`0x1e3d3c`) |
| `+0x030 + 4·i` | s32[6] | **índices del equipo elegidos** (`0x1e3d60`) |
| `+0x048` | s32 | número de elegidos (`0x1e3d4c`) |
| `+0x05C + 4·i` | ptr | conjuntos del compañero en Multi (`0x1e3514`) |
| `+0x620` | — | parámetros del combate que se pasan al sistema de batalla (`0x1e3100`) |
| `+0x838` | u8 | rango (Normal/Súper) |
| `+0x839` | u8 | tipo de combate 0–4 |
| `+0xB70` | ptr | heap |
| `+0xB78` | ptr | contexto del juego (`[+0x1C]+0x14` = equipo del jugador) |
| `+0xB84` | ptr | equipo de la Caja de Combate |
| `+0xB88 + 4·n` | u32 | id del entrenador *n* |

## 4. Punto de inyección: opción A (sustituir el equipo del combate)

`StartBattle` → `0x1e30b8` crea un `PokeParty` **nuevo** (`0x13f48c` 0x1C bytes +
constructor `0x112a04`: 6 `PokemonParam`) y llama a `0x1e3d2c(work, a, work+0x2C, party)`:

1. Si `+0x2C` ≠ 0 toma la Caja de Combate; si no, el equipo de la partida
   (`[[work+0xB78]+0x1C]+0x14`, `0x1e3d94`).
2. Para cada índice elegido, `GetMemberPointer` (`0x3b6150`) y `AddMember`
   (`0x3b645c`), que **copia** el Pokémon (`0x3b2444`) al equipo nuevo.
3. Ajusta a nivel 50 los que lo superan (o todos si `a` ≠ 0) y recalcula.

Conclusión: el equipo del combate es una copia; el equipo de la partida no se
escribe en este camino. Para la Fábrica basta con que el bucle de `0x1e3d2c`
añada Pokémon de alquiler en vez de copiar los del jugador. Comprobado en
Azahar (§6): el equipo de la partida queda idéntico byte a byte tras el combate.

Para construir los alquileres existe ya una fábrica de Pokémon a partir de un
conjunto de 16 bytes: `0x1ef904(conjunto*, nivel, IV, heap, …)` devuelve un
`PokemonParam*`. La Mansión la usa para el compañero de Multi
(`0x1e351c`: nivel 50, IV 31) y el rival se construye con `0x1e4a94` desde
`0x1e3480`. La carga de un conjunto por índice está en `0x1efc18` (con archivo
`0xb8`).

## 5. Espacio para código nuevo

- `code.bin`: entre el final de `.text` (`0x479604`, exheader) y el final de su
  última página (`0x47A000`) hay **2556 bytes a cero**, VA `0x579604`–`0x57A000`,
  igual en la base limpia y en Repolished (`maison_map.py`). La página está dentro
  del segmento de texto (0x47A páginas), así que debería cargarse con permiso de
  ejecución. En Azahar la zona está mapeada y a cero (§6); la última función de
  `.text` acaba en `0x579600` (`bx lr`). **No se ha ejecutado código allí** y Azahar
  no demuestra los permisos de la consola.
- Ninguna otra vía (CRO, ampliar el exheader) se ha medido todavía.

## 6. Comprobación en Azahar (2026-11-01)

Partida `work/frontier/lab/main` (copia de `work/partida-convertida/main`, SHA-256
`a74ddefd…`, 6 Pokémon de nivel 6–12), overlay de desarrollo
`faraway/dev_overlay.sh 517 0` (warp de la Ruta 102 a la zona 517) y gdb con
`faraway/gdbctl.sh` (hay que poner `use_gdbstub=true` en
`work/azahar-lab/config/azahar-emu/qt-config.ini` y conectar cuando el puerto
24689 ya escucha; se dejó otra vez en `false`). Log: `work/frontier/lab/gdb-f1.log`.

- La partida no necesita el Resort desbloqueado: con el warp se entra en la
  Mansión y la recepcionista (NPC 1, tile 23,24) inscribe normalmente.
- Al hablar salta `0x1e5cd4` (`BattleInstWorkCreate`); trabajo en `0x08822544`
  (`[ctx+0x64]`). El retorno a `0x7886ac` da la base de `DllField.cro` en esta
  sesión: `0x006F3000` (= `0x7886ac − 0x956ac`; puede variar con el orden de carga).
- La pantalla de `_CallTrialDownloadApp` es la de tipo de combate (Individual,
  Doble, Triple, Rotatorio, Múltiple). Con Individual Normal: `+0x838 = 0`,
  `+0x839 = 0`.
- Antes del primer combate el script pide guardar (`GlobalCall 2003`); sin
  guardar, `0x1a70` cancela.
- Elegidos Torchic, Poochyena y Silcoon (huecos 0, 2, 4): `work+0x2C = 0`,
  `work+0x30 = [0, 2, 4, 0, 0, 0]`, `work+0x48 = 3`.
- `0x1e30b8` con `r1 = 0`, `r2 = 1` (`StartBattle(0, 1)`), `lr = 0x788048`
  (`DllField.cro+0x95048`). `0x1e3d2c` recibe el `PokeParty` nuevo en `0x08822440`;
  al salir tiene 3 miembros (objetos en `0x0880a814`, `0x0880a9f8`, `0x0880abdc`,
  0x1E4 bytes cada uno), distintos de los del equipo de la partida
  (`0x08cf71f0`, 6 miembros desde `0x08cf723c`). Comparados con los huecos 0, 2
  y 4, solo difieren los punteros internos de cada objeto (cabecera y
  `+0x130`–`+0x1c4`) y una palabra que vale 8 en la copia y 4 en el original
  (`+0x138`, `+0x178`, `+0x1c4`); el resto es igual.
- En combate se ven solo esos 3 Pokémon. Derrota: `work+0x73C = 0`.
- El equipo de la partida en memoria (`0x08cf71f0`–`0x08cf7d94`) es idéntico antes
  del combate, al leer el resultado y de vuelta en el mostrador: SHA-256
  `f7436e68…` en `party_before.bin`, `party_after.bin` y `party_end.bin`.
- `x/4wx 0x579ff0` lee ceros: el relleno de `.text` está mapeado.

## 7. Datos de alquiler (F2)

`python frontier/data.py --out work/frontier/data` comprueba los SHA-256 de
`a/1/8/2`–`a/1/8/5` (iguales en ORAS 1.0 y Repolished), que cada GARC se reconstruye
idéntico sin cambios, y la estructura de niveles de abajo; escribe la tabla binaria
`rental_levels.bin` (148 bytes) y un listado con especie y objeto de cada conjunto
(`rentals.txt`, en `work/` por contener datos del juego). Tests:
`tests/test_frontier_data.py`.

Estructura medida de los conjuntos (999 por archivo, 16 bytes):

| Archivo | Rangos | Qué son |
|---|---|---|
| `maisonpkN` | 0–65 y 66–131 | Dos copias de los mismos 66 Pokémon débiles (Rattata, Pidgey…), mismo orden |
| `maisonpkN` | 132–169 y 170–207 | Dos copias de 38 Pokémon medios (Gurdurr, Sliggoo…) |
| `maisonpkN` | 208–216; 217–998 vacíos | Equipos especiales (Claydol, Metagross…) |
| `maisonpkS` | nivel *k* = 0–3: `52k`…`52k+20` y `208+175k`…`382+175k` | Cuatro copias de las mismas 196 especies (21 de Kalos + 175), mismo orden, conjuntos distintos |
| `maisonpkS` | 908–987 | Cuatro copias de 20 legendarios (Articuno…Regigigas) |
| `maisonpkS` | 988–996; vacíos 21–51, 73–103, 125–155, 177–207, 997–998 | Especiales |

Los entrenadores de cada tramo de racha del elector de la Mansión (`0x1e3aac`:
Normal racha 0–4 → entrenadores 0–49, 5–9 → 30–69, 10–14 → 50–89, 15–18 → 70–109;
el tramo usa `0x1e4860(work, …, primero, cuántos)`) solo eligen conjuntos de su nivel:
entrenadores 0–49 → nivel 0, 50–69 → 1, 70–89 → 2, 90–109 → 3, en los dos archivos
(`check_tiers`). En Súper los tramos son de 10 victorias (0–9, 10–19, …) y desde 50
entrenadores 90–189, que mezclan niveles y legendarios.

Niveles de alquiler de la Fábrica Nivel 50 (`RENTAL_LEVELS`; correspondencia con
`sInitialRentalMonRanges` de Esmeralda):

| Ronda | Conjuntos | Esmeralda |
|---|---|---|
| 1 | N 66–131 (66) | rango débil 110–199 |
| 2, 3 | N 132–169, N 170–207 (38 cada uno) | rango medio, copias 1 y 2 |
| 4–7 | S nivel 0, 1, 2, 3 (196 cada uno) | rango fuerte, copias 1–4 |
| 8+ | S niveles 0–3 (784, 196 especies) | 372–849 |

Formato de `rental_levels.bin` (para el código nativo): u16 número de niveles; u16 por
nivel con el desplazamiento de su lista; cada lista: u16 número de rangos y, por rango,
u16 archivo (`0xb6` Normal, `0xb8` Súper), u16 primer conjunto, u16 cuántos.

## 8. Prototipo F3: combate de la Mansión con 3 alquileres fijos (Azahar, 2026-11-01)

Funciones usadas (lectura estática, `frontier/disasm_code.py`):

| Función | Firma medida | Fuente |
|---|---|---|
| `0x1efc18` | `(heap, archivo, índice, salida[16])`: abre el archivo (`0x11c94c`), comprueba (`0x11c930`), lee (`0x128cbc`) y cierra (`0x36edd4`) | mismo patrón en el constructor del rival `0x1e4b38`–`0x1e4b94` |
| `0x1ef904` | `(conjunto*, nivel, IV, heap, [sp] habilidad, [sp+4] u16 en spec+0x1e) → PokemonParam*`. Habilidad < 0: al azar entre 3; ≥ 3: 0. Pone especie, forma, nivel, los 6 IV, objeto (`0x3b54c8`), 4 movimientos (`0x3b54d8`), amistad 0 si sabe Frustración (218) o 255 (`0x3b47ec`), naturaleza (`0x12c190`) y EV = 510/nº de bits, máx. 255 (`0x3b4b64`) | el rival la llama con `(set, 50, IV, heap, -1, 0xFF)` en `0x1e4e70`–`0x1e4e88`; el IV del rival sube por tramo de entrenador: 3, 7, 11, 15, 19 (Normal), …, 31 |
| `0x3b645c` | `AddMember(party, PokemonParam*)`: copia | `0x1e35c0` |
| vtable `+8` | libera el `PokemonParam` temporal | `0x1e35c4`–`0x1e35d8` |

Parche (versión F3, commit `2923e19`: `python frontier/f3_patch.py --out work/frontier/f3`; hoy `frontier/patch.py`, §9; comprueba SHA-256 del
`code.bin` limpio, del de Repolished y de su `code.ips`, las 5 palabras del sitio y
los prólogos de las 3 funciones):

- `0x579604`–`0x5796ac` (168 bytes del relleno): `frontier/asm/rental_f3.s` (hoy `rental.s`). Para
  `i < work+0x48` (máx. 6): carga `maisonpkS[208+i]`, crea el Pokémon a nivel 50 con
  IV 31, lo añade al equipo del combate y libera el temporal.
- `0x1e3d8c`: la rama «equipo de la partida» de `0x1e3d2c` pasa a ser
  `mov r0,r6; mov r1,sb; bl 0x579604; ldr r0,[r4,#0x1c]; b 0x1e3ddc`. La rama de la
  Caja de Combate no cambia. Es un parche de laboratorio: afecta a todos los combates
  de la Mansión.
- `code.ips` (574 bytes) = diferencia con el `code.bin` limpio: incluye los registros de
  Repolished y sustituye a su `code.ips`. `CODE_IPS=work/frontier/f3/code.ips
  faraway/lab.sh …` lo instala en el laboratorio.
- `tests/test_frontier_f3.py` ejecuta el sitio y el hook en Unicorn, con las 3
  funciones simuladas: argumentos, orden de llamadas, liberación, registros
  preservados y retorno a `0x1e3ddc` con 3, 4, 6 y 0 elegidos.

Prueba en Azahar (partida `work/frontier/lab/main-maison`, SHA-256 `4f5a79c7…`, la
guardada en la Mansión al final de F1; log `work/frontier/lab/gdb-f3.log`):

- En memoria, `0x579604` contiene el hook y `0x1e3d8c` la desviación.
- Individual Normal, elegidos Torchic, Poochyena y Silcoon; la Mansión pide guardar.
- Punto de ruptura en `0x579604` alcanzado: `r0 = 0x08822544` (trabajo),
  `r1 = 0x08822440` (equipo nuevo), `work+0x30 = [0,2,4]`, `work+0x48 = 3`.
  En `0x1e3ddc`: `r0 = 3` y el `PokeParty` tiene 3 miembros (`+0x18 = 3`).
- En combate salen **Venusaur, Charizard y Blastoise, Nv. 50, con objeto**
  (`f3_battle_party.png`); Venusaur 187/187 PS (= IV 31 y 255 EV en PS).
  Retirada (cuenta como derrota) y vuelta al mostrador sin cuelgues.
- Equipo de la partida en memoria (`0x08cf71f0`–`0x08cf7d94`) antes del hook y de
  vuelta en el mostrador: SHA-256 `f7436e68…` los dos (el mismo que en F1).
- La Mansión guarda tras la derrota (`f3_after.sav`, SHA-256 `08eaa586…`). Bloque de
  equipo de la partida (`save_fixture.py`, `0x14200`, 0x61C bytes) idéntico al de
  `main-maison`: `d8e76518…` en los dos; mismos 6 Pokémon y niveles.

Sin probar: victoria con alquileres (y lo que la Mansión haga después), apagar a
mitad, Doble/Triple/Rotación/Multi y la Caja de Combate con el parche, y la consola.

## 9. F4: activación por works guardados (Azahar, 2026-11-01)

Works libres (`python frontier/ids.py`): de los 376 works guardados (16384–16759), 253
aparecen en algún script retail (1157: zona, entidades y compartidos), en los datos de
entidades o como literal en `code.bin`, `static.crs` o un CRO (palabra alineada o
inmediato ARM); 121 no, y todos valen 0 en la partida del usuario y en la de laboratorio.
16665 y 16667 son del evento de Mew. Los works calculados en ejecución (base + índice) no
se ven con este método. Elegidos para la Fábrica:

| Work | Uso |
|---|---|
| 16410 | Estado: IV de los alquileres (1–31); 0 = Fábrica inactiva, la Mansión usa tu equipo |
| 16411–16413 | Alquileres: bit 15 = `maisonpkS` (`0xb8`), si no `maisonpkN` (`0xb6`); bits 0–9 = conjunto |

Lectura desde código: el work guardado *N* está en
`[[[work+0xB78]+0x1C]] + 0x13144 + 2·(N − 0x4000)` (`WorkGet` → `0x3fe118`: base
`[[[ctx+8]+0x1C]] + 0x13140`; `0x11fa90`: `+ 2·N − 0x7ffc`). Comprobado en Azahar: en
`0x579604` esa dirección (`0x08c7db20`) contiene 31, 66, 33268, 33675, lo escrito en la
partida con `faraway/save_event.py`.

Hook (`frontier/asm/rental.s`, 240 bytes en `0x579604`–`0x5796f4`; generador
`python frontier/patch.py --out work/frontier/patch`, `code.ips` 655 bytes; tests
`tests/test_frontier_patch.py`, `tests/test_frontier_ids.py`):

- Sitio `0x1e3d8c`: `mov r0,r6; mov r1,sb; bl 0x579604; mov r8,r0; nop`.
- Work 16410 = 0: hace lo que hacía el original (`r8` = equipo de la partida,
  `0x3b5d34`) y vuelve a `0x1e3d98`; sigue el bucle original en `0x1e3da0`.
- Work 16410 ≠ 0: un alquiler por elegido (máx. 3) con ese IV, guarda el número en
  `work+0x48` y salta a la cola común `0x1e3ddc` con `r0` = número.

Prueba en Azahar (logs `work/frontier/lab/gdb-f4-active.log`, `gdb-f4-inactive.log`):

- Fábrica activa (`f4_active.sav`, SHA-256 `62e5b64c…` = `f3_after.sav` + works 16410=31,
  16411=66, 16412=0x8000|500, 16413=0x8000|907): sale de `0x579604` directamente a
  `0x1e3ddc` con `r0 = 3`; en combate **Rattata (N 66), Mandibuzz (S 500) y Slaking
  (S 907), Nv. 50** (`f4_active_party.png`); los movimientos de Slaking son los del
  conjunto 907 (Retribución, Tajo Umbrío, Lanza Mugre, Golpe Aéreo; `f4_slaking_moves.png`).
- **Primera victoria con alquileres**: la Mansión da 1 PB (`f4_win_bp.png`) y sigue al
  combate 2, donde los alquileres se reconstruyen con los PS completos
  (`f4_battle2_party.png`). Slaking salió macho en el combate 1 y hembra en el 2: PID,
  sexo y habilidad (`-1` = al azar) se sortean en cada combate.
- Retirada en el combate 2; en el mostrador el equipo de la partida en memoria sigue
  siendo `f7436e68…`, y la partida guardada tras la derrota (`f4_active_after.sav`,
  `fac8791d…`) tiene el bloque de equipo `d8e76518…` (igual) y los works intactos.
- Fábrica inactiva (`f3_after.sav`, works a 0) con el mismo `code.ips`: el hook pasa por la
  rama original (`0x1e3da0` con `r8 = 0x08cf71f0`) y sale tu Torchic Nv. 12
  (`f4_inactive_torchic.png`).

Sin probar: consola; apagar a mitad; dobles y demás modalidades con la Fábrica activa
(el hook limita a 3 alquileres); la Caja de Combate (su rama no pasa por el hook, así que
con la Fábrica activa usaría la Caja).

Cambio posterior (sin probar en Azahar; Unicorn sí): con la Fábrica activa el hook pone
siempre 3 alquileres (no depende de `BattleHouse_CallPartySelectApp`, que el flujo de la
Fábrica no usará) y toma la habilidad de los bits 10–11 de cada work (0–2; 3 = al azar),
para que no cambie entre combates. El sexo (`spec+0x1e`, escrito tal cual en los bits de
género por `0x14f7c8`) sigue en 0xFF como en los rivales; se sortea en cada combate.
Hook: 244 bytes (`0x579604`–`0x5796f8`), `code.ips` 662 bytes.

## 10. F4: la Mansión sin pantalla de selección con la Fábrica activa (Azahar, 2026-11-01)

`python frontier/overlay.py --out work/frontier/build [--zones …/a/0/1/3]` (antes `frontier/build.py`, renombrado) comprueba el
SHA-256 del contenedor de la zona 517 (`bf788f5f…`, igual en ORAS 1.0, Repolished, v0.5 y el
overlay de Mew), sustituye solo su script e inserta al principio de `0x457c` (rutina que
abre `BattleHouse_CallPartySelectApp` y devuelve el work `0x800C`):
`WorkGet(16410)`; si ≠ 0, `WorkSet(0x800C, 1)` y devuelve 1 sin abrir la pantalla.
Escribe `romfs/a/0/1/3` y `code.ips` (hook de §9 con habilidad fija y 3 alquileres).
Tests: `tests/test_frontier_overlay.py`.

Prueba (`f4_active.sav`, overlay `work/frontier/build` sobre el `a/0/1/3` del overlay de
desarrollo; log `work/frontier/lab/gdb-f4-noselect.log`):

- Tras confirmar Individual se pasa directamente a «¿Quieres guardar la partida?»: no
  aparece la pantalla de selección.
- En `0x579604`: `work+0x48 = 0` (nadie eligió) y works `0x1f, 0x42, 0x81f4, 0x838b`.
  En combate Rattata, Mandibuzz y Slaking Nv. 50 (`f4_noselect_party.png`); Slaking con
  Ausente (habilidad 0, la pedida) y Vidasfera (`f4_slaking_ability.png`). Retirada y
  vuelta al mostrador.
- **Abierto**: en la partida guardada tras la derrota (`f4b_after.sav`, `76289ff9…`) el
  bloque de equipo difiere del de `f4_active.sav` en 8 bytes: solo campos de recuerdos
  del PK6 (Beldum, hueco 1: `0xA4` 1→3, `0xA5` 3→23, `0xA6` 9→11, `0xA8` 9→0; Shroomish,
  hueco 5: `0xCC` 1→2). Especie, nivel, PS, movimientos, objetos y EV, iguales. En memoria
  el equipo también cambió (`38c28b7c…`). El hook no lee ni escribe el equipo de la
  partida con la Fábrica activa. Sin aislar si es la mecánica de recuerdos del juego
  (que en F3 no se disparó) o algo del flujo sin pantalla de selección: hay que repetir
  el mismo recorrido sin parche y con la pantalla.

Control sin parche (2026-11-01): `code.ips` de Repolished y script retail, misma partida
`f4_active.sav`, recepcionista → Individual → selección (Torchic, Poochyena, Silcoon) →
guardar → combate perdido. La partida guardada tras la derrota (`control_after.sav`,
`bf647740…`) también cambia un campo de recuerdos: Poochyena (hueco 2) `0xCC` 1→2, nada
más. **Conclusión**: el juego retail actualiza los recuerdos del PK6 de los Pokémon del
equipo en este flujo; el cambio de §10 no lo causa la Fábrica. Con la Fábrica los afectados
pueden ser Pokémon que no combatieron (el juego elige del equipo de la partida). Especie,
nivel, PS, movimientos, objetos y EV no cambian en ningún caso medido.
