# Personalidad de cada edificio del Frente: interior, letrero y exterior

Diseño F10-PERSONALIDAD-DISENO (2026-11-12, Claude Code, Opus 5.5). Prioridad del usuario: **la última**. Solo
lectura y diseño, sin laboratorio de Azahar ni código del juego. Todo lo que se propone son recursos de ORAS (mapas,
edificios y modelos retail del volcado). Emerald 3DS de ZallaxDev no se ha consultado ni copiado (CC BY-NC-SA). La
idea de cada instalación sale del Esmeralda original y se traduce a piezas de ORAS.

Las medidas son estáticas, con CTRMap-F5 sobre la build de la isla del paquete
(`work/frontier/package/build-island/game`) y la base de la plaza (`frontier/lab_plaza_base.py`). Se reproducen
con `frontier/probes/personalidad/` (README allí). Las salidas están en `work/frontier/personalidad/`, que no está en
git. **Nada de este documento está probado en Azahar ni en consola.**

## 0. Resumen

| Instalación | Interior hoy | Interior propuesto (donante retail) | Letrero | Exterior: fase 1 (cabe hoy) | Exterior: fase 2 (si sube la cota, §3.3) |
| --- | --- | --- | --- | --- | --- |
| Torre | 329 ← 517 | **517**, la Mansión, sin cambios: desde ahora es la única que la usa | poste | dos vallas y un anfitrión | casa-bloque de Férrica (más alta) |
| Domo | 456 ← 365 | **365**, Sala de la Fama (hecho, §37) | poste | anfitrión | — (la casa cúpula de Arrecípolis no cabe) |
| Fábrica | 213 ← 517 | **139**, Nueva Malvalona (generador) | poste | anfitrión | — |
| Pirámide | 140 ← 517 (pisos 141–142 ← 77) | **165**, cueva de Scorched Slab (vestíbulo); pisos sin cambios | poste | anfitrión | casa de Lavacalda (arregla el tejado azul) |
| Tubo | 458 ← 517 | **88**, interior del Monte Pírico | poste | anfitrión | — |
| Arena | 457 ← 517 | **289**, Escuela de Entrenadores de Férrica | poste | dos vallas (cuadrilátero) y un anfitrión | — |
| Palacio | 340 ← 517 | **358**, sala del Campeón | poste | anfitrión | casa de tejas doradas de Algaria |

- **Interiores**: cinco donantes nuevos.
  - Todos cubren las casillas que usa el script de la Mansión, así que **no hay que reescribir coreografías**. El
    Domo sigue la misma vía (§37).
  - Su carga va de 333.184 a 1.160.192 bytes. La Mansión, que ya carga, pesa 2.320.512.
- **Letreros**: un poste de letrero del catálogo delante de cada puerta.
  - Con los siete, la plaza pasa de 2.665.344 a **2.708.224 bytes**, por debajo de `LOAD_BUDGET` = 2.724.608.
  - Se leen con un registro interactivo y una rutina de letrero trasplantada al script de la isla (§2). Hoy la isla
    no tiene esa rutina (medido).
- **Exteriores**: el margen que queda tras los letreros es de 16.384 bytes.
  - Solo caben **cuatro vallas**: dos en la Arena y dos en la Torre, 2.724.480 bytes, a 128 bytes del límite.
  - Las sustituciones de edificio miden entre 2.728.704 y 2.795.776 bytes: necesitan antes una cota medida mayor
    (§3.3).
  - El cambio que hoy cabe en todas las instalaciones es un NPC «anfitrión» junto a cada puerta. No entra en el
    presupuesto de la plaza (§3.2).

## 1. Interiores

### 1.1 Requisito común (medido)

Las siete instalaciones ejecutan scripts derivados de la zona 517. Sus coreografías y cámaras usan casillas absolutas
de la Mansión:
- la coreografía Individual, x=19–23, y=12–25 (reports/frontier.md §37);
- las recepcionistas uid 1 y uid 2 en (23,24) y (17,24) (NPC 1 y 2 de 517, `entities.txt`);
- el regreso de la Pirámide frente a la recepcionista (`pyramid.LOBBY_RETURN`, (23,25)).

