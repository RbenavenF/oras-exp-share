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

## 11. F4: inscripción en la Fábrica desde la recepcionista (Azahar, 2026-11-02)

`python frontier/overlay.py --out work/frontier/build --romfs work/faraway/dev/overlay/romfs`
(`frontier/factory.py`). Escribe `a/0/1/3` (zona 517), `a/0/2/9` (script compartido 5),
los ocho textos de historia y `code.ips`.

**Límite del script de zona** (medido, bisección en Azahar con datos de relleno, scripts
de prueba fuera del repositorio):
- El script de la zona 517 ya es el mayor de todas las zonas retail: 29.320 bytes en
  memoria y 14.428 en archivo. El contenedor ZO mayor es el de la zona 83, con 17.416.
- Un primer intento con todo el sorteo dentro del script de zona (21.696 bytes, ZO
  22.488) dejaba el juego en negro a 0 FPS al cargar la partida en la Mansión.
- Con el mismo script y 2000 celdas de datos a cero (37.376 bytes en memoria, archivo
  16.456, ZO 17.248), la zona carga. Con 1250 celdas aleatorias (34.376 en memoria,
  archivo 20.636, ZO 21.428), se cuelga.
- Conclusión: el límite es el tamaño del archivo o contenedor, no la memoria, y está
  entre 17.248 y 21.428 bytes de ZO. El build final deja la zona en 14.680 bytes (ZO
  15.472); `tests/test_frontier_overlay.py` exige un ZO ≤ 17.248.

**Scripts compartidos y `GlobalCall`** (lectura estática de `code.bin`):
- La tabla de rangos está en `0x587678` (VA): 86 filas de 8 `u16`, con este formato:
  primer id, último id, script de `a/0/2/9`, indicador, texto de historia, 0, 0, 0.
- Ejemplos: 2000–2099 → script 15, que incluye el guardado `GlobalCall 2003`;
  10290–10309 → script 41, la barca de Arenque (`reports/faraway.md`).
- Los scripts compartidos retail llegan a 29.082 bytes (el 47).
- El script 5 es un esqueleto retail de 167 bytes: un caso, el 9770, que llama a una
  rutina vacía. Ningún script retail llama a 9770 (búsqueda en los 1157 listados). Su
  fila es `0x587AA8`: (9770, 9779, 5, 1, 618).
- La Fábrica añade el caso 9771 al script 5 y cambia el texto de esa fila de 618 a 637.
  637 es una entrada nueva de los textos de historia, que tenían 637 entradas (0–636).
  Son 2 bytes de `code.bin`, comprobados en `frontier/patch.py`.
- El hijo muestra mensajes y menús con su propio texto. Los ayudantes de mensaje y menú
  se copian del script 517 (`Program.transplant`).

**Nativas de la Mansión en el hijo** (medido): con la siembra y `GetMyWinCount(0, 0)`
dentro del script compartido, el juego se queda a 0 FPS al elegir la opción. La CPU da
vueltas en código Thumb hacia `0x2fee00`–`0x2ffa00` y la pila del script hijo está
vacía. La variante que solo siembra y llama al generador no se cuelga, ni la que
devuelve sin hacer nada.

Al mover `GetMyWinCount` (y su comprobación de signo) al script de zona y pasar la racha
en el work 16429, el sorteo funciona. No está aislado si el problema es la nativa en sí
o algo de su contexto; la regla práctica es no llamar nativas de la Mansión desde el
hijo.

**Prueba de punta a punta** (`main-maison`, `faraway/lab.sh` con
`CODE_IPS=work/frontier/build/code.ips` y el overlay `work/frontier/build`; para llegar
al menú se usa `frontier/lab_factory.py`):
- El menú de la recepcionista tiene 5 opciones; «Fábrica Batalla» va antes de «No quiero
  nada» (`work/frontier/lab/f4c_menu.png`).
- Al elegirla salen «Elige tu primer Pokémon de alquiler.» y un menú de 6 alquileres de
  la ronda 1 (`maisonpkN` 66–131), con especies y objetos distintos: Wingull (Baya
  Gualot), Kricketune (Baya Zidra), Drowzee (Cuchara Torcida), Skiploom (Baya Alcho),
  Spinarak (Baya Kouba) y Boldore (Globo Helio) (`f4c_draft1.png`,
  `f4c_draft1_bottom.png`).
- El segundo y el tercer menú ofrecen solo los no elegidos (`f4c_draft2.png`,
  `f4c_draft3.png`).
- Después: «¿Quieres participar en Combates Individuales?», «Sí», guardado sin pantalla
  de selección y combate.
- En combate: Boldore, Drowzee y Spinarak Nv. 50, en el orden elegido, contra un Omanyte
  Nv. 50 (`f4c_battle_party.png`).
