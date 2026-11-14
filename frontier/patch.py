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
import arena_engine as ae  # noqa: E402
import palace_engine as pe  # noqa: E402

CLEAN = ROOT / 'baseline/oras/clean/exefs/code.bin'
REPOLISHED = ROOT / 'baseline/oras/repolished/exefs/code.bin'
REPOLISHED_IPS = ROOT / 'inputs/repolished/Omega Ruby Repolished (ver. 1.7.6)/code.ips'
HASHES = {
    CLEAN: 'd587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37',
    REPOLISHED: '3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293',
    REPOLISHED_IPS: '0da174955afe9a7baf43254ce314bf5b65032f89c70a8e1065fa92ee4c2267df',
}
ASM = ROOT / 'frontier/asm/rental.s'
ASMS = [ASM, ROOT / 'frontier/asm/dome.s', ROOT / 'frontier/asm/pike.s', ROOT / 'frontier/asm/pyramid.s',
        ROOT / 'frontier/asm/arena.s', ROOT / 'frontier/asm/modes.s']   # linked together, rental_hook first (at HOOKS)
# Battle-time routines, reached only from DllBattle.cro bridges: linked into DllBattle.cro (battle_cro_code).
CRO_ASMS = [ROOT / 'frontier/asm/arena_cro.s', ROOT / 'frontier/asm/palace_b_cro.s']
BASE = 0x100000
CAVE, CAVE_END = 0x579604, 0x57A000           # .text padding (reports/frontier.md §5): exheader .text ends at CAVE
# Luma3DS LayeredFS (sysmodules/loader/source/patcher.c, findLayeredFsPayloadOffset, Luma3DS 1441535d): when the
# padding after the exheader's .text size is >= romfsRedirPatchSize, Luma copies its redirection payload
# (romfsredir.s) to the END OF .text, i.e. CAVE, and points fsOpenFileDirectly/fsTryOpenFile at it (here 0x123e80
# and 0x1325a4); the "lf:" path goes in the .rodata padding. romfsRedirPatchSize is the fixed size of romfsredir.s:
# 0x114 = 276 bytes at 1441535d (arm-none-eabi-as of that file), the same 276 bytes measured on the user's console
# (work/frontier/consola/console-cave.bin, 2026-11-13). The first LUMA_RESERVED bytes of the cave stay zero for it
# (with margin for a longer payload in another Luma version); our code starts at HOOKS.
LUMA_PAYLOAD = 0x114
LUMA_RESERVED = 0x200
HOOKS = CAVE + LUMA_RESERVED
assert LUMA_RESERVED >= max(0x140, LUMA_PAYLOAD) and HOOKS % 4 == 0
SITE = 0x1E3D8C                               # player-party branch of the party builder 0x1e3d2c
SITE_BEFORE = [0xE5960B78, 0xE590001C, 0xE5908014, 0xE1A00008, 0xEB0747E4]  # ldr r0,[r6,#0xb78] .. bl 0x3b5d34
RESUME = 0x1E3DDC                             # common tail: level 50 adjust, per-member updates
RIVAL_SITE = 0x1E4B34                         # rival builder 0x1e4a94: ldrh r4, [r0, #4] (drawn set index)
RIVAL_BEFORE = 0xE1D040B4
COUNT_SITE = 0x1E3548                         # trainer party 0x1e3480, Singles: mov r6, #3 (rival party size)
COUNT_BEFORE = 0xE3A06003
BUILD_SITE = 0x1E3110                         # StartBattle 0x1e30b8: bl 0x1e3d2c (party builder), Pike H1
BUILD_BEFORE = 0xEB000305
LEVEL_SITE = 0x1E4E80                         # rival builder 0x1e4a94: mov r1, #50 (MAKE_PARAM level). Pike wild level
LEVEL_BEFORE = 0xE3A01032
CAP_SITE = 0x1E3E00                           # party builder tail, per member: cmp r0, #50 (level cap). F9 mode_cap
CAP_BEFORE = 0xE3500032
ISWIN = 0x1E5664                              # IsWin: ldrb r0, [r0, #0x73c]; cmp; movne; bx lr. Pike H2
ISWIN_BEFORE = (0xE5D0073C, 0xE3500001, 0x13A00000, 0xE12FFF1E)
WORK_DELETE = 0x1E5C48                        # BattleInstWorkDelete (DllField.cro 0x956b4 -> thunk 0x3738), holder r0
DELETE_SITE = 0x1E5C54                        # its `bl 0x12b8fc` after ldr r4, [r0, #0x64] (work): pyramid_save
FUNCTIONS = {'LOAD_SET': 0x1EFC18, 'MAKE_PARAM': 0x1EF904, 'ADD_MEMBER': 0x3B645C, 'PARTY_PREPARE': 0x3B5D34,
             'ARENA_UDIV': ae.UDIV, 'ARENA_START_RESUME': ae.START + 4,
             'RESUME': RESUME, 'BUILD_PARTY': 0x1E3D2C, 'WORK_DELETE_CALL': 0x12B8FC,
             # PokemonParam core accessors (reports/frontier.md §28; the battle block at [core+4])
             'GET_HP': 0x153174, 'GET_MAX_HP': 0x153254, 'SET_HP': 0x14F450, 'GET_SICK': 0x4D22E4,
             'SET_SICK': 0x14F814, 'GET_PP': 0x1531C8, 'SET_PP': 0x14F4F8, 'PARTY_COUNT': 0x4D3424}
