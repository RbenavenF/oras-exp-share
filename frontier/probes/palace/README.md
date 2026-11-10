# Sondas heredadas del Palacio B

Fuentes de los experimentos de Claude del 2026-11-05, preservadas al relevo de Codex.
Estado y resultados: `reports/frontier.md` §32. No se ejecutan desde la build ni desde los tests.

- `m1.gdb`: vuelca el setup de Individual/Multi al final de su construcción. Solo hay evidencia Individual.
- `m3-direct.gdb`: fuerza tipo IA para cliente 0. Se encontró pantalla negra: leer §32 antes de repetir.
- `m3-hybrid.gdb`: crea objeto IA con flags 7 y desvía solo comandos 3/5/6; conserva la interfaz.

Solo para una copia de la partida bajo `work/`, un laboratorio Azahar aislado y GDB detenido.
`m3-direct.gdb` requiere armar sus breakpoints después de cargar el CRO (los puede sobrescribir la carga).
`m3-hybrid.gdb` utiliza el watchpoint de rearme de la sesión medida. **Sus direcciones de heap son específicas**:
CRO 0x6f3000 y cliente 0 0x820d9ac. No usarlas en otra sesión sin verificarlas primero.
`m1.gdb` escribe un volcado local bajo `work/frontier/palace/` (crear el directorio antes).
Los scripts no conectan ni arrancan el emulador; usar `faraway/gdbctl.sh` y `scripts/azahar_lab.py`.
Parar siempre el laboratorio en el mismo namespace al acabar. No escribir sobre inputs ni la partida original.

El código B sin commit se conserva como propuesta en `reports/diseno/palacio-b-experimental.patch`, sobre
18a464f. Aplicado tal cual el 2026-11-10 tras la decisión del usuario (vía híbrida; `reports/frontier.md` §33).
- `audit_a8.py` / `audit_a8_all.py`: auditoría estática de los lectores de `setup+0xa8` para el bit 30 (§33).
