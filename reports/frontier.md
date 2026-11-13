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


## 32. F6-PALACIO-B: relevo y parada en M3 (2026-11-05)

**Estado: bloqueado por la condición de parada de la tarea; etapa A conservada.** El relevo encontró código B
sin commit tras `18a464f`. Los experimentos de Claude estaban en `work/frontier/palace/`, pero no constaban en
este informe ni en la bitácora. Codex revisó los registros y el último commit. No se declara B terminada ni se
ha establecido que toda solución con IA sea imposible: falló la conversión directa del cliente y existe un
ensayo híbrido prometedor. La instrucción de F6-PALACIO-B pide consultar al usuario si M3 se cuelga; se deja esa
decisión explícita antes de integrar otra vía.

### M1 — setup Individual medido; Multi pendiente

Fuente heredada: `work/frontier/palace/b1-gdb-m1-m3a.log`, SHA256
`c82b21a09b89917fd8d416018d8e340061ac3cf1f915e5babe0f3dcd8b6f25e3`.
Sonda conservada en `frontier/probes/palace/m1.gdb` (breakpoints 0x1e32ac/0x1e3244, instrucciones siguientes
al volcado propuesto en el diseño). En Individual: `r4=0x8822544`, setup = work+0x620 = **0x8822b64**;
work+0x839=0, work+0xae1=0, setup+0x49=0; +0x4c=0x880b36c, +0x50=0x880bf10, +0x54/+0x58=0,
+0x6c=0, +0x70=0x880cab4, +0x74=0. El entrenador de +0x70 tiene +0xc=7.
Volcado local: `b1-setup-single.bin`. **No hay hit Multi en el registro: M1 Multi no probado.**

### M2 — creación de clientes localizada; rwatch del diseño incompleto

Mismo registro. Base cargada de DllBattle **0x6f3000**. Cliente 0 **0x820d9ac**, cliente 1 **0x82121ac**;
byte +0x90 = identificador, +0x91 = tipo (0 interfaz, 1 IA). Puntero al objeto IA en +0x1c8:
0 para el cliente 0; 0x8215d78 para el 1 (flags 7 en objeto IA+0xc). Constructor CRO+0x72f40;
escritura del tipo en **CRO+0x73064 = 0x766064**; asignación del objeto IA observada en
**CRO+0x73304 = 0x766304**. Se usó watchpoint de escritura sobre cliente0+0x3c=0x820d9e8
para armar breakpoints después de cargar el CRO (la recarga sobrescribe los breakpoints anteriores).
Los rwatch sobre setup+0x6c/+0x70 que figuran en el registro no dieron una cadena completa de consumidores.
**Los rwatch pedidos sobre +0x74/+0x49 y la creación del compañero Multi no están probados.**

### M3 — conversión directa fallida; ensayo híbrido separado

**Directa**, fuente `b1-gdb-m1-m3a.log`, sonda `frontier/probes/palace/m3-direct.gdb`:
se fuerza `$r6=1` para el cliente 0 en 0x766064; aparece objeto IA 0x8211578, flags **0**;
cliente 1 conserva tipo 1 y flags 7. Después no llega una decisión de combate y la captura
`b1-m3a-black.png` muestra ambas pantallas negras (SHA256
`70365222c781532e35d42726d79c5ac9614bb4e906deb6112ffe0161e38013ed`). El registro del orquestador
`work/orch/logs/20261105-123811-claude-F6-PALACIO-B.log` conserva la espera de 20 s previa a esa captura.
Al interrumpir: PC **0x15eb5c**, LR **0x160168**. No hubo resultado IsWin medido.
**Límite:** no se repitió la conversión directa con flags 7; este fallo no demuestra por sí solo la imposibilidad
de todas las variantes de cliente 0 con IA. No se afirma tampoco un deadlock interno diagnosticado.

**Híbrida, investigación de Claude posterior al fallo directo**, fuente `b2-gdb-m3b.log`, SHA256
`989b94d7dec5cc1796f4b485af38fe3ba1d71489bbc30503ce2bfd9066fb62c4`;
sonda `frontier/probes/palace/m3-hybrid.gdb`:
- Mantiene tipo 0 para la interfaz, fuerza la creación del objeto IA y flags 7; cambia en RAM solo la columna
  de despacho de los comandos **3, 5 y 6** a 1. Los mensajes/animaciones conservan columna 0.
- Constructor: CRO+0x731f4; flags: +0x732c0; despacho: +0x49f0. Tabla de comandos en **CRO+0xdbc68**,
  filas de 0x1c bytes con tres pares procedimiento/ajuste. El comando 7 tiene procedimiento de interfaz
  +0x10e40 y puntero IA nulo (lectura estática del CRO, no una traza de ese comando).
- El registro muestra acciones `cmd=3 col=1`, selecciones `cmd=5 col=1` y entradas propias id=0 e id=1;
  en el segundo combate se puso a 1 el PS del primer Pokémon y su copia cliente (mon−0xd98) como fixture RAM.
  Capturas heredadas de victoria y sustitución: `b2-m3b-win.png`, `b2-m3b-win2.png`,
  `b2-m3b-autoswitch.png` (esta última SHA256
  `16c4dd9669594b516ec3d12ffdfb8717a01bb39b22e3379e0b9da700da51fa2d`).
- Esto es evidencia de viabilidad de **decisiones** mediante IA con la interfaz conservada; no aceptación de una
  build ni prueba de IsWin/racha/PB. El segundo despachador CRO+0x7668 fue instrumentado sin hits en esas trazas.

Codex no repitió estos combates: arrancó el laboratorio para revisar el estado, cargó una sonda, permaneció en
la plaza y lo paró al aplicar la condición de parada. `b4-start-only.log` no contiene un combate ni añade medidas
M1–M3. No se atribuyen las observaciones heredadas a una ejecución nueva.

### M4 — espacio: cálculo estático; medida GDB pendiente

`source scripts/env.sh; python` importando `frontier/patch.py` y ejecutando `patch.assemble()` sobre el código
restaurado: cueva **0x579604–0x57a000**, 2556 bytes; gancho actual 1936 bytes, fin 0x579d94, **620 libres**.
La build experimental heredada `b3-build.log` usa 2208 bytes (**348 libres**). Sus puentes de 16 bytes saltan del
CRO a code.bin; no ocupa tablas nulas del CRO. Sitios propuestos: CRO+0x731f0, +0x73258, +0x49ec.
**M4 mediante GDB y auditoría completa de consumidores del bit 30: no probadas.** El bit 30 propuesto no se
reserva ni se instala al dejar B bloqueada. El bit 31 de la Arena no cambia.

### Relevo, recuperación y pruebas

Cambios heredados: `asm/arena.s` encadenaba `palace_start`; `patch.py` enlazaba el nuevo ensamblador y los tres
puentes CRO; `palace.py` ocultaba Guardar vídeo; `tests/test_frontier_palace.py` añadía Unicorn. Faltaba ampliar
el test del Tubo que acota los intervalos cambiados del CRO. Corregido ese test de forma temporal, Codex ejecutó
la suite: **633 passed** (`work/frontier/palace/b4-tests.log`). No equivale a validación en Azahar.

Para respetar la parada sin perder el trabajo, se archivó todo el código B más esa corrección en
**`reports/diseno/palacio-b-experimental.patch`**, basado en `18a464f`, SHA256
`505e054ca90d64adeea779f86fdb29233d82389d375fd9ecdb84fd01ac53cd32`.
Es texto fuente, incluye dos ficheros nuevos; **no lo aplica el generador**. Una futura sesión autorizada puede
revisarlo con `git apply --stat` y comprobarlo con `git apply --check` antes de aplicarlo. Las referencias a §32
dentro del parche describen la intención experimental, no aceptación final.

Se restauraron explícitamente desde HEAD solo los cinco ficheros seguidos de implementación/tests del cambio
B y se retiraron los dos módulos nuevos tras archivarlos. Sin stash ni reset. `tasks.json` se actualiza a blocked.
El generador queda como `18a464f`: v0.5 + Tubo + Arena; hash de entrada v0.5 DllBattle.cro exigido por
`patch.py`: `46153fa373b8166a3a65a31272008dc8d63207f3b2498752c69c1a0c74235519`.
Suite restaurada: **566 passed** (`b4-restored-tests.log`). Laboratorio parado en su mismo namespace;
`use_gdbstub=false`, sin AppRun/Xvfb/GDB en la comprobación tras la parada; sin tocar inputs ni la partida original.
Quedaron sin seguir y sin modificar los informes y scripts de evoluciones/encuentros que ya estaban al llegar.
No se modificó REPARTO ni se hizo push.

**Decisión pendiente:** ¿retomar B con la vía híbrida de decisiones IA manteniendo la interfaz (requiere completar
M1–M4 y toda la aceptación de juego), o elegir la alternativa **2**, ficha de movimientos recortada por naturaleza
con pulsación manual, o la **3**, experimento Multi con equipo en el compañero IA y un Pokémon debilitado en
cliente 0 (cambia el formato a 2 contra 2)? La etapa A sigue utilizable mientras se decide. La naturaleza es C.

## 33. F6-PALACIO-B por la vía híbrida (2026-11-10)

Decisión del usuario del 2026-11-10 (REPARTO): vía híbrida de §32. Tarea de frontier-orch, dueño Claude.

### Código integrado

`reports/diseno/palacio-b-experimental.patch` (base 18a464f) se revisó y se aplicó tal cual sobre 7846388
(`git apply --check` correcto; ningún cambio en los ficheros que toca desde 18a464f):
- `frontier/asm/palace.s`: `palace_start` (encadenado al final de `arena_start`, code.bin 0x1e33d8): limpia el bit 30
  de `setup+0xa8` (`work+0x6c8`) y lo pone solo con estilo Individual (`work+0x621` = 0), `WORK_ROUTE` = 3 y work 16462
  ≠ 0. Tres puentes del CRO, del mismo molde que los de la Arena (`ldr ip,[pc,#4]; blx ip; b +0; .word`):
  CRO+0x731f0 `palace_ai_want` (el cliente 0 de interfaz pide objeto IA si el bit está puesto), +0x73258
  `palace_ai_flags` (flags 7 para ese objeto) y +0x49ec `palace_dispatch` (columna 1 solo para los comandos 3/5/6 del
  cliente 0 con el bit; el resto, columna retail).
- `frontier/palace_engine.py`: sitios con sus 16 bytes previos para `guarded_writes`, compuestos con el Tubo y la Arena
  en `patch.battle_cro` encima del DllBattle.cro de la v0.5 (hash exigido 46153fa3…) y un solo rehash CRO/CRR.
- `frontier/palace.py`: el menú «siguiente combate» del Palacio salta siempre «Guardar vídeo» (línea 68); la Torre lo
  conserva (test).
- Tests Unicorn de la marca en todas las rutas, exclusión con la Arena, los tres puentes a dos bases del CRO, la tabla
  de comandos medida y la ausencia de relocaciones/destinos de salto dentro de los sitios.

### Auditoría del bit 30

`python -I frontier/probes/palace/audit_a8.py baseline/oras/repolished/exefs/code.bin
dist/held-exp-share-v0.5/mods/000400000011C400/romfs` → `work/frontier/palace/c/audit-a8.txt`, y la misma
clasificación sobre code.bin y las 145 CRO de Repolished (+ las dos de la v0.5), `audit_a8_all.py` → `c/audit-a8-all.txt`:
- **Ningún** `ldr` de `+0xa8` (ni `ldrb +0xab`/`ldrh +0xaa`) seguido de `tst/and/bic` con una máscara que incluya
  0x40000000, en code.bin ni en ninguna CRO.
- DllBattle: 27 lecturas de `+0xa8`; 16 con máscara sin el bit 30; las «enteras» son punteros a función de otros
  objetos (`blx`, 0x34368, 0x8be80, 0x8f4d4, 0xab4c4) o copias de un global por `pc` (0x30998, 0x309d4), no del setup;
  0x130a8 y 0x644bc pasan `+0xa8` de otros objetos como argumento. El getter de máscara variable 0x5eaa0 se llama con
  0x100000, 0x80000, 0x40000 y 0x40; su envoltorio 0xd25a8 (máscara del llamador) no tiene llamadas directas: si lo usa
  una tabla de funciones, no está auditado.
- En code.bin solo hay una lectura de `work+0x6c8` fuera del gancho (máscara sin el bit 30). Las lecturas de
  `setup+0xa8` por puntero al setup en code.bin (`+0xa8`) tampoco tienen máscara con el bit 30; los usos de palabra
  entera (p. ej. `cmp #0`) los vería igual el bit 31 de la Arena, ya probado en regresiones (§31).
- Límite: lectura estática a 8 instrucciones; copias del word a otras estructuras no se siguen.

### M4: espacio

`patch.assemble()` sobre el código integrado: gancho **2208 bytes**, 0x579604–0x579ea4, **348 libres** hasta
0x57a000 (antes 1936/620). `palace_start` 0x579d90, `palace_ai_want` 0x579de4, `palace_ai_flags` 0x579e2c,
`palace_dispatch` 0x579e60. Los puentes del CRO no usan espacio del CRO (sustituyen 16 bytes cada uno).
Build: `python frontier/overlay.py --out work/frontier/palace/c-build` (`c-build.log`), **idéntica** (`diff -r`) a la
build experimental `b3-build` de §32; code.ips 330cf5e6…, DllBattle.cro a9b91f85….
Suite: `python -m pytest -q tests` → 633 passed.

### Azahar con la build (2026-11-10, sesión 1)

Laboratorio con GDB y sonda **pasiva** `work/frontier/palace/c-probe2.gdb` (solo registra; la única escritura es el
fixture de PS = 1 indicado abajo). Registro `work/faraway/gdb/out.log` copiado a `work/frontier/palace/c/gdb-s1.log`.

**Fallo del parche experimental, corregido.** Con `c-build` (= `b3-build`) el combate llegó al menú de acción del
jugador: el despacho nunca desviaba. En CRO+0x49ec `r1` **no es el comando**: 0x49d4..0x49e8 dejan en él
`byte1 != 0` de la fila; el comando es el **byte 0** de la fila (0x49c0 `ldrb r3,[r2,r0*28]`; la palabra 0x101 de la
fila 0 = comando 1 con el byte 1 puesto). `palace_dispatch` lee ahora `ldrb [fila]`. El test Unicorn se reescribió con
la fila en memoria y `r1` en 0/1/3 (indiferente). Gancho 2212 bytes, **344 libres**. Las trazas GDB de §32 no tenían
este fallo porque su sonda leía la fila.

**Ronda completa (`c-build2`, desde `c1-door.sav` = `pa_strong.sav` delante de la puerta, 5db91b68…):** puerta →
340 → Combatir → Individual → Metagross/Blaziken/Garchomp → guardado → 7 combates **ganados** (`PALACE RESULT raw=1`
×7). En cada combate `PALACE START … a8=40000000 palace=1 arena=0 style=0`; objeto IA del cliente 0 con flags 7;
`cmd=3 col=1` (acción) y `cmd=5 col=1` (sustituto) para el cliente 0; el resto de comandos por la columna 0. En el
combate 3 la sonda dejó a 1 PS al primer Pokémon (fixture de RAM): cayó y el cliente 0 eligió sustituto por la IA
sin pulsación (`PALACE ENTER lab: hp=1 on id=0` → `cmd=5 col=1` → `ENTER id=1`). Menú entre combates: solo
Continuar/Pausar (`c/c2-menu-novideo.png`). Combate 8 con los tres a 1 PS: `RESULT raw=0` (derrota).
Partida tras la derrota `c2-after-loss.sav` (aecf494e…): **Palacio 0/0/7**, **PB 4** = `FRONTIER_BP['palace'][0]`,
Mansión 0x1BBC0 a cero, Torre/Fábrica a 0, ruta 3 (limitación de §15).

**Pulsaciones.** El conductor `work/frontier/palace/drive.sh` solo pulsa A fuera del combate o cuando el cliente 0
ejecuta el proc de interfaz del comando 1 (CRO+0x73ec, presentación) o del 12 (CRO+0x10bec, fin); cada pulsación
queda en `c/presses.log`/`presses3.log` con su motivo. **Ninguna pulsación durante decisiones ni cambios.** Pero
los dos textos del entrenador **esperan A como en retail**: «¡… te desafía!» y su frase de derrota. Medido en la
presentación: vista = cliente0+0xc8, secuencia 0 (tabla CRO 0xe0fd0; la 1 se usa si el byte 0 del setup es 4) en
el estado 20, callback 0x48010 en el subestado 2, que espera `[[vista+0x444]+0xc]+8 == 0`; esa cola contiene una
línea de tiempo (nodo con fotograma 0x2a de 0x7e) **congelada** por su dueño (gestor `vista+0x444`, vtable CRO
0xe5168, `+0x14` = 0) hasta pulsar A; al pulsar, code.bin 0x3c4ff0 la retira. Sin probar: dónde se lee la tecla.
Por eso el criterio «sin ninguna pulsación» **no se cumple** en esos dos textos.

**Vídeo tras la derrota.** Con `c-build2` el flujo retail ofreció guardar el vídeo tras perder y A lo guardó
(«Se ha guardado el Vídeo de Combate», `c/c2-loss-1.png`). `palace.hide_record` deja `L3fdc` (SaveBattleRecord +
espera; llamadas en 0x21d0, 0x2250 y 0x25dc) en `PROC; ZERO_PRI; RETN` solo en el programa del Palacio; test.
`c-build3`: solo cambia `a/0/1/3` respecto a `c-build2`; code.ips 10e9eece…, DllBattle.cro a9b91f85….

**Reanudación y pausa (`c-build3`, desde `c3-resume-in.sav` = `b1-in.sav`, 2/1/2 en 340):** «Tu racha … asciende a
2», selección, combates 3 y 4 ganados con la IA (sin pulsaciones salvo los textos), Pausar → `c3-paused4.sav`
(aebef83e…): **4/1/4, PB 0**, Mansión a cero, bloque de equipo idéntico al de entrada (12355b31…).
Sin pantallas negras ni cuelgues en 12 combates. Suite: `python -m pytest -q tests` → 696 passed.

### Regresiones con control manual (`c-build3`, 2026-11-10)

Mismo laboratorio y sonda; partidas copiadas de las regresiones de la Arena B (§31). Registros en
`work/frontier/palace/c/gdb-{arena,factory,maison,world}.log`; el de la Torre no se guardó (se sobrescribió al
reiniciar), su resultado consta de la salida de consola de esta sesión.
- **Torre** (`b2-tower-in.sav`, 12/1): `START a8=0 palace=0`; menú de movimientos manual (`c/r-tower-menu.png`);
  cliente 0 con `cmd=3/5 col=0` (5 y 2); victoria `RESULT raw=1`.
- **Arena** (`lab_arena.py` sobre `b-paused13.sav` → `c/r-arena-in.sav`): `START a8=80000000 palace=0 arena=1`;
  Gengar cayó ante Magcargo y el reemplazo fue **manual** (lista de equipo); con la sonda `win` de
  `lab_arena_probe.py` (rival con Salpicadura) edades [3,6] → `arena_judge` (args 156/156/1/115) → victoria por juicio
  (`ARENA RESULT raw=1`). 12 decisiones del cliente 0 por la columna 0, ninguna por la IA.
- **Fábrica** (`b2-fac-factory-in.sav`, sala 213, desafío a medias): `START a8=0 palace=0`; combate con **alquileres**
  (Latias); 4 decisiones manuales y reemplazo manual tras el KO (`c/r-fac-manual-switch.png`). No se terminó.
- **Mansión** (`b2-maison-in.sav`, 517): `START a8=0 palace=0`; 3 decisiones manuales, victoria.
- **Entrenador del mundo** (`b2-trainer8.sav`, Ruta 102, Cazabichos): ese camino no pasa por 0x1e33dc (ni la Arena ni
  el Palacio ponen marca); `setup+0xa8 = 0x10000` (bit 30 a 0), sin objeto IA para el cliente 0 (solo `AIFLAGS
  client=1`), `cmd=3 col=0`, menú manual (`c/r-world-menu.png`).
- Sin cuelgues ni pantallas negras. Exclusión mutua: sin cambios de script respecto a la etapa A (probada en §27) y
  cubierta por la suite; no se repitió en Azahar. Domo, Tubo y Pirámide: no jugados (sin cambios en sus caminos; la
  marca solo se pone con ruta 3).
- Laboratorio parado (sin AppRun/Xvfb/GDB, sin session.json), `use_gdbstub=false` restaurado.

### Pendiente: textos del entrenador