Un donante sirve sin tocar el script si su suelo cubre esas 73 casillas. El Domo lo demostró con 365 (§37–§37.1):
el clon conserva el script y las nativas de 517 y recoloca sus NPC en las casillas de 517 (`dome_room.NPCS`).

`floor_fit.py` cruza el mapa de suelo de **las 536 zonas** (`Probe floor`) con `work/frontier/island/zones.tsv`.
Resultado: 175 zonas cubren el núcleo con 2 casillas o menos sin suelo (`work/frontier/personalidad/floor_fit.txt`).
Muchas son exteriores o bases secretas. De ellas se eligieron interiores con salida andando (warp de transición 2,
como el de 517) o con una salida adaptable como la de 365.

Límites de la medida:
- El muestreo de alturas no ve barreras ni muebles (§37.1).
- Algunos interiores salen como un plano lleno de 40×40 (286 y 289, por ejemplo).
- Cubrir el núcleo es **necesario pero no suficiente**. Cada sala necesita `Probe tuples` en el núcleo y un paseo
  en Azahar, como el Domo.

### 1.2 Medidas de los elegidos y alternativas

Fuentes: `floor_fit_chosen.txt` (`floor_fit.py`), `budgets.txt` (`WorldTextures`: paquete del mapa + props +
modelos) y `entities.txt` (`Probe entities`), en `work/frontier/personalidad/`.

| Zona | Lugar (texto de zona) | Núcleo sin suelo / plano | Suelo | Carga (bytes) | NPC / warps / disparadores / props | Salida a usar |
| --- | --- | --- | --- | ---: | --- | --- |
| 517 | Mansión Batalla (referencia) | 2/73, 35/73 (estrado) | x4–36 y2–34 | 2.320.512 | 10 / 1 / 0 / 0 | (19–21,31), trans 2 |
| 365 | Sala de la Fama (Domo, hecho) | 0, 73/73 | x6–27 y4–33 | 305.024 | 1 / 1 / 0 / 0 | (15–17,31), adaptada §37.1 |
| **139** | Nueva Malvalona | 0, 73/73 | x3–37 y5–39 | 1.160.192 | 11 / 1 / 1 / 3 | (19–21,38), trans 2 |
| **88** | Monte Pírico, interior | 0, 73/73 | x12–30 y4–33 | 438.528 | 9 / 3 / 0 / 0 | (19–21,32), trans 2 |
| **289** | Escuela de Entrenadores (Férrica) | 0, 69/73 | plano 40×40 (sin muros) | 919.168 | 7 / 1 / 0 / 2 | (18–20,32), trans 2 |
| **358** | Sala del Campeón (Liga) | 0, 69/73 (estrado a ~90) | x11–29 y4–39 | 333.184 | 4 / 2 / 0 / 0 | (20,34), 1×1, trans 0: adaptar |
| **165** | Scorched Slab (cueva) | 0, 73/73 | x5–32 y6–32 | 518.912 | 2 / 2 / 3 / 0 | (29,31), 1×1, trans 5: adaptar |
| 286 | Devon S. A., planta baja | 0, 72/73 | plano 40×40 | 876.032 | 3 / 2 / 1 / 0 | (21–23,29), trans 2 |
| 337 | Centro Espacial (Algaria) | 0, 70/73 | x6–36 y7–28 | 1.158.784 | 17 / 2 / 2 / 4 | (20–22,28), trans 2 |
| 273 | Museo Oceánico (Portual) | 0, 69/73 | x3–25 y5–25 | 824.064 | 14 / 3 / 1 / 10 | (13–15,25), trans 2 |
| 132 | Cueva Cardumen | 0, 72/73 | — | 706.048 | 2 / 2 / 1 / 0 | 1×1, trans 5 |

