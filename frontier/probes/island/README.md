# F11: laboratorio de ocho celdas (no paquete de entrega)

`source scripts/env.sh`; `python frontier/probes/island/build.py` genera en
`work/f11/prototype` una copia del staging de isla y del paquete v0.2. No modifica
los builders comunes. Requiere los artefactos locales indicados en `build.py`;
si faltan, el integrador debe regenerar el staging/paquete con su procedimiento
habitual. No usar un staging de otra versión sin revisar los hashes.
Antes de copiar, el generador valida el manifiesto del paquete v0.2 y los ficheros
de staging no cubiertos por ese paquete contra el manifiesto baseline; registra
las fuentes verificadas en `sources.json`.

La zona 209 conserva su área privada, sustituye su matriz por 4×2 regiones nuevas
y pinta la referencia a escala 1:1 con OFFSET (16,4). Se retira el resto de entidades
y se conserva al empleado del ferry (UID 0, modelo 300, script 2), en (34,71);
los huecos de edificios son terreno bloqueado. Solo se abre el pasillo de recepción
(26,61–65) para conectar muelle y plaza sin edificio. Los materiales se comparten
en un solo AD[11]. `build.log` registra cada región, texturas ausentes y load budget;
`hashes.json` identifica los archivos del mod. No se modifica code.ips ni CRO.
La exportación copia los cuatro GARCs: zona `a/0/1/3`, área `a/0/1/4`, geometría
`a/0/3/9` y matriz `a/0/4/0`. boot.sh comprueba el manifiesto antes de instalar y
los hashes instalados después (`installed-hashes.json`). Omitir área o geometría
invalida el ensayo, aunque el cálculo estático del presupuesto sea correcto.
Cada GR se clona del contenedor ORAS retail de siete subficheros; se sustituyen
0–3 y se asignan fila/columna en los dos primeros bytes de GR[4], conservando el resto.
Crear uno nuevo de seis (XY) dejó este prototipo en pantalla blanca al llegar.
Las escaleras conservan su pendiente/material, con comportamiento de andar normal:
el `0x6c` del catálogo impedía subir el peldaño de recepción en este prototipo.

`bash frontier/probes/island/boot.sh SAVE` instala el mod y una copia de SAVE
exclusivamente en el laboratorio del carril. SAVE debe estar fuera de la isla vieja:
por ejemplo, un checkpoint del puerto de Calagua con Pase del Frente y Ticket.
El valor predeterminado es una fixture de historia en Ruta 102, que **no** sirve
para hablar directamente con el ferry.

En el sandbox, mantener el shell que arranca Azahar vivo (PTY) y ejecutar ahí
los controles GDB y la limpieza: los PID cambian de namespace entre execs. Al acabar,
`python scripts/azahar_lab.py reap` desde ese mismo shell. No usar puertos ni PID
ajenos al carril. Las pruebas de movimiento leen coordenadas, nunca las escriben.

`python frontier/probes/island/ferry.py` parte de la fixture del puerto, sale a
Calagua y vuelve, guarda mediante la UI un `harbor-checkpoint.sav` y toma el ferry.
Exige la llegada nueva (35,71), con captura y lectura de coordenadas. La pantalla
blanca por sí sola no demuestra que se haya excedido un presupuesto de memoria.
Con el checkpoint real ya guardado, arrancar con `harbor-checkpoint.sav` y usar
`ferry.py --at-clerk` evita repetir la salida/reentrada del puerto.

Tras llegar: `python frontier/probes/island/route.py` recorre las ocho celdas por
caminos del calco; `python frontier/probes/island/checkpoint.py terrain-saved`
guarda mediante UI y valida ubicación/checksums. Reiniciar con boot.sh y esa copia
para comprobar persistencia fuera de la celda de llegada. Los scripts se deben
ejecutar secuencialmente: no compartir el FIFO GDB entre dos drivers.
Después de recargar, `route.py --pier` vuelve andando de la plaza al muelle.
No hay puertas de instalaciones en este prototipo; las prueba F11-ISLA-CONSTRUCCION.

Diagnóstico del regreso tras recargar (todavía no es una aceptación):

- `F11_GDB=0 bash frontier/probes/island/boot.sh SAVE` desactiva el stub. El arranque
  fija también su marca `default` para que Azahar respete el valor explícito.
- Desde el checkpoint `terrain-saved.sav` en (119,45),
  `python frontier/probes/island/return_ui.py NOMBRE` mantiene izquierda y exige un
  **nuevo** guardado UI al oeste de x=99. Usa `checkpoint.py --ui-only`: no lee GDB.
  El hash sin cambiar es fallo; los CRC del guardado anterior no prueban respuesta.
