# F9 — Fábrica Individual Libre

## Hito 1: rangos y equivalencias antes de habilitar

Estado: **en curso**. `factory_open.py` define y valida los rangos, pero todavía
ninguna recepción ni draft lo consume. Nivel 50 conserva sus tablas y código.
Azahar y consola de esta tarea: **no probados**. No se ha iniciado laboratorio.

Fuente fijada a pret/pokeemerald `731ad5bfd6e6f265508d0efcca0ba42f9dcf5881`:
`src/battle_factory.c` (`sInitialRentalMonRanges`, `GetFactoryMonId`,
`GenerateInitialRentalMons`, `GetNumPastRentalsRank`),
`include/constants/battle_frontier_mons.h`,
`src/data/battle_frontier/battle_frontier_mons.h` y
`include/constants/pokedex.h`. Se leen los objetos del commit mediante `git show`,
no el árbol de trabajo ni un HEAD mutable. No se convierten las especies de GBA
por resta: el auditor usa los nombres de especie y el enum de Pokédex Nacional.

Reproducción (tras `source scripts/env.sh`):

```
python frontier/probes/modos/factory_reference.py /tmp/frontier-cerebros-pokeemerald
python frontier/modes_audit.py
```

Evidencia: `work/frontier/modos/fabrica/reference.json` contiene los hashes de los
cuatro ficheros fuente y de los cuatro GARC ORAS, rangos extraídos, tabla de
**510 IDs 372–881** con candidatos ORAS por especie y los 48 IDs sin equivalente
en los rangos fuertes elegidos. `fd.load()` exige los hashes del volcado de §7 de
`reports/frontier.md` antes de cotejar los conjuntos.

| Ronda Libre | Fuente Esmeralda | Adaptación ORAS (`maisonpkS`) | Conjuntos |
| --- | --- | --- | --- |
| 1 | 372–467 | 0–20 y 208–382 | 196 |
| 2 | 468–563 | 52–72 y 383–557 | 196 |
| 3 | 564–659 | 104–124 y 558–732 | 196 |
| 4 | 660–755 | 156–176 y 733–907 | 196 |
| 5+ | 372–881 | Unión de las cuatro copias y tabla de legendarios de abajo | 828 |

La fuente repite el último rango en rondas 5–8 y lo mantiene después. La API
`pool` representa esa repetición con un único último rango y tope; `draft_pools`
selecciona la siguiente copia para las primeras 0/1/2/3/4/5 ofertas con contadores
<15/<22/<29/<36/<43/≥43. No debe usarse el índice de rango para los IV: ronda 5
usa IV 15 aunque ya tenga la unión; las rondas 6/7/8+ siguen 21/31/31. La futura
VM debe medirlo al conectar el draft: por ahora solo se prueban los rangos.

## Corrección de 850–881 y selección de legendarios

El diseño llama «legendarios 850–881» a todo el tramo, pero los IDs de la fuente
son **850–859 Dragonite**, **860–869 Tyranitar** y solo **870–881** las variantes
5/6 de las seis primeras especies de la tabla siguiente. Las once especies
legendarias ya aparecen en 756–799; 800–849 añade variantes de especies que ya
están representadas. El auditor recorre también ese intervalo, sin suponer que
sea exclusivamente legendario.

| Especie | Nacional | IDs `maisonpkS` explícitos |
| --- | --- | --- |
| Articuno | 144 | 908, 928, 948, 968 |
| Zapdos | 145 | 909, 929, 949, 969 |
| Moltres | 146 | 910, 930, 950, 970 |
| Raikou | 243 | 911, 931, 951, 971 |
| Entei | 244 | 912, 932, 952, 972 |
| Suicune | 245 | 913, 933, 953, 973 |
| Regirock | 377 | 914, 934, 954, 974 |
| Regice | 378 | 915, 935, 955, 975 |
| Registeel | 379 | 916, 936, 956, 976 |
| Latias | 380 | 922, 942, 962, 982 |
| Latios | 381 | 923, 943, 963, 983 |