- La partida guardada antes del combate (`f4c_saved.sav`, `d534beaa…`) tiene:
  - 16410 = 3 (IV de la ronda 1);
  - 16411–16413 = N128 Boldore, N122 Drowzee y N96 Spinarak, los tres con habilidad 1;
  - 16414 (estado del generador) = 29669 y 16429 = 0.
- Retirada del combate y vuelta a la recepción.
- Una segunda inscripción sortea otros 6 (Frillish, Snorunt, Pansage, Drowzee…) y B en
  el primer menú vuelve a «¿En qué te puedo ayudar?» (`f4c_cancel_menu.png`,
  `f4c_cancel_back.png`).

**Sin probar en Azahar**:
- que una derrota sola deje 16410 = 0: tras perder pulsé A de más y volví a entrar por
  «Combatir», que también lo pone a 0; la lógica sí está probada en
  `tests/test_frontier_factory.py`;
- la pausa y la reanudación;
- el texto 637 en idiomas distintos del español, y nada en consola.

Pruebas en el intérprete (`scripts/pawn_vm.py`, `tests/test_frontier_factory.py`):
- el nivel por racha (0, 6, 7, 20, 21, 48, 49 y 400);
- especies y objetos distintos, menús de 6, 5 y 4, y valores y habilidades de los works;
- cancelar en cada menú, rechazar la confirmación, perder y pausar;
- la racha que pasa la zona.

## 12. F4: intercambio tras la victoria, sorteo por ronda y limpieza en la derrota (Azahar, 2026-11-02)

**Conjuntos del rival** (lectura de `code.bin`):
- El constructor del equipo rival es `0x1e4a94(work, …, ficha del entrenador, archivo,
  [sp] nº de Pokémon, …, [sp+0x10] salida PokemonParam*[])`. Lo llaman `0x1e35a8` y
  `0x1e3610`, al montar cada combate.
- Para cada hueco `r7` sortea un índice de la lista de la ficha (`ldrh r4, [r0, #4]` en
  `0x1e4b34`). Si la especie o el objeto se repiten, vuelve a `0x1e4b24` y sortea otro
  para el mismo `r7`.
- Guarda especies y objetos (`work+0x14`, `work+0x20`), pero no los índices.
- `frontier/asm/rental.s` `rival_hook` sustituye esa instrucción por un `bl`. La función
  no usa `lr`. Hace la carga original y, con la Fábrica activa y `r7 < 3`, copia el
  índice al work `16433 + r7`. El último sorteo de cada hueco es el aceptado.
- Tests Unicorn en `tests/test_frontier_patch.py`.

**Script** (`frontier/factory.py`):
- **Tras cada victoria:** en `0x2264`, después de la comprobación de victoria y antes del
  menú de continuar, `factory_after_win`. Con la Fábrica activa, cada 7 victorias hace
  `GlobalCall 9771`, el sorteo del nivel siguiente, repetido hasta que se eligen 3. Si no,
  `GlobalCall 9772`, el intercambio.
- **Intercambio** (script compartido 5 `factory_swap`), dos menús:
  - qué alquiler das, o «No cambiar»;
  - qué conjunto del rival tomas (`maisonpkN`, con habilidad 0/1 al azar).
  - B en cualquiera de los dos mantiene el equipo.
- **Derrota:** `0x2210` (el camino de derrota) pone 16410 = 0 antes de que la Mansión
  guarde el récord (`0x3fdc` guarda la partida).
- **Texto 637 reorganizado:**
  - líneas 0–2, elegir alquiler; 3–5, intercambio;
  - 6–213, `maisonpkN` 0–207 (`LINE_N + índice`; ahí están todos los conjuntos de
    entrenadores de rango Normal);
  - desde 214, los Súper de los niveles de alquiler, en orden de hueco (`super_lines()`).
- **Fuera del intercambio:** el sorteo ya no limpia 16410 al cancelar; lo hace la
  recepción.

**Prueba** (`main-maison`, `work/frontier/build`):
- **Inscripción:** Honedge (Garra Rápida), Panpour (Campana Concha) y Joltik (Baya
  Aslac).
- **Combate 1:** Honedge cae contra Pansear; Panpour gana. «Ruben ha obtenido 1 PB.»
- **Oferta:** «¿Quieres cambiar un Pokémon de alquiler? Elige el que darías a cambio.»,
  con mis tres y «No cambiar» (`f4d_swap_give.png`).
- **Menú del rival:** Marill (Baya Tamar), Pansage (Baya Zidra) y Pansear (Baya Pasio),
  el equipo del rival vencido (`f4d_swap_take.png`). Elegí dar Honedge y tomar Marill.
