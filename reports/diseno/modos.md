# Modalidades pendientes: Nivel Libre y Dobles

Diseño F9-MODOS-DISENO, Codex, 2026-11-11. Solo lectura estática y documentación;
no modifica juego, scripts de campo, parches ni reservas. Azahar y consola: **no
probados**. Las tareas de implementación están en
`frontier/orch/propuestas/modos.json`; este documento es su contrato.

## 1. Alcance y base comprobada

Nivel Libre Individual en las siete instalaciones; Dobles Nivel 50 y Libre en
Torre y Fábrica. **Multi queda fuera**, también Triple/Rotación, Dobles en las otras
cinco instalaciones y los dobles internos del Tubo. Sin nuevas zonas ni puertas.

Fuentes ORAS: `reports/frontier.md` §1–§4, §25, §28, §30, §35–§36;
`frontier/tower.py:reception_routine`, `factory.py:reception_routine`,
`patch.py:STREAK_SITES/STREAK_ROUTES/CONSTANTS` y `asm/rental.s`.
Relectura estática sobre la base Repolished validada por `maison_map.py`:

| Eje | Estado actual | Consecuencia |
| --- | --- | --- |
| Rango de la Mansión | `work+0x838`: 0 Normal, 1 Súper; cambia archivos N/S de rivales | No es el modo de nivel |
| Selector retail | `_CallTrialDownloadApp`, recepción `0x16fc`, devuelve aceptación, tipo y auxiliar `0x800C/D/E`; `GetRank` lee el rango | Hay que conservar su inicialización: omitirla en Torre ya hizo que rechazase todo el equipo (§25) |
| `SetRank` | DllField `+0x95e3c` → code `0x1e567c`: `strb r1,[r0,#0x838]; bx lr` | El setter no valida; escribir 2 no crea un tercer rango seguro |
| Tipo | `+0x839`: 0 Individual, 1 Doble, 2 Triple, 3 Rotación, 4 Multi | `StartBattle(0,1)` no significa «Individual»: usa el tipo del trabajo |
| Montador | `0x1e30b8`, salto `0x1e3158`: **tipos 0–3 → `0x1e0634`**; Multi tiene otro camino | Dobles puede reutilizar el montador ordinario; no convertirlo en Multi |
| Tamaño rival retail | `0x1e34d0`: 3/4/6/4/2 para tipos 0/1/2/3/4 | Tipo 1 ya permite cuatro rivales; verificar cuatro selecciones del jugador |
| Nivel del jugador | Copia privada en `0x1e3d2c`; cola `0x1e3ddc`, comparador 50 `0x1e3e00`, escritura 50 `0x1e3e2c` | Saltar solo el ajuste de nivel en Libre; conservar el resto de la cola |
| Nivel rival | Constructor `0x1ef904`, llamada rival `0x1e4e80` fija 50 | Hay que cambiarlo además del jugador; ya lo intercepta `pike_level` |
| Racha | Cuatro accesores `STREAK_SITES` de Individual; macro `FACTORY_SLOT` solo desvía rango 0 | Quitar el rechazo de Dobles de la recepción no basta: escribiría racha retail |
| Alquileres | `RENTALS=3`, `RENTAL_LEVEL=50`, tres works para jugador y tres para rival | Dobles Fábrica necesita parametrizar todo el camino, no subir una constante global |

Evidencia nueva en `work/frontier/modos/{maison-map,set-rank,selector,types,player-level}.txt`.
`maison_map.py` verifica hashes de code.bin `3999d658…` y DllField `23248ab0…`.
Las direcciones code.bin son VA (offset = VA − `0x100000`); las de CRO son offsets.
El selector solo tiene **dos rangos semánticos conocidos**, Normal/Súper. No se ha
medido su UI completa ni todos sus consumidores: queda por seguir el resultado de
su callback y el byte `+0x838` al confirmar/cancelar, sin asumir un rango 2.

Reglas de referencia fijadas a pret/pokeemerald
`731ad5bfd6e6f265508d0efcca0ba42f9dcf5881`:
[GetFrontierEnemyMonLevel y SetFacilityPtrsGetLevel, battle_tower.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/battle_tower.c),
[alquileres y rangos, battle_factory.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/battle_factory.c),
[PB y selección, frontier_util.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/frontier_util.c).
Copia consultada en `/tmp/frontier-cerebros-pokeemerald` (HEAD cotejado).

## 2. Contrato de niveles y recepción

