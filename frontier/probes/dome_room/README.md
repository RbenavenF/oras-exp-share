F6-DOMO-SALA: pruebas del mapa de 456. Evidencia en reports/frontier.md §37,
`work/frontier/dome/room`. No se modifica el código de combate.

Build: `source scripts/env.sh; python frontier/overlay.py --out work/frontier/dome/room/after`.
Antes: build anterior a la modificación del mapa, guardada en `room/before`;
script y code.ips tienen que coincidir entre las dos builds.

Usar un laboratorio del carril, una sola shell persistente (todos los comandos
incluido el cierre en ella), puerto desde ORAS_GDB_PORT/work/lab-port.
Instalar el overlay sobre una copia del mod v0.5 en work/azahar-lab; partida de
entrada `work/frontier/lab/f6h_saved_plaza.sav`. Nunca tocar el save original.
Esperar a que escuche el puerto del carril y otros 8 segundos antes de conectar
`faraway/gdbctl.sh start` (el stub puede rechazar conexiones al principio).

Teclas: `bash frontier/probes/pyramid/keys.sh ...` (t/g/f/h arriba/abajo/izquierda/derecha,
a/b, z abre X). `frontier/probes/pyramid/walk_to.py X Y` lee coordenadas RAM y
camina; no escribe posición. Solo un conductor cada vez.

Puerta: plaza (6,58), arriba dos veces → interior (16,31). Recorrido propuesto, pendiente de ejecutar completo: caminar primero al
norte hasta y25 por el eje de entrada y después a (23,25), mirar al norte y A
para hablar con uid1. No intentar ir lateralmente por y31: hay barreras de acceso
que no aparecen en la sonda de alturas del modelo. Warps/colisiones retail intactos.

Sonda de combate: `frontier/probes/pyramid/lab_probe.py` emite direcciones desde
los símbolos actuales. Para esta prueba se guardó una variante en room/probe.gdb:
lee los works 16473–16475 y 16649–16650, etiquetas DOME ROOM y modo win (rival a
1 PS con Salpicadura en RAM, copias servidor y cliente). No escribe resultados,
works, PB, racha ni partida. No es prueba de dificultad.

Cerrar con `python scripts/azahar_lab.py reap` (solo el carril), restaurar
use_gdbstub=false. El estado de tarea está en work/lane-task.json.

Estado al relevo: solo entrada por puerta y aspecto comprobados; inscripción,
combate, pausa, guardar/cargar nuevo y regresiones Fábrica/Torre pendientes.
Commit bloqueado por montaje ro de .git/worktrees/codex. El after_run del
orquestador debe ejecutar reap desde el host: dos shells interrumpidas pueden
haber dejado procesos de este carril fuera del namespace PID del último agente.
No tocar el laboratorio del otro carril.
