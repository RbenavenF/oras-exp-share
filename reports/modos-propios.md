# F9 — Individual Libre: Torre, Palacio y Arena

Estado: en curso. Recepciones implementadas; aceptación de laboratorio pendiente.
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
pasiva sobre code.bin: selector, construcción, niveles, resultado, filtro de
naturaleza/PS y divisiones del juicio. Difiere los puntos del filtro/divisor
hasta StartBattle para evitar penalizar el arranque. No escribe RAM.
Los breakpoints en CRO recargados no son fiables en Azahar (BASE); se observan
sus llamadas a code.bin. No declarar reglas observadas si no aparece su traza.

Pendiente: combate Libre real de Palacio y Arena con niveles/reglas medidos;
cierre de ronda/PB, guardar/cargar modalidad y ausencia de duplicación. Consola
no probada. Sin regresión ajena: política agrupada del usuario2026-11-13.
