# Cerebros del Frente y símbolos — F8 (2026-11-11)

Diseño, sin implementación ni laboratorio. Alcance inicial: las siete instalaciones
actuales, Individual Nivel 50. Los nombres Noland, Anabel, Tucker, Spenser, Greta,
Lucy y Brandon identifican los personajes de Esmeralda; los recursos visuales serán
sustitutos de ORAS. No se han probado estos combates en ORAS ni en consola.

## 1. Fuente fijada y reglas de aparición

Fuente primaria: **pret/pokeemerald `731ad5bfd6e6f265508d0efcca0ba42f9dcf5881`**,
la revisión abreviada `731ad5bf` de PLAN. Lectura del checkout separado en `/tmp`,
no de una rama móvil. Referencias con commit:

- [frontier_util.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/frontier_util.c):
  `sFrontierBrainStreakAppearances` (86), `sFrontierBrainsMons` (97),
  `sFrontierBrainTrainerIds` (719), `GetFrontierBrainStatus` (1656),
  `GetCurrentFacilityWinStreak` (1804), `GiveFacilitySymbol` (1918),
  `CreateFrontierBrainPokemon` (2497), `GetFronterBrainSymbol` (2587).
- [battle_factory.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/battle_factory.c):
  `sFixedIVTable`, `FillFactoryBrainParty` (759), `GetFactoryMonId`,
  `GetAiScriptsInBattleFactory`. La tabla fija de `frontier_util.c` para FACTORY
  **no es el equipo de Noland**: lo genera `FillFactoryBrainParty`.
- [battle_dome.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/battle_dome.c):
  inserción del Cerebro en el cuadro (2478), `GetDomeTrainerSelectedMons`;
  [BattleDomeBattleRoom/scripts.inc](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/data/maps/BattleFrontier_BattleDomeBattleRoom/scripts.inc).
