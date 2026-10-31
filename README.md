# Repartir Exp. equipable para Omega Ruby Repolished

Prototipo local para el volcado y el paquete **Repolished 1.7.6** identificados
en `reports/source-lock.json`. La rutina ARM pasa pruebas con estados de combate
simulados y el reparto se ha validado en cuatro combates reales en Azahar
(`reports/gameplay-validation.json`) y en una 3DS con Luma3DS.

El objeto **216, Repartir Exp.**, pasa al bolsillo Objetos. Los participantes
conservan su experiencia; un portador en reserva recibe la mitad calculada por
el juego, con su redondeo y modificadores. Las demás reservas quedan fuera.
El efecto deja de depender del interruptor global. Los EV se tratan por separado
en [las notas de ingeniería](reports/ingenieria.md).

## Generación

```bash
source scripts/env.sh
python scripts/prepare_baseline.py
python scripts/analyze_assets.py
pytest -q
python scripts/validate_arm.py
python scripts/build_patch.py
python scripts/validate_gameplay.py   # requiere las partidas de work/test-saves
```

Los generadores rechazan destinos existentes. Para una base ya creada:

```bash
python scripts/prepare_baseline.py --verify-only
```

Para comprobar una segunda generación sin sobrescribir:

```bash
python scripts/prepare_baseline.py --output work/otra-base
python scripts/build_patch.py --output work/otro-parche
```

`dist/held-exp-share-v0.4/` contiene el paquete local completo en
`mods/000400000011C400/`, diferencias IPS por archivo en `patches/`, un manifiesto
y `LEEME.txt`. Las diferencias se aplican sobre **Repolished**, no sobre cualquier
ROM. El generador valida SHA-256 y bytes originales; IPS por sí solo no lo hace.
Nada se instala automáticamente.

La entrega en la historia no se modifica: el evento original da el mismo
objeto 216, que ahora va al bolsillo Objetos. v0.3 adapta la descripción
(español e inglés) y la explicación al recibirlo (español). v0.4 muestra
«X ha ganado N Puntos de Experiencia» para el portador al acabar el combate.

Partidas que ya tienen el objeto como objeto clave: convertirlas con
`scripts/save_fixture.py --move-exp-share` (ver `reports/laboratorio.md`). Los archivos de juego, las partidas y los
artefactos derivados quedan excluidos de Git.

Estado y próximos pasos: [reports/estado.md](reports/estado.md).

## Análisis en Ghidra

No hace falta GhidraMCP para el análisis por consola:

```bash
bash scripts/ghidra-headless.sh work/ghidra-projects oras \
  -import analysis/repolished-battle.elf -processor ARM:LE:32:v6 \
  -analysisTimeoutPerFile 180 -scriptPath scripts/ghidra \
  -postScript DumpFunctions.java analysis/decompiled 010324d0 01031d28 004e9f60
```

El ELF es exclusivamente de análisis. Combina el mapa real del ejecutable con
`DllBattle.cro` reubicado en una dirección **sintética** `0x01000000`.
No es una imagen arrancable. La primera pasada global alcanzó el límite de
180 segundos; las funciones relevantes sí se descompilaron. Sobre ese proyecto:

```bash
bash scripts/ghidra-headless.sh work/ghidra-projects oras \
  -process repolished-battle.elf -noanalysis -scriptPath scripts/ghidra \
  -postScript DumpFunctions.java analysis/decompiled 010324d0 01031d28 004d3a88
```
