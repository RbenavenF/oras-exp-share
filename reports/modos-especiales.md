# F9 — Libre: Domo, Tubo y Pirámide

Estado: hecho. Implementación, pruebas VM/nativas y aceptación Azahar de las tres rutas completas.
Diseño: `reports/diseno/modos.md` §2–§4. No se añaden IDs: CONFIG/bancos F9,
TEAM Domo y textos619/191–196 ya reservados en REPARTO.

Domo registra M/L después de aceptar los tres inscritos y antes del torneo.
`mode_setrank` construye un descriptor temporal con TEAM: el descriptor vivo
puede contener ya los dos combatientes. El máximo incluye siempre el tercero;
el descriptor vivo y el equipo real no se modifican. Reanudar usa CONFIG guardado,
sin recalcular L; abandonar limpia solo su banco. Sigue la desviación anterior:
se reinscriben tres al reanudar, pero L no cambia. Preview y sets forzados siguen
el mismo recorrido de F8; no se crea un constructor paralelo de Cerebros.

Tubo utiliza la recepción común Individual 50/Libre y el registro F9 existente.
Las salas sin combate incrementan con AddWinCount, con el banco de M y tope9999.
El script compartido consulta CONFIG para numerar salas y elegir el tramo salvaje.
No se alteran los hooks de PS/PP/estados ni niveles: el motor BASE conserva niveles
propios, rival/duro L y salvajes L−4/L−5. Se compactan los dos menús y el reset
posicional, y se elimina el selector retail inalcanzable0x1640–0x17af; el generador
rechaza eliminarlo si aparecen referencias entrantes/publics. Se mantiene L12a0.

Pirámide registra antes de BattleInstWorkDelete, conserva CONFIG junto a la
selección persistente anterior y no registra ni selecciona en plantas/reanudación.
Su contador, récord, derrota/abandono y detector de Brandon resuelven el banco
sin depender de WORK_ROUTE ni de que exista el work de batalla. El contador
satura9999. WORK_SUMMIT sigue evitando repetir el piso contado y el premio;
los símbolos son únicos por instalación. No se añaden bolsa, oscuridad ni salvajes.

Evidencia reproducible con `source scripts/env.sh`, directorio
`work/frontier/modos/especiales1/`:

- `env -u ORCH_LANE python -m pytest -q tests`: **3178 passed,4 skipped**,59.58s,
  `tests-release.log` (primera pasada3160/4, `tests-full.log`, antes de ampliar
  el constructor de Cerebros a las tres rutas).
- `vm.log`:525 passed,19.65s. Incluye recepción, cancelación, pausa, exclusión,
  banco Libre, piso/sala, premios y cima pendiente. Suite nativa de selección:
  `selection.log`,558 passed,2.19s; tercero del Domo/min60/100/duplicados/resume.
  Suite completa añade Cerebros L60/73/100 activos/inactivos, dos del Domo.
  Las pruebas nativas previas cubren niveles salvajes y preservación PS/PP/estado.
- `python frontier/overlay.py --out work/frontier/modos/especiales1/release`:
  build completo correcto, `build.log`, hashes de todos los archivos en
  `build-hashes.json`. Salidas:
  code.ips `0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`;
  DllField `eb70d036317eedf93cb36b8258c8cd496047cbe0b6e12462a88c46a3d9be2bb1`;
  DllBattle `5cde67f65c9692c7b710956689a1ca5e6128d01f22d5a61eca5bb4ec83d51754`;
  CRR `59579a3d34b6658528c433afd27e5bcd82345059b0cd36580398ad562d7e3910`;
  a/0/1/3 `2a81900c983f4ff4bebb6839670d0c22e0382b006310759da64f6e7ac0cdbe6a`.
- `zone-sizes.json`: descompresión de entradas GARC del build, tamaños ZO reales:
  Domo456=16904; Tubo458=17248; Pirámide140=16428,141/142=17060.
  Tubo ocupa exactamente el límite medido17248: no hay margen en ese contenedor.
- `python frontier/modes_audit.py`, `audit.json`: code2008 bytes/36 libres;
  Battle788/1148 libres; Field F9 556/980 libres dentro0xf0a00–0xf1000.
  Luma0x579604–0x579804 intacta. code.ips y DllBattle iguales al build previo.

`frontier/probes/modos/especiales.py` prepara copias nuevas bajo work/ con hash y
checksums verificados; observación pasiva por instalación y exportación de copias.
Fuente inicial `base3/tower73.sav`, SHA256
`7a8c2cc32aa3d084eac64ef087e8963f97b3640f9474c63afef508b2212cdd72`,
equipo73/55/41. No cambia fuente, inputs ni partida original.

Azahar, Pirámide (mismo release y 28 hashes instalados comprobados):

