# Estado — 2026-10-31

## Entrega disponible

Paquete generado en `dist/held-exp-share-v0.5/`. v0.3 añadió los textos;
v0.4 cambia 1 byte para que el portador tenga su propio mensaje de EXP;
v0.5 muestra la racha del DexNav («Nivel / Racha 23/7», `reports/dexnav.md`).
**Probado por el usuario en una 3DS con Luma3DS: v0.2 y v0.4 funcionan,
incluido el mensaje individual del portador.** El usuario indica (2026-11-01)
que la racha del DexNav (v0.5) también funciona junto a los otros mods.
La selección por objeto funciona; no hizo falta la alternativa por slot.
**El efecto se ha validado en cuatro combates reales en Azahar.** Las pruebas
de Azahar usan copias aisladas bajo `work/` (partida nueva y la partida
convertida del usuario).

Se ha completado:

- Identificación y hash del volcado: título `000400000011C400`, producto
  `CTR-P-ECRA`, sin incorporar ninguna actualización.
- Extracción completa: 655 archivos RomFS, 145 CRO, exheader y ejecutable
  descomprimido. La extracción directa de RomFS con ctrtool quedó incompleta;
  el proceso definitivo extrae la imagen con ctrtool y los archivos con 3dstool.
- Base limpia y base Repolished separadas en `baseline/oras/`.
- Aplicación de 4 registros IPS y 12 sustituciones RomFS del mod.
- Mapa de memoria derivado del exheader y contrastado con `static.crs`.
- Localización de la rutina EXP/EV en `DllBattle.cro`, offset `0x324D0`.
- Cambio de selección en `0x32630`, edición del objeto 216 y actualización
  de hashes CRO y tabla CRR.
- Scripts de generación con comprobación de hashes, bytes y límites.
- Pruebas y documentación de EV separada.

## Validación realizada

- **16 pruebas pytest**: formatos IPS, rechazo de bases o bytes incorrectos,
  mapa de segmentos, integridad CRO/CRR, ausencia de relocaciones sobre el
  cambio y reproducción de diferencias IPS.
- **17 escenarios ARM** con Unicorn 2.1.4 ejecutando la rutina original y
  la modificada. Se verifican participante, portador en reserva, debilitado,
  sin objeto, interruptor apagado, varios participantes, último slot,
  redondeo, mínimo de un punto, combate de entrenador, intercambio, Huevo
  Suerte, afecto, Pokérus, varios portadores, equipo debilitado y equipo vacío.
- Lectura de propiedades del objeto con las funciones ARM del propio juego:
  se verifican bolsillo, bits de restricciones, uso de campo y permiso por ID.
- Dos extracciones/generaciones de base idénticas; dos generaciones de parche
  idénticas, incluidos manifiestos y archivos del paquete.

- **7 escenarios ARM adicionales** del despachador de recompensas: normal,
  nivel 100, huevo, huevo inválido, límite por estadística, límite total y
  ganancia parcialmente limitada. La actualización de EV es real; la llamada
  final de aplicación de EXP se registra mediante un sustituto.
- Arranque real de Azahar 2126.2 con renderizado por software: el registro
  confirma `code.ips` y las sustituciones LayeredFS; la introducción muestra
  el mensaje propio de Repolished. Se ha entrado en el primer combate: `DllBattle` carga correctamente.
  El reparto a un portador en reserva sigue pendiente.

Resultados de rutina: `reports/arm-validation.json`.
Los datos externos de los combates de prueba son simulados. Estas pruebas
**no** cubren los menús, la construcción real del equipo ni la escritura
final de experiencia/EV en la partida. Los getters de huevo sí se ejecutan;
los auxiliares de descifrado usan datos simulados.

## Validación en Azahar

`scripts/validate_gameplay.py` compara partidas reales antes/después de cuatro
combates individuales salvajes y comprueba que el overlay probado coincide con
el generador. Equipo de tres clones, 0 EV iniciales.

