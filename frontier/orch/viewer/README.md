# Frontier · Observatorio

Panel web local del orquestador **frontier-orch**. Python 3.10+; sin paquetes,
compilación ni CDN. Por defecto solo consulta; `--control` habilita acciones
con clave local. No es un controlador universal de otros orquestadores: `--root`
selecciona un checkout compatible con el esquema y CLI de este proyecto.

```bash
python3 frontier/orch/viewer/server.py --root /home/rbenaven/projects/oras-exp-share
```

Abre <http://127.0.0.1:8787>. Escucha por defecto en todas las interfaces IPv4 e
IPv6 (socket dual cuando está disponible; IPv4 como alternativa). Desde otro
equipo, abre `http://IP-DE-LA-MAQUINA:8787`. `--host 127.0.0.1` limita a loopback
y `--port` cambia el puerto. El acceso depende del encaminamiento y firewall de la red.

Durante el desarrollo aislado, el comando desde el checkout principal es:

```bash
python3 work/orch-viewer/frontier/orch/viewer/server.py --root "$PWD" --control
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
JSONL parcial se omite hasta la siguiente lectura. No hay WebSocket. Las consultas no escriben; las acciones requieren habilitar controles.

Los procesos se detectan en `/proc` con ejecutable y directorio del carril;
`in_progress` por sí solo **no** significa worker trabajando. Si el entorno oculta
procesos ajenos, la detección está limitada a los procesos visibles. La tarjeta
muestra la última tarea aunque ya no haya proceso. Los eventos no llevan hora si
la fuente no la proporciona; el tiempo indicado es la última modificación del log.

Las consultas sirven `/`, `/style.css`, `/app.js` y `/api/state`; no se permite
navegar archivos. Con `--control`, POST `/api/control` admite únicamente acciones
conocidas, JSON acotado, Origin del mismo sitio y Authorization con la clave local. El filtrado de secretos de los extractos es
preventivo, no exhaustivo. Las notas de tareas y la bitácora son datos del proyecto;
no uses un proxy público sin autenticación.

## Verificar

```bash
python3 -m unittest discover -s frontier/orch/viewer -p 'test_*.py' -v
```


## Controles de ejecución

La entrega local se inicia con `--control`. Al arrancar por primera vez crea
`work/orch/viewer-control.key` con permisos 0600 (fuera de Git). Copia su contenido
al campo **Clave de control** del panel. La clave solo se guarda en sessionStorage
del navegador hasta bloquear controles/cerrar la sesión; no se devuelve por la API.
No se incluyen claves en el código ni en las capturas. Reiniciar el visor conserva
la clave; eliminar el archivo con el servidor parado fuerza una nueva al arrancar.

- **Iniciar ejecución**: modo continuo (`auto --follow`) o paralelo finito
  (`auto --parallel`). Requiere confirmar el consumo de cuota en la interfaz.
  Arranca un proceso independiente del visor; cerrar la web no para los workers.
- **Terminar tareas y parar / drain**: completa las tareas actuales de los carriles,
  incluso si necesitan varias llamadas, y deja de tomar otras.
- **Parar tras esta ejecución / stop**: termina las llamadas actuales y sale aunque
  las tareas sigan abiertas. No mata workers a mitad de una llamada.
- **Cancelar parada / resume**: retira los indicadores pendientes; si el supervisor
  ya salió, hay que usar Iniciar.
- **Responder al bloqueo**: desde el detalle de una tarea bloqueada, con controles
  habilitados. Guarda la respuesta en `work/orch/viewer-replies/`. Si el supervisor
  está activo, pide `stop`; cuando salga, el visor toma su lock, comprueba que la
  tarea no cambió, conserva notas/evidencias y añade la respuesta del usuario.
  La tarea pasa a `in_progress`, se registra en bitácora y Git, y se libera el
  turno. Se reinicia su contador de falta de progreso. Después el usuario decide
  cuándo iniciar. Las respuestas pendientes sobreviven al reinicio del visor.

La parada y las respuestas se revisan con el ritmo del supervisor (hasta ~1 minuto
mientras espera); una llamada activa puede tardar más. El estado muestra respuestas
pendientes, aplicadas y fallidas. Una respuesta obsoleta o con archivos compartidos
sucios se rechaza sin sobrescribirlos: revisa el bloqueo antes de reenviar.
No se contestan prompts interactivos de las CLI ni se hace login desde la web.

El lock real `work/orch/orch.lock`, no solo `/proc`, impide duplicar el supervisor.
No se inicia si quedan workers huérfanos visibles. El proceso iniciado tiene salida
en `work/orch/viewer-supervisor.log`; las acciones se registran en
`work/orch/viewer-actions.jsonl`. No hay ejecución arbitraria de shell desde la API.
La web no cambia los cooldowns: iniciar no asegura disponibilidad de cuota.

Los controles actuales se dirigen al modo paralelo/continuo de frontier-orch; el
modo secuencial antiguo no consume los indicadores stop/drain. La escucha en LAN
usa HTTP y debe permanecer en una red de confianza. Para acceso por Internet,
requiere un proxy con HTTPS y autenticación; hacer público GitHub no expone el
servicio local ni sus datos de ejecución.