- `pyramid-gdb.log`: inscripción real 0/1/2, CONFIG=0x149 (Individual Libre L73)
  antes de destruir el work. En las tres peleas de planta 1, descriptor retail
  vacío reconstruido con la selección persistida, CAP73/55/41 force0 y tres
  MAKE73. `pyramid-battle{,2,3}.log`: victorias raw1 con36/18/23 pulsaciones,
  modo normal, sin asistencia ni escrituras RAM.
- `pyramid-registered.json`: 58 bloques válidos, banco antiguo12/20 y Libre0/6,
  PB3. `pyramid-floor2.json`: zona142, ACTIVE2, Libre1/6, antiguo12/20, PB3,
  CONFIG329 y selección0/1/2 conservadas, BEATEN0/SUMMIT0. Cambio natural tras
  ganar los tres entrenadores; no se usó la copia de planta ya despejada.
  Save SHA256 `edfbbcd75b5697fd1e9a70ec7e6eb44ef4ea271e0e526f26428fdf8c9151f805`.
- `pyramid-floor2.png`, `pyramid-reloaded.png`, `pyramid-reloaded-gdb.log`:
  reinicio completo del emulador cargando esa copia, sin selector por planta.
  El primer combate de planta2 vuelve a construir73/55/41 y rivales73 con
  CONFIG149; se detuvo después de construir, no se declara victoria adicional.
- Equipo completo y Cajas idénticos a la fuente, byte a byte, antes del primer
  combate y al guardar planta2 (SHA256 equipo
  e376f1b635055be23d12e0dc18b1d8fbf836c806d6e2fdc40515a80c4da5d54a;
  Cajas4b00b99e63599ba5f9a744f075f66b5e7ef9f068b15987e8d610945d0d8621d8).
- Nueva suite completa `tests-lab.log`:3178 passed,4 skipped,78.01s.

Pendiente Azahar: Domo combate Libre y cierre torneo; Tubo PS/PP/estado tras
recálculo y salvaje a nivel correcto; medir bancos/PB y equipo real de ambos.
Regresión agrupada2026-11-13: solo lo nuevo/movido; otras instalaciones e historia
quedan para el recorrido completo alfa. Consola no probada.

Azahar, Tubo (mismo release, `especiales1/`):

- `pike-battle1.log`, `pike-gdb.log`: victoria normal raw1 tras43 pulsaciones;
  CAP73/55/41 force0, salvaje Seviper69 = L73−4. La sonda fuerza únicamente
  el segundo de reloj para escoger una sala salvaje; no escribe resultados,
  works ni Pokémon en RAM. `seconds.py` predice la sala a partir del banco Libre.
- Pausa real y guardado `pike-paused.sav/json`, SHA256
  78769eeb474914d26913fa055166729e3b0809366fc3520d8b072aa5ec8d134b:
  CONFIG329, ACTIVE1, Libre1/6, antiguo12/20, PB3. PP del primero9/10/15/30
  tras gastar un Puño Meteoro; los demás conservan sus PP. PS completos, estados0.
- `especiales.py carry` crea otra copia validada, exclusivamente seis works
  PS101/77/42 y estados1/4/5; conserva esos PP obtenidos en combate. Es una
  fixture explícita para medir restauración, no daño ni estados sufridos de forma
  natural. `pike-carry.sav` SHA256
  4554f936cec0791bbd3d1410052fa5232fe4da8a4e208567bf89d151b2da9935.
- Recarga y reanudación conservan L73 y Libre1/6. `pike-carry-gdb.log` mide
  CAP73/55/41, restauración de PS101/77/42, estados1/4/5 y los cuatro PP de cada
  copia después del recálculo. Milotic salvaje69; `pike-carry-pp.png` muestra
  Milotic69, Metagross73 con101/223 PS, paralizado y Puño Meteoro9/10 PP.
  Este segundo combate se detuvo tras construir/mostrar el primer turno.
- `pike-carry-registered.sav/json`, SHA256
  799cc9f3b9bd3718bac9ff81d6c821f10de99517a3f982a80b80b8c86f35945f:
  58 bloques válidos, bancos y PB anteriores intactos, equipo y Cajas byte a byte
  idénticos a la fuente, también en la pausa anterior; hashes iguales a Pirámide.
- Helper: reloj de prueba se desactiva tras consumir su cola, sin breakpoint
  permanente por fotograma; observación pasiva de restauración PS/estado.
  `tests-final.log`: suite completa3178 passed,4 skipped,62.88s; py_compile verde.

En el hito anterior quedaban pendientes la aceptación Azahar del Domo y el cierre del lab.

Azahar, Domo, relevo del 2026-11-14 (mismo release):

- Revisión de relevo: `git status --short` y `git diff` vacíos; HEAD92c8283.
  No había código a medias. Había copias locales no versionadas de una preparación
  posterior al commit; se auditó `dome-ready.sav`, SHA256
  `7ff025e04e025cf293d8096af40fd19de6109f96c83362b84bc8279f5e84c7fb`:
  58 bloques válidos, zona456, bancos50=12/20 y Libre0/6, PB0, equipo y Cajas
  idénticos a tower73.sav (`dome-ready-audit.json`). Su preparación anterior no
  quedó registrada: no se atribuyen a esta ejecución los pasos que la crearon.