Tres ejes separados: instalación (ruta actual 1–7), formato (0/1) y nivel (50/Libre).
El rango retail permanece **0**: `SetRank(0)` antes del desafío y después del
selector. No usar `SetRank(1)` como Libre: habilita Súper y no elimina el tope 50.
Tampoco codificar Libre como un valor nuevo de `+0x838` o como una ruta nueva:
rompería tablas, máscaras de Arena/Palacio y rutas de Tubo/Pirámide.

Recepción propuesta: si hay desafío pausado, ofrecer reanudarlo/abandonarlo con su
modalidad persistida antes de ofrecer otra; la exclusión mutua actual continúa.
Si es nuevo, menú Nivel 50/Libre, después selector retail para inicializar el tipo
y la selección (solo aceptar tipo 0, o 0/1 en Torre). Rechazar 2–4 y cancelar sin
borrar récord, racha pausada ni tocar PB. Fábrica conserva su draft propio y debe
inicializar tipo 1 de forma medida, sin abrir selección del equipo real. Si el
selector se muestra en Fábrica será solo para configurar el formato, nunca para
inscribir los Pokémon del jugador. El menú no debe presentar «Súper» como Libre;
si la UI retail no permite ocultarlo, informar del rango fijado o sustituir solo
su presentación después de medir la configuración mínima necesaria.

Definición propuesta:

- **Nivel 50**: mantener exactamente la adaptación actual (copia limitada a 50;
  Pokémon inferiores conservan su nivel). No añadir ahora el rechazo estricto de
  Esmeralda a Pokémon por encima de 50.
- **Libre con equipo propio**: conservar los niveles de los inscritos; rival a
  `L = max(60, máximo nivel de los inscritos)`, hasta 100. Fijar L tras selección
  y persistirlo durante el desafío. Sin subir al jugador a 60. Medir el máximo
  sobre la selección efectiva, incluida Caja de Combate, no sobre los seis de la
  partida. El C de Esmeralda escanea `gPlayerParty`; allí se reorganiza la party
  del desafío. En ORAS la selección es una copia y hay que hacer esa distinción.
- **Fábrica Libre**: alquileres **y rival a 100**, independiente del equipo real;
  fuente `SetRentalsToOpponentParty` y `CreateFrontierFactorySelectableMons`
  (`FRONTIER_MAX_LEVEL_OPEN`). No aplicar el mínimo 60 del equipo propio.

Hooks propuestos, a medir antes de escribir: desviar la rama de ajuste en la cola
`0x1e3ddc` solo con ruta válida y modalidad Libre activa; mantener normalización,
cálculos y copias posteriores. Nivel rival en la llamada a `MAKE_PARAM` debe
componerse con `pike_level`, el constructor de Cerebros y los sets forzados del
Domo. No cambiar todos los literales 50 ni `StartBattle` globalmente. Sin ruta,
ruta inválida, estado inactivo o modalidad corrupta: camino retail seguro; nunca
un acceso fuera de tabla. El acceso al nivel, recálculo de estadísticas y PS de la
copia se debe verificar antes de aplicar estados/PS del Tubo.

## 3. Estado, PB y reservas que debe pedir BASE en REPARTO

Claves de modalidad: `M=0` Individual 50 (existente), `M=1` Individual Libre,
`M=2` Doble 50, `M=3` Doble Libre. Solo Torre/Fábrica aceptan M=2/3.

Conservar works actuales y rutas para M=0: partidas antiguas leen modo 0 y siguen
funcionando. Añadir bancos de **racha y récord separados** para cada nueva clave.
No intercambiar bancos a mano al entrar/salir: el acceso debe resolver `(ruta,M)`
en cada lector/escritor, tanto nativo como script. El récord sigue en `S+2` si se
conserva el ABI de accesores; no reutilizar el hueco `S+1` como estado activo.

Solicitud simbólica (no asignación; **ningún ID numérico nuevo está reservado**):

| Reserva | Cantidad de works u16 | Uso |
| --- | --- | --- |
| `MODE_STREAK[f,M]`/`MODE_RECORD[f,M]` | 11 bancos de tres = 33 posiciones | Libre de las siete + Doble 50/Libre de Torre/Fábrica; S, hueco reservado, S+2 |
| `MODE[f]`, `LEVEL[f]` | 7+7 = 14 | Modalidad y nivel rival fijados para pausa/reanudación; estado activo sigue en `ACTIVE_WORK` |
| `FACTORY_SET3`, `FACTORY_RIVAL3` | 2 | Cuarto alquiler y cuarto rival; no suponer que los works adyacentes a los tres actuales están libres |
| `FACTORY_RENTS[M]` | 4 | Contador de cambios/alquileres acumulados por modalidad para promoción de rangos |
| Total inicial | **53 posiciones** (42 valores usados + 11 huecos) | Sin contar símbolos de F8, textos/casos ni posibles temporales de interfaz |

