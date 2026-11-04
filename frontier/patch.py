#!/usr/bin/env python3
"""Battle Factory code.bin patch: Battle Maison battles use rental Pokémon while the Factory is active.

The rentals and their IV are read from free saved works (WORK_*, frontier/ids.py); with WORK_IV = 0 the
party builder behaves as in the retail game. Steps:
1. Check the clean and Repolished code.bin (SHA-256) and the exact words at the hook site and padding.
2. Assemble frontier/asm/rental.s with arm-none-eabi-as/ld at the start of the .text padding.
3. Redirect the player-party branch of the party builder (0x1e3d8c) to it, and the rival builder's set read
   (0x1e4b34) to `rival_hook`, which copies the rival's sets to WORK_RIVAL for the swap, and the Maison's four
   Singles streak accessors to the Factory streak works while WORK_ROUTE is set. frontier/asm/dome.s is linked
   after it: with the Battle Dome's route the player's party is its two fighters (DOME_FIGHT), the rival's sets
   are forced (DOME_FORCED) and the rival's Singles party size (0x1e3548, `dome_count`) is 2.
4. Point the text of the GlobalCall row for ids 9770-9779 (shared script 5, the Factory draft;
   frontier/factory.py) at a new story text entry, TEXT_FACTORY.
5. Write code.bin and code.ips; the IPS is the diff from the clean code.bin, so it already contains
   Repolished's records and replaces its code.ips in the mod folder.

Usage: python frontier/patch.py --out work/frontier/patch
"""
import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from formats import apply_ips, read_ips, sha256  # noqa: E402
from build_patch import diff_ips  # noqa: E402

CLEAN = ROOT / 'baseline/oras/clean/exefs/code.bin'
REPOLISHED = ROOT / 'baseline/oras/repolished/exefs/code.bin'
REPOLISHED_IPS = ROOT / 'inputs/repolished/Omega Ruby Repolished (ver. 1.7.6)/code.ips'
HASHES = {
    CLEAN: 'd587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37',
    REPOLISHED: '3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293',
    REPOLISHED_IPS: '0da174955afe9a7baf43254ce314bf5b65032f89c70a8e1065fa92ee4c2267df',
}
ASM = ROOT / 'frontier/asm/rental.s'
ASMS = [ASM, ROOT / 'frontier/asm/dome.s', ROOT / 'frontier/asm/pike.s']   # linked together, rental_hook first (at CAVE)
BASE = 0x100000
CAVE, CAVE_END = 0x579604, 0x57A000           # .text padding (reports/frontier.md §5)
SITE = 0x1E3D8C                               # player-party branch of the party builder 0x1e3d2c
SITE_BEFORE = [0xE5960B78, 0xE590001C, 0xE5908014, 0xE1A00008, 0xEB0747E4]  # ldr r0,[r6,#0xb78] .. bl 0x3b5d34
RESUME = 0x1E3DDC                             # common tail: level 50 adjust, per-member updates
RIVAL_SITE = 0x1E4B34                         # rival builder 0x1e4a94: ldrh r4, [r0, #4] (drawn set index)
RIVAL_BEFORE = 0xE1D040B4
COUNT_SITE = 0x1E3548                         # trainer party 0x1e3480, Singles: mov r6, #3 (rival party size)
COUNT_BEFORE = 0xE3A06003
BUILD_SITE = 0x1E3110                         # StartBattle 0x1e30b8: bl 0x1e3d2c (party builder), Pike H1
BUILD_BEFORE = 0xEB000305
ISWIN = 0x1E5664                              # IsWin: ldrb r0, [r0, #0x73c]; cmp; movne; bx lr. Pike H2
ISWIN_BEFORE = (0xE5D0073C, 0xE3500001, 0x13A00000, 0xE12FFF1E)
FUNCTIONS = {'LOAD_SET': 0x1EFC18, 'MAKE_PARAM': 0x1EF904, 'ADD_MEMBER': 0x3B645C, 'PARTY_PREPARE': 0x3B5D34,
             'RESUME': RESUME, 'BUILD_PARTY': 0x1E3D2C,
             # PokemonParam core accessors (reports/frontier.md §28; the battle block at [core+4])
             'GET_HP': 0x153174, 'GET_MAX_HP': 0x153254, 'SET_HP': 0x14F450, 'GET_SICK': 0x4D22E4,
             'SET_SICK': 0x14F814}
