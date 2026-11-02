#!/usr/bin/env python3
"""Laboratory helper (Azahar, faraway/lab.sh running, player facing the Maison receptionist): press A until
the reception menu is on screen (white box at 700,300 of scripts/azahar_lab.py's screenshot), move to
«Battle Factory» (fourth entry, key G = down in the lab profile), press A, wait and take a screenshot.
Keys sent before the menu opens would pick «Combatir» instead (seen in the F4 tests).

Usage: python frontier/lab_factory.py
"""
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path


class Png:
    """Minimal 8-bit RGB/RGBA PNG reader (rows decoded up to the one asked for)."""
    def __init__(self, path):
        data = open(path, 'rb').read()
        pos, idat = 8, b''
        while pos < len(data):
            n, kind = struct.unpack_from('>I4s', data, pos)
            body = data[pos + 8:pos + 8 + n]
            if kind == b'IHDR':
                self.w, self.h, depth, color = struct.unpack_from('>IIBB', body)
                self.bpp = {2: 3, 6: 4}[color]
            elif kind == b'IDAT':
                idat += body
            pos += 12 + n
        self.raw, self.rows = zlib.decompress(idat), []

    def row(self, y):
        stride = self.w * self.bpp
        while len(self.rows) <= y:
            i = len(self.rows)
            f, line = self.raw[i * (stride + 1)], bytearray(self.raw[i * (stride + 1) + 1:(i + 1) * (stride + 1)])
            prev = self.rows[-1] if self.rows else bytearray(stride)
            b = self.bpp
            for x in range(stride):
                a = line[x - b] if x >= b else 0
                up = prev[x]
                c = prev[x - b] if x >= b else 0
                if f == 1: line[x] = (line[x] + a) & 255
                elif f == 2: line[x] = (line[x] + up) & 255
                elif f == 3: line[x] = (line[x] + (a + up) // 2) & 255
                elif f == 4:
                    pa, pb, pc = abs(up - c), abs(a - c), abs(a + up - 2 * c)
                    line[x] = (line[x] + (a if pa <= pb and pa <= pc else up if pb <= pc else c)) & 255
            self.rows.append(line)
        return self.rows[y]

    def getpixel(self, xy):
        x, y = xy
        r = self.row(y)
        return tuple(r[x * self.bpp:x * self.bpp + 3])


class Image:
    @staticmethod
    def open(path):
        return Png(path)
ROOT = str(Path(__file__).resolve().parents[1])
def shot():
    subprocess.run(['python', 'scripts/azahar_lab.py', 'screenshot'], cwd=ROOT, check=True, capture_output=True)
    return Image.open(f'{ROOT}/work/azahar-lab/screen.png')
def key(k):
    subprocess.run(['python', 'scripts/azahar_lab.py', 'input', 'key', '--delay', '100', k], cwd=ROOT, check=True,
                   capture_output=True)
def menu_open(img):
    return all(min(img.getpixel((x, y))) > 225 for x, y in ((700, 300), (760, 300), (700, 260)))
def main():
    for attempt in range(40):
        img = shot()
        if menu_open(img):
            break
        key('a')            # advance the greeting / talk
        time.sleep(2.5)
    else:
        sys.exit('menu never opened')
    for k in 'ggg':
        key(k); time.sleep(0.5)
    shot(); subprocess.run(['cp', f'{ROOT}/work/azahar-lab/screen.png', f'{ROOT}/work/frontier/lab/menu_before_a.png'])
    key('a')
    time.sleep(4)
    shot()
    print('selected after', attempt, 'tries')


if __name__ == '__main__':
    main()
