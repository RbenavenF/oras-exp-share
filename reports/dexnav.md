# DexNav: racha visible (v0.5)

La casilla del nivel de búsqueda del DexNav muestra `nivel/racha`, con la
etiqueta «Nivel / Racha» (inglés: «Level / Chain»). Aparece en la ficha
del Pokémon y durante la búsqueda. Base: Repolished 1.7.6 sin actualización;
`DllField.cro` es idéntico al del juego original.

Direcciones de `DllField.cro` como desplazamiento de archivo. En el mapa de
análisis (`0x01000000 + desplazamiento`) se escriben como `0x010xxxxx`.
En Azahar, el módulo se cargó en `0x006F3000`.

## Dónde está la racha

- `code.bin:0x4E4770` devuelve `obj + 4`; la racha es un u32 en `obj + 0xA8`.
- La tirada variocolor del DexNav (`+0xE5680`) recibe la racha en `r1`
  (+5 tiradas si la racha+1 es 50, +10 si es 100) y el nivel de búsqueda en `r2`.
- `code.bin:0x402590` la incrementa (de 99 vuelve a 0). La llama
  `DllFieldEventContactEncount.cro` al tocar al Pokémon oculto si el estado
  `[+0x1D0]` es 1 o 5; con otro estado llama a `code.bin:0x4025E4`, que la pone a 0.
- `DllField +0x98890` también la pone a 0. En Azahar coincidió con
  «¡Se ha escapado!».
- La interfaz llega al objeto así: `[[[ui+0xE8]+0x1D4]]`. Es el mismo camino que
  usa el juego para empezar una búsqueda (`+0xAF05C` → `+0x986D0`).
- Nivel de búsqueda: partida `0x15684 + 2·especie` (u16). Lo lee
  `code.bin:0x4EB910`, con tope 999.

## Cambio

| Archivo | Desplazamiento | Antes → después | Motivo |
| --- | --- | --- | --- |
| `DllField.cro` | `0xAFC74` | `bl SetPaneNumber` → `bl 0xF0400` | Casilla del nivel de búsqueda |
| `DllField.cro` | `0xF0400`, 108 B | ceros → rutina | Relleno libre tras el segmento de código, dentro de la región de código con hash |
| `a/0/7/1`–`8` | entrada 84, línea 69 (nueva) | `[VAR 0202 0]/[VAR 0202 1]` | Formato «nivel/racha» |
| `a/0/7/1`–`8` | entrada 84, línea 70 (nueva) | ES «Nivel / Racha», EN «Level / Chain», resto: su etiqueta original | Etiqueta |

La rutina:
1. Pone la etiqueta (línea 70) en el panel 41.
2. Lee la racha; si algún puntero es nulo, usa 0.
3. La registra como número 1 (2 cifras).
4. Llama a `SetPaneNumber` original con la línea 69.

El mensaje 21 no se toca: también lo usa el panel 49. Las entradas de texto
crecen: el generador reconstruye el GARC (`rebuild_garc`). Reconstruir sin
cambios da el mismo archivo byte a byte en los 18 GARC de texto. Se
recalculan los hashes de `DllField.cro` y su entrada en `static.crr`.

## Pruebas (Azahar 2126.2, partida convertida del usuario, GDB)

- Racha 0: «Nivel / Racha 22/0». Racha 7 escrita por GDB en la dirección que
  usa la rutina: «22/7» en la ficha y en la búsqueda («Pokémon ocultos»).
- La tirada recibió `r1 = 7` con esa misma dirección a 7: es la racha que usa el juego.
- El Pokémon escapó: la racha pasó de 7 a 0 y la ficha de Lotad mostró «3/0».
- Capturas en `work/v05-test/`.

Sin probar:
- Un incremento real acercándose con sigilo (en Azahar solo se probó el
  reinicio y el valor escrito con GDB).
- La consola por nuestra parte; el usuario indica que funciona en la suya.

El relleno usado está en la misma página que el final del código y dentro de
la región de código del CRO. En Azahar se ejecuta; en consola queda por confirmar.
