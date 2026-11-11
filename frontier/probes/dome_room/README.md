F6-DOMO-SALA. Diseño: reports/diseno/domo.md; medidas y aceptación:
reports/frontier.md §37. Artefactos locales en work/frontier/dome/room (no se suben
ROM, archivos comerciales ni partidas). Implementación inicial: 80068a1.

Build: `source scripts/env.sh; python frontier/overlay.py --out work/frontier/dome/room/exit-tiles`.
456 usa mapa/área de 365, texto 619, script Domo y nativas de 517. El warp retail
365 es de tipo 0 (sin retorno): se cambia a 2 (contacto), manteniendo plano 0,
posición y destino 209/warp 1. Las tres casillas (15–17,31) cambian de tuple
20300000 a 20000000, medido en la salida de 517. Solo se edita el mapa propio
del clon; el constructor exige los bytes originales. El guard valida tipo y plano.
ZO 15452 <= 17248; carga 305024 <= 2724608; code.ips no cambia.

Un solo laboratorio del carril y una shell conductora persistente (también para
reap). Puerto ORAS_GDB_PORT/work/lab-port; nunca usar el de otro carril. Instalar
el overlay sobre copia de v0.5 en work/azahar-lab. Fixture de entrada:
work/frontier/lab/f6h_saved_plaza.sav. Nunca tocar la partida original.
Esperar puerto y otros 8 segundos antes de conectar faraway/gdbctl.sh start.
GDB start ya continúa; no es necesario enviar run otra vez.

Teclas: `bash frontier/probes/pyramid/keys.sh ...`: t/g/f/h arriba/abajo/izquierda/
derecha, a=A, s=B, z=X. En diálogos avanzar mirando la captura: el menú se abre
tras otro A; enviar secuencias a ciegas puede empezar otra inscripción.
`frontier/probes/pyramid/walk_to.py X Y` lee RAM sin escribir posición. Si GDB
responde tarde con dos laboratorios, esperar la respuesta en out.log; no interpretar
una respuesta vacía como coordenadas válidas ni conducir en paralelo.

Plaza (6,58), norte dos veces → sala (16,31). Para recepción ir primero a (16,25),
luego (23,25), mirar norte y A. Las barreras de entrada impiden ir lateralmente
por y31. Se inscribieron Torchic/Beldum/Poochyena y se eligieron dos para combatir.
Para salir, volver por (16,25) a (16,29), sur por el centro del warp retail:
warp de vuelta a (6,57). Entrada y salida repetidas desde la build exit-tiles.

Sonda reproducible: `python frontier/probes/dome_room/lab_probe.py > work/frontier/dome/room/probe.gdb`.
Generar con el checkout de la build instalada. Modo normal es pasivo. En GDB,
`python pv_mode='win'` pone al rival 1 PS/Salpicadura solo en RAM de combate.
Las copias cliente/servidor del Domo están a 2*0x488 = 0x910 (no 0xd98 de la
Pirámide de tres Pokémon). `python watergun()` cambia el primer movimiento del
primer inscrito en ambas copias de combate a Pistola Agua para el fixture de nivel
bajo frente a Fantasma/Absorbe Fuego. No cambia equipo guardado, resultados,
racha, PB ni works. La victoria instrumentada comprueba flujo, no dificultad.

Cerrar: `python scripts/azahar_lab.py reap`; restaurar use_gdbstub=false y comprobar
own_processes() vacío desde la misma shell. Estado para supervisor: work/lane-task.json.
