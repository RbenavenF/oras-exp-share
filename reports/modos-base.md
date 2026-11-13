# F9-MODOS-BASE — hito 1 (2026-11-13, Codex)

Estado: **en curso**. API de asignación y recompensas preparada; ningún menú,
script ni hook consume todavía los modos nuevos. No declarar Libre/Dobles
jugables ni persistencia en Azahar a partir de esta entrega.

## Reservas y espacio medidos

`python frontier/ids.py` examina 1157 scripts y 147 ficheros de código: 121
candidatos retail (excluye Mew, pero incluye las asignaciones del Frente).
`python frontier/modes_audit.py` resta REPARTO y todo 0x4010–0x401F, el bloque
sospechado de borrado por rango (§25): quedan **43**. El escáner estático no
detecta todos los accesos calculados; la carga/guardado real sigue pendiente.

La propuesta de 53 posiciones de `diseno/modos.md` §3 no cabe. Se reservan
**42**, conservando los 42 valores usados y suprimiendo solo los once huecos
S+1. `frontier/modes.py` asigna direcciones independientes a racha y récord
nuevos, explícitas en REPARTO. Las siete parejas M=0 y sus works de estado
permanecen iguales. **La futura implementación nativa no puede trasladar el
incrementador retail tal cual**, porque este calcula récord = racha+4 bytes:
deberá resolver ambas direcciones, incluso en incremento. No se intercambian
bancos al entrar/salir. La última candidata sin reservar es 16399.

En la partida F3 `08eaa586be0029cb2b9fe205e968a8e959969524827af0ca3ead7352ab30864d`
las 42 posiciones están a cero (`work/frontier/modos/base/audit.json`). El path
`inputs/save/main` no existe en este carril; **no se afirma** haber cotejado esos
valores con la partida original actual. No se escribió ninguna partida.

| Región | Resultado actual | Evidencia |
| --- | --- | --- |
| code.bin | 0x579804–0x579eec, 1768 bytes; **276 libres** hasta 0x57a000 | `patch.assemble()`, `base/build.txt` |
| Luma | **0x579604–0x579804 intacto** | `patch.LUMA_RESERVED`, auditor y suite existente |
| DllBattle | 0xd7870–0xd7b84, 788 bytes; **1148 libres** | `patch.battle_cro_code()` |
| Cerebros DllField | 0xf0480–**0xf09f4**, 1396 bytes | `brains.assemble()`; cifras antiguas obsoletas |
| Reserva F9 DllField | **0xf0a00–0xf1000**, 1536 bytes; sin bytes nuevos aún | `modes_audit.measure_space()` |

El auditor exige SHA-256 del DllField v0.5
`8c9da930a13b56b797dedfc87940b85b5b3cad9a1cf35390c4796b0c6f5cb53a`,
ceros exactos, no solapamiento con Cerebros ni relocaciones internas y pertenencia
del CRO al CRR. La reserva está en el relleno de la última página de texto,
**fuera** del tamaño lógico de ese segmento (termina 0xf03f0), igual que los
ganchos DexNav/Cerebros existentes. La futura escritura debe componerse en
`patch.battle_cro` con guards de bytes/hash, rehash CRO y actualización CRR;
no basta añadir bytes a RomFS. El auditor no prueba su ejecución en consola.

## Callback y accesores: evidencia estática y Unicorn

Reproducir: `python frontier/probes/modos/measure.py`, salida en
`work/frontier/modos/base/static.txt`. Verifica hashes de `maison_map.HASHES`.
`tests/test_frontier_modes.py` ejecuta **los bytes retail** en Unicorn.

Selector DllField `0x957fc`, callback **0x96b00**:

- `[task+4]` es el paquete; +8 formato, +9 codificación de rango del selector,
  +0xa aceptación y +0xb auxiliar X. Los destinos u16 están en task+0xc/+0xe/+0x10.
- Paquete con byte 0 = 0 no escribe resultados ni configuración. Con byte 0 = 1
  y aceptación 0 escribe tipo=0, X=0, aceptación=0; no reconfigura el trabajo.
  Son **paquetes sintéticos**, no medición de qué paquete emite Cancelar en la UI.