FUNCTION_HEADS = {0x1E3D2C: 0xE92D47F0, 0x153174: 0xE92D4070, 0x153254: 0xE92D4070, 0x14F450: 0xE92D4070,
                  0x4D22E4: 0xE92D4070, 0x14F814: 0xE92D4070,
                  0x1531A8: 0xE1D050B8, 0x153288: 0xE1D050BA, 0x14F488: 0xE1C050B8, 0x4D2318: 0xE5905000,
                  0x14F84C: 0xE5805000,
                  0x1EFC18: 0xE92D4030, 0x1EF904: 0xE92D4FF0, 0x3B645C: 0xE92D4070, 0x3B5D34: 0xE92D4070,
                  # saved work N at [[game data]] + 0x13140 + 4 + 2*(N - 0x4000): WorkGet (0x3fe118) ...
                  0x3FE128: 0xE592201C, 0x3FE12C: 0xE5922000, 0x3FE130: 0xE2822801, 0x3FE134: 0xE2822DC5,
                  # ... and the EventWork getter 0x11fa90 (r0 + 2*N - 0x7ffc)
                  0x11FABC: 0xE2400B1F, 0x11FAC0: 0xE2400FFF}
# Saved works, free in the retail scripts, entity data and code (frontier/ids.py) and 0 in the user's save.
# Works 16410-16413 held the Factory state until 2026-11-04: entering any Maison clone (213, 329) sets them to 0 (Azahar,
# reports/frontier.md §25; works 0x4010-0x401F look like a block the game clears by range), so a paused Factory was lost
# by walking out of its hall and back. The works below survive it (16442 is measured to; these by the same test).
WORK_IV = 16489            # Factory state: rentals' IV 1-31; 0 = inactive (retail behaviour)
WORK_SETS = (16485, 16486, 16487)   # rentals: bit 15 Super (0xb8) else Normal (0xb6), bits 10-11 ability
SUPER = 0x8000                      # slot (3 = random), bits 0-9 set index
WORK_RIVAL = (16433, 16434, 16435)  # last rival's set indices (maisonpkN/S of the rank; written by rival_hook)
WORK_FSTREAK, WORK_ROUTE, WORK_FRECORD = 16437, 16438, 16439   # Factory streak / «route the streak» / record
MAISON_BASE = 0x195E0                 # Maison block in the save data (GetMyWinCount native, AddWinCount 0x1e2fd4)
SAVE_WORKS = 0x13144                  # saved works in the save data (WorkGet 0x3fe118)
# Maison Singles streak accessors: site -> (stub, resume). Each site is add OUT, r0, r2, lsl #1.
STREAK_SITES = {0x45CDC4: ('streak_inc', 0xE0801082), 0x45CF14: ('streak_get', 0xE0800082),
                0x45CFB8: ('streak_set', 0xE0800082), 0x45D03C: ('streak_record', 0xE0800082)}
# Streak routes: the value of saved work WORK_ROUTE -> (facility, its streak work S); its record is S + 2 (the
# accessors read the record at slot + 0x1c8) and S + 1 is the facility's own (state, free for its owner). 0 is the
# Maison's own streak. Works free per frontier/ids.py (2026-11-03); assigned in frontier/REPARTO.md.
STREAK_ROUTES = {1: ('factory', WORK_FSTREAK), 2: ('tower', 16441), 3: ('palace', 16461), 4: ('arena', 16465),
                 5: ('dome', 16473), 6: ('pike', 16477), 7: ('pyramid', 16481)}
