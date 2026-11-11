# Laboratorio de Cerebros (F8-CEREBROS-BASE)

Evidencia y alcance: `reports/frontier.md` §39. Usar solo el perfil aislado del carril y su puerto
(`work/lab-port` / `ORAS_GDB_PORT`); no instalar en una consola ni modificar una partida fuente.

Con la build de `frontier/overlay.py` instalada en el laboratorio y GDB conectado:

```sh
source scripts/env.sh
mkdir -p work/frontier/cerebros/base
python frontier/probes/brains/lab_probe.py > work/frontier/cerebros/base/probe.gdb
faraway/gdbctl.sh halt
faraway/gdbctl.sh cmd 'source work/frontier/cerebros/base/probe.gdb'
faraway/gdbctl.sh run
```

Por defecto observa. `pv_mode='win'` debilita al rival; `pv_mode='loss'` a nuestros participantes. Configurarlo
con GDB detenido antes del combate. Cambia PS y movimientos solo en las copias de combate, nunca resultados,
works, premios ni el equipo guardado. La asistencia no valida dificultad ni estrategia.

`BRAINS START` imprime entrenador, flags del motor, ruta, rachas y símbolos; `BRAINS RESULT` se imprime al consultar
IsWin, **antes** de que el script otorgue el símbolo o limpie una derrota. Para medir después, avanzar los textos,
detener GDB y ejecutar `python print(state(pv_save))`. Pausar con el menú real guarda el archivo del laboratorio;
inspeccionarlo con `faraway/save_event.py` y recargarlo para comprobar persistencia.

La sonda exporta `work/frontier/cerebros/base/rival-01.pk6` a `rival-03.pk6` al copiar el equipo desde el CRO,
antes de aplicar asistencia. Conservarlos en otra carpeta antes de un nuevo combate/arranque de la sonda.

```sh
python frontier/probes/brains/check_team.py work/frontier/cerebros/base/silver-team
python frontier/probes/brains/check_team.py work/frontier/cerebros/base/gold-team --variant gold
```

Comprueba checksum PK6 y todos los parámetros fijos del equipo de Anabel. No añadir estos PK6 ni partidas al Git.

Incidencias del entorno observadas en esta prueba: las órdenes de parada de GDB necesitan ejecutarse en el mismo
espacio de PID que lo arrancó; usar un conductor persistente cuando la herramienta aísle cada ejecución. Si Azahar
queda sin ventana en Qt/D-Bus, un bus de sesión privado permitió arrancar (`dbus-daemon --session --fork
--print-address=1 --print-pid=1`, pasar su dirección en `DBUS_SESSION_BUS_ADDRESS` y parar ese bus al terminar).
En la configuración del perfil, `use_gdbstub=true` necesita también `use_gdbstub\default=false`. Borrar solo el
framebuffer del laboratorio **después de reap y antes del nuevo Xvfb** evita capturas de un inode anterior.
Terminar siempre con `python scripts/azahar_lab.py reap` en el conductor que posee el laboratorio.

## Fábrica (Noland, F8-CEREBRO-FABRICA)

`factory_fixture.py SOURCE --sha256 H --streak 20|41 --output work/...sav` crea la copia (fuente pausada en 213).
`lab-start.sh` (variables `BUILD`, `FIXTURE`, `PROBE`) instala v0.5 + build y arranca con GDB y la sonda;
`k.sh` pulsa teclas (a=A s=B g/t/f/h abajo/arriba/izquierda/derecha); `snap.py NOMBRE` copia el guardado del
laboratorio y resume ruta, racha, símbolos, PB (0x4230) y hash del equipo. `check_team.py DIR --variant
silver|gold --factory-fixture FIXTURE.json` compara los PK6 con el generador. Resultados: `reports/frontier.md` §40.1.
