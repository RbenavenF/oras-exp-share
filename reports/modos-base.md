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

## Hito 4: Torre Libre 73, pausa y derrota reales (2026-11-14, Codex)

Build exacta del hito 3, laboratorio del carril 24691; copias bajo
`work/frontier/modos/base3/`. `frontier/probes/modos/vertical.py seed SOURCE SHA
OUTPUT` reproduce `tower73.sav` (SHA-256
`7a8c2cc32aa3d084eac64ef087e8963f97b3640f9474c63afef508b2212cdd72`)
desde `cerebros/base/tower34.sav` (SHA en `tower73.json`): tres candidatos de
niveles 73/55/41, CONFIG=0x13c, Libre S/R=6/6 y M0 S/R=12/20. La copia conserva
las estadísticas originales del fixture; el montador reconstruye la copia de
combate. No es una partida de usuario ni se distribuye el binario.

`win-gdb.log`: selección efectiva [0,2,1], tipo 0/rango 0; cap recibe 73/41/55,
CONFIG pasa de 0x13c a **0x149** y las tres llamadas MAKE_PARAM reciben **73**.
`rival73.png` muestra Houndour 73. Victoria real (raw=1), S/R Libre **7/7**,
M0 **12/20**, premio **1 PB**. Pausar guarda `paused73.sav`, SHA-256
`9490d5929b70562faa4b1a9e394d70689d93fb42c9c9a82f9c47db232eaf79b2`,
CONFIG 0x149, ACTIVE=1, PB=4 (`paused73.json`).

Carga desde disco de esa pausa, sin asistencia de combate:
`reload-loss-gdb.log` registra inscritos [3,5,4], niveles **6/6/7** conservados,
CONFIG 0x149 y tres rivales construidos a **73**. Derrota real raw=0. El guardado
`lost73.sav`, SHA-256
`4262eabaa1147d9e547d9f1e8517979e7e2f3c01b708a65e68e65850205cec9d`,
contiene Libre **0/7**, ACTIVE=0, CONFIG=0x149, M0 **12/20** y PB=4.
`lost73.json` comprueba **equipo y Cajas idénticos byte a byte a paused73.sav**.
WORK_ROUTE=2 queda en el autosave anterior a la limpieza de retorno; el script
lo limpia en RAM al salir de la rutina. No interpretar esa ruta como ACTIVE.

Comparación inicial seed→pausa: las Cajas sí son idénticas; en el segundo PK6
cambian exclusivamente +0xa4..0xa9 (metadata de entrenador/geografía) y su
checksum. No afirmar identidad total en esa primera transición: esos campos
pasan de 0103/0900/0900 a 0317/1700/0000. Los otros cinco PK6 y todos los campos
restantes, incluidos nivel, experiencia, movimientos, objetos y estadísticas,
son iguales. Tras normalizarse en la pausa, la derrota no cambia ni un byte.

Sonda reproducible: `vertical.py probe DIRECTORY`. Excluye el hook de asistencia
en arena_enter y observa los hooks de code.bin; callback CRO dinámico por
hardware. Un intento descartado (`reload-breakpoint-corruption.log`) usó un
breakpoint software antes de cargar el CRO: GDB restauró 00000000 sobre su
primera instrucción e2850c01 y causó SIGSEGV. No es evidencia de fallo del parche;
la repetición pasiva anterior termina normalmente. No hubo escrituras de RAM
para forzar victoria/derrota en las mediciones aceptadas.

Suite tras la utilidad: `tests-hito4.log`, **2267 passed, 3 skipped**, 58,86 s,
`env -u ORCH_LANE python -m pytest -q tests`. Tabla PB de 30 filas cotejada otra
vez con el objeto Git fijado (`reference-bp.json`). Consola no probada.

Sigue pendiente cerrar persistencia de las 35 reservas con CONFIG válidos,
callback Súper real y el guard de estado inactivo de §2 (el resolvedor actual
valida ruta/CONFIG pero no ACTIVE). También auditar L fijo si cambia la selección
al reanudar: el hook actual permite subir L, aunque nunca bajarlo. No habilitar
menús ni marcar BASE completa con esos pendientes.

## Hito 5: persistencia35 y callback Súper (2026-11-14, Codex)

