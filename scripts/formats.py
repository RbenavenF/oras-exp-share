"""Small, strict readers for the formats used by this project."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_file(path, expected):
    path = Path(path)
    if path.stat().st_size != expected['size'] or sha256(path) != expected['sha256']:
        raise ValueError(f'Input identity mismatch: {path}')


@dataclass(frozen=True)
class IPSRecord:
    offset: int
    data: bytes


def read_ips(data):
    """Read normal and RLE records; reject ambiguous/truncated input."""
    if data[:5] != b'PATCH':
        raise ValueError('Missing IPS signature')
    records, pos = [], 5
    while True:
        if data[pos:pos + 3] == b'EOF':
            tail = data[pos + 3:]
            if tail:
                raise ValueError('IPS resize/trailing data is not supported')
            return records
        if pos + 5 > len(data):
            raise ValueError('Truncated IPS record or missing EOF')
        offset = int.from_bytes(data[pos:pos + 3], 'big')
        size = int.from_bytes(data[pos + 3:pos + 5], 'big')
        pos += 5
        if size:
            if pos + size > len(data):
                raise ValueError('Truncated IPS payload')
            payload = data[pos:pos + size]
            pos += size
        else:
            if pos + 3 > len(data):
                raise ValueError('Truncated IPS RLE payload')
            size = int.from_bytes(data[pos:pos + 2], 'big')
            if not size:
                raise ValueError('Empty IPS RLE record')
            payload = bytes([data[pos + 2]]) * size
            pos += 3
        records.append(IPSRecord(offset, payload))


def apply_ips(original, records):
    """Apply records; a record may extend the file only if it starts within it."""
    patched = bytearray(original)
    occupied = set()
    for record in records:
        end = record.offset + len(record.data)
        if record.offset > len(patched):
            raise ValueError('IPS record outside input file')
        if end > len(patched):
            patched.extend(bytes(end - len(patched)))
        positions = set(range(record.offset, end))
        if occupied & positions:
            raise ValueError('Overlapping IPS records')
        occupied.update(positions)
        patched[record.offset:end] = record.data
    return bytes(patched)


def code_map(exheader, code_size):
    segments, offset = [], 0
    for name, header_offset in [('text', 0x10), ('rodata', 0x20), ('data', 0x30)]:
        address, pages, size = struct.unpack_from('<III', exheader, header_offset)
        if size > pages * 0x1000:
            raise ValueError(f'Invalid segment size: {name}')
        segments.append(dict(name=name, address=address, size=size,
                             mapped_size=pages * 0x1000, file_offset=offset))
        offset += pages * 0x1000
    if offset != code_size:
        raise ValueError(f'Code length {code_size:#x} differs from exheader {offset:#x}')
    bss_size = struct.unpack_from('<I', exheader, 0x3C)[0]
    # BSS starts after the actual initialized data, before its final page padding.
    segments.append(dict(name='bss', address=segments[-1]['address'] + segments[-1]['size'],
                         size=bss_size, file_offset=None))
    return segments


def file_to_va(offset, segments):
    for segment in segments:
        start = segment['file_offset']
        if start is not None and start <= offset < start + segment['mapped_size']:
            return segment['address'] + offset - start
    raise ValueError(f'Unmapped file offset {offset:#x}')


def garc_entries(data):
    """Return (entry, subentry, absolute offset, length) for uncompressed GARC."""
    if data[:4] != b'CRAG':
        raise ValueError('Not a GARC')
    u32 = lambda offset: struct.unpack_from('<I', data, offset)[0]
    header, content, total = u32(4), u32(0x10), u32(0x14)
    if total != len(data):
        raise ValueError('GARC size mismatch')
    fato = header
    if data[fato:fato + 4] != b'OTAF':
        raise ValueError('Missing FATO')
    count = struct.unpack_from('<H', data, fato + 8)[0]
    fatb = fato + u32(fato + 4)
    if data[fatb:fatb + 4] != b'BTAF':
        raise ValueError('Missing FATB')
    result = []
    for entry in range(count):
        pos = fatb + 12 + u32(fato + 12 + entry * 4)
        mask = u32(pos)
        pos += 4
        for subentry in range(32):
            if not mask & (1 << subentry):
                continue
            start, end, length = struct.unpack_from('<III', data, pos)
            pos += 12
            if not start <= start + length <= end <= len(data) - content:
                raise ValueError('Invalid GARC extent')
            result.append((entry, subentry, content + start, length))
    return result



def rebuild_garc(data, replacements):
    """Rebuild a contiguous, unpadded GARC v4 with {(entry, subentry): bytes} replaced."""
    if data[:4] != b'CRAG' or struct.unpack_from('<HH', data, 0xA) != (0x400, 4):
        raise ValueError('Only GARC v4 is supported')
    entries = garc_entries(data)
    content = struct.unpack_from('<I', data, 0x10)[0]
    position = content
    for _, _, offset, length in entries:
        if offset != position:
            raise ValueError('GARC entries are not contiguous')
        position += length
    if position != len(data):
        raise ValueError('Unexpected data after GARC entries')
    unknown = set(replacements) - {(entry, sub) for entry, sub, _, _ in entries}
    if unknown:
        raise ValueError(f'Unknown GARC entries: {sorted(unknown)}')
    header = bytearray(data[:content])
    fato = struct.unpack_from('<I', data, 4)[0]
    fatb = fato + struct.unpack_from('<I', data, fato + 4)[0]
    fimb = fatb + struct.unpack_from('<I', data, fatb + 4)[0]
    if data[fimb:fimb + 4] != b'BMIF' or fimb + 12 != content:
        raise ValueError('Unexpected FIMB layout')
    body, records, index = bytearray(), [], 0
    for entry in range(struct.unpack_from('<H', data, fato + 8)[0]):
        pos = fatb + 12 + struct.unpack_from('<I', data, fato + 12 + entry * 4)[0]
        mask = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        for sub in range(32):
            if mask & (1 << sub):
                _, _, offset, length = entries[index]
                blob = replacements.get((entry, sub), data[offset:offset + length])
                struct.pack_into('<III', header, pos, len(body), len(body) + len(blob), len(blob))
                body += blob
                records.append(len(blob))
                pos += 12
                index += 1
    struct.pack_into('<I', header, fimb + 8, len(body))
    struct.pack_into('<II', header, 0x14, content + len(body), max(records))
    result = bytes(header + body)
    garc_entries(result)
    return result

def lz11_decompress(data):
    """Nintendo LZ11 (header byte 0x11), as used for the zone GARC entries."""
    if data[0] != 0x11:
        raise ValueError('Not LZ11')
    size, pos = int.from_bytes(data[1:4], 'little'), 4
    if size == 0:
        size, pos = int.from_bytes(data[4:8], 'little'), 8
    out = bytearray()
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not flags >> bit & 1:
                out.append(data[pos])
                pos += 1
                continue
            first = data[pos]
            indicator = first >> 4
            if indicator == 0:
                length = (((first & 0xF) << 4) | (data[pos + 1] >> 4)) + 0x11
                disp = ((data[pos + 1] & 0xF) << 8 | data[pos + 2]) + 1
                pos += 3
            elif indicator == 1:
                length = (((first & 0xF) << 12) | (data[pos + 1] << 4) | (data[pos + 2] >> 4)) + 0x111
                disp = ((data[pos + 2] & 0xF) << 8 | data[pos + 3]) + 1
                pos += 4
            else:
                length = indicator + 1
                disp = ((first & 0xF) << 8 | data[pos + 1]) + 1
                pos += 2
            if disp > len(out):
                raise ValueError('LZ11 back-reference before start')
            for _ in range(length):
                out.append(out[-disp])
    if len(out) != size:
        raise ValueError('LZ11 size mismatch')
    return bytes(out)


def lz11_compress(data):
    """Greedy LZ11 encoder; output is valid LZ11, not byte-identical to Nintendo's."""
    out = bytearray(b'\x11' + len(data).to_bytes(3, 'little') if len(data) < 1 << 24 else b'\x11\0\0\0' + len(data).to_bytes(4, 'little'))
    pos, index = 0, {}
    while pos < len(data):
        flag_at, flags = len(out), 0
        out.append(0)
        for bit in range(7, -1, -1):
            if pos >= len(data):
                break
            best_len = best_disp = 0
            key = data[pos:pos + 3]
            for start in reversed(index.get(key, [])[-64:]):
                disp = pos - start
                if disp > 0x1000:
                    break
                length = 0
                while length < 0x10110 and pos + length < len(data) and data[start + length] == data[pos + length]:
                    length += 1
                if length > best_len:
                    best_len, best_disp = length, disp
            step = best_len if best_len >= 3 else 1
            for k in range(pos, pos + step):
                index.setdefault(data[k:k + 3], []).append(k)
            if best_len < 3:
                out.append(data[pos])
            else:
                flags |= 1 << bit
                d = best_disp - 1
                if best_len <= 0x10:
                    out += bytes([((best_len - 1) << 4) | d >> 8, d & 0xFF])
                elif best_len <= 0x110:
                    n = best_len - 0x11
                    out += bytes([n >> 4, (n & 0xF) << 4 | d >> 8, d & 0xFF])
                else:
                    n = best_len - 0x111
                    out += bytes([0x10 | n >> 12, (n >> 4) & 0xFF, (n & 0xF) << 4 | d >> 8, d & 0xFF])
            pos += step
        out[flag_at] = flags
    return bytes(out)