- Aceptación 1 llama al thunk `0x3870` → **code 0x1e5684**, con
  `(work, paquete[9], paquete[8], 0)`; escribe tipo y X sin reinterpretarlos.
  X=7 en el test demuestra propagación, **no** que 7 sea una opción válida de UI.
- Con rango del selector 1/2, `0x1e5684` deja rango **Normal/Súper 0/1** en +0x838,
  tipo en +0x839 y código 1/2 en +0x83a; también guarda el rango en Mansión+0x1f4.
  Tipo 1 deja +0 = 1. La selección real, count+0x48=4 y el camino byte0=2/r3=1
  no están medidos. **No omitir esta inicialización en Fábrica/Torre.**
- **SetRank 0x1e567c**, bytes `strb r1,[r0,#0x838]; bx lr`, no valida: Unicorn
  escribe 0, 1 y 2 literalmente. Libre nunca se codificará en este byte.

Las tablas de salto resuelven los accesores por tipo; no se han extrapolado:

| Operación | Entrada función | Tabla tipo 0..4 | Cuerpo Individual | Cuerpo Doble | Primera instrucción Doble |
| --- | --- | --- | --- | --- | --- |
| incremento | 0x45cd98 | 0x45cdb0 | 0x45cdc4 | **0x45cdfc** | e0801082 |
| lectura | 0x45cee8 | 0x45cf00 | 0x45cf14 | **0x45cf24** | e0800082 |
| borrado | 0x45cf8c | 0x45cfa4 | 0x45cfb8 | **0x45cfc8** | e0800082 |
| récord | 0x45d010 | 0x45d028 | 0x45d03c | **0x45d04c** | e0800082 |

Racha retail Individual en Mansión+0x1c4+2·rank y récord +0x1c8+2·rank;
Doble usa +0x1cc y +0x1d0. Rank no cero se normaliza a 1 en esas funciones.
Unicorn verifica ambos formatos, rangos de entrada 0/1/2/255, valores
0/9998/9999, saturación a **9999**, borrado que conserva récord y ausencia de
escrituras en bancos vecinos. Aún falta la matriz de los hooks **nuevos**.

Consumidores que deberá adaptar BASE:

- `GetMyWinCount` DllField 0x951a0: **primer argumento script = rango** (normaliza
  booleano), **segundo = tipo** (u8). Su salto 0x3698 llega a code 0x45cee8.
  Un `GetMyWinCount(0,0)` no leerá Dobles; resolver banco desde `(ruta,M)` en script.
- `AddWinCount` code 0x1e2fb0 lee tipo +0x839 en 0x1e2fc4 y rango +0x838 en
  0x1e301c; incrementa en 0x1e3024 y luego lee **ambos rangos** (0x1e3040/3054)
  para estadísticas de la Mansión. Proteger el rango Súper retail al añadir hooks.
- `SetTrainer` DllField 0x94edc separa únicamente argumento=4 (Multi); Individual
  y Dobles pasan ambos por 0x94f04/0x94f18, hooks actuales de Cerebros. Su ruta
  tardía lee la tabla `brains.streak_offsets` M=0: necesita resolver modo también.

## Recompensas y API preparada

`frontier/data.py:FRONTIER_BP_DOUBLES` contiene las columnas Torre/Fábrica de
las **30 filas** de `sBattlePointAwards`. `reference_bp.py` lee el objeto Git
`731ad5bfd6e6f265508d0efcca0ba42f9dcf5881:src/frontier_util.c` del checkout local
de referencia, no su fichero mutable. Coteja las siete columnas Individual
existentes y ambas Dobles. Fuente de evidencia: `base/reference-bp.json`.

`modes.bank` conserva M=0, resuelve las once parejas nuevas y rechaza ruta 0,
desconocidas, M corrupto y Dobles fuera de Torre/Fábrica. No es aún el hook
nativo. `modes.battle_points` usa la misma columna para Libre y Nivel 50,
satura el índice de ronda a 30 y rechaza bonus de Cerebro en Dobles. No aplica PB
al saldo ni decide cuándo se completó una unidad: esas partes siguen pendientes.

## Build y continuación

El hito no cambia scripts/menús ni binarios del juego. Reconstrucción por
`patch.build()` y `patch.battle_cro()` (`base/build-hashes.json`):

