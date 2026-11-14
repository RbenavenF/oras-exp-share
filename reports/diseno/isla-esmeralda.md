# Isla del Frente con la distribución de Esmeralda (F11)

Petición del usuario (2026-11-13), tras validar la alfa v0.2 en su 3DS: la próxima alfa debe tener la amplitud, la
disposición y el paisaje del Frente Batalla de Esmeralda, construidos con recursos de ORAS. Solo los edificios
siguen siendo provisionales. La cueva (Cueva Artesano) y la cascada se omiten.

Referencia visual: [`referencias/frente-esmeralda.webp`](referencias/frente-esmeralda.webp) (2048×1152, la que
adjuntó el usuario). Solo es referencia: no se copia ningún recurso de ella ni de emerald-3ds (CC BY-NC-SA).
Todo el material visual sale de ORAS.

## 1. Medidas de la referencia (fuente: pret/pokeemerald 731ad5bf)

- La imagen es el mapa entero a **16 px por casilla**: 2048/16 = 128, 1152/16 = 72.
- En Esmeralda son dos mapas unidos sin corte, con conexión `right`/`left` y desplazamiento 0:
  - `BattleFrontier_OutsideWest`: 56×72;
  - `BattleFrontier_OutsideEast`: 72×72.
  - Fuente: `data/layouts/layouts.json` y `data/maps/BattleFrontier_Outside{West,East}/map.json`.
- Se conserva la **escala 1:1 en casillas**: una casilla de Esmeralda es un paso, igual que una casilla de ORAS.
  Así se mantienen las distancias andando.

Puertas en coordenadas unidas (x de Este + 56), de los `warp_events`:

| Edificio | Mapa de Esmeralda | Casilla unida | Uso en la isla |
| --- | --- | --- | --- |
| Domo | Oeste (19,17) | (19,17) | puerta del Domo (noroeste) |
| Fábrica | Oeste (11,38) | (11,38) | puerta de la Fábrica (oeste) |
| Tubo | Oeste (42,27) | (42,27) | puerta del Tubo (centro-oeste) |
| Torre | Este (16,14) | (72,14) | puerta de la Torre (norte) |
| Arena | Este (39,29) | (95,29) | puerta de la Arena (este) |
| Palacio | Este (45,56) | (101,56) | puerta del Palacio (sureste) |
| Pirámide | Este (58,14) | (114,14) | puerta de la Pirámide (noreste) |
| Recepción (hall de entrada) | Oeste (26,61) y (26,65) | (26,61)/(26,65) | entrada desde el muelle; hueco reservado |
| Centro Pokémon | Este (3,51) | (59,51) | hueco reservado, sin puerta |
| Tienda | Oeste (51,51) | (51,51) | hueco reservado, sin puerta |
| Sala de clasificación | Este (35,12) | (91,12) | hueco reservado, sin puerta |
| Casa de Scott | Oeste (44,5) | (44,5) | hueco reservado, sin puerta |
| Intercambio de PB | Este (10,28) | (66,28) | hueco reservado, sin puerta |
| Salones 1–9 (casas pequeñas) | varias | ver map.json | huecos reservados, sin puerta |
| Cueva Artesano | Oeste (39,55), Este (28,7) | — | **se omite**, igual que la cascada |

El muelle del ferry está al suroeste (abajo a la izquierda en la imagen). Su casilla exacta de llegada se mide en
F11-ISLA-TRAZADO sobre la imagen y el map.json; hoy el ferry llega a (53,34) de la zona 209 (`frontier/island.py`
ARRIVAL).

## 2. Encaje en ORAS

Hoy la isla es la zona 209, clon del puerto del Resort (212). La plaza está pintada en una sola celda, la (0,1),
con el pintor de CTRMap-F5 (`frontier/island_build.py`, `faraway/java/ctrmap/tests/FrontierPlaza.java`).

- Las celdas de mapa de ORAS miden 40×40 casillas. Para 128×72 hacen falta **4×2 celdas** (160×80). Se centra la
  referencia y el sobrante es mar: 16 casillas a cada lado y 4 arriba y abajo.