Criterio no cumplido: «sin ninguna pulsación durante los combates». Decisiones y cambios no piden nada, pero la
presentación («¡… te desafía!») y la frase de derrota del entrenador esperan A, como en retail. Pistas (estáticas):
en la vista, tras esperar, el código llama a la importación CRO 0x1018 sobre `[[vista+0x1a0]]+0xcc` (¿impresión
terminada?) y luego `0x5ca94(vista+0x1a0)`, pone `gestor(vista+0x444)+0x14` y avanza el estado (0x43c5c, 0x48a50,
0x5e3cc). Las impresiones de la vista pasan `r2 = 1` a 0x5c314/0x5c730 (¿espera de tecla?). Sin probar.
Opciones: (a) aceptar esas dos pulsaciones de texto (comportamiento retail); (b) investigar el modo automático de
la ventana de texto y activarlo solo con el bit 30 (riesgo: toca la interfaz de todos los combates por el puente).

## 33.1. F7-VIDEO: sin vídeos en las siete instalaciones (2026-11-11)

Decisión del usuario: quitar los vídeos de todo el Frente, conservando la Mansión original.
Se extraen `palace.hide_video` / `hide_record` de §33 a `frontier/battle_video.py`, conservando las
comprobaciones de las instrucciones de entrada. El menú `L3b90` salta la entrada 68 («Guardar vídeo»)
y mantiene 67/valor 0 (Continuar) y 69/valor 2 (Pausar). La rutina `L3fdc` devuelve 0 sin llamar a
`SaveBattleRecord` ni a su espera `L4`; sus tres llamadas retail (0x21d0, 0x2250, 0x25dc) se conservan.

- Torre, Palacio, Arena y Tubo aplican la supresión en `tower.facility_program`; Domo en su propio
  constructor; Pirámide en vestíbulo y pisos (también cubre las rutinas retail heredadas sin uso actual).
- Fábrica: `factory.reception` la aplica **solo con WORK_ROUTE = 1**. Comparar WORK_IV no serviría tras
  la derrota: el script lo limpia antes del diálogo de vídeo. La ruta sigue activa hasta regresar de
  `CHALLENGE`. Con ruta 0, el desafío de la Mansión conserva el menú y la grabación originales, incluso
  en la zona 517 que comparte script con la Fábrica. No se alteran textos ni valores de las otras opciones.
- Palacio: conserva los alias públicos anteriores. Comparación con sus constructores de `0497f9c`:
  script **idéntico byte a byte, 15016 bytes** (`work/frontier/video/palace-byte-check.txt`).

Prueba principal: `tests/test_frontier_video.py`, un caso parametrizado por instalación (más los pisos
  de Pirámide), ejecuta el script generado en `pawn_vm`: ambos valores del argumento que condicionaba
  el vídeo, menú exacto Continuar/Pausar, rutina de grabación que retorna sin applet/espera y tres sitios
  de llamada conservados. Otro caso compara el menú y la grabación de la Mansión original con retail.
  Los tests anteriores del Palacio se actualizan para que la Torre también suprima el vídeo.

Verificación en `work/frontier/video/`:
- Suite: `env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests'` → **1105 passed,
  1 skipped**, 39.86 s (`tests-clean-env.log`); tests de vídeo → **9 passed** (`script-tests.log`).
  La primera suite, con ORCH_LANE heredado, dio 9 fallos exclusivamente en `test_frontier_orch.py`
  (`tests.log`); se repitió sin esa variable, como en las aceptaciones anteriores del carril.
- Build: `python frontier/overlay.py --out work/frontier/video/build` (`build.log`), ZO 517 **15892**;
  SHA256 del archivo a/0/1/3: `ce68b2700418e41cd5ec4f8c13f6d9acdbfb5e7a42c763d8464f43cd7eec4120`.
- Azahar, esa build sobre v0.5: Fábrica desde `f6td_factory_paused1.sav` (hash en `hashes.txt`),
  alquileres, victoria `raw=1` con ruta 1 → próximo combate 3, solo Continuar/Pausar
  (`factory-win-menu.png`, `factory.gdb.log`). Pausar llega a su confirmación (`factory-pause.png`).
  Sonda `frontier/probes/pyramid/lab_probe.py`, `pv_mode='win'`: rivales a 1 PS/Salpicadura en sus copias
  cliente/servidor; se elige Pulso Dragón de Latias después de Paz Mental. Sin escribir resultado ni racha.
- Arena desde `lab_arena.py ar_paused9.sav arena.sav` (fixture y hash en `arena-fixture.txt`): marca
  **0x80000000**, tres juicios de tres turnos y victoria `ARENA RESULT raw=1` → próximo combate 11,
  solo Continuar/Pausar (`arena-win-menu.png`, `arena.gdb.log`); confirmación de pausa (`arena-pause.png`).
  Sonda `lab_arena_probe.py --mode win`: rivales con Salpicadura y PS controlados al juicio, sin escribir
  resultado, works ni PB. Son pruebas de flujo asistidas, no de dificultad.
- Política aplicada: solo las dos instalaciones solicitadas. No cambian motor, ASM, patch.py,
  overlay.py ni island_build.py (`scope-check.txt`); no se repite el circuito de paquete ni historia.
  Las derrotas y finales quedan cubiertos por scripts; no repetidos en Azahar. Consola no probada.
- Laboratorio del carril, puerto **24691**, detenido con `scripts/azahar_lab.py reap` desde la misma shell
  persistente que lo arrancó (necesaria para compartir namespace de procesos); GDB desactivado y
  `own_processes=[]` (`lab-cleanup.txt`). No se toca el laboratorio del otro carril.

## 34. F6-PIRAMIDE-V2A: pisos de cueva sin PC (2026-11-10)

Medida previa, con `source scripts/env.sh; python` → `patch.assemble()` sobre ffec981:
cueva compartida **0x579604–0x57a000**, capacidad 2556 bytes, gancho **2212 bytes**, fin **0x579ea8**,
**344 libres** (el Palacio B corregido ocupa cuatro bytes más que la medida anterior de §33).
Esta tarea no añade código nativo ni cambia el gancho.

Donante elegido: **77, Ruinas Desierto**, uno de diseño §3. Sondeo reproducible con
`faraway/run.sh Probe work/frontier/pyramid/build-island/game work/frontier/pyramid/v2/survey-ws entities 77 192 195 199`
y modo `floor 77`: `work/frontier/pyramid/v2/{entities,floor77,floor192}.txt`.
Primera sala: suelo a altura 0, x=5–19, y=5–17; salida sur (12,18). La segunda cámara del donante permanece
como geometría, sin NPC y sin acceso interior (sus tres warps van al vestíbulo). No hay props en el donante.

`frontier/pyramid.py`: llegada (12,0,16), entrenadores (8,10), (12,10), (16,10), encargado (12,6).
`island_build.CLONES`: 141/142 ← 77, vestíbulo 140 ← 517. `NATIVE_DONORS` conserva 517 en los pisos.
El plan elimina NPC y disparadores retail, redirige los tres warps a 140/0 y copia las cuatro entradas de modelos
completas del área 214 (cabecera de 517 +2). `text.<zona>=619` conserva los textos de los ayudantes del script 517
independientemente del donante visual. Los entrenadores siguen visibles, pero el bit de vencido 16686 impide
combatir otra vez; es la alternativa admitida por la aceptación. Sin flags o works nuevos.

Build: `python frontier/overlay.py --out work/frontier/pyramid/v2/build`, log `v2/build-final.log`.
Cada piso: **ZO 16504** (cabecera 56, entidades 456, script 15952, otros 0/12), límite **17248**.
Carga por piso **566272 bytes** = mundo 56064 + props 24320 + modelos 485888; menor que **LOAD_BUDGET 2724608**.
El generador comprueba la carga antes de empaquetar y `pyramid.check_floor` valida ZO completo, ausencia de props y
disparadores, tres salidas al vestíbulo, texto y round-trip del script. Prueba de exceso de ZO y salida retail negativa.
Suite `python -m pytest -q tests`: **697 passed**, `work/frontier/pyramid/v2/tests-m1.log`.

Azahar, primer hito de laboratorio (build de ddd8428):
- `v2/floor1.png`: cueva, tres entrenadores y encargado, sin PC. Movimiento y tres combates del primer piso.
- `v2/beaten-return2.png`: después de salir al vestíbulo y reanudar, el entrenador 0 dice «Ya hemos combatido»;
  no hay otro StartBattle. Partida guardada por interfaz `v2/floor1-beaten0.sav`, SHA-256
  `9c58778b760f383a5c8b8bfe781f96725655d65c5b1ad7518ea27b613f733c7c`.
- Reinicio completo desde esa partida: `v2/climb.log` / `work/faraway/gdb/out.log`, primer Start del entrenador 1
  con ruta 7, piso 1, vencidos 1; conserva el vencido tras cargar. Primer cambio de piso: racha/piso/récord
  1/2/1, vencidos 0. Ronda completa, derrota y regresiones todavía en curso.
- Sonda reproducible `frontier/probes/pyramid`: modo `win` baja a 1 los PS del rival y le da Salpicadura en RAM;
  resultados, works, racha y PB no se escriben. Victoria asistida, no una prueba de dificultad del equipo.
- Suite repetida tras las herramientas de laboratorio: `v2/tests-final.log`, **697 passed**.

PS persistentes, objetos y salvajes siguen fuera de esta tarea.
Para actualizar una partida v1 guardada físicamente en un piso de la Mansión, salir primero al vestíbulo con v1:
las coordenadas de ese piso guardado no corresponden a la nueva cueva. La reanudación desde el vestíbulo conserva
piso y vencidos y usa las coordenadas nuevas. Recarga de guardados nuevos en cueva: llegada y bit de vencido comprobados como arriba.


### Recorrido de siete pisos, recompensa y derrota (Azahar)

Build ddd8428, sondas de 61d0910, un solo laboratorio. `gdb-before-reload.log` contiene la primera victoria;
`gdb-round.log` las otras veinte. `python frontier/probes/pyramid/audit_round.py` verifica **21 victorias**, tres
por piso 1–7, máscaras previas 0/1/3 y siete transiciones. `climb.log`, capturas `after-floor1.png`…`after-floor7.png`:
racha/piso/récord tras cada escalera 1/2/1, 2/3/2, 3/4/3, 4/5/4, 5/6/5, 6/7/6, **7/0/7**, ruta final 0.
El conductor terminó con error de shell `/null` tras imprimir el último estado (se editó su archivo mientras seguía
leyéndolo); no fue error del juego. Se reanudó GDB. Una A sobrante abrió otra conversación al llegar al vestíbulo:
el intento `v2-round7` no guardó y su snapshot es inválido como evidencia final; conserva el guardado anterior.
`climb.sh` usa ahora tres A ante el encargado y `save.sh` rechaza el archivo sin cambios; no editar conductores vivos.

Medida adicional de la recompensa, **fixture de frontera editada**, no otro recorrido jugado:
`save_event.py floor1-beaten0.sav --sha256 9c58778b760f383a5c8b8bfe781f96725655d65c5b1ad7518ea27b613f733c7c
--output work/frontier/pyramid/v2/top-boundary.sav --work 16481=6 --work 16482=7 --work 16483=6 --work 16686=7`.
Conserva la posición válida de cueva, selección y PB 0. Encargado: `top-bp.png` «Recibes 5 PB»;
guardado por interfaz `py_v2-top-paid.sav`, SHA **97c0571308269dfff528f77ccab5922408f2c563090ed187ddabd23c8ec3cf3e**:
zona 140, 7/0/7, ruta/vencidos 0, **PB 0→5**, equipo real SHA `12355b3132ad974cc97ae6c236f396d571b7b13ecee20f6fc64a647dc17a2f08`
idéntico al inicial. `top-boundary.json`, `top-drive.log`, `top-save.log`, `v2/save-evidence.jsonl`.

Derrota: partida v1 `py_c_lobby_saved2.sav` (8b5a8b76…, equipo 4/5/3, 7/1/7, PB 5) reanudada en la cueva nueva.
Modo `loss` de la sonda: 1 PS/Salpicadura a nuestros tres elegidos, sustituciones manuales; rival sin cambiar.
`gdb-loss.log`: entradas 0/1/2, IsWin **raw=0**, después `LOSS CLEAN`: ruta, racha, piso y vencidos 0; récord 7.
`lost.png`: «Has perdido…». Guardado por interfaz `py_v2-loss.sav`, SHA
**3a2410afe9af564d9e8b3f2dfd106fe60d57cca00997afe5c67ac4bb0e83abaa**, zona 140, **0/0/7**, PB **5→5**.
Fuentes `loss-drive*.log`, `loss-save.log`. Tests de hito: 60 passed (`tests-m3.log`), audit_round, compileall y bash -n.
Exclusión y regresión aún pendientes en esta entrada.

### Exclusión y regresión cerradas (Azahar, misma build)

Fuentes bajo `work/frontier/pyramid/v2/`:
- Pirámide rechaza Torre activa: fixture `work/frontier/lab/py_fx_tower_busy.sav`
  (SHA eaba58496f7d7266da5606eaff6e84ca179ce93dcd34d86389c7e3a0837e0445, work 16442=1),
  `pyramid-refuses-tower.png` y `gdb-busy.log`: mensaje de desafío pendiente, ningún StartBattle.
- Fábrica rechaza Pirámide activa: `work/frontier/lab/py_exit_plaza.sav`
  (SHA f2237dccc7350f48f345692b35f65357467061e9ff4e61789c1dfc19262feab9, piso 2),
  entrada caminando desde la plaza y opción Fábrica Batalla de la recepción derecha;
  `factory-refuses-pyramid.png`, `gdb-factory-busy.log`, ningún StartBattle.
  El conductor de posición sufrió respuestas vacías del FIFO; el trayecto se terminó con teclas y capturas.
- Torre, fixture `work/frontier/arena/b2-tower-in.sav`
  (SHA df1b162bf818a9a27b9862646f297336fe4e36d7a57c7eed72db411934d2155a):
  selección del equipo, `tower-menu.png` con Luchar manual, victoria asistida HP 1/Salpicadura,
  `gdb-tower.log` IsWin raw=1, ruta 2, marca nativa 0. `TOWER AFTER`: racha/récord **12→13**,
  activo 1; Pirámide racha/piso/récord/vencidos **0/0/0/0**. `tower-win.png`: próximo combate número 14.

Reinicio adicional desde `floor1-beaten0.sav` (SHA 9c58778b… indicado arriba):
`beaten-after-reload.png` muestra «Ya hemos combatido. ¡Sigue adelante!» en la cueva;
`gdb-reload-refusal.log` no contiene ningún Start ni IsWin. Se completa así la comprobación explícita
de rechazo después de guardar y cargar, además de salir y volver al piso.

Cierre: `python -m pytest -q tests` **697 passed in 18.43s** (`v2/tests-close.log`),
auditoría de 21 victorias/siete transiciones, compileall y bash -n correctos. `git diff --check` limpio.
Azahar/Xvfb/GDB detenidos en su misma shell; sin procesos del runtime ni sesión viva,
`use_gdbstub=false` restaurado (`v2/lab-stopped.log`, 2026-11-10 19:07 CET).
Aceptación v2A cerrada. No probado en consola ni el equilibrio de dificultad; PS persistentes, objetos y
salvajes siguen para otra tarea. Los vencidos permanecen visibles y rechazan combatir, alternativa admitida.

## 35. Tubo v2 — PP persistentes y medidas iniciales (2026-11-10, Codex; en curso)

Antes de escribir código nativo se ejecutó `patch.assemble()` sobre af89165:
`work/frontier/pike/v2/space-before.json`, cueva compartida **0x579604–0x57a000**,
2556 bytes, gancho **2212**, fin **0x579ea8**, **344 libres**. Todo el relleno de entrada
es cero; SHA256 de code.bin Repolished `3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293`.
El turno de frontier-orch permanece intacto. Sin tocar los informes/scripts ajenos sin seguimiento.

### Hito 1: PP en el equipo copia

Fuente reproducible: `python frontier/probes/pike/measure.py`, salida
`work/frontier/pike/v2/pp-accessors.lst`. `PokePartyGetParam` (DllField.cro 0x4e618,
tabla de saltos 0x4e688), parámetro **4** = PP, índice de movimiento en el tercer argumento:
envuelve `code.bin 0x1531c0`, que carga core desde PokemonParam+0xc y entra en **0x1531c8**.
Ese getter descifra, accede al bloque B (0x16bd00), lee byte **+0x22+movimiento**, y vuelve
a cifrar. `PokePartyRecoverAll` llama a 0x139c00, cuya rutina de curación recorre los cuatro
movimientos: getter 0x1531c8, máximo vía 0x153314/0x15311c/0x14ffd8 y setter
**0x14f4f8(core, movimiento, PP)** (0x139d04). El setter escribe el mismo byte B+0x22,
con descifrado y recálculo de checksum/cifrado retail. Bytes guardados en FUNCTION_HEADS.

`pike_pp` se llama desde H1 para restaurar y H2 para guardar, solo con ruta 6. Works
**16721–16723**: PP de movimientos 1–2, **16725–16727**: PP 3–4; cada u16 tiene dos bytes,
un work por combatiente. Reservados en REPARTO tras `python frontier/ids.py` (1157 scripts,
147 ficheros, intervalos libres 16721–23/16725–27). Cada byte 0xff deja PP llenos; valores
guardados se limitan al PP de la copia recién curada para tolerar una selección distinta al
reanudar. Inicio de desafío y curas totales/parciales restablecen los works correspondientes.
La reanudación sigue por posición como PS/estado en v1. Guardados v1 con desafío activo no
tienen PP inicializados: para actualizar, terminar/retirarse del desafío e iniciar uno nuevo.

Gancho integrado **2348 bytes**, fin **0x579f30**, **208 libres**. No hay parche CRO nuevo.
Pruebas: `tests-pp.log` **116 passed**; incluye persistencia entre dos construcciones,
PP cero, centinela, límite al cambiar movimientos y exclusión de las otras siete rutas.
Además se ejecutaron **los accesores retail reales** en Unicorn con los 32 órdenes de bloques,
comprobando cifrado, checksum y todos los bytes ajenos a PP.
`python -m pytest -q tests` → **741 passed** (`tests-m1.log`).
Build reproducible `python frontier/overlay.py --out work/frontier/pike/v2/build`
(`build-pp.log`): gancho 2348, script compartido 17295 bytes, sin superar ZO/carga.
**No probado aún en Azahar**. Inmunidades, salvajes (equipo/experiencia/captura), sala 14,
regresiones Palacio/Arena y aceptación completa v2 siguen pendientes.

### Hito 2: consulta de los inscritos e inmunidades

Fuente de reglas fijada: `pret/pokeemerald` **731ad5bf**, `src/battle_pike.c`, funciones
`DoesAbilityPreventStatus` y `DoesTypePreventStatus`; copias de lectura en
`work/frontier/pike/v2/emerald/`. Se respeta su regla específica del Tubo: Veneno/Acero
contra tóxico, Hielo contra congelación, Tierra/Eléctrico contra parálisis, Fuego contra
quemadura; Inmunidad, Escudo Magma, Flexibilidad, Insomnio/Espíritu Vital y Velo Agua.
No hay estado nuevo para quien está debilitado o ya afectado. Un objetivo inmune cuenta
para el límite de 1/2/3 intentos de la sala, como en ese origen, y se anuncia el rechazo.
No se han añadido reglas de habilidades posteriores a Esmeralda ni efectos de clima.

Medición de las consultas retail: `DllField.cro` tabla 0x4e688, índices **6** y **7** llaman
a `0x3b3b48` y `0x4d3204`: especie/forma actuales, personal 6/7, con excepción Arceus/
Multitipo que usa 0x4d2454. Índice **22** llama a `0x4d1730`: carga core+0xc y el byte
A+0xc de la PK6, la habilidad **actual**, no una habilidad posible de la especie.
La selección de Mansión puede reordenar el equipo o elegir la Caja de Combate: el constructor
0x1e3d2c usa `work+0x2c` para fuente y `work+0x30+4*k` para índice; la caja está en work+0xb84.

`pike_param` convierte los slots virtuales 256–258 a esos índices, solo en ruta 6, en
`PokePartyGetParam`. El resto de slots/rutas mantiene el control de límites retail.
Puente **DllField.cro+0x4e644**, 16 bytes originales
`0800a0e134c9feeb060050e11501009a`, sin relocaciones internas ni imports sobre ellos.
Entrada v0.5 SHA256 **8c9da930a13b56b797dedfc87940b85b5b3cad9a1cf35390c4796b0c6f5cb53a**.
Se rehacen hashes CRO y se actualiza CRR después del de DllBattle, preservando ambos.
Gancho integrado **2452/2556 bytes**, fin **0x579f98**, **104 libres**.

