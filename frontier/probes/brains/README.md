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

## Domo (Tucker, F8-CEREBRO-DOMO)

Informe `reports/frontier.md` §44; artefactos en `work/frontier/cerebros/dome/`.
Fuente `work/frontier/dome/room/paused-456.sav`, SHA256
`ec03f883df59a59703cff24a8a3da15df2d249c48eeae25a0fbdc6bb063d25d1`.
Sobre una copia, limpiar `patch.ACTIVE_WORK`, fijar ruta0, S/récord19, activo16474=1,
símbolos/pendiente0 con `faraway.save_event.edit`, validar checksums y escribir otra ruta de `work/`.
Oro: partir del guardado de plata ganado, conservar símbolo256 y PB13, fijar S/récord39,
ruta/pendiente0 y situarlo ante recepción (zona456, tile23,25; altura2).

Usar `lab_probe.py --directory work/frontier/cerebros/dome`, `lab-start.sh`, `BUILD` y `FIXTURE`.
Inscribir tres miembros mediante los menús del Domo; el preview enseña el trío de Tucker con objetos.
En el primer menú de elección, B vuelve al mismo preview. Elegir dos del jugador y comprobar que solo
hay dos Poké Balls por lado. La sonda usa el desplazamiento cliente de combates de dos miembros (`0x910`)
en ruta5, frente a `0xd98` de los combates de tres. Exporta antes de asistir.

```sh
python frontier/probes/brains/check_team.py work/frontier/cerebros/dome --facility dome
python frontier/probes/brains/check_team.py work/frontier/cerebros/dome --facility dome --variant gold
```

Conservar los PK6/JSON antes del siguiente arranque. El verificador acepta cualquier pareja distinta
del trío de la variante y comprueba todos sus parámetros, incluidos EV/IV exactos.
Tras plata, «Pausar» guarda símbolo256, bonus10 más3 PB del quinto torneo. Recargar y consultar «Símbolos».
La asistencia `win`/`loss` solo acelera el combate; jamás escribir `WORK_SYMBOLS`, resultados o PB.
La consulta IsWin imprime el estado anterior al premio/limpieza: medir de nuevo en recepción.
La derrota conserva récord y plata, limpia racha/activo/pendiente y las siete selecciones temporales
16649/50,16653/54/55,16657/58. El guardado automático retail se hace antes del retorno de ruta5 a0;
comprobar ese retorno en RAM después de los diálogos (o guardar de nuevo desde el menú del jugador).

## Fábrica (Noland, F8-CEREBRO-FABRICA)

`factory_fixture.py SOURCE --sha256 H --streak 20|41 --output work/...sav` crea la copia (fuente pausada en 213).
`lab-start.sh` (variables `BUILD`, `FIXTURE`, `PROBE`) instala v0.5 + build y arranca con GDB y la sonda;
`k.sh` pulsa teclas (a=A s=B g/t/f/h abajo/arriba/izquierda/derecha); `snap.py NOMBRE` copia el guardado del
laboratorio y resume ruta, racha, símbolos, PB (0x4230) y hash del equipo. `check_team.py DIR --variant
silver|gold --factory-fixture FIXTURE.json` compara los PK6 con el generador. Resultados: `reports/frontier.md` §40.1.

## Palacio (Spenser, F8-CEREBRO-PALACIO)

Aceptación en `reports/frontier.md` §42, artefactos en `work/frontier/cerebros/palace/`.
La fixture parte de `work/frontier/lab/pa_paused7.sav` (SHA256
`012e718ba50c3dbab606987958a3351aec79840025e385e25d73ed3c98e48c7c`), ya pausada en zona 340,
con 16462=1. Usar `faraway.save_event.edit` sobre sus bytes y escribir otra ruta en `work/`:
plata `{16438:0,16461:20,16463:20,16729:0,16730:0}`; oro desde el guardado de plata ganado,
`{16438:0,16461:41,16463:41,16730:0}`, conservando 16729=16. Comprobar hash, zona y activo
antes de editar; nunca sustituir la fuente. Estos números son los works asignados en REPARTO.

Generar overlay completa y sonda con `lab_probe.py --directory work/frontier/cerebros/palace`;
arrancar con `BUILD`, `FIXTURE` y `PROBE` en `lab-start.sh`, siempre en un conductor persistente
que también ejecute GDB y la limpieza. En Palacio el combate avanza por IA sin órdenes manuales;
las teclas solo avanzan diálogos/selección de equipo. Capturar los PK6 antes de asistencia:

```sh
python frontier/probes/brains/check_team.py work/frontier/cerebros/palace/silver-team --facility palace
python frontier/probes/brains/check_team.py work/frontier/cerebros/palace/gold-team --facility palace --variant gold
```

Para conservar el símbolo: tras ganar, «Pausar» en el menú de siguiente combate guarda la partida;
recargarla y usar «Símbolos» en la recepción. Comparar equipo (0x14200, 0x61c bytes) y cajas
(bloque 56 del guardado ORAS: 0x33000, 0x34ad0 bytes) con la fixture; `scripts/save_fixture.blocks`
valida sus checksums. Tras perder, comprobar racha/activo/ruta/pendiente=0, plata=16 y récord conservado.

