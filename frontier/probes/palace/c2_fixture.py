"""Lab fixture for Palace C: pa_strong.sav with party slot 1 (Metagross) Gentle and one move of each group."""
import binascii, hashlib, struct, sys
from pathlib import Path
sys.path.insert(0, 'scripts'); sys.path.insert(0, 'frontier')
from save_fixture import PARTY, PKSIZE, blocks, decode_pk, encode_pk, u16
import palace_ai
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
nature, moves = int(sys.argv[3]), [int(m) for m in sys.argv[4].split(',')]
data = bytearray(src.read_bytes())
layout = blocks(data)
pk = decode_pk(data[PARTY:PARTY + PKSIZE])
records = palace_ai.moves()
pk[0x1C] = nature
struct.pack_into('<4H', pk, 0x5A, *moves)
pk[0x62:0x66] = bytes(records[m][5] for m in moves)
pk[0x66:0x6A] = bytes(4)
data[PARTY:PARTY + PKSIZE] = encode_pk(pk)
offset, length, checksum_offset = layout[18]
struct.pack_into('<H', data, checksum_offset, binascii.crc_hqx(data[offset:offset + length], 0xFFFF))
blocks(data)
check = decode_pk(data[PARTY:PARTY + PKSIZE])
assert check[0x1C] == nature and list(struct.unpack_from('<4H', check, 0x5A)) == moves
groups = palace_ai.move_groups()
dst.write_bytes(data)
print(dst, hashlib.sha256(data).hexdigest(), 'species', u16(check, 8), 'nature', nature, 'moves', moves,
      'groups', [groups[m] for m in moves], 'pp', list(check[0x62:0x66]))