- `build.py --trial world --trial props --trial lod --trial compact --trial names`
  reproduce las variantes acumuladas, con sus presupuestos en build.log y orden en
  config.json. No ejecutar sobre un prototipo existente: conservar su game/ws y
  regenerar con build.py. Estos ensayos no modifican los builders de producción.
- `world` conserva solo las texturas referenciadas por los modelos (también las
  de sus mallas degeneradas); `props` exige ausencia de props y vacía su registro,
  dejando un BCH válido de una textura. `lod` asigna todos los cuartos a 209, sin
  modelos LOD. `compact` une rectángulos de suelo plano con UV de mundo 1/72;
  conserva escaleras, paredes, tilemap y colisión. La iluminación AO se interpola
  entre las esquinas del rectángulo; no usarlo como aprobación del aspecto final.
- `names` da a cada celda un nombre BCH propio, como los nombres retail de 489–492.
  Sustituye el prefijo de igual longitud dentro de la sección de strings; conserva
  todos los offsets. Es una hipótesis en ensayo, no una causa demostrada del bloqueo.
- Controles adicionales: `animations` usa el BCH vacío retail del área 0; `camera`
  su tabla vacía de cámaras; `flatcollision` sustituye la colisión por una plataforma
  a altura 36; `retailmodels` usa modelos intactos de 489–492 y sus texturas.
  Son controles diagnósticos acumulados, no un terreno aceptado ni una solución.
- `coordinates` asigna fila y columna a los primeros dos bytes de GR[4], siguiendo
  el patrón medido en los GR retail 489–492. Se prueba como hipótesis separada:
  clonar 489 dejaba (0,0) en las ocho celdas. Conservar el resto de GR[4].

Censo de coordenadas, sin modificar archivos del juego (tras preparar el workspace):

```sh
javac --release 8 -nowarn -cp work/faraway/classes:tools/CTRMap-F5/build/classes \
  -d work/faraway/classes frontier/probes/island/GRCoordinates.java
java -Djava.awt.headless=true -cp work/faraway/classes:tools/CTRMap-F5/build/classes \
  faraway.GRCoordinates work/f11/prototype/game work/f11/prototype/ws
```

Compara matriz y GR[4] en Ferrica, Calagua, una matriz 16×6, los tres exteriores
del Resort y la isla. Imprime los desacuerdos; no reescribe la geometría.

Rectificación del hito 5: las instalaciones manuales de variantes omitían área y
geometría. Sus resultados de ejecución no permiten excluir esas hipótesis. La
construcción completa con build.py sí exportaba los cuatro archivos; por eso el
ferry, recorrido y guardado del prototipo inicial mantienen su evidencia.

## F11-ISLA-CONSTRUCCION: la isla de producción

Desde F11-ISLA-CONSTRUCCION la isla la construye `frontier/island_build.py` (clase Java
`faraway.Island` → `ctrmap.tests.FrontierIsland`), no este prototipo. Para probarla:

```sh
source scripts/env.sh
python frontier/overlay.py --out work/f11/build/out \
  --romfs dist/held-exp-share-v0.5/mods/000400000011C400/romfs        # build (≈10 s)
python frontier/probes/island/lab_mod.py                               # v0.5 + build → work/f11/build/mod
F11_OUT=work/f11/build bash frontier/probes/island/boot.sh work/f11/saves/checkpoint_harbor.sav
python frontier/probes/island/drive.py NAME ferry sailor               # pase + ferry → (34,73)
python frontier/probes/island/doors.py NAME [FACILITY ...] [--pier]    # cada puerta: entrar, salir, escalón
```

`doors.py` calcula las rutas con `island_build.route` sobre la misma rejilla que se pinta
(rodeando la caja de cada edificio provisional salvo el escalón de su puerta) y exige que al
salir el jugador quede en el escalón de su puerta. `TopView.java` dibuja desde arriba los
modelos de las ocho celdas tal como se han construido (puertas en rojo, PNJ en azul) y
`topview_montage.py` lo pone bajo la referencia del usuario a la misma escala:

```sh
CP=work/faraway/classes:tools/CTRMap-F5/build/classes:tools/CTRMap-F5/lib/jogl-all.jar:tools/CTRMap-F5/lib/gluegen-rt.jar
javac --release 8 -nowarn -cp $CP -d work/faraway/classes frontier/probes/island/TopView.java
java -Djava.awt.headless=true -cp $CP faraway.TopView work/f11/build/out-island/game work/f11/build/out-island/ws 209 OUT.png 8
/usr/bin/python3 frontier/probes/island/topview_montage.py OUT.png MONTAGE.png   # Pillow
```

El prototipo de terreno sigue aquí como laboratorio; usa también `island_layout.OFFSET`, que
pasó de (16,4) a (15,6) para que ningún edificio provisional cruce el borde de una celda.