- **Combate 2:** «El próximo combate será el número 2». El equipo es Marill, Panpour y
  Joltik Nv. 50 (`f4d_battle2_party.png`); el intercambio se aplica.
- **Primera derrota (build sin la limpieza en `0x2210`):** me retiré. La partida que
  guarda la Mansión al perder (`f4d_after_loss.sav`, `afa9cb02…`) tenía todavía
  16410 = 3: guarda dentro de su rutina de derrota, antes de que la recepción limpie.
  Además: 16411 = 61 (Marill), 16412 = 88, 16413 = 1128, 16433–16435 = 44, 2, 20 (equipo
  de Stunky) y 16429 = 1.
- **Con la limpieza en `0x2210`:** inscripción nueva y derrota en el combate 1. El
  guardado de antes del combate (`f4e_before_loss.sav`, `324e8690…`) tiene 16410 = 3; el
  de la derrota (`f4e_after_loss.sav`, `d20c94ed…`) tiene 16410 = 0 y 16433–16435 =
  41, 24, 54. Vuelta al campo sin problemas.

**Sin probar en Azahar** cuando se escribió esta sección: el sorteo tras la 7.ª
victoria, la pausa y la reanudación, y rechazar el intercambio. Las tres se probaron
después (§13). Nada en consola.

## 13. F4: pausa, reanudación y ronda completa (Azahar, 2026-11-02)

**Racha en la partida** (medido comparando guardados, bloque 37):
- `0x1BBC0`: racha actual de Individual Normal (`u16`). Pasa de 0 a 1 tras una
  victoria y una pausa (`f4f_before_pause.sav` → `f4f_paused.sav`), y vuelve a 0 tras
  perder.
- `0x1BBC4`: récord.
- En memoria es `[partida] + 0x195e0 + 0x1c4 + 2·rango`: `0x45cee8`, el que llama
  `GetMyWinCount`.
- Un primer intento de edición en `0x1BC00 + 0x1C4` (bloque 38) no tuvo efecto: la
  racha siguió en 0.

**Pausa**:
- «Pausar» tras ganar guarda la partida (`f4f_paused.sav`, `02c6d7f3…`): 16410 = 3, los
  3 alquileres, 16433–16435 del último rival y racha 1.
- La Mansión no tiene un caso de reanudación aparte: al volver a la recepcionista sale
  el menú normal, y la racha continúa al inscribirse otra vez en la misma modalidad.
- Corrección: si 16410 ≠ 0 al elegir «Fábrica Batalla» (desafío pausado),
  `factory_reception` no sortea y sigue con los alquileres guardados, como en Esmeralda
  (`test_reception_resumes_a_paused_factory_without_a_draft`).

**Reanudación con racha 6** (`f4f_paused_streak6.sav`, `aa5b24b3…`: la anterior con
`0x1BBC0` = `0x1BBC4` = 6):
- «Fábrica Batalla» → «Tu racha de victorias consecutivas obtenidas hasta el momento
  asciende a 6.» → «¿Quieres participar…?», sin sorteo (`f4g_resume1.png`–`3.png`).
- Combate 7 con los alquileres guardados (Swinub con PS llenos, `f4g_battle7.png`).
  Perdido.
- La partida de la derrota (`f4g_after_loss.sav`, `e0245289…`) tiene 16410 = 0, racha 0
  y récord 6.
- El rival tenía el conjunto N92, igual que uno de mis alquileres. La Mansión no excluye
  las especies del jugador (Esmeralda sí): desviación conocida.

**Ronda completa** (`f4h_paused_streak6_legend.sav`, `2703fb2a…`: la anterior con
16410 = 31 y alquileres S922 Latias, S915 Regice y S940 Tornadus, para asegurar la
victoria):
- Reanudación y combate 7 ganado. En vez del intercambio sale «Elige tu primer Pokémon
  de alquiler.» con 6 nuevos: Purugly, Gurdurr, Stunfisk, Mightyena… (`f4h_redraft.png`).
- Elegí 3 y salió «El próximo combate será el número 8» (`f4h_after_redraft.png`).
- Pausa → `f4h_paused_round2.sav` (`0c15ca2d…`): 16410 = 6 (IV de la ronda 2),
  16411–16413 = N152 Purugly, N132 Gurdurr y N154 Stunfisk, los tres del nivel 2
  (`maisonpkN` 132–169), racha 7 y 16429 = 7.

**Intercambio rechazado** (`f4f_no_swap.png`): «No cambiar» tras ganar mantiene el equipo
y sigue al menú de continuar.

## 14. F4: PB por ronda como en Esmeralda (Azahar, 2026-11-02)

