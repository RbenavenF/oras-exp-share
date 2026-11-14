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
python frontier/probes/island/landscape.py --name flags
python frontier/probes/island/lab_mod.py work/f11/finish/flags
env -u ORCH_LANE python -m pytest -q tests
```

El primer comando genera la isla vigente; el segundo copia su game/workspace,
compila una copia de `FrontierIsland.java` con las funciones de `IslandLandscape`,
y reconstruye solo su exterior. Los originales se leen. Las cuatro sustituciones
exigen coincidencia única para detenerse si cambia el constructor.
`work/f11/finish/flags/integration.diff` es el diff revisable. `sources.json`
registra revisión, hashes de constructor, plan y archivos de entrada.
El corredor reemplaza únicamente su subdirectorio de ensayo; `base` está reservado.

## Cambios y medidas

- La escalera blanca **sí tenía** `chip_steps01` en AD229[11]. El material
  `chip_steps01a` (mesh 9 del primer GR) usa la proyección de mundo 1/72,
  que recorre la zona blanca del atlas. `IslandLandscape.stairs` limita las UV
  a la banda de piedra x65–126/y98–125 del atlas retail 128×128. El sampler
  runtime invierte V respecto al exportado: la variante `dense` con V sin invertir
  todavía muestra franjas blancas (`factory_out.png`). `flags` prueba V=1-y/128.
  No crea textura; la corrección queda pendiente de inspección en Azahar.
  Fuentes: `work/f11/finish/material-audit.txt`, `stair-retail-uv.txt`,
  `tex-229-chip_steps01.png`. Pendiente aceptación visual en Azahar.
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
  `flags/placements.txt`. No se intenta llenar todos los bloques del calco:
  los límites explícitos mantienen el presupuesto de carga.

Presupuesto medido por `FrontierPlaza.loadBudget` sobre el archivo construido:

| Ensayo | Total | Mundo | Props | Modelos |
| --- | ---: | ---: | ---: | ---: |
| F11 vigente | 3.534.592 | 654.336 | 209.152 | 2.671.104 |
| Acabado dense (sin banderas, V inicial) | 4.101.760 | 818.560 | 209.152 | 3.074.048 |
| Acabado flags | 4.151.040 | 835.328 | 209.152 | 3.106.560 |

Quedan **41.344 bytes** respecto a ISLAND_BUDGET 4.192.384. WorldTextures: `{}`.
Fuentes: `base-build.log`, `before-world.txt`, `dense/build.log`, `flags/build.log`. Los incrementos
por colocación se imprimen en el último log; no equivalen al coste de textura,
que se comparte una sola vez en el world pack. La variante `flags` añade 49.280
bytes sobre `dense`: +16.768 de world pack y +32.512 de modelos, descontando dos
tramos de valla que ya no caben sobre las casillas ocupadas por las banderas.
Las banderas conservan el emblema Aqua: es la pieza disponible más próxima,
no un recurso propio ni una reproducción de los banderines amarillos. Fuente
del descarte Magma y del coste de texels (16.384): `LandscapeAudit.java`,
`work/f11/finish/audit.log`, `audit/tex-{207,80,210}-flag.png`.
ZO209: 11.288 bytes (límite 17.248).

`flags/movement-proof.json` verifica los GARCs resultantes: archivo completo de
zonas a/0/1/3 idéntico (SHA256
`10a6c1c753533b151f8403711b405e87abbfb096b8fe723b17af598027b8d183`);
GR[0,2,3,4,5,6] idénticos para las ocho celdas originales 872–879 y nuevas
880–887. Solo cambia GR[1], geometría visual. Incluye hashes por celda.
No se modifica code.bin, CRO, asm ni la reserva Luma 0x579604–0x579804.

## Pruebas e integración pendiente

Suite del candidato final: **2931 passed, 4 skipped**, 61,52 s,
`work/f11/finish/tests-final.log`.
El entorno ORCH_LANE se retira para las pruebas del propio orquestador, que
necesitan arrancar sin pertenecer a un carril. No se omiten tests de juego.
Los tres nuevos tests validan ubicación/ausencia de solapes y reserva intacta,
rechazo de un constructor cambiado y rechazo de contenedores ajenos.

Comparación cenital: `work/f11/finish/before.png` (F11 anterior),
`dense-topview.png` y `dense-reference.png`. `TopView.java` representa los
triángulos con el color medio de su textura; **no es captura de Azahar ni permite
juzgar el muestreo UV**. La comparación a ras de suelo se registra aparte.

Para integrar, trasladar `IslandLandscape` al paquete Java común y aplicar los
cuatro hooks de `integration.diff`. El ensayo `LandscapeTrial` toma los datos de
movimiento de la isla anterior antes de repintar. En producción, conservar el
tilemap/colisión de las brochas originales y cambiar solo las brochas visuales;
no depender de IDs 872–879 ni de un build previo. Pasar la lista de placements
determinista desde Python o un fichero del plan. Mantener el guard de presupuesto,
WorldTextures vacío y las pruebas de puertas de F11.

Pendiente: inspección visual y recorrido de la variante final en Azahar;
integración común y aceptación del resultado integrado.
No empaquetar. Consola y combates: no probados, no corresponden a esta regresión
de exterior (política del usuario, caso c).