FUNCTION_HEADS = {0x1E3D2C: 0xE92D47F0, 0x1E5C48: 0xE92D4070, 0x1E5C4C: 0xE1A05000, 0x1E5C50: 0xE5904064, 0x153174: 0xE92D4070, 0x153254: 0xE92D4070, 0x14F450: 0xE92D4070,
                  ae.UDIV: 0xE3B02000, 0x4D3424: 0xE5D00018,
                  0x4D22E4: 0xE92D4070, 0x14F814: 0xE92D4070,
                  0x1531C8: 0xE92D4070, 0x14F4F8: 0xE92D4070,
                  0x15320C: 0xE5D04022, 0x14F53C: 0xE5C05022,
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
# Maison streak accessors (reports/modos-base.md): each dispatches by type through a jump table; the entries of
# type 0 (Singles) and 1 (Doubles) -> the stub of frontier/asm/modes.s, which resolves the bank from (route, mode).
# table -> (stub, retail Singles body, retail Doubles body). No other code reaches those bodies (scan of code.bin).
STREAK_SITES = {0x45CDB0: ('streak_inc', 0x45CDC4, 0x45CDFC), 0x45CF00: ('streak_get', 0x45CF14, 0x45CF24),
                0x45CFA4: ('streak_set', 0x45CFB8, 0x45CFC8), 0x45D028: ('streak_record', 0x45D03C, 0x45D04C)}
STREAK_INC_BODY = 0x45CDD0                    # Singles increment after its two adds: r0 = S, r2 = R, r3 = limit
MODE_LIVE = 0x45CDFC                          # reclaimed Doubles increment: table entry now targets streak_inc
MODE_LIVE_BEFORE = (0xE0801082, 0xE2810F73, 0xE2812E1D, 0xE1D010B0, 0xE1510003, 0x2AFFFFE5,
                    0xE2811001, 0xE6FF1071, 0xE1C010B0, 0xE1D200B0, 0xE1500001, 0x2AFFFFDF, 0xEAFFFFF0)
STREAK_INC_BODY_WORDS = (0xE1D010B0, 0xE1510003, 0x2AFFFFF3, 0xE2811001, 0xE6FF1071, 0xE1C010B0, 0xE1D200B0,
                         0xE1500001, 0x2AFFFFED, 0xE1C210B0, 0xE12FFF1E)
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
PIKE_PP = ((16721, 16722, 16723), (16725, 16726, 16727))  # two moves per u16, by fighter
PIKE_FULL = 0xFFFF
# Wild rooms (v2): the maisonpkN index of the room's wild set, 0 = no wild room (pike.s pike_wild/rival/level). The
# sets go into maisonpkN entries PIKE_WILD_FIRST.. (pike.WILD_SETS), written by frontier/overlay.py: maisonpkN has 999
# entries, 0-216 used by the Maison's trainers (maisontrN's highest index is 216) and 217-998 all zero (measured
# 2026-11-10). From PIKE_WILD_FAR on the level is 50 - 5, below it 50 - 4. Work free per frontier/ids.py
# (2026-11-10); REPARTO.md.
PIKE_WILD = 16675
PIKE_WILD_FIRST, PIKE_WILD_FAR = 217, 219
# Battle Pyramid (frontier/asm/pyramid.s, frontier/pyramid.py): with WORK_ROUTE = ROUTE['pyramid'] the party slots
# chosen in the lobby are saved here when its facility work is deleted (the count 3 in PYRAMID_COUNT) and become the
# selection of every floor battle. Free per frontier/ids.py (2026-11-05); assigned in frontier/REPARTO.md.
PYRAMID_SEL = (16681, 16682, 16683)
PYRAMID_COUNT = 16685
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
             **ae.CONSTANTS, **pe.CONSTANTS,
             'RENTALS': len(WORK_SETS), 'WORK_RIVAL': WORK_RIVAL[0],
             'MAISON_TO_WORKS': MAISON_BASE - SAVE_WORKS,
             'ROUTES': len(STREAK_ROUTES), 'WORK_ROUTE': WORK_ROUTE,
             'DOME_ROUTE': ROUTE['dome'], 'DOME_FIGHT0': DOME_FIGHT[0], 'DOME_FORCED0': DOME_FORCED[0],
             'DOME_FIGHTERS': len(DOME_FIGHT),
             'PIKE_ROUTE': ROUTE['pike'], 'PIKE_HP0': PIKE_HP[0], 'PIKE_ST0': PIKE_ST[0], 'PIKE_FIGHTERS': len(PIKE_HP),
             'PIKE_WILD': PIKE_WILD, 'PIKE_WILD_FAR': PIKE_WILD_FAR,
             'PIKE_PP0': PIKE_PP[0][0], 'PIKE_PP_GAP': 2 * (PIKE_PP[1][0] - PIKE_PP[0][0]) - 2,
             'PYRAMID_ROUTE': ROUTE['pyramid'], 'PYRAMID_SEL0': PYRAMID_SEL[0], 'PYRAMID_COUNT': PYRAMID_COUNT,
             'PYRAMID_PICKS': len(PYRAMID_SEL)}
