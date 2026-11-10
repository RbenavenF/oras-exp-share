Sondas de laboratorio de F6-PIRAMIDE-V2A, evidencia en reports/frontier.md §34.
No forman parte de la build. Ejecutar `source scripts/env.sh` primero.

- `python frontier/probes/pyramid/lab_probe.py > work/frontier/pyramid/v2/probe.gdb`:
  emite direcciones desde los símbolos actuales de `patch.assemble()`.
  Cargar con `gdbctl.sh halt`, `cmd 'source ...'`, `run`.
- `pv_mode='normal'`: solo observa. `'win'`: HP 1 y Salpicadura a las copias
  servidor/cliente del rival; `'loss'`: lo mismo a los Pokémon del jugador.
  Escribe RAM de combate, no works, resultados, PB ni partida.
- `fight.sh`: pulsa A hasta que IsWin se observe, con tope de 110 pulsaciones.
- `climb.sh`: desde llegada (12,16), recorre tres entrenadores y encargado
  de los siete pisos; `FIRST` para empezar más arriba. `SKIP0=1` desde (8,11)
  tras verificar al entrenador 0 vencido del piso 1.
- `audit_round.py`: comprueba los 21 IsWin y las siete transiciones de los logs
  conservados de §34. La primera victoria se hizo antes de reiniciar el juego.
- `save.sh NOMBRE`: desde el campo, sin diálogo; rechaza un archivo sin cambios.
  Revisar siempre captura y JSON antes de usar el snapshot como evidencia.
- `walk_to.py`: aborta ante respuesta vacía del FIFO GDB o colisión. No ejecutar
  dos conductores simultáneamente. En la plaza hubo respuestas vacías persistentes:
  la exclusión inversa se terminó con teclas y capturas, sin teletransportar.

Azahar, GDB y conductores deben ejecutarse en una única shell persistente:
las llamadas exec independientes tienen namespaces PID distintos. Parar GDB y
Azahar en esa misma shell y restaurar use_gdbstub=false al terminar.
