# ORAS Repolished · Frente de Batalla

Proyecto de modding para **Pokémon Rubí Omega + Repolished 1.7.6**: recuperar el
Frente de Batalla de Esmeralda en ORAS, junto con un Repartir Exp. equipable y la
racha visible en el DexNav. Incluye generadores, herramientas de análisis,
pruebas automatizadas y un orquestador de trabajo con Claude Code y Codex.

**Está en desarrollo.** Las siete instalaciones tienen versiones jugables, pero
sus reglas, interiores y aspecto visual aún no están completos. Este repositorio
contiene código y documentación; los paquetes instalables se generan localmente.

## Estado del proyecto

Foto del estado a 15 de noviembre de 2026. La fuente de trabajo actual es la
[cola del orquestador](frontier/orch/tasks.json) y la
[bitácora](frontier/BITACORA.md), con evidencias y límites de cada hito.

| Área | Estado |
| --- | --- |
| Repartir Exp. equipable y DexNav | Entregados en v0.5; probados en Azahar y 3DS. |
| Isla del Frente | Alfa v0.3 con distribución basada en Esmeralda, siete accesos y ferry. Probada por el usuario; materiales, cámara, paisaje y edificios necesitan mucho pulido. |
| Siete instalaciones | Fábrica, Torre, Palacio, Arena, Domo, Tubo y Pirámide con flujos jugables por etapas. No todas reproducen todavía las reglas completas de Esmeralda. |
| Cerebros y símbolos | Implementados para las siete instalaciones; aceptación y pruebas documentadas por tarea. |
| Nivel Libre | Cerrado en la cola para las seis instalaciones de equipo propio; Fábrica con alquileres a nivel 100 en curso. |
| Dobles | Pendiente en Torre y Fábrica. |
| Interiores y exteriores propios | En cola; todavía se reutilizan salas y edificios de ORAS. |
| Evento de Mew | Investigación pausada; excluido de las alfas del Frente. |

Las alfas v0.2 y v0.3 han sido probadas por el usuario en 3DS. Esa confirmación
no sustituye una matriz completa de pruebas de todas las modalidades. Los informes
separan pruebas estáticas, ejecución en Azahar y pruebas en consola.

La prioridad visual es conservar la distribución y escala esperables de Esmeralda
y mejorar el acabado con recursos de ORAS. La referencia está en
[reports/diseno/referencias/frente-esmeralda.webp](reports/diseno/referencias/frente-esmeralda.webp).
El trazado ya está incorporado; el acabado del paisaje tiene una tarea bloqueada
y la revisión de materiales y cámara sigue pendiente.

## Orientarse en el repositorio

- [frontier/PLAN.md](frontier/PLAN.md): objetivos y etapas del Frente.
- [frontier/REPARTO.md](frontier/REPARTO.md): turno, instalaciones y reservas de recursos.
- [frontier/BITACORA.md](frontier/BITACORA.md): avances, decisiones y siguiente paso.
- [frontier/orch/README.md](frontier/orch/README.md): supervisor, carriles y política de pruebas.
- [reports/frontier.md](reports/frontier.md): investigación técnica y evidencia del Frente.
- [reports/diseno/](reports/diseno/): diseños de instalaciones y aspectos visuales.
- [reports/ingenieria.md](reports/ingenieria.md) y [reports/dexnav.md](reports/dexnav.md): Repartir Exp. y DexNav.
- `frontier/`, `scripts/`, `faraway/` y `tests/`: implementación, utilidades y pruebas.

## Orquestador y visor web

`frontier-orch` asigna la cola a Claude Code y Codex, registra avances y esperas por
cuota, valida tareas y permite trabajar en carriles con worktrees y laboratorios
separados. Consulta su documentación antes de arrancarlo: **ejecutar workers consume
cuota de los proveedores**.

```bash
frontier/orch/frontier-orch status
```

