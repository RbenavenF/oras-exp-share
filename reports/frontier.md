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

## 20. F6: ferris, guardado en el muelle y una ronda ganada en la isla (Azahar, 2026-11-03)

Overlay `work/frontier/build` (el mismo `code.ips` que §19). Capturas en
`work/frontier/lab/f6f_*`.

**Probado en Azahar**:
- **Guardar desde el menú en el muelle 209**:
  - el resumen de guardado muestra «Isla del Frente» (`f6f_save_prompt.png`);
  - partida `f6f_saved_pier.sav` (`91b41949…`), hecha a partir de `f6e_saved_213.sav`;
  - al arrancar con ella se aparece en el muelle (37,44), con control libre
    (`f6f_pier_reload.png`).
- **Vuelta a Calagua**: el empleado de la isla → «Ciudad Calagua» → «Muy bien, rumbo a
  Ciudad Calagua.» → llegada al puerto de Calagua (`f6f_lilycove.png`). Allí el ferry
  ofrece Resort Batalla, Ciudad Portual, Isla del Frente y «Me quedo aquí»
  (`f6f_lilycove_menu.png`).
- **Ferry de Portual**:
  - con el warp de desarrollo al puerto de Portual (zona 275, warp 0) y `f6_pass.sav`,
    el empleado (17,24) ofrece Resort Batalla, Ciudad Calagua, Isla del Frente y «Me
    quedo aquí» (`f6f_slateport_menu.png`);
  - «Isla del Frente» → «Muy bien, rumbo a la Isla del Frente.» (`f6f_slateport_go.png`)
    → llegada al muelle (53,34) (`f6f_slateport_arrival.png`).
- **Ronda ganada en la sala 213** (desde `f6f_saved_pier.sav`):
  - alquileres Larvitar, Venipede y Carvanha contra Glameow, Chespin y Swinub;
  - victoria (`f6f_win.png`);
  - la recepcionista ofrece el cambio. Se dio Larvitar (`f6f_swap_give.png`) y se tomó
    Glameow (`f6f_swap_take.png`);
  - «El próximo combate será el número 2» con Continuar / Pausar / Guardar vídeo
    (`f6f_next_battle.png`);
  - el combate 2 empieza con Glameow contra Skorupi (`f6f_battle2.png`).

**Trampas del laboratorio** (medidas en esta sesión):
- `work/frontier/build` se genera sobre el overlay de desarrollo (`--romfs
  work/faraway/dev/overlay/romfs`) y su `a/0/1/3` lleva el warp de la Ruta 102. Tras
  `faraway/dev_overlay.sh ZONA WARP` hay que volver a ejecutar
  `python frontier/overlay.py --out work/frontier/build --romfs work/faraway/dev/overlay/romfs`.
  Si no, el warp sigue llevando a la zona anterior (pasó con 275 → seguía en 213).
- Teclas del perfil del laboratorio (`qt-config.ini`):
  - A = `a`, B = `s`, X = `z`, Y = `x`;
  - cruceta: `t` arriba, `g` abajo, `f` izquierda, `h` derecha;
  - `b` es HOME, no B.
- A velocidad 300 %, una pulsación de cruceta de 0,25 s se repite en los menús. Con
  0,08 s mueve una sola entrada.
- El trayecto Calagua → Portual pasa por el camarote del S.S. Marea. No se completó
  por esa vía: el camarote en (30,7) no era el del jugador. Para Portual se usó el
  warp de desarrollo.

**Sin probar**: la consola.

## 21. F6: la plaza de la isla, con la Fábrica enlazada y seis maquetas (Azahar, 2026-11-03)

**Qué es.** La mitad sur del muelle de la isla y el mar de alrededor (celda propia 0,1 de la
zona 209, región 864) se repintan como una explanada de camino. Encima van 7 edificios del
catálogo de CTRMap-F5, uno por instalación de Esmeralda (`island_build.FACILITIES`).
- **Pintor**: el de CTRMap-F5 en modo compuesto (`faraway/java/ctrmap/tests/FrontierPlaza.java`,
  `faraway/java/faraway/Plaza.java`). Las casillas fuera del rectángulo conservan el mar y el
  muelle del puerto.
- **Puertas**: el pintor no cablea ninguna (`DoorWiring.SKIP`). `Plaza` sustituye los warps
  de la isla por uno solo: la puerta del Gimnasio (la Fábrica), casilla (20,57) → zona 213,
  warp 0. La salida de 213 (su warp 0) vuelve a la puerta.
- **Maquetas**: las otras seis puertas no tienen warp.
- Se entra en la explanada bajando desde el embarcadero; el empleado del ferry sigue en
  (54,34).

| Instalación | Edificio | Ancla (local) |
| --- | --- | --- |
| Torre | Dewford shingle house | 16,2 |
| Domo | Lavaridge house | 4,13 |
| Fábrica | Gym (puerta → 213) | 16,13 |
| Pirámide | Lavaridge house | 30,13 |
| Tubo | Dewford shingle house | 3,25 |
| Arena | Lavaridge house | 17,25 |
| Palacio | Dewford shingle house | 28,25 |

**Dos límites medidos** (variantes con `frontier/lab_plaza.sh`, base sin plaza de
`frontier/lab_plaza_base.py`; arranque con `f6f_saved_pier.sav`; «cuelgue» = pantalla negra a
0 FPS al cargar la isla):

| Variante | Resultado | Área 231 (`a/0/1/4`) | Región 864 (`a/0/3/9`) |
| --- | --- | --- | --- |
| v0 sin plaza | carga | 253.933 | 49.502 |
| v1 solo camino | carga | 269.123 | 71.065 |
| v4 camino + abeto | carga | 323.871 | 76.571 |
| v3 casa de Lavacalda **con** prop de puerta | cuelga | 296.234 | 98.187 |
| v5 la misma casa **sin** prop de puerta | carga | 297.475 | 98.165 |
| v2 Gimnasio con prop | cuelga | 293.874 | 101.474 |
| v7 Gimnasio sin prop | carga | 292.994 | 101.449 |
| v8 Sala de Concursos sin prop | carga | 365.535 | 94.617 |
| v11 Sala de Concursos + Gimnasio | carga | 386.675 | 123.952 |
| v10 cuatro edificios distintos | cuelga | 467.393 | 181.548 |
| v14 siete de dos pueblos | cuelga | 458.007 | 258.497 |
| v6 / v12 siete distintos (v12 sin pasajeros) | cuelga | 625.239 / 557.461 | 265.694 / 251.184 |
| v13 siete veces la misma casa | carga | 297.475 | 225.492 |
| v15 Gimnasio + dos casas repetidas (la elegida) | carga | 333.123 | 222.687 |

Conclusiones:
1. **El prop de puerta cuelga la carga** aunque el área sea pequeña: compárense v3 con v5 y
   v2 con v7. No se ha investigado el porqué (registro de props del área 231, o sus
   texturas). Por eso ningún edificio lleva prop (`|nodoorprop` en el plan, y
   `island_build` lo rechaza). La puerta sin prop funciona igual: en retail la casilla de
   la puerta del Gimnasio de Azuliza también es `21000001` (bloqueada) y el warp salta al
   empujar contra ella.
2. **Las texturas que cada edificio arrastra al área tienen un límite**:
   - el tamaño de la región no es el límite: v13 carga con 225.492 bytes de región, y v10
     cuelga con 181.548;
   - el área sí lo marca: carga hasta 386.675 bytes y cuelga desde 458.007;
   - hay áreas retail más grandes (hasta 871.676), así que el límite real (memoria de
     texturas, número de texturas…) no se ha medido. Se usa la cota medida:
     `island_build.AREA_LIMIT = 386675`, y la build se niega a pasarla;
   - un modelo repetido no arrastra texturas nuevas: de ahí las dos casas repetidas.

**Probado en Azahar** (overlay `work/frontier/build`; capturas en `work/frontier/lab/f6g_*`):
- la isla carga en el muelle con la explanada y las casas a la vista (`f6g_plaza1.png`);
- delante de la Fábrica (`f6g_factory_front.png`), empujando hacia arriba se entra en la
  sala 213 (`f6g_hall.png`);
- al salir de 213 se aparece en (20,58), delante de la puerta (`f6g_back.png`);
- la puerta de la Pirámide (maqueta) no deja pasar (`f6g_mock.png`);
- desde la explanada se vuelve al embarcadero y el empleado del ferry habla
  (`f6g_clerk.png`).

**Defectos visibles** (sin arreglar):
- las barandillas del muelle original siguen dibujadas sobre la explanada (son de las
  celdas vecinas);
- la cerca que viene con la casa de Lavacalda bloquea (33–34, 58).

**Sin probar**:
- la consola;
- guardar en la explanada;
- combatir en 213 tras entrar por la puerta nueva. Es el mismo script y la misma zona que
  en §19–§20.

## 22. F6: partida completa por la puerta de la Fábrica (Azahar, 2026-11-03)

Overlay `work/frontier/build` del commit `ea733e9`, montado como en §21 (overlay de desarrollo
debajo, `code.ips` de la build). Partida de inicio: `f6f_saved_pier.sav` (`91b41949…`).
Capturas en `work/frontier/lab/f6h_*`.

**Probado en Azahar**:
- Del muelle (37,44) a la explanada y a la casilla (20,58). Empujando hacia arriba se entra
  en la sala 213 y se aparece en (20,31) (`f6h_hall.png`).
- La recepcionista de la izquierda (17,25) es la del registro de la Mansión («¿Quieres
  consultar tus resultados?»). La de los combates es la de la derecha: se le habla desde
  (23,25) mirando arriba.
- Su menú ofrece «Fábrica Batalla». Se sortean seis alquileres: Honedge (Garra Rápida),
  Snorunt (Roca Helada), Omanyte (Baya Tamar), Geodude (Roca Suave)…
  - se eligieron los tres primeros que ofrecía cada lista;
  - «¿Quieres participar en Combates Individuales?» → guardar → Sí.
- **Combate 1**: Honedge contra Gothorita (`f6h_battle1.png`). Rival: Gothorita y Kricketune
  como mínimo. Honedge y Snorunt cayeron; salió Omanyte.
- **Fin de la ronda**: no se capturó. Se pulsó A de más y se volvió a abrir el menú normal
  de la Mansión («Combate Individual»). Se salió con la flecha táctil y «¿Prefieres no
  participar?» → Sí.
  - Después, el equipo es el propio del jugador (Torchic, Beldum, Poochyena, Cascoon,
    Silcoon, Shroomish; `f6h_party_after.png`). Es decir, la ronda terminó en derrota y la
    limpieza devolvió el equipo, como en §12.
- Salida de la sala: desde (20,31), empujando hacia abajo se aparece en la explanada
  delante de la puerta (`f6h_plaza_out.png`).
- **Guardar en la explanada**: el resumen muestra «Isla del Frente» (`f6h_save_prompt.png`).
  Partida `f6h_saved_plaza.sav` (`00a9a98f…`).
- **Recarga**: con esa partida se aparece en (20,59), delante de la Fábrica, con control
  libre: se baja a (20,60) (`f6h_plaza_reload.png`).

**Trampas del laboratorio** (medidas en esta sesión):
- En la explanada, una pulsación de cruceta de 0,08 s avanza unas dos casillas (de 37,44 a
  37,75 con 16 pulsaciones). Con `HOLD=0.04 faraway/walk.sh` avanza una.
- B no cierra el menú táctil de la Mansión. Se toca la flecha con
  `python scripts/azahar_lab.py input mousemove 735 690 mousedown 1 sleep 0.2 mouseup 1`
  (coordenadas de la ventana del laboratorio). `click 1` es demasiado corto.