**Cómo los da la Mansión** (`work/frontier/survey/zone517.lst`):
- Tras cada victoria se llama a `0x3de4(rango, tipo, jefe)`. Calcula los PB por tramo de
  racha: Normal 1 o 2; Súper de 2 a 7; jefe 20 o 50.
- `0x3f4c` los suma con `0x30` (`PlayerGetBP` + `PlayerSetBP` + `RecordAdd 34`) y dice
  «Ruben ha obtenido N PB.».

**Cambio** (`factory.battle_points`), insertado tras crear los locales de `0x3de4`
(`0x3e04`):
- Con la Fábrica activa, la racha sale de `GetMyWinCount(0, 0)`.
- Si no es múltiplo de 7, la rutina sale sin PB y sin mensaje.
- Si lo es, da `BATTLE_POINTS[ronda − 1]` (3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, el
  último repetido) y sigue en `0x3f4c` con el mensaje retail.
- La Mansión sin la Fábrica no cambia (tests `test_factory_battle_points_*`,
  `test_maison_battle_points_unchanged`).
- Sin el +10 tras el As del Frente (F5).

**PB en la partida** (medido): `0x4230`, `u16`; también cambia `0x1f488`. Las dos subieron
de 1 a 2 con la 7.ª victoria del build anterior (1 PB de la Mansión) y de 1 a 4 con el
build nuevo.

**Prueba** (`f4h_paused_streak6_legend.sav`, build nuevo):
- Reanudación, combate 7 ganado (Latias cayó ante Snubbull; Tornadus ganó) y sorteo de
  la ronda 2.
- Continuar → combate 8 con Klefki, Octillery y Cacturne del nivel 2. Perdido.
- La partida de la derrota (`f4i_after_loss.sav`, `d080c541…`) tiene PB 4 (+3 en la
  ronda 1), 16410 = 0, racha 0 y récord 7.
- El mensaje de PB no quedó en captura: los toques de pantalla lo pasaron.

## 15. F4: racha propia de la Fábrica (Azahar, 2026-11-02)

**Accesores de la racha de la Mansión** (lectura de `code.bin`; base = partida +
`0x195e0`; `r1` = tipo, `r2` = rango; tablas de saltos por tipo):

| Función | Individual | Instrucción sustituida |
|---|---|---|
| sumar 1 (`AddWinCount` → `0x1e3024`) | `0x45cdc4` | `add r1, r0, r2, lsl #1`, luego `+0x1c4` actual y `+0x1c8` récord |
| leer (`GetMyWinCount`, `0x45cee8`) | `0x45cf14` | `add r0, r0, r2, lsl #1` |
| poner a 0 (`ClearWinCount` → `0x45cf8c`) | `0x45cfb8` | `add r0, r0, r2, lsl #1` |
| leer récord (`0x45d010`) | `0x45d03c` | `add r0, r0, r2, lsl #1` |

En la partida son `0x1BBC0` (actual, Normal), `0x1BBC2` (Súper), `0x1BBC4` (récord,
Normal) y `0x1BBC6`.

**Desvío** (`frontier/asm/rental.s`, macro `FACTORY_SLOT`):
- Cada instrucción se sustituye por un salto a un trozo que, con rango Normal y el work
  16438 ≠ 0, apunta la base para que `+0x1c4` sea el work 16437 (racha de la Fábrica) y
  `+0x1c8` el 16439 (récord). Si no, ejecuta la instrucción original.
- Solo usa `ip` y las banderas, que el código siguiente vuelve a fijar.
- Todo lo de la Mansión que lee o escribe la racha de Individual Normal actúa sobre la
  de la Fábrica: número de combate, tramos de entrenador, PB, récords, `ClearWinCount`
  al perder.
- Tests Unicorn de las cuatro funciones completas: sin desvío, rango Súper, y desvío con
  récord nuevo.
- Hook total: 496 bytes.

**Script** (`factory.reception_routine`):
- `factory_reception` hace `SetRank(0)` y 16438 = 1 durante el desafío. Al volver lo
  pone a 0.
- Una inscripción nueva pone 16437 = 0, como en Esmeralda (cada desafío empieza en la
  ronda 1). Una reanudación la conserva.
- Volver al menú, cancelar o rechazar ponen a 0 16410, 16437 y 16438.
- La recepción pone 16438 = 0 justo después de `BattleInstWorkCreate`, por si una
  partida guardada a mitad de desafío lo dejó en 1.
- «Combatir» (opción 0) abandona una Fábrica pausada: 16410 = 16437 = 0.
- El sorteo ya no lee la racha de la Mansión: recibe 16429 = 0 al inscribirse y la
  racha de la Fábrica tras cada victoria.

