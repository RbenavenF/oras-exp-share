# F11-ISLA-ACABADO: candidato aislado (2026-11-14, Codex)

Estado: en curso. El candidato no forma parte del constructor de producción todavía.
Se respeta la asignación del brief: `island_build.py`, `overlay.py` y `faraway/java/`
los modifica quien integra. Este carril aporta piezas, selección, prueba empaquetada
y un diff generado de los cuatro puntos de integración; no modifica esos ficheros.

## Reproducir

```sh
source scripts/env.sh
python frontier/overlay.py --out work/f11/finish/base/out \
  --romfs dist/held-exp-share-v0.5/mods/000400000011C400/romfs
python frontier/probes/island/landscape.py --name review --fresh-movement
python frontier/probes/island/lab_mod.py work/f11/finish/review
env -u ORCH_LANE python -m pytest -q tests
```

El primer comando genera la isla vigente; el segundo copia su game/workspace,
compila una copia de `FrontierIsland.java` con las funciones de `IslandLandscape`,
y reconstruye solo su exterior. Los originales se leen. Las cuatro sustituciones
exigen coincidencia única para detenerse si cambia el constructor.
`work/f11/finish/review/integration.diff` es el diff revisable. `sources.json`
registra revisión, hashes de constructor, plan y archivos de entrada.
El corredor reemplaza únicamente su subdirectorio de ensayo; `base` está reservado.

## Cambios y medidas

- La escalera blanca **sí tenía** `chip_steps01` en AD229[11]. El material
  `chip_steps01a` usa la proyección de mundo 1/72, que recorre la zona blanca
  del atlas. `IslandLandscape.stairs` limita las UV a la banda de piedra
  x65–126/y98–125 del atlas retail 128×128: U=1-x/128, V=y/128.
  `TextureCodec.flipToBgra` exporta la imagen girada 180 grados; el sampler ya
  recorre V de abajo arriba, pero hay que deshacer el giro de U. Las hipótesis
  anteriores `dense` y `flags` todavía salían blancas: se descartan. **`final`
  muestra piedra gris en Azahar y se cruza la rampa de Arena en ambos sentidos**
  (`work/f11/proto/finish-final/at_110_37.png`, `at_110_39.png`). No añade textura.
  Fuentes: `LandscapeAudit.java`, `work/f11/finish/flags-stairs-audit.log`,
  `tools/CTRMap-F5/src/ctrmap/formats/h3d/texturing/TextureCodec.java`,
  `work/f11/finish/final/uv-only-proof.log` y `work/f11/finish/final-walk.out`.
- Baldosa: material retail `tokusane_miti` del contenedor del Resort, compartido
  con los edificios. Los huecos B se cubren con baldosa, excepto la caja de la
  Pirámide (x122–136/y11–20), que lleva arena. **B sigue en GRID y la reserva
  de cada edificio no se consume.** Las vallas dejan de tener roca debajo.
- El agua del calco ya existía en la construcción anterior: material `ctr_water`,
  textura `enkei_sea01` presente en AD229[11]. Se conserva en canales y estanques.
  La vista cenital de ambos modelos lo comprueba; no se afirma que antes faltase.
- 361 piezas del catálogo ORAS: 23 árboles +20 estrechos, 136 arbustos +100
  estrechos, 68 tramos de valla, 8 parterres y 6 banderas Aqua.
  Árbol y arbusto: `chip_wood_b`; valla: `chip_saku02` y `chip_saku02b`;
  parterre: `flower01` de la Liga. Se excluyen suelo, bordes y sombras del recorte
  retail para no tapar el piso. Variantes estrechas escalan X/Z a 0,5, no Y.
  No se generan imágenes ni se modifican los siete edificios provisionales.
- Cada pieza ocupa solo T/p/f, una altura y una celda. No invade pasos, agua,
  puertas ni B. La selección es determinista y distribuida; se conserva en
  `final/placements.txt`. No se intenta llenar todos los bloques del calco:
  los límites explícitos mantienen el presupuesto de carga.

Presupuesto medido por `FrontierPlaza.loadBudget` sobre el archivo construido:

| Ensayo | Total | Mundo | Props | Modelos |
| --- | ---: | ---: | ---: | ---: |
| F11 vigente | 3.534.592 | 654.336 | 209.152 | 2.671.104 |
| Acabado dense (sin banderas, V inicial) | 4.101.760 | 818.560 | 209.152 | 3.074.048 |
| Acabado final (mismas piezas que flags) | 4.151.040 | 835.328 | 209.152 | 3.106.560 |