- Opción A, la pedida: **un exterior continuo en una zona** con 8 celdas.
  Es la preferida por el usuario (2026-11-13): una sola área, sin cortes. Antes de descartarla hay que probar a
  compartir texturas, quitar del área lo que no se usa y elegir piezas más ligeras.
- Opción B, solo si A no carga y está documentada la causa: **dos sectores**, como en la propia Esmeralda.
  - Oeste y Este en dos zonas, la segunda en una zona libre que encuentre `ZoneRepurposeScanner`.
  - El paso entre las dos zonas es continuo si comparten área. Si cada una necesita su propia área para caber,
    el paso lleva un **fundido o warp**, como las rutas que ORAS parte respecto a Esmeralda: hay que cargar la
    otra área. El usuario acepta el fundido.
  - Reducir la escala va **después** de B, y con el porqué escrito.

### 2.1 Presupuesto de carga

`LOAD_BUDGET` = 2.724.608 es lo mayor que se ha visto cargar con la plaza actual. No es el límite del motor
(`reports/frontier.md` §23; `personalidad.md` §3.3). Lo mide `Plaza` («load budget»): paquete del mapa, paquete
de props y modelos de todas las regiones del área.

Antes de pintar, F11-ISLA-TRAZADO mide con esa misma métrica exteriores **retail** grandes. Lo que el juego carga
de fábrica también carga en consola, y eso da un techo seguro:
- el Resort, zonas 210, 211 y 212;
- una ciudad grande, por ejemplo Calagua o Portual.

Si el exterior continuo cabe por debajo de ese techo retail, `LOAD_BUDGET` puede subir a él con esa justificación.
Hay que anotar la fuente y la zona. Si no cabe, se documenta qué pesa: celdas, texturas o modelos de región.

