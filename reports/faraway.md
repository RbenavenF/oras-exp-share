# Mapa Viejo e Isla Suprema — estado (fase 2)

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

- Fase 3: modelo de campo de Mew (no existe en ORAS), escondite y persecución
  en hierba alta, geometría definitiva (hierba alta, playa), escenas.
- Derrotar a Mew (no a la inversa) y quedar sin Pokémon; recarga con el mapa
  ya recibido; otros idiomas (ahora: español y, en el resto, inglés).
- Paquete final combinado e instalador; prueba en consola.