**Prueba** (`main-maison-maison20`, `b442b8dd…`: `main-maison` con racha y récord de
Individual Normal en 20):
- «Fábrica Batalla» → sorteo → «¿Quieres participar…?» sin «Tu racha… asciende a 20».
- Partida guardada antes del combate (`f4j_saved.sav`, `becfbd96…`): Mansión 20/20,
  Fábrica 0, 16438 = 1.
- Combate 1 ganado y sin mensaje de PB. Intercambio rechazado. «El próximo combate será
  el número 2» (`f4j_next.png`).
- Pausa (`f4j_paused.sav`, `7195a65c…`): Fábrica 1, récord de la Fábrica 1, Mansión
  20/20.
- Reanudación: «Tu racha… asciende a 1» (`f4j_resume.png`). Combate 2 y retirada.
- Partida de la derrota (`f4j_after_loss.sav`, `355e5928…`): 16410 = 0, Fábrica 0,
  récord de la Fábrica 1, Mansión 20/20.

**Limitación conocida**: una partida guardada durante el desafío (al guardar antes del
combate, al pausar o al perder) queda con 16438 = 1. Hasta que vuelvas a hablar con la
recepcionista, las lecturas de la racha de Individual Normal de la Mansión van a las de
la Fábrica.
- Solo las hacen los scripts de la Mansión, salvo lo que no se haya visto: no se ha
  medido si la tarjeta de entrenador o el PSS muestran esa racha.
- La recepción lo limpia al entrar.

## 16. F6: medidas para el pase y el ferry (volcado, 2026-11-02)

Fuentes: listados `work/frontier/survey/shared79.lst`, `zone317.lst`, `zone212.lst`
(generados con `pawn.listing` y los nombres de `oras_natives.tsv`), tabla `GlobalCall` de
`code.bin`, `a/1/9/7` (datos de objeto) y `a/0/7/x`/`a/0/8/x` (textos).

**Campeón de la Liga: flag 2720** (PKHeX `flags_oras`: «Entered Hall of Fame»). Ningún
script lo activa con un literal (lo pone el código del Salón de la Fama); 37 lecturas
`FlagGet(2720)` en scripts retail, entre ellas el ferry (compartido 79, `0x8d8`) y el
marinero del puerto de Calagua (zona 317, `0x10ac`). La partida del usuario
(`inputs/save/20261031-123645/main`) es de principio de juego: 2720 = 0, un solo objeto
clave (216).

**Ferry: script compartido 79**, fila `GlobalCall` 33 (`0x587888`: ids 10430–10439,
texto 11). La zona 317 lo abre con `GlobalCall(10430)` desde el caso 5 (empleado, NPC
uid 0, modelo 300).
- `0x14a0` (caso 10430): `PlayerGetZoneID` → 275 (Portual) llama `0x8b8(4, 275)`; 317
  (Calagua) `0x8b8(0, 317)`; cualquier otra zona `0x8b8(0, 212)` (Resort). El primer
  argumento es el NPC que habla.
- `0x8b8(npc, zona)`: `ItemGetNum(736)` (Ticket del Barco) y `FlagGet(2720)`. Sin 2720,
  línea 0 («no está en servicio»); sin ticket, líneas 2–3; con ambos, líneas 4–5 y menú
  (`0x760` = `ListMenuInit(180, 112, 0, 1, 0, 0)`; `ListMenuAdd(línea, valor, 0)`):
  - zona 275: 6/valor 0 (Resort), 8/2 (Calagua), 9/3 (salir);
  - zona 317: 6/0 (Resort), 7/1 (Portual), 9/3;
  - otra: 7/1, 8/2, 9/3.
- Resultado (`0x7c8`, work 32784) → `SWITCH @1470`: 0 `@cb8`, 1 `@e84`, 2 `@1140`,
  otro `@13fc`. Cada caso confirma (línea 10/12/11 + Sí/No, `0x260`), despide (13) o
  dice 14, fija `WorkSet(16707, destino)` y `WorkSet(16709, 0)`, fundido (nativa 33 con
  (1, 2, 45), espera `0x210`), bocina (`SEPlay(655698)`) y `0x724` = `_MapChangeCore`
  con (zona, x, altura, y, dirección, 0):
  - al Resort, directo: (212, 53, 2, 34, 2), 16707 = 3;
  - entre Portual y Calagua, por el camarote (zona 216, (216, 37, 56, 9, 1)), 16707 =
    1 o 2;
  - del Resort a Portual o Calagua, directo, con `ReserveScript(1)`.
- 16707 solo lo lee la zona 216 (camarote); los puertos y el Resort solo lo escriben.
  Un viaje directo a la isla no necesita tocarlo.
- Texto 11 (16 líneas en los 8 idiomas): 0 sin servicio, 1–5 ticket, 6–8 destinos, 9
  salir, 10–12 confirmaciones, 13 despedida, 14 «espere a bordo», 15 variable.