ROUTE = {facility: route for route, (facility, _) in STREAK_ROUTES.items()}
# Battle Dome (frontier/asm/dome.s, frontier/dome.py): with WORK_ROUTE = ROUTE['dome'] the player's battle party is
# the two party slots in DOME_FIGHT and the rival brings two members, the sets in DOME_FORCED (rental work value:
# bit 15 Super, bits 0-9 index). Free per frontier/ids.py (2026-11-04); assigned in frontier/REPARTO.md.
DOME_FIGHT = (16649, 16650)
DOME_FORCED = (16657, 16658)
# Battle Pike (frontier/asm/pike.s, frontier/pike.py): with WORK_ROUTE = ROUTE['pike'] the battle party's HP and
# status are set from these works when it is built and copied back to them by IsWin, by position (HP 0xFFFF = full).
# Free per frontier/ids.py (2026-11-04); assigned in frontier/REPARTO.md.
PIKE_HP = (16661, 16662, 16663)
PIKE_ST = (16669, 16670, 16671)
PIKE_FULL = 0xFFFF
# A facility's «challenge in progress» work (started or paused; 0 = none): the Factory's rental IV, for the others
# the work between their streak and record. A reception refuses while another facility's is not 0 (REPARTO.md).
ACTIVE_WORK = {facility: WORK_IV if facility == 'factory' else streak + 1
               for facility, streak in STREAK_ROUTES.values()}
ABILITY_SHIFT, ABILITY_RANDOM = 10, 3
# GlobalCall range table (rodata, 86 rows of u16 first id, last id, shared script, flag, story text, 0, 0, 0
# from 0x587678): the row for ids 9770-9779 (shared script 5, a retail placeholder) gets the Factory text.
GLOBAL_ROW = 0x587AA8
GLOBAL_ROW_BEFORE = (9770, 9779, 5, 1, 618, 0, 0, 0)
TEXT_FACTORY = 637                  # new story text entry (the retail archives have 637 entries, 0-636)
# Native groups per zone (rodata, one u32 bit mask per zone id from 0x587d58; the zone-script loader 0x3ff5a4
# hands it to the registrar 0x3fbc80, one amx_Register 0x506190 per bit). Bit 8 is the Maison group (DllField.cro
# table 0xf8b44, BattleInstWorkCreate...), set only for zones 448, 517 and 520. A zone script naming a native its
# zone does not register fails amx_Exec 0x503310 on every event and the game hangs (reports/frontier.md §19).
ZONE_NATIVES, ZONE_COUNT = 0x587D58, 536
NATIVES_DEFAULT, NATIVES_MAISON = 0x243, 0x100
MAISON_NATIVE_ZONES = (448, 517, 520)
CONSTANTS = {'WORK_IV': WORK_IV, 'WORK_SET0': WORK_SETS[0], 'ARCHIVE_NORMAL': 0xB6, 'ARCHIVE_SUPER': 0xB8, 'RENTAL_LEVEL': 50,
             'RENTALS': len(WORK_SETS), 'WORK_RIVAL': WORK_RIVAL[0],
             'ROUTE_DELTA': MAISON_BASE - SAVE_WORKS - 2 * (WORK_ROUTE - 0x4000),
             'ROUTES': len(STREAK_ROUTES), 'WORK_ROUTE': WORK_ROUTE,
             'DOME_ROUTE': ROUTE['dome'], 'DOME_FIGHT0': DOME_FIGHT[0], 'DOME_FORCED0': DOME_FORCED[0],
             'DOME_FIGHTERS': len(DOME_FIGHT),
             'PIKE_ROUTE': ROUTE['pike'], 'PIKE_HP0': PIKE_HP[0], 'PIKE_ST0': PIKE_ST[0], 'PIKE_FIGHTERS': len(PIKE_HP),
             **{f'SLOT_DELTA_{route}': MAISON_BASE - SAVE_WORKS - 2 * (streak - 0x4000) + 0x1C4
                for route, (_, streak) in STREAK_ROUTES.items()}}