BASE debe ejecutar `frontier/ids.py`, cotejar REPARTO actualizado (incluidos los
candidatos 16729–16731 de Cerebros), descartar bloques que el juego limpia por
rango (16410–16414, §25), comprobar persistencia con guardar/recargar y registrar
reservas **antes de usarlas**. No pedir contigüidad de todos los bancos, solo S/S+2
si se conserva ese ABI. Confirmar el requisito de contadores de cambios frente al
estado real de Fábrica al implementar; actualmente `factory.py` no tiene uno
persistente por modalidad. Textos ES/EN y cualquier GlobalCall adicional se
reservan también en REPARTO antes de escribirlos.

Desviar accesores Dobles: localizar incremento, lectura, puesta a cero y récord
por llamadas desde `GetMyWinCount/AddWinCount/ClearWinCount/GetWinCount` con tipo
1. No inventar sus direcciones extrapolando las de Individual. Revisar también
`SetTrainer`, rank brackets, `IsBoss`, cartel y todos los `GetMyWinCount(0,0)`
actuales. Si se usa tipo 1 real en el montador, el script no puede leer el banco
Individual por seguir pasando ceros. Ruta 0 debe conservar ambos formatos y
rangos retail sin ninguna escritura en los works del Frente.

PB se añaden al saldo único del jugador; la **racha que decide la recompensa es
la de la modalidad**, no una bolsa de PB por modo. Libre usa la misma columna de
PB que Nivel 50. La tabla existente `data.FRONTIER_BP` contiene solo Individual:
extraer una segunda columna de `sBattlePointAwards`, no sumar 1 sin saturar.
Torre Doble: `min(ronda+1,15)` con ronda desde 1; Fábrica Doble: Individual+1 con
tope 15 (primeras rondas 4,4,5,5…, última 15). Contrastar las 30 filas.

Unidades sin cambios: Torre/Fábrica/Palacio/Arena cada siete victorias, Domo cada
cuatro victorias (un torneo), Tubo cada catorce salas, Pirámide cada siete pisos.
Premio solo al completar unidad; pausa/recarga no repiten PB. Derrota/abandono
borra solo racha activa, conserva récords y símbolos y limpia datos transitorios.
Cambiar de modalidad tras cerrar el desafío no hereda racha de otra ni reinicia
su récord; la política actual de iniciar una nueva racha tras abandono sigue.
Saturación de contadores medida, sin overflow u16 ni cambios retroactivos de M=0.

Cerebros: F8 define símbolos únicos por instalación, no por modalidad. Habilitar
sus umbrales en **Individual Libre** con nivel L (100 para Noland), mismos equipos
e IV/EV de F8 y racha del banco Libre; Dobles sin Cerebro ni bonus +10. Evitar
que reaparezca el jefe de Mansión en el combate 20. Pausa de jefe pendiente de
Pirámide conserva modalidad/nivel. F9 depende de F8-BASE y debe adaptar su API,
no introducir un constructor paralelo de jefes.

## 4. Nivel Libre por instalación

| Instalación | Reutiliza | Cambios y mediciones específicas |
| --- | --- | --- |
| Torre, ruta 2, zona 329 | Selección, copia, rondas, rival Mansión | Quitar ajuste a 50, fijar L por selección y Caja, banco M=1, Anabel con nivel L |
| Fábrica, ruta 1, zona 213 | Draft seis, intercambio, IV por ronda, copia privada | M=1, nivel 100 en alquiler y rival, rangos Libre, Noland nivel 100; no consultar máximo del equipo real |
| Palacio, ruta 3, zona 340 | Selección y motor B/C | L, M=1; conservar bit30 y filtro naturaleza/PS, cuyo umbral porcentual debe funcionar a nivel 60–100; sigue tipo 0 |
| Arena, ruta 4, zona 457 | Selección, bit31 y juicio a tres turnos | L, M=1; medir PS iniciales del nuevo nivel, sin arrastrar referencias a PS de nivel 50; cambio prohibido intacto |
| Domo, ruta 5, zona 456 | Inscripción de tres, preview y elección de dos, cuatro rondas | Calcular L de los **tres inscritos**, fijarlo todo el torneo; preview/equipo forzado/jefe coinciden; dos combatientes siempre |
| Tubo, ruta 6, zona 458 | Tres inscritos, salas, PS/PP/estados y slots virtuales | L, M=1; combate duro al nivel L, salvaje a L−4 o L−5 según set, adaptación del actual 46/45 (§35); aplicar PS después de recalcular a L, persistir L por las catorce salas |
| Pirámide, ruta 7, zonas 140–142 | Tres seleccionados persistentes, pisos, vencidos | L y M=1 sobreviven destrucción del work y cambios de piso; no seleccionar de nuevo en cada planta; Brandon usa el mismo L; bolsa/oscuridad/salvajes nuevos quedan fuera |