| Caso | Objeto | ΔEXP | Resultado |
|---|---|---|---|
| Reserva | slot 2 | 24 / 12 / 0 | Portador recibe la mitad y EV completos |
| Participante | slot 1 | 16 / 0 / 0 | Igual que sin objeto; sin duplicar |
| Sin objeto | — | 16 / 0 / 0 | Control |
| Debilitado | slot 2, 0 HP | 16 / 0 / 0 | Portador sin EXP ni EV |

Menús comprobados: el objeto aparece en Objetos, admite Dar y queda equipado
tras guardar. Resultado detallado: `reports/gameplay-validation.json`.

## Partida existente con el objeto clave

Probado con una copia de una partida real (`inputs/save/20261031-123645/main`,
SHA-256 `a30034d1…61e2`), avanzada en Ruta 102 con el 216 en Objetos clave.
Copias en `work/user-save-test/`.

- Tras aplicar el parche el objeto **sigue en Objetos clave**, con la
  descripción antigua, pero el menú ofrece **Dar** y se puede equipar.
- **Duplicación**: al darlo desde Objetos clave el bolsillo no se descuenta
  (sigue ×1 en la partida guardada). Probable causa: el juego descuenta del
  bolsillo indicado por los datos del objeto (Objetos), no de donde está.
- Combate salvaje real (Torchic Nv. 12 contra Seedot Nv. 2), portador
  Poochyena en reserva: Torchic +12 EXP, portador +6 EXP, resto 0.
  EV: participante y portador +1 Defensa, resto 0.

Solución: `save_fixture.py --move-exp-share` mueve el 216 de Objetos clave
(`0xA40`) a Objetos (`0x400`) y recalcula el checksum del bloque 1; solo
cambian 6 bytes. Probado en Azahar con la copia convertida
(`work/partida-convertida/main`): aparece en Objetos, al darlo desaparece de
la Bolsa y el Pokémon lo conserva tras guardar. Sin duplicación.

## Próximo paso

1. Entrega en la historia: no se modifica el evento; debe entregar el objeto
   216 en el bolsillo Objetos. Comprobarlo al llegar a ese punto.
2. Combates dobles, hordas y entrenadores con varios Pokémon.

## Racha del DexNav (v0.5)

Detalle en `reports/dexnav.md`. Azahar: «22/0», «22/7» con la racha escrita
por GDB (ficha y búsqueda) y «3/0» tras «¡Se ha escapado!». El usuario
indica que funciona en su configuración real.

## Mensaje de EXP (v0.4)

Probado en Azahar con la partida del usuario convertida (`work/v04-test/`):
combate contra Wurmple Nv. 2, Torchic participa y Poochyena lleva el objeto.
Mensajes vistos: «Torchic ha ganado 16 Puntos de Experiencia.» y «Poochyena
ha ganado 8 Puntos de Experiencia.»; sin resumen de equipo. La partida
guardada confirma +16 y +8 EXP. En ARM, los 7 casos de despacho comprueban
que solo se emiten mensajes individuales; con la instrucción original el
mismo arnés reproduce el resumen. El usuario confirmó v0.4 en su 3DS.

## Textos (v0.3)

Sin cambiar tamaños: la línea nueva se rellena con ceros tras el terminador,
así el GARC y los IPS conservan su estructura. El generador comprueba el texto
original exacto antes de sustituirlo.

| Archivo | Entrada:línea | Cambio |
|---|---|---|
| `a/0/7/7` (texto ES) | 117:216 | Descripción del objeto |
| `a/0/7/3` (texto EN) | 117:216 | Descripción del objeto |
| `a/0/8/5` (historia ES) | 432:16 | Explicación al recibirlo |

La descripción en español se ha visto en Azahar. La línea de la historia solo
se ha comprobado decodificando el archivo; el evento de esa partida ya pasó.
Los mensajes de activar/desactivar (164:160-161) quedan inaccesibles y no se
cambian. El resumen de equipo (147:45) ya no se muestra desde v0.4.

Consola: Luma3DS desactiva en `ro` la firma CRR y los hashes CRO/CRR
(`sysmodules/loader/source/patcher.c`); el parche además los recalcula.

Huevo, nivel 100 y límites de EV solo se han probado con ARM.
La referencia a Alpha Sapphire del `instructions.txt` se trata como errata,
según indicación expresa del usuario. No se modificaron los inputs.
