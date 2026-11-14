# F9 — Individual Libre: Torre, Palacio y Arena

Estado: terminado. Recepciones y aceptación F9 propios completadas en el carril.
Integración y recorrido completo de alfa corresponden al orquestador.
El corte vertical de Torre BASE sigue siendo evidencia de motor: no se repite.

`frontier/tower.py` ofrece Nivel 50/Libre antes de la inicialización retail del
selector. Solo acepta Individual y fuerza rango Normal. Tras elegir equipo/Caja,
las tres instalaciones llaman al registro nativo ya entregado en BASE, antes de
guardar. ACTIVE=2 distingue inscripción nueva de reanudación; Libre provisional
es CONFIG=0x13c, válido incluso si se cancela el equipo. La selección aceptada
fija L=max(60,máximo inscritos), conservando niveles propios.

Una pausa ofrece Reanudar/Abandonar/No quiero nada antes del selector. No ofrece
cambiar nivel; valida CONFIG 0,50,0x13c–0x164 sin destruir configuraciones
inválidas. Abandonar borra solo la racha del banco activo, conserva récord y
el otro banco. No introduce llamadas a PB. No cambia el motor, bits30/31,
IA del Palacio ni juicio de la Arena. Textos619/191–196 reservados en REPARTO.

Evidencia reproducible, desde el carril y con `source scripts/env.sh`:

- `env -u ORCH_LANE python -m pytest -q tests`: **3090 passed,4 skipped**,78.29s,
  `work/frontier/modos/propios1/tests-release.log`. ORCH_LANE heredado contamina
  nueve pruebas del orquestador en una ejecución anterior; se elimina solo del
  entorno del proceso de pruebas.
- `tests/test_frontier_modes_propios.py`:144 casos VM de recepción, cancelación,
  pausa, bancos, corrupción, fronteras de PB y Cerebros. Constructor de Cerebros
  ampliado a las tres rutas y L60/73/100, activo/inactivo. La selección efectiva,
  mínimo60, nivel100 y Caja siguen cubiertos por la suite BASE.
- `python frontier/overlay.py --out work/frontier/modos/propios1/release`:
  construcción completa, `build-release.log`; ZO de las tres recepciones
  **17136<=17248**. No se alteran los scripts de las otras instalaciones.
- `python frontier/modes_audit.py`: `propios1/audit.json`; code2008 bytes,
  36 libres; Battle788 bytes,1148 libres; Field F9 472 bytes,1064 libres.
  Reserva Luma **0x579604–0x579804 intacta**. Cifras posteriores a F7.
- `build-hashes.json` contiene todos los SHA256 del build. Salidas principales:
  code.ips `0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`,
  DllField `c3ef67de4621865e61f88246c4e286b94fba37cfbdbb8350bdc63a55b5e48fdb`,
  DllBattle `5cde67f65c9692c7b710956689a1ca5e6128d01f22d5a61eca5bb4ec83d51754`,
  CRR `796122ec06b30592ef1632fa277d56b8f0cbae0b333b0f95cfe1c8f88790edcb`,
  a/0/1/3 `778b8bab34755cff73238e2318bb356b5a17949020abbdca4272c65321b33faf`.
  El laboratorio instaló el build `final`: sus zonas329/340/457 son idénticas
  byte a byte a `release` (`target-equivalence.json`); el único archivo distinto
  es a/0/1/3 por eliminar un local sin uso de otras instalaciones antes de release.

Laboratorio: solo carril24691, copias bajo `work/frontier/modos/propios1/`.
`palace.json` y `arena.json` documentan fuente, hashes, posición y works.
Fuente `base3/tower73.sav`, SHA256
`7a8c2cc32aa3d084eac64ef087e8963f97b3640f9474c63afef508b2212cdd72`;
equipo73/55/41. Palacio comienza con pausa LibreL73 y racha6; Arena con
desafío nuevo. No se toca la fuente ni inputs.

`frontier/probes/modos/propios.py palace|arena DIRECTORIO` genera observación
pasiva: selector, construcción, niveles, resultado, filtro de naturaleza/PS
y entrada al juicio. El filtro de Palacio se activa tras StartBattle; el juicio
se arma manualmente con el CRO ya cargado. No escribe RAM.
Los breakpoints plantados antes de cargar/reponer un CRO no son fiables en
Azahar (BASE). Palacio observa sus llamadas a code.bin. Arena verifica primero
la instrucción real de arena_judge ya cargado, planta un breakpoint hardware
y lo retira antes de salir de ese combate; no queda un hook sobre un CRO recargado.

## Laboratorio de Palacio

Build `final` (tres zonas equivalentes a release), nueva shell persistente para
conservar el espacio de PID del laboratorio. `palace-gdb.log` y
`palace-battle.log`: selector rank0/type0, inscritos `[0,1,2]`, niveles propios
**73/55/41**, tres OPEN MAKE a **73**, CONFIG0x149. Start flag **0x40000000**,
trainer53, sin Cerebro. Cuatro llamadas al filtro de Palacio, client0/thinker0,
naturaleza13, PS223/223 y150/223, porcentajes59/85/52/29. Resultado raw1
(victoria),16 pulsaciones del helper `package/battle.py`, `pv_mode=normal`,
sin modificación de RAM ni asistencia de combate. El umbral bajo50% de
naturaleza no se alcanzó en esta pelea; sus dos columnas siguen cubiertas por
las pruebas del motor existente, que no se modifica aquí.

Pausa tras el séptimo: `palace-round7.png` muestra próximo combate8;
`palace-paused7.sav/json`:58 bloques válidos, CONFIG329, ACTIVE1, banco Libre
**6/6→7/7**, Nivel50 **12/20** conservado, PB **3→7** (+4 de primera ronda).
SHA256 guardado `c8f7164b3eb0942ebb64a9e4721003bc70e9917690ac7a24114357172c32719a`.

