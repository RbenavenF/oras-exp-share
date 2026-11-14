# F9 — Fábrica Individual Libre

## Hito 1: rangos y equivalencias antes de habilitar

Estado: **en curso**. `factory_open.py` define y valida los rangos, pero todavía
ninguna recepción ni draft lo consume. Nivel 50 conserva sus tablas y código.
Azahar y consola de esta tarea: **no probados**. No se ha iniciado laboratorio.

Fuente fijada a pret/pokeemerald `731ad5bfd6e6f265508d0efcca0ba42f9dcf5881`:
`src/battle_factory.c` (`sInitialRentalMonRanges`, `GetFactoryMonId`,
`GenerateInitialRentalMons`, `GetNumPastRentalsRank`),
`include/constants/battle_frontier_mons.h`,
`src/data/battle_frontier/battle_frontier_mons.h` y
`include/constants/pokedex.h`. Se leen los objetos del commit mediante `git show`,
no el árbol de trabajo ni un HEAD mutable. No se convierten las especies de GBA
por resta: el auditor usa los nombres de especie y el enum de Pokédex Nacional.

Reproducción (tras `source scripts/env.sh`):

```
python frontier/probes/modos/factory_reference.py /tmp/frontier-cerebros-pokeemerald
python frontier/modes_audit.py
```

Evidencia: `work/frontier/modos/fabrica/reference.json` contiene los hashes de los
cuatro ficheros fuente y de los cuatro GARC ORAS, rangos extraídos, tabla de
**510 IDs 372–881** con candidatos ORAS por especie y los 48 IDs sin equivalente
en los rangos fuertes elegidos. `fd.load()` exige los hashes del volcado de §7 de
`reports/frontier.md` antes de cotejar los conjuntos.

| Ronda Libre | Fuente Esmeralda | Adaptación ORAS (`maisonpkS`) | Conjuntos |
| --- | --- | --- | --- |
| 1 | 372–467 | 0–20 y 208–382 | 196 |
| 2 | 468–563 | 52–72 y 383–557 | 196 |
| 3 | 564–659 | 104–124 y 558–732 | 196 |
| 4 | 660–755 | 156–176 y 733–907 | 196 |
| 5+ | 372–881 | Unión de las cuatro copias y tabla de legendarios de abajo | 828 |

La fuente repite el último rango en rondas 5–8 y lo mantiene después. La API
`pool` representa esa repetición con un único último rango y tope; `draft_pools`
selecciona la siguiente copia para las primeras 0/1/2/3/4/5 ofertas con contadores
<15/<22/<29/<36/<43/≥43. No debe usarse el índice de rango para los IV: ronda 5
usa IV 15 aunque ya tenga la unión; las rondas 6/7/8+ siguen 21/31/31. La futura
VM debe medirlo al conectar el draft: por ahora solo se prueban los rangos.

## Corrección de 850–881 y selección de legendarios

El diseño llama «legendarios 850–881» a todo el tramo, pero los IDs de la fuente
son **850–859 Dragonite**, **860–869 Tyranitar** y solo **870–881** las variantes
5/6 de las seis primeras especies de la tabla siguiente. Las once especies
legendarias ya aparecen en 756–799; 800–849 añade variantes de especies que ya
están representadas. El auditor recorre también ese intervalo, sin suponer que
sea exclusivamente legendario.

| Especie | Nacional | IDs `maisonpkS` explícitos |
| --- | --- | --- |
| Articuno | 144 | 908, 928, 948, 968 |
| Zapdos | 145 | 909, 929, 949, 969 |
| Moltres | 146 | 910, 930, 950, 970 |
| Raikou | 243 | 911, 931, 951, 971 |
| Entei | 244 | 912, 932, 952, 972 |
| Suicune | 245 | 913, 933, 953, 973 |
| Regirock | 377 | 914, 934, 954, 974 |
| Regice | 378 | 915, 935, 955, 975 |
| Registeel | 379 | 916, 936, 956, 976 |
| Latias | 380 | 922, 942, 962, 982 |
| Latios | 381 | 923, 943, 963, 983 |

Son **44 conjuntos**, de forma base y cuatro movimientos no nulos, comprobados
contra el volcado. No usar 908–987 como bloque: entre ellos están las nueve
especies posteriores excluidas Cobalion 638, Terrakion 639, Virizion 640,
Tornadus 641, Thundurus 642, Heatran 485, Cresselia 488, Landorus 645 y Regigigas
486 (36 conjuntos). No aparecen como especies en el Frente de la fuente fijada.

