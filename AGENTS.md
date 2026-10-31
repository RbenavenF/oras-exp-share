# ORAS: Repartir Exp. equipable para Repolished

## Objetivo
Crear un parche compatible con Omega Ruby Repolished para que el
Repartir Exp. beneficie a un Pokémon elegido, preferiblemente mediante
un objeto equipado. Priorizar una primera implementación funcional.

Prototipo inicial:
- Los participantes conservan su experiencia normal.
- El portador no participante recibe el 50 % calculado por el juego.
- Las demás reservas no reciben experiencia por reparto.
- No duplicar la recompensa si el portador participa.
- Respetar las condiciones de elegibilidad del juego.
- Documentar por separado qué sucede con los EV.

La selección por slot es una alternativa si el objeto equipable se atasca.
La entrega del objeto en la historia se implementa después del efecto.

## Base
- Juego base sin actualización: el autor de Repolished recomienda
  evitar las actualizaciones de ORAS.
- Paquete concreto del mod en inputs/repolished.
- Volcado del juego en inputs/game.
- Partida de prueba en inputs/save.
- No asumir que todos los cambios están en el ejecutable principal:
  investigar también módulos CRO y datos si corresponde.

## Herramientas
Ejecutar: source scripts/env.sh
- Ghidra 12.1.4, Java 21.
- GhidraMCP 2.0 descargado y extraído en tools/ghidra-mcp.
  Falta instalar la extensión y configurar el cliente MCP.
- Azahar 2126.2: scripts/azahar.sh
- Ghidra GUI: scripts/ghidra.sh
- ctrtool y 3dstool disponibles en PATH tras cargar env.sh.
- GDB multiarch, binutils ARM, Python, Capstone y pytest.
- Código de pk3DS en tools/pk3DS. Su GUI es Windows Forms.
- No hay cliente Codex instalado o configurado por este bootstrap.

## Trabajo
1. Inspeccionar los inputs e instrucciones de Repolished.
2. Extraer el juego y construir baseline con el mod aplicado.
3. Mapear el ejecutable usando el exheader; trabajar sobre copias.
4. Localizar reparto de experiencia y datos del objeto.
5. Introducir el objeto en una copia de la partida para probarlo.
6. Implementar el efecto y generar un parche reproducible.
7. Ajustar el evento de entrega y textos posteriormente.

## Criterios prácticos
- Avanzar de forma autónoma con cambios locales reversibles.
- No modificar inputs ni la partida original.
- Guardar notas breves: dirección/offset, bytes y motivo del cambio.
- Comprobar el hash y bytes de entrada en el generador del parche.
- IPS no valida por sí mismo la identidad del ejecutable.
- No inventar direcciones ni declarar pruebas de ejecución no realizadas.
- Probar portador en reserva, participante, debilitado y sin objeto.
- No instalar automáticamente el parche en la consola.
- No subir binarios comerciales, partidas o claves a Git.
- Primera entrega: scripts de generación, parche y explicación breve.
