#!/usr/bin/env python3
"""Battle Factory reception (F4): the «Battle Factory» option of the Maison receptionist, the draft of 6
rentals, the choice of 3, and the texts they need. Used by frontier/overlay.py.

Zone scripts must stay small: the zone 517 script is already the largest retail one, and a 20.6 KB zone
script (ZO container 21428 bytes) hangs the field load in Azahar while 16.5 KB (container 17248) loads
(reports/frontier.md §11). So the draft lives in a shared script, run with GlobalCall:
- code.bin's GlobalCall range table (patch.GLOBAL_ROW) maps ids 9770-9779 to shared script 5 (a/0/2/9),
  a retail placeholder (case 9770, an empty routine; no script calls 9770). Its text field is pointed at a
  new story text entry, patch.TEXT_FACTORY, so the 930 lines below load only during the draft.
- Shared script 5 gets case GLOBAL_DRAFT -> `factory_draft`: level from the current streak (saved work
  WORK_STREAK / 7, capped: the zone script reads GetMyWinCount and passes it, because the draft hung the
  game while it called that Maison native itself, reports/frontier.md §11), 6 sets drawn from that level
  with a linear congruential generator seeded by the real-time clock and saved work WORK_RNG (species and
  items all different, as Emerald's Factory), three menus to choose 3 of them, then the saved works the
  code.bin hook reads (patch.WORK_IV = round IV, patch.WORK_SETS = sets with a random ability 0/1).
  GlobalSetParentParam(0, 1) if chosen, 0 if a menu was cancelled. Message and menu helpers are copied from
  zone 517 (0x1d8, 0x5d4, 0x618, 0x104c, 0x10b4).
- Zone 517 (addresses of work/frontier/survey/zone517.lst, reports/frontier.md §1): a fifth reception menu
  entry «Battle Factory» (text 619 line LINE_OPTION, value 4) before «Nothing»; at 0x1634 value 4 calls
  `factory_reception`: WORK_STREAK = max(GetMyWinCount(0, 0), 0), GlobalCall(GLOBAL_DRAFT); if chosen, works
  0x800C-0x800E and the Maison challenge routine 0x18f8(rank 0, Singles, 0) without the mode
  selection app. Its result is the «back to the menu» local (-4) the info options also set: declined
  confirmation or cancelled draft -> back to the menu, Factory cleared; challenge played -> 0, Factory
  cleared if the streak is 0 (lost), kept if not (paused, for the resume). Option 0 (the Maison's own
  challenge) first clears the Factory (WorkSet(WORK_IV, 0)), as do case 1 (0x1458, the «you did not save»
  cleanup) and the lost-battle path (0x2210, before the game saves the record).
- After each win (0x2264, before the continue menu) `factory_after_win`: every 7 wins a new draft of the
  next level (GlobalCall GLOBAL_DRAFT until 3 are chosen), otherwise the swap offer (GlobalCall
  GLOBAL_SWAP, shared script 5 `factory_swap`), with the last rival's sets copied by the code.bin rival hook
  (patch.WORK_RIVAL).

Rental slots: every set any level can draw, numbered so each level is one contiguous range (round 1-3:
the Normal ranges; 4-7: the four Super tiers; 8+: all Super tiers). Slot s has one data cell
(set index | Super << 10 | species << 11 | item << 21) and one menu line, LINE_SLOTS + s, «Species (Item)»
in each language's own names (read from the dump's game text at build time).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from formats import garc_entries, text_lines, words_to_text  # noqa: E402
from pawn import ARGC, CASETBL, OP, PACKED, Op, Program  # noqa: E402
import data as fd  # noqa: E402
import patch  # noqa: E402

WORK_RNG = 16414                 # free saved works (frontier/ids.py): generator state between drafts,
WORK_STREAK = 16429              # streak handed from the zone script to the draft
SHARED_SCRIPT = 5                # a/0/2/9 entry: GlobalCall 9770-9779 (patch.GLOBAL_ROW)
SHARED_PLACEHOLDER = 9770        # its only retail case
GLOBAL_DRAFT = 9771
GLOBAL_SWAP = 9772
TEXT_ZONE = 619                  # zone 517's story text
TEXT_LINES = 188                 # lines of text 619 in every language (Repolished 1.7.6)
LINE_OPTION = TEXT_LINES         # «Battle Factory», in text 619
# Lines of patch.TEXT_FACTORY: prompts, then «Species (Item)» for every Normal set a trainer or a rental can use
# (maisonpkN 0-207, line = LINE_N + index), then the Super sets of the rental levels in slot order.
LINE_PICK = (0, 1, 2)
LINE_SWAP_GIVE, LINE_SWAP_TAKE, LINE_NO_SWAP = 3, 4, 5
LINE_N = 6
NORMAL_LINES = 208
LINE_S = LINE_N + NORMAL_LINES
# Text 619 line after LINE_OPTION: the refusal every facility reception shows while another facility has a
# challenge in progress (patch.ACTIVE_WORK; frontier/REPARTO.md). Zone 517's clones keep text 619.
LINE_BUSY = TEXT_LINES + 1
BUSY = {'es': 'Tienes un desafío a medias en otra instalación.\nTermínalo antes de empezar otro.',
        'en': 'You have a challenge in progress at another facility.\nPlease finish it there first.'}
MENU_FACTORY = 4                 # value of the new reception menu entry
WORK_SELECT_RESULT, WORK_SELECT_TYPE, WORK_SELECT_X = 0x800C, 0x800D, 0x800E
LCG_MUL, LCG_ADD = 0x41C64E6D, 0x6073
# Retail routines of script 517 the new code calls (copied into the shared script for the draft).
MSG, MSG_WAIT, MSG_CLOSE = 0x1D8, 0x5D4, 0x618        # (line, 1, 0, 256, 0); (); (0)
MENU_INIT, MENU_RUN = 0x104C, 0x10B4                  # (180, 112, cursor, 1, 0, 0); () -> value
HELPERS = {'msg': MSG, 'msg_wait': MSG_WAIT, 'msg_close': MSG_CLOSE, 'menu_init': MENU_INIT,
           'menu_run': MENU_RUN}
CHALLENGE = 'L18f8'                                   # (rank, type, work 0x800E) -> 1 if declined
RECEPTION_RESULT, RECEPTION_AGAIN, RECEPTION_NEXT = 'L1634', -4, 'L1810'
CLEANUP = 'L1458'
AFTER_BATTLE = 'L2264'          # battle loop: local -8 = 1 after a win; then the continue / pause menu (0x3b90)
LOST = 'L2210'                  # battle loop, lost battle: record (0x3fdc, which saves the game), ClearWinCount
BATTLE_POINTS = 'L3de4'         # (rank, type, boss): BP by streak bracket into local -8, then 0x3f4c adds and says it
BATTLE_POINTS_GIVE = 'L3f4c'
OPTION = {'es': 'Fábrica Batalla', 'en': 'Battle Factory'}
PICK = {'es': ['Elige tu primer Pokémon de alquiler.', 'Elige tu segundo Pokémon de alquiler.',
               'Elige tu tercer Pokémon de alquiler.'],
        'en': ['Choose your first rental Pokémon.', 'Choose your second rental Pokémon.',
               'Choose your third rental Pokémon.']}
SWAP = {'es': ['¿Quieres cambiar un Pokémon de alquiler?\nElige el que darías a cambio.',
               '¿Qué Pokémon del rival quieres?', 'No cambiar'],
        'en': ['Do you want to swap a rental Pokémon?\nChoose the one to give away.',
               'Which of your opponent\u2019s Pokémon do you want?', 'Don\u2019t swap']}
GAMETEXT = {lang: f'a/0/7/{lang}' for lang in range(1, 9)}                       # 1 JP kana .. 8 KO
STORYTEXT = {lang: f'a/0/{(78 + lang) // 10}/{(78 + lang) % 10}' for lang in range(1, 9)}
LANG = {lang: 'es' if lang == 7 else 'en' for lang in range(1, 9)}              # as faraway/build.py


def slots():
    """(slots, level ranges): slots = [(rank, set index)], level ranges = [(first slot, count)] per level."""
    order = [*fd.NORMAL_TIERS[1:], *fd.SUPER_TIERS]
    result, starts = [], []
    for tier in order:
        starts.append((len(result), len(fd.indices(tier))))
        result += fd.indices(tier)
    levels = [*starts, (starts[3][0], len(result) - starts[3][0])]
    for level, (first, count) in zip(fd.RENTAL_LEVELS, levels):
        if result[first:first + count] != fd.indices(level):
            raise ValueError('rental levels are not contiguous slot ranges')
    return result, levels


def slot_cells(sets, table):
    cells = []
    for rank, index in table:
        s = sets[rank][index]
        if index >= 1 << 10 or s['species'] >= 1 << 10 or s['item'] >= 1 << 10:
            raise ValueError(f'{rank}{index} does not fit a slot cell')
        cells.append(index | (rank == 'S') << 10 | s['species'] << 11 | s['item'] << 21)
    return cells


def check_draws(sets, table, levels):
    """Every draft can finish: after any 5 picks some set still has a new species and a new item."""
    for first, count in levels:
        picked = [sets[r][i] for r, i in table[first:first + count]]
        by_species, by_item = {}, {}
        for s in picked:
            by_species[s['species']] = by_species.get(s['species'], 0) + 1
            by_item[s['item']] = by_item.get(s['item'], 0) + 1
        worst = sum(sorted(by_species.values())[-5:]) + sum(sorted(by_item.values())[-5:])
        if count - worst < 1:
            raise ValueError(f'level at slot {first}: a draft could run out of sets')


def super_lines():
    """[(first index, last index, line of the first)] for the Super sets that have a line (rental levels 4-8)."""
    out = []
    for k, tier in enumerate(fd.SUPER_TIERS):
        line = LINE_S + k * len(fd.indices(tier))
        for _, first, last in tier:
            out.append((first, last, line))
            line += last - first + 1
    return out


def line_of(rank, index):
    if rank == 'N':
        if not 0 <= index < NORMAL_LINES:
            raise ValueError(f'N{index} has no line')
        return LINE_N + index
    return next(line + index - first for first, last, line in super_lines() if first <= index <= last)


def lines_for(lang, gametext, sets, table):
    """Lines of the new text patch.TEXT_FACTORY in one language (layout: LINE_* above)."""
    def names(entry):
        e = next(e for e in garc_entries(gametext) if e[0] == entry)
        return [words_to_text(w) for w in text_lines(gametext[e[2]:e[2] + e[3]])[0]]
    species, items = names(fd.TEXT_SPECIES), names(fd.TEXT_ITEMS)
    out = list(PICK[LANG[lang]]) + list(SWAP[LANG[lang]])
    supers = [(r, i) for r, i in table if r == 'S']
    for rank, index in [('N', i) for i in range(NORMAL_LINES)] + supers:
        if len(out) != line_of(rank, index):
            raise ValueError('text layout does not match line_of')
        s = sets[rank][index]
        out.append(f'{species[s["species"]]} ({items[s["item"]]})' if s['item'] else species[s['species']])
    return out


class Routine:
    """Emits one Pawn routine into a Program, with named locals and checked encodings."""

    def __init__(self, program, label, locals_):
        self.p = program
        self.local = {name: -4 * (k + 1) for k, name in enumerate(locals_)}
        self.serial = 0
        self.size = 4 * len(locals_)
        program.label(label)
        self.op('PROC', 0)
        if self.size:
            self.op('STACK_P', -self.size)

    def op(self, name, *args):
        code = OP[name]
        want = 1 if code in PACKED else ARGC.get(code, 0)
        if len(args) != want:
            raise ValueError(f'{name} takes {want} arguments')
        self.p.emit(name, *args)

    def new_label(self, stem):
        self.serial += 1
        return f'factory_{stem}_{self.serial}'

    def load(self, name):
        self.op('LOAD_P_S_PRI', self.local[name])

    def load_alt(self, name):
        self.op('LOAD_P_S_ALT', self.local[name])

    def store(self, name):
        self.op('STOR_P_S_PRI', self.local[name])

    def const(self, value):
        self.op('CONST_P_PRI', value) if -0x8000 <= value < 0x8000 else self.op('CONST_PRI', value)

    def const_alt(self, value):
        self.op('CONST_P_ALT', value) if -0x8000 <= value < 0x8000 else self.op('CONST_ALT', value)

    def add(self, value):
        self.op('ADD_P_C', value) if -0x8000 <= value < 0x8000 else self.op('ADD_C', value)

    def set(self, name, value):
        self.op('CONST_S', self.local[name], value)

    def field(self, shift, bits):
        """PRI = (PRI >> shift) & (2**bits - 1)."""
        if shift:
            self.op('SHR_P_C_PRI', shift)
        self.const_alt((1 << bits) - 1)
        self.op('AND', 0)

    def cell(self, base):
        """PRI = data cell base + PRI (cells)."""
        self.op('SMUL_P_C', 4)
        self.add(base)
        self.op('LOAD_I', 0)

    def line_of_slot(self, slot, first_super):
        """PRI = text line of draft slot `slot` (local): Normal slots are maisonpkN 66.. in order, then Super."""
        done, normal = self.new_label('line'), self.new_label('normal')
        self.load(slot)
        self.const_alt(first_super)
        self.op('JSLESS', normal)
        self.load(slot)
        self.add(LINE_S - first_super)
        self.op('JUMP', done)
        self.p.label(normal)
        self.load(slot)
        self.add(LINE_N + fd.NORMAL_TIERS[1][0][1])
        self.p.label(done)

    def line_of_value(self, value, tmp):
        """PRI = text line of a rental work value (local; bit 15 Super, bits 0-9 index); `tmp` is a scratch local."""
        done = self.new_label('vline')
        self.load(value)
        self.field(0, 10)
        self.store(tmp)
        self.load(value)
        self.field(15, 1)
        normal = self.new_label('vnormal')
        self.op('JZER', normal)
        for first, last, line in super_lines():
            skip = self.new_label('vskip')
            self.load(tmp)
            self.const_alt(first)
            self.op('JSLESS', skip)
            self.load(tmp)
            self.const_alt(last)
            self.op('JSGRTR', skip)
            self.load(tmp)
            self.add(line - first)
            self.op('JUMP', done)
            self.p.label(skip)
        self.const(LINE_NO_SWAP)            # not a rental set: should not happen
        self.op('JUMP', done)
        self.p.label(normal)
        self.load(tmp)
        self.add(LINE_N)
        self.p.label(done)

    def arg(self, value):
        return ('local', self.local[value]) if isinstance(value, str) else value

    def sysreq(self, native, *args):
        self.p.sysreq(native, *(self.arg(a) for a in args))

    def call(self, target, *args):
        self.p.call(target, *(self.arg(a) for a in args))

    def ret(self):
        """Return PRI."""
        if self.size:
            self.op('STACK_P', self.size)
        self.op('RETN', 0)


def rand_routine(p, state):
    """factory_rand(n) -> 0..n-1 (n < 2**15): state = state * LCG_MUL + LCG_ADD; (state >> 16 & 0x7fff) * n >> 15."""
    r = Routine(p, 'factory_rand', [])
    r.op('LOAD_P_PRI', state)
    r.const_alt(LCG_MUL)
    r.op('SMUL', 0)
    r.add(LCG_ADD)
    r.op('STOR_P_PRI', state)
    r.field(16, 15)
    r.op('LOAD_P_S_ALT', 12)        # n
    r.op('SMUL', 0)
    r.op('SHR_P_C_PRI', 15)
    r.ret()


def draft_routine(p, cells, levels, helpers):
    """factory_draft(): GlobalSetParentParam(0, 1) once the works are written, 0 if a menu was cancelled."""
    state = p.data_block('factory_rng', [0])
    table = p.data_block('factory_slots', cells)
    level_cells = []
    for first, count in levels:
        level_cells += [first, count]
    level_table = p.data_block('factory_levels', level_cells)
    ivs = p.data_block('factory_ivs', [fd.fixed_iv(n + 1) for n in range(len(levels))])
    rand_routine(p, state)
    names = ['level', 'first', 'count', 'iv', 'sel', 'value',
             *(f'{f}{k}' for f in ('slot', 'cell', 'species', 'item', 'picked') for k in range(fd.DRAFT_SIZE)),
             *(f'chosen{k}' for k in range(fd.PARTY_SIZE))]
    r = Routine(p, 'factory_draft', names)

    # Seed: real-time seconds + 32767 × saved state (the high half of the last draft's state).
    r.sysreq('WorkGet', WORK_RNG)
    r.op('SMUL_P_C', 0x7FFF)
    r.op('PUSH_PRI', 0)
    r.sysreq('_GetRealTimeToSecond')
    r.op('PALT', 0)
    r.op('ADD', 0)
    r.op('STOR_P_PRI', state)

    # Level = min(streak / 7, last level); its slot range and IV.
    r.sysreq('WorkGet', WORK_STREAK)
    r.op('MOVE_ALT', 0)
    r.const(fd.STAGES_PER_ROUND)
    r.op('SDIV_ALT', 0)              # PRI = streak / 7
    r.store('level')
    r.const_alt(len(levels) - 1)
    capped = r.new_label('level')
    r.op('JSLEQ', capped)            # level <= last
    r.set('level', len(levels) - 1)
    r.p.label(capped)
    r.load('level')
    r.op('SMUL_P_C', 2)
    r.cell(level_table)
    r.store('first')
    r.load('level')
    r.op('SMUL_P_C', 2)
    r.add(1)
    r.cell(level_table)
    r.store('count')
    r.load('level')
    r.cell(ivs)
    r.store('iv')

    # Draw 6: species and items all different.
    for k in range(fd.DRAFT_SIZE):
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
        r.set(f'picked{k}', 0)

    # Choose 3 of them.
    cancel = 'factory_cancel'
    for n in range(fd.PARTY_SIZE):
        r.call(helpers['msg'], LINE_PICK[n], 1, 0, 256, 0)
        r.call(helpers['msg_wait'])
        r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
        for k in range(fd.DRAFT_SIZE):
            skip = r.new_label('menu')
            r.load(f'picked{k}')
            r.op('JNZ', skip)
            r.p.push(0)
            r.p.push(k)
            r.line_of_slot(f'slot{k}', levels[3][0])
            r.op('PUSH_PRI', 0)
            r.p.emit('SYSREQ_N', 'ListMenuAdd', 12)
            r.p.label(skip)
        r.call(helpers['menu_run'])
        r.store('sel')
        done = r.new_label('chosen')
        for k in range(fd.DRAFT_SIZE):
            other = r.new_label('choice')
            r.load('sel')
            r.op('EQ_P_C_PRI', k)
            r.op('JZER', other)
            r.load(f'picked{k}')
            r.op('JNZ', cancel)      # not offered: treat as a cancel
            r.set(f'picked{k}', 1)
            r.load(f'cell{k}')
            r.store(f'chosen{n}')
            r.op('JUMP', done)
            r.p.label(other)
        r.op('JUMP', cancel)         # B (65535) or anything unexpected
        r.p.label(done)
    r.call(helpers['msg_close'], 0)

    # Saved works for the code.bin hook.
    for n, work in enumerate(patch.WORK_SETS):
        r.load(f'chosen{n}')
        r.field(0, 10)
        r.store('value')
        r.load(f'chosen{n}')
        r.field(10, 1)
        normal = r.new_label('archive')
        r.op('JZER', normal)
        r.load('value')
        r.add(patch.SUPER)
        r.store('value')
        r.p.label(normal)
        r.call('factory_rand', 2)
        r.op('SMUL_P_C', 1 << patch.ABILITY_SHIFT)
        r.load_alt('value')
        r.op('ADD', 0)
        r.store('value')
        r.sysreq('WorkSet', work, 'value')
    r.sysreq('WorkSet', patch.WORK_IV, 'iv')
    r.op('LOAD_P_PRI', state)
    r.field(16, 16)
    r.store('value')
    r.sysreq('WorkSet', WORK_RNG, 'value')
    r.sysreq('GlobalSetParentParam', 0, 1)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label(cancel)
    r.call(helpers['msg_close'], 0)
    r.sysreq('GlobalSetParentParam', 0, 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def swap_routine(p, helpers):
    """factory_swap(): after a win, offer one of the last rival's sets (patch.WORK_RIVAL, maisonpkN indices
    written by the code.bin rival hook) for one of the player's rentals, as Emerald's Factory. Two menus:
    which rental to give (or «Don't swap»), then which rival set to take. B in either menu keeps the team."""
    names = ['sel', 'give', 'value', 'tmp', *(f'mine{k}' for k in range(fd.PARTY_SIZE)),
             *(f'rival{k}' for k in range(fd.PARTY_SIZE))]
    r = Routine(p, 'factory_swap', names)
    for k in range(fd.PARTY_SIZE):
        r.sysreq('WorkGet', patch.WORK_SETS[k])
        r.store(f'mine{k}')
        r.sysreq('WorkGet', patch.WORK_RIVAL[k])
        r.store(f'rival{k}')
    keep = 'factory_swap_keep'

    def menu(prompt, entries, extra):
        r.call(helpers['msg'], prompt, 1, 0, 256, 0)
        r.call(helpers['msg_wait'])
        r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
        for k, local in enumerate(entries):
            r.p.push(0)
            r.p.push(k)
            if local.startswith('mine'):
                r.line_of_value(local, 'tmp')
            else:
                r.load(local)
                r.field(0, 10)
                r.add(LINE_N)
            r.op('PUSH_PRI', 0)
            r.p.emit('SYSREQ_N', 'ListMenuAdd', 12)
        if extra:
            r.sysreq('ListMenuAdd', LINE_NO_SWAP, len(entries), 0)
        r.call(helpers['menu_run'])
        r.store('sel')
        r.const_alt(len(entries) - 1)
        r.op('JSGRTR', keep)            # «Don't swap», B (65535) or anything unexpected
        r.load('sel')
        r.const_alt(0)
        r.op('JSLESS', keep)

    menu(LINE_SWAP_GIVE, [f'mine{k}' for k in range(fd.PARTY_SIZE)], True)
    r.load('sel')
    r.store('give')
    menu(LINE_SWAP_TAKE, [f'rival{k}' for k in range(fd.PARTY_SIZE)], False)
    # value = rival set (Normal archive) with a random ability slot 0/1, written over the rental given away
    taken = r.new_label('taken')
    for k in range(fd.PARTY_SIZE):
        other = r.new_label('take')
        r.load('sel')
        r.op('EQ_P_C_PRI', k)
        r.op('JZER', other)
        r.load(f'rival{k}')
        r.field(0, 10)
        r.store('value')
        r.op('JUMP', taken)
        r.p.label(other)
    r.op('JUMP', keep)
    r.p.label(taken)
    r.call('factory_rand', 2)
    r.op('SMUL_P_C', 1 << patch.ABILITY_SHIFT)
    r.load_alt('value')
    r.op('ADD', 0)
    r.store('value')
    for k in range(fd.PARTY_SIZE):
        other = r.new_label('give')
        r.load('give')
        r.op('EQ_P_C_PRI', k)
        r.op('JZER', other)
        r.sysreq('WorkSet', patch.WORK_SETS[k], 'value')
        r.p.label(other)
    r.p.label(keep)
    r.call(helpers['msg_close'], 0)
    r.op('ZERO_PRI', 0)
    r.ret()


def shared_program(shared, zone, cells, levels):
    """Shared script 5 with case GLOBAL_DRAFT -> factory_draft and the zone 517 helpers it calls."""
    p = Program.from_script(shared)
    main = f'L{shared.main:x}'
    start = p.items.index(('label', main))
    index = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op) and p.items[i].op == CASETBL)
    table = p.items[index]
    pairs = [(table.args[2 + 2 * k], table.args[3 + 2 * k]) for k in range(table.args[0])]
    if sorted(v for v, _ in pairs) != [-1, SHARED_PLACEHOLDER]:
        raise ValueError(f'shared script {SHARED_SCRIPT} is not the retail placeholder')
    end = next(i for i in range(index + 1, len(p.items)) if not isinstance(p.items[i], tuple))
    p.items.insert(end, ('label', 'factory_case_end'))
    pairs += [(GLOBAL_DRAFT, 'factory_case_draft'), (GLOBAL_SWAP, 'factory_case_swap')]
    table.args = [len(pairs), table.args[1]] + [x for pair in sorted(pairs) for x in pair]
    for case, routine in (('factory_case_draft', 'factory_draft'), ('factory_case_swap', 'factory_swap')):
        p.label(case)
        p.call(routine)
        p.emit('JUMP', 'factory_case_end')
    # Each helper is copied with its own prefix (shared callees are duplicated, which is harmless).
    helpers = {name: p.transplant(zone, address, f'z{name}_') for name, address in HELPERS.items()}
    draft_routine(p, cells, levels, helpers)
    swap_routine(p, helpers)
    return p