Notas:
- La identidad de cada zona sale de su primera línea de texto. Por ejemplo, 139 está junto a «Nueva Malvalona»
  en zones.tsv; 289 dice «En la pizarra hay notas sobre los cambios de estado…»; 358 es «Hola, [jugador]… Estaba
  deseando que nos enfrentáramos aquí» (Máximo).
- Los nombres en español de 165 y 132 no se han comprobado en el juego. Se usa el de zones.tsv.

### 1.3 Propuesta por instalación

- **Torre → 517 (sin cambios)**. La Mansión Batalla es la heredera de la Torre en ORAS y la sala más elegante del
  juego. Al mover las otras cinco a donantes propios, la Torre queda como única dueña de 517. Coste cero.
  - Alternativa medida: 337, Centro Espacial, de aspecto futurista. Cubre el núcleo, salida andando, 17 NPC y 4
    props que limpiar, carga 1.158.784.
- **Fábrica → 139, Nueva Malvalona**. La Fábrica de Esmeralda es una nave industrial; ORAS no tiene nada más
  maquinal que la central de Nueva Malvalona.
  - Suelo plano y amplio. La salida es un pasillo al sur, x17–23 y33–38, como el de 517 pero 7 casillas más abajo.
  - Limpiar sus 11 NPC (bolas de objeto y Voltorb), 1 disparador (19–21,33) y 3 props (casos 7, 7 y 1 del script
    retail: con el script de la Fábrica ejecutarían casos ajenos).
  - Alternativa: 286, Devon S. A. («los orgullosos fabricantes»), 876.032 bytes.
- **Palacio → 358, sala del Campeón**. El Palacio de Esmeralda es un salón noble con su señor en el trono. La sala
  del Campeón es el salón de honor de ORAS: estrado amplio x11–29 y10–27.
  - Riesgo: igual que en 365, la entrada sur (20,34) es de llegada (trans 0, z −45), al pie de una escalera. Hace
    falta la adaptación de §37.1 (tipo de warp y tuples de salida en el FIELD_DATA propio, con guardas).
  - El warp norte (19–21,6) lleva a la Sala de la Fama retail (365): se redirige a la puerta del Palacio o se anula.
  - NPC y recepcionistas a la altura del estrado (z ≈ 90, como los NPC de 358).
  - Alternativa sin escalera: 273, Museo Oceánico (salida andando, 10 props).
- **Arena → 289, Escuela de Entrenadores**. La Arena juzga Mente, Técnica y Cuerpo; la escuela es una sala de
  madera de juicio y lecciones. La salida (18–20,32) queda una casilla a la izquierda y otra abajo de la de 517.
  - Limpiar 7 NPC y 2 props.
  - El mapa de suelo no ve muros (plano 40×40): se necesitan tuples antes de aceptar.
- **Tubo → 88, interior del Monte Pírico**. El Tubo de Esmeralda (Lucía, salas al azar) es sombrío y misterioso.
  - La salida (19–21,32) es casi la de 517 (19–21,31). De los cinco, es el clon más barato.
  - Otros dos warps (al 87 y al 89): redirigir a la puerta del Tubo, como hicieron los pisos de la Pirámide (§34).
  - Limpiar 9 NPC.
- **Pirámide → vestíbulo 165** (cueva de Scorched Slab). Los pisos ya son cueva de las Ruinas Desierto (§34); el
  vestíbulo pasa de la Mansión a una cueva de roca caliente, a juego con ellos.
  - Salida: warp 1 (29,31), 1×1, trans 5 (escalón), a 6 casillas de la recepción. Necesita la adaptación de salida
    de §37.1.
  - El warp 0 (7,28) se redirige a la misma puerta.
  - Limpiar 2 NPC y 3 disparadores (const 16621).
  - `LOBBY_RETURN` (23,25) cae en suelo.
  - Alternativa: 132, Cueva Cardumen.
- **Domo → 365** (hecho, §37). Sin trabajo de interior.