Son **44 conjuntos**, de forma base y cuatro movimientos no nulos, comprobados
contra el volcado. No usar 908–987 como bloque: entre ellos están las nueve
especies posteriores excluidas Cobalion 638, Terrakion 639, Virizion 640,
Tornadus 641, Thundurus 642, Heatran 485, Cresselia 488, Landorus 645 y Regigigas
486 (36 conjuntos). No aparecen como especies en el Frente de la fuente fijada.

Dragonite tiene candidatos ORAS 376/551/726/901; Tyranitar,
377/552/727/902. Ya pertenecen a las cuatro copias fuertes: la unión conserva
cada ID una vez. No multiplicar su probabilidad por las diez variantes de
Esmeralda. Cada ID fuente 850–881 figura explícitamente en el JSON con sus
cuatro candidatos medidos. Es una equivalencia **por especie y copia de Mansión**,
no igualdad de movimientos, naturaleza, EV ni objeto entre generaciones; no hay
correspondencia biyectiva para 10 variantes fuente y 4 variantes ORAS.

Se conserva la adaptación fuerte ya entregada, de 196 especies frente a las 96
de Esmeralda. Doce especies fuente no tienen conjunto en estas cuatro copias
fuertes ORAS: Fearow 22, Clefable 36, Golduck 55, Dodrio 85, Hypno 97, Rhydon 112,
Electabuzz 125, Magmar 126, Xatu 178, Misdreavus 200, Dusclops 356 y Glalie 362.
No se sustituyen silenciosamente por evoluciones; los 48 IDs fuente afectados
quedan documentados como excluidos. Las 84 restantes están representadas en
cada copia; la unión final incluye **207 especies ORAS**. Las diferencias de
movimientos y las especies adicionales son las de los rangos fuertes de §7.
Esto no corrige retroactivamente Nivel 50 ni añade legendarios a su rango final.

## Espacio y build exacta de este hito

`work/frontier/modos/fabrica/space-map.json` (`modes_audit.py`):

- code.bin: 2008 bytes en 0x579804–0x579fdc; **36 libres** hasta 0x57a000.
- DllBattle: termina en 0xd7b84; **1148 libres** hasta 0xd8000.
- Cerebros DllField: 0xf0480–0xf0a00; F9 usa 556 bytes hasta 0xf0c2c y tiene
  **980 libres** hasta 0xf1000.
- Reserva Luma **0x579604–0x579804 intacta**. Este hito no escribe ningún motor.

Build completa ejecutada:
`python frontier/overlay.py --out work/frontier/modos/fabrica/build-map`.
Registro `build-map.log`; los 28 archivos y sus hashes completos están en
`build-map-hashes.json`. Script 517 16036 bytes, ZO 16828; compartido 5 22147;
texto ES 637 69544; hook 2008. IPS SHA-256
`0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`;
DllField SHA-256 `eb70d036317eedf93cb36b8258c8cd496047cbe0b6e12462a88c46a3d9be2bb1`.
Es la build anterior a conectar Libre de Fábrica; construirla no constituye
aceptación jugable de esta tarea. No se ha instalado en el laboratorio.

## Continuación concreta

1. Reservar en REPARTO líneas nuevas del texto 637 después de 1127 para las 44
   etiquetas de legendarios y, si hace falta, un mensaje propio en 619 después
   de 196. Conservar todos los números de línea de Domo/Tubo/Pirámide/Cerebros.
2. Conectar recepción Individual 50/Libre y CONFIG[1]=0x164 para Libre (100), sin
   selector del equipo real; bancos `modes.bank(1,M)` y contador propio de
   `FACTORY_RENTS[M]`. No reutilizar 16429 como dato persistente: `WORK_STREAK`
   sigue siendo solo el paso temporal a GlobalCall.
