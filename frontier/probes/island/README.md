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