Común a los cinco clones nuevos:
- conservar script, texto 619 y nativas de 517 (`KEEP_TEXT`, `NATIVE_DONORS`);
- colocar en las casillas de 517 **los NPC que direcciona el script de cada instalación**. El Domo conserva uid 0,
  1 y 2 (`dome_room.NPCS`); en las demás hay que listarlos sobre el desensamblado antes de construir.
- El encabezado de zona (música, cámara) viene del donante (`WorkspaceOps.cloneWithOwnMap`). Comprobar en Azahar si
  suena la música del donante (la de Nueva Malvalona, la del Monte Pírico…). Si no encaja, copiar los campos de 517.
  No medido.
- **ZO**: el script no cambia, solo crecen o menguan las entidades. Hoy los clones de 517 miden 15.808–16.156 bytes
  (213, 329, 340, 457, 458, 140, medido sobre la build del paquete); límite 17.248. Con NPC recolocados, cada
  `check_room` debe repetir la guarda de tamaño.

### 1.4 Lo que falta en la construcción común

Medido en `faraway/java/faraway/Build.java`:
- El plan solo admite `clearNpcs`, `clearTriggers`, `warp.i` (redirigir), `exitTiles`, `trigger.i`, `npc.i` y
  `loadBudget`. **No hay forma de borrar props** (139, 289, 337 y 273 los tienen).
- Los warps sobrantes solo se pueden redirigir.

Hace falta:
- `clearProps`;
- un módulo genérico de salas (`frontier/rooms.py`): tabla zona → donante, NPC, salida, ajustes de warp y tuples, y
  `check_room` como `dome_room`;
- pasar el Domo a ese módulo **sin cambiar ni un byte** de su ZO.

Son ficheros comunes (isla y construcción): los hace el integrador.

## 2. Letreros

**Modelo**:
- Catálogo de CTRMap-F5 (`oras_buildings.tsv`): `Sign post` (1×1, región 153), `Route sign` (1×1) y `Billboard`
  (2×1).
- Medidos, uno a la derecha y dos casillas al sur de cada puerta (casillas locales de la celda: Torre (21,8),
  Domo (8,18), Fábrica (22,19), Pirámide (34,19), Tubo (7,31), Arena (22,31), Palacio (33,31)):

| Variante | Presupuesto de la plaza | Margen hasta 2.724.608 |
| --- | ---: | ---: |
| control (build actual) | 2.665.344 | 59.264 |
| siete `Sign post` | **2.708.224** | 16.384 |
| siete `Billboard` | 2.716.032 | 8.576 |
| siete `Route sign` | 2.717.568 | 7.040 |

El control reproduce exactamente el presupuesto de la build del paquete (`java.log`: 2.665.344). Se elige
`Sign post`, el más barato.

**Lectura**:
- CTRMap-F5 sabe cablear letreros (`MapPainter.wireSigns`): una línea de texto, un caso de script con la forma de
  los 169 letreros retail y un registro interactivo (`NpcTemplates.makeSignFurniture`) en la casilla. Todo ello
  necesita una rutina de letrero en el script de la zona.
- `SignCheck` (`frontier/probes/personalidad/SignCheck.java`): **ninguna** de las zonas 209, 212, 213, 329, 340,
  456, 457, 458, 140 y 517 la tiene. Las zonas 16 y 14 sí (control).
- Vía propuesta:
  - el host de `FrontierPlaza` acepta el trasplante (`SignWrapperInjector`, el mismo mecanismo que la rutina de NPC
    parlante) y da el texto de cada letrero;
  - `island_build` verifica la rutina (`ZoneScriptAnalyzer.findSignWrapper`) y los siete registros.
- **Tamaño**: el ZO de la isla mide 11.288 bytes (script 10.784, entidades 408). Quedan 5.960 bytes hasta 17.248
  para la rutina, siete casos y siete registros de 0x14 bytes.