assert list(WORK_SETS) == [WORK_SETS[0] + k for k in range(3)] and 0 < WORK_IV - WORK_SETS[0] < 128   # rental.s: sub
assert 0 < WORK_IV - WORK_RIVAL[0] < 128 and 2 * (WORK_IV - 0x4000) < 256                              # rental.s: imm8
assert WORK_FRECORD == WORK_FSTREAK + 2      # the accessors read the record at slot + 0x1c8
assert sorted(STREAK_ROUTES) == list(range(1, 8))   # rental.s has seven slot_deltas words
assert 0 < CONSTANTS['ROUTE_DELTA'] < 0x10000          # two subs: bits 8-15 and 0-7
_streak_works = [w for _, s in STREAK_ROUTES.values() for w in (s, s + 1, s + 2)]
assert len(set(_streak_works)) == len(_streak_works) and WORK_ROUTE == WORK_FSTREAK + 1
assert all(0 < CONSTANTS[f'SLOT_DELTA_{r}'] for r in STREAK_ROUTES)
assert 0 < WORK_IV - WORK_ROUTE < 128 and 2 * (WORK_ROUTE - 0x4000) < 256           # rental.s, dome.s: imm8 offsets
assert DOME_FIGHT[1] == DOME_FIGHT[0] + 1 and DOME_FORCED[1] == DOME_FORCED[0] + 1   # dome.s reads them in pairs
assert 0 < DOME_FIGHT[0] - WORK_ROUTE and len(DOME_FIGHT) == len(DOME_FORCED) == 2
assert list(PIKE_HP) == [PIKE_HP[0] + k for k in range(3)] and list(PIKE_ST) == [PIKE_ST[0] + k for k in range(3)]
assert 0 < 2 * (PIKE_ST[0] - PIKE_HP[0]) < 256                                       # pike.s: ldrh/strh imm8


def word(data, va):
    return struct.unpack_from('<I', data, va - BASE)[0]


def arm_branch(source, target, link=False):
    delta = (target - source - 8) >> 2
    return (0xEB000000 if link else 0xEA000000) | (delta & 0xFFFFFF)