**Pase del Frente: objeto 701** (Pase TMV de Kalos; no se puede obtener en ORAS).
- Datos idénticos a los del Mapa Viejo (442), que ya funciona en consola: bolsillo de
  objetos clave (4), precio 0, mismos bytes de cabecera (`a/1/9/7`).
- Ningún script lo da, quita ni consulta: 6 operandos con el valor 701, ninguno ante una
  nativa `Item*`. Control: la misma búsqueda encuentra `ItemGetNum(457)` (Pase de
  Concursos) en el compartido 27 y en la zona 276, por eso 457 se descarta.
- En `code.bin` aparece en el `movw` de una enumeración de todos los objetos
  (`0x5949dc`–…: `movweq r0, #0x2b1`, `#0x2b2`, …), como el 442.

**Puerto de Calagua (zona 317)**: 3 NPC. uid 0: empleado del ferry (caso 5). uid 1:
modelo 309, flag 1050, sin script. uid 2: marinero, modelo 232, caso 4. El caso 4 dice
la línea 23 del texto 523 sin la Liga y la 24 con ella.

## 17. F6: Pase del Frente y destino nuevo del ferry (Azahar, 2026-11-02)

Código: `frontier/island.py`, integrado en `frontier/overlay.py`. Tests:
`tests/test_frontier_island.py`, que ejecuta en `scripts/pawn_vm.py` (ahora con `SWITCH`)
el menú del ferry y el marinero. Tres roturas a mano (sin la entrada del menú, sin
cambiar la llegada, con el salto del marinero invertido) hacen fallar 2, 1 y 4 tests.

- **Objeto 701**: nombre, plurales y descripción en las entradas 113–117 de los textos
  de juego (ES; los demás idiomas, EN). Solo cambia la línea 701.
- **Marinero** (zona 317, evento 4): el caso apunta a una rutina nueva.
  - Con el flag 2720 y sin el objeto 701, dice la línea de presentación, da el pase con
    la rutina de entrega del compartido 10 (`0xC0C`) y dice la línea final.
  - En otro caso llama a su rutina retail.
  - Las dos líneas se añaden al final del texto 523: 30–31 sobre el retail, 44–45
    sobre el puerto del evento de Mew. Funciona con los dos puertos (test con el puerto
    de Mew construido en memoria).
- **Ferry** (compartido 79):
  - En Portual y Calagua, antes de «Me quedo aquí»: `ItemGetNum(701)` → si lo tienes,
    `ListMenuAdd(16, 4, 0)`.
  - Valor 4 en la tabla de destinos: copia del caso del Resort (`0xcb8`–`0xe84`) con
    la línea 17 y la llegada `island.ARRIVAL`.
  - **Provisional**: la llegada es la del Resort (212, 53, 2, 34, 2) hasta que exista la
    zona de la isla.
  - Textos: líneas 16–17 añadidas al texto 11.

**Prueba en Azahar** (`work/frontier/lab/f6_champion_ticket.sav`, `936975ed…`: la
partida de laboratorio `main` en la Ruta 102 con 2720 = 1 y el Ticket del Barco).
- Montaje: `faraway/dev_overlay.sh 317 0` (warp de desarrollo al puerto de Calagua) y
  `frontier/overlay.py`. Al laboratorio va `work/frontier/labroot`: el overlay de
  desarrollo con la build del Frente encima.
- Marinero: «Oye, ¿tú no eres quien ha ganado la Liga?», tres páginas, y «Ruben ha
  obtenido un Pase del Frente» (`f6_give.png`). Después, «Ruben mete el Pase del Frente
  en el Bolsillo Objetos Clave» y «Enséñale el ticket al empleado del ferry y elige la
  Isla del Frente…» (`f6_sailor_last.png`).
- Segunda vez: la línea retail 24, «El ferry S.S. Marea ya está en funcionamiento»
  (`f6_sailor_again.png`).
- Empleado del ferry: ticket y «¿Adónde te gustaría ir?». El menú muestra Resort
  Batalla, Ciudad Portual, **Isla del Frente** y Me quedo aquí (`f6_ferry_menu.png`).
- Isla del Frente: «Muy bien, rumbo a la Isla del Frente.», Sí/No
  (`f6_ferry_confirm.png`, `f6_ferry_yesno.png`). Sí: fundido y llegada al muelle del
  Resort (destino provisional).
  - Esta partida no había visitado el Resort, así que salta la escena retail de Blasco
    en su primera visita (`f6_arrival.png`). Es del Resort, no del ferry nuevo.

**No probado**:
- guardar la partida con el pase;
- otros idiomas;
- el menú de Portual (solo el test de la VM);
- la consola.