Sin cambios de motor desde b449950. Reutiliza la misma build exacta y la suite
completa del hito 4 (2267 passed, 3 skipped). `sentinels-source.sav` es una copia
de paused73.sav, trasladada a zona 517 (23.5,25.5), flags retail 385/386=1 para
mostrar Súper. Fuente SHA-256
`c60c62395705cd311821ff76bfacbb6d914b256a1324cd040ca0a808a30bed39`.
`persistence.py seed SOURCE SHA OUTPUT` produce `sentinels-valid.sav`, SHA-256
`195fbe87f5cfd6830cd7dc8f61da6ef7ecca456a4ea3eeffda0e7d6887fdea13`:
35 reservas no nulas, CONFIG válidos, ACTIVE y WORK_ROUTE=0. Metadatos con todos
los valores esperados en `sentinels-valid.sav.json`. No se inició combate con
rachas/sets artificiales.

`sentinels-super-gdb.log`: callback real de Súper Individual. Configurador
0x1e5684 recibe r1=2, tipo=0, init=1, LR=0x789b50 (DllField base 0x6f3000).
Paquete `0300000044258208000201000101000000000000`: bytes +8/+9/+10/+11 =
0/2/1/0, por tanto **auxiliar X=0**; resultado rango=1, tipo=0, selector=2.
Se declina la confirmación y cancela el selector: work 0x800c pasa a 0 sin
comenzar desafío. La lectura de 43 works (35 reservas + 7 ACTIVE + ruta) no
encuentra diferencias. No confundir este rango Súper con Libre.

Tras salir del salón a la antesala, avanzar el evento retail de recepción y
volver a entrar, guardado real desde menú X→Guardar. `sentinels-saved.sav`,
SHA-256 `4ec0ea564573cda563ef89d5ec8e64ba470fba0421d15cc5cc1e2d819db75f7a`,
zona 517 (19.5,31.5). `sentinels-saved.json`: checksums válidos de 58 bloques,
43 works sin diferencias, equipo y Cajas idénticos a la copia fuente.
Apagado y arranque desde ese guardado: `sentinels-reload-gdb.log` mide los mismos
43 valores en RAM, otra vez sin diferencias (`sentinels-reload-check.json`).
Esta vez selector Normal: código 1→rango 0, tipo 0 y X=0. Confirma los dos rangos
con la misma sonda y build; no demuestra persistencia frente a todos los eventos
retail del juego. Laboratorio del carril detenido con azahar_lab.py reap.

### Pendientes concretos para continuar BASE

`contract-gaps.json` ejecuta los helpers Unicorn de
`tests/test_frontier_modes_engine.py` contra el code.bin construido:

- Ruta 2, ACTIVE=0, CONFIG=0x149: mode_level devuelve **73**, debería usar 50
  en estado inactivo según §2. No basta añadir un guard a todos los accesores:
  tower.facility_program limpia ACTIVE al entrar en LOST, antes de las lecturas
  y ClearWinCount retail; hay que preservar limpieza/guardado del banco Libre.
- Con CONFIG=0x149 y nuevos inscritos [100,55,41], mode_cap cambia CONFIG a
  **0x164**. El contrato pide conservar L durante la pausa/reanudación. Hace
  falta distinguir fijación inicial de selección y desafío ya fijado; no usar
  rango 1/2 para este estado. La medición aceptada de niveles 6/6/7 solo prueba
  que L no baja, no que sea inmutable ante un inscrito superior.
- Code.bin está lleno (0 libres); diseñar/medir espacio para esas correcciones
  conservando Luma 0x579604–0x579804. DllField 0xf0a00–0xf1000 sigue vacío, con
  auditoría/guards/CRR preparados; no asumir su dirección runtime desde code.bin.
- Selección de Caja de Combate no probada en vivo. Domo: auditar el máximo de
  los tres inscritos antes de sustituir selección por dos combatientes
  (dome_party); no declarar esa composición solo por probar dos niveles.

No hay decisión externa que pedir: tarea **in_progress**, sin menús nuevos y
sin prueba de consola. La regresión de otras instalaciones/historia se mantiene
para el recorrido de la alfa por instrucción del usuario.