3. Conectar pools/promoción/IV al draft, conservando el camino Nivel 50; preparar
   la repetición exacta para Noland. **Atención:** la repetición necesita el
   contador al generar las seis ofertas, no el contador después de cambios
   durante la ronda. Reservar un snapshot persistente si hace falta (candidatos
   libres: `modes_audit.py`), medirlo antes de usarlo. La fuente marca alquiler
   inicial/cambio y lo cuenta tras victoria (`SetBattleFactoryData`,
   `FACTORY_DATA_WIN_STREAK_SWAPS` condicionado por `sPerformedRentalSwap`);
   registrar explícitamente la política adaptada, no inferir +3 de tres elegidos.
4. VM de draft/cambios/cancelación, rango y replay de Noland; evitar especie y
   objeto repetidos también al cambiar. Los rivales ordinarios seguirán siendo
   de Mansión: medir y documentar rango/IV efectivos, además del nivel 100.
5. Build final, suite y aceptación Azahar de novedades requerida en el brief,
   incluidos ronda/PB, recarga y derrota/limpieza. Solo entonces marcar done.

Verificación del hito: `env -u ORCH_LANE python -m pytest -q tests` → **3313 passed,
4 skipped**, 59,57 s (`tests-map-final.log`), con los 135 casos nuevos y el cotejo
contra la fuente local fijada ejecutados. `git diff --check` correcto.

## Hito 2: draft Libre y replay de las ofertas (sin habilitar recepción)

Estado: **en curso**. El script compartido ya consume los rangos Libre cuando
CONFIG[1] es exactamente `0x164`. La recepción todavía no ofrece Libre ni escribe
esa configuración; por tanto esta build no entrega aún una modalidad jugable.
No se ha iniciado laboratorio; Azahar y consola de F9 Fábrica siguen **no probados**.

Reservas previas al uso registradas en REPARTO: snapshot **16471** del contador
al generar las ofertas; etiquetas legendarias **1134–1177** del texto 637. El
guard de la primera build rechazó la reserva prevista 1128–1171: las líneas
1128–1133 ya las emite `brains.lines` como preview de Tucker/Domo. Se corrigió la
reserva antes de construir y se preservaron esas seis líneas. Fuente:
`brains.line_base() = 1072`, `len(brains.lines(7)) = 62`,
`dome.brain_preview_lines`. Esta medida corrige la continuación del hito 1.

Implementación:

- `factory_open.install_data`: tabla privada de slots con los **926** anteriores
  intactos y los 44 legendarios añadidos en orden creciente de ID ORAS. Mantiene
  las ocho parejas (inicio, cantidad) Nivel 50 sin alterar y añade cinco parejas
  Libre. Rechaza datos de entrada que no coincidan con el volcado validado.
- `factory_open.select_range`: para cada oferta, toma el rango Libre de su ronda
  y lo promociona al siguiente para las primeras 0–5 ofertas según 15/22/29/36/43
  cambios. Tope en la unión final. CONFIG distintos de 0x164 conservan el camino
  de Nivel 50; su rechazo en recepción está pendiente. Los IV se calculan antes,
  con la ronda real limitada a ocho, sin depender del rango promocionado.
- `factory_draft`: lee `FACTORY_RENTS[1]`, guarda su snapshot en 16471 solamente
  tras elegir los tres y guarda semilla/IV/IDs. Cancelar cualquiera de los tres
  menús conserva equipo, semilla y snapshot previos. El contador aún no se
  incrementa ni se inicializa: conexión a inscripción/intercambios pendiente.
- `factory_brain`: repite las seis ofertas con semilla y snapshot, aunque haya
  cambiado el contador desde el draft. Genera después tres conjuntos de la ronda
  sin promoción, distintos de los seis IDs ofrecidos, sin repetir especie/objeto
  entre ellos (los objetos cero no restringen el trío, como antes). Se reutiliza
  el constructor F8: en este hito no cambia ningún ARM/CRO.
- Los nombres de los nuevos alquileres resuelven tanto en draft como en menú de
  cambio, sin desplazar los textos de otras instalaciones. El intercambio aún
  necesita filtro de duplicados y cómputo de cambios antes de habilitar Libre.