`tests-immune.log`: **302 passed** (incluye ambos tipos, cada habilidad, objetivo inmune
que cuenta para el límite, selección reordenada 5/0/3, caja/equipo y ocho rutas en Unicorn,
ejecutando el puente y el contador real de miembros). `tests-m2.log`: **927 passed**.
Build `v2/build-immune`, `build-immune.log`: compartido 19794 bytes, gancho 2452,
ZO de Mansión 15864. Textos 637: nueva línea inmune 1055; Pirámide se desplaza a 1056–1070.
**Aún no probado en Azahar este puente y las inmunidades**. Salvajes no implementados.

### Primera comprobación dinámica de PP (build del hito 1)

Sonda `frontier/probes/pike/lab_probe.py`, log `v2/gdb-pp.log`, fixture de entrada
`work/frontier/lab/pk_saved_458.sav` (desafío iniciado de nuevo para inicializar PP).
Selección Torchic/Poochyena/Beldum (son motes de Pokémon modificados de la copia de laboratorio).
Enemigos debilitados solo en RAM, PS 1 y Salpicadura; resultados, works y PB sin escribir.
Tres IsWin reales raw=1. En el segundo, primer movimiento **10→6 PP**; en la construcción
siguiente el work contiene **[6,10,15,30]**, H1 lo restaura, y el tercer combate deja **3 PP**.
PS de entrada también bajan **156→137**. Primer combate gastó 10→7, pero hubo curaciones
antes del segundo: no se usa esa pareja como prueba de persistencia.
`before-room14.png` está mal nombrada: muestra «Ruben ha obtenido 1 PB» tras la sala 14;
el segundo resultado tenía racha 13 antes de AddWinCount y el tercero 14 (pasó a 15).
El guardado en disco aún no había cambiado al tomar esta medida: PB/equipo al salir pendientes.

### Hito 3: curar solo la copia del Tubo

Al pausar y guardar después de la prueba PP se obtuvo `v2/pp-paused.sav`: sala 15,
activo 1, récord 15 y PB 1; work 16721 = 0x0a03, conserva 3 PP en el primer movimiento.
La comparación descifrada con `work/frontier/lab/pk_saved_458.sav` detectó dos cambios
indeseados: PS PK6+0xf0, 26→34 y 25→35. El constructor retail 0x1e3d8c cura el equipo
original antes de copiarlo. `rental_hook` ahora omite esa llamada solo en ruta 6 y H1
cura la copia antes de restaurar los works. Las demás rutas conservan la llamada anterior.

`v2/tests-copy-final.log`: **935 passed in 20.64s**; incluye ocho rutas del constructor,
H1/H2 con copia curada y selección del Domo. compileall, bash -n y diff --check correctos.
`v2/space-copy.txt`: **2468/2556 bytes**, fin **0x579fa8**, **88 libres**.
Build regenerada en `v2/build-immune` (`build-copy.log`). `boot.sh` exige que el IPS
instalado coincida con el código del que se calculan los símbolos de la sonda.
Un arranque anterior (`boot-immune.log`) usó código desfasado respecto a la sonda y se
interrumpió; no aporta evidencia. El válido es `boot-immune2.log`.
Todavía no se ha medido la conservación completa del equipo al salir con esta corrección.

### Hito 4: recuperar espacio compartido

`arena_start` y `palace_start` comparten ahora una sola lectura del save/ruta y limpian
ambas marcas antes de habilitar la correspondiente a un desafío Individual activo.
Se mantienen registros, pila, bits ajenos y continuación. Elimina **52 bytes**:
**2416/2556**, fin **0x579f74**, **140 libres** (`v2/space-shared.txt`).
`tests-shared-real.log`: 252 passed; suite `tests-shared-full.log`: **935 passed in 20.60s**.
Build `v2/build-shared` generada (`build-shared.log`). Regresión dinámica de estos cambios
Arena/Palacio todavía **no probada**.

Sonda salvaje **solo RAM**, build anterior de 2468 bytes, `competitor=0`, setup+0xb3=1,
rival count=1. `gdb-wild-experiment.log` / `fight-wild-experiment.log`: victoria raw=1
contra un rival único, PP 3→2, sin escribir resultado/racha. No equivale a sala salvaje
implementada: conserva presentación de entrenador y un set de Mansión a nivel 50.
`boot-wild2.log`, `wild-bag-open.png`, `wild-balls-available.png`, `wild-ball-consumed.png`:
se puede abrir Bolsa/Poké Balls y usar una; existencias 13→12 (captura no conseguida en
ese intento). Por tanto esta propuesta **no garantiza ausencia de captura**; no instalarla.
Las dos puertas de experiencia retail DllBattle+0x25590 y +0x6bc94 excluyen setup+0xb3 != 0
(`bag-gate.lst`), pero aún falta prueba dinámica de experiencia y equipo al salir.
El candidato sin integrar `frontier/probes/pike/wild_candidate.s` añade 168 bytes
(`wild-size.json`, medido antes de compactar: 2468+168=2636/2556, exceso 80).
No es un mínimo ni un bloqueo definitivo: comparte código pendiente de integrar y todavía
requiere desvíos validados, sets propios y prohibición de captura. No reservar su work provisional.

### Hito 5: salas salvajes integradas (Claude, relevo de Codex)

Relevo: Codex se cortó por cuota con dos cambios sin commit (`lab_probe.py`: sondas de consulta y
setup salvaje solo RAM; `wild_candidate.s` sin seguimiento). Se conservan; el candidato queda marcado
como sustituido. Ningún laboratorio vivo al empezar (`ps`: sin Azahar/Xvfb/GDB del Tubo).

Diseño elegido para caber: el combate sigue siendo el de la Mansión (competitor 2), que ya es el
que no da experiencia (`noexp` de la Mansión) y no permite capturar por ser de entrenador; cambiar
competitor a 0 abría la Bolsa y gastaba Poké Balls (hito 4). La sala salvaje solo cambia el rival:
- work **16675** `PIKE_WILD` (libre según `python frontier/ids.py`: 1157 scripts, 147 ficheros,
  «free 16673-16675»; reservado en REPARTO): índice de maisonpkN del set salvaje, 0 = ninguno.
  La rutina de la sala lo pone a 0 en cada sala y solo la sala salvaje lo escribe.
- sets en **maisonpkN 217–222** (Seviper, Milotic, Dusclops, Electrode, Breloom, Wobbuffet con los
  movimientos de `sLvl50_Mons` de pokeemerald 731ad5bf). Medido: el archivo tiene **999** entradas,
  los entrenadores de maisontrN usan como máximo la **216** y 217–998 son ceros; overlay.py exige
  que las seis estén vacías y reescribe solo esas (`a/1/8/2` en la build).
- `dome_count` (0x1e3548) devuelve **1** con ruta 6 y `PIKE_WILD` ≠ 0; `rival_hook` salta a
  `pike_rival` con ruta 6 (r4 = set salvaje, r2 = 0xb6); nuevo sitio **0x1e4e80** `mov r1, #50`
  (`e3a01032`) del constructor del rival → `pike_level`: 46 para 217–218, 45 desde 219, 50 si no.
- Tercer Pokémon según racha como `GetBattlePikeWildMonHeaderId` (≤280, ≤560, ≤840 salas).
- Pista POKÉMON = combate duro o salvaje, como Esmeralda. Texto nuevo 1056; Pirámide 1057–1071.

Espacio: `patch.assemble()` → gancho **2544/2556 bytes**, fin **0x579ff4**, **12 libres**.
Desviaciones: un solo combate por sala (Esmeralda: hierba con encuentros); presentación del combate
de la Mansión (entra un entrenador que saca al Pokémon salvaje); naturaleza fija Fuerte, sin EV.
Tests: `python -m pytest -q tests` → **968 passed** (incluye Unicorn de cuenta/set/nivel en 9/5/8
combinaciones de ruta y work, sorteo de la sala salvaje por racha y limpieza en todas las salas).
Build `python frontier/overlay.py --out work/frontier/pike/v2/build-wild` (`build-wild.log`).
**No probado aún en Azahar**: Bolsa/captura/experiencia con competitor 2, combate salvaje ganado y
perdido, ni el resto de la aceptación.

### Corrección del hito 2: números de tipo de ORAS

Las inmunidades de tipo usaban los números de Esmeralda, que tiene el tipo «???» en el 9:
Fuego 10, Eléctrico 13, Hielo 15. En ORAS no existe y son **Fuego 9, Eléctrico 12, Hielo 14**
(texto de juego 18 en orden y tabla personal `a/1/9/5`: Blaziken 9/1, Pikachu 12/12, Lapras 10/14,
Metagross 8/13, Garchomp 15/4). Con la tabla anterior el Agua protegía de quemaduras, el Dragón
de congelación y el Psíquico de parálisis, mientras Fuego/Hielo/Eléctrico no protegían.
Corregido `STATUS_IMMUNE_TYPES` = tóxico (3, 8), congelación (14), parálisis (4, 12), quemadura (9);
las habilidades conservan sus números de Gen 3 (Inmunidad 17, Escudo Magma 40, Flexibilidad 7,
Insomnio 15, Espíritu Vital 72, Velo Agua 41). Tests con las expectativas corregidas y un caso
nuevo que comprueba que 10/13/15 ya no protegen. Suite: `tests-wild.log`.

### Hito 6: aceptación en Azahar (build-wild, 2026-11-10, Claude)

Build `work/frontier/pike/v2/build-wild` (code.ips SHA256 `f64e527c…`), un solo laboratorio, tres
arranques sucesivos con `frontier/probes/pike/boot.sh` (el anterior se detiene antes). Sonda
`frontier/probes/pike/lab_probe.py`; logs `gdb-wild-session1.log`, `gdb-palace.log`, `gdb-arena.log`.
Salas forzadas fijando los segundos que lee `pike_room`: `frontier/probes/pike/seconds.py` ejecuta el
script 5 construido en la VM con los works del juego y devuelve los segundos que dan la sala pedida
por la puerta izquierda; la sonda los pone al volver la función de tiempo de code.bin 0x12fa94 a
DllField+0x4fad8 (un breakpoint dentro de DllField, 0x742aec, no saltó nunca). Cada predicción del
log coincide con lo mostrado. Combates asistidos solo en RAM (rival PS 1/Salpicadura, o rival 300 PS
para perder); resultados, works de racha y PB no se escriben salvo donde se indica.

Partida de entrada: copia de `v2/pp-paused.sav` (Tubo pausado, sala 15). Selección Torchic/Beldum/
Poochyena (motes de Metagross/Blaziken/Garchomp; la sonda lee tipos 8/13 y habilidad 29 del primero).
- **PP del guardado**: el primer combate entra con [3,10,15,30], los PP guardados antes de la pausa.
- **Inmunidad**: racha 17 (sala 4), estado previsto; «¡Un Pokémon salvaje ha usado un ataque
  extraño…!» y «¡Su tipo o habilidad lo protege del estado!» (`immune-1.png`, `immune-2.png`);
  consulta del hueco virtual 256: tipos 8/13, habilidad 29 → tóxico rechazado por Acero; works de
  estado siguen a 0.
- **Salvaje ganada**: racha 18, «¡Un Pokémon salvaje se lanza al ataque!» (`wild-room-msg.png`);
  `PIKE COUNT route=6 wild=217`, setup competitor 2 con **1** rival; Seviper **Nv. 46**, una sola
  Ball en su marcador (`wild-battle-start.png`). **Bolsa**: el cursor llega a BOLSA y A no abre nada
  (`wild-bag-refused*.png`), al contrario que la sonda de competitor 0 del hito 4. Victoria raw=1.
- **PP entre salas**: tras la salvaje, Metagross guarda [9,10,15,30]; el combate de la sala siguiente
  (individual, `wild=0`, 3 rivales: el work se limpió) entra con **[9,10,15,30]**.
- **Sala 14 y PB**: nuevo desafío (ver incidencia), salas NPC forzadas hasta la racha 13: «¡Última sala
  de la ronda!» (`room14-msg.png`), victoria y «Ruben ha obtenido 1 PB» (`room14-bp.png`), racha 14.
- **Salvajes**: Dusclops (219) **Nv. 45** y Seviper (217) ganadas (14→15→16; la sonda de derrota no
  alcanzó la segunda copia del rival). **Derrota**: fixture en RAM de los works del equipo (PS 1,
  PP 0), Seviper con 300 PS en sus dos copias (0x82063d0 y 0x8206ce0, a 0x910). En pantalla
  1/156 y 1/184 y PP [0,0,0,0] al entrar (los works mandan); Forcejeo, IsWin **raw=0** con racha 16.
  Limpieza: ruta 0, racha 0, activo 0, récord 20 (`wild-lost.png`).
- **Equipo al salir**: guardado del juego tras la derrota `v2/wild-after-loss.sav` (SHA256
  `c9093b9f…`) frente a `pp-paused.sav`: especie, EXP, PS, PP, movimientos y objetos idénticos en los
  seis; sigue habiendo 6 Pokémon. Cambian solo campos de recuerdos (0xA4–0xA8, 0xCC–0xD0; retail,
  §10) y el **bit 5 del byte 0x30** (cintas) de los tres participantes: con el récord del Tubo en 20
  la Mansión concede su cinta de racha (hipótesis: Combatiente Experto; el Tubo cuenta salas).
- **Exclusión**: con el work activo del Palacio puesto a 1 en RAM, la recepcionista del Tubo dice
  «Tienes un desafío a medias en otra instalación» (`pike-refuses-palace.png`); en el Palacio
  (`work/frontier/palace/c3-resume-in.sav`) con el del Tubo a 1, igual (`palace-refuses-pike.png`).
  Restaurados a 0 antes de seguir.
- **Regresión Palacio**: misma partida, reanudación y victoria asistida: racha 2→3, récord 3,
  `setup+0xa8 = 0x40000000`, `wild=0`, 3 rivales. **Arena** (`work/frontier/lab/ar_paused9.sav`):
  victoria asistida, racha 9→10, `setup+0xa8 = 0x80000000`. Ambos con el inicio compartido de 7386d80.
  No se ejercitó el juicio de 3 turnos de la Arena ni se observó la IA del Palacio (KO en un turno).

**Incidencia sin aislar**: tras ganar en la racha 19, unas pulsaciones de A de más llevaron al
vestíbulo con racha 20, activo 1 y récord 20; al volver a combatir en la misma sesión el desafío empezó
de cero (primera sala con racha 0, equipo curado). No se capturó qué opción del menú se eligió
(Continuar/Pausar/Vídeo). La reanudación tras recargar la partida (inicio de esta sesión) sí conservó
la racha 15. Pendiente de reproducir; no forma parte de los criterios de v2.

Laboratorio detenido al final: sin procesos de Azahar/Xvfb/GDB del laboratorio y `use_gdbstub=false`
restaurado. No probado en consola.

## 36. F6-PALACIO-C: movimientos por naturaleza y PS (2026-11-11, Claude)

Tarea de frontier-orch (modo paralelo, carril `claude`). Sobre la vía híbrida de §33 (bit 30 de `setup+0xa8`, cliente 0
de interfaz con objeto IA y flags 7, comandos 3/5/6 por la columna IA).

### Reglas de Esmeralda (fuente)

pret/pokeemerald **731ad5bf**, descargado con `curl` de raw.githubusercontent.com a `work/frontier/palace/c-src/`:
- `src/battle_gfx_sfx_util.c` `ChooseMoveAndTargetInBattlePalace` (sha256 510be3aa…): `percent = Random() % 100`;
  columna baja si `palaceFlags` del combatiente (que `battle_script_commands.c:4659`/`:6389` ponen si
  `maxHP / 2 >= hp`, PS > 0 y sin dormir); grupo = ataque si `percent < t[0]`, defensa si `< t[1]`, si no apoyo; a la
  IA solo le llegan los movimientos de ese grupo con PP. Sin ninguno: elige al azar de otros grupos y con 50 %
  «no obedece» (fuera de esta tarea).
- `GetBattlePalaceMoveGroup`: objetivo SELECTED/USER_OR_SELECTED/RANDOM/BOTH/FOES_AND_ALLY → apoyo si potencia 0,
  ataque si no; DEPENDS/OPPONENTS_FIELD → apoyo; USER → defensa; el resto → ataque.
- `src/battle_script_commands.c:855` `gBattlePalaceNatureToMoveGroupLikelihood` (sha256 e0847cd2…), con
  `PALACE_STYLE(atk, def, atkLow, defLow) = {atk, atk+def, atkLow, atkLow+defLow}`. Copiada en
  `frontier/palace_ai.py` (`EMERALD_STYLES`, 25 filas, orden de naturalezas igual en Gen 6).

### Tabla de grupos desde a/1/8/9

`palace_ai.move_groups()`: GARC `a/1/8/9` (sha256 426aaeb0…, idéntico en retail y Repolished), paquete `WD` de
622 registros de 0x24 bytes; pk3DS `Move6`: potencia 0x03, objetivo 0x14 (`MoveTarget`). Correspondencia de
objetivos de Gen 6 con los de Esmeralda calibrada sobre los movimientos 1–354 contra `src/data/battle_moves.h` del
mismo commit: coincide en 348; las 6 diferencias (Metrónomo, Conversión 2, Sonámbulo, Ayuda, Capa Mágica, Robo) van
en `EMERALD_OVERRIDES` con el grupo de Esmeralda. Resultado: 393 ataque, 113 defensa, 116 apoyo; empaquetada a
2 bits (156 bytes). Los movimientos de Gen 4–6 siguen la regla por objetivo (hipótesis razonada, no medida en un
juego con Palacio).

### Dónde decide la IA (lectura estática de DllBattle.cro v0.5)

- Comando 3, columna IA = proc **0xd0c8**. En su estado 1 llama a **0xe044**(cliente, BattleMon, u8 usable[4]) en
  **0xd468** (`f50200eb`, `bl` relativo sin relocación), que devuelve el primer hueco usable o 4 (Forcejeo), y copia
  `usable[]` a **IA+0x198** (0xd4f8).
- Los guiones de la IA saltan los huecos con IA+0x198 = 0 (**0xa88c0**: estado 8, la puntuación queda excluida con
  la marca de 0x170 a 1) y el elector de reserva **0xa9438** también elige solo entre ellos. Resultado de la IA en
  IA+0x278 (hueco) / +0x279 (objetivo), leído en 0xd61c.
- BattleMon: PS `u16 +0x10`, PS máx. `u16 +0xe` (la curación se acota con él, 0x7aa4/0x1ecf0), movimiento del hueco
  k en `u16 +0x11c + 14k` (0xa9274), `[mon]` = PokemonParam (0x50fe4, bayas de confusión), `[pp+0xc]` = CoreParam;
  naturaleza = code.bin **0x152f08**(core) (descifra, bloque A +0x14 = PK6 0x1C, cifra; el setter es 0x168b10).
- `rand(n)`: thunk CRO **0x490** → code 0x48ad84 (el que usa la propia IA, p. ej. 0xa8fd0).

### Implementación y espacio

La cueva de code.bin está casi llena (**2544/2556, 12 libres**, `patch.assemble()`), así que el filtro va en la
propia CRO: el relleno a cero entre el fin de .text (**0xd7628**) y .rodata (**0xd8000**), 2520 bytes, dentro de la
región de código declarada en la cabecera (`0xb0` = 0x180, `0xb4` = 0xe6e80, que ldr:ro mapea como código).
Ninguna relocación apunta dentro salvo el fin exclusivo del rango [0xd7610, 0xd7628) (0xd68f8, montado en
0xd68a8–0xd68c4). `frontier/asm/palace_cro.s` se enlaza en **0xd7630** (568 bytes: 312 de código, 100 de tabla de
naturalezas, 156 de grupos; quedan **1944**), y 0xd468 pasa a `bl 0xd7630`. Medido con
`python frontier/palace_ai.py` → `work/frontier/palace/c/space-c1.txt`.

`palace_moves`: llama a 0xe044; si devuelve 4 o no es el cliente 0 de interfaz con el bit 30, nada cambia. Si no:
`rand(100)`, naturaleza, columna por `hp <= maxHP >> 1`, grupo, y pone a 0 los huecos usables de otro grupo; si
ninguno usable es del grupo, los deja todos (la IA elige de los otros grupos: decisión, Esmeralda elige al azar).
Devuelve el resultado retail. Desviaciones: la columna baja es instantánea (en Esmeralda queda fija hasta el
cambio y no se activa dormido); sin «no obedece» ni textos.

### Pruebas Unicorn

