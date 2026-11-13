# Plan de prueba en consola: Frente de Batalla alfa v0.2

Paquete: `dist/oras-frontier-alpha-v0.2` (lo genera `python frontier/package.py`; hashes en su `manifest.json`).
Partida de prueba: `dist/oras-frontier-checkpoint-test-v0.2` (su `LEEME.txt`).
Evidencia anterior en Azahar: `reports/frontier.md` §38 y §49; la validación del paquete v0.2 se registra en §50.
**El usuario confirma el 2026-11-13 que la v0.2 funciona en su 3DS.**
Fuente: conversación («Confirmado en la 3ds funciona»). Confirmación funcional general; no se ha aportado
un desglose de modalidades/jefes ni un nuevo volcado de RAM. Se cierra F7-CONSOLA-MANSION con el arreglo de Luma. La v0.1 sí se probó y se colgaba en todo combate de tipo Mansión por la
colisión con Luma descrita al final. No se instala nada automáticamente: lo copia el usuario.

## Qué es nuevo para la consola

La v0.2 incorpora el arreglo de la cueva para Luma, los siete Cerebros con símbolos de plata/oro y la consulta
«Símbolos» en las recepciones. El Frente ya no ofrece «Guardar vídeo»; la Mansión original conserva esa opción.
La consola ha ejecutado v0.5, el evento de Mew y la alfa v0.1 fallida. Estas piezas de v0.2 necesitan validación:

| Pieza | Dónde | Se ejecuta en | Riesgo |
| --- | --- | --- | --- |
| Código nuevo al final de `.text` (cueva 0x579604–0x57A000; desde F7-CUEVA-LUMA, 0x579604–0x579804 reservado a Luma y el código en 0x579804) | `code.ips` | toda instalación (alquiler, rachas, rival, Domo, Tubo, Pirámide) | v0.1: colisión medida; v0.2: reserva separada, validación real de Luma pendiente |
| `DllBattle.cro`: copia de vuelta del equipo, puentes de Arena y Palacio, Palacio C y rutinas de Arena/Palacio B en el relleno de la región de código (0xd7630–0xd7b83) | `romfs/DllBattle.cro` + `.crr/static.crr` | **cualquier combate** carga el CRO; el código del relleno corre en Palacio y Arena | alto para Palacio y Arena (permisos de `ldr:ro` sobre el relleno, sin medir); la carga del CRO en sí, medio |
| `DllField.cro`: puente del Tubo (0x4e644) y Cerebros (0xf0480…) | `romfs/DllField.cro` + CRR | consultas de equipo del Tubo y rivales de Cerebros | medio |
| Isla 209, plaza con siete edificios, interiores 213/329/340/456/457/458/140–142 | `romfs/a/0/1/3`, `a/0/1/4`, `a/0/3/9`, `a/0/4/0`, `a/1/3/7` | al llegar a la isla y entrar en cada edificio | medio: memoria de la consola con la plaza cargada (en Azahar no hay límite real) |
| Scripts y textos (marinero, ferry, recepciones, texto 637) | `a/0/2/9`, `a/0/7/x`, `a/0/8/x` | puerto, ferry, recepciones | bajo: misma técnica que el evento de Mew, probada en consola |

## Antes de empezar

1. Copia de la partida con Checkpoint (Backup).
2. Copia en el PC de la carpeta `SD:/luma/titles/000400000011C400/` actual (v0.5 o Mew).
3. Juego europeo 1.0 **sin** actualización; Luma con «Enable game patching».
4. Instalar el paquete según su `LEEME.txt` (sustituir la carpeta entera, no mezclar).
5. Tener a mano el móvil para fotografiar pantallas de error.

## Orden de pruebas (de menos a más riesgo)

Anotar en cada paso: hecho / falla, y si falla, la pantalla exacta y lo último que se hizo.