Pruebas nuevas: `tests/test_frontier_factory_open_vm.py`, **177** casos. Ejecutan
Pawn para 120 combinaciones de ronda/contador, IV, tope, tres de seis, ausencia de
especie/objeto repetido, cancelación, aislamiento de bancos, replay con contador
mutado, repetición de Noland estable, rechazo de CONFIG no soportados por esta
rama, 44 etiquetas de intercambio y una selección real de legendario en VM.
Los tests previos siguen comprobando draft Nivel 50 y replay antiguo.

Build ejecutada con `python frontier/overlay.py --out
work/frontier/modos/fabrica/hito2/build`; registro `hito2/build.log` y **28 hashes**
completos en `hito2/build-hashes.json`. Script 517 **16036**, ZO **16828**;
compartido 5 **24978**; texto ES 637 **71780**; hook **2008** bytes.
IPS SHA-256 `0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`;
DllField `eb70d036317eedf93cb36b8258c8cd496047cbe0b6e12462a88c46a3d9be2bb1`;
compartidos a/0/2/9 `be4a6e0937b89a450c8d64c4a5d8b78593acba481692cb626c393100f3838deb`.
Build sin instalar. `hito2/audit.json`: code **36 libres**, Battle **1148 libres**,
Field F9 **980 libres**; reserva Luma 0x579604–0x579804 intacta. El auditor incluye
el snapshot como reserva adicional a los 35 works de BASE (no lo ofrece libre).

Continuación desde este hito:

1. Recepción sin selector del equipo real: elegir Individual 50/Libre, escribir
   CONFIG=0/0x164, bancos propios, validar CONFIG pausado y preservar equipo/IV/
   semilla/snapshot al cancelar una reanudación. Medir presupuesto ZO: margen
   actual 420 bytes frente al máximo comprobado 17248; mover helpers al compartido
   si hace falta, reservando cualquier caso/texto antes de usarlo.
2. Conectar contador por modalidad y saturación; no contar tres por draft.
   Fuente fijada: `battle_factory.c` 259–264 solo actualiza con
   `sPerformedRentalSwap`; `BattleFactoryBattleRoom/scripts.inc` 91–98 y 175–180
   intentan +1 tras victoria. Hará falta una marca persistente de alquiler/cambio
   pendiente de victoria (reservar y comprobar antes de usar). Determinar marcado
   inicial con scripts/screen de la fuente; no afirmar todavía que se reproduce.
3. Intercambio: filtrar especie/objeto contra los dos conservados, no contar
   «No cambiar»/B ni elección inválida; nueva racha limpia solo contador/banco
   activo, derrota conserva récord y limpia transitorios. VM recepción/premios,
   pausa/recarga y símbolos/bonus de Noland Libre.
4. Suite, build final y aceptación Azahar del brief: draft/combate/cambio a 100,
   rango/IV ordinario medido, ronda/PB, guardar/cargar y derrota. Regresión solo
   novedades según usuario 2026-11-13; recorrido alfa y consola no probados aquí.

Verificación final del hito 2: `env -u ORCH_LANE python -m pytest -q tests` →
**3490 passed, 4 skipped**, 62,05 s (`hito2/tests-green.log`). La pasada inicial
`hito2/tests.log` detectó la colisión del texto antes de corregir LINE_BASE; la
siguiente `hito2/tests-final.log` detectó una aserción del test de overlay que
presuponía que Cerebros era el último bloque. El test ahora comprueba por separado
el bloque íntegro de Cerebros y los 44 nuevos textos en los ocho idiomas, sin
relajar las comprobaciones de prefijos ni de otras entradas. Pasada final verde
tras ambas correcciones y los 177 casos nuevos; `git diff --check` correcto.

## Hito 3: alquiler pendiente de victoria e intercambio Libre

