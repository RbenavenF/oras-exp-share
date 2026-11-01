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