def busy_check(r, facility, back):
    """Emit into Routine `r` (a zone 517 script): if any other facility's patch.ACTIVE_WORK is not 0, say LINE_BUSY
    with zone 517's message routines and jump to `back`. The mutual exclusion between facilities (REPARTO.md)."""
    free, busy = r.new_label('free'), r.new_label('busy')
    for other, work in patch.ACTIVE_WORK.items():
        if other != facility:
            r.sysreq('WorkGet', work)
            r.op('JNZ', busy)
    r.op('JUMP', free)
    r.p.label(busy)
    r.call(f'L{MSG:x}', LINE_BUSY, 1, 0, 256, 0)
    r.call(f'L{MSG_WAIT:x}')
    r.call(f'L{MSG_CLOSE:x}', 0)
    r.op('JUMP', back)
    r.p.label(free)


def reception_routine(p):
    """factory_reception() -> 1 = back to the reception menu, 0 = challenge played.

    patch.WORK_ROUTE is set for the whole challenge: the code.bin streak hooks then point the Maison's Singles
    Normal streak and record at the Factory's own works (patch.WORK_FSTREAK / WORK_FRECORD), so every Maison
    streak read and write (battle number, trainer brackets, BP, records, ClearWinCount after a loss) applies
    to the Factory. Cleared when the challenge returns, and at every reception (a save made during the
    challenge can hold it). Refused, with nothing changed, while another facility has a challenge in progress."""
    r = Routine(p, 'factory_reception', [])
    busy_check(r, 'factory', 'factory_refused')
    r.sysreq('SetRank', 0)                      # the streak route covers rank Normal only
    r.sysreq('WorkSet', patch.WORK_ROUTE, 1)
    r.sysreq('WorkGet', patch.WORK_IV)
    r.op('JNZ', 'factory_resume')    # paused Factory challenge: keep the rentals and streak, as Emerald
    r.sysreq('WorkSet', patch.WORK_FSTREAK, 0)  # a new challenge starts at round 1
    r.sysreq('WorkSet', WORK_STREAK, 0)
    r.sysreq('GlobalCall', GLOBAL_DRAFT)
    r.sysreq('GlobalGetChildParam', 0)
    r.op('JZER', 'factory_back')
    r.p.label('factory_resume')
    r.sysreq('WorkSet', WORK_SELECT_RESULT, 1)
    r.sysreq('WorkSet', WORK_SELECT_TYPE, 0)
    r.sysreq('WorkSet', WORK_SELECT_X, 0)
    r.call(CHALLENGE, 0, 0, 0)
    r.op('EQ_P_C_PRI', 1)
    r.op('JNZ', 'factory_back')      # declined the confirmation
    r.sysreq('GetMyWinCount', 0, 0)  # the Factory streak (route still set)
    r.op('MOVE_ALT', 0)
    r.op('ZERO_PRI', 0)
    r.op('JSLESS', 'factory_kept')   # 0 < streak: paused, keep the rentals for the resume
    r.sysreq('WorkSet', patch.WORK_IV, 0)
    r.p.label('factory_kept')
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.op('ZERO_PRI', 0)
    r.ret()
    r.p.label('factory_back')
    r.sysreq('WorkSet', patch.WORK_IV, 0)
    r.sysreq('WorkSet', patch.WORK_FSTREAK, 0)
    r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
    r.p.label('factory_refused')     # another facility's challenge in progress: nothing changed
    r.const(1)
    r.ret()