`tests/test_frontier_palace.py` (CRO parcheada real a dos bases; stubs solo en 0xe044, 0x490 y 0x152f08): tabla
de grupos (movimientos conocidos, sobrescrituras), tabla de naturalezas (Fuerte, Audaz, Grosera, Amable), que el
blob cabe en el relleno de la región de código sin relocaciones, filtro con seis naturalezas (incluidas las
extremas Grosera 88 % y Amable 90 %) en las dos columnas y los bordes de cada umbral, PS 50/100, 51/100, 50/101,
51/101 y 1/100, cambio de columna (Amable al 50 %), grupo vacío, huecos no usables, cliente/tipo/bit ajenos y
Forcejeo. `env -u ORCH_LANE python -m pytest -q tests` → **1066 passed, 1 skipped**
(`work/frontier/palace/c/tests-c1.log`; con `ORCH_LANE` puesto, 9 tests del orquestador fallan por el entorno del
carril, no por este cambio).

### Azahar (2026-11-11, laboratorio del carril, puerto 24690)

Build `python frontier/overlay.py --out work/frontier/palace/c-build` (`c/c-build.log`): code.ips f64e527c…,
DllBattle.cro 3ea58b39…, gancho de code.bin 2544 bytes (sin cambios). Partida `c/c2-gentle.sav` (64e336fd…) =
`work/frontier/lab/pa_strong.sav` con Metagross **Amable** (alta: 18 % ataque, 70 % defensa, 12 % apoyo; baja:
90/5/5) y Puño Meteoro (ataque), Defensa Férrea (defensa), Onda Trueno (apoyo), Terremoto (ataque)
(`frontier/probes/palace/c2_fixture.py`). Sonda pasiva `frontier/probes/palace/lab-c2-probe.gdb`; base de
DllBattle medida **0x6f3000** (lr − 0x73260 en `palace_ai_flags`).

- **El código del relleno de la CRO se ejecuta**: `palace_moves` (CRO+0xd7630) entra y sale en cada decisión de los
  dos clientes desde el primer combate (en Azahar; en consola no probado).
- **Ronda completa del Palacio** (puerta (31,69) → 340 → Combatir → Individual → Metagross/Blaziken/Garchomp →
  guardado): **7 combates ganados** (`ISWIN raw=1` ×7), `START a8=40000000 palace=1`, menú posterior «Combatir
  número 8» con Continuar/Pausar (`c/t-after7.png`). Sin cuelgues ni pantallas negras. Registro
  `c/gdb-palace-round.log`. 48 pulsaciones, todas fuera de decisiones: 27 de menú, 14 de presentación y 7 de
  frase final del entrenador (`c/presses.log`).
- **Movimientos elegidos frente a la tabla**: `python frontier/probes/palace/c2_check_log.py
  work/frontier/palace/c/gdb-palace-round.log` → **68 decisiones del cliente 0, 0 discrepancias**: el grupo sorteado
  es el de Esmeralda para su naturaleza, pct y columna, y el movimiento elegido estaba entre los que quedaron y era
  del grupo (13 veces el grupo no tenía ninguno usable: se quedaron los otros y la IA eligió uno de ellos). Amable,
  48 sorteos en columna alta: 3 ataque, 40 defensa, 5 apoyo (Defensa Férrea mientras era usable; Onda Trueno con
  pct 88–89); 15 en columna baja: 14 ataque, 1 defensa. Blaziken y Garchomp (Alegre, solo ataques) sacaron apoyo
  o defensa y se quedaron todos sus movimientos.
- **Cambio de columna**: combate 1, Metagross de 84/156 (alta, pct 7 → ataque) a **75/156** (75 ≤ 78: baja, pct 38
  → ataque, que en alta habría sido defensa); combate 3, 28/156 con pct 88 → ataque (umbral 90 de la columna baja).
  Combate 2 con fixture de RAM `pa['hp_pct']=45`: entra con 70/156, pct 84 → ataque.
- Cuando Defensa Férrea dejó de figurar como usable en 0xe044 (defensa ya subida; no se midió la causa) y salió
  defensa, quedaron Puño Meteoro, Onda Trueno y Terremoto y la IA eligió Puño Meteoro: «otro grupo».
- **El rival** (cliente 1, tipo 1) pasa por `palace_moves` sin filtro en todos los combates (`NOFILTER`).

**Regresiones** (misma build y sonda):
- **Mansión** (instalación sin motor; se entró por error en la 517 con la misma partida): `START a8=0 palace=0`,
  solo el cliente 1 con objeto IA, menú de movimientos manual con los del fixture (`c/r-maison-moves.png`), dos
  decisiones del rival sin filtro; `c/gdb-maison.log`. No se terminó el combate.
- **Arena** (`c/r-arena-in.sav` = `work/frontier/lab/ar_saved_457.sav`; al cargar, el desafío se invalidó como en
  retail y se inscribió de nuevo): `START a8=80000000 palace=0 arena=1`, ningún objeto IA para el cliente 0,
  decisiones manuales (A = Luchar → primer movimiento), rival sin filtro, victoria `ISWIN raw=1` y «combate número
  2» (`c/ra-after.png`); `c/gdb-arena.log`. El juicio de la Arena no se dio (KO antes del tercer turno).
- Laboratorio parado al final (sin procesos del carril, sin `session.json`, `use_gdbstub=false`).

**No probado**: consola (ldr:ro y permisos de la región de código de la CRO), el juicio de la Arena con este
parche, Doble/Multi, la Fábrica/Torre/Tubo/Pirámide/Domo con esta build. «No obedece» y textos, fuera.
Suite: `env -u ORCH_LANE python -m pytest -q tests` → 1066 passed, 1 skipped (`c/tests-c2.log`).
## 37. F6-DOMO-SALA: sala amplia retail propia (2026-11-11, Codex)

Hito estático: `frontier/dome_room.py` y `island_build.py`: 456 clona el mapa/área de **365**, la sala amplia
final de la Liga; conserva script del Domo y nativas de 517. La puerta de plaza y salida siguen en warp 1
(6,57). Sin cambios en `patch.py`, ensamblador, CRO ni código ejecutable generado: `code.ips` antes/después
idéntico (SHA256 `f64e527c6348571ca8c83780ecd23152dd144bfe108abad7e286b9cdef19c4ce`).

Selección reproducible: build inicial `python frontier/overlay.py --out work/frontier/dome/room/before`;
`faraway/run.sh Probe work/frontier/dome/room/before-island/game work/frontier/dome/room/survey-ws zones`
→ `work/frontier/island/zones.tsv`. Medidos `entities 517 315 314 449 448 365 354`, `floor 314|315|365|354|448`
y `WorldTextures` para esos candidatos (`work/frontier/dome/room/{entities,floor*,budget*}.txt`).

| Donante | Datos de zones.tsv | Carga en bytes | Decisión |
| --- | --- | ---: | --- |
| 314, vestíbulo de concursos | matrix 358, área 179, 22 NPC, 2 warps, 4 triggers, 7 props | 1.221.632 | Pasillo x13–17 desde y21; no cubre la recepción y escenas de 517. |
| 315, sala de concursos anexa | matrix 359, área 179, 8 NPC, 1 warp, 1 prop | 1.165.696 | Suelo x5–19/y4–14, demasiado corto para las escenas. |
| 354, Liga | matrix 261, área 149, 2 NPC, 2 warps, sin props | 545.536 | Menos adecuada que la sala amplia plana. |
| 448, Instituto de Combate | matrix 350, área 199, 5 NPC, 1 warp, 1 prop | 326.144 | Menos amplia que 365. |
| **365, Liga** | **matrix 272, área 160, 1 NPC, 1 warp, sin props** | **305.024** | Suelo plano x6–26/y4–32; cubre recepción y coreografía Individual (x19–23/y12–25). |

Build `work/frontier/dome/room/after`, log `build-after.log`: carga **305.024** = mundo 21.760 + props 42.112
+ modelo 241.152, menor que `LOAD_BUDGET` 2.724.608. ZO completo **15.452 bytes** (56/360/14996/0/12),
menor que 17.248. Script antes/después idéntico: SHA256
`9caf56fceb24c52be75b59a5c39c4ead3a7de8a1178fd128b0e881047d00bd53`.
Solo quedan tres NPC: espectador uid0, recepcionistas uid1/2 (modelos 297/62 registrados desde área 214);
sin eventos de Liga ni triggers. `dome_room.check_room` guarda tamaño, entidades, salida, texto 619 y script.
`tests/test_frontier_dome_room.py` incluye rechazo de tamaño, salida retail, texto, script y triggers dañados.
Azahar y aceptación completa: en curso; no probado aún el ciclo del torneo en este mapa ni consola.

**Relevo bloqueado (00:28)**: no hay commit de esta implementación. El sandbox permite escribir en la raíz
`.git`, pero monta `.git/worktrees/codex` en solo lectura (`findmnt -T …/worktrees/codex`); `git add` y
`git commit` fallan al crear `index.lock`. El orquestador debe incluir ese gitdir exacto entre sus raíces de
escritura y recoger los cambios sin commit del carril (incluidos dome_room.py y tests nuevos).

Azahar ejecutado: build anterior con `f6dm_saved_456.sav` → `room/before.png` (solicitud de inscripción en la
sala de la Fábrica). Build nueva con `f6h_saved_plaza.sav`, caminar hasta (6,58), norte dos veces →
`room/{dome-door,after-entry,after-entry2}.png`: puerta e interior amplio de piedra, tres NPC visibles, RAM
(297,2,567), tile (16,31). **No probados** inscripción, combate, pausa, guardar/cargar con guardado nuevo,
salida a plaza ni regresiones Fábrica/Torre en esta build. El primer intento de caminar lateralmente desde la
entrada se detuvo en (17,31): el muestreo de alturas no detecta las barreras de la entrada. Ir primero al norte;
receta propuesta en `frontier/probes/dome_room/README.md`, todavía no validada completa.

Se interrumpieron dos shells conductoras y se reinició el laboratorio; al perder esas shells, sus namespaces PID
no son visibles desde llamadas posteriores de Codex. La última shell se cierra con `reap` y use_gdbstub=false;
el `after_run` del orquestador debe hacer **reap desde el host** y comprobar que no quedan procesos de este
carril de las shells anteriores. No se han señalado procesos de otros carriles.

Suite final ejecutada antes de los cambios solo documentales: `env -u ORCH_LANE python -m pytest -q tests` →
**988 passed, 1 skipped** (`room/tests-clean-env.log`); compileall de dome_room.py y `git diff --check` correctos.
Con ORCH_LANE heredado fallan nueve tests del supervisor porque el agente ficticio escribe lane-task en vez de
tasks.json; el orquestador no se modificó. Estado del carril: blocked por el gitdir, aceptación de juego pendiente.

### 37.1. Continuación de aceptación (2026-11-11, Codex)

El orquestador recogió la implementación anterior en **80068a1** y habilitó escritura del gitdir del carril.
Se retoma desde ese commit; el bloqueo de commit descrito arriba pertenece a la sesión anterior.
Artefactos de esta aceptación: `work/frontier/dome/room/` (locales, no comerciales en Git).

- Puerta de plaza → sala 456: `accept-entry.png`; recepcionista hablando: `accept-reception.png`.
  Recorrido ejecutado: (16,31) → (16,25) → (23,25), mirar norte. No se alteran colisiones para atravesar las barreras.
- Inscripción de Torchic/Beldum/Poochyena y selección de dos para el torneo: `accept-registration.png`.
  Recepcionista, rival y jugador recorren la sala amplia: `accept-choreography.png`; combate: `accept-battle.png`.
- Primer intento perdido; segundo torneo ganado: `accept-win.png`, `accept-next-round.png` (Continuar/Pausa).
  `accept-battle.gdb.log`: RESULT n=1 raw=0 y n=2 raw=1. Victoria asistida en RAM de combate, sin escribir
  resultado, racha, PB, works ni partida: rival a 1 PS/Salpicadura, y primer movimiento del inscrito 0 a Pistola Agua
  para poder golpear al Fantasma/Absorbe Fuego del fixture. Se corrige la sonda: las copias cliente/servidor del Domo
  están separadas por **0x910** (dos * 0x488), no 0xd98 de la Pirámide. Generador reproducible nuevo:
  `frontier/probes/dome_room/lab_probe.py`, normal pasivo por defecto, ayudantes optativos. Prueba de flujo,
  **no de dificultad**. Los movimientos de Torchic en el guardado siguen siendo (10,45,52,28).
- Pausa elegida en el menú real tras ganar: `accept-paused.png`. RAM: work 16438=0 (ruta libre), Torre
  16441–16443=0/0/0, Domo 16473–16475=1/1/1. Guardado real mediante X → Guardar, checksums válidos con
  `save_event.sf.blocks`; `save-inspect.txt`, copia `paused-456.sav`, SHA256
  `ec03f883df59a59703cff24a8a3da15df2d249c48eeae25a0fbdc6bb063d25d1`.
  Zona guardada 456, centro de tile (23.5,25.5), altura 2. Apagar y volver a cargar conserva posición y sala;
  se puede hablar con la recepcionista: `accept-reloaded.png`.

La salida retail necesita adaptación: 365 tiene warp tipo **0, sin retorno**, a altura 0. El render sitúa
al jugador a altura 2; subir el plano del warp a 2 fue una hipótesis que **no** pasó la prueba. Tampoco pasaron
las builds `final` (tipo 2/plano 0), `return2` (2/plano 2), `final-walk` (5/plano 2) y `return30` (2/plano 2/y30).
Una transición experimental cambiando el tipo a 5 en RAM llegó a plaza (117,2,1035) = tile **(6,57)**,
`experiment-type5-exit.png`, pero no basta para aceptar la build. `return5zero` (tipo 5/plano 0/y31) tampoco salió.
El constructor admite una cuarta columna opcional de datos
`warp.index=índice,zona,warp,tipo`; solo 456 la usa. Destino intacto 209/warp1, sin cambiar script ni nativas.


**Salida resuelta y aceptación cerrada (13:48).** No era necesario mover el warp ni cambiar el motor.
`Probe tuples` mide en 365, (15–17,31), **20300000**; en la salida equivalente de 517, **20000000**
(`tuples365.txt`, `tuples517.txt`). El constructor cambia solo el segundo byte de esas tres casillas en el
FIELD_DATA **propio del clon**, con comprobación de los cuatro bytes originales, y el tipo del warp 0→2.
Plano 0, posición (279,0,567), ancho 3 y destino 209/warp1 se conservan. `exit-tuples.txt` confirma los
3 tuples finales 20000000 al leer los archivos empaquetados de la build desde un workspace nuevo.
La sala 364 también se midió (`floor364.txt`, `entities364.txt`): suelo y4–22, insuficiente para la recepción y25.
No se cambian los movimientos del torneo ni las otras puertas.

Build aceptada: `python frontier/overlay.py --out work/frontier/dome/room/exit-tiles`,
`build-exit-tiles.log`: ZO **15452 <= 17248**, carga **305024 <= 2724608**, nativas del donante 517.
Desde apagado, carga del guardado de pausa dentro: `accept-exit-tiles-reload.png`; caminar por (16,29) y sur
sale a plaza, RAM (117,2,1035) = **(6,57)**, `accept-exit-tiles-out.png`. Se repite entrada por la puerta y
salida (`accept-final-entry.png`, `accept-final-exit.png`). La inscripción/combate/pausa/guardado anteriores
se probaron con este mismo mapa y script, antes de corregir solo estas tres casillas de salida.
Regresión de puertas en la build final: Fábrica y Torre entran y salen, capturas
`accept-factory-{in,out}.png`, `accept-tower-{in,out}.png`, log `accept-final-doors.gdb.log`.
Interiores RAM (369,2,567); tras salir y pasos adicionales, plaza (369,2,1089) y (351,2,891).
Comparación visual: `before.png` (Fábrica) frente a `accept-final-entry.png` (sala amplia de piedra).

`accept-hashes.txt`: script Domo y code.ips idénticos al antes. El DllBattle.cro de `before` es anterior a la
integración del Palacio C: difiere del actual; los CRO actuales son idénticos entre `final` (antes de los cambios
de salida de esta continuación) y `exit-tiles`. Ninguna fuente nativa, CRO, code.bin ni patch.py modificados
por esta tarea. La prueba asistida del combate no acredita dificultad ni consola; consola **no probada**.

Verificación final: `env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests'` →
**1077 passed, 1 skipped** en 39 s (`tests-exit-tiles.log`); `git diff --check` correcto.
Laboratorio detenido mediante `scripts/azahar_lab.py reap` desde su shell conductora; use_gdbstub=false;
`own_processes()` → **[]** (`lab-cleanup.txt`). Puerto usado 24691, sin tocar el laboratorio del otro carril.

Reconstrucción independiente `repro-exit-tiles`: **27 archivos idénticos byte a byte** frente a la build
aceptada (`build-repro-exit-tiles.log`, `repro-check.txt`). Generación y py_compile de la sonda correctos.

## 38. F7-PAQUETE: alfa instalable v0.1 y prueba del paquete exacto (2026-11-11, Claude)

**Paquete** (`frontier/package.py`, tests `tests/test_frontier_package.py`): comprueba el ROM y los ficheros de
Repolished de `reports/source-lock.json` (tamaño y SHA-256; falla con otro volcado), el `code.bin` limpio y el de
Repolished (`patch.HASHES`) y el paquete v0.5 contra su manifiesto; rechaza un árbol con cambios sin commit; ejecuta
`frontier/overlay.py --romfs <romfs de v0.5>` con la isla completa (sin overlay de desarrollo: ni warp de la Ruta 102
ni puerto de Mew) y monta `dist/oras-frontier-alpha-v0.1/` = ficheros de v0.5 + los 26 de romfs de la build y su `code.ips` encima (`code.ips`,
`DllBattle.cro`, `DllField.cro`, `.crr/static.crr`, `a/0/1/3`…), `LEEME.txt`, `manifest.json` (SHA-256 de cada
fichero, commit, hashes de entrada) y un ZIP comprobado. `package.py checkpoint SAVE` copia la partida de prueba
solo si su SHA-256 es el probado. Nada de `dist/` va a git.

**Prueba en Azahar del paquete exacto**: `frontier/probes/package/boot.sh` copia la carpeta
`luma/titles/000400000011C400` del paquete tal cual a los mods del laboratorio y comprueba que coincide con el
manifiesto (37 ficheros) antes de arrancar. Sonda GDB pasiva (`probes/package/probe.py`: solo breakpoints que
imprimen; sin escribir memoria): `FRONT START` (StartBattle 0x1e33dc, con la ruta 16438 y los works de cada
instalación) y `FRONT RESULT` (IsWin). Conductor `probes/package/circuit.py`, combates con `battle.py` (A, cambio tras
debilitado, segundo movimiento cada 8 pulsaciones). Capturas en `work/frontier/pkg/shots/`, registro
`work/frontier/pkg/circuit.log` y `circuit-run3*.out`. Equipo de la partida del usuario (Nv. 6–12, la Mansión no
sube niveles): las derrotas son lo esperado.

Partida de partida: `work/frontier/pkg/saves/p0_harbor_ticket.sav` (a49684bd…) = la de prueba de Mew
(`dist/oras-mew-checkpoint-test-v0.1`, e97f3674…, derivada de la del usuario, flags 2720 y 2729) + Ticket del Barco
(736). Guardada por el juego con el paquete en el puerto → `checkpoint_harbor.sav` (**5ddaa992…**), la de Checkpoint.

| Paso | Paquete 92c11f6 (14:11–15:00) | Paquete fec40b9 = main (20:03–21:10) |
| --- | --- | --- |
| Marinero → «Ruben ha obtenido un Pase del Frente» | sí (`c_sailor_pass.png`) | sí (`c3_s3_*.png`) |
| Ferry: menú con «Isla del Frente» → muelle (53,34) | sí (`c_ferry_menu.png`) | sí |
| Plaza (37,60) | sí | sí |
| Fábrica (ruta 1) | 2 victorias, derrota en el 3.º (racha 16437 = 2) | 4 victorias (con intercambio y «Continuar»), derrota en el 5.º |
| Torre (ruta 2) | combate, derrota | combate, derrota |
| Arena (ruta 4) | combate, derrota | combate, derrota |
| Palacio (ruta 3) | combate, derrota | combate, derrota |
| Tubo (ruta 6) | sala superada (16477 = 3 al combatir), derrota | sala superada (16477 = 2), derrota |
| Domo (ruta 5) | inscripción, rival, elección de 2, combate, derrota; salida (6,57) | igual; salida a la plaza (6,57) |
| Pirámide (ruta 7) | vestíbulo → piso 141 (12,16), entrenador, derrota → vestíbulo → plaza | igual |
| Guardar en la plaza (209, (32,58)), recargar | sí: `c_saved_plaza.sav` aa3b80cc… | sí: `c3_saved_plaza.sav` a51f8d94…, 6 Pokémon |
| Empleado del muelle → Ciudad Calagua | sí (`c_back_port.png`) | sí (`c3_back_port.png`) |