Estado: **en curso**. Recepción Libre todavía cerrada. Se han implementado y
probado en VM los dos requisitos que faltaban dentro del draft/intercambio.
Azahar, persistencia del nuevo work y consola: **no probados**; laboratorio no
iniciado y build sin instalar.

La fuente fijada aclara el alquiler inicial: `data/maps/
BattleFrontier_BattleFactoryPreBattleRoom/scripts.inc:40` llama
`factory_setswapped` **antes** de seleccionar tres. En el mismo archivo, línea
154, un intercambio confirmado vuelve a marcarlo. `BattleFrontier_
BattleFactoryBattleRoom/scripts.inc:91–98` y `175–180` intentan incrementar
tras victoria ordinaria/Noland; `src/battle_factory.c:259–264` solo escribe el
contador si hay marca y la consume. Objetos Git leídos del commit completo
731ad5bfd6e6f265508d0efcca0ba42f9dcf5881: copias locales `hito3/source-{0,1,2}.txt`
y SHA-256 por fichero en `hito3/accounting-source.json`.

Reserva **16673** anotada en REPARTO antes de usarla y añadida al auditor. Es una
marca persistente: 1 para Individual 50, 2 para Individual Libre, 0 sin alquiler
pendiente. El draft completo y el cambio confirmado marcan una unidad; no
incrementan el contador. La victoria posterior consume la marca y acredita +1
al banco `FACTORY_RENTS[M]`, con saturación 65535. Una marca corrupta o de otra
modalidad se descarta sin sumar. Cancelar draft/cambio o «No cambiar» no crea
marca; ejecutar de nuevo el callback sin otra marca no suma. La recepción actual
Nivel 50 limpia su contador al empezar; los caminos comunes de abandono/derrota
limpian la marca antes de guardar. La inscripción Libre aún debe inicializar
su banco propio. El draft Nivel 50 conserva exactamente sus rangos, IV y menús;
se añade contabilidad sin promoción retroactiva.

`factory_swap_meta` usa una tabla privada generada del volcado validado: dirección
por archivo e ID, sin los bits de habilidad. En Libre se rechaza el cambio si
la especie o el objeto no nulo se repite con cualquiera de los dos conservados.
El hueco reemplazado se excluye de la comprobación; IDs fuera de los archivos
tienen metadatos cero y se rechazan. Esta validación se ejecuta al confirmar la
selección; de momento el menú muestra también opciones que se rechazarán sin
cambiar el equipo. Pendiente mejorar su presentación al habilitar recepción.
Los tres Pokémon del rival resuelven ahora sus etiquetas por archivo igual que
los alquileres; al aceptar se conserva el bit Súper (necesario para Noland),
y se sortea solo la habilidad. Nivel 50 conserva su política previa de
intercambio; no se activa allí el filtro nuevo de especie/objeto.

Pruebas nuevas: `tests/test_frontier_factory_lifecycle.py`, **50 casos VM**:
draft inicial, cancelación, marca única, consumo tras victoria, saturación,
bancos aislados (también los dos Dobles), récords intactos, configuración corrupta,
cruce N/S de la misma especie, objeto repetido de otra especie, cambio a un
legendario Súper en cada posición, crédito diferido y cancelación/ID inválido.
Los 237 casos anteriores de draft/intercambio/replay también pasaron.

Build exacta: `python frontier/overlay.py --out
work/frontier/modos/fabrica/hito3/build`, registro `hito3/build.log`.
Script 517 **16256**, ZO **17048** (200 bytes hasta el máximo comprobado 17248);
compartido 5 **31077**, texto 637 ES **71780**, hook **2008**. Los 28 hashes están
en `hito3/build-hashes.json`; IPS
`0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`,
DllField `eb70d036317eedf93cb36b8258c8cd496047cbe0b6e12462a88c46a3d9be2bb1`,
compartidos `3e0fd0ce562d7cf2ba3d0b3895206988dc9519a3246f0e8ec0d9e180a5e47ec9`.
Auditor `hito3/audit.json`: code 36 libres, Battle 1148, Field F9 980; reserva
Luma 0x579604–0x579804 intacta; candidatos restantes 16677/16678. Ningún
ARM/CRO ni fichero de construcción común modificado.