def after_win_routine(p):
    """factory_after_win(): Factory active -> every 7 wins a new draft of the next level (repeated until 3 are
    chosen), otherwise the swap offer. Called from the battle loop after a win, before the continue menu."""
    r = Routine(p, 'factory_after_win', ['streak'])
    r.sysreq('WorkGet', patch.WORK_IV)
    r.op('JZER', 'factory_after_win_end')
    r.sysreq('GetMyWinCount', 0, 0)
    r.store('streak')
    r.sysreq('WorkSet', WORK_STREAK, 'streak')
    r.load('streak')
    r.op('MOVE_ALT', 0)
    r.const(fd.STAGES_PER_ROUND)
    r.op('SDIV_ALT', 0)                  # PRI = streak / 7
    r.op('SMUL_P_C', fd.STAGES_PER_ROUND)
    r.load_alt('streak')
    r.op('SUB_ALT', 0)                   # PRI = streak - 7 * (streak / 7)
    r.op('JZER', 'factory_after_win_draft')
    r.sysreq('GlobalCall', GLOBAL_SWAP)
    r.op('JUMP', 'factory_after_win_end')
    r.p.label('factory_after_win_draft')
    r.sysreq('GlobalCall', GLOBAL_DRAFT)
    r.sysreq('GlobalGetChildParam', 0)
    r.op('JZER', 'factory_after_win_draft')
    r.p.label('factory_after_win_end')
    r.op('ZERO_PRI', 0)
    r.ret()