### 0. Arranque y lo ya conocido (tu partida, sin Frente)
- Arranca el juego y carga **tu partida normal**. Mirar: llega al juego; la DexNav muestra nivel/racha (p. ej. «23/7»).
- Un **combate salvaje**: es la primera carga del `DllBattle.cro` nuevo. Si se cuelga al empezar el combate, es el CRO o
  el CRR (no sigas: vuelve a la v0.5).
- Con un portador de Repartir Exp. en reserva: al acabar, su mensaje propio de EXP (como en la v0.5).
- Un combate de entrenador si tienes alguno a mano.
- **No guardes** si algo raro pasa.

### 0b. Mansión original y comprobación de Luma
- Antes del Frente, entrar en la **Mansión Batalla original del Resort**, modalidad Individual, seleccionar tres
  Pokémon e iniciar un combate. Terminarlo y volver a la recepción. Este caso verifica directamente el cuelgue
  de v0.1; no basta un combate de historia.
- Si se dispone del depurador de Luma, hacer la comparación de memoria del apartado final en ese combate.

### 1. Puerto y pase (partida de prueba)
- Restaurar `FrenteTest-puerto-Calagua` con Checkpoint y Continuar: apareces en el puerto de Calagua.
- Marinero de la derecha (dos casillas a la derecha del punto de partida y mirando arriba): «Oye, ¿tú no eres quien ha
  ganado la Liga?» y «Ruben ha obtenido un Pase del Frente».
- Empleada del ferry (a la izquierda, junto a la pasarela): enseñar el ticket; el menú ofrece Resort Batalla, Ciudad
  Portual, **Isla del Frente**, Me quedo aquí.

### 2. Isla y plaza
- «Isla del Frente» → Sí: fundido y llegada al muelle de la isla. **Primer punto de riesgo de memoria.**
- Caminar al oeste y bajar hasta la explanada: se ven los siete edificios. Recorrerla entera (riesgo de memoria con todo
  cargado).
- Guardar en la plaza (menú X → Guardar). Apagar con HOME → cerrar programa, volver a abrir y Continuar: apareces en la
  plaza.

### 3. Instalaciones sin motor de combate nuevo
En cada una: entrar por la puerta, hablar con la recepcionista **de la derecha**, inscribirse (guarda la partida),
jugar un combate, terminar (perder vale) y salir por la puerta a la plaza.
En el Frente no debe aparecer «Guardar vídeo». Consultar también «Símbolos» en cada recepción: una partida nueva
no tiene ninguno. Los encuentros de plata/oro requieren las rachas que indica el LEEME; no se declaran probados
en consola por completar solamente este circuito.
1. **Torre** (casa de tejado plano, al norte): tu equipo. Prueba la cueva de `code.bin` (racha por ruta).
2. **Fábrica** (gimnasio del centro): alquiler de 3 de 6. El alquiler es código de la cueva: mirar que en combate salen
   los alquilados (nivel 50) y que al acabar tu equipo está igual.
3. **Domo** (casa del oeste): sala de piedra amplia. Inscribir 3, el rival enseña sus 3, elegir 2. **Al acabar, salir
   por abajo**: en Azahar la primera build dejaba al jugador encerrado; está arreglado, pero es lo primero que hay que
   mirar.
4. **Pirámide** (casa de tejado azul, este): inscripción y paso a la cueva (zona 141). Hablar con un entrenador del
   piso. Mirar que la cueva carga (riesgo de memoria) y que al perder vuelves al vestíbulo.

### 4. Instalaciones con motor de combate nuevo (lo más arriesgado, al final)
5. **Arena** (casa de paja, sur): puente de `DllBattle.cro` hacia la cueva. Si el combate llega al turno 3 con los dos
   en pie, hay juicio.
6. **Tubo** (cabaña del suroeste): puente de `DllField.cro`. Elegir puertas; mirar al menos una sala sin combate y un
   combate; PS/estado arrastrados.
7. **Palacio** (casa de dos plantas, sureste): **código en el relleno de `DllBattle.cro`, el mayor riesgo**. Tus Pokémon
   eligen solos el movimiento. Si se cuelga al primer turno de un Pokémon tuyo, es este código (anotar el turno).

