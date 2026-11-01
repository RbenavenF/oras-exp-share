"""Minimal read-only CRO0 parser: segments and internal relocation patches.

Layout from 3dbrew (https://www.3dbrew.org/wiki/CRO0). Offsets here are file offsets;
segment offsets in the format are packed as (offset << 4) | segment index.
"""
import struct


class Cro:
    def __init__(self, data):
        self.data = data
        assert data[0x80:0x84] == b'CRO0', 'not a CRO0'
        u = lambda off: struct.unpack_from('<I', data, off)[0]
        seg_off, seg_num = u(0xC8), u(0xCC)
        # (file offset, size, type): type 0 text, 1 rodata, 2 data, 3 bss
        self.segments = [struct.unpack_from('<3I', data, seg_off + 12 * i) for i in range(seg_num)]
        rel_off, rel_num = u(0x128), u(0x12C)
        self.relocs = []  # (target file offset, type, source file offset)
        for i in range(rel_num):
            target, kind, src_seg, _, _, addend = struct.unpack_from('<IBBBBI', data, rel_off + 12 * i)
            self.relocs.append((self.resolve(target), kind, self.segments[src_seg][0] + addend))

    def resolve(self, packed):
        return self.segments[packed & 0xF][0] + (packed >> 4)

    def segment_of(self, offset):
        for index, (start, size, kind) in enumerate(self.segments):
            if start <= offset < start + size:
                return index, kind
        return None

    def pointer_at(self):
        """file offset of a pointer slot -> file offset it points to (after relocation)."""
        return {target: source for target, _, source in self.relocs}