Dragonite tiene candidatos ORAS 376/551/726/901; Tyranitar,
377/552/727/902. Ya pertenecen a las cuatro copias fuertes: la unión conserva
cada ID una vez. No multiplicar su probabilidad por las diez variantes de
Esmeralda. Cada ID fuente 850–881 figura explícitamente en el JSON con sus
cuatro candidatos medidos. Es una equivalencia **por especie y copia de Mansión**,
no igualdad de movimientos, naturaleza, EV ni objeto entre generaciones; no hay
correspondencia biyectiva para 10 variantes fuente y 4 variantes ORAS.

Se conserva la adaptación fuerte ya entregada, de 196 especies frente a las 96
de Esmeralda. Doce especies fuente no tienen conjunto en estas cuatro copias
fuertes ORAS: Fearow 22, Clefable 36, Golduck 55, Dodrio 85, Hypno 97, Rhydon 112,
Electabuzz 125, Magmar 126, Xatu 178, Misdreavus 200, Dusclops 356 y Glalie 362.
No se sustituyen silenciosamente por evoluciones; los 48 IDs fuente afectados
quedan documentados como excluidos. Las 84 restantes están representadas en
cada copia; la unión final incluye **207 especies ORAS**. Las diferencias de
movimientos y las especies adicionales son las de los rangos fuertes de §7.
Esto no corrige retroactivamente Nivel 50 ni añade legendarios a su rango final.

## Espacio y build exacta de este hito

`work/frontier/modos/fabrica/space-map.json` (`modes_audit.py`):

- code.bin: 2008 bytes en 0x579804–0x579fdc; **36 libres** hasta 0x57a000.
- DllBattle: termina en 0xd7b84; **1148 libres** hasta 0xd8000.
- Cerebros DllField: 0xf0480–0xf0a00; F9 usa 556 bytes hasta 0xf0c2c y tiene
  **980 libres** hasta 0xf1000.
- Reserva Luma **0x579604–0x579804 intacta**. Este hito no escribe ningún motor.

Build completa ejecutada:
`python frontier/overlay.py --out work/frontier/modos/fabrica/build-map`.
Registro `build-map.log`; los 28 archivos y sus hashes completos están en
`build-map-hashes.json`. Script 517 16036 bytes, ZO 16828; compartido 5 22147;
texto ES 637 69544; hook 2008. IPS SHA-256
`0368f52100d49dfe34809ddda710637a58b1055fb8f07b7de0a5337d2a4dbb2d`;
DllField SHA-256 `eb70d036317eedf93cb36b8258c8cd496047cbe0b6e12462a88c46a3d9be2bb1`.
Es la build anterior a conectar Libre de Fábrica; construirla no constituye
aceptación jugable de esta tarea. No se ha instalado en el laboratorio.

## Continuación concreta

1. Reservar en REPARTO líneas nuevas del texto 637 después de 1127 para las 44
   etiquetas de legendarios y, si hace falta, un mensaje propio en 619 después
   de 196. Conservar todos los números de línea de Domo/Tubo/Pirámide/Cerebros.
2. Conectar recepción Individual 50/Libre y CONFIG[1]=0x164 para Libre (100), sin
   selector del equipo real; bancos `modes.bank(1,M)` y contador propio de
   `FACTORY_RENTS[M]`. No reutilizar 16429 como dato persistente: `WORK_STREAK`
   sigue siendo solo el paso temporal a GlobalCall.
3. Conectar pools/promoción/IV al draft, conservando el camino Nivel 50; preparar
   la repetición exacta para Noland. **Atención:** la repetición necesita el
   contador al generar las seis ofertas, no el contador después de cambios
   durante la ronda. Reservar un snapshot persistente si hace falta (candidatos
   libres: `modes_audit.py`), medirlo antes de usarlo. La fuente marca alquiler
   inicial/cambio y lo cuenta tras victoria (`SetBattleFactoryData`,
   `FACTORY_DATA_WIN_STREAK_SWAPS` condicionado por `sPerformedRentalSwap`);
   registrar explícitamente la política adaptada, no inferir +3 de tres elegidos.
4. VM de draft/cambios/cancelación, rango y replay de Noland; evitar especie y
   objeto repetidos también al cambiar. Los rivales ordinarios seguirán siendo
   de Mansión: medir y documentar rango/IV efectivos, además del nivel 100.
5. Build final, suite y aceptación Azahar de novedades requerida en el brief,
   incluidos ronda/PB, recarga y derrota/limpieza. Solo entonces marcar done.

Verificación del hito: `env -u ORCH_LANE python -m pytest -q tests` → **3313 passed,
4 skipped**, 59,57 s (`tests-map-final.log`), con los 135 casos nuevos y el cotejo
contra la fuente local fijada ejecutados. `git diff --check` correcto.