- `installed-relevo.json`: 28 archivos instalados cotejados con build-hashes.json,
  cero discrepancias. No se reconstruye ni modifica la build ba0580a.
- `dome-gdb-part1.log`, `dome-preview1.png`, `dome-forced1.json`: inscripción
  real en orden1/2/0 (niveles55/41/73); se eligen1/2 para la primera pelea.
  CAP55/41 sin ajuste y dos MAKE73, CONFIG149. Así el máximo procede del
  tercero inscrito que no combate. Preview Bronzor/Omanyte/Chespin; works
  RIVAL101/118/97 y FORCED118/101; rivales en pantalla Omanyte73 y Bronzor73.
- `dome-battle1.log`: victoria natural raw1,41 pulsaciones; el conductor manejó
  un reemplazo tras KO. Segunda ronda selecciona0/1 (73/55); preview
  Honedge/Grimer/Bunnelby (`dome-preview2.png`), MAKE679/88 a73. Victoria
  natural raw1 tras33 pulsaciones, `dome-battle2.log`. Sin asistencia ni
  escrituras RAM; la sonda observa construcción, selección y resultados.
- `dome-paused2.sav/json/png`: pausa real tras dos victorias y guardado manual;
  Libre2/6, antiguo12/20, CONFIG329, ACTIVE1, ruta0, PB0 (todavía sin torneo).
  SHA256 `dbb32d4e14a8235d4d839d193921e09bec84e0e38728aedded1d58091c21e205`.
  Equipo completo y Cajas idénticos a la fuente. El helper exporta ahora también
  TEAM/RIVAL/FIGHT/FORCED y observa cantidades/bancos por pelea.
- `tests-relevo.log`: primera ejecución con ORCH_LANE heredado falla9 pruebas del
  orquestador (3169 passed,4 skipped); misma causa ambiental ya evitada en hitos
  anteriores. `env -u ORCH_LANE python -m pytest -q tests` pasa3178/4 en61.93s
  (`tests-relevo-clean.log`). Tras ampliar la sonda, suite3178/4 en62.92s
  (`tests-dome-evidence.log`); `py_compile` y `git diff --check` correctos.
- `dome-resume-menu.png`: recarga completa de dome-paused2.sav, aviso de
  modalidad/nivel conservados y opción Reanudar. Se reinscriben0/1/2 (desviación
  ya descrita), sin recalcular CONFIG149. `dome-gdb-part2.log` muestra banco
  Libre2/6 antes de ronda3, tres inscritos0/1/2 y DOME COUNT2. CAP73/55,
  MAKE188/60 a73 (Skiploom/Poliwag), victoria natural raw1 tras26 pulsaciones
  (`dome-battle3.log`). El primer intento del conductor en esta fase se interrumpió
  en el selector por repetir un slot; no constituye combate ni victoria.
- Final: `dome-preview4.png`, Baltoy/Ledyba/Pineco. FORCED103/94,
  MAKE165/204 a73 (Ledyba/Pineco); CAP55/41, DOME COUNT2, Libre3/6,
  antiguo12/20 y CONFIG149. No se nivela al tercero ni se cambia L entre rondas.
- `dome-battle4.log`: victoria natural raw1 tras32 pulsaciones. `dome-prize.png`
  concede1 PB al cerrar las cuatro rondas; siguiente combate5. Pausa posterior
  y guardado `dome-champion.sav/json/png`, SHA256
  `22315db63803511a2fea7f3348ee462781dd0ccb7e931b611bce5ee87bffdb58`:
  58 bloques válidos, zona456, Libre4/6, antiguo12/20, PB1, CONFIG329,
  ACTIVE1, ruta0, TEAM0/1/2. Transitorios de combate limpios; la pausa no concede
  otro PB. `dome-champion-audit.json`: equipo completo y Cajas byte a byte
  iguales a tower73.sav, mismos hashes que las otras dos instalaciones.
- `lab-closed.json`: `faraway/gdbctl.sh stop`, `python scripts/azahar_lab.py reap`,
  procesos propios vacíos, gdbstub desactivado; D-Bus privado terminado. Solo se
  usó el laboratorio del carril, puerto24691. No consola ni recorrido alfa;
  no regresiones de otras instalaciones conforme a usuario2026-11-13.

Aceptación F9 completada: VM y límites/premios/jefes cubiertos por la suite;
Azahar Pirámide (combates, piso y recarga), Tubo (combate, salvaje y arrastre),
Domo (tercero máximo, preview, dos combatientes, cuatro victorias y pausa/recarga).
Build exacto ba0580a sin cambios; las sondas añadidas no forman parte del parche.
