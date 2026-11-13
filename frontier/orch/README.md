# frontier-orch: el Frente de Batalla sin escribir «continúa»

Un supervisor que ejecuta las tareas de `tasks.json` con Claude Code y Codex en modo no interactivo, de una en una.

```bash
tmux new -d -s frente 'frontier/orch/frontier-orch auto; read -p "[frontier-orch terminado] Enter para cerrar"'
frontier/orch/frontier-orch status     # tareas, cuotas en espera, turno
frontier/orch/frontier-orch auto       # trabaja hasta acabar, bloquearse o quedarse sin progreso
frontier/orch/frontier-orch once       # una sola ejecución de un agente
frontier/orch/frontier-orch release    # devuelve el turno si el propio supervisor murió
```

Para pararlo: Ctrl+C. El turno de `REPARTO.md` se devuelve al salir. Si el supervisor muere de golpe, usa `release`.

## Qué hace

1. Toma el turno de `frontier/REPARTO.md` (se niega si lo tiene otra sesión) y lo devuelve al terminar.
2. Elige la primera tarea abierta: primero `in_progress`, luego `pending`, en el orden de `tasks.json`.
3. Se la da a su dueño si tiene cuota. Si no, al otro agente.
4. **Si la tarea sigue abierta**, la reanuda en la misma sesión con «Continúa la tarea…», sin que nadie escriba nada.
   Excepción: un agente con `"fresh_sessions": true` en `config.json` (Codex) empieza siempre una sesión nueva con
   el brief completo y el aviso de que la tarea ya está empezada. Medido el 2026-11-04: la sesión reanudada del Domo
   reenviaba ~142k tokens por llamada (124 llamadas, 17,2 M de entrada) y gastaba la cuota de Codex en ~15 min.
   Las órdenes de Codex fijan además `model_reasoning_effort="medium"`.
5. **Si un agente agota su cuota**:
   - lo deja en espera hasta la hora que da el aviso, más 2 minutos (Claude: «resets 6:30am»; Codex: «try again at
     10:04 AM»). Si el aviso no da hora, `cooldown_minutes` (30);
   - pasa la tarea al otro con un aviso de relevo: revisar `git status`/`git diff`, porque puede haber cambios a
     medias.
6. **Si los dos están en espera**, duerme hasta que el primero vuelva.
7. **Cuando el agente marca la tarea `done`**, pasa los tests de aceptación (`acceptance`, la suite). Si fallan, la
   reabre con el fallo en `notes`.
8. **Se detiene y te espera** si:
   - una tarea queda `blocked` (el agente pone su pregunta en `notes`);
   - hay `no_progress_limit` (2) ejecuciones seguidas sin ningún cambio en el repositorio;
   - se llega a `max_runs` (40) ejecuciones de agente. Las esperas no cuentan.
9. **Tras cada ejecución**, `after_run` para cualquier laboratorio de Azahar que haya quedado abierto.
10. **Si un agente pierde la sesión** («Failed to authenticate: OAuth session expired…», medido el 2026-11-03 a los 37
    minutos):
    - queda fuera hasta el próximo `auto` y el otro hereda la tarea;
    - si los dos están sin login, se para y lo dice;
    - tras hacer login (`/login` en Claude, `codex login`), vuelve a lanzar `auto`.

Para seguir una ejecución en directo: `frontier/orch/frontier-orch status` (funciona con `auto` en marcha) da el
registro actual; `tail -f` sobre él.

Registros de cada ejecución en `work/orch/logs/`; lo que dice el propio supervisor, en `work/orch/orch.log` (sobrevive
a la terminal); estado (sesiones, esperas) en `work/orch/state.json`.

## Permisos (decididos y medidos el 2026-11-03)

- **Claude**: `-p --output-format stream-json --verbose --permission-mode auto --permission-prompts none`.
  - `-p` no admite `bypassPermissions`;
  - en modo `auto` el propio Claude Code decide cada acción;
  - lo que pediría confirmación se deniega en vez de quedarse esperando.
- **Codex**: `exec` con `sandbox_mode="workspace-write"` y `approval_policy="never"`, más dos ajustes:
  - `sandbox_workspace_write.writable_roots=["<repo>/.git"]`: sin él, `.git` es de solo lectura y Codex no puede
    hacer commit (medido: `index.lock: Read-only file system`);
  - `network_access=true`, porque gdb habla con Azahar por localhost.