Continuación: recepción 50/Libre con CONFIG válido y bancos propios; cancelar
reanudación debe conservar alquileres/semilla/IV/snapshot/marca. Limpiar solo
racha/contador activos en abandono/derrota y preservar récords/símbolos. El margen
ZO ya es 200 bytes: probablemente hará falta llevar menú y preparación al
compartido; **9779 aún no está reservado ni usado**, 9770–9778 ya tienen dueño.
No reutilizar WORK_STREAK para transportar operaciones de menú pausado: contiene
la ronda que necesita el replay de Noland. Reservar cualquier caso/texto nuevo
antes de escribirlo. Después VM recepción/PB/símbolos y toda la aceptación
Azahar del brief, incluida medición del rango/IV ordinario, guardar/cargar y
derrota. No marcar done antes. Regresión agrupada 2026-11-13: solo novedades.

Suite final: `env -u ORCH_LANE python -m pytest -q tests` → **3540 passed,
4 skipped**, 65,50 s (`hito3/tests-green.log`). La primera ejecución sin quitar
ORCH_LANE falló en nueve tests del supervisor por heredar el carril real
(`hito3/tests.log`); 3531 pasaron. Sin cambios al supervisor; repetición con el
entorno aislado usado en los hitos anteriores, verde. `git diff --check` correcto.

## Hito 4 — recepción Individual 50/Libre y bancos (2026-11-14, en curso)

Reserva previa en REPARTO: GlobalCall **9779** y texto637 **1178–1185**.
`factory_reception.py` lleva el menú al compartido para respetar el límite ZO.
Una inscripción nueva ofrece 50/Libre/cancelar y ejecuta el draft real; solo
tras elegir tres se reinician racha y contador de la modalidad elegida. Los
récords y otros tres bancos se conservan. Cancelar cualquiera de los menús
restaura CONFIG, contador y WORK_STREAK; el draft conserva semilla, snapshot,
alquileres, IV y marca. No se toma el máximo del equipo real.

Con WORK_IV activo, CONFIG 0/50/0x164 permite reanudar/abandonar/cancelar.
Reanudar o cancelar conserva todos los works; rechazar la confirmación retail
al reanudar también. CONFIG pausado incompatible se rechaza conservándolo.
Abandonar borra solo la racha/contador activos y los works temporales del
desafío, nunca récords/símbolos. La limpieza retail de derrota conserva el
enrutamiento hasta ClearWinCount: no se anticipa el borrado de la racha antes
de actualizar el récord. Los caminos comunes limpian el contador activo.

VM nueva `tests/test_frontier_factory_reception.py`: **41 casos**, usa el draft
real en compartido y el adaptador de zona; cancelación de cada menú, bancos,
configuración inválida, pausa, confirmación y limpieza del contador. Suite final
`env -u ORCH_LANE python -m pytest -q tests`: **3581 passed, 4 skipped, 93.85 s**
(`hito4/tests-final.log`; ejecución previa verde 66.23s en `tests.log`). Probe
`frontier/probes/modos/fabrica.py`: fixtures nuevas en work/, origen con hash y
checksum validados, snapshot y GDB pasivo. `py_compile` y comparación exacta con
`hito4/probe.gdb` correctos. No escribe memoria del emulador.

Build exacta `python frontier/overlay.py --out work/frontier/modos/fabrica/hito4/build`,
`hito4/build.log`: script517 **16308**, ZO **17100** (148 bytes de margen hasta
17248), compartido5 **31874**, ES637 **72360**, hook **2008**. Los 28 hashes en
`hito4/build-hashes.json`. IPS y DllField idénticos a hito3; compartidos
`1baa8e18b62959a9b1a024111f9288048c52b023fa11c8f53245c720f605f513`.
Auditor `hito4/audit.json`: reserva Luma intacta, espacio de motor como hito3.
`overlay.py` solo añade los ocho textos de recepción al final; no mueve líneas
anteriores ni cambia la isla. Regresión agrupada 13nov: solo Fábrica nueva.