assert list(WORK_SETS) == [WORK_SETS[0] + k for k in range(3)] and 0 < WORK_IV - WORK_SETS[0] < 128   # rental.s: sub
assert 0 < WORK_IV - WORK_RIVAL[0] < 128 and 2 * (WORK_IV - 0x4000) < 256                              # rental.s: imm8
assert WORK_FRECORD == WORK_FSTREAK + 2      # the accessors read the record at slot + 0x1c8
assert sorted(STREAK_ROUTES) == list(range(1, 8))   # modes.s has seven mode_config entries
assert 0 < CONSTANTS['MAISON_TO_WORKS'] < 0x10000      # modes.s: two subs, bits 8-15 and 0-7
_streak_works = [w for _, s in STREAK_ROUTES.values() for w in (s, s + 1, s + 2)]
assert len(set(_streak_works)) == len(_streak_works) and WORK_ROUTE == WORK_FSTREAK + 1
assert 0 < WORK_IV - WORK_ROUTE < 128 and 2 * (WORK_ROUTE - 0x4000) < 256           # rental.s, dome.s: imm8 offsets
assert DOME_FIGHT[1] == DOME_FIGHT[0] + 1 and DOME_FORCED[1] == DOME_FORCED[0] + 1   # dome.s reads them in pairs
assert 0 < DOME_FIGHT[0] - WORK_ROUTE and len(DOME_FIGHT) == len(DOME_FORCED) == 2
assert list(PIKE_HP) == [PIKE_HP[0] + k for k in range(3)] and list(PIKE_ST) == [PIKE_ST[0] + k for k in range(3)]
assert 0 < 2 * (PIKE_ST[0] - PIKE_HP[0]) < 256                                       # pike.s: ldrh/strh imm8
assert 0 <= 2 * (PIKE_WILD - 0x4000) - 0x200 < 256 and PIKE_WILD_FIRST > 0               # pike.s: imm8 after +0x200
assert list(PYRAMID_SEL) == [PYRAMID_SEL[0] + k for k in range(3)] and 0 < PYRAMID_COUNT - PYRAMID_SEL[0] < 128
assert 0 < 2 * (PYRAMID_SEL[0] - WORK_ROUTE) < 0x10000                                # pyramid.s: ADDW


def word(data, va):
    return struct.unpack_from('<I', data, va - BASE)[0]