- [battle_pike.c](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/src/battle_pike.c):
  `SetHintedRoom`, `GetPikeQueenFightType` (1501), `HealSomeMonsBeforePikeQueen`;
  [BattlePyramidTop/scripts.inc](https://github.com/pret/pokeemerald/blob/731ad5bfd6e6f265508d0efcca0ba42f9dcf5881/data/maps/BattleFrontier_BattlePyramidTop/scripts.inc):
  Brandon se combate en la cima, tras contar los pisos, no como un entrenador ordinario.

La tabla siguiente usa **ordinales visibles**, empezando por 1. `S` es el work
de racha ORAS antes de resolver la unidad siguiente. Las conversiones son decisiones
de adaptación a los scripts actuales, contrastadas por lectura de `frontier/dome.py`,
`pike.py`, `pyramid.py`, `tower.py` y REPARTO, no ejecución de estos jefes.

| Instalación / Cerebro | Símbolo | Plata | Oro | Tras ambos símbolos | Disparador en ORAS |
| --- | --- | --- | --- | --- | --- |
| Fábrica / Noland | Conocimiento (Knowledge) | combate 21 | combate 42 | 21, 42, 63, 84… | S=20 / 41; siguiente combate |
| Torre / Anabel | Habilidad (Ability) | combate 35 | combate 70 | 35, 70, 105, 140… | S=34 / 69; siguiente combate |
| Palacio / Spenser | Ánimo (Spirits) | combate 21 | combate 42 | 21, 42, 63, 84… | S=20 / 41; siguiente combate |
| Arena / Greta | Agallas (Guts) | combate 28 | combate 56 | 28, 56, 84, 112… | S=27 / 55; siguiente combate |
| Domo / Tucker | Táctica (Tactics) | final del torneo 5 (combate 20) | final del torneo 10 (combate 40) | finales de 5, 10, 15, 20… | S=19 / 39; solo S%4=3 |
| Tubo / Lucy | Suerte (Luck) | sala 28 | sala 140 | salas 28, 140, 196, 252… | S=27 / 139; sustituye sorteo de esa sala |
| Pirámide / Brandon | Bravura (Brave) | cima tras piso 21 (ascensión 3) | cima tras piso 70 (ascensión 10) | pisos 21, 70, 105, 140… | tras contar piso: S=21 / 70; antes de PB y retorno |

Los nombres españoles de símbolos de esta tabla son la redacción propuesta para
ORAS, no una extracción de la traducción de Esmeralda. Los umbrales sí están fijados.
La fila DOME de la fuente `{4,9,5,0}` usa torneos ya ganados, antes del torneo que
contiene la final; no significa combates 4 y 9. PYRAMID `{21,70,35,0}` consulta pisos
ya completados. PIKE `{28,140,56,1}` tiene además su consulta anticipada `nextRoom`:
la implementación no debe sumar dos veces el avance de sala.

Regla común de la fuente: con cero símbolos solo aparece en plata; con uno solo
en oro; con dos reaparece en el umbral de plata con equipo de plata y en el de oro
y sus repeticiones con equipo de oro. Tener plata y reiniciar la racha **no** da
otra pelea de plata. Las modalidades que admiten jefes son Individual; Doble y
Libre quedan para F9, sin duplicar los símbolos por modalidad.

## 2. Equipos: contrato de datos

El anexo §7 contiene los 36 conjuntos fijos de los otros seis Cerebros: especie,
objeto, naturaleza, IV, EV y cuatro movimientos. Se mantienen los identificadores
simbólicos ingleses de pokeemerald para evitar traducciones ambiguas. EV en orden
**PS, Ataque, Defensa, Velocidad, Ataque Especial, Defensa Especial** (orden de
`struct FrontierBrainMon`, no el orden de algunas interfaces de ORAS). Nivel 50 en
esta entrega. En Esmeralda `SetFacilityPtrsGetLevel()` determina el nivel del modo;
no extrapolar Nivel Libre sin F9.

Noland: tres Pokémon aleatorios de los rangos de alquiler de la ronda, no un trío
fijo ni el trío Metang/Skarmory/Aggron de la tabla no usada. A Nivel 50, plata usa
la ronda 3 (`challengeNum=2`), IV **15** (`GetFactoryMonFixedIV(4,FALSE)`); oro ronda
6 (`challengeNum=5`), IV **31**. La fuente excluye Unown, conjuntos fuera del límite
de Nivel 50, los **IDs de conjunto** de los seis alquileres guardados, especies
repetidas dentro del rival y objetos repetidos salvo NONE. No confundir excluir
conjuntos con excluir las especies de los seis. Usa naturaleza/movimientos/EV del
conjunto, convierte Return en Frustration y amistad 0; IA completa de la Fábrica.
Los rangos equivalentes ORAS ya figuran en PLAN §1 y `frontier/data.py`:
plata, nivel de alquiler de ronda 3; oro, ronda 6. Adaptación explícita: conjuntos
de Mansión equivalentes, no una reproducción de todos los conjuntos de Esmeralda.
La Fábrica actual aún deja el rival a la Mansión: sustituirlo es trabajo de Noland,
no afirmar que ya está resuelto.

En el Domo, Tucker presenta tres y combate con **dos**. Reutilizar vista previa
y elección 2 de 3 existentes; implementar selección rival según el equipo del
jugador contrastando `GetDomeTrainerSelectedMons`, o documentar expresamente la
primera aproximación aleatoria (la actual). No ejecutar un 3 contra 2 ni generar
un trío distinto después de enseñar la ficha.

Los EV del anexo no caben fielmente en la máscara de seis bits de `Maison6.Pokemon`
(reparte EV por estadísticas marcadas). BASE debe medir un escritor de EV explícitos
en el constructor de la **copia rival**, fijar IV/naturaleza/amistad, recalcular y
comprobar los seis valores; no sustituirlos silenciosamente por 252/252/6. ORAS usa
su división físico/especial, habilidades y balance de sexta generación: se conservan
los movimientos de la fuente, aunque su efecto táctico cambie (p. ej. los puños de
Alakazam). Habilidades: normales de ORAS, sin oculta, elección definida/reproducible
en BASE; la equivalencia exacta de personalidad/habilidad de GBA no está probada.
Sin megas ni equipamiento nuevo. Para Return, amistad 255 como
`CreateFrontierBrainPokemon`; no confundirlo con Noland.

## 3. Infraestructura común ORAS (F8-CEREBROS-BASE)

Hechos heredados de `reports/frontier.md` §1–§4: `SetTrainer(tipo)` elige por racha
en `code.bin` 0x1e3aac, carga la ficha con 0x1e54a0 y guarda ID con 0x1e4a14;
**su argumento es tipo de combate, no un ID de entrenador**. `work+0x001` es el
indicador de jefe de la Mansión. `IsBoss` pasa por 0x1e5674. En el script retail,
victoria → `AddWinCount` (0x1f60) → `IsBoss` (0x205c) → `BattleHouse_SetRibbon`,
diario y ruta especial (0x264c); derrota → `ClearWinCount` (0x2210).

Diseño preferido, a verificar en BASE:

1. Un módulo común `frontier/brains.py` con tablas de umbrales/equipos y generación
   de rutinas Pawn; un pequeño proveedor nativo solo para identidad/equipo rival.
   Calcular elegibilidad antes de `SetTrainer`, según ruta, racha y símbolos, y
   repetir el cálculo al reanudar. Las siete rutas ordinarias deben seguir iguales.
2. Interceptar selección/carga de rival **solo con ruta 1–7 y estado de Cerebro**.
   Medir cómo suministrar ficha, nombre, clase y modelo antes de la colocación de
   0x2b98 y presentación 0x4338. Reutilizar `SetTrainer` para vida útil del trabajo,
   sin sobreescribir entradas retail de `maisontr` que también usa la Mansión.
   El precedente `rival_hook`/`dome_rival` fuerza sets, pero todavía no resuelve
   el nombre, la clase ni EV explícitos. Estos son puertas de aceptación de BASE.
3. En rutas del Frente, sustituir la decisión y salida especial del jefe retail
   por las del Cerebro. No basta hacer que `IsBoss` sea verdadero: provocaría
   cinta/diario/flujo de la líder de Mansión y omitiría o duplicaría PB. Suprimir
   también jefes retail accidentales (p. ej. combate 20), incluida la selección
   nativa, **solo** en rutas del Frente. Ruta 0 conserva Mansión, cintas y líderes.
4. Al ganar, añadir una única victoria/unidad según instalación, conceder el
   símbolo indicado antes del siguiente guardado, y PB de ronda más **10** por
   Cerebro (precedente `data.BRAIN_BONUS` y tabla de PB de Esmeralda). No añadir PB
   desde la rama retail además de esta. Guardar símbolos en la misma transacción
   lógica que racha/PB: tras cargar no repetir premio; sin guardar, todo vuelve
   al guardado anterior. Revancha: conserva oro y otorga el bonus una vez por victoria.
5. Derrota/empate/abandono: limpieza habitual de desafío y racha, conservar récord
   y símbolos anteriores; limpiar el estado temporal del jefe, sets forzados,
   indicador nativo de jefe y ruta al salir. La pausa conserva la elegibilidad,
   nunca se interpreta como victoria. Ningún préstamo altera equipo/cajas reales.
6. Textos por generador en **texto 637** (historia): intro, plata/oro, victoria,
   derrota, premio y consulta. Reutilizar `GlobalCall`/texto del script 5 y helpers
   de cada zona; no llamar nativas exclusivas de Mansión desde el compartido (§11).
   Reservar casos y líneas con el integrador: 9771–9777 ya tienen uso, no asignar
   9778/9779 sin comprobar el corpus integrado. Índices derivados por composición,
   nunca copiar el final histórico 1071 de REPARTO: Tubo/Pirámide ya lo desplazaron.

Primera instalación de prueba: Torre, Anabel plata, desde racha 34. BASE entrega
esa ruta vertical (identidad, equipo exacto, premio, derrota, guardado) y la supresión
segura del jefe retail para las siete. F8-CEREBRO-TORRE completa oro/revanchas/textos;
no duplica esa primera implementación ni obliga a repetir su prueba de plata.

## 4. Persistencia, presentación y reservas propuestas

`frontier/ids.py` ejecutado sobre baseline: **1157 scripts, 147 ficheros de código**;
candidatos libres incluyen 16729–16731 y 16733–16735, 16738–16739. Evidencia local
`work/frontier/cerebros/ids.txt`. El escáner no resta reservas de nuestros mods y no
detecta todos los índices calculados: cruzar REPARTO y repetir en BASE. No usar
16410–16414: están abandonados porque el juego los borra (§25).

Propuesta **sin asignar todavía** (REPARTO permanece intacto por el brief del carril):

| Work candidato | Uso propuesto | Formato |
| --- | --- | --- |
| 16729 | símbolos permanentes | u16, 2 bits por ruta 1–7: desplazamiento `2*(ruta-1)` |
| 16730 | Cerebro pendiente del desafío | ruta + variante plata/oro + premio pendiente; codificación final en BASE |
| 16731 | control del avance de cima Pirámide | hito pendiente/ya resuelto, persistente durante pausa |

Cada par de símbolos: 0 ninguno, 1 plata, 3 plata+oro; 2 inválido, normalizar a 3
si se detecta, sin volver a pagar PB. Bits 14–15 reservados a 0. Espeja los dos
flags por instalación de `GiveFacilitySymbol`, con un único work de 14 bits en vez
de catorce flags sin auditar. No borrar 16729 al retirarse, perder, salir o iniciar
otro desafío. No reutilizar el work de activo ni el de récord. Para Noland, guardar
semilla o selección rival estable con mecanismo propio existente si la pausa puede
ocurrir tras el sorteo: pedir más works en BASE si hace falta. Estos números son
candidatos, **solo se convierten en asignación al registrarlos en REPARTO antes de usarlos**.

Presentación inicial: opción «Símbolos» en la **recepcionista de cada instalación**,
con nombre de instalación y «Sin símbolo / Plata / Oro»; BASE aporta tabla/consulta,
cada tarea conecta su menú sin iniciar el desafío ni cambiar WORK_ROUTE. Oro
significa que posee ambos. Puede consultarse con otra instalación pausada. Evita
un NPC nuevo en la plaza y un cambio de isla. Cartel global/estuche gráfico y
récords son trabajo posterior; no prometer iconos en la ficha del entrenador.

Sustitutos visuales propuestos (decisión de diseño, aspecto y correspondencia
modelo/clase **no probados**). Usar recursos existentes, sin crear modelos de los
Cerebros. Los modelos de campo 263/298/277 están en el registro donante 517 y en
`pyramid.TRAINER_NPCS`; no se ha verificado aquí qué apariencia/sexo tienen. Son
fallbacks concretos; en BASE resolver un donante temático y su registro completo
si no encajan, manteniendo un sustituto explícito en el informe de cada tarea.

| Cerebro | Modelo de campo fallback | Clase de combate ORAS propuesta | Aspecto buscado |
| --- | --- | --- | --- |
| Noland | 263 | 30 Científico | varón técnico |
| Anabel | 298 | 9 Entrenadora Guay | entrenadora de cabello claro |
| Tucker | 277 | 10 Entrenador Guay | varón de presentación vistosa |
| Spenser | 263 | 31 Médium | anciano; donante temático por verificar |
| Greta | 298 | 63 Luchadora | luchadora |
| Lucy | 277 | 13 Bruja | entrenadora de pelo oscuro |
| Brandon | 263 | 96 Montañero | explorador |

IDs/nombres de clase comprobados por lectura de **gametext ES `a/0/7/7`, entrada 21**
(`TextReference.GameText_AO` de pk3DS). Son clases existentes; no cambiar su texto
global a «Cerebro» porque afectaría a entrenadores de historia. Mostrar «Cerebro
del Frente: Anabel», etc., en el diálogo específico. Modelo de **combate**: usar el
que ORAS vincula a la clase propuesta en `a/0/3/7`; su ID interno/compatibilidad
con la Mansión queda por medir en BASE, no confundirlo con el modelo de campo ni
con un ID de `maisontr`. El nombre de combate debe ser el del Cerebro mediante
ficha privada o sustitución acotada, no un nombre aleatorio de la Mansión.

## 5. Adaptadores por instalación

| Instalación (ruta, zona) | Racha / activo / récord | Trabajo propio, además de datos/textos/modelo |
| --- | --- | --- |
| Fábrica (1, 213) | 16437 / 16489 / 16439 | Noland aleatorio según §2; IV rival independiente del IV de alquiler del jugador; registrar rival en 16433–16435 sin romper cambio; no ofrecer cambio al cerrar ronda; +10 PB |
| Torre (2, 329) | 16441 / 16442 / 16443 | Anabel 35/70; equipo propio; BASE demuestra plata, tarea propia completa oro y repeticiones |
| Palacio (3, 340) | 16461 / 16462 / 16463 | Spenser conserva bits y filtro de naturaleza del Palacio C; no abrir órdenes manuales; no ampliar alcance a corregir IA rival por naturaleza |
| Arena (4, 457) | 16465 / 16466 / 16467 | Greta con juicio por Cuerpo y prohibición de cambiar vigentes; el jefe no activa un combate ordinario sin reglas; Mente/Técnica siguen pendientes |
| Domo (5, 456) | 16473 / 16474 / 16475 | Tucker solo final, S%4=3; fijar el trío antes de preview; alimentar DOME_FORCED con dos de él, conservando elección del jugador y torneo; umbrales 19/39, no 4/9 |
| Tubo (6, 458) | 16477 / 16478 / 16479 | Lucy reemplaza sorteo final de sala; PIKE_WILD=0, tres rivales, rango normal, conservar PS/PP/estado de v2; resolver una sola sala tras ganar, no una victoria más una sala extra |
| Pirámide (7, 140/141/142) | 16481 / 16482 / 16483 | Tras vencer los entrenadores y contar el piso 21/70, parar antes de PB/salida; cima lógica en sala actual con NPC/interacción, sin zona nueva; combate de Brandon no incrementa pisos; hito persistente evita saltarlo o cobrarlo dos veces |

Pirámide necesita separar «piso completado» de «ascensión cerrada»: hoy
`stairs_routine` cuenta piso, limpia vencidos, da PB y vuelve al vestíbulo sin
combate intermedio. Guardar estado pendiente antes de Brandon; al perder aplicar
`pyramid` limpieza y conservar símbolo anterior; al ganar cerrar PB/activo una vez.
La conservación de PS de Pirámide no está implementada: F8 no la promete.

Tubo no debe curar todo silenciosamente ante Lucy. Esmeralda tiene curación
específica previa (`HealSomeMonsBeforePikeQueen`), que requiere adaptar su selección
a la recepción actual sin puertas físicas. Primera implementación: conservar el
estado v2 actual al entrar a Lucy y documentar esa desviación; curación exacta de
Esmeralda queda fuera. No convertir Lucy en sala dura o salvaje de un Pokémon.

## 6. Riesgos, secuencia, pruebas y estimación

**Espacio**: los «~600 bytes» son la foto de §33 (620 libres). Medición estática de
esta tarea con `patch.assemble()` sobre esta rama: **2544/2556 bytes**, fin
**0x579ff4**, quedan **12 bytes** hasta 0x57a000 (coincide con §36). No cabe un
servicio de Cerebros ahí. La cueva del Palacio C en DllBattle tiene 1944 bytes
libres según REPARTO/§36, pero pertenece al CRO de batalla y su vida útil no prueba
que sirva durante `SetTrainer` de campo. No usarla sin verificar carga/importaciones.

Preferencia: decisiones, persistencia y tablas en Pawn/datos; código nativo mínimo
en un **nuevo espacio de DllField o code.bin medido y reservado**. BASE empieza con
auditoría estática de hueco, relocaciones, bytes de entrada, presupuesto de código
y vida útil, antes de elegir sitio. Alternativa: reorganizar ganchos existentes
para recuperar espacio, con el coste de regresión de motor. Ampliar exheader sigue
sin probar. Falta de hueco es riesgo técnico que BASE debe resolver o documentar
con medidas; no autoriza sobrescribir código ni afirmar un bloqueo anticipado.

Otros riesgos: clase/modelo/nombre no son sinónimos; recargar trabajo de Mansión
entre mapas; coincidencia de jefe retail en 20; límites ZO por zona **17248 bytes**;
texto compartido 637; bucle de rechazo infinito al forzar especies/objetos
duplicados; diferencias de EV/generación; off-by-one en Domo/Pirámide/Tubo;
dos carriles reservando los mismos IDs; campos temporales de RAM no guardados.
BASE asigna IDs y líneas en REPARTO, y define un único punto de extensión para que
las tareas posteriores toquen sus módulos propios. No reservar conjuntos 217–222
de maisonpkN: ya son los salvajes del Tubo (`patch.py`). Ni editar clases/listas
globales usadas por la Mansión. Generadores con hashes y bytes previos verificados.

Secuencia: BASE (incluye Anabel plata) → siete adaptadores independientes. Los
IDs ya están en `tasks.json` por la cola anterior. `propuestas/cerebros.json` es
la especificación completa para una cola vacía o para reconciliar esos criterios,
**no se debe ejecutar add sobre IDs existentes**: `check_task` lo rechaza por
duplicados. Las tareas vigentes remiten a este diseño y a sus propuestas, así
que no hace falta modificarlas desde este carril. Si el integrador reconstruye la
cola, añadir una sola vez las ocho propuestas; no ejecutar ambas colas.

Pruebas de implementación exigidas: VM para elegibilidad (S-1/S/S+1, 0/1/2
símbolos, repetición, rutas 0–7), derrota/pausa/retirada, bonus y persistencia sin
premios duplicados; equipos y EV/IV/movimientos exactos; Unicorn de cualquier
gancho nuevo y ruta retail inactiva; tamaños/round-trip/textos e IDs. Suite completa
`python -m pytest -q tests` en cada hito. En Azahar, jefe plata ganado y oro o
derrota en cada instalación; BASE ya cubre plata/derrota Torre, y TORRE cubre oro.
Fijar fixtures justo antes del umbral, leer identidad/equipo real antes de ayudar
la victoria y marcar ayudas. Guardar/cargar símbolo; pérdida limpia racha sin
perderlo. Si se toca motor/code.bin/asm/patch, añadir un combate de Palacio,
Arena, Tubo e historia; si se toca construcción común/isla, plaza y puertas
afectadas. Sin recorrido completo salvo paquete de consola (política usuario).

Estimación **hipótesis**, sesiones de agente con evidencia y suite: BASE 4–7
(identidad/espacio/EV son lo incierto); Torre 1 adicional, Palacio 1–2, Arena 1–2,
Fábrica 2–3, Domo 2–3, Tubo 1–2, Pirámide 2–3. Total 14–23 sesiones, más
integración/paquete y prueba de consola. No es una estimación de horas medidas.
Esta tarea de diseño no usa Azahar y no cambia juego, REPARTO ni tasks.json.

## 7. Anexo: conjuntos fijos de Esmeralda

Extraídos por campos de `sFrontierBrainsMons` en el commit de §1, omitiendo FACTORY
por el motivo de §2. IV es el valor de cada estadística; MAX_PER_STAT_IVS=31.
Cada fila conserva el orden del equipo. Especificación de datos, no un parche.


### Torre — Anabel

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | ALAKAZAM | BRIGHT_POWDER | MODEST | 24 | 106,0,152,152,100,0 | THUNDER_PUNCH, FIRE_PUNCH, ICE_PUNCH, DISABLE |
| Plata | ENTEI | LUM_BERRY | LONELY | 24 | 100,152,152,0,100,6 | FIRE_BLAST, CALM_MIND, RETURN, ROAR |
| Plata | SNORLAX | QUICK_CLAW | ADAMANT | 24 | 152,152,0,0,106,100 | BODY_SLAM, BELLY_DRUM, YAWN, SHADOW_BALL |
| Oro | RAIKOU | LUM_BERRY | MODEST | 31 | 158,0,252,100,0,0 | THUNDERBOLT, CALM_MIND, REFLECT, REST |
| Oro | LATIOS | BRIGHT_POWDER | MODEST | 31 | 252,0,252,6,0,0 | PSYCHIC, CALM_MIND, RECOVER, DRAGON_CLAW |
| Oro | SNORLAX | CHESTO_BERRY | ADAMANT | 31 | 252,252,0,0,6,0 | CURSE, RETURN, REST, SHADOW_BALL |

### Domo — Tucker

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | SWAMPERT | FOCUS_BAND | BRAVE | 20 | 152,152,106,0,100,0 | SURF, EARTHQUAKE, ICE_BEAM, COUNTER |
| Plata | SALAMENCE | LUM_BERRY | ADAMANT | 20 | 152,152,106,100,0,0 | EARTHQUAKE, BRICK_BREAK, DRAGON_CLAW, AERIAL_ACE |
| Plata | CHARIZARD | WHITE_HERB | QUIET | 20 | 100,152,106,152,0,0 | OVERHEAT, ROCK_SLIDE, AERIAL_ACE, EARTHQUAKE |
| Oro | SWAMPERT | LEFTOVERS | BRAVE | 31 | 252,252,6,0,0,0 | SURF, EARTHQUAKE, ICE_BEAM, MIRROR_COAT |
| Oro | METAGROSS | QUICK_CLAW | BRAVE | 31 | 252,252,6,0,0,0 | PSYCHIC, METEOR_MASH, EARTHQUAKE, PROTECT |
| Oro | LATIAS | CHESTO_BERRY | MODEST | 31 | 252,0,252,6,0,0 | THUNDERBOLT, PSYCHIC, CALM_MIND, REST |

### Palacio — Spenser

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | CROBAT | BRIGHT_POWDER | ADAMANT | 16 | 152,0,0,152,100,106 | CONFUSE_RAY, DOUBLE_TEAM, TOXIC, FLY |
| Plata | SLAKING | SCOPE_LENS | HARDY | 16 | 152,152,0,106,100,0 | EARTHQUAKE, SWAGGER, SHADOW_BALL, BRICK_BREAK |
| Plata | LAPRAS | QUICK_CLAW | QUIET | 16 | 0,0,252,0,106,152 | ICE_BEAM, HORN_DRILL, CONFUSE_RAY, PROTECT |
| Oro | ARCANINE | WHITE_HERB | HASTY | 31 | 6,252,252,0,0,0 | OVERHEAT, EXTREME_SPEED, ROAR, PROTECT |
| Oro | SLAKING | SCOPE_LENS | HARDY | 31 | 6,252,0,252,0,0 | HYPER_BEAM, EARTHQUAKE, SHADOW_BALL, YAWN |
| Oro | SUICUNE | KINGS_ROCK | HASTY | 31 | 252,0,252,6,0,0 | BLIZZARD, SURF, BITE, CALM_MIND |

### Arena — Greta

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | HERACROSS | SALAC_BERRY | JOLLY | 20 | 106,152,0,152,0,100 | MEGAHORN, ROCK_TOMB, ENDURE, REVERSAL |
| Plata | UMBREON | LEFTOVERS | CALM | 20 | 152,0,100,0,152,106 | BODY_SLAM, CONFUSE_RAY, PSYCHIC, FAINT_ATTACK |
| Plata | SHEDINJA | BRIGHT_POWDER | ADAMANT | 20 | 0,252,6,252,0,0 | SHADOW_BALL, RETURN, CONFUSE_RAY, AERIAL_ACE |
| Oro | UMBREON | CHESTO_BERRY | CALM | 31 | 252,0,0,0,252,6 | DOUBLE_EDGE, CONFUSE_RAY, REST, PSYCHIC |
| Oro | GENGAR | LEFTOVERS | MODEST | 31 | 252,0,252,0,6,0 | PSYCHIC, HYPNOSIS, DREAM_EATER, DESTINY_BOND |
| Oro | BRELOOM | LUM_BERRY | JOLLY | 31 | 6,252,0,252,0,0 | SPORE, FOCUS_PUNCH, GIGA_DRAIN, HEADBUTT |

### Tubo — Lucy

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | SEVIPER | QUICK_CLAW | BRAVE | 16 | 252,0,252,0,6,0 | SWAGGER, CRUNCH, POISON_FANG, GIGA_DRAIN |
| Plata | SHUCKLE | CHESTO_BERRY | BOLD | 16 | 252,0,0,0,106,252 | TOXIC, SANDSTORM, PROTECT, REST |
| Plata | MILOTIC | LEFTOVERS | MODEST | 16 | 152,0,100,0,152,106 | ICE_BEAM, MIRROR_COAT, SURF, RECOVER |
| Oro | SEVIPER | FOCUS_BAND | BOLD | 31 | 252,0,0,0,252,6 | SWAGGER, CRUNCH, SLUDGE_BOMB, GIGA_DRAIN |
| Oro | STEELIX | BRIGHT_POWDER | BRAVE | 31 | 252,0,0,0,6,252 | EARTHQUAKE, ROCK_SLIDE, EXPLOSION, SCREECH |
| Oro | GYARADOS | CHESTO_BERRY | ADAMANT | 31 | 252,6,0,0,0,252 | DRAGON_DANCE, RETURN, ROAR, REST |

Nota de implementación (2026-11-12, `reports/frontier.md` §46): el Shuckle de plata suma 610 EV en
Esmeralda; ORAS limita el total a 510 (`0x3b4b64`) y el parche usa 252,0,0,0,106,152. La fila se
conserva como dato de origen.

### Pirámide — Brandon

| Símbolo | Especie | Objeto | Naturaleza | IV | EV (PS/At/Def/Vel/AtE/DefE) | Movimientos |
| --- | --- | --- | --- | --- | --- | --- |
| Plata | REGIROCK | QUICK_CLAW | ADAMANT | 16 | 152,152,0,0,106,100 | EXPLOSION, SUPERPOWER, EARTHQUAKE, ANCIENT_POWER |
| Plata | REGISTEEL | LEFTOVERS | ADAMANT | 16 | 152,152,0,0,6,200 | EARTHQUAKE, METAL_CLAW, TOXIC, IRON_DEFENSE |
| Plata | REGICE | CHESTO_BERRY | MODEST | 16 | 106,0,152,0,100,152 | ICE_BEAM, AMNESIA, THUNDER, REST |
| Oro | ARTICUNO | SCOPE_LENS | MILD | 31 | 6,0,252,252,0,0 | BLIZZARD, WATER_PULSE, AERIAL_ACE, REFLECT |
| Oro | ZAPDOS | LUM_BERRY | MILD | 31 | 6,0,252,252,0,0 | THUNDER, DETECT, DRILL_PECK, LIGHT_SCREEN |
| Oro | MOLTRES | BRIGHT_POWDER | MILD | 31 | 6,0,252,252,0,0 | FIRE_BLAST, HYPER_BEAM, AERIAL_ACE, SAFEGUARD |

## 8. Verificación de este diseño y reproducción

Ejecutado el 2026-11-11 desde lane/codex:

```bash
source scripts/env.sh
git clone --filter=blob:none --no-checkout https://github.com/pret/pokeemerald.git /tmp/frontier-cerebros-pokeemerald
git -C /tmp/frontier-cerebros-pokeemerald checkout --detach 731ad5bfd6e6f265508d0efcca0ba42f9dcf5881
git -C /tmp/frontier-cerebros-pokeemerald rev-parse HEAD
python frontier/ids.py
python -c 'import sys; sys.path.insert(0,"frontier"); import patch; b,_=patch.assemble(); print(len(b), patch.CAVE_END-patch.CAVE-len(b), hex(patch.CAVE+len(b)))'
env -u ORCH_LANE bash -c 'source scripts/env.sh; python -m pytest -q tests'
git diff --check
```

Resultado de la suite: **1105 passed, 1 skipped, 40.14 s**,
`work/frontier/cerebros/tests.log`. Las medidas de works y espacio se describen
en §4/§6. `work/frontier/cerebros/design-check.txt`: ocho objetos válidos con
`frontier_orch.check_task`, dependencias existentes e IDs duplicados detectados
contra la cola actual; 36 filas del anexo comparadas campo a campo con el C fijado;
siete pares ID/nombre de clase comparados con gametext; REPARTO y tasks.json intactos.
Para reproducir el cotejo de equipos, tomar los bloques `.species/.heldItem/
.fixedIV/.nature/.evs/.moves` de `sFrontierBrainsMons`, ignorar FACTORY y comparar
las seis filas por instalación en orden. Los resultados de juego de documentos
previos son evidencia heredada: aquí no se ejecutó Azahar ni se generó un parche.
