#!/usr/bin/env python3
"""Lab only: tile the 3DS screens (top 400x240 at 400,225; bottom 320x240 at 440,465) of Azahar screenshots
into one PNG, two per row. Usage: montage.py OUT.png IN.png... [--top-only]"""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lab_factory import Png  # noqa: E402


def crop(path, top_only):
    img = Png(path)
    rows = []
    for y in range(225, 465 if top_only else 705):
        r = img.row(y)
        x0, x1 = (400, 800) if y < 465 else (440, 760)
        line = bytearray()
        for x in range(x0, x1):
            line += r[x * img.bpp:x * img.bpp + 3]
        line += bytes(3 * (400 - (x1 - x0)))
        rows.append(bytes(line))
    return rows


def main():
    args = [a for a in sys.argv[1:] if a != '--top-only']
    top_only = '--top-only' in sys.argv
    out, paths = args[0], args[1:]
    tiles = [crop(p, top_only) for p in paths]
    h = len(tiles[0])
    cols = 2
    raw = bytearray()
    for start in range(0, len(tiles), cols):
        group = tiles[start:start + cols] + [[bytes(1200)] * h] * (cols - len(tiles[start:start + cols]))
        for y in range(h):
            raw += b'\0' + b''.join(t[y] + bytes(12) for t in group)
    width = cols * 404

    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))
    height = h * ((len(tiles) + cols - 1) // cols)
    Path(out).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                          + chunk(b'IDAT', zlib.compress(bytes(raw))) + chunk(b'IEND', b''))


if __name__ == '__main__':
    main()