El **Observatorio** es un visor web local de solo lectura: cola, dependencias,
workers, actividad reciente, esperas por cuota y herramientas. Se actualiza cada
3 segundos; muestra la espera registrada, no el saldo real del proveedor.

Por ahora vive en la rama
[feature/orch-viewer](https://github.com/RbenavenF/oras-exp-share/tree/feature/orch-viewer),
sin integrar en `main`. Para abrirlo desde un clon de esa rama, con Python 3.10+:

```bash
python3 frontier/orch/viewer/server.py --root "$PWD" --host 127.0.0.1
```

Abre <http://127.0.0.1:8787>. Lee el checkout indicado por `--root` y necesita sus
datos locales para mostrar actividad real. Sin `--host`, escucha en todas las
interfaces para permitir acceso desde la red local. No incluye autenticación;
no debe exponerse directamente a Internet. Detalles en el
[README del visor](https://github.com/RbenavenF/oras-exp-share/blob/feature/orch-viewer/frontier/orch/viewer/README.md).

## Entorno y generación local

Se requiere un volcado propio de Rubí Omega **sin actualización**, el paquete
Repolished 1.7.6 y las herramientas de desarrollo. Las entradas concretas se
identifican mediante hashes en [reports/source-lock.json](reports/source-lock.json).
No se incluyen ROM, claves, partidas ni archivos comerciales generados.

El entorno de trabajo utiliza Python, herramientas ARM y de extracción 3DS,
Azahar/GDB para pruebas, Ghidra para análisis y herramientas basadas en CTRMap para
recursos de mapas. Las rutas y dependencias locales se configuran en
[scripts/env.sh](scripts/env.sh); clonar el repositorio no instala esos programas.

Con los inputs y herramientas preparados, el flujo de Repartir Exp./DexNav es:

```bash
source scripts/env.sh
python scripts/prepare_baseline.py
python scripts/analyze_assets.py
pytest -q
python scripts/validate_arm.py
python scripts/build_patch.py
```

Para una base ya creada: `python scripts/prepare_baseline.py --verify-only`.
Los generadores de este flujo rechazan destinos existentes; usa `--output` para
crear otra copia. La validación de combates de v0.5 requiere las partidas locales
de laboratorio (`scripts/validate_gameplay.py`).

El Frente tiene su propio generador de overlay:

```bash
python frontier/overlay.py --out work/frontier/build-local
```

Ese comando produce una build de trabajo; no equivale a una alfa aceptada. Los
paquetes exactos, sus hashes y las regresiones de cada alfa se documentan en la
bitácora y la cola. Nada se instala automáticamente en la consola.

## Repartir Exp. y DexNav (v0.5)

El objeto 216, Repartir Exp., pasa al bolsillo Objetos y se puede equipar. Los
participantes conservan su experiencia; un portador en reserva recibe el 50 %
calculado por el juego, con sus modificadores y redondeo. Las demás reservas no
reciben experiencia por reparto, y participar no duplica la recompensa del portador.
El efecto deja de depender del interruptor global. Los EV se documentan por separado
en las notas de ingeniería.

Se conservan la entrega original del objeto y los textos adaptados de las versiones
anteriores. v0.5 añade «Nivel / Racha» al DexNav. Las partidas que todavía tienen el
objeto en Objetos clave requieren la conversión descrita en
[reports/laboratorio.md](reports/laboratorio.md).

## Trabajo y publicación

Antes de modificar el proyecto, lee [AGENTS.md](AGENTS.md), PLAN, REPARTO y las
últimas entradas de la bitácora. El supervisor conserva el turno mientras trabaja;
las intervenciones paralelas se hacen en checkouts aislados según esas normas.

`inputs/`, `work/`, `dist/`, herramientas descargadas, ROM, claves y partidas se
mantienen fuera de Git. Los parches se construyen con comprobaciones de hash y
bytes de entrada; un IPS por sí solo no valida la versión del juego. Las capturas
y referencias documentales no constituyen un paquete del juego.