Los rangos Libre de Fábrica no son «los mismos pero a 100». En la referencia,
`sInitialRentalMonRanges[8..15]`: cuatro rangos fuertes (372–467, 468–563,
564–659, 660–755), después unión fuerte con legendarios (372–881), repetida hasta
la octava ronda y siguientes. Adaptación a Mansión: primeras cuatro rondas las
cuatro copias fuertes `maisonpkS` ya mapeadas en §7; quinta+ unión fuerte que
incluya los legendarios compatibles. **La correspondencia exacta de 850–881 no
está medida**: tarea Fábrica debe identificar sus equivalentes ORAS, documentar
exclusiones y producir una tabla propia; no escoger índices por aritmética.
La promoción por cambios usa el rango siguiente (tope último), IV de la ronda y
contador del banco activo, sin alterar los rangos Nivel 50 entregados. El rival
ordinario aún generado por Mansión es una desviación existente; en Libre debe
usar el nivel correcto y documentar rango/IV observado, sin declarar paridad con
Esmeralda por haber corregido solo el nivel.

## 5. Dobles de Torre y Fábrica

Torre: aceptar tipo **1**, cuatro elegidos del equipo/Caja, dos en campo y dos de
reserva; rival cuatro mediante montador de tipos 0–3 (§1). Confirmar que la app
configura `+0x48=4`, índices `+0x30` válidos y `+0x839=1`, y que las comprobaciones
de especie/objeto/huevos funcionan con cuatro. No tocar máscaras de Palacio o
Arena ni convertir cuatro Pokémon en cuatro clientes. Medir órdenes a ambos
activos, objetivos aliados/rivales, cambio de ambas posiciones y reemplazo tras
KO; un combate normal Individual no cubre esos caminos.

Fábrica: elegir **cuatro de seis**, sin repetidos; cuatro rivales, oferta de cambio
uno por uno de los cuatro vencidos, se puede no cambiar. Cuarto ID con los mismos
bits de archivo/habilidad que los otros, guardado antes del combate y estable al
reanudar. Adaptar draft, textos, menús, bucles, count `+0x48`, constructor de
alquileres, captura de rivales, validación del intercambio, semillas y limpieza.
`WORK_SETS` y `WORK_RIVAL` hoy se leen como bloques contiguos: con cuarto work
separado hay que pasar a una tabla o a un acceso explícito; no leer el vecino.
No aumentar `data.PARTY_SIZE` globalmente: rompería Individual y otras instalaciones.

**Adaptación pedida por esta tarea:** Fábrica Dobles de Esmeralda conserva
`FRONTIER_PARTY_SIZE` (tres), según `SetRentalsToOpponentParty` y el constructor
`FillFactoryFrontierTrainerParty`. Aquí serán **cuatro**, conforme al criterio de
aceptación y a la Mansión. Las tablas de PB sí serán las de Dobles de Esmeralda.
M=2 usa nivel 50, M=3 nivel 100; en Torre Libre el nivel se deriva de sus cuatro
inscritos. No ofrecer Multi, compañero IA, comunicación, Triple ni Rotación.

## 6. Medidas pendientes, riesgos y aceptación

Antes de habilitar menús, BASE debe medir:

1. Callback del selector, rango 0/1 y auxiliar X: dónde fija tipo/rango/selección,
   cancelación y reanudación; configuración mínima equivalente para Fábrica.
2. Los cuatro accesores de racha Dobles y todos los consumidores script/nativos;
   máscaras de ruta y nivel válidos, ruta 0 Normal/Súper intacta.
3. Sitio de ajuste de nivel del jugador y rival, orden de recálculo/PS del Tubo,
   Caja de Combate y máximo de inscritos; constructor privado de Cerebros.
4. Espacio real tras integrar F8: foto de F8-DISEÑO = 2544/2556 bytes, **12 libres**
   en code.bin. No presupuestar hooks nuevos ahí sin reservar otra ubicación
   verificada o recuperar espacio con pruebas. Revisar límites ZO <=17248 y CRR.