Cada combate de la tabla tiene su `FRONT START` con la ruta de la instalación y su `FRONT RESULT`; tras cada derrota la
recepción limpia el work activo (16442, 16462, 16466, 16474, 16478 y 16482 a 0 al empezar la siguiente).

**Fallo encontrado y su causa**: con el primer paquete (3da42aa) el jugador quedaba **encerrado en la sala del Domo**
(456): en (15–17,31) el sur no sacaba. El warp heredado de 365 tiene el byte 5 (transición) a 0 —solo 11 warps del
juego lo usan— y el de 517 a 2. Con una copia diagnóstica del paquete con ese byte a 2 se salió a (6,57)
(`p1_dome_in456.sav`, 4508c4ad…). Codex encontró y arregló lo mismo en paralelo (64a7299: tipo del warp 0→2 y tres
casillas de salida del FIELD_DATA, §37); mi arreglo equivalente se descartó al integrar. El paquete de `main` (fec40b9)
sale bien del Domo (tabla).

**Historia sin cambios y v0.5** (mismo paquete fec40b9):
- Entrenador: copia de la del usuario con la fixture de reserva de v0.5 (`s0_reserve.sav`, 9966ec53…) + flag 1748 a 0
  y posición (160,146) (`s1_story.sav`, aeacbea8…): «¡El Cazabichos Ricky te desafía!», Wurmple Nv. 4, victoria y
  «Ruben ha ganado 64 ₽» (`r_tr_*.png`; con el paquete 92c11f6). Después el jugador **no podía andar** (gira pero no
  avanza): efecto de la posición escrita en la partida (trampa conocida, §4 del plan), no del paquete.
- Salvaje: `s0_reserve.sav` sin mover (Ruta 102, hierba), Poochyena Nv. 2, Ascuas, victoria; guardado del juego
  `r_after_wild.sav` (d86b7b28…). EXP: participante 1105→**1133**, portador de Repartir Exp. (216) en reserva
  1105→**1119** (la mitad) con EV (+1 Ata, +1 Vel), reserva sin objeto 1105→**1105**. Como la v0.5.
- DexNav: Poochyena → «Nivel / Racha **5/0**» (`r_dexnav1.png`).

**Paquete final**: tras el commit de esta entrada se reconstruye; los 37 ficheros de `luma/` deben ser idénticos a los
probados (`work/frontier/pkg/tested-manifest-fec40b9.json`; solo cambian `LEEME.txt` y el commit del manifiesto).

**Sin probar**: consola (plan en `reports/consola-frente.md`); victoria completa de una ronda en Torre, Arena,
Palacio, Tubo, Domo y Pirámide (equipo débil); juicio de 3 turnos de la Arena; ferry de Portual con este paquete;
otros idiomas. Trampa del conductor: el marinero deambula; `circuit.py` no comprueba que el diálogo se abra (en una
pasada se habló a destiempo y acabó en el Resort): repetir el paso a mano mirando la captura.

## 39. Cerebros: infraestructura común y Anabel — F8-CEREBROS-BASE

Implementación inicial en `57df06a`; continuación de Codex tras relevo de Claude del 2026-11-11.
Al revisar `git status`, `git diff` y el último commit, el carril estaba limpio: no había cambios parciales que
completar o deshacer. Diseño aplicado: `reports/diseno/cerebros.md`, con las reservas de REPARTO (no se usa el
reparto alternativo de propuestas). Solo está activada la Torre (`brains.ENABLED`).

`frontier/brains.py` contiene los umbrales de las siete instalaciones, símbolo persistente en **16729**
(dos bits por ruta, Torre plata = 4, oro+plata = 12), jefe pendiente en **16730**, reserva Pirámide **16731** y
mensaje **16733**. Comprueba la aparición antes de elegir el rival; sustituye la presentación; al ganar concede
símbolo y 10 PB antes de la recompensa de ronda. Derrota/limpieza borran el jefe pendiente, conservando símbolos.
Entrenadores 129–142, sets 223–264, caso 9778 del script 5, texto 637 líneas 1072–1099; la Torre usa entrenadores
131/132 y sets 229–234. Los demás Cerebros quedan para sus tareas específicas.

Nativo `frontier/asm/brains_cro.s`: DllField.cro **0xf0480–0xf08c0**, 1088 bytes, con saltos en **0x94f04,
0x94f18 y 0x95044**. No pisa DexNav (0xf0400–0xf046c); quedan 1856 bytes hasta 0xf1000. SetTrainer selecciona al
Cerebro y evita la bandera de jefe de Mansión en rutas del Frente; StartBattle reconstruye los tres rivales con
los parámetros del diseño. Sin jefe pendiente conserva el equipo. En Normal, tras la victoria 19, el elector
del Frente usa el tramo 70–109 para evitar el jefe de Mansión y el entrenador 0 posterior; ruta 0 conserva retail.
Fuente de direcciones y tamaño: `brains.SITES`, `brains.assemble`, `brains.CODE` y `brains_cro.s`; tests Unicorn.

Validación de esta continuación (laboratorio del carril, puerto **24691**, artefactos locales en
`work/frontier/cerebros/base/`):

- Build completa: `source scripts/env.sh; python frontier/overlay.py --out work/frontier/cerebros/base/build`
  (`build.log`); usa v0.5 más esta build en el perfil aislado.
- Suite completa con entorno del supervisor retirado de sus tests de orquestación:
  `env -u ORCH_LANE python -m pytest -q tests`: **1188 passed, 1 skipped** (`tests-acceptance.log`, 44.33 s; también `tests-final.log`). La primera ejecución
  con ORCH_LANE heredado falló en nueve tests del propio orquestador; no fue un fallo del parche. Sin esa variable
  ya pasó antes de ampliar la cobertura (1182/1). Unicorn cubre StartBattle sin jefe en las siete rutas, además
  del elector, carga y construcción plata/oro; VM cubre umbral, presentación, premio y limpieza.
- Fixture: copia de `work/frontier/lab/f6tc_paused14.sav` (SHA256
  `eb6d1fa2ce58e3dafaec9847d36b344bfecff622cf05ba9b46f8f7ee799d4eb9`), editada con `faraway/save_event.py`
  a racha 16441=34, símbolos 16729=0 y pendiente 16730=0. Nunca se escribe la fuente.
- Anabel plata aparece: `BRAINS START` registra ruta 2, racha 34, pendiente **10** y flag retail 0.
  Presentación «Soy Anabel, Cerebro … Torre» (`anabel-intro.png`), sustituto visual femenino de ORAS.
  `frontier/probes/brains/lab_probe.py` exporta los tres PK6 de COPY antes de asistencia;
  `check_team.py work/frontier/cerebros/base/silver-team` valida checksum, orden, especie, objeto, naturaleza,
  movimientos, nivel 50, amistad 255, seis IV 24, seis EV exactos y PS completos (`silver-team.json`).
- Victoria: asistencia explícita `pv_mode='win'`, solo copias del combate (PS 1/Salpicadura del rival), heredada
  de la sonda Pirámide; no se escriben resultados, works, recompensas ni equipo guardado. `BRAINS RESULT raw=1`,
  después **16441=35, 16443=35, 16729=4, 16730=0** (`win-gdb.log`). Pausa mediante el menú real devuelve ruta a 0;
  el juego escribe `tower35-silver.sav`, SHA256
  `0102574bcc5c199bbf7ca0d1b2fb01a00639375cd7020b279e995cf4c2c60ddd`, con 58 bloques válidos y
  **símbolo 4 / racha 35** (`saved-symbol.json`).

- Persistencia: reinicio real con `tower35-silver.sav`, símbolo **4**, racha **35**, activo **1** y pendiente **0**
  al reanudar en la Torre (`reload-gdb.log`, `reload-verified.png`).
- Derrota contra Anabel oro: copia del guardado anterior editada solo a racha **69**, pendiente 0, conservando
  la plata (`gold-fixture.json`). Entrenador **132**, pendiente **18**, flag retail 0 (`gold-start-driver.log`).
  PK6 reales comprobados antes de asistencia: Raikou/Latios/Snorlax, IV 31 y resto exacto del diseño
  (`gold-team.json`, `check_team.py .../gold-team --variant gold`). Asistencia `pv_mode='loss'` solo a nuestras
  copias: resultado **0**; tras textos, ruta **0**, racha **0**, activo **0**, récord **35**, símbolo **4**,
  pendiente **0** (`gold-loss-gdb.log`, `gold-loss.png`). La derrota conserva la plata y limpia la racha.

Regresión aplicada: caso **b** de la política del usuario, porque la implementación toca DllField.cro. Una batalla
por motor propio y una normal de historia, todas con la misma build; sin circuito completo de siete instalaciones.
Fuentes de las copias y SHA256 en `regression-sources.json`; no se modifica ninguna fuente.

| Prueba en Azahar | Resultado medido | Evidencia en `work/frontier/cerebros/base/` |
| --- | --- | --- |
| Palacio, racha 7 | flag 0x40000000, entrenador 59; derrota 0; ruta/racha/activo a 0, símbolo/pendiente 0 | `palace-start-driver.log`, `palace-battle-driver.log`, `palace-gdb.log`, `palace-end.png` |
| Arena, racha 9 | flag 0x80000000, entrenador 67; derrota 0; ruta/racha/activo a 0, símbolo/pendiente 0 | `arena-start-driver.log`, `arena-battle-driver.log`, `arena-gdb.log`, `arena-end.png` |
| Tubo, sala 0 | entrenador 5, regla single; victoria 1, sala 1, activo 1, símbolo/pendiente 0 | `pike-start-driver.log`, `pike-battle-driver.log`, `pike-gdb.log`, `pike-end.png` |
| Historia, Ruta 102 | Zigzagoon Nv. 3 contra Torchic Nv. 12, daño y regreso al campo; ruta/símbolos/pendiente permanecen 0 | `story-battle.png`, `story-4.png` a `story-9.png`, `story-gdb.log` |

Palacio/Arena usan asistencia de derrota en copias; Tubo usa su sonda existente `pk_mode='win'` (rival PS 1 /
Salpicadura), y fuerza únicamente los segundos del reloj a 100005 para escoger una sala de combate single por la
puerta izquierda (`PIKECLOCK` en `pike-gdb.log`). Historia usa copia exacta de la partida original (SHA256
`a30034d1e34d6c2e752e245b23295a6fa7924d26f03153a75e351362ed2561e2`), sin editarla ni asistir el combate.
No se midió EXP ni resultado IsWin de historia: la evidencia es el combate y el regreso al campo.

Identidad de la build probada (`build-manifest.json`, SHA256):
- `code.ips`: `f64e527c6348571ca8c83780ecd23152dd144bfe108abad7e286b9cdef19c4ce`.
- `DllField.cro`: `791fef103b8bbf2a6a07587b575fd749a68e1c34251868854df6386ebcd3c750`.
- `DllBattle.cro`: `3ea58b3999e5c1335a95d67778a3d1abc920c3b7eb8f884f557d9af440017bfe`.

Aceptación F8-CEREBROS-BASE completa. `frontier/probes/brains/README.md` explica reproducción y lectura de la sonda.
Laboratorio propio parado con `azahar_lab.py reap`, sin procesos restantes; bus D-Bus privado parado y GDB
inhabilitado en el perfil (`cleanup.log`). No probado: concesión de oro en Azahar (sí VM), PB medidos en RAM,
dificultad sin asistencia, consola. Los otros seis Cerebros siguen desactivados para sus tareas específicas.

## 40. Noland — adaptador de la Fábrica (F8-CEREBRO-FABRICA, en curso)

Implementación inicial: `frontier/factory_brain.py`, contrato del diseño
`reports/diseno/cerebros.md` §2. La Fábrica activa la API común de Cerebros en
`overlay.maison_program`: ruta 1, combate 21/42 y repeticiones según símbolos,
entrenadores privados 129/130 (Noland, clase 30 Científico), presentaciones y
premios de texto 637 ya reservados en BASE. No se usa un trío fijo de Noland.

Para excluir los **seis** IDs ofrecidos sin reservar más works, el draft guarda
su semilla inicial completa de 16 bits en el work existente 16490. Antes de
SetTrainer, `brains_check` pide el trío a través del caso existente 9772:
`factory_swap` despacha a `factory_brain` cuando ruta=1 y pendiente=9/17;
tras ganar, pendiente ya es 0 y ese caso sigue ofreciendo el intercambio ordinario.
El generador reproduce los seis con las mismas reglas del draft y luego elige
otros tres del rango de la ronda, excluyendo esos IDs, Unown, especies repetidas
y objetos repetidos salvo NONE. Semilla y racha determinan el resultado al
reanudar; el reloj solo participa en un draft nuevo. Los desafíos pausados con
una versión anterior usan otro significado de 16490: terminar esos desafíos
antes de adoptar este contrato; no se afirma compatibilidad de sus seis ofertas.

`brains_cro.s` conserva los tres IDs de 16433–16435 antes del constructor retail,
que los sobrescribe por su gancho existente. Después los restaura y construye
la copia rival con archivo N/S codificado en bit 15, nivel 50, IV 15/31 para
plata/oro y habilidad normal slot 0. Conserva los EV del conjunto de Mansión
(reparto de MAKE_PARAM), convierte Return (216) en Frustration (218) en la copia
del conjunto y fija amistad 0 con `0x3b47ec`. Medido por Capstone sobre el baseline:
`0x3b47ec` empieza `ldr r0,[r0,#0xc]`, limita r1 a 255 y salta al escritor
`0x168cdc`; MAKE_PARAM ya lo llama en `0x1efaf0`.
No cambia los alquileres/IV del jugador ni el código de `patch.py`/`rental.s`.

Espacio medido con `python frontier/brains.py`: DllField.cro
**0xf0480–0xf0978, 1272 bytes**, 1672 libres antes de .rodata en 0xf1000.
Se amplía el blob de BASE dentro del mismo relleno a cero comprobado por tests;
no hay nuevos works, casos ni líneas. REPARTO no se modifica por orden del
orquestador del carril; al integrar, actualizar el extremo del blob allí
(antes 0xf08c0). La identidad de campo conserva el sustituto visual de BASE;
la apariencia de Noland todavía no está verificada en Azahar.

Evidencia inicial (2026-11-11):

- `env -u ORCH_LANE python -m pytest -q tests`: **1217 passed, 1 skipped**,
  39.40 s, `work/frontier/cerebros/factory/tests-full.log`.
- VM y referencia Python: 20 combinaciones de reloj/ronda, reproducción de seis,
  equipo válido y estable al repetir; umbrales plata/oro/revancha y máscara de
  símbolos; premio +10 una sola vez. Unicorn: conservación a través de retail,
  archivos N/S, IV independiente del 9 del jugador, movimientos y amistad.
- `python frontier/overlay.py --out work/frontier/cerebros/factory/build`:
  build completa correcta (`build.log`), script 517 15816 bytes, ZO 16608
  (límite 17248), compartido 5 21798 bytes y cueva code.bin sin crecer (2544).

**No probado todavía:** Noland en Azahar, victoria/guardado/recarga/derrota,
regresión del motor (Palacio/Arena/Tubo/historia) y plaza/puerta de Fábrica por el
cambio de overlay. Consulta y diálogo propio de derrota siguen pendientes;
BASE solo aporta cuatro líneas por instalación, ya ocupadas. Para añadirlos
el integrador debe reservar líneas o ampliar la API común, sin ocupar líneas
no registradas desde el carril. Consola no probada.

### 40.1. Textos propios, consulta y Azahar (2026-11-12, Claude)

Textos añadidos por esta tarea (commit 10fb540), sin renumerar los de BASE: segundo bloque del texto 637 desde
`line_base() + 28` (**líneas 1100–1127**, 4 por ruta: `lost`, `symbol_none`, `symbol_silver`, `symbol_gold`,
`brains.MORE_KEYS`). `brains_lost` sustituye al `WorkSet(16730, 0)` del camino de derrota (0x2210) en todos los
clones de 517: si el Cerebro de la ruta actual estaba pendiente dice su línea **una vez** antes de que se guarde la
derrota y pone 16730 = 0; sin Cerebro no hace nada más que la limpieza. Consulta: `brains.symbols_option` añade
«Símbolos» (texto 619 **línea 190**, valor **5**) antes de «No quiero nada» en la recepción; `brains_symbols` lee
16729 de la ruta (2 se lee como oro) y la recepcionista dice «Aún no tienes / Tienes … de plata / de oro»;
vuelve al menú como las opciones de información. Solo conectada en la Fábrica; las otras tareas la conectan con
una llamada. ZO 213: **16804** ≤ 17248. Reservas registradas en REPARTO (líneas, valor, extremo 0xf0978).

Azahar, carril claude (puerto 24690), v0.5 + build del carril. Partidas de `factory_fixture.py` desde
`work/frontier/lab/f6td_factory_paused1.sav` (bc3c35e7…): racha 20 `fixture20.sav` (fa94a95d…) y racha 41 con
plata `fixture41.sav` (7ee309db…). Sonda `lab_probe.py --directory work/frontier/cerebros/factory`, asistencia
solo en copias de combate. Evidencia en `work/frontier/cerebros/factory/` (no en Git).

| Prueba | Build | Resultado medido | Evidencia |
| --- | --- | --- | --- |
| Plata, racha 20 | 4f1976a | «Soy Noland, Cerebro del Frente de la Fábrica Batalla», modelo de científico; «¡El Científico Noland te desafía!»; entrenador 129; PK6 Octillery/Grumpig/Persian, IV 15, amistad 0, conjunto/EV = generador (`check_team.py --factory-fixture`, rc 0); victoria raw 1; rival registrado 16433–16435 = 191/202/207 | `shots/silver-*.png`, `silver-team.json`, `run1/`, `run2/gdb.log` |
| Guardado y recarga | 4f1976a | ronda nueva sin intercambio tras el 21; combate 22 ganado e intercambio ordinario; Pausar → `silver-paused23.sav` (bf1a641c…): símbolos **1**, PB **0 → 14** (10 + 4 de ronda), racha/récord 22, equipo intacto (hash 2d97e5df…). Recarga: reanuda en el 23 con entrenador 101, 16729 = 1, 16730 = 0 | `run2/`, `run3/gdb.log`, `shots/reload-battle23.png` |
| Oro, racha 41: equipo y derrota | 4f1976a | «Has vuelto a llegar hasta mí…», entrenador 130, Nidoking/Politoed/Walrein IV 31 (`gold-team.json`, rc 0); derrota raw 0 → ruta/racha/activo/pendiente 0, símbolo plata conservado, PB 0, equipo intacto (`gold-after-loss.sav` 1f815c63…) | `run3/`, `shots/gold/`, `shots/loss/` |
| Consulta | 10fb540 | «Símbolos» en el menú; «Aún no tienes…» (símbolos 0), «…de plata» (1), «…de oro» (3); vuelve al menú | `shots/v2/menu.png`, `consult-none/silver/gold.png` |
| Oro ganado | 10fb540 | victoria raw 1; «¡Has obtenido el Símbolo Conocimiento de oro! Recibes 10 PB más.»; ronda nueva sin intercambio; Pausar → `gold-won-paused43.sav` (191ea5bc…): símbolos **3**, PB **0 → 15** (10 + 5), racha/récord 42 | `shots/v2/gw*.png`, `run4/gdb.log` |
| Derrota de plata | 10fb540 | «¡Buen combate! Pero aún te queda mucho por aprender. Te espero de nuevo en la Fábrica Batalla.» una vez; después ruta/racha/activo/pendiente 0, símbolos 0, PB 0 (`silver-after-loss.sav` 464abd9f…) | `shots/v2/lost-*.png`, `run5/gdb.log` |

La línea de plata ganada no se capturó (se pasó con A en la primera sesión); su premio sí: PB +10 y símbolo
en el guardado. Regresión con la build 10fb540 (DllField 3122308f…, DllBattle 3ea58b39…, code.ips f64e527c…),
caso **b** (DllField y la ruta común de derrota) y **c** (overlay.py), en `regression/`:

| Prueba | Resultado |
| --- | --- |
| Palacio (`pa_paused7.sav`, 012e718b…) | marca 0x40000000, entrenador 30, derrota raw 0, ruta/racha/activo 0, sin línea ni símbolo (`palace-gdb.log`, `palace-end.png`) |
| Arena (`ar_paused9.sav`, 093ed149…) | marca 0x80000000, entrenador 49, derrota raw 0, limpieza a 0, sin línea ni símbolo (`arena-gdb.log`, `arena-end.png`) |
| Tubo (`pk_cx_lastroom_fixture.sav`, 1477e9ee…) | ruta 6, sala 14, el segundo entra con PS 90 conservados; victoria raw 1; racha 13 → 14, activo 1, «¿Qué puerta eliges?» (`pike-gdb.log`, `pike-end.png`) |
| Historia (`work/frontier/pkg/saves/s0_reserve.sav`, 9966ec53…) | Wurmple salvaje Nv. 3 contra Torchic Nv. 12, sin asistencia, derrotado y regreso al campo (`story-*.png`); works no medidos (la sonda no pasa por ese camino) |
| Plaza | desde la recepción de 213 salida a la plaza y reentrada (`plaza-exit.png`, `plaza-reenter.png`) |

**No probado:** consola; oro en Azahar con la build 4f1976a (sí con 10fb540); revancha 63 (VM); PB medidos en
RAM durante el combate (solo en el guardado); dificultad real sin asistencia; inglés en el juego.

## 41. Anabel — Cerebro de la Torre (F8-CEREBRO-TORRE)

BASE (§39) ya entregó a Anabel: elegibilidad 35/70 y repeticiones, equipos exactos plata/oro (anexo de
`reports/diseno/cerebros.md` §7), nombre y clase (Entrenadora Guay, clase 9; modelo de campo/combate de
sustitución femenino de ORAS, ver §39), textos intro/plata/oro/victoria (texto 637), derrota (bloque 1100–1127,
§40) y premio (+10 PB, `brains_won`). Esta tarea añade lo que faltaba a la Torre y la evidencia de oro:

- `frontier/tower.py` `tower_program`: «Símbolos» en el menú de recepción de la Torre (texto 619 línea
  `factory.LINE_SYMBOLS` = 190, valor `brains.MENU_SYMBOLS` = 5, antes de «Nada»), con `brains.symbols_option`
  como la Fábrica. Solo cambia el script de la zona 329: Palacio/Arena/Tubo comparten `facility_program`, pero la
  opción se añade en `tower_program`, fuera de él. Sin reservas nuevas (línea, valor y casos ya en REPARTO por §40).
- `tests/test_frontier_brain_tower.py` (VM sobre el script de la Torre construido): desafío completo de 0 a 174
  (Anabel en 35 plata, 70/105/140 oro; símbolos 0→1→3; +10 PB por victoria; líneas en orden), derrota ante oro
  conserva la plata y una racha nueva no repite la plata, derrota ante plata sin premio y revancha, plata con
  ambos símbolos conserva el oro, reanudar repite la elegibilidad sin premio, otras rutas sin Anabel, consulta
  0/1/2/3 (2 se lee como oro) y el menú y su despacho. `test_frontier_tower.py` acepta la nueva entrada.

Azahar (carril 24690, build `python frontier/overlay.py --out work/frontier/cerebros/tower/build` con f113c4d;
code.ips f64e527c… igual que la de §40: no cambia el motor, política del usuario **caso a**, solo la Torre).
Evidencia en `work/frontier/cerebros/tower/` (no en Git). Asistencia `pv_mode='win'` solo en las copias del
rival, tras exportar sus PK6.

| Prueba | Resultado medido | Evidencia |
| --- | --- | --- |
| Fixture | copia de `work/frontier/brains/t34.sav` (0fc1c711…, zona 329, racha 34) editada con `faraway/save_event.py` a 16441 = 16443 = 69, 16729 = 4 (plata), 16730 = 0 → `t69-silver.sav` (7a3a5ea8…) | `saved-gold.json` |
| Consulta con plata | menú «Combatir / Quiero información / Cambiar la melodía / Símbolos»; «Tienes el Símbolo Habilidad de plata de la Torre Batalla.» y vuelta al menú | `menu.png`, `consult-silver.png` |
| Oro, racha 69 | «Has vuelto a llegar hasta mí. Soy Anabel. ¡Esta vez combatiré con todas mis fuerzas!»; «¡La Entrenadora Guay Anabel te desafía!»; `BRAINS START` entrenador **132**, pendiente **18**, flag retail 0; PK6 Raikou/Latios/Snorlax IV 31, EV/naturaleza/objeto/movimientos/amistad 255 exactos (`check_team.py … --variant gold`, rc 0) | `b2.png`, `b3.png`, `g1.png`, `gold-team.json`, `gold-win-gdb.log` |
| Oro ganado | `BRAINS RESULT raw=1`; «¡Has obtenido el Símbolo Habilidad de oro! Recibes 10 PB más.»; RAM 16729 = **12**, racha/récord 70; «Ruben ha obtenido 10 PB» de ronda; «El próximo combate será el número 71» | `gold-won-line.png`, `g3.png`, `g4.png` |
| Guardado | Pausar → `tower70-gold.sav` (8bb678f9…): símbolos **12** (plata + oro de la ruta 2), racha/récord 70, activo 1, pendiente 0, PB **1 → 21** (10 del Cerebro + 10 de ronda), equipo intacto (hash 12355b31… igual a la fixture) | `saved-gold.json` |
| Recarga | reinicio con `tower70-gold.sav`: «Tienes el Símbolo Habilidad de oro de la Torre Batalla.» | `consult-gold.png`, `reload-gdb.log` |

Plata ganada, guardado/recarga de plata y derrota contra oro: evidencia de BASE (§39), sin cambios que la
invaliden (el motor y las rutinas de Cerebro son las mismas; esta tarea solo añade la opción del menú).
Laboratorio parado (`reap`, `use_gdbstub=false`).

Desviaciones conocidas: la línea de victoria de una revancha de plata con oro ya obtenido dice «¡Has obtenido el
Símbolo Habilidad de plata!» aunque el oro se conserva (VM); textos de la Mansión en la recepción (§F6).
**No probado:** consola; revanchas 105/140 en Azahar (VM sí); consulta «Aún no…» en Azahar (VM sí; la línea
de la Fábrica equivalente sí se vio en §40.1); dificultad real sin asistencia; inglés en el juego.

## 42. Spenser — Cerebro del Palacio (F8-CEREBRO-PALACIO)

Implementación heredada `0a79d21` (Claude), aceptación completada por Codex el 2026-11-12. Relevo:
`git status --short` y `git diff` vacíos; el último commit contenía código/tests, sin entrada de bitácora ni
aceptación. Se conserva el cambio y se completa aquí; no hubo cambios parciales que deshacer.

`brains.ENABLED` incorpora `palace`, con sus seis conjuntos del anexo de `reports/diseno/cerebros.md` §7.
Entrenadores privados **133/134**, conjuntos **235–240**, IV **16/31**, EV/movimientos/naturaleza/objeto exactos.
`palace_program` conecta `brains.symbols_option` al menú de la zona 340. API común: plata en S=20, oro en
S=41; con ambos símbolos, 21/42/63…; +10 PB una vez al ganar, símbolo en 16729 bits 4–5, limpieza de pendiente
16730 al resolver el combate. Sin reservas nuevas ni cambios de motor/isla/REPARTO/tasks.json.
La presentación usa **Médium (clase 31)**: joven psíquico masculino de ORAS en campo y combate, sustituto
explícito del anciano Spenser; no se incorpora un modelo de Esmeralda. Nombre real de combate verificado:
«¡El Médium Spenser te desafía!» (`gold-name.png`). Se mantienen Palacio B/C y su filtro por naturaleza para
el jugador; la IA rival sigue siendo la habitual del juego, no se declara IA rival por naturaleza.

Tests del commit heredado: `tests/test_frontier_brain_palace.py` ejecuta el script generado en VM, cubriendo
umbrales/racha 0–104, plata/oro/repeticiones, derrota sin premio, símbolos ajenos, pausa/reanudación y menú/consulta
0/1/2/3; comprueba las tablas completas de equipos/EV/IV y textos ES/EN. La suite común cubre persistencia y no
duplicación de premios. `check_team.py --facility palace` añade cotejo de PK6 reales antes de asistencia, sin
cambiar su opción por defecto Torre ni el modo Fábrica.

Evidencia local: `work/frontier/cerebros/palace/` (no en Git). Build completa:
`python frontier/overlay.py --out work/frontier/cerebros/palace/build`, `build.log`; zona 340 ZO **16724** bytes
(<17248), script **15932**; `build-manifest.json`. SHA256 de motor:

- code.ips: `f64e527c6348571ca8c83780ecd23152dd144bfe108abad7e286b9cdef19c4ce`.
- DllField.cro: `a0b1803991ae5f9362f7834213d333481747c26c67adc63c60c256ba93aca99a`.
- DllBattle.cro: `3ea58b3999e5c1335a95d67778a3d1abc920c3b7eb8f884f557d9af440017bfe`.

Azahar del carril **24691**, v0.5 + overlay anterior. Política de regresión **caso a**: solo Palacio;
no se cambia la construcción común ni la isla aunque se genere la overlay completa. Asistencia declarada:
`pv_mode='win'/'loss'` solo debilita copias de combate (PS 1 y Salpicadura), nunca resultados, works ni premios.
Las órdenes de combate permanecen automáticas; las teclas avanzan textos y selección previa.

| Prueba | Resultado medido | Fuente |
| --- | --- | --- |
| Fixture plata | copia de `work/frontier/lab/pa_paused7.sav` (012e718b…) pausada en zona 340; 16462=1, racha/récord editados a 20, símbolos/pendiente 0; salida `p20.sav` SHA256 73569503… | `fixture.json`, README de la sonda |
| Plata | intro propia; entrenador **133**, racha 20, pendiente **11**, flags **0x40000000**; Crobat/Slaking/Lapras exactos, checksum PK6 y todos los campos fijos validados antes de asistencia | `pre-battle.png`, `silver-win-gdb.log`, `silver-team.json`; `check_team.py …/silver-team --facility palace` rc 0 |
| Victoria | `raw=1`; después símbolo **16**, pendiente **0**, racha **21**; ronda concede 5 PB | `silver-win-gdb.log`, `silver-result.png`, `next.png` |
| Pausa/guardado | `p21-silver.sav` SHA256 **d9307afd67c3a8d739363bd790b118e0a4d3229c19089081d4acf6679bfbd325**: racha/récord 21, activo 1, símbolo 16, pendiente 0; PB **4→19** = 10 del Cerebro + 5 de ronda | `p21-silver.json`, `initial.json` |
| Equipo y cajas | bytes idénticos antes/después de victoria/guardado: equipo 0x14200–0x1481c SHA256 12355b31…; cajas, bloque 56 (0x33000, 0x34ad0 bytes), SHA256 4b00b99e…; checksums de guardados válidos | `snapshot.py`, `initial.json`, `p21-silver.json`; `scripts/save_fixture.blocks` |
| Recarga | reinicio desde ese archivo; menú «Símbolos» muestra «Tienes el Símbolo Ánimo de plata de el Palacio Batalla.» | `consult-menu.png`, `consult-silver.png`, `reload-gdb.log` |
| Oro | copia de la plata guardada, racha/récord 41, pendiente/ruta 0; `p41-silver.sav` SHA256 0ea8c51c…; intro oro, nombre real; entrenador **134**, pendiente **19**, flag **0x40000000**; Arcanine/Slaking/Suicune exactos IV 31 | `gold-fixture.json`, `gold-intro.png`, `gold-name.png`, `gold-team.json`; `check_team.py …/gold-team --facility palace --variant gold` rc 0 |
| Derrota oro | `raw=0`, texto de derrota propio; después ruta/racha/activo/pendiente **0**, símbolo **16** conservado, récord **41**; regreso normal a recepción | `retry-result.png`, `retry-field.png`, `gold-loss-gdb.log` |
| Cierre | `azahar_lab.py reap` desde el conductor que arrancó el lab; `own_processes()` vacío, GDB deshabilitado | `cleanup.log` |

La primera toma de estado final por GDB se atascó; se repitió oro/derrota con el mismo fixture/build en un
conductor interactivo, que registró la limpieza y ejecutó reap. No fue necesario cambiar el juego.
Suite completa: `source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests`: **1259 passed, 1 skipped**
(`tests-final.log`, 42.83 s; repetición final en `tests-acceptance.log`). La primera ejecución con ORCH_LANE
heredado dio los nueve fallos de tests del supervisor ya descritos en §39; sin esa variable, todos pasan.

Límites: no probado en consola ni inglés en juego; victoria de oro/revanchas solo en VM, no Azahar;
no capturada la línea de premio de plata (sí símbolo y PB guardados); tras derrota la limpieza se mide en RAM,
no se hizo un nuevo guardado. Textos comunes conservan la contracción incorrecta «de el Palacio» y textos de
Mansión de la recepción; no se extiende esta tarea a esa revisión editorial ni a un modelo de anciano.

## 43. F8-CEREBRO-ARENA — Greta (2026-11-12)

Greta usa la infraestructura de Cerebros BASE en la ruta 4, zona 457: combate 28 sin símbolo,
56 con plata, y múltiplos de 28 tras obtener ambos. `frontier/brains.py` habilita Arena y añade
los seis sets exactos de `reports/diseno/cerebros.md` §7 (241–246, entrenadores 135/136).
Plata IV20: Heracross/Umbreon/Shedinja; oro IV31: Umbreon/Gengar/Breloom. Objetos, naturalezas,
movimientos y EV individuales se aplican con el constructor BASE. La recepción incorpora «Símbolos».
No requiere nuevas reservas ni modificar REPARTO. Nombre Greta y clase 63 (Luchadora) en combate;
sustitución visual: mujer rubia con traje de artes marciales azul de ORAS, sin modelo propio de Greta.

El motor B de Arena se conserva: bit31, cambio prohibido, juicio por Cuerpo a tres turnos;
Mente/Técnica siguen fuera. La construcción genera los mismos símbolos e instrucciones nativas
con Arena habilitada o deshabilitada: solo difieren las dos filas privadas Greta de `brain_table`
(0xf0898–0xf08cf; `native-data-only.json`). No cambia ASM, patch.py, lógica CRO ni construcción
común. Regresión del usuario caso a: únicamente Arena en Azahar.

Artefactos locales en `work/frontier/cerebros/arena/` (sin subir partidas ni binarios):

| Comprobación | Resultado medido | Fuente |
| --- | --- | --- |
| Script | 22 tests propios: umbrales vecinos, plata/oro/revanchas, pérdida, pausa, consulta, equipos y no duplicar premio | `tests/test_frontier_brain_arena.py` |
| Construcción | overlay completa correcta, ZO Arena 16724 ≤ 17248 | `build.log`, `build-manifest.json` |
| Fixture plata | fuente pausada `work/frontier/lab/ar_paused9.sav`, SHA256 093ed149…; copia S=27, récord 27, símbolo/pendiente 0 | `fixture.json`, `s27.sav`; reproducción en `frontier/probes/brains/README.md` |
| Greta plata | intro propia, entrenador 135, pendiente 12, flag 0x80000000; Heracross/Umbreon/Shedinja exactos antes de asistencia | `greta-intro.png`, `silver-team.json`; `check_team.py …/silver-team --facility arena` rc 0 |
| Reglas Arena | menú impide cambiar a otro participante; juicios a edades [3,3], [6,3], [9,3]; último empate elimina ambos, aún quedan reservas del jugador | `switch-attempt.png`, `silver-gdb.log` |
| Victoria y premio | raw=1; línea «¡Has obtenido el Símbolo Agallas de plata! Recibes 10 PB más.»; S=28, símbolo64, pendiente0 | `silver-result.png`, `silver-gdb.log` |
| Guardado | pausa guarda S/récord28, activo1, ruta4, símbolo64, pendiente0, PB2→14 (10 Cerebro + 2 ronda); checksums válidos y hashes equipo/cajas idénticos a inscripción | `enrolled.json`, `s28-silver.json`; SHA256 guardado 2a31f499… |
| Recarga | reinicio desde ese guardado sin editar; consulta «Tienes el Símbolo Agallas de plata de la Arena Batalla.» | `consult-silver.png`, `reload-gdb.log` |

Asistencia explícita de laboratorio: sonda de Cerebros exporta los PK6 **antes** de modificar copias de
combate; `judge-win.gdb`, derivada de `frontier/lab_arena_probe.py`, pone Salpicadura a ambos y conserva
PS iniciales hasta el tercer turno; entonces deja rival a 1 PS y jugador completo. Shedinja queda 1/1
(empate). No se escriben resultado, works, símbolos, premios ni equipo guardado. Para la derrota se usa
la misma sonda con modo `loss`, que invierte los PS al tercer turno. Reproducción en README de sondas.

Oro desde `s55-silver.sav`, copia del guardado plata con S/récord55 y pendiente/ruta0:
intro «Soy Greta. ¡Esta vez combatiré con todas mis fuerzas!» (`gold-intro.png`), entrenador136,
pendiente20 y flag0x80000000 (`gold-loss-gdb.log`). `check_team.py …/gold-team --facility arena --variant gold`
termina con rc0 (`gold-team.json`). Se ejecutan tres juicios, edades [3,3], [3,6], [3,9]; todos eliminan
al jugador con 1 PS frente a Umbreon 202/202. Resultado raw0, texto de derrota propio (`gold-loss.png`),
regreso a recepción (`gold-return.png`) y lectura posterior GDB: ruta/racha/activo/pendiente0,
récord55, símbolo64. No se otorga símbolo oro ni bonus al perder.

Suite final `source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests`: **1281 passed,
1 skipped, 47.63 s** (`tests-final.log`; primera suite verde en `tests-full.log`). Se aísla ORCH_LANE
por los tests del supervisor descritos en §39. Una ejecución intermedia falló por un alias local de
la fixture de tests al corregir comentarios copiados de Palacio; corregido y repetida la suite completa.

No probado: consola, inglés en juego, dificultad sin asistencia, victoria oro y revanchas en Azahar
(sí VM). No capturada la presentación de nombre/clase en la pantalla inicial del combate; sí datos de
entrenador/nombre generados y las introducciones de campo. El juicio sigue limitado a Cuerpo según diseño.

Guardado real tras derrota mediante menú X→Guardar: `gold-loss-saved.sav` SHA256 a52ee68b…,
works de limpieza idénticos a RAM, PB14 conservados. `scripts.save_fixture.blocks` valida los checksums
de fuente, plata y derrota; equipo y cajas de la derrota son idénticos byte a byte a la fuente original
(sha de sus regiones en `gold-loss-saved.json`). La fuente sigue con SHA256 093ed149….
Laboratorio 24691 parado con `azahar_lab.py reap` desde su conductor persistente:
`cleanup.log` registra `own_processes=[]`, GDB deshabilitado y bus D-Bus privado cerrado.


## 44. Tucker — Cerebro del Domo (F8-CEREBRO-DOMO)

La ruta5 usa BASE con Tucker en las finales de los torneos5/10 (S19/39), con los umbrales y
revanchas de `brains.due`. `brains_check` convierte S+1 a torneos únicamente si S%4=3; las otras
rondas no convocan al Cerebro. Entrenadores137/138, clase ORAS10 («Entrenador Guay»), nombre Tucker:
se usa el modelo masculino de esa clase, sin modelo propio de Esmeralda.

`dome_round` reconoce pendiente13/21 y prepara el trío fijo de los sets247–249/250–252 antes del
preview. Las seis líneas privadas de especie/objeto se añaden al final de los textos de Cerebros
(1128–1133), sin desplazar líneas compartidas existentes. Volver con B conserva ese trío.
El jugador inscribe tres, elige dos, y el rival selecciona dos distintos de sus tres al azar,
en orden aleatorio, como el Domo anterior. Desviación ya declarada: no hay selección estratégica
contra el jugador. El constructor nativo de Tucker exige dos miembros, valida índices distintos
del trío debido y aplica a cada miembro el set/IV/EV exacto de su fila. No sustituye la pareja por
los dos primeros sets. La consulta «Símbolos» usa la rutina BASE; premio10 PB una sola vez,
símbolo persistente. Al perder/retirarse y al devolver control a recepción limpia los dos slots
del jugador, trío y pareja rival temporales; mantiene TEAM para una pausa y los símbolos/récord.

Medidas de la build completa `python frontier/overlay.py --out work/frontier/cerebros/dome/build`
(`build.log`, `static.json`): ZO Domo16804≤17248 bytes; bloque nativo Cerebros1396 bytes,
final0xf09f4, quedan1548 hasta0xf1000. El integrador debe actualizar esa ampliación y las seis
líneas en REPARTO; el brief paralelo prohíbe cambiarlo en este carril. No se asignan nuevos works,
casos GlobalCall ni sets fuera de las reservas de Tucker. Hashes `build-manifest.json`:

