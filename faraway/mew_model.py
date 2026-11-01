#!/usr/bin/env python3
"""Build a field (MoveModels) version of Mew from its battle model.

ORAS has no field model for Mew. A field model is an "MM" container: [BCH with model, materials,
textures and LUTs] + [GF motion pack with 239 field slots]. The battle model keeps the model and the
textures in separate BCH files (a/0/0/8 entries 1547 and 1549) and its Pokemon-Amie motions in the
same motion-pack format (entry 1553). SPICA merges the two BCH files; the motion pack is rebuilt here.

Measured layouts (reports/faraway.md): MM = "MM", u16 count, u32 offsets[count + 1], subfiles
aligned to 0x80. Motion pack = u32 count, u32 offset per slot (0 = empty), u32 end of data, data
(4-byte aligned), zero padding to 0x80 in field packs. Slot 0 is the bone table; Wingull and
Captain Briney use field slots 1 (idle), 3 (move) and 94.
"""
import mmap
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from formats import lz11_decompress  # noqa: E402

POKEMON_MODELS = ROOT / 'baseline/oras/repolished/romfs/a/0/0/8'
MEW_MODEL, MEW_TEXTURES, MEW_AMIE_MOTIONS = 1547, 1549, 1553    # pm0151_00 entries, found by name
AMIE_WAIT, AMIE_MOVE = 1, 15                                    # kw01_wait01, kw33_moveA01
FIELD_SLOTS = 239
FIELD_MOTIONS = {0: 0, 1: AMIE_WAIT, 3: AMIE_MOVE, 94: AMIE_WAIT}  # field slot -> Amie slot
FIELD_TEMPLATE = 484                                            # Wingull's field model (pm0278_00_fi)
FIELD_SCALE = 0.6                                               # battle size -> about the player's height
DOTNET = ROOT / 'tools/dotnet/dotnet'
TOOL = ROOT / 'work/faraway/mewmodel/MewModel.dll'


def container(raw):
    count = struct.unpack_from('<H', raw, 2)[0]
    offsets = struct.unpack_from(f'<{count + 1}I', raw, 4)
    return [raw[a:b] for a, b in zip(offsets, offsets[1:])]


def build_container(magic, files, align=0x80):
    header = 4 + 4 * (len(files) + 1)
    out = bytearray(magic + struct.pack('<H', len(files)))
    position = -(-header // align) * align
    offsets, body = [], bytearray()
    for blob in files:
        offsets.append(position + len(body))
        body += blob + bytes(-len(blob) % align)
    offsets.append(position + len(body))
    out += struct.pack(f'<{len(offsets)}I', *offsets)
    out += bytes(position - len(out))
    return bytes(out + body)


def model_entry(index):
    with POKEMON_MODELS.open('rb') as stream:
        data = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        fato = struct.unpack_from('<I', data, 4)[0]
        content = struct.unpack_from('<I', data, 0x10)[0]
        fatb = fato + struct.unpack_from('<I', data, fato + 4)[0]
        record = fatb + 12 + struct.unpack_from('<I', data, fato + 12 + 4 * index)[0]
        start, _, length = struct.unpack_from('<III', data, record + 4)
        raw = data[content + start:content + start + length]
    return lz11_decompress(raw) if raw[0] == 0x11 else raw


def _move_model(index):
    from formats import garc_entries
    data = (ROOT / 'baseline/oras/repolished/romfs/a/0/2/1').read_bytes()
    _, _, offset, length = garc_entries(data)[index]
    raw = data[offset:offset + length]
    return lz11_decompress(raw) if raw[0] == 0x11 else raw


def motion_pack(source):
    count = struct.unpack_from('<I', source, 0)[0]
    offsets = struct.unpack_from(f'<{count}I', source, 4)
    end = struct.unpack_from('<I', source, 4 + 4 * count)[0]

    def motion(slot):
        start = offsets[slot]
        if not start:
            raise ValueError(f'Motion slot {slot} is empty')
        following = [o for o in offsets if o > start] + [end]
        return source[start:min(following)]

    blobs = {slot: motion(amie) for slot, amie in FIELD_MOTIONS.items()}
    data_start = 4 + 4 * FIELD_SLOTS + 4
    table, body, cache = [0] * FIELD_SLOTS, bytearray(), {}
    for slot in sorted(blobs):
        key = FIELD_MOTIONS[slot]
        if key not in cache:
            cache[key] = data_start + len(body)
            body += blobs[slot] + bytes(-len(blobs[slot]) % 4)
        table[slot] = cache[key]
    out = struct.pack(f'<I{FIELD_SLOTS}II', FIELD_SLOTS, *table, data_start + len(body)) + body
    return out + bytes(-len(out) % 0x80)


def build(work):
    work.mkdir(parents=True, exist_ok=True)
    import os
    if os.environ.get('FARAWAY_MODEL_EXPERIMENT') == 'wingull-spica':
        # Laboratory control: Wingull's own field model re-written by SPICA, in Mew's new slot.
        sys.path.insert(0, str(ROOT / 'work/faraway'))
        import bchinfo
        parts = container(bchinfo.mm_entry(484))
        (work / 'wingull.bch').write_bytes(parts[0])
        subprocess.run([str(DOTNET), str(TOOL), 'roundtrip', str(work / 'wingull.bch'), str(work / 'wingull_rt.bch')],
                       check=True, env={'DOTNET_ROOT': str(DOTNET.parent), 'DOTNET_CLI_TELEMETRY_OPTOUT': '1'})
        return build_container(b'MM', [(work / 'wingull_rt.bch').read_bytes(), parts[1]])
    model, textures = container(model_entry(MEW_MODEL))[0], container(model_entry(MEW_TEXTURES))[0]
    for blob, name in ((model, b'pm0151_00'), (textures, b'pm0151_00_Body1')):
        if name not in blob:
            raise ValueError(f'Entry does not hold {name!r}')
    (work / 'model.bch').write_bytes(model)
    (work / 'textures.bch').write_bytes(textures)
    # Battle models use the PokePack shader, which the field never loads: every material is replaced by a
    # copy of a retail field material (Wingull's, MoveModels 484) holding Mew's base colour texture.
    template = container(_move_model(FIELD_TEMPLATE))[0]
    (work / 'template.bch').write_bytes(template)
    subprocess.run([str(DOTNET), str(TOOL), 'fieldify', str(work / 'field.bch'), str(work / 'model.bch'),
                    str(work / 'textures.bch'), str(work / 'template.bch'), str(FIELD_SCALE)], check=True,
                   env={'DOTNET_ROOT': str(DOTNET.parent), 'DOTNET_CLI_TELEMETRY_OPTOUT': '1'})
    motions = motion_pack(container(model_entry(MEW_AMIE_MOTIONS))[0])
    mm = build_container(b'MM', [(work / 'field.bch').read_bytes(), motions])
    (work / 'pm0151_00_fi.mm').write_bytes(mm)
    return mm


if __name__ == '__main__':
    print(len(build(ROOT / 'work/faraway/mew')))