- **Textos**: CTRMap escribe una sola lengua. Las líneas se ponen en ES y EN con las herramientas de texto del
  overlay, como los demás textos del Frente. Las otras seis lenguas reciben el texto EN, como los nombres de
  Cerebros, o se declaran pendientes. Propuesta, texto propio y no copiado:
  - «TORRE BATALLA / Combate tras combate hasta la cima.»
  - «DOMO BATALLA / Torneos de cuatro rondas.»
  - «FÁBRICA BATALLA / Combate con Pokémon de alquiler.»
  - «PIRÁMIDE BATALLA / Siete pisos en la penumbra.»
  - «TUBO BATALLA / Tres puertas, un camino.»
  - «ARENA BATALLA / Mente, Técnica y Cuerpo, en tres turnos.»
  - «PALACIO BATALLA / Tus Pokémon deciden.»
  - EN: «BATTLE TOWER / Battle after battle, to the top.», y así las demás.
- Las líneas del texto de la isla se reservan en REPARTO antes de usarlas.

## 3. Exteriores

### 3.1 Presupuesto medido

`plaza_variants.sh` pinta la base de la plaza con cada variante y guarda la línea «load budget» de `Plaza`
(`work/frontier/personalidad/plaza_variants.txt`). Los costes no se suman: los edificios del mismo área de origen
comparten texturas (§24).

| Variante (con los siete postes salvo «sin letreros») | Bytes | ¿Cabe en 2.724.608? |
| --- | ---: | --- |
| + 2 vallas de hierro a los lados de la Arena (x15 y x25, y25–28) | 2.716.288 | sí (8.320) |
| + 2 vallas en la Arena y 2 en la Torre (x14 y x24, y2–5) | 2.724.480 | sí (**128**) |
| Pirámide → casa ancha de Azuliza (29,13) | 2.721.280 | sí (3.328) |
| Pirámide → casa ancha + vallas de la Arena | 2.729.472 | no |
| Pirámide → casa de Lavacalda (31,13) | 2.728.704 | no (+4.096) |
| Torre → casa-bloque de Férrica (17,1) | 2.732.160 | no (+7.552) |
| Palacio → casa de tejas doradas de Algaria (28,25) | 2.795.776 | no |
| + árbol junto al Tubo (11,26) | 2.854.400 | no: el área 8 es nueva y cuesta ~146 KB |
| + dos arbustos junto al Domo | 2.850.560 | no |
| todos los cambios de edificio + vallas | 2.872.064 | no |
| sin letreros: Torre → casa-bloque | 2.689.280 | sí |
| sin letreros: Palacio → tejas doradas | 2.752.896 | no |
| sin letreros: Fábrica → taller de vidrio (Ruta 113) | 2.795.392 | no |

Las sustituciones conservan la casilla de la puerta: ancla = puerta − `doorDX/doorDY` del catálogo. Por ejemplo,
la casa de Lavacalda (puerta 1,4) en (31,13) deja la puerta de la Pirámide en (32,17).

### 3.2 Fase 1 (cabe hoy)

- **Siete postes** (§2).
- **Arena**: dos vallas de hierro a los lados del cuadrilátero, en el área 11, que la isla ya carga. Es el retoque
  geométrico con más margen.
- **Torre**: dos vallas más, solo si se acepta un margen de 128 bytes. Cualquier pieza que se añada después a la
  isla obligaría a quitarlas. Recomendación: dejarlo para la fase 2 salvo que el usuario lo quiera ya.
- **Un anfitrión por puerta**: un NPC con frase propia de la instalación, junto a la puerta y sin bloquearla. Hoy es
  el único retoque que cabe en todas.
  - Los modelos de NPC no están en el presupuesto de la plaza (paquete del mapa + props + modelos de región) y su
    coste de memoria **no se ha medido**.
  - Referencia retail: las zonas exteriores del Resort tienen 24 y 26 NPC (211 y 210, zones.tsv); la isla tendría 8.
  - Modelos: los registrados en el área 214 (regdonor que ya usa el Domo) u otros con `regdonor`, elegidos viéndolos.
  - Entidades: 7 × 0x30 = 336 bytes más en el ZO de la isla, dentro del margen de §2.