- **Medido con las herramientas reales** en un repositorio de prueba:
  - Claude y Codex hacen cada uno su tarea, con commits, sin intervención;
  - la reanudación de Codex hace commit;
  - Codex arranca, captura y para el laboratorio desde su sandbox.
- **Sin probar con las herramientas reales**:
  - un límite de uso de verdad (se ha probado con agentes falsos, `tests/test_frontier_orch.py`);
  - gdb desde el sandbox de Codex.

Cada ejecución gasta cuota. Con `max_runs` y el freno por falta de progreso no hay bucles infinitos, pero una tarea
larga puede consumir mucho. `status` dice cuántas ejecuciones lleva.

## Política de regresión (2026-11-13: regresión agrupada)

Va en el mensaje de cada agente (`brief` de `config.json`). Al integrar, el orquestador solo pasa la suite
(`pytest`, ~50 s).
- **Cada tarea**:
  - la suite y las pruebas sin emulador (VM/Unicorn) de lo que toca;
  - en Azahar, **solo lo nuevo**: la función hecha, una vez. Si toca la isla o la construcción común
    (`island_build.py`, `overlay.py`, `faraway/java/`), la plaza y las puertas que cambien;
  - excepción: si mueve o reescribe código que ya funcionaba, prueba también lo movido.
- **Cada alfa** (F7-PAQUETE-*): la regresión agrupada. Recorrido completo con el paquete exacto y la carga de Luma
  simulada: siete instalaciones, Mansión original, Repartir Exp. y DexNav (`frontier/probes/package/circuit.py`,
  ~35 min automático, medido el 2026-11-13 18:33–19:08 en el carril claude).
- Si la alfa encuentra un fallo, se busca hacia atrás tarea a tarea: cada una deja su commit y los hashes de su build.

Antes (2026-11-11), cada tarea que tocaba el motor hacía además un combate del Palacio, la Arena, el Tubo y la historia.

## Tareas

`tasks.json`: `id`, `title`, `owner` (`claude` o `codex`), `design`, `accept` (criterios), `status`
(`pending` | `in_progress` | `done` | `blocked`), `notes` y `evidence`. Para añadir trabajo, añade una tarea; para
cambiar el orden, muévela en la lista. Una tarea `blocked` se desbloquea respondiendo en `notes` y poniéndola en
`in_progress`.

Codex también tiene la función *goals* (activa en esta versión). El supervisor no la usa: la continuación y el
relevo los hace él.

## Modo paralelo (`auto --parallel`, 2026-11-10)

Cada agente trabaja a la vez en su **carril**:
- un `git worktree` en `work/orch/lanes/<agente>`, rama `lane/<agente>`;
- su propio `work/`, con su laboratorio de Azahar (`work/azahar-lab`) y su puerto de GDB (`work/lab-port`:
  Claude 24690, Codex 24691; el 24689 queda para el checkout principal);
- lo grande y de solo lectura enlazado al checkout principal (`inputs`, `tools`, `baseline`, `dist`, `.venv`, el
  runtime de Azahar, la ROM del laboratorio); se copian los ajustes y partidas del laboratorio y `work/frontier/lab`.

Reglas del carril (van en el mensaje del agente):
- coge sus tareas abiertas; si el otro agente está sin cuota, también las de él (con aviso de relevo);
- no toca `tasks.json` ni el turno: escribe `work/lane-task.json` (`status`, `notes`, `evidence`);
- hace commit en su rama. Tras cada ejecución el supervisor hace `rebase` del carril sobre `main`, avanza `main`
  (solo *fast-forward*), pasa la aceptación en `main` y apunta el estado en `tasks.json`;
- `BITACORA.md` y `reports/frontier.md` se unen sin conflicto (`.gitattributes`, `merge=union`); cualquier otro
  conflicto se aborta y bloquea esa tarea, sin tocar `main`.

Límites: lo que un agente deja sin commit al quedarse sin cuota se queda en su carril; si el otro hereda la tarea, no lo ve (el aviso de relevo lo dice; el brief ya pide commit en cada hito). Dos tareas que toquen lo mismo (el hueco de `code.bin`, `patch.py`, el CRO) chocan al integrar o, peor,
integran sin conflicto pero se pisan en el juego: la aceptación de `main` solo pasa los tests. Repartir en paralelo
tareas que no compartan motor; una regresión en Azahar con lo integrado sigue siendo trabajo de la tarea.