def assemble():
    """(hook bytes at CAVE, {global symbol: address})."""
    with tempfile.TemporaryDirectory() as tmp:
        elf, binary = (Path(tmp) / n for n in ('hook.elf', 'hook.bin'))
        defs = [a for k, v in CONSTANTS.items() for a in ('--defsym', f'{k}={v}')]
        objs = [Path(tmp) / f'{src.stem}.o' for src in ASMS]
        for src, obj in zip(ASMS, objs):
            subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, src], check=True)
        resumes = {f'STREAK_{stub[7:].upper()}_RESUME': site + 4 for site, (stub, _) in STREAK_SITES.items()}
        syms = [f'--defsym={k}={v:#x}' for k, v in {**FUNCTIONS, **resumes}.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={CAVE:#x}', '-e', 'rental_hook', *syms, '-o', elf, *objs],
                       check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        names = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
        symbols = {n: int(a, 16) for a, t, n in (line.split() for line in names.splitlines()) if t == 'T'}
        if symbols['rental_hook'] != CAVE:
            raise ValueError('rental_hook is not at the start of the cave')
        return binary.read_bytes(), symbols


def zone_natives(code, clones):
    """Give each clone zone ({slot: donor}) its donor's native groups, on the measured table only."""
    masks = struct.unpack_from(f'<{ZONE_COUNT}I', code, ZONE_NATIVES - BASE)
    maison = tuple(z for z, m in enumerate(masks) if m & NATIVES_MAISON)
    if maison != MAISON_NATIVE_ZONES or any(m & NATIVES_DEFAULT != NATIVES_DEFAULT for m in masks):
        sys.exit(f'zone native table {ZONE_NATIVES:#x} differs: Maison group in zones {maison}')
    for slot, donor in clones.items():
        if masks[slot] != NATIVES_DEFAULT:
            sys.exit(f'zone {slot} native groups {masks[slot]:#x}, expected the default {NATIVES_DEFAULT:#x}')
        struct.pack_into('<I', code, ZONE_NATIVES - BASE + 4 * slot, masks[donor])


def build(native_clones=None):
    """Patched code.bin, the hook and the site words. `native_clones`: {zone: donor} for zone_natives."""
    for path, expected in HASHES.items():
        if sha256(path) != expected:
            sys.exit(f'{path.relative_to(ROOT)}: unexpected sha256')
    clean, code = CLEAN.read_bytes(), bytearray(REPOLISHED.read_bytes())
    if apply_ips(clean, read_ips(REPOLISHED_IPS.read_bytes())) != bytes(code):
        sys.exit('Repolished code.bin is not clean code.bin + Repolished code.ips')
    got = [word(code, SITE + 4 * i) for i in range(len(SITE_BEFORE))]
    if got != SITE_BEFORE:
        sys.exit(f'hook site words differ: {[f"{w:08x}" for w in got]}')
    for va, head in FUNCTION_HEADS.items():
        if word(code, va) != head:
            sys.exit(f'{va:#x}: unexpected word {word(code, va):08x}')
    hook, symbols = assemble()
    if CAVE + len(hook) > CAVE_END or any(code[CAVE - BASE:CAVE - BASE + len(hook)]):
        sys.exit('hook does not fit in the zero padding')
    code[CAVE - BASE:CAVE - BASE + len(hook)] = hook
    site = [0xE1A00006,                               # mov r0, r6        (work)
            0xE1A01009,                               # mov r1, sb        (battle party)
            arm_branch(SITE + 8, CAVE, link=True),    # bl  rental_hook (Factory: continues at 0x1e3ddc)
            0xE1A08000,                               # mov r8, r0        (player party, as 0x1e3d94)
            0xE1A00000]                               # nop               (0x3b5d34 already called)
    struct.pack_into(f'<{len(site)}I', code, SITE - BASE, *site)
    if word(code, RIVAL_SITE) != RIVAL_BEFORE:
        sys.exit(f'rival site word differs: {word(code, RIVAL_SITE):08x}')
    struct.pack_into('<I', code, RIVAL_SITE - BASE, arm_branch(RIVAL_SITE, symbols['rival_hook'], link=True))
    if word(code, COUNT_SITE) != COUNT_BEFORE:
        sys.exit(f'rival count site word differs: {word(code, COUNT_SITE):08x}')
    struct.pack_into('<I', code, COUNT_SITE - BASE, arm_branch(COUNT_SITE, symbols['dome_count'], link=True))
    if word(code, BUILD_SITE) != BUILD_BEFORE:
        sys.exit(f'party build call {BUILD_SITE:#x} differs: {word(code, BUILD_SITE):08x}')
    struct.pack_into('<I', code, BUILD_SITE - BASE, arm_branch(BUILD_SITE, symbols['pike_build'], link=True))
    got = tuple(word(code, ISWIN + 4 * i) for i in range(4))
    if got != ISWIN_BEFORE:
        sys.exit(f'IsWin {ISWIN:#x} differs: {[f"{w:08x}" for w in got]}')
    struct.pack_into('<I', code, ISWIN - BASE, arm_branch(ISWIN, symbols['pike_iswin']))
    for va, (stub, before) in STREAK_SITES.items():
        if word(code, va) != before:
            sys.exit(f'streak accessor {va:#x} differs: {word(code, va):08x}')
        struct.pack_into('<I', code, va - BASE, arm_branch(va, symbols[stub]))
    row = struct.unpack_from('<8H', code, GLOBAL_ROW - BASE)
    if row != GLOBAL_ROW_BEFORE:
        sys.exit(f'GlobalCall row {GLOBAL_ROW:#x} differs: {row}')
    struct.pack_into('<H', code, GLOBAL_ROW - BASE + 8, TEXT_FACTORY)
    zone_natives(code, native_clones or {})
    return bytes(code), hook, site


# Battle Pike H2 needs the battle's result party in the battle setup (+0x4c) when IsWin reads it. The battle module
# copies its party back there at the end (DllBattle.cro 0x15378, the copy at 0x156fc, after restoring the original
# order) only for setup competitor 0 (wild) or 1 (trainer); the Maison's setup is 2 (0x1e0790: strb 2, [setup]), so
# its copy kept the pre-battle state (static gate: work/frontier/pike/copy-back-disasm.txt). The patch lets 0-2 through. Competitor 2 then
# also gets the part common to all three (order, form and max HP fixes on its own copy) and none of the parts
# reserved to 0 or 1 (0x154b0, 0x1552c, 0x15708). The Maison's battle party is a copy it discards (§4, §6), so the
# other facilities see no change. Applied over the mod's DllBattle.cro (v0.5, already patched elsewhere): CRO
# hashes and the static.crr entry are updated as scripts/build_patch.py does.
MOD_ROMFS = ROOT / 'dist/held-exp-share-v0.5/mods/000400000011C400/romfs'
BATTLE_CRO, CRR = 'DllBattle.cro', '.crr/static.crr'
BATTLE_CRO_SHA256 = '46153fa373b8166a3a65a31272008dc8d63207f3b2498752c69c1a0c74235519'
COPY_BACK = 0x15398                         # file offset: cmp r1, #0; cmpne r1, #1; bne 0x1580c
COPY_BACK_BEFORE = (0xE3510000, 0x13510001, 0x1A000119)
COPY_BACK_AFTER = (0xE3510002, 0xE1A00000, 0x8A000119)   # cmp r1, #2; nop; bhi 0x1580c


def battle_cro(romfs=MOD_ROMFS):
    """{romfs path: bytes}: the mod's DllBattle.cro with the copy back for competitor 2, and its static.crr."""
    from build_patch import rehash_cro, update_crr
    original = (romfs / BATTLE_CRO).read_bytes()
    import hashlib
    if hashlib.sha256(original).hexdigest() != BATTLE_CRO_SHA256:
        sys.exit(f'{BATTLE_CRO}: not the v0.5 one')
    got = struct.unpack_from('<3I', original, COPY_BACK)
    if got != COPY_BACK_BEFORE:
        sys.exit(f'{BATTLE_CRO} {COPY_BACK:#x} differs: {[f"{w:08x}" for w in got]}')
    changed = bytearray(original)
    struct.pack_into('<3I', changed, COPY_BACK, *COPY_BACK_AFTER)
    changed = rehash_cro(original, bytes(changed))
    crr = update_crr((romfs / CRR).read_bytes(), original, changed)
    return {BATTLE_CRO: changed, CRR: crr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game code)')
    code, hook, site = build()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'code.bin').write_bytes(code)
    ips = diff_ips(CLEAN.read_bytes(), code)
    if apply_ips(CLEAN.read_bytes(), read_ips(ips)) != code:
        sys.exit('IPS round trip failed')
    (out / 'code.ips').write_bytes(ips)
    print(f'hook {len(hook)} bytes at {CAVE:#x}-{CAVE + len(hook):#x}; site {SITE:#x}: '
          + ' '.join(f'{w:08x}' for w in site))
    print(f'wrote {out}/code.bin (sha256 {sha256(out / "code.bin")[:16]}…) and code.ips ({len(ips)} bytes)')


if __name__ == '__main__':
    main()