| Salida | SHA-256 |
| --- | --- |
| code.bin | 82ddec4c5c1de82bc78d2e4b8d1ebea1071a77911b05c4fa9e75fa7e02b57275 |
| DllBattle.cro | 5cde67f65c9692c7b710956689a1ca5e6128d01f22d5a61eca5bb4ec83d51754 |
| DllField.cro | 10278e967452d75a2227a19a4a4c8a6754e7ce80d74054856c7f1c4acdefc593 |
| .crr/static.crr | 151abe3f64d76f6151eab0bafe5c2229c310812e5d249eeb25c8c00f53133747 |

Próximo hito: probar en el laboratorio **del carril** el selector Normal/Súper,
confirmación/cancelación y auxiliar X; tipo 1 con cuatro inscritos de equipo/Caja;
persistencia de las reservas al entrar/salir y guardar/cargar. Usar copias, no
partida original. Después implementar el resolvedor nativo de las dos direcciones
(no asumir S+2), guardar MODE/LEVEL por ruta y API de selección/pausa/validación.
Mantener nuevos menús cerrados hasta el corte Torre Individual Libre L=73.

Pendientes del contrato, sin prueba en este hito: salto de ajuste a 50 conservando
la cola y PS/estados del Tubo, L por selección efectiva/Caja, rival y Anabel al
nivel L, VM/Unicorn de los hooks, build ZO <=17248, pausa/guardar/cargar/derrota,
equipo/Caja intactos y regresión de motor Palacio/Arena/Tubo/historia. No hubo
Azahar ni consola en este hito preparatorio; se aplica regresión cuando cambien
los bytes del motor.


## Hito 3: validación nativa de CONFIG (2026-11-14, Codex)

Corrige el hito 2 (`9b1b09a`): `mode_of` validaba M y ruta, pero aceptaba
niveles corruptos (por ejemplo 0x100 y 0x1ff). Ahora comparte el contrato de
`modes.unpack_config`: CONFIG=0 conserva partidas antiguas; Nivel 50 requiere
L=50; Libre requiere 60–100 en equipo propio y exactamente 100 en Fábrica.
Configuraciones inválidas vuelven al acceso retail, no escriben sus bancos ni
CONFIG y conservan el ajuste retail del jugador. `mode_level` devuelve 50 para
ellas. No se habilitan menús nuevos.

El código usa el carry como resultado de validación; la salida legacy compara
CONFIG con 1 para devolver C=0. Las pruebas ejecutan los cuatro accesores retail
parcheados y comparan bancos con la API Python, también para niveles inválidos,
formatos incompatibles y rangos Normal/Súper. Se elimina la saturación separada
de `mode_level` y el mínimo redundante del montador: L ya está validado antes.

Evidencia: `work/frontier/modos/base3/`. `tests-full.log`: **2267 passed,
3 skipped**, 53,22 s, comando `env -u ORCH_LANE python -m pytest -q tests` tras
`source scripts/env.sh`. `build.log`: overlay completa, ZO Mansión **16828**,
script compartido 22080 bytes. `audit.json`: code.bin **2044 bytes**, intervalo
**0x579804–0x57a000**, **0 libres**. Luma 0x579604–0x579804 conservada;
DllField F9 0xf0a00–0xf1000 sigue reservada y vacía. Los símbolos de Cerebros
se reconstruyen con la dirección actual de `mode_level` y sus guards/CRR.

Build exacta en `build-hashes.json`:

- code.bin: `2c5c1ffbd1c3dcc12426b6957fb821a9b3c013a2450b3214aca2d32ba6f224b7`
- DllField.cro: `9de84813459e1254974417e2ac1cf868a649bb4f3a2a083a24c44c6daf6635e5`
- static.crr: `a45e9079570cddd33b0eee11caa37dc4e8bc5b97e2d6a7542b448f151a6496a3`
- DllBattle.cro: `5cde67f65c9692c7b710956689a1ca5e6128d01f22d5a61eca5bb4ec83d51754`

Azahar para esta build sigue en curso; consola no probada. La regresión de otras
instalaciones/historia queda para la alfa por la instrucción del usuario del
13 de noviembre, que sustituye el siguiente paso de la entrada anterior.