## 18. F6: zona de la isla (Azahar, 2026-11-02; en curso)

Código: `frontier/island_build.py`, llamado desde `frontier/overlay.py` salvo con
`--no-island`. Prepara una copia de los archivos que abre CTRMap-F5 (con las archivos
del Frente encima) y ejecuta `faraway/java/faraway/Build.java`. Al plan se añade
`keeptext.<zona>`: el clon conserva el texto del donante.

**Zonas libres** (`faraway/run.sh Probe … repurpose`, que llama a `ZoneRepurposeScanner`
de CTRMap-F5; salida en `work/frontier/island/repurpose.txt`):
- «SAFEST» solo son 473 y 474, las de Mew.
- 209 y 213 («Battle Resort», sin mapa, sin NPC, sin warps, sin disparadores) salen como
  «likely free».
- Ningún script empuja 209 o 213 antes de un cambio de mapa. Los únicos literales son
  209 como desplazamiento de flag (zona 368) y 213 como espera de fotogramas.
- Los cambios de mapa calculados de los compartidos 46, 71 y 74 son de Bases Secretas.
  El del 35 es un ayudante que recibe la zona como argumento.
- El texto 9 de la zona 209 son 12 líneas `[VAR BDFF n]` y no lo usa otra zona.
- Lugar 279: impar y vacío en los 8 idiomas; el 277 es el de Mew.

**Construcción** (`work/frontier/build-island/java.log`):
- **209 «Isla del Frente»**: clon de 212 (muelle del Resort) con mapa propio y área
  231.
  - Un solo NPC: el empleado del ferry, uid 0, modelo 300, evento 2 (`GlobalCall(10430)`),
    en (54,34).
  - Warp 0 → 213.
  - Script: el de 212 con el despachador reducido a −1, 1 y 2. En el 1 se cambia
    `JNZ @3f28` por `JUMP`.
- **213**: clon de 517 (sala de la Mansión con la Fábrica), con área 232 y el texto 619
  conservado. Script idéntico al de 517 parcheado (14.940 bytes). Warp 0 → 209.
- Llegada del ferry: `island.ARRIVAL` = (209, 53, 2, 34, 2).

**Errores medidos y corregidos**:
- Con el script de 212 entero, la llegada se cuelga. El evento 1 se ejecuta al llegar y,
  con 16615 = 0, monta la escena de Blasco con los NPC 1–3, que no existen: pantalla
  inferior oscurecida y sin control.
- Sin el evento 1, la pantalla se queda en blanco: ese evento hace la bocina, el fundido
  de entrada y `WorkSet(16707, 0)` (`0x3f28`).

**Probado en Azahar** (`f6_pass.sav`, `333ebfc5…`: `main` con 2720, Ticket del Barco y
Pase del Frente; warp de desarrollo al puerto, con gdb para leer la casilla):
- empleado de Calagua → «Isla del Frente» → llegada a (53,34) con la cámara normal, el
  nombre «Isla del Frente» abajo y control libre (`f6c_island.png`);
- al norte del muelle se entra en 213, la sala de la Mansión, con el mismo nombre
  (`f6c_hall.png`).

**Fallo abierto: hablar con la recepcionista de la Fábrica en 213 cuelga el juego.**
- La pantalla inferior se oscurece y la superior se congela a 0 FPS.
- El CPU sigue en marcha, dentro de un formateador `printf` (`0x2ff9f0`/`0x2fee84`).
- En la pila se está formateando la cadena «0x08d73c4c». Hay retornos en `0x3dc308`,
  `0x3ffc54` y `0x50334c`: parece un aviso o volcado de error del juego que no vuelve.
- En 517 la misma recepcionista funciona (§11–§15).
- Sin probar todavía:
  - si cuelga cualquier NPC de 213 o solo los de la Mansión;
  - qué comprueba el código (zona 517, área, registro de NPC…).

**Pendiente**:
- la vuelta en ferry desde la isla (empleado uid 0, rama «otra zona»);
- salir de 213 a 209;
- guardar en la isla;
- la consola.

## 19. F6: el cuelgue de la sala clonada, resuelto (Azahar, 2026-11-03)

**Causa medida: los grupos de nativas se registran por zona.** La sala 213 ejecuta el
script de 517, que llama a nativas de la Mansión, y el juego solo las registra en las
zonas 448, 517 y 520.
- `code.bin` `0x587d58`: una máscara `u32` por zona (536 entradas, indexadas por el
  número de zona).
- El cargador de scripts de zona (`0x3ff5a4`) la pasa a `0x3fbc80`, que hace un
  `amx_Register` (`0x506190`) por cada bit.