- Para usar `faraway/walk.sh pos` hay que poner `use_gdbstub=true` y
  `use_gdbstub\default=false` antes de arrancar, y lanzar `faraway/gdbctl.sh start`.
  Al acabar se devuelven a `false` y `true`.

**Sin probar**:
- la consola;
- ganar una ronda entrando por la puerta nueva. La victoria y el intercambio se
  probaron en la misma sala en §20, entrando por el warp antiguo del muelle.

## 23. F6: el cuelgue de las puertas era una textura fuera de su paquete; la cota del área, refutada (Azahar, 2026-11-03)

Corrige las dos conclusiones de §21. Variantes de la plaza en `work/frontier/plaza-exp/` y
capturas `work/frontier/lab/f6g_*` y `f6i_*`. Los scripts de medida de esta sección
estaban en el directorio temporal de la sesión y no se conservan; lo que queda es lo que
se repite con `faraway/run.sh WorldTextures GAME WS 209`.

**Causa**:
- Un área tiene dos paquetes de texturas:
  - fichero 11 del contenedor AD, el del mapa;
  - fichero 1, el de los props.
- El juego busca las texturas de los modelos del mapa solo en el fichero 11.
- El traslado de texturas del pintor de CTRMap-F5 da una textura por presente si está en
  cualquiera de los dos (`BchTexturePack.missingIn`, `tools/CTRMap-F5/src/ctrmap/formats/h3d/BchTexturePack.java:584`,
  llamado desde `planCarry`, línea 508).
- Si la textura de un edificio solo está en el paquete de props, no se copia al del mapa
  y la isla se cuelga al cargar.
- Pasa de dos maneras:
  - el prop de puerta importa al paquete de props una textura que el edificio también
    usa: `chip_mado_a` (casa de Lavacalda) y `poke_gym_mado` (Gimnasio);
  - el paquete de props del área original del puerto ya tiene la textura: `c102_09_mado`
    en v6, v10 y v12, que no llevaban ningún prop.

**Medidas** (`WorldTextures` lista las texturas de los modelos del mapa que faltan en el
fichero 11; control: en el área sin pintar, v0, la lista sale vacía):

| Variante | Resultado | Fuera del paquete del mapa |
| --- | --- | --- |
| v0, v5, v7, v8, v11, v13, v15 | cargan | ninguna |
| v3 (casa con prop de puerta) | cuelga | `chip_mado_a` (solo en props) |
| v2 (Gimnasio con prop) | cuelga | `poke_gym_mado` (solo en props) |
| v6, v10, v12 | cuelgan | `c102_09_mado` (solo en props) |
| v14 | cuelga | ninguna |

**Partición del prop de puerta** (variantes hechas a mano sobre v3/v5; control: la lista de
props generada con la referencia 0x3a coincide byte a byte con la de v3):
- «solo registro» (v3 sin el prop colocado): cuelga;
- «solo colocación» (v5 con un prop del modelo 0x53, registrado de origen): carga (brillo
  118,9; v5 en el mismo montaje: 118,7);
- **fix11** (v3 entero con el fichero 11 de v5, que tiene `chip_mado_a`): carga (119,8).
  Solo difiere de v3 en el fichero 11.
- La entrada que el pintor añade al registro de props es idéntica byte a byte a las de las
  áreas originales con esos modelos (áreas 9–24, 202, 203).
- Mientras cuelga, el hilo principal está en un bucle de espera, y un hilo de carga en
  `svc 0x32` (SendSyncRequest) en 0x1f76a4 (gdb, `info threads`).

**Arreglo** (en nuestro código; CTRMap-F5 es de su autor y no se ha tocado):
- `FrontierPlaza.keepWorldTexturesInWorldPack` copia al fichero 11 las texturas de los
  modelos del mapa que solo tiene el fichero 1;
- después vuelve a preguntar y se niega si falta alguna;
- `Plaza` lo ejecuta tras el pintado;
- `island_build` exige su línea en el registro.
- Con el arreglo, v3 y v10 cargan (v3f, v10f). v6 y v14 siguen colgándose.

**La cota de §21 (386.675 bytes de área empaquetada), refutada**: v10f carga con 467.609 bytes
y v14f se cuelga con 458.007. Se cambia por la suma que imprime `Plaza` («load budget»):
paquete del mapa + paquete de props + modelos de todas las regiones de la isla, sin
comprimir.

| Variante | Resultado | Presupuesto | Paquete del mapa |
| --- | --- | --- | --- |
| v0 | carga | 1.849.472 | 342.272 |
| v5 / v3f | carga | 2.078.208 / 2.080.768 | 420.224 / 418.176 |
| v13 (siete veces la misma casa) | carga | 2.411.392 | 420.224 |
| v15 (Gimnasio + dos casas repetidas) | carga | 2.527.872 | 544.128 |
| v10f (cuatro edificios distintos) | carga | 2.724.608 | 827.136 |
| v14f (siete de dos pueblos) | cuelga | 2.986.112 | 903.168 |
| v6f (siete distintos) | cuelga | 3.396.352 | 1.256.704 |

- `island_build.LOAD_BUDGET = 2724608`: lo mayor medido que carga.
- No es el límite real del motor: hay áreas originales con paquetes del mapa mayores (área
  11: 1.418.112) y regiones originales con modelos de hasta 1.349.504 bytes (región 389).
  Lo más probable es un presupuesto de memoria conjunto, que no se ha medido.
- Las dos casas de Férrica (las únicas comunes a v6 y v14) cargan solas (brillo 118,7 y
  118,9).

**Build** (`python frontier/overlay.py --out work/frontier/build --romfs work/faraway/dev/overlay/romfs`):
- los siete edificios llevan su prop de puerta (sin `nodoorprop`);
- copia `chip_mado_a` y `poke_gym_mado` al paquete del mapa;
- presupuesto 2.540.160 bytes.

**Probado en Azahar** (desde `f6h_saved_plaza.sav`):
- la isla carga; el Gimnasio muestra su puerta de cristal (`f6i_boot.png`);
- empujando contra ella se entra en la sala 213 (20,28), y al salir se aparece en (20,58)
  (`f6i_back.png`);
- la puerta de la Pirámide (maqueta) sigue sin dejar pasar (31,58; `f6i_mock.png`).

**Guardas probadas rompiéndolas**:
- sin la copia en `keepWorldTexturesInWorldPack`, la build se niega: «zone 209's map draws
  with textures its world pack lacks {chip_mado_a=true, poke_gym_mado=true}…»;
- `check_budget` con `> LOAD_BUDGET + 1` y con la primera línea en vez de la última: falla
  `test_island_load_budget_over_the_measured_one_is_refused` en los dos casos.
- La exigencia de las líneas «Swinging-door prop(s) placed» y «world textures copied» en el
  registro no se ha probado rompiéndola.

**Sin probar**:
- ver la animación de apertura de la puerta (la captura cayó en el fundido);
- la causa del cuelgue de v6 y v14;
- la consola.

## 24. F6: la plaza fija, con un edificio distinto por instalación (Azahar, 2026-11-03)

**Coste de cada edificio** (`frontier/lab_building_costs.sh`, sin emulador; salida en
`work/frontier/survey/building_costs.txt`). Es el presupuesto de carga (§23) con el edificio
solo, con su puerta, en (16,13). Con solo el camino: 1.945.984 bytes; margen hasta
`LOAD_BUDGET`: 778.624. Lo que añade cada uno, en KB:

| Edificio | KB | Edificio | KB |
| --- | --- | --- | --- |
| Tienda | 79 | Casa de Pardal | 108 |
| Casa de Lanette (Ruta 114) | 92 | Centro Pokémon | 115 |
| Cabaña de la Ruta 124 | 99 | Casa de la playa (Ruta 109) | 116 |
| Choza de Pacifidlog | 102 | Casa de Lavacalda | 135 |
| Casa de paja del Resort | 106 | Casa de tejas de Azuliza | 142 |
| Férrica, tejado plano | 106 | Gimnasio | 145 |
| Férrica, dos plantas | 155 | Sala de Concursos | 312 |
| Casa cúpula de Arrecípolis | 410 | | |

Los costes no se suman exactamente: los edificios del mismo área de origen comparten
texturas. Por ejemplo, las dos casas de Férrica juntas cuestan menos que por separado.

**Edificios que no se dibujan**:
- la choza de Pacifidlog y la casa de Lanette se cortan y se colocan (1.470 y 1.108
  triángulos según el pintor), pero en la isla solo se ve su suelo, el felpudo y la puerta;
- su colisión sí bloquea (`f6j_pyramid.png`, `f6j_palace.png`);
- no se ha investigado por qué. `island_build.NOT_DRAWN` los rechaza.

**Distribución fija** (`island_build.FACILITIES`; casillas globales de la zona 209):

| Instalación | Edificio | Puerta | Frente |
| --- | --- | --- | --- |
| Torre | Férrica, tejado plano | (19,46) | (19,47) |
| Domo | Casa de Pardal | (6,56) | (6,57) |
| Fábrica | Gimnasio → sala 213 | (20,57) | (20,58) |
| Pirámide | Casa de tejas de Azuliza | (32,57) | (32,58) |
| Tubo | Cabaña de la Ruta 124 | (5,69) | (5,70) |
| Arena | Casa de paja del Resort | (20,69) | (20,70) |
| Palacio | Férrica, dos plantas | (31,69) | (31,70) |

- Presupuesto 2.665.344 bytes (`load budget` del registro de la build).
- La copia de texturas de §23 actúa: `battle01_object_a_dif01`, `build02`,
  `c102_09_mado` y `poke_gym_mado`. Sin ella, la isla se colgaría.
- El área 231 y las regiones 862–865 de la build son idénticas byte a byte a las de la
  variante `fix7b` recorrida en el emulador.

**Probado en Azahar** (capturas `work/frontier/lab/f6j_*`; posición por gdb):
- La isla carga (brillo 119,8) y se ven los siete edificios.
- Se llega al frente de cada puerta por la explanada.
- Las seis maquetas bloquean: se empuja desde el frente y la posición no cambia.
  - Domo, Tubo, Arena y Torre, con la variante `fix7`;
  - Pirámide y Palacio, con `fix7b`.
- La Fábrica, con la build definitiva: se entra en la sala y al salir se vuelve delante
  de la puerta (`f6j_final_hall.png`, `f6j_final_back.png`).

**Defectos visibles** (sin arreglar):
- la casa de Azuliza sale con el tejado azul (probablemente texturas con el mismo nombre
  que otra del área);
- las barandillas del muelle original al este de la explanada;
- las dos casas de Férrica se parecen.

**Zonas para los interiores**: el escáner de §18 (`work/frontier/island/repurpose.txt`) da 46
zonas «likely free» por debajo de 536 (las únicas que ejecutan scripts), aparte de 209 y 213.
Cada una hay que verificarla antes de usarla, como 209 y 213 en §18.

**Sin probar**:
- la consola;
- por qué no se dibujan la choza y la casa de Lanette.

## 25. F6-TORRE: Torre v1, rutas y exclusión mutua (2026-11-03/04)

Implementación en `frontier/tower.py`, desde el script **retail** de 517; integración en
`overlay.facility_scripts`, `island_build.CLONES/DOORS`. Individual, rango Normal, equipo propio
con la selección y el ajuste de nivel de la Mansión. Ruta 2: works 16441 (racha), 16442
(desafío activo), 16443 (récord). Los PB se dan cada siete victorias según
`data.FRONTIER_BP['tower']`. `factory.busy_check` impide entrar en un desafío si otra
instalación tiene su `patch.ACTIVE_WORK` distinto de cero, en ambas recepciones.