- code.ips: `f64e527c6348571ca8c83780ecd23152dd144bfe108abad7e286b9cdef19c4ce`.
- DllField.cro: `a9d3a03febea7c65b7e2ce3803104441f0b3de2cc03b4bf6f297a5f930bb82c0`.
- DllBattle.cro: `3ea58b3999e5c1335a95d67778a3d1abc920c3b7eb8f884f557d9af440017bfe`.

31 tests nuevos en `tests/test_frontier_brain_dome.py`: VM (plata, oro, derrota, premios no duplicados,
revanchas, consulta, B en preview, retorno/limpieza), constructor Unicorn (las seis parejas ordenadas
por variante, EV/IV/set exactos, rechazar pareja repetida/fuera del trío o recuento incorrecto).
Suite completa: **1312 passed, 1 skipped, 44.52 s** en `tests-acceptance.log` (hito1:44.24 s,
`tests-m1.log`). Se desactiva ORCH_LANE solo para los tests del supervisor (§39).

### 44.1. Aceptación Azahar

Artefactos locales, sin partidas/binarios comerciales en Git: `work/frontier/cerebros/dome/`.
Fixture plata `s19.sav`, SHA2564069a630… desde `work/frontier/dome/room/paused-456.sav`
(SHA256ec03f883… completo en `fixture.json`), editando solo la copia: S/récord19, activo1,
ruta/símbolos/pendiente0, otras instalaciones inactivas. Recepción zona456. Todos los checksums válidos.

| Caso ejecutado | Resultado medido | Evidencia local |
|---|---|---|
| Presentación y preview plata | Tucker, entrenador137, pendiente13; preview Swampert/Cinta Focus, Salamence/Baya Ziuela, Charizard/Hierba Blanca; solo dos miembros por lado | `tucker-intro.png`, `preview-team.png`, `battle.png`, `silver.gdb.log` |
| Equipo plata | Swampert y Charizard, IV20; objeto/naturaleza/movimientos/EV/amistad255/nivel50 exactos; exportados antes de asistencia | `check_team.py …/dome --facility dome` rc0, `team-silver.json` |
| Victoria | IsWin raw1, S19→20, símbolo256, pendiente0; se continuó una ronda ordinaria más (raw1, S21) antes de pausar | `silver.gdb.log`, `normal-result.png` |
| Guardado y recarga | `silver-paused.sav` SHA256b5bfffe0…: S/récord21, activo1, símbolo256, pendiente0, PB0→13=bonus10+torneo3; reinicio y consulta real muestran plata | `silver-save.json`, `consult-silver.png` |
| Preview oro y B | Copia del guardado plata, S/récord39, ruta/pendiente0: trío Swampert/Restos, Metagross/Garra Rápida, Latias/Baya Atania, idéntico tras volver con B | `gold-fixture.json`, `gold-trio-visible.png` |
| Equipo oro | entrenador138, pendiente21; Latias y Metagross IV31, parámetros exactos, dos miembros | `check_team.py …/dome --facility dome --variant gold` rc0, `team-gold.json`, `gold.gdb.log` |
| Derrota oro | IsWin raw0; recepción: ruta/racha/activo/pendiente0, récord39, plata256, siete selecciones temporales0 | `gold-reception.png`, lectura posterior en `gold.gdb.log` |
| Guardado automático derrota | `gold-loss.sav` SHA256cda68076…: S/activo/pendiente0, récord39, plata256, PB13, parámetros de equipo iguales a fixture; ruta5 guardada antes del retorno retail a0 (RAM0 comprobado) | `gold-loss-save.json` |

Asistencia de laboratorio declarada: `pv_mode=win` en plata, `loss` en oro, únicamente PS y movimientos
(Salpicadura) de copias de combate cliente/servidor. Nunca modifica resultados, works, premios ni equipo
guardado. `check_team.py` valida PK6 capturados antes de asistir; los PK6 de plata fueron sobrescritos
al reiniciar oro, permanece el JSON de validación y el log de exportación. Dificultad sin asistencia
no probada. Tras plata, cajas idénticas; los seis Pokémon decodificados son iguales salvo byte0xcc
del sexto (1→2) y su checksum (`silver-party-diff.json`). Ese byte es la intensidad del recuerdo del
entrenador original según [PKHeX PK6.cs](https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/PKM/PK6.cs);
no se atribuye aquí su causa. Los datos de
combate inspeccionados (especie, objeto, EXP, EV, nivel, PS) coinciden en los seis, sin Salpicadura ni PS1
persistentes. La derrota conserva esos parámetros (`gold-loss-save.json`).

### 44.2. Regresión del motor y cierre

Política usuario caso b: un combate por motor propio y uno de historia, con la misma build anterior.
Fuentes y SHA256 completos en `regression-sources.json`; solo se cargaron copias de laboratorio.

| Instalación | Combate ejecutado | Evidencia local |
|---|---|---|
| Palacio | entrenador37, ruta3, S7, flag0x40000000, pendiente/símbolo0; IA automática, derrota raw0 y recepción | `palace.gdb.log`, `palace-return.png` |
| Arena | entrenador54, ruta4, S9, flag0x80000000, pendiente/símbolo0; tres Pokémon, derrota raw0 y recepción | `arena.gdb.log`, `arena-return.png` |
| Tubo | entrenador1, ruta6, sala sencilla a S0, flag0; equipo3 contra3, victoria raw1 y S1, pendiente/símbolo0 | `pike.gdb.log`, `pike-battle.png`, `pike-finish.png` |
| Historia | Ruta102, Torchic contra Zigzagoon salvaje, victoria con Arañazo sin asistencia; regreso al campo y guardado manual, EXP1105→1121, ruta/símbolos/pendiente0, 58 checksums válidos | `story.gdb.log`, `story-battle.png`, `story-saved.png`, `story-save.json` |

Asistencia de regresión: PS1/Salpicadura solo en copias del jugador para Palacio/Arena; del rival para
Tubo. Tubo usa además su sonda existente para forzar una sala de combate sencillo por el reloj; no se
escribe el resultado ni la racha. Historia usa modo normal, sin PS/movimientos alterados.
Guardado historia `story-after.sav` SHA256bfa6bbbb7ba4dd600c281be44273735eb1f0e717cc9a12c14e735e8bfad64429.
No se amplía a las otras instalaciones ni al recorrido de paquete: no cambian isla/construcción común.

Lab24691 cerrado con `python scripts/azahar_lab.py reap` desde su conductor propietario; `cleanup.log`
registra `own_processes=[]`, sesión ausente, GDB deshabilitado y bus D-Bus privado cerrado.
El conductor también termina. No se han tocado REPARTO/tasks.json ni hecho push.
No probado: consola, inglés en juego, concesión oro y revanchas en Azahar (VM sí), dificultad sin asistencia.

## 45. Cerebro del Tubo — Lucy (F8-CEREBRO-TUBO, aceptación parcial)

`95a8aaa` habilita Lucy y sus dos tríos privados en `brains.py`; `pike_rooms_loop` consulta
`brains_check` antes del sorteo de cada sala. S=27/139 produce plata/oro; después de ambos símbolos
se aplican las revanchas BASE (salas28,140,196,252…). El jefe pone PIKE_WILD=0, rango Normal,
tres rivales y conserva PS/PP/estado v2. Solo AddWinCount cuenta la sala ganada. Recepción añade
«Símbolos». Clase13 Bruja y modelo ORAS de pelo oscuro sustituyen el aspecto de Esmeralda.
Se conserva la desviación de v2: no se reproduce la curación parcial exacta previa a Lucy.

### Comprobaciones y límite encontrado

Artefactos locales en `work/frontier/cerebros/pike/` (no distribuir PK6, partidas ni build):

| Prueba | Resultado y fuente |
| --- | --- |
| Suite hito1 | 1329 passed, 1 skipped,44.90s; `tests-m1.log` |
| Script | 17 tests específicos `tests/test_frontier_brain_pike.py`: umbrales vecinos, símbolos, revanchas, pausa, premio único, derrota, estado v2, llegada desde sala no bélica y consulta |
| Build | `build.log`, `static.json`: ZO17112<=17248; bloque1396 bytes hasta0xf09f4. Comparación con Lucy deshabilitada: mismas instrucciones/símbolos, solo dos filas privadas cambian |
| Fixture válida | `s27-paused.sav`, copia editada de `work/frontier/lab/pa_paused7.sav`, SHA256 fuente012e718ba50c3dbab606987958a3351aec79840025e385e25d73ed3c98e48c7c; `fixture.json` |
| Plata en Azahar | trainer139, flag0, pendiente14, S27; victoria asistida raw1; después S28,activo1,símbolo1024,pendiente0. `silver.gdb.log` |
| Estado arrastrado | Hooks pasivos SET_HP0x14f450/SET_SICK0x14f814 llamados por pike_build restauran PS60/70/80 y estados0/0/1; pike_pp+32 registra cuatro PP5 por miembro. Entrada del primero confirma PS60/PP5. `retention.gdb`, `silver.gdb.log` |
| Equipo rival real | Tres PK6 exportados antes de asistencia, `silver-team/`, `team-silver-measured.json`; Seviper y Milotic coinciden íntegramente. Shuckle difiere en un EV; `check-silver.log` falla deliberadamente y no se ha relajado el verificador |

**Bloqueo de aceptación:** el anexo §7 exige para Shuckle plata EV252,0,0,0,106,252
(total610). El escritor nativo0x3b4b64 utilizado por BASE limita a510, como documenta
`frontier/asm/brains.s`: la copia real queda252,0,0,0,106,152. Se conservan los610 solicitados
en la tabla del parche; no se ha alterado silenciosamente el diseño ni declarado equipo exacto en ejecución.
Hace falta decidir si corregir el anexo a152 de Defensa Especial (total510), o exigir una excepción de motor
que admita610. La segunda opción cambia la infraestructura común y requiere regresión de motor caso b.
La suite de script comprueba la tabla solicitada y por sí sola no detecta este límite de ejecución.

La asistencia solo modifica PS/movimientos de copias de combate (enemigos1PS/Splash); no escribe resultados,
works, símbolos ni PB. No prueba dificultad. `PIKE RETAIN status` lee una dirección no validada para estados;
la evidencia de parálisis es el argumento1 de SET_SICK, no ese campo de la sonda.
La primera fixture `pk_saved_458.sav` no estaba pausada correctamente: al cargar, retail detectó interrupción
y reinició ACTIVE/racha; no usarla para esta prueba. La fuente pausada de Palacio mantiene los demás
activos a0 y permite entrar al Tubo con S27. No se han tocado inputs ni la partida fuente.
Política de regresión caso a: solo Tubo, sin cambios de motor/isla/construcción común.

Persistencia comprobada: se aceptó continuar después de Lucy antes de seleccionar Pausar, por lo que
el guardado real se hizo en S30 tras una sala vacía y un combate normal adicional (asistido raw1).
`silver-paused.sav` SHA256d47e48af5a3a189f24385842c88884129bbb28421fc5ba48d96400fcac28c38d:
símbolo1024,pendiente0,S/récord30,activo1; PB4→15 (+10 jefe y +1 segunda ronda).
`saved-silver.json` valida checksums, equipo0x14200..0x1481c y cajas0x33000..0x67ad0 idénticos a la
fixture inicial. Reinicio real con este archivo y consulta «Símbolos»: «Tienes el Símbolo Suerte de plata»
(`silver-reloaded-symbol.png`). El avance único de Lucy se midió previamente en RAM a S28, no se infiere
solo del guardado posterior. Suite hito2:1329 passed,1 skipped,48.27s (`tests-m2.log`).

**Pendiente/no probado:** combate oro o derrota de jefe en Azahar (sí VM), consola y fidelidad completa
EV de Shuckle. `s139-silver.sav`/`gold-fixture.json` están preparados para retomar oro desde139 con
plata1024 y estado v2 controlado; no se han ejecutado. Laboratorio del carril cerrado al terminar.

## 46. Cerebro del Tubo — Lucy: EV de Shuckle y aceptación completa (F8-CEREBRO-TUBO)

**Decisión EV (tomada por el agente, reversible; revisable por el usuario).** El Shuckle de plata de Esmeralda
lleva EV 252,0,0,0,106,252 (610). ORAS no admite más de 510: el escritor nativo `0x3b4b64` que usa el
constructor de Cerebros (`frontier/asm/brains_cro.s`) recorta el último valor, y el PK6 real del hito 2 (§45) ya
salía 252,0,0,0,106,**152**. Se ha alineado la tabla con lo que construye el juego (`frontier/brains.py`,
DefE 152, total 510) en lugar de ampliar el motor para admitir 610, que exigiría tocar infraestructura común
y regresión caso b para unos 12 puntos de Def. Esp. a nivel 50. El anexo de diseño conserva la fila de
Esmeralda con una nota. Nuevo test `test_brain_evs_are_legal_in_oras`: ningún set de Cerebro supera 252
por estadística ni 510 en total. Si el usuario prefiere los 610, hay que cambiar el escritor de EV
(motor, caso b) y revertir esta fila.

Cambio solo de datos privados de Lucy (no de instrucciones, works, isla ni construcción común):
política de regresión caso a, solo Tubo. Build `python frontier/overlay.py --out work/frontier/cerebros/pike/build`
(`build.log`). Artefactos en `work/frontier/cerebros/pike/` del carril claude (no distribuir).

| Prueba | Resultado y fuente |
| --- | --- |
| Suite | `env -u ORCH_LANE python -m pytest -q tests`: 1330 passed, 1 skipped, 42.31 s (`tests-m3.log`); `git diff --check` limpio |
| Fixture plata | `s27-paused.sav` (copia de la del hito 2, SHA256 0c49b972…; S/récord27, activo1, PS60/70/80, estado0/0/1, PP5, PIKE_WILD217) |
| Plata Azahar | trainer139, flag0, S27, pendiente14 (`silver.gdb.log`); intro «Soy Lucy, Cerebro del Frente de el Tubo Batalla.» y «¡La Bruja Lucy te desafía!». Equipo exportado antes de asistencia: `check_team.py silver-team --facility pike` **rc0** (`check-silver.log`), Shuckle 252,0,0,0,106,152, IV16. Victoria asistida raw1; «¡Has obtenido el Símbolo Suerte de plata! Recibes 10 PB más.» (`silver-symbol.png`); RAM tras textos S28, activo1, símbolo1024, pendiente0 (`silver-after.txt`) |
| Pausa y guardado | «Pausar» en el menú del combate29 directamente tras Lucy: `silver-paused.sav` SHA256 937bb8b2…, 58 bloques válidos, S/récord28, activo1, ruta6, símbolo1024, pendiente0, PB 4→15 (+10 jefe, +1 ronda), equipo bruto y cajas idénticos a la fixture (`saved-silver.json`) |
| Recarga | Reinicio con `silver-paused.sav`, recepción → «Símbolos»: «Tienes el Símbolo Suerte de plata de el Tubo Batalla.» (`silver-reloaded-symbol.png`) |
| Fixture oro | `s139.sav` desde `silver-paused.sav` con `faraway/save_event.py`: S/récord139, PS60/70/80, estado0/0/1, PP5, PIKE_WILD217; SHA256 6d3dc6d8… (`gold-fixture-mine.json`) |
| Oro Azahar | recepción «racha… 139»; «Has vuelto a llegar hasta mí. Soy Lucy…» (`gold-intro.png`); trainer140, pendiente22. Equipo oro exportado antes de asistencia: `check_team.py gold-team --facility pike --variant gold` **rc0** (`check-gold.log`). Hooks pasivos restauran PS60/70/80 y estado0/0/1 antes del combate; en combate Beldum 70/156 y Poochyena 80/184 paralizado (`gold-retained-party.png`) |
| Derrota oro | Asistencia en modo derrota (solo PS de copias propias); raw0. RAM tras volver a recepción: ruta0, S0, activo0, pendiente0, símbolo1024 (`gold-after.txt`). Auto-guardado `gold-loss.sav` (SHA256 9a9dc707…, 58 bloques): S0, activo0, récord139, símbolo1024, pendiente0, PIKE_WILD0, PS v2 a 0, PB 15→15 (sin premio), equipo/cajas idénticos (`gold-loss-save.json`). Como en el Domo (§44), el archivo conserva ruta6 escrita antes del retorno retail, que en RAM ya es 0 |
| Laboratorio | puerto 24690; `reap` desde la misma sesión; sin `session.json` ni procesos del carril; bus D-Bus privado cerrado (`cleanup.log`) |

La asistencia solo cambió PS/movimientos de copias de combate; no tocó resultados, works, símbolos ni PB.
No probado: consola, oro ganado en Azahar (sí en VM), revanchas en Azahar (sí en VM), inglés en juego,
dificultad real sin asistencia, aspecto exacto de Esmeralda (sustitución de clase/modelo de §45).

## 47. Cerebro de la Pirámide — Brandon (F8-CEREBRO-PIRAMIDE, 2026-11-12)

Diseño: `reports/diseno/cerebros.md` §1, §5, §7. Código: `frontier/pyramid.py` (escalera, cima, consulta),
`frontier/brains.py` (sets, ENABLED, `check_routine(p, streak_work, offset)`). Tests:
`tests/test_frontier_brain_pyramid.py` (VM) y `tests/test_frontier_brains.py` (ids cotejados con gametext ES).

Flujo: el encargado del piso 7, con los tres entrenadores vencidos, cuenta el piso (racha y récord) y llama
`brains_check` con unidad = pisos contados. Si toca Brandon (21; con plata 70; con ambos 21 y 70, 105, 140…),
guarda la variante en el work 16731 (`WORK_SUMMIT`, reservado en REPARTO para la cima) y combate allí mismo:
el combate es el de los pisos (trabajo propio, `SetTrainer(0)`) con `WORK_BRAIN` = 7 + 8·variante, y
`brains_cro.s` pone el entrenador 141/142 (clase 96 Montañero, nombre Brandon) y su equipo exacto. Ganar:
`brains_won` (símbolo, +10 PB, línea), después los PB del desafío y vuelta al vestíbulo; el combate no suma piso.
Perder: línea de derrota, fin del desafío (racha 0), récord y símbolos intactos. Con 16731 ≠ 0 (recarga) el
encargado va directo a Brandon sin volver a contar; los entrenadores del piso 7 siguen vencidos hasta cerrar.
Retirarse en recepción también limpia 16731. Consulta: la segunda recepcionista del vestíbulo (evento 3, NPC 2 de
517, casilla 17,24). Sin líneas de texto nuevas (las de Cerebros por ruta) ni zona nueva. Sustitución visual: en
campo Brandon es el encargado (modelo 62); en combate, la clase 96.

Espacio: el piso pasaba a ZO 17692 > 17248; los tres entrenadores comparten `pyramid_trainer(bit)` y una
`pyramid_battle(brain)` con la cima. ZO 140/141/142 = 16140/16956/16956 (`romfs/a/0/1/3` de la build).

Aceptación en Azahar (puerto 24690, política caso a: solo la Pirámide; no cambian motor, asm, patch.py, isla ni
construcción común; `brain_table` solo gana las dos filas de datos de Brandon, como Lucy). Evidencia en
`work/frontier/cerebros/pyramid/` del carril claude:

| Prueba | Resultado | Fuente |
| --- | --- | --- |
| Fixture plata | copia de `work/frontier/lab/py_c_lobby_saved2.sav` (8b5a8b76…): S/récord 20, piso 7, vencidos 7, ruta 7, otros activos 0 | `fixture.json`, `s20-floor7.sav` |
| Plata | intro de Brandon; entrenador 141, S=21 ya contado, WORK_BRAIN 15; equipo Regirock/Registeel/Regice IV16 y EV exactos (`check_team.py --facility pyramid` rc0); victoria raw1 | `silver.gdb.log` (transcrito de consola), `talk1.png`, `check-silver.log` |
| Premio | «Símbolo Bravura de plata… 10 PB más», luego «Recibes 6 PB» (desafío 3); guardado: S/récord 21, activo/ruta/pendiente 0, símbolos 4096, PB 5→21, equipo y cajas idénticos | `after-win1.png`, `won-bp.png`, `silver-saved.json` (silver-saved.sav 110c8e5519e0327c…) |
| Recarga y consulta | reinicio desde ese guardado; recepcionista 2: «Tienes el Símbolo Bravura de plata» | `symbols-talk.png` |
| Pendiente guardado (oro) | copia del guardado de plata con S/récord 70, piso 7, vencidos 7, 16731=2: entrenador del piso «Ya hemos combatido»; encargado directo a «Has vuelto a llegar hasta mí» sin «Piso 7 de 7» | `gold-fixture.json`, `gold-trainer-beaten.png`, `gold-intro.png` |
| Oro | entrenador 142, S=70 (sin piso extra), Articuno/Zapdos/Moltres IV31 y EV exactos (rc0) | `gold.gdb.log`, `check-gold.log` |
| Derrota | raw0; línea de Brandon y «Has perdido…»; vestíbulo; guardado: S/activo/ruta/pendiente 0, récord 70, símbolos 4096, PB 21 | `gold-loss-save.json` (gold-loss.sav 1b703d142ed4e64a…) |
| Equipo real | plata idéntico; tras oro difieren solo amistad (+2, 0xCA/0xA2) y checksum de los cinco no huevo, también los que no combatieron: pasos al caminar, no el combate | comparación con `save_fixture.decode_pk` (bitácora) |
| Laboratorio | parado con `gdbctl.sh stop` y `reap`; sin `session.json`; use_gdbstub=false | `cleanup.log` |

