#!/usr/bin/env python3
"""Laboratory: stack the top screens of several lab screenshots into one PNG (for quick review)."""
import struct
import sys
import zlib


def read_png(path):
    data = open(path, 'rb').read()
    pos, idat, width = 8, b'', 0
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height = struct.unpack('>II', body[:8])
        if kind == b'IDAT':
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 3 + 1
    return [raw[y * stride + 1:(y + 1) * stride] for y in range(height)]


def main():
    out, files = sys.argv[1], sys.argv[2:]
    rows = []
    for name in files:
        rows += [row[400 * 3:800 * 3] for row in read_png(name)[225:465]]
    raw = b''.join(b'\0' + row for row in rows)
    chunk = lambda kind, body: struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    with open(out, 'wb') as stream:
        stream.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 400, len(rows), 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    main()