### 3.3 Fase 2 (necesita una cota mayor medida)

`LOAD_BUDGET` es lo mayor que se ha visto cargar, no el límite del motor:
- 2.986.112 se colgó (v14f);
- entre 2.724.608 y 2.986.112 no hay medidas (§23).

Antes de cambiar edificios hay que buscar la cota en Azahar por bisección, con las variantes de arriba (2.728.704,
2.732.160, 2.795.776, 2.872.064), entrando y saliendo por las puertas.

Si la cota sube:
- **Pirámide → casa de Lavacalda**: un pueblo junto al desierto, y quita el tejado azul (§24, sin arreglar);
- **Torre → casa-bloque de Férrica**: más alta, para el centro de la plaza;
- **Palacio → tejas doradas de Algaria**: además, deja de parecerse a la casa de la Torre (§24).

Riesgo: una cota medida solo en Azahar **no asegura la consola**. Subir `LOAD_BUDGET` sin prueba en consola es una
decisión del usuario.

Descartados:
- Domo → casa cúpula de Arrecípolis: +400 KiB sola;
- Fábrica → taller de vidrio: 2.795.392 sin letreros;
- árboles y arbustos: área 8, ~146 KB.

Retoque de coste cero no medido: teñir texturas propias de la isla (área 231, privada). El mismo tamaño no cambia el
presupuesto, pero los edificios del mismo área comparten nombre de textura. Diferenciarlos exige copias renombradas,
que sí cuestan. Queda como idea, sin tarea.

## 4. Regresión (política del usuario, 2026-11-11)

- Sala nueva de una instalación: es construcción común (isla y `island_build`), caso (c). Se prueban la plaza, la
  puerta de esa instalación (entrar y salir) y su flujo, caso (a): inscripción, un combate y pausa, guardar y cargar.
  Ni motor ni code.bin, salvo que la máscara de nativas cambie.
- Módulo genérico y el Domo pasado a él: build con el ZO de 456 idéntico byte a byte. Si es idéntico, basta una
  entrada y salida del Domo.
- Letreros, vallas y anfitriones: isla, caso (c). Plaza, leer los siete letreros y entrar y salir por las siete
  puertas, porque el pintor recalcula toda la celda. Sin combates.
- Bisección de la cota: solo cargar la isla y las puertas. Nunca empaquetar una variante sin medir.

## 5. Riesgos y no probado

- Nada de este diseño está probado en Azahar ni en consola.
- Colisiones y muebles de los donantes: el mapa de suelo no los ve. Los tuples y Azahar deciden. Si un donante
  falla, hay alternativa medida en §1.2.
- Salidas de llegada (358, 165): misma clase de problema que 365, resuelto allí con tuples y tipo 2 (§37.1). No
  está garantizado en otro mapa.
- Música y cámara del donante: no medidas.
- El trasplante de la rutina de letrero no se ha usado en este proyecto. CTRMap-F5 lo prueba en sus tests
  (`SignWrapperInjectTest`, `SignCommitTest`).
- Margen de la plaza tras la fase 1: 8.320 bytes (16.384 sin vallas). Cualquier pieza nueva del exterior compite
  por él.
- Partidas guardadas dentro de una sala que cambia de mapa: las coordenadas guardadas pueden caer en un mueble.
  Como en §34, salir antes a la plaza; el diseño lo documenta en el LEEME del paquete.

## 6. Tareas

`frontier/orch/propuestas/personalidad.json`, listas para `frontier-orch add`. Ninguna está encolada.
- `F10-SALAS-BASE`;
- `F10-SALA-FABRICA`, `F10-SALA-PALACIO`, `F10-SALA-ARENA`, `F10-SALA-TUBO` y `F10-SALA-PIRAMIDE`;
- `F10-LETREROS`;
- `F10-EXTERIOR-FASE1`;
- `F10-COTA-CARGA`, que pide una decisión del usuario sobre la consola;
- `F10-EXTERIOR-FASE2`.
