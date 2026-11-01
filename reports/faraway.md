# Mapa Viejo e Isla Suprema — estado (fase 3 en curso)

Base: Omega Ruby 1.0 EUR + Repolished 1.7.6 + Repartir Exp. + racha DexNav (v0.5).
Todo lo medido abajo es del volcado local; las pruebas son de Azahar 2126.2.

## Circuito validado en Azahar (2026-11-01)

1. Partida con el Episodio Delta completado (flag 2729): en el puerto de Calagua
   aparece un marinero nuevo. Entrega el **Mapa Viejo** una sola vez («Ruben ha
   obtenido un Mapa Viejo» → Bolsillo Objetos Clave); la segunda vez solo habla.
2. Al entregarlo, el **capitán Arenque** aparece en el muelle (`FlagReset` + `MdlAdd`).
   Reconoce el mapa, pregunta Sí/No y, con Sí: fundido, bocina y cambio de mapa.
3. **Isla Suprema** (zona 473, clon de Isla del Sur con mapa y área propios): la
   pantalla inferior muestra «Isla Suprema». Arenque y Peeko esperan junto al bote.
4. Interior (zona 474, clon del claro de Isla del Sur): Mew provisional (modelo de
   Wingull). Grito, «¡Miu!» y combate contra **Mew Nv. 30**.
5. Captura con Master Ball: Pokédex registrada; en la caja, Mew con lugar de
   encuentro 277 («Isla Suprema»), nivel 30, 3 IV perfectos, sin variocolor.
6. Guardado en el juego: flags 3031 (capturado) y 3034 (combate iniciado) en el
   archivo. Al recargar, Mew ya no aparece.
7. Arenque en la isla: «¿Volvemos a Ciudad Calagua?» → vuelta al puerto.
8. Partida sin Delta (2720 sí, 2729 no): en el puerto no aparecen ni el marinero
   ni Arenque.
9. Huida: Mew Nv. 30 debilitó a Torchic; con Beldum la huida funcionó. Mew
   desaparece; al salir del claro y volver a entrar está otra vez («¡Miu!»).

Capturas en `work/faraway/` (no se versionan).

## Modelo y persecución (2026-11-01)

El modelo provisional se sustituyó por Mew real en el commit `94d6db4`.
`faraway/mew_model.py` extrae modelo, texturas y animaciones de Poké Recreo de
las entradas 1547, 1549 y 1553 de `a/0/0/8`. SPICA copia los materiales de
Wingull de campo (MoveModel 484), conserva las texturas de Mew y cambia el
shader de batalla `1@PokePack` por `0@FieldChar`. El shader de batalla causaba
un bloqueo al cargar el claro. Escala del esqueleto: 0,6. El contenedor MM se
añade como MoveModel 544; las animaciones de campo usan las ranuras 1, 3 y 94.

La persecución añadida por Claude tiene cinco posiciones:
`(20,19) → (25,17) → (16,21) → (25,23) → (20,14)`.
Cuatro disparadores del evento 42 se arman mediante `WORK_MEW_SPOT = 16667`,
valores 0–3. La altura del disparador es **36**; con 0 no se activaba al pisar
la zona. El movimiento probado usa
`MdlAcmdMakeMoveEx(19, destinoX, 38, destinoY, 0, 1, 1)`; no se da por
resuelto el significado de todos sus parámetros. Hablar con Mew antes del
último punto también lo hace huir. En el último punto habla y empieza el combate.

Claude dejó documentada la cadena completa y la sesión detenida en
«¡Mew no tiene adónde huir!». Al retomar esa misma sesión se comprobó
directamente el inicio del combate **Mew Nv. 30** y su captura con una
Master Ball de laboratorio. Evidencias locales:
`work/faraway/validation-hide-seek/battle-after-chase.png` y
`captured-after-chase.png` en la misma carpeta.

Se corrigió después un fallo de estado: al borrar el modelo tras el combate,
el código volvía a poner el work en 0 y armaba un disparador sin Mew presente.
Ahora se usa **5 (inactivo)** tras cualquier resultado. Al cargar el claro,
se vuelve a 0 solo si Mew no está capturado; si lo está, se conserva 5.
La rutina de huida comprueba además el flag de captura antes de mover el modelo.
El cambio está en scripts Pawn del claro dentro de `a/0/1/3`, sin nuevo parche ARM.