def zo_files(data):
    """Split a "ZO" zone container into its subfiles."""
    if data[:2] != b'ZO':
        raise ValueError('Not a ZO container')
    count = struct.unpack_from('<H', data, 2)[0]
    offsets = struct.unpack_from(f'<{count + 1}I', data, 4)
    return [data[a:b] for a, b in zip(offsets, offsets[1:])]


def zo_build(files):
    header = 4 + 4 * (len(files) + 1)
    offsets, body = [], bytearray()
    for blob in files:
        offsets.append(header + len(body))
        body += blob
    offsets.append(header + len(body))
    return b'ZO' + struct.pack(f'<H{len(offsets)}I', len(files), *offsets) + body


# Gen 6 text files (pk3DS TextFile.cs): one section, per-line XOR stream.
TEXT_KEY_BASE, TEXT_KEY_ADVANCE = 0x7C89, 0x2983


def _crypt_line(words, key):
    result = []
    for word in words:
        result.append(word ^ key)
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return result


def text_lines(blob):
    """Return (lines, flags): decrypted u16 words per line, incl. terminator."""
    sections, count, total, initial, sdo = struct.unpack_from('<HHIII', blob, 0)
    if sections != 1 or initial != 0 or sdo + total != len(blob) or u32le(blob, sdo) != total:
        raise ValueError('Invalid text file')
    lines, flags, key = [], [], TEXT_KEY_BASE
    for index in range(count):
        offset, length, flag = struct.unpack_from('<iHH', blob, sdo + 4 + 8 * index)
        flags.append(flag)
        words = struct.unpack_from(f'<{length}H', blob, sdo + offset)
        lines.append(_crypt_line(words, key))
        key = (key + TEXT_KEY_ADVANCE) & 0xFFFF
    return lines, flags


