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

Laboratorio de la aceptación B (2026-11-10, `reports/frontier.md` §33), copiados de `work/frontier/palace/`
(rutas internas a `work/frontier/palace/…`; copiarlos allí para usarlos):
- `lab-c-lab-start3.sh`: instala `c-build3` y una copia de la partida (`FIXTURE=`), arranca con stub GDB.
- `lab-c-probe2.gdb`: sonda pasiva (marca, flags IA, despacho con el comando leído de la fila, entradas, IsWin);
  `pa['low']=N` pone a 1 PS las N siguientes entradas propias (fixture de RAM, solo laboratorio).
- `lab-drive.sh`: pulsa A solo fuera del combate o en los textos del entrenador (comandos 1/12) y registra el motivo.
- `lab-manual_battle.sh`, `lab-until_battle.sh`, `lab-enter.sh`, `lab-regress-start.sh`, `lab-k.sh`: control manual.

Etapa C (2026-11-11, `reports/frontier.md` §36), con rutas relativas a la raíz del carril o checkout:
- `c2_fixture.py SRC DST NATURALEZA m1,m2,m3,m4`: copia de una partida con el primer Pokémon del equipo con esa
  naturaleza y esos movimientos (PP base); usado: `pa_strong.sav` → `c2-gentle.sav` (Amable, 309/334/86/89).
- `lab-c2-start.sh` (`FIXTURE=…`, `BUILD=…`): instala v0.5 + build y arranca con el stub del puerto del carril.
- `lab-c2-probe.gdb`: sonda pasiva; aprende la base de DllBattle en `palace_ai_flags` (lr − 0x73260) y registra
  `PALACE FILTER` (naturaleza, pct, PS, columna, grupo, huecos usables que quedan), `PALACE MOVE` (movimiento final
  de cada cliente, 0xd78c), `NOFILTER` (otros clientes), `ISWIN`. `pa['hp_pct']=P`: la siguiente entrada propia con
  P % de PS (fixture de RAM). Direcciones de code.bin de la build de §36: recalcular con `patch.assemble()` si cambia.
- `lab-c2-drive.sh` (`RESULTS=N` o `UNTIL=patrón`): A solo fuera del combate y en los textos del entrenador.
- `c2_check_log.py LOG`: comprueba cada `FILTER` contra la tabla de Esmeralda y que el movimiento elegido después
  sea de los que quedaron y del grupo sorteado (o de otro grupo si el sorteado no tenía ninguno usable).
- `lab-c2-k.sh`: pulsaciones y captura.
