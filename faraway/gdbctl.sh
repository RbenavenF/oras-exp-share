#!/usr/bin/env bash
# Laboratory GDB control for the Azahar stub: a persistent gdb-multiarch fed through a FIFO.
#   gdbctl.sh start            connect (the stub halts the game), then let it run
#   gdbctl.sh halt             pause the game (SIGINT to gdb)
#   gdbctl.sh run              resume
#   gdbctl.sh cmd "GDB CMD"    run a command while halted; prints its output
#   gdbctl.sh stop             quit gdb (the emulator closes when the debugger leaves)
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/work/faraway/gdb"   # per checkout: each frontier-orch lane has its own
PORT_FILE="$(dirname "$D")/../lab-port"; PORT=${ORAS_GDB_PORT:-$(cat "$PORT_FILE" 2>/dev/null || echo 24689)}
mkdir -p "$D"
send() { timeout 5 bash -c 'printf "%s\n" "$2" > "$1"' bash "$D/in" "$*"; }
wait_quiet() { local n=0 last=-1; while true; do local s; s=$(stat -c %s "$D/out.log"); [ "$s" = "$last" ] && n=$((n+1)) || n=0; last=$s; [ $n -ge ${1:-3} ] && break; sleep 0.2; done; }
case "$1" in
  start)
    rm -f "$D/in"; mkfifo "$D/in"; : > "$D/out.log"
    # gdb reads the FIFO through a read-write descriptor, so it never sees end of file.
    nohup setsid bash -c "exec 3<>\"$D/in\"; exec gdb-multiarch -q -nx <&3 > \"$D/out.log\" 2>&1" >/dev/null 2>&1 &
    echo $! > "$D/gdb.pid"; sleep 1
    send "set pagination off"; send "set confirm off"; send "set width 0"
    send "set architecture arm"
    send "target remote 127.0.0.1:$PORT"
    # wait for the stub to answer (it stops the game): 2 s were not enough with two labs at once (2026-11-11)
    for _ in $(seq 1 60); do grep -qE 'in \?\? \(\)|could not connect|Connection (refused|timed out)' "$D/out.log" && break; sleep 0.5; done
    send "continue"; sleep 1; tail -5 "$D/out.log";;
  halt) kill -INT "$(cat "$D/gdb.pid")"; sleep 0.5; wait_quiet 3;;
  run) send "continue"; sleep 0.3;;
  cmd) shift; start=$(stat -c %s "$D/out.log"); send "$*"; sleep 0.3; wait_quiet 4; tail -c +$((start+1)) "$D/out.log";;
  stop) send "quit" || true; sleep 1; kill "$(cat "$D/gdb.pid")" 2>/dev/null || true;;
esac