5. Reserva y persistencia de works, sin reutilizar candidatos de otros diseños;
   la imagen del banco activo debe llegar a pisos y no depender de `WORK_ROUTE`
   guardado, que se limpia en recepción.

Riesgos principales: rachas Dobles escribiendo Mansión (alto), recálculo de nivel
que sanea PS o elimina estados del Tubo (alto), cuarto alquiler fuera de bloque
(alto), falta de espacio común (alto), pausas que cambian modo/nivel o duplican PB
(alto), selector con texto Súper engañoso y tamaño del script (medio), equivalencia
de conjuntos Libre y dificultad rival (medio). Cada uno bloquea la habilitación
de su modalidad hasta contar con evidencia; no bloquea esta entrega de diseño.

Tests previstos: VM de recepción/cancelación/exclusión mutua, M=0–3 y valores
inválidos; PB primera/última ronda y antes/exacto/después de los límites; Unicorn
de accesores de ambos formatos/rangos con route 0/1–7/inválida y bancos aislados;
constructores con niveles 50/60/73/100, equipo mixto y Caja; cuarto alquiler e
intercambio en posición 4, sin tocar partida/equipo originales; símbolos y pausa
pendiente, reconstrucción de scripts y guards de bytes. Con partida anterior sin
works nuevos, M=0 debe conservar resultados y todas las rachas/records existentes.

**Regresión del usuario (2026-11-11)**: suite completa obligatoria en cada hito.
Diseño actual: sin laboratorio. Futuras tareas solo de script/textos: instalación
modificada; motor/code.bin/CRO/asm/patch: un combate Palacio, Arena, Tubo e historia
además de las modalidades tocadas; isla/construcción común: plaza y puertas que
puedan cambiar. Recorrido completo solo al preparar paquete para consola. Evitar
repetir la misma regresión dentro de un hito integrado, guardando los hashes de
la build exacta y evidencias de cada caso. No llamar «probado» a una modalidad
cubierta solo por VM: Azahar debe medir tipo, cantidades y niveles efectivos.

Estimación orientativa en sesiones con suite/evidencia/commit: BASE común 3–5;
Libre Torre/Palacio/Arena 2–3; Libre Fábrica 2–4; Libre Domo/Tubo/Pirámide 3–5;
Dobles Torre 1–2; Dobles Fábrica 3–5. Total **14–24 sesiones**, más si falta una
cueva segura o el selector no permite separar nivel y rango. Sin plazo de reloj
ni tiempo de emulador prometido. Serializar los cambios del motor común aunque
`owner:any` permita relevo entre agentes.

## 7. Tareas y relevo

El JSON contiene seis tareas nuevas, con dependencias y aceptación concreta:
BASE → Libre de equipo propio y Libre especial/Fábrica → Dobles Torre → Dobles
Fábrica. La cadena deliberadamente evita dos carriles modificando el mismo motor
a la vez. Todas dependen transitivamente de F8-CEREBROS-BASE; esa tarea ya está en
la cola y debe terminar antes de reservar espacio o adaptar su constructor.

El integrador puede encolarlas con
`frontier/orch/frontier-orch add frontier/orch/propuestas/modos.json`.
Este diseño **no ejecuta add**, no edita tasks.json ni el turno/tabla de REPARTO.
Antes de encolar, cotejar IDs contra la cola vigente; `check_task` y dependencias
se verifican en esta entrega, no se garantiza una cola futura sin duplicados.

Verificación de esta entrega: `env -u ORCH_LANE bash -c 'source scripts/env.sh;
python -m pytest -q tests'` → **1105 passed, 1 skipped**, 39,97 s
(`work/frontier/modos/tests.log`). Seis propuestas aceptadas por `check_task` contra
IDs de la cola actual, dependencias anteriores o existentes, sin ciclos ni IDs
duplicados (`work/frontier/modos/design-check.txt`). `git diff --check` correcto.
No se ejecutó laboratorio, build, parche, encolado ni implementación de modos.

Para reproducir las lecturas nuevas, tras `source scripts/env.sh`:

```bash
python frontier/maison_map.py
python frontier/disasm.py baseline/oras/repolished/romfs/DllField.cro 957fc 180
python frontier/disasm_code.py baseline/oras/repolished/exefs/code.bin 1e567c 12
python frontier/disasm_code.py baseline/oras/repolished/exefs/code.bin 1e3158 120
python frontier/disasm_code.py baseline/oras/repolished/exefs/code.bin 1e3ddc 65
```
