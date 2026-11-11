#!/usr/bin/env python3
"""Battle Dome v1 (reports/diseno/domo.md): the zone script of its interior (a clone of the Battle Maison hall) and
its parts of shared script 5.

Singles, Level 50, rank Normal, with three of the player's own Pokémon entered for the challenge. Before each battle
the player sees the rival's three Pokémon and picks two of the three entered; the rival brings two of its three (at
random). A tournament is four battles (round 1, round 2, semifinal, final); BP after each final won
(data.FRONTIER_BP['dome'], by tournaments won); own streak (battles won) and record by route 5; the loss ends the
challenge; the Maison's continue / rest / retire menu after every win, so the challenge can be paused between any
two battles and goes on with the next tournament after a final.

Zone script: the **retail** zone 517 script (no Factory option), with these changes (addresses of
work/frontier/survey/zone517.lst, reports/frontier.md §1), as frontier/tower.py:
- reception (0x14f4): patch.WORK_ROUTE = 0 right after BattleInstWorkCreate;
- menu result (0x1634): option 0 («Combatir») calls `dome_reception`; its result is the «back to the menu» local;
- `dome_reception`: refuses while another facility has a challenge in progress (factory.busy_check); SetRank(0),
  WORK_ROUTE = ROUTE (the code.bin streak hooks then use the Dome's streak and record works); a new challenge
  (ACTIVE = 0) starts its streak at 0; the entry (GlobalCall GLOBAL_ENTRY: three party slots, no eggs, no repeated
  species or held item) into TEAM, also on resuming a paused challenge (deviation: Emerald keeps the team); then
  ACTIVE = 1, the Maison's challenge routine 0x18f8(rank 0, Singles, 0) as the Factory calls it (works 0x800C-E
  set, no mode selection app); ACTIVE stays 1 only if the streak is not 0 (paused), and WORK_ROUTE = 0;
- party selection (0x457c, BattleHouse_CallPartySelectApp): skipped with the Dome's route, answering «accepted»
  (work 0x800C = 1) as overlay.maison_program does for the Factory;
- before StartBattle (0x1edc; the rival trainer is already on the floor): with the Dome's route, DOME_STREAK =
  GetMyWinCount(0, 0) and GlobalCall GLOBAL_ROUND (round name, the rival's three sets, the player's two fighters);
- lost battle (0x2210) and the «did not save» cleanup (0x1458): ACTIVE = 0;
- BP (0x3de4): with the Dome's route, none for battles 1-3 of a tournament; after the final, GlobalCall GLOBAL_WON
  (the champion's line) and data.FRONTIER_BP['dome'][tournaments - 1] (last value repeated).

Shared script 5 (patch.GLOBAL_ROW: ids 9770-9779, text patch.TEXT_FACTORY; the Factory uses 9771-9772), lines after
the Factory's in text 637 (LINE_BASE):
- GLOBAL_ENTRY `dome_entry`: three times the game's party screen (CallPokeSelect(1, 0x800C, 0, 1), as 17 retail
  uses; 6 = cancelled) with checks by PokePartyGetParam(slot, param, 0): param 8 egg, 0 species, 12 held item
  (measured in DllField.cro 0x4e618's jump table: 0 -> 0x1532d8 block A +0, 12 -> 0x4d2454 block A +2, 8 -> egg
  flag). GlobalSetParentParam(0, 1) once TEAM is written, 0 if cancelled.
- GLOBAL_ROUND `dome_round`: level = min(streak / 4, last) of the Factory's rental levels (factory.slots); three
  sets drawn from it with all species and items different (so the code.bin builder never redraws a forced slot
  forever, frontier/asm/dome.s); RIVAL = the three; a menu shows them («Species (Item)», factory.line_of); two menus
  pick the fighters by nickname (WordSetTemotiMonsNickName(buffer k, slot), lines «[VAR 0102 k]»; B goes back to
  the rival's team); patch.DOME_FIGHT = their party slots, patch.DOME_FORCED = two of RIVAL at random, in random
  order (the rival's two; the code.bin hook reads them).
- GLOBAL_WON `dome_won`: the champion's line.

Known deviations (design §1, §6): the Maison's texts and receptionist; no bracket, no simulated 14 others, no
ranking, no rival style, no Tucker, no Doubles or Open Level; the streak counts battles (tournaments = streak / 4);
the entry has no banned species list and does not cap levels (the builder scales those above 50 to 50, 0x1e3ddc);
the rival's two are random, not chosen against the player's team; the rival's IVs are the Maison's by streak; the
Maison's boss can appear on the Dome streak (its sets are replaced by the forced ones).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from pawn import OP, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import battle_video  # noqa: E402
import patch  # noqa: E402

FACILITY = 'dome'
ZONE = 456                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§26)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
DOME_BP = fd.FRONTIER_BP[FACILITY]
ROUNDS = 4                       # battles per tournament (16 trainers)
ENTRIES = 3                      # Pokémon entered
FIGHTERS = len(patch.DOME_FIGHT)  # 2 per battle, on each side
# Saved works, free per frontier/ids.py (2026-11-04), assigned in frontier/REPARTO.md. The code.bin hook reads
# patch.DOME_FIGHT and patch.DOME_FORCED; these only the scripts.
TEAM = (16493, 16494, 16495)     # party slots entered
WORK_STREAK = 16651              # streak handed from the zone script to GLOBAL_ROUND (the child may not call Maison natives)
RIVAL = (16653, 16654, 16655)    # the rival's three sets this battle (rental work value: bit 15 Super, bits 0-9 index)
WORK_RNG = 16659                 # generator state between draws
WORKS = (*TEAM, WORK_STREAK, *RIVAL, WORK_RNG, *patch.DOME_FIGHT, *patch.DOME_FORCED)
GLOBAL_ENTRY, GLOBAL_ROUND, GLOBAL_WON = 9773, 9774, 9775
STREAK_LIMIT = 0x7FFF
POKE_SELECT_ARGS = (1, factory.WORK_SELECT_RESULT, 0, 1)   # CallPokeSelect: 17 of 23 retail uses
SELECT_CANCEL = 6
PARAM_SPECIES, PARAM_EGG, PARAM_ITEM = 0, 8, 12
LINE_BASE = factory.LINE_S + sum(1 for rank, _ in factory.slots()[0] if rank == 'S')  # after the Factory's lines
TEXTS = {
    'es': {'entry': ['Elige el primer Pokémon que vas a inscribir.',
                     'Elige el segundo Pokémon que vas a inscribir.',
                     'Elige el tercer Pokémon que vas a inscribir.'],
           'egg': 'Un Huevo no puede participar en el torneo.',
           'dup': 'Inscribe tres Pokémon distintos, de especies\ndistintas y sin repetir objeto.',
           'rounds': ['¡Primera ronda del torneo!', '¡Segunda ronda del torneo!', '¡Semifinal del torneo!',
                      '¡Final del torneo!'],
           'preview': 'Estos son los Pokémon de tu rival.\nSolo sacará a dos de ellos.',
           'first': '¿Qué Pokémon combatirá primero?',
           'second': '¿Y cuál combatirá en segundo lugar?',
           'won': '¡Enhorabuena! ¡Has ganado el torneo\ndel Domo Batalla!'},
    'en': {'entry': ['Choose the first Pokémon to enter.', 'Choose the second Pokémon to enter.',
                     'Choose the third Pokémon to enter.'],
           'egg': 'An Egg cannot take part in the tournament.',
           'dup': 'Enter three different Pokémon of different\nspecies, holding different items.',
           'rounds': ['Tournament round one!', 'Tournament round two!', 'Tournament semifinal!',
                      'Tournament final!'],
           'preview': 'These are your opponent’s Pokémon.\nIt will only send out two of them.',
           'first': 'Which Pokémon will battle first?',
           'second': 'And which one will battle second?',
           'won': 'Congratulations! You won the\nBattle Dome tournament!'},
}
LINE_ENTRY = tuple(LINE_BASE + k for k in range(ENTRIES))
LINE_EGG = LINE_BASE + 3
LINE_DUP = LINE_BASE + 4
LINE_ROUNDS = tuple(LINE_BASE + 5 + k for k in range(ROUNDS))
LINE_PREVIEW = LINE_BASE + 9
LINE_FIRST, LINE_SECOND = LINE_BASE + 10, LINE_BASE + 11
LINE_NICK = tuple(LINE_BASE + 12 + k for k in range(ENTRIES))   # «[VAR 0102 k]»: nickname in word buffer k
LINE_WON = LINE_BASE + 15
NICK_VAR = 0x0102                # nickname tag (story text: «[VAR 0102 0] y [VAR 0102 1] están estupendamente»)


def lines(lang):
    """Text 637 lines of the Dome, from LINE_BASE, in one game language."""
    t = TEXTS[factory.LANG[lang]]
    out = [*t['entry'], t['egg'], t['dup'], *t['rounds'], t['preview'], t['first'], t['second'],
           *(f'[VAR {NICK_VAR:04X} {k}]' for k in range(ENTRIES)), t['won']]
    assert len(out) == LINE_WON - LINE_BASE + 1
    return out


# --- shared script 5 -------------------------------------------------------------------------------------------

def _say(r, helpers, line):
    r.call(helpers['msg'], line, 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)


def entry_routine(p, helpers):
    """dome_entry(): TEAM = three party slots; GlobalSetParentParam(0, 1), or 0 if the player cancelled."""
    names = ['sel', *(f'{f}{k}' for f in ('slot', 'species', 'item') for k in range(ENTRIES))]
    r = factory.Routine(p, 'dome_entry', names)
    cancel = 'dome_entry_cancel'
    for n in range(ENTRIES):
        again = f'dome_entry_again{n}'
        r.p.label(again)
        _say(r, helpers, LINE_ENTRY[n])
        r.sysreq('CallPokeSelect', *POKE_SELECT_ARGS)
        r.sysreq('WorkGet', factory.WORK_SELECT_RESULT)
        r.store('sel')
        r.const_alt(SELECT_CANCEL - 1)
        r.op('JSGRTR', cancel)           # 6 = cancelled (or anything past the party)
        r.load('sel')
        r.const_alt(0)
        r.op('JSLESS', cancel)
        hatched = r.new_label('hatched')
        r.sysreq('PokePartyGetParam', 'sel', PARAM_EGG, 0)
        r.op('JZER', hatched)
        _say(r, helpers, LINE_EGG)
        r.op('JUMP', again)
        r.p.label(hatched)
        r.sysreq('PokePartyGetParam', 'sel', PARAM_SPECIES, 0)
        r.store(f'species{n}')
        r.sysreq('PokePartyGetParam', 'sel', PARAM_ITEM, 0)
        r.store(f'item{n}')
        dup, unique = r.new_label('dup'), r.new_label('unique')
        for j in range(n):
            r.load('sel')
            r.load_alt(f'slot{j}')
            r.op('JEQ', dup)
            r.load(f'species{n}')
            r.load_alt(f'species{j}')
            r.op('JEQ', dup)
            no_item = r.new_label('noitem')
            r.load(f'item{n}')
            r.op('JZER', no_item)            # two Pokémon holding nothing are fine
            r.load_alt(f'item{j}')
            r.op('JEQ', dup)
            r.p.label(no_item)
        r.op('JUMP', unique)
        r.p.label(dup)
        _say(r, helpers, LINE_DUP)
        r.op('JUMP', again)
        r.p.label(unique)
        r.load('sel')
        r.store(f'slot{n}')
    for k, work in enumerate(TEAM):
        r.sysreq('WorkSet', work, f'slot{k}')
    r.sysreq('GlobalSetParentParam', 0, 1)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(cancel)
    r.sysreq('GlobalSetParentParam', 0, 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def round_routine(p, helpers, levels):
    """dome_round(): the round's line, the rival's three sets, the player's two fighters, the rival's two."""
    state, table = p.data_labels['factory_rng'], p.data_labels['factory_slots']
    level_table = p.data_labels['factory_levels']
    names = ['streak', 'level', 'first', 'count', 'sel', 'value', 'pick0', 'pick1', 'drop',
             *(f'{f}{k}' for f in ('slot', 'cell', 'species', 'item', 'team') for k in range(ENTRIES))]
    r = factory.Routine(p, 'dome_round', names)
    # Seed as the Factory's draft: real-time seconds + 32767 × the saved state.
    r.sysreq('WorkGet', WORK_RNG)
    r.op('SMUL_P_C', 0x7FFF)
    r.op('PUSH_PRI', 0)
    r.sysreq('_GetRealTimeToSecond')
    r.op('PALT', 0)
    r.op('ADD', 0)
    r.op('STOR_P_PRI', state)

    r.sysreq('WorkGet', WORK_STREAK)
    r.store('streak')
    r.op('MOVE_ALT', 0)
    r.const(ROUNDS)
    r.op('SDIV_ALT', 0)                  # PRI = tournaments won
    r.store('level')
    r.const_alt(len(levels) - 1)
    capped = r.new_label('level')
    r.op('JSLEQ', capped)
    r.set('level', len(levels) - 1)
    r.p.label(capped)
    for name, offset in (('first', 0), ('count', 1)):
        r.load('level')
        r.op('SMUL_P_C', 2)
        if offset:
            r.add(offset)
        r.cell(level_table)
        r.store(name)

    # The rival's three: species and items all different.
    for k in range(ENTRIES):
        again = r.new_label(f'draw{k}')
        r.p.label(again)
        r.call('factory_rand', 'count')
        r.load_alt('first')
        r.op('ADD', 0)
        r.store(f'slot{k}')
        r.cell(table)
        r.store(f'cell{k}')
        r.field(11, 10)
        r.store(f'species{k}')
        r.load(f'cell{k}')
        r.field(21, 10)
        r.store(f'item{k}')
        for j in range(k):
            for f in ('species', 'item'):
                r.load(f'{f}{k}')
                r.load_alt(f'{f}{j}')
                r.op('JEQ', again)
        # cell -> rental work value: index (bits 0-9) | Super (cell bit 10) << 15
        r.load(f'cell{k}')
        r.field(0, 10)
        r.store('value')
        r.load(f'cell{k}')
        r.field(10, 1)
        normal = r.new_label('normal')
        r.op('JZER', normal)
        r.load('value')
        r.add(patch.SUPER)
        r.store('value')
        r.p.label(normal)
        r.load('value')
        r.store(f'cell{k}')             # from here on: the work value
        r.sysreq('WorkSet', RIVAL[k], 'value')

    # Round name (streak % 4).
    r.load('streak')
    r.op('MOVE_ALT', 0)
    r.const(ROUNDS)
    r.op('SDIV_ALT', 0)
    r.op('SMUL_P_C', ROUNDS)
    r.load_alt('streak')
    r.op('SUB_ALT', 0)                   # PRI = streak % 4
    r.add(LINE_ROUNDS[0])
    r.store('value')
    r.call(helpers['msg'], 'value', 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)

    for k, work in enumerate(TEAM):
        r.sysreq('WorkGet', work)
        r.store(f'team{k}')
        r.sysreq('WordSetTemotiMonsNickName', k, f'team{k}')

    preview = 'dome_round_preview'
    r.p.label(preview)
    r.call(helpers['msg'], LINE_PREVIEW, 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
    for k in range(ENTRIES):
        r.p.push(0)
        r.p.push(k)
        r.line_of_slot(f'slot{k}', levels[3][0])
        r.op('PUSH_PRI', 0)
        r.p.emit('SYSREQ_N', 'ListMenuAdd', 12)
    r.call(helpers['menu_run'])          # any answer goes on
    r.call(helpers['msg_close'], 0)

    def pick(prompt, local, skip):
        r.call(helpers['msg'], prompt, 1, 0, 256, 0)
        r.call(helpers['msg_wait'])
        r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
        for k in range(ENTRIES):
            if skip is not None:
                other = r.new_label('pickskip')
                r.load(skip)
                r.op('EQ_P_C_PRI', k)
                r.op('JNZ', other)
            r.sysreq('ListMenuAdd', LINE_NICK[k], k, 0)
            if skip is not None:
                r.p.label(other)
        r.call(helpers['menu_run'])
        r.store(local)
        r.call(helpers['msg_close'], 0)
        r.load(local)
        r.const_alt(ENTRIES - 1)
        r.op('JSGRTR', preview)          # B (65535): back to the rival's team
        r.load(local)
        r.const_alt(0)
        r.op('JSLESS', preview)
        if skip is not None:
            r.load(local)
            r.load_alt(skip)
            r.op('JEQ', preview)

    pick(LINE_FIRST, 'pick0', None)
    pick(LINE_SECOND, 'pick1', 'pick0')
    for n, work in enumerate(patch.DOME_FIGHT):
        done = r.new_label('fight')
        for k in range(ENTRIES):
            other = r.new_label('fightk')
            r.load(f'pick{n}')
            r.op('EQ_P_C_PRI', k)
            r.op('JZER', other)
            r.sysreq('WorkSet', work, f'team{k}')
            r.op('JUMP', done)
            r.p.label(other)
        r.p.label(done)

    # The rival's two: drop one of the three at random, then a random order.
    r.call('factory_rand', ENTRIES)
    r.store('drop')
    forced = r.new_label('forced')
    for d in range(ENTRIES):
        other = r.new_label('drop')
        keep = [k for k in range(ENTRIES) if k != d]
        r.load('drop')
        r.op('EQ_P_C_PRI', d)
        r.op('JZER', other)
        straight = r.new_label('straight')
        r.call('factory_rand', 2)
        r.op('JZER', straight)
        keep.reverse()
        r.sysreq('WorkSet', patch.DOME_FORCED[0], f'cell{keep[0]}')
        r.sysreq('WorkSet', patch.DOME_FORCED[1], f'cell{keep[1]}')
        r.op('JUMP', forced)
        r.p.label(straight)
        keep.reverse()
        r.sysreq('WorkSet', patch.DOME_FORCED[0], f'cell{keep[0]}')
        r.sysreq('WorkSet', patch.DOME_FORCED[1], f'cell{keep[1]}')
        r.op('JUMP', forced)
        r.p.label(other)
    r.p.label(forced)
    r.op('LOAD_P_PRI', state)
    r.field(16, 16)
    r.store('value')
    r.sysreq('WorkSet', WORK_RNG, 'value')
    r.op('ZERO_PRI', 0)
    r.ret()


def won_routine(p, helpers):
    r = factory.Routine(p, 'dome_won', [])
    _say(r, helpers, LINE_WON)
    r.op('ZERO_PRI', 0)
    r.ret()


def shared_cases(levels):
    """(case value, routine, builder(p, helpers)) for factory.shared_program."""
    return [(GLOBAL_ENTRY, 'dome_entry', entry_routine),
            (GLOBAL_ROUND, 'dome_round', lambda p, h: round_routine(p, h, levels)),
            (GLOBAL_WON, 'dome_won', won_routine)]


# --- zone script --------------------------------------------------------------------------------------------------

def reception_routine(p):
    """dome_reception() -> 1 = back to the reception menu, 0 = challenge played."""
    r = factory.Routine(p, 'dome_reception', ['declined'])
    factory.busy_check(r, FACILITY, 'dome_refused')
    r.sysreq('SetRank', 0)                      # the streak route covers rank Normal only
    r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
    r.sysreq('WorkGet', ACTIVE)
    r.op('JNZ', 'dome_resume')                  # paused challenge: keep the streak
    r.sysreq('WorkSet', STREAK, 0)              # a new challenge starts at battle 1
    r.p.label('dome_resume')
    r.sysreq('GlobalCall', GLOBAL_ENTRY)
    r.sysreq('GlobalGetChildParam', 0)
    r.op('JZER', 'dome_back')                   # entry cancelled: nothing else changes
    r.sysreq('WorkSet', ACTIVE, 1)
    r.sysreq('WorkSet', factory.WORK_SELECT_RESULT, 1)
    r.sysreq('WorkSet', factory.WORK_SELECT_TYPE, 0)
    r.sysreq('WorkSet', factory.WORK_SELECT_X, 0)
    r.call(factory.CHALLENGE, 0, 0, 0)
    r.store('declined')
    r.sysreq('GetMyWinCount', 0, 0)             # the Dome streak (route still set)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', 'dome_kept')                 # 0 < streak: paused (or declined while paused)
    r.sysreq('WorkSet', ACTIVE, 0)
    r.p.label('dome_kept')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.load('declined')
    r.op('EQ_P_C_PRI', 1)                       # 1 = declined the confirmation: back to the menu
    r.ret()
    r.p.label('dome_back')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.p.label('dome_refused')
    r.const(1)
    r.ret()


def before_battle_routine(p):
    """dome_before_battle(): with the Dome's route, the round, the preview and the picks (GLOBAL_ROUND)."""
    r = factory.Routine(p, 'dome_before_battle', ['streak'])
    r.sysreq('WorkGet', patch.WORK_ROUTE)
    r.op('EQ_P_C_PRI', ROUTE)
    r.op('JZER', 'dome_before_battle_end')
    r.sysreq('GetMyWinCount', 0, 0)
    r.store('streak')
    r.sysreq('WorkSet', WORK_STREAK, 'streak')
    r.sysreq('GlobalCall', GLOBAL_ROUND)
    r.p.label('dome_before_battle_end')
    r.op('ZERO_PRI', 0)
    r.ret()