Validación de esta corrección: generación completa de los 26 archivos del
overlay y **34 pruebas pytest aprobadas**, incluidas ocho nuevas de estado
en `tests/test_faraway.py`. Estas últimas ejecutan el flujo simbólico del
script y simulan las llamadas nativas: prueban reinicio, captura, resultados
de combate, cuatro huidas y disparadores obsoletos. No sustituyen la prueba
del motor de movimiento. Una prueba adicional evita que el controlador de
Azahar borre los metadatos de una sesión al intentar cerrarla desde otro
espacio de PIDs (sandbox).

Pruebas posteriores en Azahar con el estado inactivo implementado:

- **Capturado:** recarga, cruce de los cuatro rectángulos de activación,
  salida a la zona 473 y reentrada. Mew sigue ausente y se puede caminar.
  Guardado comprobado: flag 3031 = 1, work 16667 = 5.
- **Guardado intermedio:** después de dos huidas, work = 2; al reiniciar el
  juego se conservan Mew en su escondite y el progreso. El tercer y cuarto
  disparador llevan a Mew hasta el punto final. Guardado final: work = 4.
  El reinicio a 0 corresponde a una nueva visita, no a continuar un guardado.
- **Huida del combate:** con Bola Humo (objeto 228, nombre contrastado en los
  textos del volcado), se vuelve al claro sin Mew. Guardado: flag 3031 = 0,
  flag 3034 = 1, work = 5. Se cruza el primer disparador sin activarlo,
  se sale y se regresa: Mew reaparece en el primer punto y work = 0.

La huida reveló además un mensaje invisible después del combate: el campo
seguía fundido a negro y el diálogo apuntaba al NPC que acababa de borrarse.
Se añadió el fundido de entrada retail de Registeel (zona 159, `sub_840`):
helper del compartido 79 en `0x30`, argumentos `(2, 4)`, seguido de la espera
de fundido en `0x210`. Los hashes nativos coinciden con los del encuentro
retail: `4190ECEC`, `7B2FEC69` y `B295378D` (este último es el índice 10
del compartido 79). El mensaje usa ahora el jugador 255 como referencia.
Repetido en Azahar con el overlay final: aparece «Mew ha desaparecido entre
la hierba…» sobre el claro visible; al cerrar el diálogo se puede caminar y
guardar, con work = 5 y captura = 0. Evidencia: `flee-visible-message.png`.

Las pruebas de huida usan una copia artificial: flags de captura y combate
reiniciados, primer Pokémon curado y equipado con Bola Humo. Al derivar esa
copia de un guardado con Mew borrado, primero hay que salir y entrar al claro
para reconstruir los NPC. No se ha modificado la partida original.
Partidas y capturas de evidencia: `work/faraway/validation-hide-seek/`.
Resumen y hashes de los archivos probados: `reports/faraway-validation.json`.

Para regenerar con las herramientas locales ya compiladas:

```bash
source scripts/env.sh
python faraway/build.py
pytest -q
```

Resultado: `work/faraway/build/overlay/`, para superponer al paquete v0.5.
No contiene el warp de desarrollo de la Ruta 102. La generación reemplaza
su propia carpeta de trabajo; no instala nada en la consola.

Paquete combinado para Luma: `dist/oras-mew-luma-preview-v0.1.zip`, con la
estructura `luma/titles/000400000011C400/`, instrucciones y manifiesto.
Incluye Repolished, Repartir Exp., DexNav y el evento normal de Mew; no incluye
partidas ni el warp de desarrollo. Se genera con `python faraway/package.py`
(requiere destino nuevo; `--output work/otro-paquete` permite otra generación).
El empaquetador valida los hashes de v0.5, las fuentes y el overlay del informe
de pruebas, y comprueba cada archivo del ZIP contra su copia en disco.
Es una entrega preliminar: el evento aún no está validado en una 3DS.

## Consola y v0.2 (2026-11-01)

El usuario jugó el circuito de v0.1 en su consola. Funcionó. Sus observaciones:
el viaje no tiene animación, Arenque sigue en el muelle tras el evento, el
modelo de Mew se ve mal y Mew no se esconde porque no hay hierba alta.

- **Viaje:** el ferry retail (script compartido 79) tampoco tiene animación;
  la barca de Arenque sí. Su rutina retail (compartido 41, `GlobalCall` 10290,
  `sub_1FC`) hace fundido, `WorkSet(16697, 6|7)`,
  `CallApplicationDemo(9, 0×7, 30)`, un fotograma de espera y el cambio de mapa.
  Los otros usos de `CallApplicationDemo` son 7, 8, 10, 11, 12, 15, 16, 17, 20
  y 21 (teleférico, submarino, etc.). El viaje copia esa secuencia en los dos
  sentidos; el valor de 16697 se guarda en la pila y se restaura. En Azahar
  sale la escena retail del bote con Peeko; tras ida y vuelta, el guardado
  tiene 16697 = 0, como antes.
