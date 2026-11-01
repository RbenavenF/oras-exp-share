#!/usr/bin/env python3
"""Local isolated Azahar/Xvfb test session; never uses a personal emulator profile."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import signal
import struct
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'work/azahar-lab'
RUNTIME = ROOT / 'work/azahar-runtime'


def environment(display=None):
    env = os.environ.copy()
    env.update(XDG_CONFIG_HOME=str(LAB / 'config'), XDG_DATA_HOME=str(LAB / 'data'),
               XDG_CACHE_HOME=str(LAB / 'cache'), XDG_RUNTIME_DIR=str(LAB / 'runtime'),
               LIBGL_ALWAYS_SOFTWARE='1', QT_QPA_PLATFORM='xcb')
    env['LD_LIBRARY_PATH'] = str(RUNTIME / 'x11/usr/lib/x86_64-linux-gnu')
    if display:
        env['DISPLAY'] = display
    return env


def prepare():
    for directory in ['config/azahar-emu', 'data/azahar-emu/load/mods', 'cache', 'runtime', 'framebuffer']:
        (LAB / directory).mkdir(parents=True, exist_ok=True)
    (LAB / 'runtime').chmod(0o700)
    rom = LAB / 'omega-ruby.cci'
    if not rom.exists():
        source = json.loads((ROOT / 'reports/source-lock.json').read_text())['rom']['path']
        shutil.copyfile(ROOT / source, rom)
    destination = LAB / 'data/azahar-emu/load/mods/000400000011C400'
    if not destination.exists():
        shutil.copytree(ROOT / 'dist/held-exp-share-v0.5/mods/000400000011C400', destination)
    config = LAB / 'config/azahar-emu/qt-config.ini'
    if not config.exists():
        config.write_text('[UI]\nfirst_start=false\ncheck_for_update_on_start=false\n'
                          'confirmClose=false\n[Renderer]\ngraphics_api=1\n'
                          'resolution_factor=1\n[Audio]\noutput_engine=null\n')


def start():
    prepare()
    state_file = LAB / 'session.json'
    if state_file.exists():
        raise RuntimeError('Session metadata exists; inspect/stop the current session first')
    read_fd, write_fd = os.pipe()
    try:
        with (LAB / 'xvfb.log').open('w') as log:
            server = subprocess.Popen([str(RUNTIME / 'x11/usr/bin/Xvfb'), '-displayfd', str(write_fd),
                                       '-screen', '0', '1200x900x24', '-nolisten', 'tcp',
                                       '-fbdir', str(LAB / 'framebuffer')],
                                      stdout=log, stderr=log, pass_fds=(write_fd,), start_new_session=True)
        os.close(write_fd)
        if not select.select([read_fd], [], [], 15)[0]:
            server.terminate()
            raise RuntimeError('Xvfb did not report a display')
        number = os.read(read_fd, 64).decode().strip()
        if not number.isdigit():
            raise RuntimeError('Xvfb failed; see its log')
    finally:
        os.close(read_fd)
    display = ':' + number
    with (LAB / 'azahar-console.log').open('w') as log:
        emulator = subprocess.Popen([str(RUNTIME / 'app/AppRun'), '-w', str(LAB / 'omega-ruby.cci')],
                                    env=environment(display), stdout=log, stderr=log, start_new_session=True)
    state = dict(display=display, xvfb_pid=server.pid, azahar_pid=emulator.pid,
                 pid_namespace=os.readlink('/proc/self/ns/pid'))
    state_file.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(state))


def screenshot():
    data = (LAB / 'framebuffer/Xvfb_screen0').read_bytes()
    header = struct.unpack_from('>25I', data)
    width, height, bpp, stride = header[4], header[5], header[11], header[12]
    if bpp != 32 or header[7] != 0 or header[14:17] != (0xFF0000, 0xFF00, 0xFF):
        raise ValueError('Unexpected Xvfb pixel format')
    offset = header[0] + header[19] * 12
    rows = bytearray()
    for y in range(height):
        row = data[offset + y * stride:offset + y * stride + width * 4]
        rgb = bytearray(width * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
        rows.extend(b'\0' + rgb)
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))
    path = LAB / 'screen.png'
    path.write_bytes(png)
    print(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'start', 'screenshot', 'input', 'stop'])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'start':
        start()
    elif args.action == 'screenshot':
        screenshot()
    else:
        state_file = LAB / 'session.json'
        state = json.loads(state_file.read_text())
        if args.action == 'input':
            subprocess.run([str(RUNTIME / 'x11/usr/bin/xdotool'), *args.arguments],
                           env=environment(state['display']), check=True)
        else:
            if state.get('pid_namespace', os.readlink('/proc/self/ns/pid')) != os.readlink('/proc/self/ns/pid'):
                raise RuntimeError('Stop must run in the same PID namespace as start (outside the sandbox)')
            for key in ['azahar_pid', 'xvfb_pid']:
                try:
                    command = Path(f'/proc/{state[key]}/cmdline').read_bytes()
                    if str(RUNTIME).encode() not in command:
                        raise RuntimeError(f'PID {state[key]} is not from this test session')
                    os.kill(state[key], signal.SIGTERM)
                except FileNotFoundError:
                    pass
            state_file.rename(LAB / 'last-session.json')


if __name__ == '__main__':
    main()
