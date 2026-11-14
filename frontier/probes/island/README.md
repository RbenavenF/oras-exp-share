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
y pinta la referencia a escala 1:1 con OFFSET (16,4). Se vacían las entidades;
los huecos de edificios son terreno bloqueado. Solo se abre el pasillo de recepción
(26,61–65) para conectar muelle y plaza sin edificio. Los materiales se comparten
en un solo AD[11]. `build.log` registra cada región, texturas ausentes y load budget;
`hashes.json` identifica los archivos del mod. No se modifica code.ips ni CRO.
Cada GR se clona del contenedor ORAS retail de siete subficheros y solo se sustituyen
0–3: crear uno nuevo de seis (XY) dejó este prototipo en pantalla blanca al llegar.
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
