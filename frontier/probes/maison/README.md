# F7-CONSOLA-MANSION

Solo laboratorio del carril, puerto de `work/lab-port`. No altera ROM, partida fuente ni RAM.

* `dump.py /ruta/al/dump.dmp`: comprueba cabecera/tamaños, registros y los 96 bytes
  anteriores hasta el PC frente a las distribuciones publicadas alfa y v0.5. La base
  CRO 0x6f3000 es la de este incidente. El volcado no contiene el heap del cliente:
  una cuenta cero se deduce del camino de instrucciones, no de leer su objeto.
* Arranque: `frontier/probes/package/boot.sh
  dist/oras-frontier-checkpoint-test-v0.1/FrenteTest-puerto-Calagua/main`.
  Verifica los 37 ficheros del manifest; no usar overlay reconstruida para reproducir.
* En el mismo conductor persistente que arrancó el laboratorio:
  `faraway/gdbctl.sh halt`, `faraway/gdbctl.sh cmd 'source frontier/probes/maison/trace.gdb'`,
  `faraway/gdbctl.sh run`. Registra selección (incluida Caja de Combate), tamaño final
  del equipo y cliente. Se detiene antes del acceso nulo si la cuenta es cero.
  Comprueba la instrucción del punto CRO para evitar interpretar otra base como cliente.
* Ferry: desde la partida publicada (27,24), caminar a (27,26), (19,26), (19,25),
  mirar izquierda y hablar. No ir primero al oeste por y24: el marinero bloquea (22,24).
  Elegir Resort Batalla. Usar menús retail de Mansión, sin activar una instalación.
* Conservar `work/faraway/gdb/out.log` por modalidad en `work/frontier/console-maison/`.
  Si se detecta vacío, comparar misma modalidad/selección con v0.5 antes de atribuir causa.
  Parar siempre el laboratorio del carril con `python scripts/azahar_lab.py reap`.

Si el sandbox aísla PID por llamada, todas las órdenes que hacen `halt` y la limpieza
se ejecutan desde el conductor que inició GDB. Las capturas/lecturas de archivos pueden
hacerse desde otro proceso. No interrumpir el conductor con Ctrl-C: termina también
sus procesos de laboratorio. No tocar procesos de otro carril.