- **Arenque en el muelle:** se mantiene a propósito; la especificación pide
  que el viaje se pueda repetir también tras capturar a Mew.
- **Modelo de Mew:** al copiar el material de Wingull se perdían la
  transformación UV (escala 2 con espejo en cuerpo y ojos, ±4 con
  desplazamiento en los iris) y la transparencia de los iris. `fieldify`
  conserva ahora UV, modos de repetición, mezcla, prueba alfa y máscara de
  profundidad. Copiar el *mapper* completo dejó a Mew negro: el tipo de
  sampler depende de la unidad (0 en la unidad 0 de Mew, 1 en la unidad 1 de
  campo). Por eso solo se copian los modos de repetición.
- Paquete `dist/oras-mew-luma-preview-v0.2.zip`.

## Identificadores (medidos)

| Qué | Valor | Prueba |
| --- | --- | --- |
| Delta completado | flag 2729 | PKHeX `flags_oras` |
| Estado del evento | flags 3026 mapa, 3031 Mew capturado, 3034 combate, 3037/3039 ocultar NPC; work 16665 progreso | Ningún script (1157), NPC (2904), entrada de PKHeX ni literal de código los usa |
| Mapa Viejo | objeto 442 («Mapa» de 4.ª gen.) | Ningún script lo da, quita ni consulta |
| Combate | fila 29 de la tabla estática (`DllField.cro` 0xF1B20 + 12·29): Deoxys duplicado | Ningún script ni código usa el índice 29 (la fila 55 sí la usa el código) |
| Zonas | 473/474 («???», sin warps ni scripts que lleguen) | `ZoneRepurposeScanner` de CTRMap-F5 |
| Nombre de lugar | ranura 277 (impar y vacía); 0–168 son de Kalos y no se tocan | Lista de lugares |
| Puerto | zona 317, texto 523 (30 líneas en los 8 idiomas) | |
| Arenque / Peeko | MoveModels 283 / 484 (uid 4134), entradas de registro copiadas del área 104 | S.S. Marea |

`WildBattleResultGet` = 4 es captura, como en todos los scripts de legendarios.

## Herramientas

- `scripts/pawn.py`: lee, escribe y ensambla scripts Pawn de GF (compresión de
  celdas, contenedor, reubicación por etiquetas, trasplante de rutinas entre
  scripts, publics). Prueba: los 1157 scripts retail (536 de zona, 536 de
  entidades, 85 compartidos) se reconstruyen byte a byte.
- `faraway/event.py`: textos y scripts del evento. El puerto y la isla se
  construyen **sobre los scripts retail** (317, 214, 215) añadiendo casos; los
  diálogos y el viaje usan rutinas trasplantadas del barquero (script compartido
  79) y la entrega de objetos la del script compartido 10.
- `faraway/java/faraway/Build.java` (CTRMap-F5): clona zonas con mapa y área
  propios, restaura texto, script y lugar del hueco, coloca NPC y warps.
- `faraway/build.py`: prepara la copia, compila, ejecuta Java y aplica textos,
  objeto y combate sobre los activos de v0.5 (`build_patch.patched_assets`).
- Laboratorio: `faraway/lab.sh`, `dev_overlay.sh` (warp de desarrollo en la Ruta
  102, nunca en una entrega), `gdbctl.sh`, `walk_to.py`, `save_event.py`.

## Errores encontrados y corregidos

- Los *publics* son direcciones de código: al ampliar un `CASETBL` se movían y
  el juego fallaba al cargar el puerto. Ahora se reubican.
- Un script nuevo desde cero (sin base retail) se colgaba al hablar; construido
  sobre el script retail del donante funciona. Causa exacta sin aislar.
- Girar un modelo de Pokémon hacia el jugador no termina nunca: Mew no gira
  (igual que Registeel en el juego).
- El registro de NPC necesita la entrada retail completa (colisión, sombra).
- Teletransportar una partida editando la Situación cuelga al cargar; para el
  laboratorio se usa un warp de desarrollo.

## Pendiente

- Fase 3: geometría definitiva (hierba alta, playa), ocultación en la hierba y
  escenas. Ya hay modelo real y persecución por cuatro huidas.
- Derrotar a Mew (no a la inversa) y quedar sin Pokémon; recarga con el mapa
  ya recibido; otros idiomas (ahora: español y, en el resto, inglés).
- Prueba del evento en consola y entrega final; ya hay paquete combinado
  preliminar para copiar a la SD de Luma.