La asistencia (`pv_mode`) solo cambió PS/movimientos de las copias de combate. No probado: consola, oro
ganado y revanchas en Azahar (sí en VM), inglés en juego, dificultad sin asistencia, aspecto de Esmeralda.

## 48. F7-CONSOLA-MANSION: diagnóstico del aborto de consola (2026-11-12, Codex)

En curso. El informe de la primera prueba real está en `reports/consola-frente.md`
(incidencia añadida al final). `frontier/probes/maison/dump.py` compara el volcado
sin copiarlo al repositorio: los 96 bytes hasta PC0x76638c coinciden en alfa y v0.5;
la instrucción retail de CRO+0x7338c desreferencia r0=0, FAR0xc. No implica que la
causa sea heredada: un equipo vacío puede venir de un gancho anterior.

La sonda pasiva `frontier/probes/maison/trace.gdb` mide selección, equipo construido
y clientes, y detiene antes del acceso nulo si la cuenta es cero. Usa base CRO
0x6f3000, validando la instrucción del constructor antes de leer el cliente.
En el carril Codex, `boot.sh` verificó los 37 ficheros instalados frente al manifest
de la alfa exacta y arrancó la partida publicada (SHA2565ddaa992…7edeffa).
Evidencia local: `work/frontier/console-maison/{dump.json,boot2.log}`.
No se ha modificado el motor ni reconstruido/sustituido la distribución.

### 48.1 Medidas en Azahar y huella del volcado (Claude, 2026-11-12)

Relevo de Codex (cortado por cuota con el árbol limpio; sus registros de Individual y Doble, en su carril
`work/frontier/console-maison/`, ya mostraban combates sin cuelgue). Laboratorio 24690, paquete alfa exacto
(`boot.sh`: 37 ficheros = manifest), partida `reception.sav` (98089a84…, la de Codex) y `trace.gdb`:

| Caso | Equipo construido | Cliente 0 (cuenta) | Resultado |
| --- | --- | --- | --- |
| Individual / Doble (Codex) | 3 / 4 | — / 0x820e2bc (4) | sin cuelgue |
| Triple | 6 | 0x820f4dc (6) | sin cuelgue (`triple.log`) |
| Rotatorio | 4 | 0x820e2bc (4) | sin cuelgue (`rotation.log`) |
| Múltiple (sin enlace, compañero Aura) | 2 | 0x82118dc (2); cliente 2 IA (2) | sin cuelgue (`multi.log`) |
| «Fábrica Batalla» en la recepcionista de 517 | 3 alquileres, ruta 1 | 0x820d9ac (3) | sin cuelgue (transcrito) |
| Partida del usuario `dumps/domo-cuelgue/main` (120cde02…) llevada a 517, Individual | 3 (0,3,5) | 0x820d9ac (3) | ruta 0 tras la recepción; sin cuelgue (transcrito) |
| Misma partida en el Domo (456), ruta 5 | 2 | 0x820d09c (2) | sin cuelgue (`user-dome.log`); se perdió el combate |

La partida del usuario es la de Checkpoint con Poochyena Nv. 98, Cascoon y Shroomish Nv. 99 y la Caja de Combate
vacía; guardada en el Domo al inscribirse (16438 = 5, Domo activo 16474 = 1, racha 0, TEAM 0,3,5).

Huella (`frontier/probes/maison/stackdiff.py`, `stack.gdb`): la pila de consola (0x198 bytes) es **idéntica palabra
a palabra** a la del constructor del cliente 0 en un combate del Domo en Azahar, salvo +0x24 (el cliente). Llamada
desde el montaje Individual (LR CRO+0x166c0). El montón es determinista (BattleMain 0x81fb500, contenedor 0x81fb588
iguales): cada Pokémon de cualquiera de los dos bandos aparta 0x488 antes del cliente 0. El cliente de consola
0x820c78c corresponde a **2 Pokémon en el combate**: jugador 0 y rival 2. Un rival de 2 en Individual solo lo da
`dome_count` con WORK_ROUTE = 5 (Domo); Tubo salvaje da 1. Conclusión medida: el volcado es un combate con la ruta
del Domo y el equipo del jugador vacío, no un combate de la Mansión original (allí la recepción pone la ruta a 0 al
crear el work, medido). Los dos volcados del usuario son idénticos byte a byte (00:21 y 01:16 del reloj de la consola).

Con ruta 5 el equipo del jugador solo puede quedar vacío si (a) el montador toma la rama Caja de Combate
(work+0x2c ≠ 0: no pasa por `rental_hook`/`dome_party` y la cuenta work+0x48 no se escribe) o (b) los dos huecos
DOME_FIGHT apuntan a Pokémon vacíos (AddMember 0x3b645c descarta especie 0, 0x4d2e7c). BattleInstWorkCreate
(0x1e5910) pone a 0 +0x2c..+0x4c, y el Domo no llama a la app de selección, así que ninguna de las dos se ha visto en
Azahar. Estado: **no reproducido**; falta saber los pasos exactos de la consola. No se ha cambiado el motor.
No probado: v0.5 (no aplica: sin cuelgue que comparar), consola.

## 49. F7-CUEVA-LUMA: Luma pisa el principio de la cueva de code.bin (2026-11-13, Claude)

**Causa** (medida por el usuario en su 3DS con el depurador de Luma; `work/frontier/consola/`): con LayeredFS, el
cargador de Luma3DS (`sysmodules/loader/source/patcher.c`, `findLayeredFsPayloadOffset`/`patchLayeredFs`,
comprobado en 1441535d) copia su carga de redirección (`romfsredir.s`, `romfsRedirPatchSize` = 0x114 = 276 bytes,
tamaño fijo del ensamblado) **al final del .text del exheader** si el relleno hasta la página es ≥ ese tamaño, y
desvía `fsOpenFileDirectly` (0x1325a4 → 0x579604) y `fsTryOpenFile` (0x123e80 → 0x579610); la ruta «lf:…» va al
relleno de .rodata (0x5eba14), fuera de .text. Nuestra cueva empezaba en ese mismo 0x579604 con `rental_hook`: en
consola todo combate de tipo Mansión ejecutaba código de Luma. Azahar aplica LayeredFS por su cuenta y no escribe
nada en el ejecutable. Las palabras de la carga de consola que no son reubicaciones coinciden con el ensamblado de
`romfsredir.s`; el resto de .text de consola difiere de nuestro code.bin solo en bytes que no tocamos.

**Arreglo** (`frontier/patch.py`):
- `LUMA_PAYLOAD` 0x114, `LUMA_RESERVED` **0x200**: 0x579604–0x579804 se deja a cero; nuestro código empieza en
  `HOOKS` = 0x579804 (`rental_hook`). `assemble()` falla si algo cae en la reserva o pasa de 0x57a000; `build()` exige
  la cueva entera a cero. code.bin: 1768 bytes (0x579804–0x579eec), **276 libres**.
- Las rutinas que solo corren en combate y solo se llaman desde DllBattle.cro (Arena: `arena_enter`, `arena_switch`,
  `arena_turn_end`, `arena_judge`; Palacio B: `palace_ai_want`, `palace_ai_flags`, `palace_dispatch`) pasan al
  relleno de la región de código de **DllBattle.cro, 0xd7870–0xd7b84** (788 bytes, tras `palace_cro.s`
  0xd7630–0xd7868; quedan 1148 hasta .rodata 0xd8000): `asm/arena_cro.s` y `asm/palace_b_cro.s` (antes `palace.s`),
  enlazados en su offset de fichero (`patch.battle_cro_code`, `BATTLE_CRO_AT`). `arena_judge` llama a UDIV 0x15ec10
  por dirección absoluta. Puentes `nop; bl stub; b +0; nop` (`arena_engine.bridge`): `bl` relativo dentro del CRO
  (sin reubicación, cualquier base) y LR = sitio + 8 como antes. Escritos con `guarded_writes`, rehash y CRR como hoy.
  `arena_start`/`palace_start` (StartBattle), Fábrica, rival, rachas, Domo, Tubo y Pirámide siguen en code.bin.
- `frontier/luma.py`: la carga medida y los dos desvíos (`overlay()`), y CLI que escribe un code.bin/code.ips «como lo
  ve la consola» para el laboratorio. `frontier/probes/luma/lab_mod.py`: carpeta de mod como el paquete (v0.5 + build
  + code.ips, `plain` o `luma`) con `manifest.json` para `probes/package/boot.sh`.

**Tests** (`tests/test_frontier_luma.py`; `test_frontier_patch.py` corre todos sus casos Unicorn también con Luma
encima): reserva ≥ carga; Luma cae sobre ceros y deja intactos nuestros bytes; cada gancho de code.bin apunta a
≥ HOOKS con Luma aplicado; ningún salto ni literal nuestro entra en la reserva; `pike_param` (DllField) fuera de ella;
puentes de DllBattle con `bl` a sus rutinas; ensamblado que no cabe → error; la carga coincide con
`console-text.bin`. Mutación: con `LUMA_RESERVED` = 0 los casos «luma» del alquiler fallan (16): la VM reproduce el
cuelgue. Suite: 1405 passed, 2 skipped.

**Azahar con Luma simulado** (laboratorio 24690; `work/frontier/cueva/`):

| Prueba | Build | Resultado |
| --- | --- | --- |
| Mansión original (517) Individual, `reception.sav` 98089a84… | **alfa v0.1 + carga de Luma** (`mod-alpha-luma`, code.ips a885e4b7…) | **SIGSEGV** en el montador (pc 0x1e3dc0 → `bl 0x3b6150`, `ldrcc r0,[r0,…]` en 0x3b6154) con equipo r8 = **0xd8e007f7**: la huella de los volcados 4/6 de consola (`alpha-luma-maison.gdb.log`) |
| Mansión original Individual, misma partida | **arreglo + carga de Luma** (`mod-luma`, code.ips 5bcc632a…, 38 ficheros) | «¡La Turista Kate te desafía!», tres Pokémon, `FRONT START` ruta 0 y `FRONT RESULT raw=0` (`maison-luma.gdb.log`, `maison_battle.png`) |
| Circuito `circuit.py` desde `checkpoint_harbor.sav` (5ddaa992…): marinero, ferry, plaza y las siete | arreglo + Luma | Fábrica (ruta 1, 16489 = 3), Torre (2), Arena (4), Palacio (3), Tubo (6, sala superada), Domo (5) y Pirámide (7, piso 141): cada uno `FRONT START` con su ruta y `FRONT RESULT` (derrota, equipo Nv. 6–12), vuelta a la plaza; `circuit done` (`circuit.log`, `circuit.out`, `circuit.gdb.log`, `shots/c_*_battle.png`) |
| Historia: `s1_story.sav` (aeacbea8…), Cazabichos de la Ruta 102 | arreglo + Luma | combate de entrenador hasta el final y vuelta al campo con su línea posterior (`shots/story_*.png`) |

Los puentes de Arena y Palacio están en todo combate (constructor de clientes, despacho de órdenes, entrada y fin de
turno), así que el combate de la historia y el de la Mansión original los ejecutan desde su nueva ubicación. Un
breakpoint de GDB en el CRO no salta en Azahar (el cargador repone los marcadores, `probes/maison/README.md`): la sonda
`FRONT ENTRY` en `arena_enter` (`patch.battle_cro_runtime`, base 0x6f3000) quedó a 0 avisos; la prueba de que corren
es que los combates terminan.

**Sin probar**: consola (el usuario puede validarlo con el depurador de Luma: 0x579604–0x579717 será Luma y
0x579804 `rental_hook`); juicio de 3 turnos de la Arena y decisiones del Palacio en Azahar tras el traslado (sí en
Unicorn: `test_frontier_arena.py`, `test_frontier_palace.py`, sobre el CRO parcheado en dos bases); otras versiones de
Luma con carga > 0x200. El paquete (`frontier/package.py`) no se ha regenerado: su lista `BUILD_FILES` no incluye
`a/1/8/3` (Cerebros) y falla; es de F7-PAQUETE-V02.

## 50. Paquete alfa v0.2 — F7-PAQUETE-V02 (2026-11-13)

`frontier/package.py` (commit **18018ba**) genera `dist/oras-frontier-alpha-v0.2` y su ZIP: arreglo
F7-CUEVA-LUMA, Cerebros y símbolos, sin «Guardar vídeo» en el Frente. Incluye `a/1/8/3` (entrenadores de
los Cerebros), 38 ficheros de mod y LEEME (39 hashes en el manifiesto). El LEEME explica el fallo de Luma
que colgaba todo combate de tipo Mansión en v0.1 y los límites que siguen pendientes.
Partida: `dist/oras-frontier-checkpoint-test-v0.2/FrenteTest-puerto-Calagua/main`, SHA-256
`5ddaa992c5aea98a3da1af80c1f2486b6d2db1690da0ae8be84abf2397edeffa` (misma partida inicial sin pase de §38).

**Relevo**: Claude dejó el generador en commit, las dos carpetas en `dist/` y la regresión ejecutada en su
carril, pero se cortó antes de documentarla. Codex recibió el árbol limpio, revisó los registros y capturas
y los copió a `work/frontier/pkg02/recovered/` del carril codex para conservarlos. No se atribuyen estas
sesiones de Azahar a Codex. Fuente original: `../claude/work/frontier/pkg02/` y su `pkg/circuit.log`.

**Identidad del paquete**: Codex reconstruyó con
`python frontier/package.py --output work/frontier/pkg02/oras-frontier-alpha-v0.2` desde 18018ba limpio
(`package.log`), generó Checkpoint con `package.py checkpoint` y verificó los **39 hashes reales** tanto
en esa copia como en `dist/oras-frontier-alpha-v0.2`. Todos idénticos a su manifiesto. ZIP reconstruido:
`33fe04dcf300d645955be8bd9fe2ff876e49ab586f30aaad57553da9df16bfc5`.
`code.ips` de distribución: `988859140bd930ec6186cb45ae954eb112309acc2bc6558b252cecd21ff80be2`.

**Carga simulada de Luma**: `frontier/probes/luma/package_ips.py` lee el IPS exacto del paquete y comprueba
`console_check` antes de emitir el IPS exclusivo del laboratorio. SHA-256 de ese IPS:
`5bcc632aa2797565e47e18555238d8c7f53f0e5c2e775244dab35ceaaa07974a`; su `code.bin`:
`e1eee2ba2e29dcf9ceac707957f995d7e48d0bb66fda482c809ddad626acf21b`.
Ambos son idénticos byte a byte a los usados por Claude. `recovered/boot-circuit.log` documenta la copia exacta
comprobada (38 ficheros) antes de sustituir únicamente el IPS por esta variante. El IPS simulado nunca se distribuye.
El script exporta además `package-code.bin` (antes de Luma) para comparar ambos estados con el depurador.

**Regresión caso d del paquete exacto + Luma**, por Claude, revisada por Codex:

| Caso | Evidencia en `work/frontier/pkg02/recovered/` |
| --- | --- |
| Marinero, pase, ferry, llegada y plaza | `sailor_pass.png`, `shots/c_ferry_menu.png`, `shots/c_island_pier.png`, `shots/c_plaza.png` |
| Fábrica, ruta 1: alquiler, victoria, siguiente combate y derrota | `circuit.out` 18:40–18:44; `circuit.gdb.log`: dos pares START/RESULT, racha 0→1 |
| Torre, Arena, Palacio, Tubo, Domo, Pirámide | `circuit.out` 18:45–19:08; START/RESULT de rutas 2/4/3/6/5/7; capturas `shots/c_*_battle.png`, salida de cada edificio y `circuit done` |
| Mansión original Individual, ruta 0 | `maison.gdb.log`: START ruta 0, RESULT raw=0; `shots/v02_maison_battle.png`, `shots/v02_maison_after.png` |
| Guardar/cargar en plaza, ferry a Calagua | `shots/saved_plaza.png`, `shots/reloaded_plaza.png`, `shots/back_port.png`, `reload-port.gdb.log`; `saves/v02_saved_plaza.sav`, SHA-256 `4784ac54131ba7cc356b979f1191c055a4f0b9d4cd0ac2b17c2166965e903095` |
| Combate normal salvaje, Wurmple Nv. 3, Torchic Nv. 12 | `shots/wild_1.png`, `shots/wild_t*.png`; guardado posterior `saves/v02_after_wild.sav` |
| Repartir Exp. | Comparación de partidas con `scripts/save_fixture.py`, `../exp-check.json`: EXP participante 1105→1129 (+24), portador no participante 1105→1117 (+12), reserva sin objeto 1105→1105; +1 EV PS en participante y portador, ninguno en otra reserva; 58 bloques válidos |
| DexNav | `shots/dexnav.png`: Wurmple, «Nivel / Racha 15/0» |

Guardado tras salvaje SHA-256 `c701566473a931a84357c1f8af55561fcaafc4f6b3d262f36cf688049e961717`;
inicial de reserva `9966ec53de0acd99588da932caeb490e3b4fee0ea32b220e2f5c7e5c001ad574`.
El combate salvaje cubre la carga normal del motor; no se repite el entrenador de §49, conforme a política d.

Codex arrancó también el paquete exacto en su laboratorio 24691 (`boot.log`, `boot2.log`), pero al recuperar
la regresión completa evitó repetirla. El intento de conductor local falló antes de hablar con el marinero por
los PID de GDB entre namespaces (`pos()` sin lectura); no es una prueba de combate ni un fallo del paquete.
El laboratorio codex quedó parado. Ningún proceso del carril claude fue modificado.

**Pruebas**: `source scripts/env.sh; env -u ORCH_LANE python -m pytest -q tests`: 1407 passed, 3 skipped
(`work/frontier/pkg02/tests-m1.log`, 51.04 s; repetición final `tests-final.log`, 46.74 s); `git diff --check` limpio. El informe de consola v0.2 contiene
el orden de pruebas, la Mansión original y la comparación de 0x579604–0x579fff con los binarios y `console_check`.

**No probado**: v0.2 en consola real; los siete encuentros de Cerebros, rondas completas y juicio de Arena con
este paquete exacto (sus pruebas al implementarlos son anteriores); ferry de Portual y otros idiomas.
No se modificó motor, isla ni LEEME durante el cierre documental: los 39 ficheros validados siguen siendo
los de 18018ba. Tras integrar este cierre, `package.py` puede regenerar el manifiesto con el nuevo commit;
los ficheros del juego y LEEME deben mantener sus hashes.

## 51. Modalidades F9-BASE, hito 1: reservas y medidas previas (2026-11-13)

Estado en curso; detalle y continuación en `reports/modos-base.md`.
`frontier/modes_audit.py`: 43 candidatos tras REPARTO y exclusión 0x4010–0x401f;
reservadas 42 posiciones en REPARTO (53 propuestos menos 11 huecos S+1).
M=0 intacto; nuevos bancos con racha/récord explícitos, no presuponer S+2.
Espacio medido: code.bin 1768 bytes en 0x579804–0x579eec, 276 libres y reserva Luma
intacta; Cerebros DllField termina 0xf09f4, reserva F9 0xf0a00–0xf1000.
Accesores Dobles reales por tablas de salto: incremento 0x45cdfc, lectura 0x45cf24,
borrado 0x45cfc8 y récord 0x45d04c. Unicorn ejecuta los bytes retail, límite 9999,
rangos 0/1 y normalización de no cero; callback 0x96b00 con paquetes sintéticos,
configuración 0x1e5684 y SetRank sin validación. PB Dobles cotejados en las 30 filas
de pokeemerald 731ad5bf; API Python preparada, sin hooks/menús activos nuevos.
Evidencia: work/frontier/modos/base/{audit.json,static.txt,reference-bp.json,build-hashes.json}.
Suite env -u ORCH_LANE python -m pytest -q tests: 1512 passed, 3 skipped, 48.80s.
No probado: UI/cancelación real, cuatro inscritos, persistencia Azahar, Libre L=73,
nativos nuevos ni consola. Binarios reconstruidos sin cambios respecto al inicio.