def battle_points(p):
    """Factory BP as Emerald: none for battles 1-6 of a round; after the 7th, BATTLE_POINTS[round - 1] (clamped).
    Inserted in the Maison's BP routine 0x3de4 once its locals exist (-4 win count, -8 BP); the Maison's own
    brackets stay for the Maison. No Frontier Brain bonus yet (F5)."""
    start = _index(p, BATTLE_POINTS)
    at = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
              and p.items[i].op == OP['STOR_P_S_PRI'] and p.items[i].args == [-4])
    if p.items[at + 1].op != OP['PUSH_P_C'] or p.items[at + 1].args != [0]:
        raise ValueError('BP routine locals not found at 0x3e04')
    table = p.data_block('factory_bp', list(fd.BATTLE_POINTS))
    b = Program(p.script)
    b.native_hashes = p.native_hashes
    b.sysreq('WorkGet', patch.WORK_IV)
    b.emit('JZER', 'factory_bp_retail')
    b.sysreq('GetMyWinCount', 0, 0)
    b.emit('STOR_P_S_PRI', -4)
    b.emit('MOVE_ALT', 0)
    b.emit('CONST_P_PRI', fd.STAGES_PER_ROUND)
    b.emit('SDIV_ALT', 0)                    # rounds won = streak / 7
    b.emit('STOR_P_S_PRI', -8)
    b.emit('SMUL_P_C', fd.STAGES_PER_ROUND)
    b.emit('LOAD_P_S_ALT', -4)
    b.emit('SUB_ALT', 0)                     # streak - 7 * rounds
    b.emit('JNZ', 'factory_bp_none')
    b.emit('LOAD_P_S_PRI', -8)
    b.emit('ADD_P_C', -1)
    b.emit('CONST_P_ALT', len(fd.BATTLE_POINTS) - 1)
    b.emit('JSLEQ', 'factory_bp_index')
    b.emit('CONST_P_PRI', len(fd.BATTLE_POINTS) - 1)
    b.label('factory_bp_index')
    b.emit('SMUL_P_C', 4)
    b.emit('ADD_P_C', table)
    b.emit('LOAD_I', 0)
    b.emit('STOR_P_S_PRI', -8)
    b.emit('JUMP', BATTLE_POINTS_GIVE)
    b.label('factory_bp_none')
    b.emit('STACK_P', 8)
    b.emit('ZERO_PRI', 0)
    b.emit('RETN', 0)
    b.label('factory_bp_retail')
    p.items[at + 2:at + 2] = b.items


