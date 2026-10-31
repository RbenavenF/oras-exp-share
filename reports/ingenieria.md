# Notas de ingeniería — prototipo v0.4

## Identidad y base

- SHA-256 del volcado:
  `96aa3fe18a5c8cdb52f4f989712f1fa73da2bc8b3cf08e21762cf2d6a4e1d7ef`.
- `.code` limpio, descomprimido, 5 439 488 bytes:
  `d587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37`.
- `.code` con Repolished:
  `3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293`.

Hashes de todas las entradas y herramientas: `source-lock.json`.
Los 107 bytes escritos por el IPS del mod están detallados, con bytes anteriores
y posteriores, en `repolished-ips-records.json`. Sus offsets son `0x47AAE6`,
`0x47AB0C`, `0x47AB32` y `0x47ABA0`; todos caen en `.rodata`.
El prototipo de reparto no añade cambios a `.code`.

## Mapa del ejecutable

| Sección | Offset en code.bin | Dirección virtual | Tamaño real | Reserva por páginas |
| --- | --- | --- | --- | --- |
| text | `0x000000` | `0x00100000` | `0x479604` | `0x47A000` |
| rodata | `0x47A000` | `0x0057A000` | `0x071A14` | `0x072000` |
| data | `0x4EC000` | `0x005EC000` | `0x0439F4` | `0x044000` |
| bss | sin bytes | `0x0062F9F4` | `0x07EC2C` | incluida tras data |

`static.crs` confirma las bases y el tamaño data+bss `0xC2620`.
En este volcado los offsets de las tres secciones inicializadas se traducen
sumando `0x100000`; los scripts calculan la traducción por sección.

## Cadena que localizó el reparto

| Lugar | Evidencia |
| --- | --- |
| Objeto 216 | Archivo de nombres inglés, GARC `a/0/7/3`, entrada 114: `Exp. Share`. |
| `DllBag.cro + 0x2208` | Compara el ID con `0xD8`; consulta estado mediante thunk `0x378`. |
| Importación en `DllBag.cro + 0x37C` | `static.crs` la resuelve a VA `0x004E9F60`. |
| VA `0x004E9F60` | Lee el bit 3 de la palabra situada en `objeto_estado + 0x34`. |
| VA `0x003674D4` | Consulta posesión del objeto 216 y copia su estado al byte `+0x8C` de la configuración de combate. |
| `DllBattle.cro + 0x3263C` | Lee ese byte en la rama de no participantes. |
| `DllBattle.cro + 0x324D0` | Calcula EXP y el vector de EV de hasta seis destinatarios. |
| `DllBattle.cro + 0x31D28` | Aplica modificadores solo si la EXP del destinatario ya es distinta de cero. |

Los offsets CRO son **offsets de archivo**, no direcciones de ejecución.
Las direcciones `0x010xxxxx` del proyecto Ghidra usan una base sintética.
El análisis global de Ghidra quedó limitado a 180 s; hubo advertencias de
análisis automático fuera de estas funciones. Las pruebas ARM contrastan la
ruta usada sin depender del pseudocódigo para ejecutarla.

## Cambio de código

Especificación completa y hashes esperados: `held-exp-share-spec.json`.

En `DllBattle.cro + 0x32630`, se sustituyen 24 bytes:

```text
antes:   50009de5040090e5100090e58c00d0e5000050e30400000a
después: 040196e7b201d0e100f020e300f020e3d80050e30400001a
```

```asm
ldr   r0, [r6, r4, lsl #2]  ; Pokémon del slot actual
ldrh  r0, [r0, #0x12]       ; objeto equipado
nop
nop
cmp   r0, #0xD8            ; ID 216
bne   0x3265C             ; no portador: conserva EXP cero
```

La rama participante salta directamente a `0x3265C` con EXP normal y no ejecuta
la comprobación nueva. Antes de ambas ramas permanece la comprobación de HP
mediante el getter de estadística `0xD`, que devuelve `u16[Pokémon + 0x10]`.
La rama compartida existente conserva mitad, mínimo de un punto y marca de
reserva. No hay relocaciones sobre los 24 bytes modificados.

### Mensaje de EXP del portador (v0.4)