Quedan **41.344 bytes** respecto a ISLAND_BUDGET 4.192.384. WorldTextures: `{}`.
Fuentes: `base-build.log`, `before-world.txt`, `dense/build.log`, `final/build.log`. Los incrementos
por colocación se imprimen en el último log; no equivalen al coste de textura,
que se comparte una sola vez en el world pack. La variante `flags` añade 49.280
bytes sobre `dense`: +16.768 de world pack y +32.512 de modelos, descontando dos
tramos de valla que ya no caben sobre las casillas ocupadas por las banderas.
Las banderas conservan el emblema Aqua: es la pieza disponible más próxima,
no un recurso propio ni una reproducción de los banderines amarillos. Fuente
del descarte Magma y del coste de texels (16.384): `LandscapeAudit.java`,
`work/f11/finish/audit.log`, `audit/tex-{207,80,210}-flag.png`.
ZO209: 11.288 bytes (límite 17.248).

`final/movement-proof.json` verifica los GARCs resultantes: archivo completo de
zonas a/0/1/3 idéntico (SHA256
`10a6c1c753533b151f8403711b405e87abbfb096b8fe723b17af598027b8d183`);
GR[0,2,3,4,5,6] idénticos para las ocho celdas originales 872–879 y nuevas
880–887. Solo cambia GR[1], geometría visual. Incluye hashes por celda.
No se modifica code.bin, CRO, asm ni la reserva Luma 0x579604–0x579804.

## Pruebas e integración pendiente

Suite de cierre: **2931 passed, 4 skipped**;
`work/f11/finish/tests-close.log` (duración al pie del log).
El entorno ORCH_LANE se retira para las pruebas del propio orquestador, que
necesitan arrancar sin pertenecer a un carril. No se omiten tests de juego.
Los tres nuevos tests validan ubicación/ausencia de solapes y reserva intacta,
rechazo de un constructor cambiado y rechazo de contenedores ajenos.

Comparación cenital nueva: `work/f11/finish/before-reference-after.png`, con la
referencia, F11 vigente reconstruida (`before.png`) y acabado (`final-topview.png`).
`TopView.java` representa los triángulos de los ocho modelos con el color medio
de su textura; **no es captura de Azahar ni permite juzgar el muestreo UV**.
Se sigue el método de la cenital de F11 (§51). `landscape_compare.py` alinea los
recortes con el mismo OFFSET del calco. La captura cenital en Azahar no está
probada; las vistas de suelo sí son capturas del emulador.

### Azahar ejecutado (solo laboratorio del carril, puerto 24691)

- `flags-ferry.out`: copia de `v03-back-calagua.sav` → ferry → llegada (34,73).
  `work/f11/proto/finish-flags/arrival.png` muestra el muelle.
- `flags-doors.out`, `work/f11/proto/finish-flags/doors.log`: siete entradas/salidas
  reales, terminado a las 14:33:21. Fábrica (26,45), Domo (34,24), Tubo (57,34),
  Torre (87,21), Pirámide (129,21), Arena (110,36), Palacio (116,63). Las rutas
  cruzan las ocho celdas. Capturas `*_in.png`/`*_out.png` en ese mismo directorio.
- La última corrección `flags` → `final` cambia **solo 752 bytes de UV de
  escaleras**. `LandscapeUvProof.java` comprueba los modelos reales: no cambia
  ningún vértice de posición, normal, color, comando ni otro subfichero GR.
  `final/uv-only-proof.log`; `final/archive-diff.json`: de los 39 ficheros del
  mod, solo difiere a/0/3/9, los otros 38 son idénticos. Por la política caso(c),
  no se repiten las siete puertas para ese cambio de UV; se comprueba su aspecto
  y el paso de Arena 110,39 →110,37 →110,39 (`final-walk.out`).
- Cuatro puntos a ras de suelo: muelle (`finish-flags/arrival.png`), plaza central
  (`finish-final/central-plaza.png`), Tubo (`finish-flags/pike_out.png`), Palacio
  (`finish-final/reloaded-palace.png`), todos bajo `work/f11/proto/`.
  El agua se ve en Tubo y Palacio; también `finish-final/at_97_47.png`, con valla
  y bandera retail. Árboles/arbustos del catálogo son una aproximación de forma
  ORAS al calco; no reproducen las copas de Esmeralda. Se conservan emblemas Aqua.