Recarga real con build release y esa copia (`boot-palace-reload.log`): vuelve
el menú de pausa, sin selección de nivel (`palace-reload-paused.png`). Se
inscriben índices **[1,2,4] =55/41/7** que daríanL60 en un desafío nuevo;
tras registro permanece **CONFIG0x149**, racha/récord7/7, banco50 12/20.
Se acepta guardar, sin comenzar otro combate. `palace-reloaded-gdb.log` y
`palace-reloaded7.sav/json`: PB **7**, sin premio duplicado,58 bloques válidos.
SHA256 `f0803bcbeb8adb5a5308e76c8736b5c86a131dd96fe2029795aa3c1c16686de5`.
Equipo y Cajas tienen hashes idénticos en fuente, inscripción, pausa y recarga:
`e376f1b635055be23d12e0dc18b1d8fbf836c806d6e2fdc40515a80c4da5d54a` y
`4b00b99e63599ba5f9a744f075f66b5e7ef9f068b15987e8d610945d0d8621d8`.

Helpers reproducibles:
`propios.py seed palace|arena SOURCE SHA256 OUTPUT` reproduce las dos copias
iniciales byte a byte (`seed-reproduction.json`, `seed-arena-reproduction.json`,
`cmp` correcto). `propios.py snapshot SOURCE OUTPUT` exporta una copia nueva
con checksums, bancos, PB y hashes de equipo/Cajas. Ambos restringen destino
a work/ y rechazan sobrescritura. Solo se adjuntan metadatos al informe,
ninguna partida ni binario comercial a Git.

Suite posterior:3090 passed,4 skipped,70.12s (`tests-lab-final.log`).
Aceptación final:3090 passed,4 skipped,82.36s (`tests-acceptance.log`). Consola no probada.
Sin regresión ajena: política agrupada del usuario2026-11-13.
La ficha de reglas de la app retail aún habla de reducir a50; es presentación
heredada. Las medidas anteriores comprueban los niveles efectivos en Libre.


## Laboratorio de Arena

Build `release`, copia `arena.sav` reproducida por `seed arena`. Menú nuevo
Nivel50/Libre (`arena-level-menu.png`), Individual Normal; selección efectiva
`[0,1,2]`,73/55/41. `arena-registered.sav/json`:58 bloques válidos,
CONFIG**0x149**,ACTIVE1, banco Libre**0/6**, Nivel50**12/20**,PB3.
SHA256 `c2d7b584fee6e92383075d1cf4646bdd0ce9ab0964a21728541ef7f1781142ff`;
equipo/Cajas con los mismos hashes que Palacio/fuente.

Traza de constructor: rank0/type0, tres OPEN CAP input73/55/41 force0,
tres OPEN MAKE level73, BRAINS START flag**0x80000000**, trainer44, normal,
sin líder Mansión. En la UI aparece Skiploom73 y Metagross73 con223/223PS.
El intento de cambiar a Blaziken vivo da «¡No se puede cambiar a Torchic!»
(apodo del Metagross); `arena-switch-refused.png`.

Observación inicial de PS guardados: works16693/16694=**223/165**. El divisor
absoluto code.bin15ec10 captura muchas llamadas ajenas y ralentiza a1FPS; se
desactiva sin escribir RAM. Se comprueba arena_judge cargado en**0x7caa58**
(base0x6f3000 + símbolo0xd7a58), instrucción**0xe92d40f8**, antes de instalar
su hook hardware. Terremoto contra Skiploom permite alcanzar tres turnos.
Traza exacta: `F9 ARENA JUDGE ENTRY current-entry=193/223,165/165 ages=3/3`.
Metagross cae por el juicio (86% frente100%), aunque conservaba193PS; captura
de su página «Debilitado» en la sesión. Hook retirado inmediatamente después,
antes de que el CRO pueda descargarse; combate continúa con entradas normales.
El helper final reproduce este protocolo mediante `arena_loaded(0x6f3000)`
solo con la UI de combate ya cargada, y `arena_unload()` antes de salir.
No se usa asistencia de combate ni escritura de RAM; `pv_mode=normal`.


Cierre Arena: `arena-battle.log`, derrota natural raw0 tras32 pulsaciones del
helper y dos sustituciones de debilitados. `arena-gdb.log`: ACTIVE16466 pasa
1→0, banco Libre0/6 y Nivel50 12/20 intactos; CONFIG329 conservado.
`arena-loss.sav/json`:58 bloques válidos,PB3 sin premio; SHA256
`44a8a71c5e8592aba69b65a87459b8779fce2344d7fc2b11006aa77cf65a6ad0`.
Los tres inscritos son idénticos byte a byte a antes del combate; todos los
niveles del equipo siguen73/55/41/6/7/6 y Cajas idénticas. El hash del equipo
completo tras perder es `02acc5c2bd195145d9410907282214f764557001c292934e624eaaaab7ea3cc7`:
solo el slot3 no inscrito cambia offsets PK6 0xcc,0xcd,0xce,0xd0 y checksum
(`arena-party-diff.json`). No se atribuye causa a esos metadatos no investigados;
no hay cambios de niveles, experiencia ni de los inscritos.

`gdbctl.sh stop` y `azahar_lab.py reap` ejecutados en la misma shell/PID namespace
que arrancó el laboratorio: `lab-stopped.log` = `F9 LAB REMAINING []` y
session.json ausente. Sin procesos del carril pendientes. Builds exactas y
reserva Luma verificadas arriba; no se modificó motor entre build y aceptación.
Commits: `1e52882` (implementación y VM) y el de cierre de esta evidencia.