def _index(p, label):
    return p.items.index(('label', label))


def _clear(p, *also):
    """WorkSet(WORK_IV, 0) and WorkSet(w, 0) for each extra work."""
    body = Program(p.script)
    body.native_hashes = p.native_hashes
    for work in (patch.WORK_IV, *also):
        body.sysreq('WorkSet', work, 0)
    return body.items


def reception(p):
    """Insert the menu entry, the dispatch to factory_reception and the Factory clears into script 517."""
    start, native = _index(p, 'L14f4'), p.native('ListMenuAdd')
    create = next(i for i in range(start, len(p.items)) if isinstance(p.items[i], Op)
                  and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == p.native('BattleInstWorkCreate'))
    route = Program(p.script)
    route.native_hashes = p.native_hashes
    route.sysreq('WorkSet', patch.WORK_ROUTE, 0)  # every reception starts with the Maison's own streaks
    p.items[create + 1:create + 1] = route.items
    adds = [i for i in range(start, _index(p, RECEPTION_RESULT)) if isinstance(p.items[i], Op)
            and p.items[i].op == OP['SYSREQ_N'] and p.items[i].args[0] == native]
    if len(adds) != 4:
        raise ValueError('reception menu not found')
    entry = Program(p.script)
    entry.native_hashes = p.native_hashes
    entry.sysreq('ListMenuAdd', LINE_OPTION, MENU_FACTORY, 0)
    p.items[adds[2] + 1:adds[2] + 1] = entry.items

    at = _index(p, RECEPTION_RESULT)
    head = p.items[at + 1:at + 3]
    if [o.op for o in head] != [OP['LOAD_P_S_PRI'], OP['JNZ']] or head[0].args != [-12] or head[1].args != ['L17b0']:
        raise ValueError('reception result check not found at 0x1634')
    dispatch = Program(p.script)
    dispatch.native_hashes = p.native_hashes
    dispatch.emit('LOAD_P_S_PRI', -12)
    dispatch.emit('EQ_P_C_PRI', MENU_FACTORY)
    dispatch.emit('JZER', 'factory_not_chosen')
    dispatch.call('factory_reception')
    dispatch.emit('STOR_P_S_PRI', RECEPTION_AGAIN)
    dispatch.emit('JUMP', RECEPTION_NEXT)
    dispatch.label('factory_not_chosen')
    p.items[at + 3:at + 3] = _clear(p, patch.WORK_FSTREAK)   # option 0: the Maison's own challenge abandons
                                                              # a paused Factory
    p.items[at + 1:at + 1] = dispatch.items

    at = _index(p, CLEANUP)
    if p.items[at + 1].op != OP['PROC']:
        raise ValueError('0x1458 is not a routine start')
    p.items[at + 2:at + 2] = _clear(p)

    at = _index(p, AFTER_BATTLE)
    head = p.items[at + 1:at + 4]
    if [o.op for o in head] != [OP['LOAD_P_S_PRI'], OP['EQ_P_C_PRI'], OP['JZER']] or head[0].args != [-8] \
            or head[1].args != [1] or head[2].args != ['L2624']:
        raise ValueError('won-battle check not found at 0x2264')
    call = Program(p.script)
    call.call('factory_after_win')
    p.items[at + 4:at + 4] = call.items

    at = _index(p, LOST)              # clear before the loss is saved, so the save never holds a dead Factory
    if p.items[at + 1].op != OP['ZERO_P_S'] or p.items[at + 1].args != [-8]:
        raise ValueError('lost-battle path not found at 0x2210')
    p.items[at + 1:at + 1] = _clear(p)
    battle_points(p)
    reception_routine(p)
    after_win_routine(p)