Órdenes:
- `frontier/orch/frontier-orch lanes setup`: crea o completa los carriles (lo hace también `auto --parallel`);
- `frontier/orch/frontier-orch auto --parallel`;
- `frontier/orch/frontier-orch status`: también los carriles y sus commits pendientes de integrar;
- `frontier/orch/frontier-orch lanes remove`: borra los worktrees (antes quita los enlaces; lo compartido no se
  toca) y las ramas ya integradas.

Prueba de los dos laboratorios a la vez: `frontier/orch/lab_smoke.sh` (arranca uno por carril, conecta GDB a cada
puerto, lee un registro de cada uno y comprueba que `reap` de uno no mata al otro).

### Sin parar (`auto --follow`, 2026-11-11)

`frontier/orch/frontier-orch auto --follow` es el modo paralelo sin fin: un carril sin nada que hacer espera (revisa controles y bandeja
cada minuto como máximo (`poll_minutes` puede acortar la espera)) en vez de salir; una tarea bloqueada no para a los demás; una cuota agotada se espera. Sale
solo con `drain`, `stop` o si los dos agentes se quedan sin login.

Cola y orden:
- `owner: "any"`: la coge el primer carril libre. Úsalo para que Claude no se quede parado si Codex tarda.
- `after: ["ID", …]`: la tarea no empieza hasta que esas estén `done`.
- Una tarea en curso la sigue el carril que la empezó; otro solo la hereda si ese agente se queda sin cuota.

Mientras corre (el supervisor tiene el turno; nadie más escribe en `main`):
- `frontier/orch/frontier-orch add tareas.json`: una tarea o `{"tasks": [...]}`; se valida al momento y el
  supervisor la mete en `tasks.json` (con commit) en menos de un minuto. Un fichero inválido va a
  `work/orch/inbox/refused/` y lo dice el registro.
- `frontier/orch/frontier-orch drain`: cada carril termina la tarea que lleva (las ejecuciones que hagan falta), no
  coge otra y el supervisor sale y suelta el turno. Para hacer un checkpoint, revisar o cambiar el orquestador.
- `frontier/orch/frontier-orch stop`: más rápido; termina la ejecución en curso de cada carril y sale.
- `frontier/orch/frontier-orch resume`: cancela un `drain`/`stop` pedido que aún no se ha cumplido.
- `status` muestra `drain`/`stop` pendientes, la bandeja de entrada y, por tarea pendiente, de qué depende.

### Migración y marcha atrás

Lo nuevo es opcional: `auto` sin `--parallel` funciona como antes. Cambios fuera del orquestador, compatibles:
- `.gitignore` sin barra final en los directorios de la raíz (para ignorar también los enlaces de los carriles);
- `scripts/azahar_lab.py`: puerto de GDB desde `ORAS_GDB_PORT` o `work/lab-port` (por defecto 24689) y orden `reap`;
- `faraway/gdbctl.sh` y `faraway/walk.sh`: rutas relativas a su checkout y el mismo puerto;
- `config.json`: `after_run` usa `reap` (solo el laboratorio de su carpeta), Codex escribe en `{git_common}` (el
  `.git` principal, igual que antes en secuencial) y la sección `lanes`.

Marcha atrás: `frontier/orch/frontier-orch lanes remove` y `git revert -m 1 <commit de la fusión de orch-parallel>`.
Si un carril tiene commits sin integrar, `lanes remove` conserva su rama.

### Cola revisada el 2026-11-13

El usuario confirma v0.2 funcional en 3DS y autoriza continuar. F7-CONSOLA-MANSION cerrada.
Se encolan las seis implementaciones F9 y las diez F10, en cadena: modalidades primero,
personalidad después. El modo `--follow` conserva los dos carriles y los relevos por cuota,
pero esta cadena solo permite una tarea a la vez porque comparten motor y construcción.
Las cifras de espacio de los diseños anteriores a F7-CUEVA-LUMA deben medirse de nuevo;
la reserva de Luma no se reutiliza. F10-COTA-CARGA sigue requiriendo decisión del usuario
antes de subir LOAD_BUDGET; la confirmación de v0.2 no valida una carga futura mayor.