**Medición F11-ISLA-TRAZADO (2026-11-14):** Resort 211 suma **4192384 bytes** con esta métrica
(9 regiones); Resort 210/212: 3507584/1849472; Calagua: 3329536; Portual: 3265152; matriz de Férrica:
8356096 (incluye rutas, no demuestra carga simultánea). Fuentes, comandos y desglose en
[`reports/frontier.md`, apartado F11](../frontier.md#f11--trazado-materiales-y-cota-retail-2026-11-14-codex-hito-2),
`frontier/probes/island/survey.sh` y `work/f11/retail/zone*.txt`. Se usa Resort 211 como referencia comparable;
no se cambia aquí LOAD_BUDGET de producción ni se considera la suma una garantía de RAM residente.

### 2.2 Materiales (solo ORAS)

Hay que elegir del catálogo de CTRMap-F5 y de las áreas retail el equivalente más próximo de cada elemento:

- suelo de baldosa clara y caminos;
- hierba y jardines;
- acantilados marrones en terrazas;
- agua y estanques;
- escaleras;
- muelle;
- vallas y banderines;
- parterres, árboles y arbustos;
- la arena del recinto de la Pirámide.

Los árboles del área 8 cuestan ~146 KB (`personalidad.md` §3.1). Hay que preferir los del área que ya carga la isla, o
medir antes una alternativa. Ningún espacio importante del paisaje se elimina por falta de pieza exacta: se usa la
más próxima y se anota.

La tabla medida por cada clase del calco está en **reports/frontier.md, apartado F11 → Materiales ORAS por clase**,
con región/mesh/área, texels y aumento del world pack. `frontier/probes/island/Materials.java` reproduce los costes.
La palmera sin passengers comparte `yashi` ya cargada; el árbol redondo exige un atlas mayor. La palmera completa
introduce un conflicto de imagen con `chip_kusa` y no se propone importarla así.

### 2.3 Decisión A/B de F11-ISLA-TRAZADO (2026-11-14)

**A provisional: una zona (209), una sola área privada y 4×2 celdas, a escala 1:1, sin cortes.** El prototipo de terreno
comparte texturas en AD[11], no tiene referencias fuera del world pack y mide **4028928 bytes**, 163456 menos
que Resort 211. Ha cargado por ferry en Azahar y se han cruzado fronteras horizontales y verticales leyendo la
posición, sin modificarla. Fuentes: `work/f11/prototype/{build.log,ferry5.log,route-walk.log}` y generador aislado
`frontier/probes/island/`. B no se justifica por el terreno medido; no se reduce la escala.
Se han recorrido las ocho celdas, guardado mediante UI en (119,45), celda (2,1), y recargado allí con movimiento
posterior: `terrain-saved.json` y `reload.log`. Zona/área/matriz final: **209/229/431** (`zones-final.txt`).

El GR debe conservar el contenedor ORAS retail completo (7 subficheros), sustituyendo 0–3. El contenedor nuevo
de 6 subficheros dio pantalla blanca con el mismo presupuesto: no era prueba de falta de memoria. La pendiente
de recepción funciona con andar normal; el comportamiento de escalera `0x6c` del catálogo la bloqueaba en
este ensayo. Solo el exportador del prototipo abre el pasillo temporal por recepción (26,61–65); el calco no cambia.

La aceptación queda pendiente del regreso al muelle tras recargar: hay un bloqueo reproducible cerca de x=99,
también sin GDB. Limpiar texturas/props y compactar suelo no lo resuelve; diagnóstico y presupuestos de
variantes en reports/frontier.md (F11). No se declara A cerrada ni se justifica B todavía.

Se ha validado el recorrido inicial del **terreno**. La carga con los siete edificios recolocados y su decoración definitiva,
los retornos de interiores y la consola siguen **no probados**: F11-ISLA-CONSTRUCCION medirá su composición,
compartirá texturas, retirará lo que no use y elegirá piezas ligeras antes de plantear B. Los builders comunes,
el motor y la reserva Luma 0x579604–0x579804 no se modifican en este hito.

## 3. Lo que se conserva y lo que cambia

- **Se conservan**:
  - interiores, scripts, mecánicas y textos de las siete instalaciones;
  - Cerebros, modos y la reserva de Luma 0x579604–0x579804.
- **Cambian**:
  - el mapa exterior;
  - la casilla de cada puerta de la plaza (tabla de §1) y los retornos de cada interior, es decir, los warps de
    salida que llevan a su puerta;
  - colisiones, cámaras y la llegada y salida del ferry;
  - las coordenadas de `frontier/probes/package/circuit.py`.
- **Edificios**: siguen siendo los provisionales de hoy (`island_build.FACILITIES`), recolocados en su sitio nuevo.
  Se reserva el hueco del edificio definitivo de cada instalación, con su silueta aproximada de la referencia, para
  sustituirlo después sin mover caminos.
- **Partidas antiguas**: una partida guardada en la isla vieja reaparece en la casilla vieja del mapa nuevo, que
  puede ser mar o muro. El LEEME de la alfa debe decir que **hay que guardar fuera de la isla antes de actualizar**.

## 4. Tareas (frontier/orch/tasks.json)

1. **F11-ISLA-TRAZADO**: va justo detrás de F9-MODOS-BASE en la cola. No espera a que termine, porque no toca lo
   mismo. Hace tres cosas:
   - la cuadrícula calcada;
   - los techos retail;
   - un prototipo de terreno de 8 celdas en Azahar, sin edificios nuevos.

   Y deja la decisión A/B escrita.
2. **F11-ISLA-CONSTRUCCION**: el exterior entero con los siete edificios recolocados, las puertas, los retornos, el
   ferry y las pruebas.
3. **F7-PAQUETE-V03**: la alfa siguiente, detrás de F11-ISLA-CONSTRUCCION y F9-MODOS-BASE, y antes de seguir con
   las modalidades (F9-LIBRE-PROPIOS pasa a depender de ella).

Revisión de F10 por este cambio:
- Las coordenadas de la plaza antigua dejan de valer en F10-LETREROS (casillas de `personalidad.md` §2) y en
  F10-EXTERIOR-FASE1 (vallas de la Arena en x15/x25). Las dos tareas se reescriben sobre el trazado nuevo.
- F10-COTA-CARGA queda anulada: las variantes de `plaza_variants.sh` son de la plaza antigua, y la cota la mide
  F11-ISLA-TRAZADO.
- F10-EXTERIOR-FASE2 pasa a ser «edificio definitivo en su hueco reservado». Ya no usa las casas de pueblo
  ancladas en la plaza antigua.
- Las salas propias (F10-SALA-*) no dependen de la plaza y no cambian.
