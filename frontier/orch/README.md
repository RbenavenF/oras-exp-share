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

## Tareas

`tasks.json`: `id`, `title`, `owner` (`claude` o `codex`), `design`, `accept` (criterios), `status`
(`pending` | `in_progress` | `done` | `blocked`), `notes` y `evidence`. Para añadir trabajo, añade una tarea; para
cambiar el orden, muévela en la lista. Una tarea `blocked` se desbloquea respondiendo en `notes` y poniéndola en
`in_progress`.

Codex también tiene la función *goals* (activa en esta versión). El supervisor no la usa: la continuación y el
relevo los hace él.