Azahar parcial, laboratorio propio puerto24691. Fuente fixture
`work/frontier/modos/base3/tower73.sav`, SHA256
`7a8c2cc32aa3d084eac64ef087e8963f97b3640f9474c63afef508b2212cdd72`;
`hito4/fresh.sav/json` conserva equipo 73/55/41 y cajas. Instalación de los
28 archivos de la build anterior en el mod del laboratorio. Recepción Libre,
draft y combate arrancan sin selector real (`draft-menu.png`, `battle100.png`).
`registered.sav/json`, guardado retail de inscripción, valida 58 bloques:
CONFIG=356, IV=3, marca=2, snapshot=0, contadorLibre=0/rachaLibre=0/récordLibre=6;
50 conserva racha12/récord20/contador22 y los bancos Dobles también se conservan.
Hashes de equipo y cajas idénticos a fresh.json.

GDB (`probe.gdb`, registro de laboratorio que se preservará al cerrarlo) mide
alquileres S283/S14/S309, especies346/671/437, **nivel100/IV3**, y rival ordinario
N50/N20/N44 (Fletchinder/Pansage/Stunky), **nivel100/IV3**, entrenador N43.
`ordinary-rival.json` documenta el archivo guardado por hash de data.load y el
pool permitido del entrenador: N0–65 en esta ronda. Desviación explícita: el
rival ordinario conserva rango e IV de la Mansión; no usa las copias fuertes
Libre del draft ni el generador de Esmeralda. No extrapolar esta medición a
rondas posteriores. Noland tiene su generador independiente del hito2.

Primera victoria real sin asistencia: GDB `BRAINS RESULT raw=1` en
`hito4/azahar-first.log`. Antes del intercambio: rachaLibre=1, contadorLibre=1,
marca=0; los otros bancos conservan valores. Cambio Cradily por Fletchinder N50
confirmado (`swap-done.png`); pausa retail y `paused.sav/json`: 58 bloques válidos,
SHA256 `0d612535ec624e0c14cbe28024fc86315c8d2f9bf6ef0853064c186dbac4af10`,
primer alquiler=50, contadorLibre=1, marca=2, rachaLibre=1/récordLibre=6,
IV3, snapshot0. Equipo y cajas conservan sus hashes; PB3 sin premio entre rondas.
Tras cerrar y arrancar Azahar de nuevo, carga retail del mismo guardado y menú
Reanudar/Abandonar/Cancelar (`resume-menu.png`). Cancelar con B conserva los
works medidos en `FACTORY RELOAD CANCEL` (`azahar-reload.log`): CONFIG356,
racha1/récord6/contador1/marca2, alquileres50/33806/33077, IV3/semilla37001/
snapshot0; contadores ajenos22/24/25 intactos.

Reanudar acepta el guardado sin otro draft ni selector real: GDB carga N50 del
archivo182 y S14/S309 del184 y crea los tres a **100/IV3**; rival ordinario
N3/N13/N44 (Bunnelby/Swinub/Stunky), entrenador13, también **100/IV3**.
`resume-level100.png` muestra Fletchinder100 contra Bunnelby100. Semilla37001,
alquileres, marca pendiente y bancos siguen intactos hasta el combate.

Pendiente de Azahar: cierre de ronda/PB y derrota con limpieza
del banco activo y récord conservado. Pendiente mejorar presentación del
intercambio incompatible (hito3). VM de PB: test_frontier_factory.py comprueba
rondas7–700 y ausencia dentro de ronda; símbolo/bonus Noland una vez en
test_frontier_factory_brain.py, dos callbacks consecutivos pagan solo10. Motor
Libre100 en test_frontier_modes_engine.py; replay con snapshot en
test_frontier_factory_open_vm.py. Todos incluidos en la suite anterior. Consola no probada. Estado de tarea in_progress.
