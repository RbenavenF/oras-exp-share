from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from formats import garc_entries, lz11_compress, lz11_decompress, zo_build, zo_files
from pawn import OP, Instruction, Op, Program, Script, compress_cells, decode, decompress_cells, encode, gf_hash

ROOT = Path(__file__).resolve().parents[1]
ROMFS = ROOT / 'baseline/oras/repolished/romfs'


def test_cell_compression_round_trip_and_five_byte_form():
    cells = [0, 1, -1, 63, 64, -64, -65, 0x7FFF, -0x8000, 0x12345678, -0x45444E0E, 0x7FFFFFFF, -0x80000000]
    data = compress_cells(cells)
    assert decompress_cells(data, len(cells)) == (cells, len(data))
    # A full 32-bit value carries only its top four bits in the first group (retail encoding).
    assert compress_cells([-0x45444E0E])[0] == 0x8B


def test_gf_hash_matches_known_native():
    assert gf_hash('FlagGet') == 0x133DAA6A


def test_lz11_and_zo_round_trip():
    data = bytes(range(256)) * 20 + b'ZO' * 300
    assert lz11_decompress(lz11_compress(data)) == data
    files = [b'a' * 56, b'', b'xyz' * 9]
    assert zo_files(zo_build(files)) == files


def test_relocation_keeps_branch_targets():
    # JUMP (at 4, two cells) skips ZERO_ALT and lands on ZERO_PRI at 16; insert an instruction at the target.
    instructions = [Instruction(0, OP['PROC'], [0]), Instruction(4, OP['JUMP'], [12]),
                    Instruction(12, OP['ZERO_ALT'], [0]), Instruction(16, OP['ZERO_PRI'], [0]),
                    Instruction(20, OP['RETN'], [0])]
    script = Script(0xF1E0, 10, 10, 0x1C, 8, 4096, 0, [[], [], [], [], [], []], b'', encode(instructions), [])
    program = Program.from_script(script)
    index = next(i for i, item in enumerate(program.items) if item == ('label', 'L10'))
    program.items.insert(index + 1, Op(OP['INC_PRI'], [0]))
    rebuilt = decode(program.build_script('L0').code)
    jump = next(i for i in rebuilt if i.op == OP['JUMP'])
    target = jump.address + jump.args[0]
    assert [i.op for i in rebuilt if i.address >= target] == [OP['INC_PRI'], OP['ZERO_PRI'], OP['RETN']]


def _retail_scripts():
    zones = (ROMFS / 'a/0/1/3').read_bytes()
    for entry, _, offset, length in garc_entries(zones)[:536]:
        files = zo_files(lz11_decompress(zones[offset:offset + length]))
        yield f'zone{entry}', files[2], True
        c = files[1][4:9]
        start = 12 + c[0] * 0x14 + c[1] * 0x30 + c[2] * 0x18 + c[3] * 0x18 + c[4] * 0x18
        size = struct.unpack_from('<I', files[1], start)[0]
        yield f'entities{entry}', files[1][start:start + size], None
    shared = (ROMFS / 'a/0/2/9').read_bytes()
    for entry, _, offset, length in garc_entries(shared):
        yield f'shared{entry}', shared[offset:offset + length], False


@pytest.mark.skipif(not (ROMFS / 'a/0/1/3').exists(), reason='Local baseline required')
def test_every_retail_script_round_trips_raw_and_symbolic():
    count = 0
    for name, raw, pad in _retail_scripts():
        script = Script.parse(raw)
        assert encode(decode(script.code)) == script.code, name
        padded = pad if pad is not None else True
        built = script.build(pad=padded)
        # Entity scripts are stored without the trailing alignment their container adds.
        assert built[:len(raw)] == raw and not any(built[len(raw):]), name
        program = Program.from_script(script)
        assert program.build_script(f'L{script.main:x}').build(pad=padded) == built, name
        count += 1
    assert count == 536 * 2 + 85