def arm_branch(source, target, link=False):
    delta = (target - source - 8) >> 2
    return (0xEB000000 if link else 0xEA000000) | (delta & 0xFFFFFF)


def link(asms, at, entry, constants, functions):
    """(.text bytes linked at `at`, {global symbol: address}) of `asms` assembled with `constants`."""
    with tempfile.TemporaryDirectory() as tmp:
        elf, binary = (Path(tmp) / n for n in ('hook.elf', 'hook.bin'))
        defs = [a for k, v in constants.items() for a in ('--defsym', f'{k}={v}')]
        objs = [Path(tmp) / f'{src.stem}.o' for src in asms]
        for src, obj in zip(asms, objs):
            subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, src], check=True)
        syms = [f'--defsym={k}={v:#x}' for k, v in functions.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={at:#x}', '-e', entry, *syms, '-o', elf, *objs], check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        names = subprocess.run(['arm-none-eabi-nm', elf], check=True, capture_output=True, text=True).stdout
        symbols = {n: int(a, 16) for a, t, n in (line.split() for line in names.splitlines()) if t == 'T'}
        return binary.read_bytes(), symbols


def mode_constants():
    """modes.s tables (frontier/modes.py): CONFIG work per route and the (streak, record) works of every bank, as
    2*(work - 0x4000), in mode_banks order (M0 routes 1-7, M1 routes 1-7, M2 routes 1-2, M3 routes 1-2)."""
    import modes
    rows = [modes.bank(route, mode) for mode, routes in ((0, range(1, 8)), (1, range(1, 8)), (2, (1, 2)),
                                                           (3, (1, 2))) for route in routes]
    off = lambda w: 2 * (w - 0x4000)
    return {**{f'CFG_{r}': off(modes.CONFIG[r]) for r in range(1, 8)},
            **{f'{k}_{i}': off(w) for i, row in enumerate(rows) for k, w in zip('SR', row)}}


def assemble():
    """(hook bytes at HOOKS, {global symbol: address}). Fails if any of it would fall in Luma's reserve or past
    the cave."""
    hook, symbols = link(ASMS, HOOKS, 'rental_hook', {**CONSTANTS, **mode_constants()},
                         {**FUNCTIONS, 'STREAK_INC_BODY': STREAK_INC_BODY, 'mode_live': MODE_LIVE})
    if symbols['rental_hook'] != HOOKS:
        raise ValueError('rental_hook is not at the start of the hooks')
    if HOOKS + len(hook) > CAVE_END:
        raise ValueError(f'code.bin hooks {len(hook)} bytes: past the cave end {CAVE_END:#x} '
                         f'({CAVE_END - HOOKS} bytes after the Luma reserve)')
    if any(CAVE <= a < HOOKS for a in symbols.values()):
        raise ValueError('code.bin hooks inside the Luma reserve')
    return hook, symbols


def mode_live_code(symbols):
    """ACTIVE guard in the retired Doubles increment body; guarded against the fixed baseline in build()."""
    constants = {f'ACTIVE_{route}': 2 * (ACTIVE_WORK[facility] - 0x4000)
                 for route, (facility, _) in STREAK_ROUTES.items()}
    blob, _ = link([ROOT / 'frontier/asm/modes_live.s'], MODE_LIVE, 'mode_live', constants,
                   {'MODE_OF': symbols['mode_of']})
    if len(blob) > 4 * len(MODE_LIVE_BEFORE):
        raise ValueError('mode_live exceeds the retired Doubles increment body')
    return blob


# DllBattle.cro (v0.5) file offset of the battle-time routines (CRO_ASMS): after palace_cro.s (palace_ai.AT,
# 0xd7630-0xd7868), in the zero padding of the declared code region before .rodata (palace_ai.RODATA 0xd8000).
BATTLE_CRO_AT = 0xD7870
# Where Azahar loaded the v0.5 DllBattle.cro in the measured battles (palace_engine; work/frontier/palace/
# b2-gdb-m3b.log). Only for laboratory GDB probes: the game code never assumes it.
DLLBATTLE_AZAHAR = 0x6F3000


def battle_cro_runtime(name, base=DLLBATTLE_AZAHAR):
    """Run-time address of a battle_cro_code() symbol for lab probes (CRO loaded at `base`)."""
    return base + battle_cro_code()[1][name]


def battle_cro_code():
    """(blob linked at BATTLE_CRO_AT, {symbol: DllBattle.cro file offset}) of CRO_ASMS."""
    import palace_ai
    blob, symbols = link(CRO_ASMS, BATTLE_CRO_AT, 'arena_enter', CONSTANTS, {'ARENA_UDIV': ae.UDIV})
    _, palace_symbols = palace_ai.assemble()
    if palace_symbols['palace_cro_end'] > BATTLE_CRO_AT or BATTLE_CRO_AT + len(blob) > palace_ai.RODATA:
        raise ValueError(f'battle CRO code {BATTLE_CRO_AT:#x}+{len(blob)} does not fit between palace_cro.s '
                         f'and .rodata')
    if not palace_ai.TEXT_END <= BATTLE_CRO_AT:
        raise ValueError('battle CRO code is not after .text')
    return blob, symbols


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
    if tuple(word(code, MODE_LIVE + 4 * i) for i in range(len(MODE_LIVE_BEFORE))) != MODE_LIVE_BEFORE:
        sys.exit('retired Doubles increment body differs')
    live = mode_live_code(symbols)
    code[MODE_LIVE - BASE:MODE_LIVE - BASE + len(live)] = live
    if any(code[CAVE - BASE:CAVE_END - BASE]):
        sys.exit('the code.bin cave is not zero padding')
    code[HOOKS - BASE:HOOKS - BASE + len(hook)] = hook
    site = [0xE1A00006,                               # mov r0, r6        (work)
            0xE1A01009,                               # mov r1, sb        (battle party)
            arm_branch(SITE + 8, HOOKS, link=True),   # bl  rental_hook (Factory: continues at 0x1e3ddc)
            0xE1A08000,                               # mov r8, r0        (player party, as 0x1e3d94)
            0xE1A00000]                               # nop               (0x3b5d34 already called)
    struct.pack_into(f'<{len(site)}I', code, SITE - BASE, *site)
    if word(code, RIVAL_SITE) != RIVAL_BEFORE:
        sys.exit(f'rival site word differs: {word(code, RIVAL_SITE):08x}')
    struct.pack_into('<I', code, RIVAL_SITE - BASE, arm_branch(RIVAL_SITE, symbols['rival_hook'], link=True))
    if word(code, COUNT_SITE) != COUNT_BEFORE:
        sys.exit(f'rival count site word differs: {word(code, COUNT_SITE):08x}')
    struct.pack_into('<I', code, COUNT_SITE - BASE, arm_branch(COUNT_SITE, symbols['dome_count'], link=True))
    if word(code, CAP_SITE) != CAP_BEFORE:
        sys.exit(f'level cap site word differs: {word(code, CAP_SITE):08x}')
    struct.pack_into('<I', code, CAP_SITE - BASE, arm_branch(CAP_SITE, symbols['mode_cap'], link=True))
    got = tuple(word(code, STREAK_INC_BODY + 4 * i) for i in range(len(STREAK_INC_BODY_WORDS)))
    if got != STREAK_INC_BODY_WORDS:
        sys.exit(f'streak increment body {STREAK_INC_BODY:#x} differs')
    if word(code, LEVEL_SITE) != LEVEL_BEFORE:
        sys.exit(f'rival level site word differs: {word(code, LEVEL_SITE):08x}')
    struct.pack_into('<I', code, LEVEL_SITE - BASE, arm_branch(LEVEL_SITE, symbols['pike_level'], link=True))
    if word(code, BUILD_SITE) != BUILD_BEFORE:
        sys.exit(f'party build call {BUILD_SITE:#x} differs: {word(code, BUILD_SITE):08x}')
    struct.pack_into('<I', code, BUILD_SITE - BASE, arm_branch(BUILD_SITE, symbols['pike_build'], link=True))
    got = tuple(word(code, ISWIN + 4 * i) for i in range(4))
    if got != ISWIN_BEFORE:
        sys.exit(f'IsWin {ISWIN:#x} differs: {[f"{w:08x}" for w in got]}')
    struct.pack_into('<I', code, ISWIN - BASE, arm_branch(ISWIN, symbols['pike_iswin']))
    if word(code, DELETE_SITE) != arm_branch(DELETE_SITE, FUNCTIONS['WORK_DELETE_CALL'], link=True):
        sys.exit(f'work delete call {DELETE_SITE:#x} differs: {word(code, DELETE_SITE):08x}')
    struct.pack_into('<I', code, DELETE_SITE - BASE, arm_branch(DELETE_SITE, symbols['pyramid_save'], link=True))
    if word(code, ae.START) != ae.START_BEFORE:
        sys.exit(f'Arena StartBattle site {ae.START:#x} differs')
    struct.pack_into('<I', code, ae.START - BASE, arm_branch(ae.START, symbols['arena_start']))
    for va, (stub, *before) in STREAK_SITES.items():
        if [word(code, va), word(code, va + 4)] != before:
            sys.exit(f'streak accessor table {va:#x} differs')
        struct.pack_into('<2I', code, va - BASE, symbols[stub], symbols[stub])
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
FIELD_CRO = 'DllField.cro'
FIELD_CRO_SHA256 = '8c9da930a13b56b797dedfc87940b85b5b3cad9a1cf35390c4796b0c6f5cb53a'
PIKE_PARAM_SITE = 0x4E644
PIKE_PARAM_BEFORE = bytes.fromhex('0800a0e134c9feeb060050e11501009a')


def battle_cro(romfs=MOD_ROMFS):
    """v0.5 + Pike copy-back + Arena and Palace bridges, guarded together, with updated CRO/CRR hashes; DllField.cro
    with the Pike's bridge and the Frontier Brains (frontier/brains.py, frontier/asm/brains_cro.s).

    Additional facility bridges can extend the write list before the single rehash.
    Arena acts only with its setup bit; the unmarked path replays retail instructions.
    """
    from build_patch import guarded_writes, rehash_cro, update_crr
    original = (romfs / BATTLE_CRO).read_bytes()
    import hashlib
    if hashlib.sha256(original).hexdigest() != BATTLE_CRO_SHA256:
        sys.exit(f'{BATTLE_CRO}: not the v0.5 one')
    got = struct.unpack_from('<3I', original, COPY_BACK)
    if got != COPY_BACK_BEFORE:
        sys.exit(f'{BATTLE_CRO} {COPY_BACK:#x} differs: {[f"{w:08x}" for w in got]}')
    _, symbols = assemble()
    blob, cro_symbols = battle_cro_code()
    writes = [dict(offset=COPY_BACK, before=struct.pack('<3I', *COPY_BACK_BEFORE).hex(),
                   after=struct.pack('<3I', *COPY_BACK_AFTER).hex()), *ae.cro_writes(cro_symbols),
              *pe.cro_writes(cro_symbols),
              dict(offset=BATTLE_CRO_AT, before=bytes(len(blob)).hex(), after=blob.hex())]
    changed = guarded_writes(original, dict(path=BATTLE_CRO, sha256=BATTLE_CRO_SHA256, writes=writes))
    changed = rehash_cro(original, changed)
    crr = update_crr((romfs / CRR).read_bytes(), original, changed)
    field = (romfs / FIELD_CRO).read_bytes()
    field_write = dict(offset=PIKE_PARAM_SITE, before=PIKE_PARAM_BEFORE.hex(),
                       after=struct.pack('<4I', 0xE59FC004, 0xE12FFF3C, 0xEA000000,
                                         symbols['pike_param']).hex())
    import brains                       # DllField natives SetTrainer/StartBattle -> the Frontier Brains (brains.py)
    field_changed = guarded_writes(field, dict(path=FIELD_CRO, sha256=FIELD_CRO_SHA256,
                                               writes=[field_write, *brains.cro_writes()]))
    field_changed = rehash_cro(field, field_changed)
    crr = update_crr(crr, field, field_changed)
    return {BATTLE_CRO: changed, FIELD_CRO: field_changed, CRR: crr}


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
    print(f'Luma reserve {CAVE:#x}-{HOOKS:#x}; hook {len(hook)} bytes at {HOOKS:#x}-{HOOKS + len(hook):#x} '
          f'({CAVE_END - HOOKS - len(hook)} free); site {SITE:#x}: '
          + ' '.join(f'{w:08x}' for w in site))
    print(f'wrote {out}/code.bin (sha256 {sha256(out / "code.bin")[:16]}…) and code.ips ({len(ips)} bytes)')


if __name__ == '__main__':
    main()