Cada destinatario tiene un registro de 0x14 bytes: `+0x11` marca reparto y
`+0x12` agrupa el mensaje. El cálculo inicializa `+0x12 = 1`; los llamadores
(`DllBattle+0x2573C` y `+0x6BEC8`) lo ponen a 0 solo si `+0x11 == 0`. El
despachador `+0x6A39C` muestra entonces el mensaje individual 0x2B/0x2C
(«X ha ganado N Puntos de Experiencia») o, si `+0x12` sigue a 1, el resumen
0x2D («El resto del equipo también ha ganado…»).

En `DllBattle.cro + 0x3264C`: `01c0a0e3` (`mov ip, #1`) → `00c0a0e3`
(`mov ip, #0`). El portador deja de marcarse como reparto y recibe su propio
mensaje; el resumen ya no aparece. `+0x11` no se lee en ningún otro punto
del cálculo, los llamadores ni el despachador. Sin relocaciones sobre esos bytes.

El efecto funciona con el interruptor original encendido o apagado y sin
consultar si el objeto está en la bolsa. Si hay varios portadores elegibles,
todos reciben reparto. No se ha añadido una limitación artificial de ejemplares.

## Datos del objeto

GARC `romfs/a/1/9/7`: 776 entradas de 36 bytes. La entrada 216 empieza en
`0x5B40` y es igual en la base limpia y en Repolished.
Se cambia `0x5B48: 7f 02 05` por `1f 00 00`:

- Bolsillo 4 → 0 (Objetos).
- Bits 5 y 6 del campo empaquetado → 0.
- Efecto de uso de campo 5 → 0 (elimina el uso de activar/desactivar).

El getter ARM `0x004D3A88`, campos 9/10/11/13, devuelve respectivamente
`1/1/4/5` antes y `0/0/0/0` después. El control por ID `0x003B6F30` permite
216. La rama de menú en `DllBag.cro + 0x2258` ofrece Dar al superar esos controles;
su funcionamiento completo en interfaz aún no se ha probado.
El precio, nombre, descripción e icono permanecen como en Repolished. La
descripción antigua todavía habla del reparto global: habrá que corregirla.

## EV, por separado

La misma rutina calcula los EV después de seleccionar destinatarios de EXP:

- Participantes elegibles: vector de EV original.
- Portador elegible en reserva: **vector de EV completo**, no el 50 %.
- Reservas no portadoras y Pokémon con HP cero: vector de EV cero.
- Permanecen los cálculos originales de Brazal Firme, objetos recios y Pokérus.
  Un portador de Repartir Exp. no puede llevar además otro objeto.

Se ejecutó esa parte de la rutina en Unicorn: un EV de HP de la especie
derrotada produce uno tanto para participante como para portador; Pokérus
produce dos para el portador. También se ejecutaron el despachador posterior
`DllBattle+0x6A39C` y la actualización de EV `+0x76760`: se respetan 252 por
estadística y 510 en total, incluido el caso de ganancia parcialmente limitada.
Al nivel 100 no se despacha EXP, pero sí se conservan los EV.

Los getters originales de huevo (`main 0x4D23F4`) y huevo inválido
(`0x4D17F0`), llamados a través de `0x4D2E28`, excluyen ambos casos. Las pruebas
usan bloques descifrados simulados y sustituyen los auxiliares de cifrado.
La función final de EXP `DllBattle+0x78834` se sustituye por un registro de
llamadas: todavía no se verifica la escritura de EXP, la subida de nivel ni
la persistencia de EV en la partida. No se cambian esas funciones posteriores.

## Integridad del módulo y distribución

Se recalculan las cuatro ranuras SHA-256 del CRO y se sustituye su digest en
la tabla ordenada de `romfs/.crr/static.crr` (145 entradas). La firma RSA de
CRR permanece original: su aceptación por el cargador sigue pendiente de prueba.

El paquete local incluye todas las sustituciones de Repolished, su `code.ips`
sin cambios y los tres archivos modificados por este prototipo. Las diferencias
IPS por archivo tienen ida y vuelta comprobada contra los binarios generados.
Los datos completos permanecen en carpetas ignoradas por Git.

## Referencias de formatos

- Implementación local de pk3DS, commit
  `6daaca934ca2284a73ab743bf89c848c57cd9de1`: `GARC.cs`, `GARCReference.cs`,
  `Item6.cs`, `TextFile.cs`, `TextReference.cs` y `CRO.cs`.
- [Formato CRO y relocaciones en 3dbrew](https://www.3dbrew.org/wiki/CRO0),
  contrastado con tablas del volcado y comprobaciones de hashes locales.