- Guardado mediante UI en Palacio, 58 bloques válidos, recargado en `final`:
  `final/palace-scene.json`, SHA256 f5455b207ffe1aeeff3322911f071bff85d686004e14cf3bd6e38f5c6cc6151a.
  Segundo guardado mediante UI en plaza (85,52), ya en `final`:
  `plaza-final.json`, SHA256 39b80c791a42052db23ed57867f751dd0ef5c84feb68e52152b5b4912bbcd443,
  58 bloques válidos. Resultado de recarga: `final-save-load.log` y
  `work/f11/proto/finish-final/reloaded-plaza.png`.

### Integración pendiente, responsabilidad del integrador

**Adaptación sin snapshots ya ejecutada:**
`python frontier/probes/island/landscape.py --name integration-fresh --fresh-movement`.
`integration-fresh/integration.diff` reemplaza al diff de `final` como propuesta
para producción. Mantiene `brush`, el donante y la construcción originales;
construye las brochas visuales por separado y asigna únicamente `bc.model` antes
de compactar y estampar los edificios. El runner generado no llama a `remember`
y el constructor no llama a `preserve`. No reutiliza tilemaps ni colisiones de
regiones de un build anterior. La matriz anterior solo se lee para verificar
el resultado del ensayo, no para construir el movimiento.

`work/f11/finish/integration-fresh/equivalence.json` verifica igualdad byte a
byte con `final` de los seis GARCs completos de `island_build.ZONE_ARCHIVES`,
incluidos los modelos, mundo, zonas y colisiones. Presupuesto y placements
idénticos (`build.log`, `movement-proof.json`): 4.151.040 bytes, WorldTextures
vacía, ZO209 de 11.288 y 361 piezas. No se repite Azahar para archivos idénticos,
conforme a la política de regresión. Esta equivalencia valida la adaptación
aislada, no la construcción común que aún debe integrar su dueño.

Trasladar `IslandLandscape` al paquete Java común **sin** `remember`, `preserve`
ni el mapa estático `movement`; cargar los placements desde Python o el plan y
aplicar `integration-fresh/integration.diff`. El antiguo ensayo `LandscapeTrial` toma los datos de movimiento
de la isla anterior antes de repintar. **No copiar esa dependencia a producción**:
conservar tilemap/colisión de las brochas originales, pintar las nuevas brochas
visuales por separado y sustituir solo `bc.model`; mantener el tratamiento de
escaleras y el estampado de edificios existente. No depender de IDs 872–879 ni
de un build previo. Pasar la lista determinista de placements desde Python o
el plan. Mantener el guard de presupuesto, WorldTextures vacío y tests de puertas.
El test de cuatro hooks del ensayo deberá adaptarse al trasladar las funciones:
rechaza deliberadamente un constructor distinto del que se ensayó.

No reconstruir `--name final` sobre esta evidencia: el corredor sustituye su
subdirectorio, incluidos los checkpoints; usar otro nombre para la integración.
El manifiesto `final/sources.json` fija los hashes exactos de los helpers además
de la revisión base a9fa187; `final/installed-hashes.json` fija los 39 ficheros
instalados. Los recursos comerciales, capturas y partidas quedan en work, fuera
de Git. Código, pruebas y documentación sí quedan en Git.

Pendiente: integración común, aceptación del resultado integrado y la captura
cenital del propio Azahar exigida por el brief; la comparación de modelos no
sustituye ese criterio.
No empaquetar. Consola y combates: no probados; no corresponden a esta regresión
de exterior (política del usuario, caso c). Laboratorio cerrado: `work/f11/finish/cleanup.log`, remaining=[], session_metadata=false.

### Cámara de evidencia, separada del candidato jugable

`frontier/probes/island/photo_camera.py` y `PhotoCamera.java` generan una copia
desechable con cámara cenital. No forman parte de la integración del paisaje.
El ensayo inicial pitch=-89,9°, distancia=3000, FOV=45° dio pantalla negra;
distancia=1000 y FOV=110° sí muestran el mapa. No se ha determinado la causa
exacta del primer resultado. Los campos proceden del lector/editor de cámaras
de CTRMap-F5 (`CameraDataFile`, `CameraData`, `CameraCoordinates`).