**Zona 329, comprobaciones de §18**:
- `frontier/zone_check.py 329`, salida `work/frontier/tower/zone_check.txt`: sin warps
  retail entrantes; máscara original 0x243. Los dos operandos 329 no son destinos: el
  compartido 57 (`0xBD0`, llamada a `0x77C`) lo usa como flag de objeto; la zona 275
  (`0x3FB0`) como entrenador. El escáner marca también `JUMP`, que no implica cambio de mapa.
- 36 palabras alineadas con valor 329 en código/CRO, frente a 48 para 209 y 45 para 213;
  el recuento es orientativo, no una demostración de ausencia de usos calculados.
- Build completa del 2026-11-03: clon de 517 con área propia 233, texto 619, parent 279
  (`ZoneHeader.parentMapOf`: u16 de cabecera +0x1C & 0x3FF), máscara parcheada 0x343.
  ZO 15.832 bytes, por debajo de los 17.248 medidos. 213 conserva área 232 y máscara 0x343.
- Fuentes: `work/frontier/build-island/java.log`, `work/frontier/tower/build-codex.log` y
  `build-evidence.json` (hashes de todos los archivos generados y máscaras/cabeceras).
- Carga y recepción de 329 observadas por Claude y repetidas por Codex desde una partida
  guardada allí. Salida medida por GDB (`faraway/walk.sh pos`): (19,47), captura
  `work/frontier/lab/f6tc_tower_exit.png`.

**Relevo de `bdae3b7`**:
- La selección de equipo rechazaba todos los Pokémon hasta ejecutar primero la selección
  de modalidad de la Mansión (`0x12A0`, `_CallTrialDownloadApp`). Corregido en ese commit,
  conservando la rutina de selección de equipo `0x457C` intacta.
- La sesión de Claude jugó desde una copia con racha editada a 6 y equipo fuerte generado
  por `frontier/lab_tower.py`. Guardó en 329 antes de combatir (`f6t_saved_329.sav`,
  SHA256 `33bb1d0fae0a68699340624aabb6422750126bb5cf4743d437e1edde21992db7`) y pausó
  con racha/récord 12 y 1 PB (`f6t_paused12.sav`,
  `df1b162bf818a9a27b9862646f297336fe4e36d7a57c7eed72db411934d2155a`).
  Es evidencia heredada de seis victorias, incluido el final de ronda 7, no una ronda
  iniciada desde cero. Comandos/resultados recuperados en
  `work/frontier/tower/previous-transcript.txt`.

**Azahar, repetido por Codex con la build completa**:
- Cargar `f6t_paused12.sav`, recepción, selección de los tres Pokémon propios, combates
  13 y 14 ganados; el juego ofrece el combate 15 y entrega **2 PB** al terminar el 14
  (`f6tc_tower_bp2.png`, `f6tc_next15.png`). Los Pokémon fuertes están al nivel 50 en combate.
- Pausa elegida en el menú y guardada: `f6tc_paused14.sav`, SHA256
  `eb6d1fa2ce58e3dafaec9847d36b344bfecff622cf05ba9b46f8f7ee799d4eb9`:
  zona 329, works 16441/16442/16443 = 14/1/14, ruta guardada 2, **PB 3**.
  Fábrica 16410/16437/16439 = 0/0/0; los cuatro u16 de Mansión en 0x1BBC0 siguen a cero
  y todo su bloque 0x1BA00–0x1BC00 es idéntico al de racha 12.
- Equipo: no se sustituye por alquileres. Entre los guardados 6 y 12 solo cambian los
  PS actuales (+0xF0 del PK6 descifrado) de dos Pokémon curados. Entre 12 y 14 cambia
  el PK6 del tercer Pokémon en +0xCC–0xD0 y su checksum: son intensidad, recuerdo, variable
  y sentimiento del entrenador original según [PKHeX, PK6.cs](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/PK6.cs).
  No se afirma identidad byte a byte de todo el bloque del equipo.
  Especies, objetos, movimientos, EXP y EV/IV se conservan.
- Mediciones de partidas: `work/frontier/tower/snapshot.py` y `save-evidence.jsonl`,
  basadas en `save_event`/`save_fixture`, con validación de checksums.

**Azahar, 2026-11-04 (Claude; build con los works nuevos de la Fábrica, capturas `work/frontier/lab/f6td_*`)**:
- **Derrota**: desde `f6tc_paused14.sav`, reanudación (racha 14), equipo propio, combate 15 y «Huir» → «¿Quieres
  abandonar…?» Sí. La partida que guarda la derrota (`f6td_after_loss.sav`, SHA256
  `692f9d4a041545ecb6e2928b6f6a96b7068d12bc3c639fe3c2f4811593cf313c`): zona 329, 16441/16442/16443 = 0/0/14,
  PB 3, Mansión 0x1BBC0 a cero. La ruta queda en 2 en esa partida hasta la siguiente recepción (limitación de §15).
- **Fábrica → Torre** (sesión anterior de Claude, build `9dc2dc8`): con la Torre pausada (16442 = 1), elegir
  «Fábrica Batalla» en 213 da «Tienes un desafío a medias…» y vuelve al menú (`f6t_factory_refused.png`); la línea
  se cortaba y se acortó en `bdae3b7`.
- **Torre → Fábrica**: con la Fábrica pausada, «Combatir» en 329 da el rechazo con el texto corto completo
  (`f6td_tower_refused.png`); se sale a (19,47).
- **Fallo encontrado y corregido: entrar en una sala de la Mansión borra 16410–16413.** Con
  `f6t_factory_paused.sav` (16410 = 31 y tres alquileres) la Torre no rechazaba. Medido guardando desde el menú:
  recargar en la plaza no cambia ningún work; entrar en 329, o en 213, sin hablar con nadie, pone 16410–16413 a 0 y
  no cambia ningún otro work. Es decir, desde F6 una Fábrica pausada se perdía al salir de su sala y volver. Causa
  no localizada (los scripts de 209, 213 y 329 no escriben esos works; probablemente el juego limpia por rango el
  bloque 0x4010–0x401F, que `ids.py` no puede ver). Arreglo: `WORK_IV` = 16489, `WORK_SETS` = 16485–16487,
  `factory.WORK_RNG` = 16490 (libres según `ids.py`); `rental.s` lee los alquileres por debajo de `WORK_IV`
  (hook 580 bytes). `test_no_frontier_work_in_the_block_cleared_on_entering_a_hall` vigila el bloque.
- **Con el arreglo** (`f6t_factory_paused2.sav`, SHA256 `c70f4519…`, plaza, Fábrica pausada con S922/S915/S940):
  plaza → 329 (rechazo) → plaza → 213: «Fábrica Batalla» reanuda sin sorteo; combate 1 ganado con los alquileres;
  «El próximo combate será el número 2»; Pausar. Partida `f6td_factory_paused1.sav`, SHA256
  `bc3c35e7ebd2c92c5bdad3e38af14716f568907397cb77fdd0210e55efb2448f`: zona 213, 16489 = 31, alquileres intactos,
  **16437 = 1, 16439 = 1** (racha de la Fábrica por la ruta 1), Torre 0/0, Mansión a cero, PB sin cambios.
  Salida de 213 a (20,58) (`f6td_factory_exit.png`).
- En ese intercambio el menú muestra «No cambiar» en cada fila: los conjuntos S922/S915/S940 puestos a mano no están
  en ningún nivel de alquiler y no tienen línea de texto. Con alquileres sorteados se ven los nombres (§20).

**Sin probar**: la consola; el jefe de la Mansión y los tramos por encima de la racha 19 en la Torre; reinicio sin
guardar a mitad de desafío en 329. Los textos y las reglas de equipo son los de la Mansión.

## 26. F6-DOMO: Domo v1 (2026-11-04, validación en curso)

Implementación heredada de `2326b25`: `frontier/dome.py` y `frontier/asm/dome.s`, zona 456
clonada de 517, ruta 5, works 16473/16474/16475 (victorias, activo, récord). Cuatro combates
por torneo, inscripción de tres propios y elección de dos antes de cada combate. Rival:
dos elegidos al azar entre los tres anunciados; PB de `data.FRONTIER_BP['dome']` al ganar
la final. Al reanudar se inscribe de nuevo para evitar índices obsoletos si cambió el equipo.
La racha interna cuenta combates; torneos ganados = racha / 4. Después de la final se conserva
el menú de continuar/descansar/retirarse. No hay cuadro, simulación de otros participantes,
Tucker ni modalidades Doble/Libre. Persisten los textos generales de la Mansión.