### 5. Vuelta
- Volver al muelle, empleado de la isla → Ciudad Calagua. Guardar en el puerto.

## Si se cuelga

- Pantalla congelada o negra: mantener POWER ~10 s hasta que se apague.
- Pantalla de excepción de Luma («An exception occurred»): fotografiarla; Luma guarda el volcado en
  `SD:/luma/dumps/arm11/`. Copiar ese fichero al PC (el último por fecha) y adjuntarlo.
- Antes de reintentar: restaurar la copia de Checkpoint (el cuelgue puede ocurrir a mitad de guardado).
- Anotar: paso de esta lista, pantalla, qué tecla se pulsó, si el cuelgue se repite.
- Si falla en el paso 0 o 2, no seguir con las instalaciones: volver a la v0.5 y avisar.

## Volver a la v0.5

1. **Antes**, si la partida está guardada en la isla o en un edificio del Frente, volver a Calagua en el ferry y guardar
   allí: con la v0.5 la zona 209 es una zona sin usar del juego y la 213, 329, 340, 456–458 y 140–142 tampoco tienen
   el Frente; cargar una partida guardada en ellas sin el paquete **no está probado** y probablemente cuelgue.
2. Apagar. Borrar `SD:/luma/titles/000400000011C400/` y copiar la carpeta guardada en «Antes de empezar» (o la de
   `dist/held-exp-share-v0.5/mods/000400000011C400`).
3. O restaurar la partida de Checkpoint anterior a las pruebas.
4. Con la v0.5, el Pase del Frente (objeto 701) queda en la mochila con el nombre retail de ese hueco; los works del
   Frente quedan escritos pero ninguna parte del juego retail los lee (`frontier/ids.py`). Sin probar en consola.

## Qué devolver

Una tabla con los pasos 0–5 (hecho / falla), fotos de los fallos y, si hay, el volcado de `SD:/luma/dumps/arm11/`.

## Incidencia de consola: Mansión original (2026-11-11; investigación 2026-11-12)

El usuario sí ha probado la alfa en consola: la Mansión Batalla original se cuelga;
con su partida normal los combates de historia funcionan. Esto corrige el alcance
histórico de «nada en 3DS» del encabezado. La modalidad/selección exactas del cuelgue
no están documentadas. La causa se determinó después: véase «Causa medida y arreglo».

Volcado de solo lectura `dumps/crash_dump_00000000.dmp`, SHA256
`d58509dec10ac67381e34c41f96fa300f912c73e5d4ff6b6da6b8d8688d29787`:
`frontier/probes/maison/dump.py` verifica sus 652 bytes, ARM11/data abort, PC
0x76638c, r0=0, FAR=0xc, LR=0x12bad8. Con base CRO 0x6f3000 corresponde a
0x7338c (`ldrh r0,[r0,#0xc]`). Los **96 bytes completos** de la ventana de código
del volcado coinciden tanto con DllBattle de la alfa como con v0.5. El constructor
retail llega a r0=0 cuando el equipo de cliente tiene cuenta cero; el dump no contiene
el heap para consultar el objeto directamente. Esta coincidencia no demuestra que
v0.5 también falle: falta ejecutar el caso con ella.

Sondas y protocolo: `frontier/probes/maison/README.md`. Investigación en curso;
no distribuir un supuesto arreglo ni declarar las cinco modalidades verificadas
hasta tener las trazas de los combates. No se ha cambiado el motor.

### Resultado de la investigación (Claude, 2026-11-12)

- En Azahar, con el paquete alfa exacto, la Mansión original **no se cuelga** en ninguna de las cinco modalidades
  (Individual, Doble, Triple, Rotatorio, Múltiple), ni con «Fábrica Batalla» de su recepcionista, ni con la partida
  `domo-cuelgue` del usuario llevada a la Mansión (`reports/frontier.md` §48.1).