La cámara se aplica solo al AD229[3], con límites (0,0)–(159,79). La herramienta
comprueba que el área sea privada y rechaza reemplazar un directorio existente.
Su prueba por bytes exige que ese sea el único subfichero cambiado del único
área cambiada del único archivo cambiado entre los 39 del mod. Modelos,
texturas, colisiones, puertas, scripts, motor y cámara del candidato `final`
se conservan. **El a/0/1/4 fotográfico nunca debe ir a producción.**

La toma desde arriba revela una limitación de cobertura: se ven las columnas
de celdas próximas al jugador; las demás quedan negras. Las capturas regionales
no sustituyen una toma única de las ocho celdas a la vez. `photo_compare.py`
compara los fotogramas completos, sin reconstruir las zonas negras ni coser
las perspectivas, junto a la referencia y el F11 anterior (este último sigue
siendo la vista de modelos con color medio, identificada expresamente).

Ejecución del 2026-11-14, 14:56–14:59, puerto del carril 24691:

- `photo-reproduce/camera-only-proof.json`: solo AD229[3] distinto de `final`.
  `photo-guarded` reproduce los 39 archivos de ese mod con el guard de área.
- `work/f11/proto/finish-photo/at_34_24.png` y `at_129_21.png`: capturas cenitales
  reales oeste/este, llegando por movimiento normal desde el guardado de plaza.
  Recorrido: `work/f11/finish/photo-reproduce/route.out`.
- `work/f11/finish/photo-reference-before-after.png`: comparación con fotogramas
  completos; `photo-reference-before-after-crops.png`: recortes ampliados con
  sus cajas y hashes de originales en el JSON homónimo. Sin recursos generados.
  Se conserva la relación de aspecto y no se reconstruye ningún píxel faltante.
- `photo-evidence.json`: manifiesto de capturas, comparación, suite y cierre;
  comprueba que los 39 archivos de `final/mod` siguen iguales a su manifiesto.
- `tests-photo-final.log`: **2931 passed, 4 skipped**, 67,11 s. Compilación Java
  y ejecución completa de `photo_camera.py photo-guarded` correctas; comparación
  con y sin recortes ejecutada con Pillow. `git diff --check` limpio.
- `photo-reproduce/cleanup.json`: laboratorio cerrado en la misma shell que
  lo arrancó, `remaining=[]`, `session_metadata=false`.

La integración común sigue pendiente de su dueño. La evidencia cenital pasa de
no probada a **regional en Azahar**; no se declara lograda una captura única de
las ocho celdas. No se repiten puertas ni ferry por una cámara de fotografía
que no se entrega: los archivos jugables siguen idénticos a los ya validados.

### Entrega reproducible al integrador, sin APIs de snapshots

```sh
source scripts/env.sh
python frontier/probes/island/integration_bundle.py work/f11/finish/kit-nuevo
git apply --check work/f11/finish/kit-nuevo/FrontierIsland.diff
```

El exportador versionado no necesita una construcción anterior ni datos del juego.
Rechaza un destino existente y un constructor cuyos puntos de integración cambien.
Entrega `IslandLandscape.java` sin `remember`, `preserve` ni el mapa de snapshots,
`FrontierIsland.diff`, `landscape-plan.properties` (361 claves consecutivas
`island.landscape.N`) y `manifest.json` con hashes. No aplica cambios comunes.

El integrador debe copiar el helper a `faraway/java/ctrmap/tests/`, aplicar el diff,
añadir las claves del plan a `frontier/island_build.py:plan` y cargar su lista en
`faraway/java/faraway/Island.java`, antes de llamar a `FrontierIsland.build`:

```java
IslandLandscape.placements = new ArrayList<>();
for (int i = 0; plan.getProperty("island.landscape." + i) != null; i++) {
    IslandLandscape.placements.add(plan.getProperty("island.landscape." + i));
}
```

Añadir el import `ctrmap.tests.IslandLandscape`. Reinicializar la lista en cada
ejecución evita conservar placements de otra construcción en la misma JVM.
Las claves contienen texto UTF-8; conservar la lectura de Properties mediante
Reader existente. No añadir `LandscapeTrial` ni las herramientas fotográficas a producción.

Verificación ejecutada: `landscape.py --name integration-stripped --fresh-movement`
compila exactamente el helper exportado y genera los seis GARCs idénticos byte a
byte a `final` (`integration-stripped/equivalence.json`). El plan exportado coincide
con los 361 placements probados; `git apply --check` acepta el diff. Presupuesto
4.151.040, WorldTextures vacía, ZO209 11.288. Esta prueba no valida aún la lectura
del plan en el runner común: ese cambio sigue reservado al integrador.