- Bit 8 (`0x100`): el captador `0x19c908`, que salta a `DllField.cro+0x95e6c`, devuelve
  la tabla de 50 nativas de `0xf8b44` (`BattleInstWorkCreate` … `TrialHouse_GetDLItem`).
- Valores: 0x243 por defecto; 0x343 solo en 448, 517 y 520.
- Los otros dos usos de la tabla son de los scripts compartidos. `0x3fb230` busca el id de
  `GlobalCall` en la tabla de rangos `0x587678` y toma `0x587bd8[grupo]`. Ningún grupo
  compartido lleva el bit 8.

**Cómo se midió (gdb, lab con `f6_pass.sav`):**
- En el cuelgue, `amx_Exec` (`0x503310`) llama sin cesar a `amx_Register(amx, NULL, 0)`:
  1.605 llamadas desde `0x50334c` tras cargar la zona. Comprueba el flag `NTVREG`
  (`0x1000`), que nunca llega a ponerse.
- Rompiendo en la rama de nativa no encontrada (`0x5062c4`, error 19), en la tabla de
  nativas del AMX cargado (14.937 bytes, 120 nativas) hay 44 sin resolver. Las 44 son del
  grupo de la Mansión (`_CallTrialDownloadApp`, `BattleInstWorkCreate`, `SetTrainer`,
  `StartBattle`…). Las otras 76 resuelven. Se reproduce con `python frontier/zone_natives.py
  --amx work/frontier/lab/gdb-f6e-natives213.txt` (sin `--amx`, solo las tablas estáticas).
- Al cargar 213 se registran 9 tablas: `0x3aaef8`–`0x3aaf20` y `0x3fbca8`/`0x3fbcc4`/
  `0x3fbd50`/`0x3fbda0`. La máscara recibida es 0x243.
- Por eso cuelga cualquier NPC de 213, no solo la recepcionista: el NPC 7 en (27,13)
  también lo hacía.
- Lo que se formateaba en la pila (`0x08d73c4c`) es la dirección de la entrada sin
  resolver. No es un error del juego.

**Descartado (medido):** el campo `0x18` de la cabecera de zona es un índice único por
zona (permutación de 0–537 en las 536 zonas). Con 213 = 12, como 517, el cuelgue sigue
igual. El cambio de prueba se deshizo.

**Arreglo**:
- `frontier/patch.py` `zone_natives(code, clones)` copia a cada clon la máscara de su
  donante. Antes comprueba que la tabla es la medida (bit 8 exactamente en 448, 517 y
  520; todas las máscaras con 0x243) y que el clon tiene la máscara por defecto.
- `island_build.CLONES` (`{209: 212, 213: 517}`) es a la vez la lista de clones del plan de
  CTRMap y la de máscaras. `overlay.py` se la pasa a `patch.build`.
- Tests:
  - `test_zone_natives_*`: solo cambia la palabra de 213, y la tabla inesperada se
    rechaza;
  - `test_every_island_clone_gets_its_donors_native_groups`.
- Roturas a mano: sin la escritura, y sin la comprobación de la tabla. En cada caso falla
  un test.

**Probado en Azahar** (overlay `work/frontier/build`; capturas `work/frontier/lab/f6e_*`):
- En 213 la recepcionista habla y su menú muestra «Fábrica Batalla» (`f6e_hall_menu.png`).
  «Combatir» abre la pantalla de tipo de combate (`f6e_battletype.png`).
- **Fábrica en 213:**
  - «Elige tu primer/segundo Pokémon de alquiler» (`f6e_factory_draft.png`);
  - Combates Individuales y guardado en la recepción;
  - combate con los alquileres Cranidos, Larvitar y Snubbull (`f6e_battle_party.png`).
  - Perdido el combate, se vuelve a la sala con «Isla del Frente» en pantalla
    (`f6e_after_battle.png`), no a la Mansión real.
- **Guardar y cargar en 213:** `f6e_saved_213.sav` (`c013ad56…`), guardada por la
  Fábrica en la recepción de 213. Al arrancar con ella se aparece en la sala 213 delante
  de la recepcionista, y habla.
- Salida de 213 → muelle de la isla (37,22), con el nombre «Isla del Frente».
- **Ferry de vuelta:** el empleado de la isla (54,34) ofrece Ciudad Portual, Ciudad
  Calagua y «Me quedo aquí» (`f6e_island_ferry.png`). Se eligió Portual: viaje y llegada
  al puerto de Portual (`f6e_slateport.png`).

**Sin probar**:
- el viaje de vuelta a Calagua desde la isla;
- la entrada «Isla del Frente» del ferry de Portual (solo con `pawn_vm`);
- ganar una ronda de la Fábrica en 213;
- guardar desde el menú en el muelle 209;
- la consola.