def build_text(lines, flags):
    count, sdo = len(lines), 0x10
    table, body, key = bytearray(), bytearray(), TEXT_KEY_BASE
    for words, flag in zip(lines, flags, strict=True):
        table += struct.pack('<iHH', 4 + 8 * count + len(body), len(words), flag)
        body += struct.pack(f'<{len(words)}H', *_crypt_line(words, key))
        body += bytes(len(body) % 4)  # line data is 4-byte aligned; length excludes it
        key = (key + TEXT_KEY_ADVANCE) & 0xFFFF
    total = 4 + len(table) + len(body)
    return struct.pack('<HHIII', 1, count, total, 0, sdo) + struct.pack('<I', total) + table + body


def words_to_text(words):
    """Readable form: real newlines and [VAR XXXX a,b] for control codes."""
    text, i = '', 0
    while i < len(words) and words[i]:
        word = words[i]
        if word == 0x10:
            count, variable = words[i + 1], words[i + 2]
            args = words[i + 3:i + 2 + count]
            text += f'[VAR {variable:04X}' + (' ' + ','.join(map(str, args)) if args else '') + ']'
            i += 2 + count
        else:
            if word in (0x5B, 0x5D):
                raise ValueError('Literal brackets are not supported')
            text += chr(word)
            i += 1
    return text


def text_to_words(text):
    words, i = [], 0
    while i < len(text):
        if text[i] == '[':
            end = text.index(']', i)
            parts = text[i + 1:end].split()
            if parts[0] != 'VAR':
                raise ValueError(f'Unknown text code: {text[i:end + 1]}')
            args = [int(a) for a in parts[2].split(',')] if len(parts) > 2 else []
            words += [0x10, 1 + len(args), int(parts[1], 16), *args]
            i = end + 1
        else:
            words.append(ord(text[i]))
            i += 1
    words.append(0)
    return words


def u32le(data, offset):
    return struct.unpack_from('<I', data, offset)[0]