def battle_points(p):
    """Dome BP, inserted in the Maison's BP routine 0x3de4 once its locals exist (-4 win count, -8 BP), while
    WORK_ROUTE = ROUTE: after a final, the champion's line and DOME_BP[tournaments - 1]; none otherwise."""
    start = factory._index(p, factory.BATTLE_POINTS)
    at = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
              and p.items[i].op == OP['STOR_P_S_PRI'] and p.items[i].args == [-4])
    if p.items[at + 1].op != OP['PUSH_P_C'] or p.items[at + 1].args != [0]:
        raise ValueError('BP routine locals not found at 0x3e04')
    table = p.data_block('dome_bp', list(DOME_BP))
    b = _program(p)
    b.sysreq('WorkGet', patch.WORK_ROUTE)
    b.emit('EQ_P_C_PRI', ROUTE)
    b.emit('JZER', 'dome_bp_retail')
    b.sysreq('GetMyWinCount', 0, 0)
    b.emit('STOR_P_S_PRI', -4)
    b.emit('MOVE_ALT', 0)
    b.emit('CONST_P_PRI', ROUNDS)
    b.emit('SDIV_ALT', 0)                    # tournaments won = streak / 4
    b.emit('STOR_P_S_PRI', -8)
    b.emit('SMUL_P_C', ROUNDS)
    b.emit('LOAD_P_S_ALT', -4)
    b.emit('SUB_ALT', 0)                     # streak - 4 * tournaments
    b.emit('JNZ', 'dome_bp_none')
    b.sysreq('GlobalCall', GLOBAL_WON)
    b.emit('LOAD_P_S_PRI', -8)
    b.emit('ADD_P_C', -1)
    b.emit('CONST_P_ALT', len(DOME_BP) - 1)
    b.emit('JSLEQ', 'dome_bp_index')
    b.emit('CONST_P_PRI', len(DOME_BP) - 1)
    b.label('dome_bp_index')
    b.emit('SMUL_P_C', 4)
    b.emit('ADD_P_C', table)
    b.emit('LOAD_I', 0)
    b.emit('STOR_P_S_PRI', -8)
    b.emit('JUMP', factory.BATTLE_POINTS_GIVE)
    b.label('dome_bp_none')
    b.emit('STACK_P', 8)
    b.emit('ZERO_PRI', 0)
    b.emit('RETN', 0)
    b.label('dome_bp_retail')
    p.items[at + 2:at + 2] = b.items