## Arena (Greta, F8-CEREBRO-ARENA)

Informe `reports/frontier.md` §43; artefactos en `work/frontier/cerebros/arena/`.
Fuente de la fixture: `work/frontier/lab/ar_paused9.sav`, SHA256
`093ed149abb9054559480270eba79e36c5457e4fd3e940e6b7940a86cd4cc239`, zona 457,
activo 16466=1. Crear copia con `save_event.edit`, works
`{16438:0,16465:27,16467:27,16729:0,16730:0}` para plata. Oro desde el guardado de
plata ganado, racha/récord 55 y pendiente 0, conservando el símbolo (16729=64).
Nunca sobrescribir la fuente. Construcción y arranque igual que Palacio, con rutas de Arena.
`check_team.py DIR --facility arena [--variant gold]` valida los tres PK6 previos a asistencia.

Para ejercitar el juicio en el combate de Greta, generar `frontier/lab_arena_probe.py --mode win`
en `work/` y adaptar esa copia: al final de `ar_enter`, antes del print, añadir
`if ar_mode != 'normal': ar_harmless(mon)`; en `ar_end` aplicar `ar_harmless` a ambos
`mons[0]` y `mons[1]`. Cargar tras la sonda de Cerebros, manteniendo `pv_mode='normal'`.
Así ambos usan Salpicadura y el juicio recibe PS completos para el jugador y 1 para
el rival al tercer turno (Shedinja conserva 1/1 y empata). No altera script, resultado,
works, premios ni equipo guardado. La prohibición de cambiar se comprueba con el menú
Pokémon y otro participante. Para derrota, reiniciar con la misma sonda adaptada y `ar_mode='loss'` (invierte los PS al tercer turno),
conservando `pv_mode='normal'`.

La comparación `brains.assemble()` con y sin las filas de Arena está en
`native-data-only.json`: instrucciones y símbolos idénticos, solo cambian las dos filas
Greta de `brain_table` (datos privados); no se modifica el motor de Arena ni otro gancho.

## Tubo (Lucy, F8-CEREBRO-TUBO)

Informe `reports/frontier.md` §45; artefactos `work/frontier/cerebros/pike/`.
Usar una partida realmente pausada: fuente `work/frontier/lab/pa_paused7.sav`, SHA256
`012e718ba50c3dbab606987958a3351aec79840025e385e25d73ed3c98e48c7c`.
Con `faraway.save_event.edit`, limpiar los siete `patch.ACTIVE_WORK`, poner activo16478=1,
S16477/récord16479=27, ruta16438=0, símbolos16729/pendiente16730=0 y posición(458,22,2,24).
PS16661..16663=60,70,80; estados16669..16671=0,0,1; seis works PP16721..16723/16725..16727=0x0505.
Se puede dejar PIKE_WILD16675=217 para verificar que Lucy lo limpia. Validar checksums; escribir copia en work/.
`lab_probe.py --directory work/frontier/cerebros/pike`, `lab-start.sh` con BUILD/FIXTURE/PROBE; usar puerto del carril.
Elegir tres participantes. La sonda en modo win exporta los tres rivales antes de debilitarlos.
Conservar `rival-0*.pk6` en `silver-team` y ejecutar:

```sh
python frontier/probes/brains/check_team.py work/frontier/cerebros/pike/silver-team --facility pike
```

Desde §46 la tabla usa Shuckle DefE152 (total510, límite de ORAS) y pasa con rc0; oro igual con `--variant gold`.
`lab_probe.py` genera `pv_mode='normal'`: poner `win`/`loss` (en el fichero o con `python pv_mode=...` en GDB
detenido) antes de que salgan los Pokémon. En recepción: Combatir → Combate Individual → Participar → Sí.
El resultado raw1 se imprime antes del premio; avanzar y medir state(pv_save): S28, símbolo1024, pendiente0.
Para guardar, elegir «Pausar» en el menú de siguiente combate; evitar pulsaciones A en lote tras la victoria,
porque aceptan continuar y entran en las puertas de la siguiente ronda. Oro parte de S139 conservando plata.
Para medir retención: hooks pasivos de SET_HP0x14f450 y SET_SICK0x14f814 restringidos a LR en
pike_build..pike_iswin, y pike_pp+32 (ver símbolos de la build), además de PP/PS en arena_enter.
No interpretar como estado el offset0x34 de la sonda local: no está validado.

## Pirámide (Brandon, F8-CEREBRO-PIRAMIDE)

Informe `reports/frontier.md` §47; artefactos en `work/frontier/cerebros/pyramid/`. Fixture: copia de una partida
en el vestíbulo con desafío, editada con `faraway.save_event.edit` a S/récord 20 (o 69), activo 16482=7,
vencidos 16686=7, ruta 7 y los demás activos a 0; hablar con la recepcionista (reanudar) lleva al piso 7 (zona 141,
llegada 12,16). Caminar con `frontier/probes/pyramid/walk_to.py` 10 16 → 10 7 → 12 7, mirar arriba y hablar con
el encargado. Para el pendiente guardado, 16731 = variante y la racha ya contada (21/70).
`check_team.py DIR --facility pyramid [--variant gold]`. La recepcionista de símbolos está en la casilla 17,24.
