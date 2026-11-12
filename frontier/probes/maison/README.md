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

## Llegar a recepción sin editar RAM

Primera llegada: avanzar los diálogos hasta el campo. Muelle 212 → plaza 210
(pasar por 37,15); tras los diálogos, 210 (56,92) y subir a 211 (56,86).
En 211 ir a (58,77) y subir: vestíbulo 516. Rodear por las escaleras de x10:
(14,16) → (10,16) → (10,7) → (14,7) → (14,4), subir a sala 517.
Desde (19,31): (19,28) → (18,28) → (18,25). Recepción de combates en (23,25);
la de (17,25) solo muestra registros. Guardar desde el menú del juego en copia local.

Copia local de esta sesión: `work/frontier/console-maison/reception.sav`, SHA256
`98089a843e04b8f9f2c13e7209390a94b92d0bcc0e9f5f98436dbe20e8365bd3`.
Derivada del Checkpoint publicado únicamente mediante ferry, diálogos, caminata y
Guardar; equipo sin modificar. Sala517 (17.5,25.5), works16438/16489/16685=0.
No añadir esta partida ni capturas de recursos del juego a Git.

El cargador sustituye los marcadores de breakpoint del CRO, incluso los de tipo
hardware en Azahar. `trace.gdb` arma el punto CRO después de cargar DllBattle,
desde el asignador estable de code.bin; lo desactiva al volver al campo. Vacía la
caché de registros de GDB en cada callback, antes de medir. Un error de la sonda
se distingue expresamente de `MAISON EMPTY` y no demuestra un fallo del juego.

## Pila y montón (Claude, 2026-11-12)

* `stack.gdb`: en el constructor de cliente (CRO 0x7336c, cliente 0) imprime `STACKWORDS`, los 0x198 bytes
  desde sp, lo mismo que guarda Luma. Se arma en StartBattle (0x1e33dc) → asignador 0x12bad4 y se desarma
  solo (si se deja 0x12bad4 activo, el emulador va a 0 FPS: no es un cuelgue del juego).
* `stackdiff.py DUMP.dmp LOG`: compara la pila del volcado con la del laboratorio y traduce el puntero del
  cliente a Pokémon en el combate: 0x488 por Pokémon de ambos bandos (dos objetos de 0x244; contenedor
  0x81fb588), 3+3 → 0x820d9ac, 2+2 → 0x820d09c, 4+4 → 0x820e2bc, 6+6 → 0x820f4dc.
* `gdbctl.sh start` vacía `work/faraway/gdb/out.log`: copiar el registro antes de reiniciar el laboratorio.