Reglas contrastadas con `pret/pokeemerald` **731ad5bf**, descargado en
`work/frontier/dome/emerald-battle_dome.h` y `emerald-battle_dome.c`:
[`include/constants/battle_dome.h`](https://github.com/pret/pokeemerald/blob/731ad5bf/include/constants/battle_dome.h)
define `DOME_ROUNDS_COUNT = 4`, rondas 0–3 y `DOME_BATTLE_PARTY_SIZE = 2`.
La tabla de PB ya estaba contrastada en `frontier/data.py` con el mismo commit.

Comprobación estática de zona: `work/frontier/dome/zone_check.txt` (sesión anterior):
456 sin warps entrantes retail; máscara 0x243; dos operandos en compartido 35 sin cambio
de mapa detrás. Los 30 literales alineados de código/CRO son un recuento orientativo,
no una prueba de ausencia de referencias calculadas. Build repetida por Codex:
`work/frontier/dome/build-codex.log`; área propia 234, máscara parcheada 0x343, ZO 15.788 bytes.
Los warps de la isla son Torre 0, Domo 1, Fábrica 2; sus salidas se calculan con `door_warp`.

Pruebas de Codex, build completa desde `2326b25`:
- `source scripts/env.sh && python -m pytest -q tests`: **288 passed** (10,10 s),
  `work/frontier/dome/tests-codex.log`. Incluye VM, Unicorn, exclusión y las rutas anteriores.
- Azahar: desde `f6dm_strong.sav` (copia de laboratorio, equipo fuerte de `lab_tower.py`),
  caminar hasta (6,57) y entrar por (6,56): sala del Domo, recepción e inscripción funcionan.
  Capturas `work/frontier/lab/dc_door2.png`, `dc_hall.png`, `dc_select1.png`, `dc_registered.png`.
- Guardado real en 456 antes del combate: `dc_registered.sav`, SHA256
  `3294aa93b5c3fe83df3c79f0e40815fa6cd4be2ac68d783ad8957cb580472fcf`;
  inscripción 0,1,2; ruta 5; racha/récord 0; activo 1; Mansión y Fábrica a cero.
- Primera ronda: vista previa Baltoy (Garra Rápida), Swinub (Antiderretir), Snubbull
  (Roca del Rey), `dc_preview_menu.png`. Se eligen los huecos **2,0** (Garchomp, Metagross;
  conservan los motes Poochyena y Torchic del fixture), `dc_pick1.png`, `dc_pick2.png`.
- Medido con GDB, sin alterar los equipos: en **0x1E3DA0**, count=2 y slots=2,0;
  en **0x1E3568**, r6=2; en **0x1E4B38**, conjuntos N108 y N79. Los works del rival
  anunciado son 108,79,83; los forzados 108,79. `work/frontier/dome/trace.gdb` y
  `gdb-teams.log`; captura del combate `dc_battle_now.png` con dos Poké Balls del rival.

Pendiente de probar: torneo completo y PB, derrotas en primera ronda y final, pausa/recarga,
cambio del equipo durante pausa, salida, exclusión en Azahar y regresión de Fábrica/Torre
con esta build; fixture de Mansión 20/20. Nada de esto se considera aceptado todavía.

**Pruebas adicionales recuperadas del corte de cuota de las 05:17**:
- Primera victoria y descanso: `dc_paused1.sav`, SHA256
  `9b741a581ac2e0cb1f4c3d83a33e5850ca1f721c534814f282dadb5972c4801b`, racha/activo/récord
  1/1/1, PB 0. `dc_round1end.png` anuncia el combate 2. En el equipo solo cambian los PS
  actuales de dos Pokémon curados (PK6 +0xF0); todos los demás bytes descifrados son idénticos
  (`work/frontier/dome/compare-round1.json`).
- Salida del Domo medida con `walk.sh`: (6,57), `dc_exit.png` y `gdb-teams.log`.
  Caminando desde allí se entra en la Fábrica con su nuevo warp 2 (`dc_factory_hall.png`).
  Elegir Fábrica Batalla rechaza el desafío porque el Domo sigue pausado (`dc_factory_refused.png`).
- Se recargó en 456 una copia de la pausa con el orden del equipo permutado 2,0,1 y el
  bloque de Mansión copiado de `main-maison-maison20`: `dc_resume_changed.sav`, SHA256
  `9340d4110694394aa4e1cdcbd22ad863ad72b6b02354f1728936764547044371`;
  generador `work/frontier/dome/resume_fixture.py`. No se editó la racha del Domo.
  La ronda 2 comenzó: GDB mide count=2, slots=0,2, racha 1, rival N109/N110 de 110,109,67;
  `dc_first2.png`, `dc_second2.png`, `dc_fight2.png`. La victoria de esa ronda **no se completó**.
- `dc_resumed_registered.sav` es una copia del guardado del laboratorio durante la
  reanudación: conserva el equipo y los works anteriores de la pausa. No demuestra por sí
  sola que se guardara la nueva inscripción; no usarla como evidencia de esa escritura.

**Reanudación y semifinal, Codex 10:36–10:44**:
- Suite tras el relevo: **296 passed**, `work/frontier/dome/tests-relevo.log` (10,42 s).
- Recargado `dc_resume_changed.sav` en 456; inscripción nueva **1,2,0** y combatientes **1,0**,
  confirmados en GDB y después en el guardado. Menú con el orden inscrito: `de_choose_first.png`.
  No hay índices obsoletos tras permutar el equipo durante la pausa.
- Rondas 2 y 3 ganadas en Azahar. Rivales medidos: N119/N75 de 75,115,119 y N95/N99 de
  85,99,95; jugador count=2 slots=1,0; `gdb-teams.log`, `de_preview2_actual.png`, `de_preview3.png`.
  `de_won2.png` y `de_won3.png` anuncian los combates 3 y 4.
- Pausa real antes de la final: `dc_paused3.sav`, SHA256
  `b86d33b81ade525f63844b3af0d1ca79d53d54b84ba89c9187c6898510cc500a`;
  racha/activo/récord = **3/1/3**, PB **0**, Mansión **20/20**, Fábrica y Torre a cero.
  El bloque completo del equipo **y** el bloque de Mansión son idénticos a los del fixture
  de reanudación (`work/frontier/dome/compare-rounds23.json`, checksums validados).

**Derrota en final y primera ronda** (Azahar, abandonar con «Huir» y confirmar; el motor
resuelve la rama `IsWin = false`, no se forzó el resultado por GDB):
- Final desde la pausa 3: `de_final_name.png`, `de_forfeit_final.png`, `de_loss_final.png`;
  `dc_loss_final.sav`, SHA256 `e2f91280f3823ff70b3eecfc4bfa7b282fe6407499d220d4d83e803cded16637`.
- Nueva inscripción tras perder, ronda 1: `de_round1_again.png`, `de_forfeit_first.png`,
  `de_loss1_done.png`; `dc_loss1_done.sav`, SHA256
  `711876fce2da6472e057d5d5897a335892639414b54a0341f930576261034554`.
- Ambas guardan **racha 0, activo 0, récord 3, PB 0**, Mansión **20/20**. Equipo completo
  y bloque de Mansión idénticos a sus respectivos guardados anteriores (`compare-loss-final.json`,
  `compare-loss1.json`). También se valida que puede iniciarse un nuevo desafío tras la derrota.
- `dc_loss1.sav` fue una captura prematura mientras el combate seguía en curso: es idéntica
  a `dc_before_loss1.sav`; la evidencia de la derrota es **dc_loss1_done.sav**.

**Final ganada, exclusión inversa y regresión de la Fábrica** (Azahar, Claude, 2026-11-04; build de
`2326b25` repetida, `work/frontier/dome/build-final.log`; capturas `work/frontier/lab/df_*`):
- Desde `dc_paused3.sav`: recepción, inscripción 0,1,2, «racha … asciende a 3», «¡Final del torneo!»
  (`df_step8.png`), vista previa Froakie/Boldore/Poliwag (`df_step10.png`), dos contra dos (en la pantalla de
  cambio solo hay dos miembros, `df_battle_d.png`) y final ganada. Las pulsaciones de A eligieron «Continuar»
  dos veces, así que la línea del campeón no se capturó; se ganaron además las rondas 1 y 2 del torneo siguiente
  («¡Segunda ronda del torneo!», `df_battle_h.png`) y se pausó tras el combate 6 (`df_b5.png`).
- `df_paused6.sav`, SHA256 `959b7fa88a9d06e03b029cac5b9e2c39fb5b91611b127d5c0e4c9d14e2ff93ff`: zona 456,
  racha/activo/récord **6/1/6**, ruta 5, **PB 0 → 1** (solo el de la final: `FRONTIER_BP['dome'][0]` = 1; los
  combates 5 y 6 no dan PB), Mansión **20/20**, Fábrica y Torre a cero.
- Salida de 456 a **(6,57)** otra vez; con el Domo pausado, la Torre (puerta (19,46) → 329) se niega con el texto
  de exclusión (`df_tower_refused.png`).
- Con la Fábrica pausada (`f6t_factory_paused2.sav`, 16489 = 31), el Domo se niega (`df_dome_refused.png`). Después,
  por la puerta de la Fábrica (warp 2) y «Fábrica Batalla»: reanuda sin sorteo; GDB en `0x1e3ddc` (rama de
  alquileres de `rental_hook`) con `r0` = 3 y `work+0x48` = 3, y en `0x1e3568` el rival de **3** (ruta 1); combate
  con el alquiler Latias (`df_factory_battle.png`). Los cambios de `rental_hook`/`rival_hook` no alteran la Fábrica.
- Suite: `python -m pytest -q tests` → 296 passed (`work/frontier/dome/tests-final.log`).

**Sin probar**: consola; la línea «¡Has ganado el torneo!» en pantalla (la rama sí: PB 1 en el guardado); el jefe
de la Mansión en la racha del Domo; reinicio sin guardar dentro de 456.

## 27. F6-PALACIO-A: Palacio etapa A (2026-11-04)

Implementación en `frontier/palace.py` sobre el flujo de la Torre, generalizado en `frontier/tower.py`
(`facility_program(retail, facility)`; el script de la Torre sale idéntico byte a byte al anterior). Zona 340 (clon de
517, área nueva 235, texto 619, lugar 279), ruta 3, works 16461/16462/16463 (racha, desafío a medias, récord), PB de
`data.FRONTIER_BP['palace']` tras cada 7.º combate. Puerta de la isla: warp 3 (`island_build.DOORS['Palace']`, último
en `FACILITIES`). El jugador da las órdenes: la mecánica propia del Palacio (la naturaleza elige) es la etapa B.

**Zona 340, comprobaciones de §18** (`python frontier/zone_check.py 340` → `work/frontier/palace/zone_check.txt`;
contexto con `work/frontier/palace/ctx.py`, `ctx2.py`): máscara 0x243, sin warps de entrada. Los cinco literales 340
no son zonas: compartido 57 `0xD10` (tabla de `@77C`, objeto y flags, como el 329); zonas 214 `0x1700`, 244 `0x198C` y
316 `0x14C8` (argumento de rutinas que empiezan con `MdlAcmdInit`, animación de modelo); zona 444 `0x23BC` (`@30`:
`FlagSet` 1740 + N, entrenador). 58 palabras alineadas = 340 en código/CRO (209: 48; 213: 45), orientativo.

**Azahar (build `python frontier/overlay.py --out work/frontier/build --romfs work/faraway/dev/overlay/romfs`,
`work/frontier/palace/build.log`; partidas en `work/frontier/lab/pa_*`, hechos en
`work/frontier/palace/save-evidence.jsonl` con `work/frontier/palace/snapshot.py`)**:
- Desde `pa_strong.sav` (plaza, equipo fuerte de `frontier/lab_tower.py`): (31,70) → puerta (31,69) → interior
  (20,31) de una sala de la Mansión (`pa_palace_hall.png`). Menú sin «Fábrica Batalla» (`pa_palace_menu.png`).
- Combatir → modalidad (Individual) → selección de 3 **propios** (`pa_party_select.png`) → guardar. La partida
  guardada (`pa_saved_340.sav`, SHA256 `1a6d7b4f…`): zona 340, ruta 3, Palacio 0/1/0.
- Combates 1 y 2 ganados a nivel 50; «El próximo combate será el número 3» (`pa_next3.png`); Pausar. Partida
  `pa_paused2.sav` (`463cb5a9…`): zona 340, ruta 3, **Palacio 2/1/2**, Torre/Fábrica/Domo 0, Mansión 0x1BBC0 a cero,
  PB 0 (sin PB en los combates 1–6).
- Salida del 340 a **(31,70)** (`pa_exit.png`). Con el Palacio pausado, «Fábrica Batalla» en 213 se niega
  (`pa_factory_refused.png`).
- Desde `pa_streak6.sav` (racha editada 6/1/6, como en la Torre): reanudación («Prosigamos…»), combate 7 ganado,
  «**Ruben ha obtenido 4 PB**» (`pa_bp4.png`, `FRONTIER_BP['palace'][0]`), «el número 8» (`pa_next8.png`); pausa
  `pa_paused7.sav` (`012e718b…`): **7/1/7, PB 4**, Mansión a cero. Equipo frente a `pa_streak6.sav`: solo cambia el
  +0xF0 del PK6 (PS actuales) de dos Pokémon.
- Reanudación («Tu racha … asciende a 7», `pa_resume_streak7.png`), combate 8 y «Huir» → abandonar. Partida de la
  derrota `pa_after_loss.sav` (`0521f47c…`): **0/0/7** (récord conservado), PB 4, Mansión a cero; la ruta queda en 3
  hasta la siguiente recepción (limitación de §15).
- Desde `pa_tower_paused.sav` (Torre 3/1/3): «Combatir» en 340 → «Tienes un desafío a medias…» y vuelve al menú
  (`pa_palace_refused.png`). La Torre, en la misma build, acepta su desafío y lee su racha 3 por la ruta 2
  (`pa_tower_resume3.png`).
- Suite: `python -m pytest -q tests` → 326 passed (`work/frontier/palace/tests-final.log`).

**Sin probar**: consola; una ronda de 7 entera empezada desde cero (las victorias 1–2 desde cero y la 7 desde la racha
editada); el jefe de la Mansión en la racha del Palacio; reinicio sin guardar en 340; el Domo rechazando con el Palacio
pausado (cubierto por la suite, `busy_check`). Textos y reglas de equipo de la Mansión.

## 28. F6-TUBO: Tubo v1 (2026-11-04)

Código inicial `23c471c`; recuperación del relevo y parche CRO `f5e6a2a`. Zona 458, clon de 517, ruta 6,
works 16477/16478/16479. Las 14 salas se representan mediante un bucle de script con menú de tres puertas y pistas,
en una sola zona (desviación del diseño de dos interiores). La sala 14 siempre es combate individual; el combate
fuerte usa rango Súper de la Mansión. Selección de tres propios mediante su pantalla; al reanudar se eligen de nuevo
 y los PS/estados se aplican por posición. PP restaurados en cada combate; sin inmunidades ni combates salvajes.

**Retorno de PS**: H1 en `code.bin` 0x1e3110 aplica los works al equipo temporal; H2 en IsWin 0x1e5664 recoge los
PS/estado de `[work+0x66c]`. La puerta de DllBattle.cro 0x15398 solo admitía competidores 0/1; el 2 (Mansión) no
copiaba el resultado. `patch.battle_cro()` admite también 2, comprobando SHA256 completo y tres instrucciones,
recalculando hashes CRO/CRR. Listado estático `work/frontier/pike/copy-back-disasm.txt`. Este cambio afecta a la
copia temporal de todas las instalaciones de la Mansión: su regresión en juego sigue pendiente.

**Azahar, Codex, build `work/frontier/pike/build-relevo.log`**:
- Carga de `pk_saved_458.sav`, modalidad Individual y selección de los tres primeros Pokémon de laboratorio.
  Pista «voces de gente» a la izquierda y tres puertas (`work/frontier/lab/pk_cx_room1.png`, `pk_cx_doors.png`);
  la izquierda da combate individual (`pk_cx_event1.png`).
- Primer combate ganado contra Shinx y otros dos; daño visible del último rival Boldore: 130/156 y luego 87/156
  (`pk_cx_last_enemy.png`, `pk_cx_win1.png`; son capturas intermedias, no los PS finales). Tras ganar se continúa
  directamente. La siguiente pista indica Pokémon a la izquierda, y da combate fuerte (`pk_cx_hard.png`).
- Segundo combate comienza contra Hydreigon, **61/156 PS**, antes de atacar (`pk_cx_h2_hp.png`). Menú de ataques
  **10/10, 10/10, 15/15, 30/30 PP** (`pk_cx_h2_pp.png`): daño conservado, PP restaurados. En esta ejecución no se
  han editado los works ni usado GDB entre los dos combates.
- Huir en el segundo combate → guardado automático `pk_cx_loss.sav`, SHA256
  `7e6bfda38efa0cd0678bee8310835806a1e830aa4f797a547f0384727c02eb5f`: Tubo **0/0/1**, PS **61/156/184**,
  estados 0/0/0, PB 0. Rachas de Fábrica, Torre, Palacio, Domo y Mansión a cero. Comparación de los seis PK6
  descifrados con la entrada: solo cambia +0xF0 (PS actuales) de los huecos 0 y 1 por la curación de la Mansión;
  todos los demás bytes idénticos (`work/frontier/pike/cx-party-comparison.json`).
- Salida andando del interior a la cabaña del Tubo (`pk_cx_exit_walk.png`); guardar:
  `pk_cx_exit.sav`, SHA256 `b80b64e18a5b259dfaaf7e3920a996d848a4bd58d2b640e6171b4e2d84e9df1a`,
  zona 209 **(5.5,70.5)**, ruta 0. Pulsar arriba entra de nuevo (`pk_cx_entered.png`); guardar:
  `pk_cx_entered_done.sav`, SHA256 `3b21f6214191a9e98aac73bf9c55ae479f4077031ef86e2d3d8b9b65ce7f726c`,
  zona **458 (20.5,31.5)**. `pk_cx_entered.sav` era una captura prematura idéntica a la de salida y no demuestra entrada.
- Hechos de las partidas en `work/frontier/pike/save-evidence.jsonl`; suite **398 passed** en
  `tests-relevo-final.log`, incluyendo 8 pruebas nuevas del CRO (puerta ARM, identidad de entrada, hashes).

**Azahar, Claude, 2026-11-04 (build `work/frontier/pike/build3.log`, mismo código que `63f4e93`; capturas
`work/frontier/lab/pk_f_*`, `pk_g_*`, `pk_pal_*`, `pk_pike_refused.png`; hechos en `save-evidence.jsonl`)**:
- **Valores de estado** (sesión anterior de Claude, build sin el CRO, works escritos con GDB antes del combate): 1 →
  «PARALIZADO», 2 → «DORMIDO», 4 → «QUEMADO» en la pantalla del equipo del combate, en el orden de la selección
  (`pk_b2_party.png`); PS 40 aplicados al primero. Es el enum de pml; 3 (congelación) y 5 (veneno) no se han visto.
- **Reanudación con daño y sala 14**: `pk_cx_lastroom_fixture.sav` (racha/activo/récord 13/1/13, PS 100/90/184,
  estados 1/4/0). «Tu racha … asciende a 13», selección de tres, guardar, «Sala 14 de 14.» y «¡Última sala de la
  ronda! Te espera un combate.» (`pk_f_room14.png`, `pk_f_last.png`). En el combate: 100/156 PARALIZADO, 90/156
  QUEMADO, 184/184 (`pk_f_party.png`). Combate ganado (dos debilitados) y **«Ruben ha obtenido 1 PB»**
  (`pk_f_w3.png`, `FRONTIER_BP['pike'][0]`); después «Sala 1 de 14.» de la ronda 2.
- **Debilitados entre combates**: el siguiente combate (sala 1, «voces de gente» → combate individual) empieza con el
  tercero (los dos debilitados no salen, `pk_g_b.png`); derrota. Partida de la derrota `pk_r14_then_loss.sav`
  (`cc9db86c…`): Tubo **0/0/14**, PS 0/0/0, **PB 1**; bloque del equipo cifrado idéntico al de la entrada (mismo
  SHA256 `12355b31…`); Mansión y demás instalaciones a cero.
- **Salida** de 458 andando: (5,70) otra vez.
- **Regresión con el CRO nuevo (Palacio)**: (31,69) → 340, selección, dos combates ganados; el segundo empieza con
  156/156 aunque el primero acabó en 46/156 (`pk_pal_b2.png`: fuera de la ruta 6 la Mansión sigue curando y los
  ganchos no actúan); «El próximo combate será el número 3» y Pausar → `pk_palace_paused_crobuild.sav`
  (`53823118…`): Palacio **2/1/2**, ruta 3, Tubo intacto (0/0/14), PB 1. Equipo descifrado frente a la partida
  anterior (`work/frontier/pike/party_diff.py`): solo +0xCA (amistad) y la suma de tres Pokémon que no combatieron
  (pasos andando).
- **Exclusión en juego**: con el Palacio pausado, «Combatir» en 458 → «Tienes un desafío a medias en otra
  instalación…» (`pk_pike_refused.png`). El sentido inverso (otras recepciones con el Tubo a medias) lo cubre la suite
  (`factory.busy_check` recorre `patch.ACTIVE_WORK`).
- Suite: `python -m pytest -q tests` → **398 passed** (`work/frontier/pike/tests-final.log`).

**Sin probar**: consola; una sala de estado y una cura total vistas en Azahar (sí la cura parcial, `pk_r2_room1_res.png`
de la sesión anterior, y la sala de PNJ; estado y curas cubiertos por la suite); congelación (3) y veneno (5) en
pantalla; la pausa del Tubo tras ganar (se probó la reanudación desde una partida con la racha editada); una ronda de
14 salas desde cero; el combate fuerte con rango Súper más allá del primer combate de Codex; Fábrica, Torre y Domo
con el CRO nuevo en el juego (el camino de combate es el mismo que el del Palacio y el Tubo). El veneno grave se
guarda como veneno normal (valor 5).

## 29. Arena Batalla: escalón A (2026-11-04)

Implementación en `e3c85ba` (`frontier/arena.py`): flujo de la Torre con equipo propio, zona **457**, ruta **4**,
works **16465/16466/16467** (racha/activo/récord), siete combates y `FRONTIER_BP['arena']`. Sin límite de turnos
ni juicio; el motor del escalón B queda pendiente. Conserva textos y selección de modalidad de la Mansión,
como el Palacio; no incorpora Greta. Zona comprobada estáticamente con `frontier/zone_check.py 457` y contexto
de los literales (`work/frontier/arena/zone_check.txt`, `ctx.txt`): las tres referencias de scripts son al objeto
457. Clon de 517, área 237; puerta (20,69), warp 4 de la isla, salida (20,70). El Palacio pasa al warp 5.

**Evidencia de Azahar recuperada del relevo de Claude**, posterior al commit de código: registro
`work/orch/logs/20261104-205236-claude-F6-ARENA-A.log`, capturas `work/frontier/lab/ar_*.png`, partidas del mismo
prefijo y `work/frontier/arena/save-evidence.jsonl`. Codex revisó capturas, comandos del registro, checksums y los
ocho SHA256 completos de las partidas; auditoría en `save-audit-relevo.json`. No son nuevas partidas jugadas por
Codex. Los estados siguientes proceden de esos guardados, no de inferencias sobre los textos:

| Prueba | Partida en `work/frontier/lab/` (SHA256 abreviado) | Resultado |
| --- | --- | --- |
| Entrada por la puerta, recepción, selección de tres propios y guardado | `ar_saved_457.sav` (`dabc9fd8…`) | Zona 457, ruta 4, Arena 0/1/0, PB 0 |
| Ronda desde cero y derrota por Huir después de ocho victorias | `ar_after_loss_run1.sav` (`55b358fc…`) | Arena 0/0/8, PB 1 |
| Salida andando y guardado en la explanada | `ar_exit_plaza.sav` (`735326f5…`) | Zona 209, coordenadas 20.5/70.5 (casilla 20,70), ruta 0 |
| Reanudación desde racha editada a 6, activo 1 | `ar_resumed_saved.sav` (`7c743650…`) | Zona 457, ruta 4, Arena 6/1/8, PB 1 |
| Victoria 7 con 1 PB, victorias 8–9 y Pausar | `ar_paused9.sav` (`093ed149…`) | Arena 9/1/9, PB 2; `ar_bp1.png` muestra el premio |
| Palacio rechaza con Arena pausada | `ar_palace_refused_in340.sav` (`f445d704…`) | Zona 340, Arena 9/1/9, Palacio 0/0/0, ruta 0 |
| Arena rechaza con Palacio pausado | `ar_arena_refused_in457.sav` (`10700392…`) | Zona 457, Arena 0/0/0, Palacio 2/1/2, ruta 0 |

La fixture `ar_streak6.sav` (`d1657561…`) se hizo a partir de `ar_exit_plaza.sav` cambiando solo los works
16465=6 y 16466=1 con `faraway/save_event.py` (el récord se conservó en 8). La primera ronda sí se jugó desde cero;
la segunda secuencia es una prueba de reanudación y premio con fixture editada. La pausa posterior en 9 fue real.
Los rechazos son visibles en `ar_palace_refused.png` y `ar_arena_refused.png`; sus zonas se fijan por los guardados.
La racha de la Mansión permanece 0/0/0/0 en los ocho guardados; Torre, Fábrica y Domo permanecen a cero.

**Equipo y regresiones**: `python work/frontier/pike/party_diff.py work/frontier/lab/pa_strong.sav
work/frontier/lab/ar_after_loss_run1.sav` da únicamente +0xF0 (PS actuales) en los dos primeros Pokémon, sin
cambios en los otros cuatro (`work/frontier/arena/party-diff-relevo.txt`). No se afirma identidad binaria del equipo:
la instalación lo cura. Durante el paseo posterior al Palacio también cambia la amistad, según el registro de Claude.
La suite completa ejecutada por Codex da **430 passed** (`tests-relevo.log`), incluyendo rutas ARM, exclusión,
PB y las instalaciones anteriores. La reconstrucción con `python frontier/overlay.py --out work/frontier/build
--romfs work/faraway/dev/overlay/romfs` reproduce los **25 archivos** de la build heredada byte por byte
(`build-relevo.log`, `build-manifest-relevo.json`).

**Límites**: consola no probada; no se repitieron combates de Fábrica, Torre ni Domo en esta sesión (persiste la
limitación del CRO del Tubo anotada en §28). La exclusión en juego se midió contra el Palacio; las demás rutas
quedan cubiertas por la suite. Textos propios de Arena, Greta y escalón B pendientes.

Intento adicional de Codex de recargar `ar_paused9.sav`: el arranque no llegó a mostrar el juego (captura negra,
`work/frontier/arena/lab-relevo.log`); **recarga de esa pausa concreta no probada**. No invalida las pruebas
anteriores de Claude de reanudación desde la fixture 6/1/8. El laboratorio se cerró y se comprobó que no quedaban
procesos en su namespace (`lab-stop-relevo.txt`); no se atribuye al juego un fallo del arranque del laboratorio.

## 30. F6-PIRAMIDE: Pirámide Batalla v1 (2026-11-05)

Diseño: `reports/diseno/piramide.md`. Código: `frontier/pyramid.py`, `frontier/asm/pyramid.s`; integración en
`island_build` (clones 140/141/142 de 517, puerta), `overlay` (scripts, caso 9777 del compartido 5, líneas 1055–1069
del texto 637) y `patch.py`/`rental.s`. Tests: `tests/test_frontier_pyramid.py` (VM y Unicorn).

**Experimento 0** (Azahar, build del banco de pruebas de Codex `frontier/pyramid_probe.py`, gdb):
- `BattleInstWorkCreate` desde el vestíbulo 140 (clon de 517, máscara de nativas de 517) devuelve el trabajo en
  `0x0880a6cc`; la pantalla de modalidad y la de equipo funcionan; `_MapChangeCore(141, 19, 0, 18, 0, 0, 0, 1, 0)`
  (firma del ayudante `0x724` del compartido 79) lleva a la zona 141.
- **El trabajo de la instalación no sobrevive a `_MapChangeCore`**: ya en 141, `+0x2c..+0x44` lee ceros, `+0x48 =
  0x0bc204e8` y la cabecera es otro objeto: memoria liberada y reutilizada. Consecuencia: la selección se guarda en
  works guardados (abajo) y cada combate de piso crea su propio trabajo.
- El clon de la cueva 192 no sirve de piso tal cual: se llega a la boca de la cueva sin poder andar y los NPC puestos
  en (16–22, 17) no se ven. La v1 usa clones de 517 también para los pisos.
- `StartBattle` desde un script que no es el de 517 (pisos 141/142, con la máscara de 517) funciona: combates
  completos, victoria y derrota (abajo). La misma zona no hace falta reentrarla: los pisos alternan 141/142.
- `BattleInstWorkDelete`: `DllField.cro` 0x956b4 → thunk 0x3738 → literal `0x001e5c48` (leído en 0x6f673c, DllField en
  0x6f3000) → `code.bin 0x1e5c48(holder)`: `ldr r4, [r0, #0x64]` (el trabajo) y `bl 0x12b8fc` en `0x1e5c54`.

**Hooks** (`frontier/asm/pyramid.s`, solo con `WORK_ROUTE` = 7):
- `pyramid_save` en `0x1e5c54` (sustituye el `bl 0x12b8fc`, al que salta al final): si la selección es del equipo
  (`+0x2c` = 0), de 3 (`+0x48`) y cada índice está en 0–5, copia `+0x30..+0x38` a los works 16681–16683 y pone
  16685 = 3. Medido con gdb: trabajo `0x8822544`, selección 0/1/2, cuenta 3.
- `pyramid_party`, desde `rental_hook` tras `dome_party`: pone los tres works como selección del trabajo nuevo.

**Flujo** (`frontier/pyramid.py`): vestíbulo 140 con la recepcionista de la derecha; pisos 141 (impares) y 142
(pares) con tres entrenadores (eventos 2–4) y un encargado (evento 5); la salida de un piso lleva al vestíbulo y la
del vestíbulo a la puerta (32,57) de la plaza (warp 3 de la isla). Works: racha de pisos 16481, piso actual 16482
(= «desafío a medias»), récord 16483, vencidos 16686, línea 16687, número 16689.

**Azahar** (build `work/frontier/pyramid/build`, partida inicial `py_start.sav` = copia de `pa_strong.sav`; partidas
en `work/frontier/lab/`, hechos en `work/frontier/pyramid/save-evidence.jsonl`, capturas `py_v1_*`):

| Prueba | Partida | Hechos |
| --- | --- | --- |
| Puerta (32,57) → vestíbulo, inscripción, guardado del desafío | `py_lobby_saved.sav` (`708bc25e…`) | zona 140, ruta 7, 16481–3 = 0/1/0, selección 0/1/2, cuenta 3 |
| Piso 1: tres combates ganados con los 3 elegidos a Nv. 50, «Ya hemos combatido», encargado → piso 2 | `py_floor2_try.sav` (`be355c35…`, guardado en 142) | zona 142, ruta 7, racha 1, piso 2, récord 1 |
| Recarga en el piso 2 y combate ganado | `py_plaza_active.sav` (`d4fb6779…`) | vencidos = 2 (bit del entrenador 1) |
| Piso 2 → vestíbulo → plaza | `py_exit_plaza.sav` (`f2237dcc…`) | zona 209, casilla **(32,58)**, desafío conservado |
| Fábrica con la Pirámide a medias | `py_v1_fac_refused.png` | «Tienes un desafío a medias en otra instalación» |
| Pirámide con la Torre a medias (16442 = 1, partida editada `py_fx_tower_busy.sav`) | `py_v1_pyr_refused.png` | mismo rechazo |
| Piso 7 con sus tres vencidos (partida editada `py_fx_floor7.sav`: piso 7, vencidos 7, racha y récord 6) | `py_f7_lobby.sav` (`d345c5df…`) | «Recibes 5 PB», PB 0 → 5, ruta 0, racha 7, piso 0, récord 7, vuelta al vestíbulo |
| Desafío nuevo con Silcoon, Shroomish, Cascoon (huecos 4, 5, 3) | `py_c_lobby_saved2.sav` (`8b5a8b76…`) | selección 4/5/3, racha 7 conservada, piso 1; en combate salen esos tres en ese orden |
| Derrota en el piso 1 | `py_after_loss.sav` (`745c8388…`) | «Has perdido…», vestíbulo, ruta 0, racha 0, piso 0, récord 7, PB 5 |

Equipo real: `party_diff.py py_start.sav py_after_loss.sav` → solo +0xF0 (PS actuales) de los miembros 0 y 1, la
cura de la Mansión ya vista en §28. Regresión: la Torre (329) con esta build hizo inscripción, guardado y al menos
cuatro combates seguidos (`py_tw_*`); no se guardó su estado final. Rechazo «No» del vestíbulo y cancelación de la
pantalla de equipo (vuelta al vestíbulo sin desafío) vistos en pantalla.

**Desviaciones y límites**: pisos con el aspecto de la Mansión (no una cueva) y el PC de la Mansión en cada piso
(cambiar el equipo entre pisos cambia quién combate: los índices son huecos del equipo; un hueco vacío no se ha
probado); cada combate cura; objetos equipados permitidos; prohibiciones de la Mansión; los entrenadores vencidos se
quedan (dicen «Ya hemos combatido»). La racha sigue tras los 7 pisos y vuelve a 0 al perder o abandonar. Sin
oscuridad, salvajes, objetos, bolsa ni Brandon (v2). Consola no probada; Fábrica, Domo, Tubo, Palacio y Arena no se
volvieron a jugar con esta build (sus tests sí, en verde).

## 31. Arena B: medidas del motor (2026-11-05, en curso)

Todavía **sin parche de etapa B**, ni juicio probado. Reproducción estática:

```bash
source scripts/env.sh
python frontier/arena_survey.py > work/frontier/arena/b-static.txt
python frontier/patch.py --out work/frontier/arena/b-measure-patch
```

El primer comando incluye SHA256 de cada entrada, listados ARM y las tablas de eventos resueltas mediante las
relocaciones internas de `frontier/cro.py`. Las direcciones del CRO siguientes son **offsets de fichero**;
las de `code.bin` son VA. Entradas: code `3999d658…`, DllField `23248ab0…`, DllBattle retail `330170f6…`.
El generador final deberá seguir leyendo el DllBattle de **v0.5** (`46153fa3…`) y conservar el cambio del Tubo
`patch.COPY_BACK` (0x15398); no se ha escrito aún ningún cambio del Palacio B.

### M1 — identificación de la Arena: cadena localizada; bit libre pendiente de confirmar

- Tabla de nativas DllField 0xf79a4 → **0x559ac**, `CallSakasaBattle` (hash FEB567AE;
  `work/frontier/natives_dllfield.txt`, TSV de CTRMap). Pasa dos bytes 7 y dos argumentos del script en la pila;
  llama al thunk 0x2c08. La importación estática en 0x2c0c apunta a **code 0x3da5cc**
  (`scripts/analyze_assets.py:CRO.static_imports`, contra `static.crs`).
- 0x3da5cc crea un trabajo de 0x290 bytes; 0x3da658 construye reglas en `work+0x248` (0x3eab6c) y 0x3da674
  llama a **0x1dbd18** con la configuración del combate en `work+0x30`. Esta última llama a 0x1d6c74 (limpia
  **0x218 bytes**) y a 0x3673bc (configura el combate). Por tanto, `CallSakasaBattle` NO demuestra por sí sola
  que haya un bit libre en +0x8c: ese byte ya es el Repartir Exp. (`ingenieria.md`).
- En StartBattle, **0x1e30b8**, el setup de la Mansión es `facility_work+0x620`, con la misma estructura.
  Un sitio al final de la construcción, antes de entregarla al motor: **0x1e33d8–0x1e33e0**. El hook del Tubo
  0x1e3110 sucede antes de que el setup esté completamente construido: no poner ahí un bit que luego se borre.
- **Azahar/GDB**, v0.5 + `work/frontier/build`, partida copiada de `ar_saved_457.sav`:
  breakpoint 0x1e30b8 → trabajo **0x08822544**; en 0x1e33d8, setup **0x08822b64**;
  `dump binary memory work/frontier/arena/b-setup.bin $arena_work+0x620 $arena_work+0x838`.
  SHA256 `423661572e743699b3833372cd0db86bfcf6e24ac02dcca52c0fe87a0a995153`.
  Primeros words = `2, 9, 0x0a0a000a, 0`; +0xa8 = 0, +0x154 = 0. Es una observación de este combate,
  **no prueba de espacio libre**. Log inicial `work/frontier/arena/b-gdb.log`.
- El word +0xa8 tiene máscaras retail (ejemplos CRO 0x6094: 0x20000, 0x14d84: 0x100000;
  0x5eaa0 es un getter de máscara variable). No se ha reservado ningún bit todavía. Pendiente revisar sus
  productores/consumidores, incluidas las demás CRO. Los listados exploratorios `b-code-a8-refs.txt` y
  `b-cro-a8-refs.txt` contienen también accesos a otros tipos de objeto: no asumir que todos son el setup.

### M2 — contador desde la entrada: localizado estáticamente; ejecución pendiente

- Movimiento 252 (Sorpresa): registro **0xde050** → fábrica **0xb707c** → tabla 0xdd0f8,
  evento 0x1f → **0xbc974**. Usa 0x51394(mon, 0), que consulta bit 0 de `mon+0x169`.
  **Ese bit NO es un contador**: 0x6c548 lo pone tras una acción; no usarlo para contar tres turnos.
- Habilidad 3 (Impulso): registro **0xdf358** → fábrica **0xc94d0** → tabla 0xdd400, evento **0x80** →
  **0xc6014**. También consulta ese bit. El evento 0x80 se despacha desde **0x1d11c**, dentro de 0x1cf44
  (final de turno, con fases y reentradas; un hook en su entrada contaría varias veces).
- **Edad en campo: u16[BattleMon+0x158]**. Se incrementa al final del turno en **0x1d1a8–0x1d1b4**,
  saturada a 9999; la rutina de entrada **0x72498–0x724cc** guarda el turno global `server+0x14` en
  `mon+0x15a` y pone `mon+0x158 = 0`. El turno global sube en **0x1d230–0x1d23c**.
  Esto permite investigar un contador por enfrentamiento sin inventar un contador global persistente.
  Pendiente medir 0→1→2→3 y la entrada del siguiente Pokémon; falta decidir cómo reiniciar el juicio si entra
  uno nuevo mientras el contrario sigue en campo.

### M3 — final de turno y debilitamiento: candidatos; Canto Mortal en laboratorio pendiente

- Rutina **0x1cf44**, fases en `server+0x108a`: estados finales de efectos 0x7f/0x80/0x81; limpieza de
  flags, incremento de la edad y del turno global en el tramo 0x1d19c–0x1d250. Hay que enganchar una fase
  que se ejecute una sola vez y deje al motor procesar los dos debilitamientos antes de decidir el resultado.
- **0x1dacc** es un manejador de KO forzado en la cola: comprueba PS, pone `u16[mon+0x10] = 0`
  en **0x1dc38**, llama al thunk 0x400 → **code 0x3b48fc**, emite mensajes 4/0x4b vía 0x71bd8 y llama a
  **0x6a068(server, mon, 0, contexto)** para tramitar el debilitamiento. No confundir poner PS=0 con completar
  el KO y enviar al siguiente Pokémon. La cola se reserva con 0x6f920/0x6f92c y se entrega con 0x6d4ec.
- Registro de movimiento 195 (Canto Mortal): **0xde420 → 0xb7f30 → 0xdcee0**, evento 0x25 → 0xc09c8.
  El otro registro ID 195, en 0xddb00 → 0xb2040, es de **otro registro**, no del movimiento: no usarlo.
  Falta vincular dinámicamente Canto Mortal con su condición y su manejador de la cola.

### M4 — cambio desde el menú: predicado localizado; bloqueo y Fantasma no probados

- **0x79458** consulta el tipo Fantasma (7) con 0x75a14 en 0x79478, antes de las trampas.
  Si es Fantasma salta a 0x796b0 y devuelve **5** (permitido). Reconoce Sombra Trampa (23/0x17) en
  0x79558 y Trampa Arena (71/0x47) en 0x79560. Devuelve 0 (habilidad), 3 (estado) o 4 (otra restricción);
  las salidas por habilidad/estado escriben identificador y habilidad en los punteros r2/r3.
- Llamadores: 0x5e4c, 0x6648 y 0xfe48 comprueban retorno == 5. Para impedir cambiar a un Fantasma,
  el hook deberá actuar **antes de 0x79478**, conservando los argumentos/salidas de la rama retail.
- GDB: con DllBattle en **0x006f3000**, 0x0076c458 tiene los words esperados de 0x79458 y el breakpoint
  llega desde **LR 0x006f8e50** (offset 0x5e50). r0 = 0x082121ac (cliente), r1 = 0x082063d0
  (Flabébé rival, id 12). Esto demuestra ejecución del predicado, **todavía no el camino del menú del jugador**.

### M5 — espacio: no hay cueva grande en el texto declarado del CRO

- Texto declarado: offset **0x180**, tamaño **0xd74a8**, fin **0xd7628**. El barrido ingenuo da huecos de hasta
  252 bytes (p. ej. 0x1a40c), pero son **tablas de saltos con relocaciones** (0x1a404 salta a esa tabla).
- Excluyendo todos los words destino de relocaciones internas, solo quedan dos tramos alineados de ≥16 bytes:
  **0x7744c (16)** y **0x7fddc (16)**. Son candidatos a pequeños trampolines, no prueba de que estén libres.
  No se afirma que la página hasta 0xd8000 pertenezca al segmento ejecutable declarado.
- `python frontier/patch.py --out work/frontier/arena/b-measure-patch`: hook actual **1272 bytes**,
  **0x579604–0x579afc**, fin disponible **0x57a000** → **1284 bytes restantes** en code.bin.
  Sigue abierta la alternativa del diseño (lógica en code.bin, llamada desde CRO). Falta medir/validar el puente
  y compartir ese espacio con Palacio B; no se ha reservado una cueva sobre sus futuras necesidades.

Pruebas del hito inicial: `python -m pytest -q tests` → **506 passed**, log
`work/frontier/arena/b-tests-measures.log`. Ningún parche de motor nuevo probado ni instalado. Pendientes M1–M4
completas, Unicorn del juicio/contador y toda la aceptación de Azahar de la etapa B.

### Continuación dinámica de M1–M4 y experimento del juicio (2026-11-05)

Log completo de medidas: `work/frontier/arena/b-gdb-dynamic.log`. Las escrituras experimentales siguientes se
hicieron en la RAM del laboratorio, no en los inputs ni en una build de entrega.

- **M2 verificada en el servidor**. Sus Pokémon NO son los objetos del cliente (los de la interfaz).
  En esta ejecución: servidor **0x082091c0**, contenedor `[server+8] = 0x081fb928`; jugador Metagross
  **0x08206a9c**, Flabébé **0x08207168**. En 0x71021c (CRO+0x1d21c), el turno global antes de subir es 1
  y las edades son **2/2**, luego turno global 2 y edades **3/3**. Tras el KO, entrada de Garchomp en
  **0x08206f24**, breakpoint **0x7654d0** (CRO+0x724d0): `u16[mon+0x158]=0`,
  `u16[mon+0x15a]=4`, `server+0x14=4`. Esto prueba el reinicio de la edad al entrar.
- **M3 verificada con Canto Mortal**. Se sustituyó en RAM el primer movimiento de Metagross por 195
  (registros original/actual `mon+0x116`/`mon+0x11c`, PP en +0x118/+0x11e). También se editó inicialmente
  la copia del cliente para mostrarlo; editar solo esa copia NO cambia la ficha del servidor.
  La condición de Canto Mortal es **0x14**, word **mon+0x6c**: se vio `0x22` en ambos, y 0 al expirar.
  `0xa8398`, caso 0x14 en 0xa8460–0xa8498, reserva un evento de cola **0x12**, pone el id en `packet+4`
  y lo entrega con 0x6d4ec. El despacho 0x1a454 (tabla de 0x1a40c, índice 0x12) lleva a **0x1a9ac → 0x1dacc**.
  NO usar 0x22: ese es otro evento.
  Watchpoint en PS del servidor: **129→0**, PC **0x003b48fc**, LR **0x00710c44**, r4 = 0x08206a9c,
  r5 = servidor. Corresponde exactamente al `bl 0x400` tras el store a cero en CRO **0x1dc38**.
  Después aparece la selección de sustituto y entra Garchomp (medida M2).
  El rival cambió Flabébé por Phantump antes de expirar Canto Mortal: **no es una prueba de KO doble**.
- **M4, menú confirmado**. Al pulsar Pokémon, breakpoint **0x76c458**, LR **0x702e4c**
  (llamada CRO **0xfe48**), r0 = cliente **0x0820d9ac**, r1 = Garchomp cliente **0x0820618c**,
  r2/r3 = salidas `0x0ffffea4`/`0x0ffffea8`. Retail devuelve 5 y abre el equipo.
  Experimento posterior: al detenerse ANTES del predicado se pusieron ambos tipos del objeto cliente (+0x100,
  +0x101) a **7**, se escribieron las salidas id=2/atributo=0 y se devolvió **3** directamente al llamador.
  Al intentar sustituirlo por Cascoon, aparece **«¡No se puede cambiar a Poochyena!»**
  (`work/frontier/arena/b-menu-denied-ghost-type.png`). Es una medida del camino de rechazo con tipos
  Fantasma sintéticos: **no sustituye la aceptación de un Fantasma real con el parche**.
  Para escribir RAM de forma fiable se usó `gdb.selected_inferior().write_memory(...)`; varios `set {tipo}`
  de GDB fallaron con «Cannot access memory at address 0x16». Los intentos fallidos constan en el log y
  no se cuentan como pruebas. Los tipos escritos se verificaron como `07 07 12` antes de forzar el retorno.
- **M1, candidato de bit**: se puso **0x80000000** en `setup+0xa8` durante este mismo combate; la entrada
  siguiente y el menú retail siguieron funcionando. Los lectores de máscara directa de este campo en el CRO
  y los callers de 0x5eaa0 examinados no usan ese bit (listados `b-cro-a8-refs.txt`, `b-rule-getter-refs.txt`).
  Se reserva como marca de Arena en REPARTO, con limpieza/puesta en el final de StartBattle. Esto es evidencia
  acotada a esta ruta y esta base: **las regresiones con la marca apagada y la comprobación de los demás
  consumidores siguen pendientes**. No usar el bit del Repartir Exp. de +0x8c.

`frontier/asm/arena.s` contiene por ahora **solo `arena_judge`**, aislado de la build: toma PS actuales/iniciales
por lado y devuelve máscara 1 (cae jugador), 2 (cae rival), 3 (ambos), 0 (snapshot ausente). Compara los porcentajes
enteros truncados, no las fracciones exactas. En Unicorn se ejecuta junto con la **división retail real**
**code 0x15ec10**, import DllBattle 0x424 (su cola está en 0x300788). Se comprueba también la conservación de
r4–r11 y de la pila. **11 casos**: victoria, derrota, empate, empate por truncado, PS cero, límites u16, curación
sobre PS iniciales y snapshot inválido. No se ha probado aún en Azahar el juicio ni está conectado a los KO.

M5, puente previsto sin cueva del CRO: sustituir cuatro instrucciones por
`ldr ip,[pc,#4]; blx ip; b resume; .word <VA code.bin>` (16 bytes). Sitios medidos:

| Offset CRO | Bytes previos (16) | Instrucciones que debe reproducir el stub |
| --- | --- | --- |
| 0x724c0 | `010c85e20010a0e3bab5c0e1b815c0e1` | `add r0,r5,#0x100; mov r1,#0; strh fp,[r0,#0x5a]; strh r1,[r0,#0x58]` |
| 0x1d21c | `0600a0e1353901eb00f020e300f020e3` | `mov r0,r6; bl 0x6b6fc; nop; nop` |
| 0x7945c | `0060a0e10180a0e10cd04de202a0a0e1` | `mov r6,r0; mov r8,r1; sub sp,#12; mov sl,r2` |

El último sitio va DESPUÉS del push retail de 0x79458 (que ya conserva el LR original): un rechazo temprano
puede restaurar ese frame y volver al llamador antes de la excepción Fantasma. Para los demás stubs, el LR
que deja `blx` permite obtener la base cargada del CRO y llamar a sus rutinas relativas. **Puente todavía no
ensamblado ni ejecutado**; comprobar destinos al interior de esos 16 bytes y relocaciones antes de escribirlos.

Suite tras el experimento: **519 passed**, `work/frontier/arena/b-tests-judge-full.log`; 45 en
`tests/test_frontier_arena.py`. Los dos tests del barrido de ceros comprueban explícitamente que se excluyan
las tablas relocadas y que se respete el fin declarado del segmento. Laboratorio parado al cerrar este hito.

### Motor integrado para laboratorio; Azahar pendiente (2026-11-05)

`frontier/arena_engine.py` define los tres puentes y genera entradas de `guarded_writes`. `patch.battle_cro`
valida el DllBattle v0.5 completo, aplica conjuntamente Tubo y Arena, y recalcula CRO/CRR una vez. Palacio B aún
no existe; puede añadir sus escrituras a esa misma lista sin descartar ninguna de estas. Los tres intervalos
están libres de relocaciones y de destinos internos de salto a sus instrucciones intermedias (test estático
sobre el CRO v0.5). No se escribe en los ceros de tablas.

`patch.py` enlaza ya `arena.s`, con los siguientes símbolos en esta revisión:

| Rutina | VA code.bin | Efecto |
| --- | --- | --- |
| arena_start | 0x579afc | Desde 0x1e33d8, limpia bit 31 y lo pone solo con ruta 4, work 16466 no cero y estilo Individual; reproduce `mov r0,r5` y vuelve a 0x1e33dc |
| arena_enter | 0x579b50 | Puente de 0x724c0: reproduce el reinicio nativo de edad y copia PS actuales del entrante al work 16693 (jugador) o 16694 (rival) si la marca está puesta |
| arena_switch | 0x579bb0 | Puente de 0x7945c, después del push retail: con marca y PS no cero devuelve 3/salidas válidas y restaura el frame original, antes de consultar Fantasma; sin marca/debilitado reproduce las cuatro instrucciones |
| arena_turn_end | 0x579bfc | Puente de 0x1d21c: exige dos activos vivos con edades ≥3; ordena los lados por id, calcula Cuerpo y pone a cero todos los perdedores antes de tramitar los KO; siempre reproduce llamada retail 0x6b6fc |
| arena_judge | 0x579d38 | Mismo juicio porcentual ya probado; ahora enlazado junto a los otros hooks |

Para cada perdedor se reserva evento 0x12 con `0x6f920(server,0x12,id)`, se escriben `packet+4=id`,
`packet+5=1` (tramitar KO aunque sus PS estén ya a cero) y se entrega mediante 0x6d4ec. **Es una implementación
por validar en Azahar**: especialmente el empate con ambos últimos Pokémon y el resultado de la instalación.
El menor de los dos contadores nativos de edad mide los turnos desde el último entrante; así la edad del
superviviente no necesita borrarse ni un tercer work. No se suman turnos en cada reentrada de la máquina de fases.

Los stubs obtienen la base del CRO a partir del LR del puente, por lo que no dependen de 0x6f3000. Los tests
los ejecutan con el CRO cargado en **0x02000000 y 0x03000000**, y con ambos órdenes de velocidad. Incluyen:
marca por ruta/activo/estilo, conservación de otros bits, reinicio de edad y snapshots con/sin marca, bloqueo con
tipo Fantasma y sustitución tras KO, victoria/derrota/empate, no juzgar en turno 2 ni con un entrante de edad 0,
KO natural, y el camino retail sin marca. En empate verifican que ambos PS sean cero ANTES de entregar el primer
evento. Verifican asimismo pila, registros y ejecución de la llamada retail desplazada.

`python -m pytest -q tests` → **560 passed**, `work/frontier/arena/b-tests-engine-full.log`.
`python frontier/overlay.py --out work/frontier/arena/b-build` → build completa; hook **1936 bytes**,
**0x579604–0x579d94**, quedan **620 bytes** hasta 0x57a000 (compartidos con Palacio B futuro).
Nada de esta build se ha probado todavía en Azahar ni en consola. La aceptación B sigue abierta.

### Aceptación en Azahar del motor B (2026-11-05, Claude, relevo de Codex)

Build `work/frontier/arena/b-build` (= `python frontier/overlay.py --out work/frontier/arena/b-build-check`,
idéntica por `diff -r`; commit bb09fa8) sobre v0.5, instalada solo en el laboratorio con
`work/frontier/arena/b-lab-start2.sh` (`FIXTURE=<partida>`). Sonda GDB: `python frontier/lab_arena_probe.py
--mode win|loss|tie|normal`; rompe en arena_start+4, arena_enter, arena_turn_end, arena_judge, 0x3b48fc (KO
desde CRO+0x1dc44) y pike_iswin. En los modos win/loss/tie fija los PS en el juicio (rival 1 / jugador 1 /
iguales) y pone Salpicadura al rival. **Corrección de la sonda**: la IA elige con la **copia del cliente** del rival,
no con la del servidor; con solo la del servidor, Houndour usó Pulso Umbrío y debilitó a Gengar en el turno 2
(sin juicio, sin KO forzado). Medido: servidor 0x8207168 / cliente **0x82063d0** (mismos words +8/+0xc;
movimientos originales 492/53/399/417), igual desfase **0xd98** que Garchomp 0x8206f24/0x820618c. La sonda
escribe ahora ambas copias si coinciden esos words y avisa si no (`ARENA WARN`). Es herramienta de laboratorio, no
forma parte del parche. Log completo: `work/frontier/arena/b2-gdb-arena.log` (a1635c48…).

Partida: `b-paused13.sav` (71e03694…) = `b-paused-fixture.sav` de Codex (Gengar/Blaziken/Garchomp con
Salpicadura/Protección/Recuperación/Gruñido) con solo 16465 = 16467 = 13 (`faraway/save_event.py`); PB 2.
Guardado de la inscripción del combate 14: `b-start14.sav` (ad9a152c…).

| Prueba | Resultado medido |
| --- | --- |
| Marca | `ARENA START flag=80000000 style=0` en los tres combates de la Arena; snapshots al entrar = PS del entrante |
| Cambio con Fantasma real | Gengar activo → Pokémon → Blaziken → Cambiar: «¡No se puede cambiar a Gengar!» (`b2-ghost-blocked.png` 5bcd1494…) |
| Juicio victoria ×3 (combate 14) | Garchomp entra con edad 0 tras KO natural de Gengar: edades [1,3]→[2,4]→[3,5], juicio `[184,184,1,108]`, KO de Houndour por 0x1dacc, entra el siguiente; igual con Fletchinder ([6,3]) y el tercero ([9,3]). `RESULT raw=1` |
| Racha y PB | «Ruben ha obtenido 1 PB» (`b2-win-bp.png` 0c500496…), «El próximo combate será el número 15» |
| Empate a mitad (combate 15) | edades [3,3], juicio `[136,136,123,123]`, KO de ambos; se pide sustituto (`b2-tie-replace.png`) y entran Blaziken y Grimer (`b2-tie-next.png`) |
| Juicio derrota | Blaziken a 1: juicio `[1,156,143,143]`, cae solo Blaziken, Grimer sigue con su edad; entra Garchomp (edad 0) |
| Empate con mi último | Garchomp/Grimer `[184,184,143,143]`: caen ambos, el rival conserva uno → derrota, `RESULT raw=0` |
| Racha tras derrota | `b2-after-loss.sav` (4000357e…): 16465 = 0, 16466 = 0, 16467 = 14, PB 3; equipo sin cambios |
| Empate de los dos últimos (combate 1 de ronda nueva) | tres juicios de empate seguidos; el último deja a ambos sin Pokémon: `RESULT raw=0` (derrota, como el empate de Esmeralda); `b2-after-lasttie.sav` (d3677c07…) 0/0/14, PB 3 |

**Con el work de la Arena a 0** (sonda normal, solo lectura, salvo donde se dice):

- **Torre** (`f6t_paused12.sav`, ruta 2, racha 12): `ARENA START flag=0`; cambio desde el menú en dos turnos
  seguidos (entradas id 0/1 a mitad de combate); edades **[3,7]** con ambos vivos sin juicio; derrota natural, después
  16441 = 0, 16443 = 12, Arena 0/0/0 y works 16693/16694 = 0 (`b2-tower-after.sav` 32d773f9…). Log `b2-gdb-tower.log`.
- **Mansión retail** (zona 517, `lab_tower.py work/frontier/lab/control_after.sav` → `b2-maison-in.sav`): `flag=0`;
  cambio Metagross→Blaziken permitido (`b2-maison-switch.png`); tras poner en RAM Salpicadura a los dos activos,
  edades **[3,5]** y **[4,6]** con ambos vivos y sin juicio. Abandonado por Huir. Log `b2-gdb-maison.log`.
- **Salvaje** (copia de `inputs/save/20261031-123645/main`, a30034d1…, Ruta 102): sin `ARENA START`
  (no pasa por StartBattle de la Mansión); `flag=0` en entrada y fin de turno; cambio Torchic→Beldum permitido
  (`b2-wild-switched.png`); edades hasta **[5,5]** con ambos vivos y sin juicio. Un segundo encuentro, huido.
  Log `b2-gdb-wild.log`.

**No probado**: combate contra un entrenador del mundo (los de la parte recorrida de la Ruta 102 ya estaban
vencidos: «Para seguir avanzando, tengo que atrapar más Pokémon»); Fábrica, Palacio, Domo, Tubo y Pirámide en juego
(solo la suite: la marca exige ruta 4); consola. Observación: tras un combate de la Arena los works 16693/16694
quedan con los últimos PS (184/143); solo se leen con la marca y se reescriben al entrar.
Suite `python -m pytest -q tests` → **560 passed** (`b2-tests.log`). Laboratorio parado y `use_gdbstub` restaurado a false.

**Cierre de regresiones con el work de la Arena a 0** (2026-11-05, Claude; misma b-build, `b-probe-normal.gdb`,
copias de partidas en `work/frontier/arena/b2-*`; herramientas `work/frontier/arena/tools/{npcs,try_npc,fac,regress}.*`):

- **Entrenador del mundo**: los cuatro entrenadores de la Ruta 102 (zona 24, NPC uid 5–8, scripts 3010/3008/3007/3301,
  posiciones leídas del fichero de entidades con `tools/npcs.py`) estaban vencidos en la partida real. El flag de vencido
  es **1740 + id del entrenador** (`shared 52`/`81`: `FlagSet(arg+1740)` antes de `_TrainerEyeRegist`). Control:
  1747, 1748, 1750 y 2041 a 1 en la partida y 1741–1746/1749/1751… a 0. Copia `b2-trainer8.sav` (9fd9d995…) = partida
  real con **solo el flag 1748 a 0** y el jugador en (160,146) (13 bytes cambiados, incluido el checksum). El Cazabichos
  reta («¡Te desafío con un Pokémon de tipo Bicho!»), combate con Wurmple Nv. 4: `setup+0xa8 = 0x10000` (bit 16 retail,
  bit 31 a 0), cambio Torchic→Beldum permitido (`b2-trainer-switched.png` 4b69f569…), edades **[3,3]…[5,5]** con
  ambos vivos y sin juicio. Log `b2-gdb-trainer.log` (9111f330…).
- **Palacio** (`pa_paused2.sav`, ruta 3): `flag=0`, cambio permitido, edades hasta [5,5] sin juicio (`b2-gdb-palace.log`).
- **Domo** (`dc_paused3.sav`, ruta 5): inscripción y combate; `flag=0`, cambio permitido; el combate se ganó por KO
  natural (`RESULT raw=1`) antes de llegar a 3 turnos con los dos vivos (`b2-gdb-dome.log`).
- **Fábrica** (`f6td_factory_paused1.sav`, sala 213, ruta 1): `flag=0` y cambio permitido; varios KO naturales. La
  pantalla fue la de selección del equipo propio: **no** se verificó que fuera el flujo de alquiler (`b2-gdb-factory.log`).
- **Tubo** (`pk_cx_lastroom_fixture.sav`, ruta 6): el gancho del Tubo sigue en marcha con el DllBattle conjunto (el primero
  entra con 100/156 PARALIZADO, el segundo QUEMADO, como §28); `flag=0`, cambio permitido (`b2-pike-switched.png`
  faafbf3d…, `b2-gdb-pike.log`).
- **Pirámide**: no se llegó a combatir (sesión parada en la plataforma del piso). Cubierta en la suite:
  `test_arena_start_marks_only_its_active_singles_setup` ahora incluye las rutas 1, 2, 3, 5, 6 y **7** con el work de la
  Arena a 1 (marca nunca puesta). Comprobado al romperlo: con `cmp ip, ip` en lugar de `cmp ip, #ARENA_ROUTE` fallan 7
  casos; restaurado, pasan.

Suite `python -m pytest -q tests` → **566 passed** (`work/frontier/arena/b3-tests.log`). Laboratorio parado, sin procesos,
`use_gdbstub=false`; partida original intacta (a30034d1…). Consola no probada.