- El volcado no encaja con la Mansión: su pila coincide con la de un combate del **Domo** y su montón dice que había
  2 Pokémon en el combate (rival 2, jugador 0). Solo el Domo pone 2 rivales.
- Con la partida `domo-cuelgue` el Domo tampoco se cuelga en Azahar.

**Preguntas al usuario** (para reproducirlo):
1. ¿En qué edificio salió la pantalla de Luma: la Mansión del Resort Batalla o la casa del oeste de la isla
   (Domo, sala de piedra)?
2. ¿La partida `domo-cuelgue/main` es la que cargaste justo antes de ese cuelgue? Si no, la copia de Checkpoint
   anterior al cuelgue.
3. Los pasos desde Continuar: a quién hablaste, opciones elegidas (Combatir, qué tres inscribiste y qué dos
   elegiste como luchadores; si pulsaste B en algún menú), y si antes, en la misma sesión, jugaste otra instalación.

### Causa medida y arreglo (F7-CUEVA-LUMA, 2026-11-13)

Medido por el usuario con el depurador de Luma: Luma copia su código de LayeredFS (276 bytes) en **0x579604**, el
final del .text del exheader, que era el principio de nuestra cueva (`rental_hook`), y desvía 0x1325a4 y 0x123e80
hacia él. Por eso en consola se colgaba **todo** combate de tipo Mansión (también la Mansión original), y en Azahar,
que no escribe nada en el ejecutable, no. Las preguntas de arriba quedan contestadas por la medida.

Arreglo (`reports/frontier.md` §49): 0x579604–0x579804 se deja libre para Luma (su tamaño, según su código fuente, es
fijo: 0x114 bytes), nuestro código empieza en 0x579804, y las rutinas de combate de Arena y Palacio pasan a
`DllBattle.cro`. En Azahar, simulando a Luma (sus 276 bytes escritos en el code.bin): la alfa v0.1 reproduce el
cuelgue con el mismo equipo 0xd8e007f7 de los volcados; con el arreglo, Mansión original Individual, las siete
instalaciones y un combate de la historia van bien.

### Comparación con el depurador de Luma (v0.2)

Usar el `manifest.json` del paquete instalado, apartado `console_check`; no el de otra build. En un combate de la
Mansión original, pausar el proceso de Rubí Omega con el depurador de Luma y leer memoria sin modificarla:

1. **0x579604–0x579717**: los 276 bytes de LayeredFS. Los primeros 16 bytes deben coincidir con
   `luma_payload_first16` (bytes en orden de memoria); los saltos de 0x1325a4 y 0x123e80, con `luma_branches`.
2. **0x579804**: primeros 16 bytes iguales a `hooks_first16`. La primera palabra ARM es **0xe92d41f0**
   (`push {r4-r8,lr}`), que se ve como bytes `f0 41 2d e9` en memoria little endian.
3. Comparar la ventana completa **0x579604–0x579fff** con el `code.bin` construido y con su variante de laboratorio:

   ```bash
   source scripts/env.sh
   python frontier/probes/luma/package_ips.py dist/oras-frontier-alpha-v0.2 --out work/frontier/pkg02/luma
   ```

   `work/frontier/pkg02/luma/package-code.bin` contiene ceros en 0x579604–0x579803: **antes** de que Luma escriba.
   `work/frontier/pkg02/luma/code.bin` contiene el IPS del paquete más la carga de Luma: es la referencia para la
   memoria **después** de cargar. En ambos ficheros, el offset de una dirección es dirección − **0x100000**.
   Fuera de la carga de Luma, el código propio desde 0x579804 debe coincidir con ambas referencias.
   `code_with_luma_sha256_text` identifica la referencia simulada hasta 0x57a000; no es el hash de toda la RAM.

Conservar el volcado de esa ventana, la versión de Luma y el manifiesto instalado junto al resultado del combate.
Si una versión distinta de Luma usa otros bytes, registrar la diferencia antes de atribuirla al Frente. No aplicar
el IPS de laboratorio en la consola: el paquete distribuido deja la reserva libre para el Luma real.
