# F9 — Libre: Domo, Tubo y Pirámide

Estado: en curso. Implementación y pruebas VM/nativas listas; aceptación Azahar pendiente.
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

Pendiente Azahar: un combate Libre por instalación; cerrar torneo Domo; Tubo
PS/PP/estado tras recálculo y salvaje a nivel correcto; Pirámide cambio de piso y
recarga sin reinscribir, medir bancos/PB/niveles y equipo real. No probado aún.
Regresión agrupada2026-11-13: solo lo nuevo/movido; otras instalaciones e historia
quedan para el recorrido completo alfa. Consola no probada.
