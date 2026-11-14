# F11: laboratorio de ocho celdas (no paquete de entrega)

`source scripts/env.sh`; `python frontier/probes/island/build.py` genera en
`work/f11/prototype` una copia del staging de isla y del paquete v0.2. No modifica
los builders comunes. Requiere los artefactos locales indicados en `build.py`;
si faltan, el integrador debe regenerar el staging/paquete con su procedimiento
habitual. No usar un staging de otra versión sin revisar los hashes.

La zona 209 conserva su área privada, sustituye su matriz por 4×2 regiones nuevas
y pinta la referencia a escala 1:1 con OFFSET (16,4). Se vacían las entidades;
los huecos de edificios son terreno bloqueado. Solo se abre el pasillo de recepción
(26,61–65) para conectar muelle y plaza sin edificio. Los materiales se comparten
en un solo AD[11]. `build.log` registra cada región, texturas ausentes y load budget;
`hashes.json` identifica los archivos del mod. No se modifica code.ips ni CRO.

`bash frontier/probes/island/boot.sh SAVE` instala el mod y una copia de SAVE
exclusivamente en el laboratorio del carril. SAVE debe estar fuera de la isla vieja:
por ejemplo, un checkpoint del puerto de Calagua con Pase del Frente y Ticket.
El valor predeterminado es una fixture de historia en Ruta 102, que **no** sirve
para hablar directamente con el ferry.

En el sandbox, mantener el shell que arranca Azahar vivo (PTY) y ejecutar ahí
los controles GDB y la limpieza: los PID cambian de namespace entre execs. Al acabar,
`python scripts/azahar_lab.py reap` desde ese mismo shell. No usar puertos ni PID
ajenos al carril. Las pruebas de movimiento leen coordenadas, nunca las escriben.