def _program(p):
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    return body


def _ops(p, build):
    body = _program(p)
    build(body)
    return body.items


PARTY_SELECT = 'L457c'           # PROC: BattleHouse_CallPartySelectApp(arg, 0x800C) (overlay.PARTY_SELECT)
BEFORE_BATTLE = 'L1edc'          # battle loop: StartBattle(0, 1) follows


def dome_program(retail):
    """Zone 517's retail script with the Dome (module docstring)."""
    p = Program.from_script(retail)
    start = factory._index(p, 'L14f4')
    create = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
                  and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == p.native('BattleInstWorkCreate'))
    p.items[create + 1:create + 1] = _ops(p, lambda b: b.sysreq('WorkSet', patch.WORK_ROUTE, 0))
    at = factory._index(p, factory.RECEPTION_RESULT)
    head = p.items[at + 1:at + 3]
    if [o.op for o in head] != [OP['LOAD_P_S_PRI'], OP['JNZ']] or head[0].args != [-12] or head[1].args != ['L17b0']:
        raise ValueError('reception result check not found at 0x1634')

    def dispatch(b):                 # value 0 falls through here (others jump to 0x17b0)
        b.call('dome_reception')
        b.emit('STOR_P_S_PRI', factory.RECEPTION_AGAIN)
        b.emit('JUMP', factory.RECEPTION_NEXT)
    p.items[at + 3:at + 3] = _ops(p, dispatch)

    at = factory._index(p, PARTY_SELECT)
    if not (isinstance(p.items[at + 1], Op) and p.items[at + 1].op == OP['PROC']):
        raise ValueError('0x457c is not a routine start')

    def skip(b):
        b.sysreq('WorkGet', patch.WORK_ROUTE)
        b.emit('EQ_P_C_PRI', ROUTE)
        b.emit('JZER', 'dome_select_retail')
        b.sysreq('WorkSet', factory.WORK_SELECT_RESULT, 1)
        b.emit('CONST_P_PRI', 1)
        b.emit('RETN', 0)
        b.label('dome_select_retail')
    p.items[at + 2:at + 2] = _ops(p, skip)

    at = factory._index(p, BEFORE_BATTLE)
    following = [o for o in p.items[at + 1:at + 4] if isinstance(o, Op)]
    if [o.op for o in following] != [OP['PUSH_P_C'], OP['PUSH_P_C'], OP['SYSREQ_N']] \
            or following[2].args[0] != p.native('StartBattle'):
        raise ValueError('StartBattle not found at 0x1edc')
    p.items[at + 1:at + 1] = _ops(p, lambda b: b.call('dome_before_battle'))

    at = factory._index(p, factory.CLEANUP)
    if p.items[at + 1].op != OP['PROC']:
        raise ValueError('0x1458 is not a routine start')
    p.items[at + 2:at + 2] = _ops(p, lambda b: b.sysreq('WorkSet', ACTIVE, 0))
    at = factory._index(p, factory.LOST)  # before the loss is saved, so the save never holds a dead challenge
    if p.items[at + 1].op != OP['ZERO_P_S'] or p.items[at + 1].args != [-8]:
        raise ValueError('lost-battle path not found at 0x2210')
    p.items[at + 1:at + 1] = _ops(p, lambda b: b.sysreq('WorkSet', ACTIVE, 0))
    battle_points(p)
    reception_routine(p)
    before_battle_routine(p)
    return battle_video.suppress(p)


def zone_script(retail):
    """Built zone script bytes of the Dome's interior."""
    return dome_program(retail).build_script(f'L{retail.main:x}').build()
