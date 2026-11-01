# Frente de Batalla — estado medido

Hechos estables del proyecto (PLAN §8). La historia de cada sesión está en
`frontier/BITACORA.md`. Todo lo de este informe sale de lectura estática salvo que
se diga lo contrario; **nada de F1 se ha comprobado aún en ejecución**.

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
añada Pokémon de alquiler en vez de copiar los del jugador. **Pendiente de
comprobar en ejecución** (gdb en Azahar) y de comprobar que nada después del
combate copia el equipo de vuelta (la Mansión no da EXP, pero hay que verlo).

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
  ejecución. **No comprobado en ejecución.**
- Ninguna otra vía (CRO, ampliar el exheader) se ha medido todavía.
