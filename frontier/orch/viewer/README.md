# Frontier · Observatorio

Visor web local **de solo lectura** del orquestador. Python 3.10+; sin paquetes,
compilación, CDN ni conexión a proveedores. No ejecuta comandos del proyecto.

```bash
python3 frontier/orch/viewer/server.py --root /home/rbenaven/projects/oras-exp-share
```

Abre <http://127.0.0.1:8787>. `--port` cambia el puerto. Se vincula exclusivamente
al loopback: no publica los logs en Internet. Desde otro equipo, usa un túnel SSH
(`ssh -L 8787:127.0.0.1:8787 usuario@maquina`) y abre la misma URL.

Durante el desarrollo aislado, el comando desde el checkout principal es:

```bash
python3 work/orch-viewer/frontier/orch/viewer/server.py --root "$PWD"
```

## Servicio local

La entrega está arrancada en la sesión tmux `frontier-viewer`, independiente de
las sesiones del supervisor. Para ver su consola: `tmux attach -t frontier-viewer`.
Para parar solo el visor: `tmux kill-session -t frontier-viewer`.
No se instala arranque automático tras reiniciar la máquina.

El código vive en la rama `feature/orch-viewer`, checkout `work/orch-viewer`.
No se integra en el checkout principal mientras el supervisor tiene su turno.
Los datos siempre se leen del checkout que se indica con `--root`.

## Qué muestra

- Vista general, workers y última bitácora.
- Cola en el orden original de `tasks.json`, búsqueda, filtros, dependencias y
  detalle de criterios/notas/evidencias. El orden no promete ejecución serial:
  el supervisor decide según dependencias, asignación y disponibilidad.
- Estado de cuota: **espera registrada**, no saldo ni porcentaje del proveedor.
  Si se recupera cuota fuera del supervisor, su fecha puede seguir obsoleta.
- Actividad: extractos de comandos, mensajes y cambios de archivo de logs
  JSONL Codex/Claude. No se sirven logs crudos ni salidas de herramientas.
- Herramientas: explicación del flujo documentado, no inventario de procesos activos.

Actualización cada 3 segundos; caché del servidor 2 segundos. Solo se leen las
colas de logs (máximo 160 KB por worker), no archivos enormes completos. Una línea
JSONL parcial se omite hasta la siguiente lectura. No hay WebSocket ni escrituras.

Los procesos se detectan en `/proc` con ejecutable y directorio del carril;
`in_progress` por sí solo **no** significa worker trabajando. Si el entorno oculta
procesos ajenos, la detección está limitada a los procesos visibles. La tarjeta
muestra la última tarea aunque ya no haya proceso. Los eventos no llevan hora si
la fuente no la proporciona; el tiempo indicado es la última modificación del log.

Solo se sirven `/`, `/style.css`, `/app.js` y `/api/state`; no se permite navegar
archivos ni mutar el estado por HTTP. El filtrado de secretos de los extractos es
preventivo, no exhaustivo. Las notas de tareas y la bitácora son datos del proyecto;
no uses un proxy público sin autenticación.

## Verificar

```bash
python3 -m unittest discover -s frontier/orch/viewer -p 'test_*.py' -v
```
