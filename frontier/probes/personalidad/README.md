# Sondas de F10-PERSONALIDAD-DISENO

Medidas estáticas (sin emulador) de `reports/diseno/personalidad.md`. Salidas en `work/frontier/personalidad/`.

- `survey.sh [GAME]`: mapa de suelo de las 536 zonas (`faraway.Probe floor`), entidades y carga (`WorldTextures`)
  de los donantes candidatos y `floor_fit.txt`. GAME por defecto: `work/frontier/package/build-island/game`
  (build de la isla del paquete; vale cualquier build de `frontier/overlay.py`).
- `floor_fit.py FLOORS [ZONAS…]`: qué zonas tienen suelo en las casillas de la coreografía de la Mansión
  (x19–23, y12–25 y la fila de recepción). Necesario, no suficiente: no ve barreras (reports/frontier.md §37.1).
- `plaza_variants.sh [BASE]`: presupuesto de carga de la plaza para cada variante de exterior (letreros, vallas,
  sustituciones). BASE por defecto: `work/frontier/plaza-exp/base-game` (`python frontier/lab_plaza_base.py`). La
  variante `control` debe dar 2.665.344, el presupuesto de la build actual.
- `SignCheck.java`: si el script de cada zona tiene la rutina de letrero de CTRMap-F5. Uso:

  ```
  source scripts/env.sh; faraway/run.sh Probe GAME WS zones >/dev/null   # compila work/faraway/classes
  CP=tools/CTRMap-F5/build/classes:tools/CTRMap-F5/lib/jogl-all.jar:tools/CTRMap-F5/lib/gluegen-rt.jar
  javac --release 8 -nowarn -cp $CP:work/faraway/classes -d work/frontier/personalidad/classes frontier/probes/personalidad/SignCheck.java
  java -Djava.awt.headless=true -cp work/frontier/personalidad/classes:work/faraway/classes:$CP faraway.SignCheck GAME WS 209 212 517 16
  ```
