"""Battle Frontier F6: the Frontier Pass, the Lilycove sailor who hands it over and the ferry's new destination.

Measured in reports/frontier.md §16:
- League champion: flag 2720 (PKHeX "Entered Hall of Fame"); no script sets it, 37 retail scripts read it.
- The pass is item 701 (Kalos's TMV Pass): Key Items pocket, same item data as the Old Sea Map (442); no script
  gives, takes or checks it.
- Lilycove harbor (zone 317): the sailor is NPC uid 2, event 4. His retail routine says story text 523 line 23
  before the League and 24 after. He now hands over the pass once to a champion who does not hold it.
- The ferry is shared script 79 (GlobalCall 10430, story text 11, 16 lines). Its routine 0x8b8(npc, zone) shows
  the destination menu with ListMenuAdd(line, value, 0) and switches on the answer: 0 Battle Resort (0xcb8),
  1 Slateport (0xe84), 2 Lilycove (0x1140). In Slateport (275) and Lilycove (317) the menu gains «Isla del
  Frente» (value 4) when the pass is held; value 4 runs a copy of the Battle Resort case (confirm, yes/no, the
  same fade and horn, a direct map change) with its own lines and arrival point.

The harbor and the ferry are edited by content, not by hash: the harbor may already carry the Mew event (same
zone, more cases and text lines), and every check below says what it expected when it fails.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
sys.path.append(str(ROOT / 'faraway'))
from pawn import OP, Op, Program  # noqa: E402
import event as ev  # noqa: E402  (faraway/event.py: ferry helper addresses, give routine, conversation idioms)

ITEM_PASS = 701
FLAG_CHAMPION = 2720
ZONE_HARBOR = 317
TEXT_HARBOR = 523
SAILOR_EVENT = 4
SAILOR_NPC = -4                 # local holding the NPC being talked to, as the Mew event's routines use it
FERRY_SCRIPT = 79
SHARED10 = 10                   # shared script with the item-give routine (ev.GIVE_ROUTINE)
FERRY_TEXT = 11
FERRY_TEXT_LINES = 16
LINE_ISLAND, LINE_ISLAND_GO = FERRY_TEXT_LINES, FERRY_TEXT_LINES + 1
MENU_ISLAND = 4
MENU_CANCEL = (9, 3)            # (line, value) of «Me quedo aquí»
FERRY_MENU = 'L8b8'
RESORT_CASE, RESORT_CASE_END = 'Lcb8', 'Le84'
RESORT_CONFIRM_LINE = 10
RESORT_ARRIVAL = (212, 53, 2, 34, 2)       # (zone, x, height, y, direction) of the retail Battle Resort trip
# Provisional: the island zone does not exist yet, so the new destination lands at the Battle Resort harbor.
ARRIVAL = RESORT_ARRIVAL
MAPCHANGE = 'L724'
GAMETEXT_ITEM = {'counted': 113, 'single': 114, 'plural': 115, 'single2': 116, 'description': 117}

ITEM = {
    'es': {'counted': 'Pase[VAR 1101 254,256]s del Frente', 'single': 'Pase del Frente',
           'plural': 'Pases del Frente', 'single2': 'Pase del Frente',
           'description': 'Pase de acceso al Frente Batalla. Con él, el\nferry te lleva hasta la Isla del Frente.'},
    'en': {'counted': 'Frontier Pass[VAR 1101 254,512]es', 'single': 'Frontier Pass',
           'plural': 'Frontier Passes', 'single2': 'Frontier Pass',
           'description': 'A pass to the Battle Frontier. Show it\nat the ferry to sail to Frontier Island.'},
}
SAILOR = {
    'es': ['Oye, ¿tú no eres quien ha ganado la Liga?[VAR BE01]\n'
           'En una isla han abierto el Frente Batalla, un lugar\n'
           'lleno de instalaciones de combate.[VAR BE01]\n'
           'Solo dejan ir a los mejores entrenadores, así que\nesto es para ti.',
           'Enséñale el ticket al empleado del ferry y elige\nla Isla del Frente. ¡Mucha suerte!'],
    'en': ["Hey, aren't you the one who won the League?[VAR BE01]\n"
           "They've opened the Battle Frontier on an island\n"
           "out at sea. It's packed with battle facilities.[VAR BE01]\n"
           'Only top Trainers may go there, so this is for you.',
           'Show your ticket to the ferry clerk and pick\nFrontier Island. Good luck!'],
}
FERRY = {
    'es': ['Isla del Frente', 'Muy bien, rumbo a la Isla del Frente.'],
    'en': ['Frontier Island', 'Very well, to Frontier Island.'],
}


def _ops(items, start, end):
    return [(i, items[i]) for i in range(start, end) if isinstance(items[i], Op)]


def _index(p, label):
    return p.items.index(('label', label))


def _routine_end(p, start):
    """Index of the next PROC after the routine starting at `start` (or the end of the program)."""
    return next((i for i in range(start + 2, len(p.items)) if isinstance(p.items[i], Op)
                 and p.items[i].op == OP['PROC']), len(p.items))


def _sub(p):
    s = Program(p.script)
    s.native_hashes = p.native_hashes
    return s


# --- Lilycove harbor: the sailor ------------------------------------------------------------------
def sailor_target(p, main):
    """(index of the CALL in event 4's case stub, retail routine label), checked."""
    start = _index(p, main)
    table = next(op for _, op in _ops(p.items, start, len(p.items)) if op.op == OP['CASETBL'])
    cases = dict(zip(table.args[2::2], table.args[3::2]))
    if SAILOR_EVENT not in cases:
        raise ValueError(f'zone {ZONE_HARBOR}: no event {SAILOR_EVENT} in the main dispatcher')
    stub = _ops(p.items, _index(p, cases[SAILOR_EVENT]), len(p.items))[:3]
    if [op.op for _, op in stub] != [OP['PUSH_P_C'], OP['CALL'], OP['JUMP']] or stub[0][1].args != [0]:
        raise ValueError(f'zone {ZONE_HARBOR}: event {SAILOR_EVENT} is not a plain call stub')
    retail = stub[1][1].args[0]
    body = _ops(p.items, _index(p, retail), _routine_end(p, _index(p, retail)))
    flag = p.native('FlagGet')
    reads = [k for k, (_, op) in enumerate(body[:-1]) if op.op == OP['PUSH_P_C'] and op.args == [FLAG_CHAMPION]
             and body[k + 1][1].op == OP['SYSREQ_N'] and body[k + 1][1].args[0] == flag]
    if len(reads) != 1:
        raise ValueError(f'zone {ZONE_HARBOR}: event {SAILOR_EVENT} routine does not read flag {FLAG_CHAMPION}')
    return stub[1][0], retail


def harbor_program(script, ferry, shared10, lines):
    """Zone 317 program whose sailor gives the pass. `lines`: story text 523 line numbers of SAILOR's texts."""
    p = Program.from_script(script)
    main = f'L{script.main:x}'
    at, retail = sailor_target(p, main)
    p.items[at].args = ['frontier_sailor']
    h = {name: p.transplant(ferry, ev.FERRY[name], f'fr{name}_', 'L4')
         for name in ('msg', 'keywait', 'close', 'talk_se', 'eye', 'face', 'wait_acmd', 'wait_frames')}
    h['give'] = p.transplant(shared10, ev.GIVE_ROUTINE, 'frgive_', 'L4')
    w = ev.Writer(p, ferry, h, ferry.natives[ev.FERRY_FADE_NATIVE][1])
    intro, after = lines
    ev.begin_routine(p, 'frontier_sailor')
    p.sysreq('FlagGet', FLAG_CHAMPION)
    p.emit('JZER', 'frontier_sailor_retail')
    p.sysreq('ItemGetNum', ITEM_PASS)
    p.emit('JNZ', 'frontier_sailor_retail')
    w.talk_begin(SAILOR_NPC)
    w.say(SAILOR_NPC, intro)
    p.call(h['give'], ITEM_PASS, 1, 1)
    p.sysreq('ItemGetNum', ITEM_PASS)
    p.emit('JZER', 'frontier_sailor_end')
    w.last(SAILOR_NPC, after)
    p.label('frontier_sailor_end')
    w.talk_end(SAILOR_NPC)
    p.emit('JUMP', 'frontier_sailor_done')
    p.label('frontier_sailor_retail')
    p.call(retail)
    p.label('frontier_sailor_done')
    ev.end_routine(p)
    return p


# --- Ferry: the new destination -------------------------------------------------------------------
def _menu_adds(p):
    """[(index of the first push, line, value)] of every ListMenuAdd(line, value, 0) in the ferry menu routine."""
    start = _index(p, FERRY_MENU)
    ops = _ops(p.items, start, _routine_end(p, start))
    native = p.native('ListMenuAdd')
    adds = []
    for k, (i, op) in enumerate(ops):
        if op.op == OP['SYSREQ_N'] and op.args[0] == native:
            pushes = [o for _, o in ops[k - 3:k]]
            if [o.op for o in pushes] != [OP['PUSH_P_C']] * 3 or op.args[1] != 12 or pushes[0].args != [0]:
                raise ValueError('ferry: ListMenuAdd without three constant arguments')
            adds.append((ops[k - 3][0], pushes[2].args[0], pushes[1].args[0]))
    return adds


def _menu_entry(p, skip):
    s = _sub(p)
    s.sysreq('ItemGetNum', ITEM_PASS)
    s.emit('JZER', skip)
    s.sysreq('ListMenuAdd', LINE_ISLAND, MENU_ISLAND, 0)
    s.label(skip)
    return s.items


def _island_case(p):
    """Copy of the Battle Resort case with the island's confirmation line and arrival point."""
    start, end = _index(p, RESORT_CASE), _index(p, RESORT_CASE_END)
    block = p.items[start:end]
    inner = {item[1] for item in block if isinstance(item, tuple)}
    rename = {label: f'island_{label}' for label in inner}
    out = []
    for item in block:
        if isinstance(item, tuple):
            out.append(('label', rename[item[1]]))
        else:
            out.append(Op(item.op, [rename.get(a, a) if isinstance(a, str) else a for a in item.args]))
    ops = [op for op in out if isinstance(op, Op)]
    head = [(op.op, op.args) for op in ops[:7]]
    if head != [(OP['PUSH_P_C'], [0]), (OP['PUSH_P_C'], [256]), (OP['PUSH_P_C'], [0]), (OP['PUSH_P_S'], [12]),
                (OP['PUSH_P_C'], [RESORT_CONFIRM_LINE]), (OP['PUSH_P_C'], [20]), (OP['CALL'], ['Ld8'])]:
        raise ValueError('ferry: the Battle Resort case does not start with its confirmation message')
    ops[4].args = [LINE_ISLAND_GO]
    changes = [k for k, op in enumerate(ops) if op.op == OP['CALL'] and op.args == [MAPCHANGE]]
    if len(changes) != 1:
        raise ValueError('ferry: the Battle Resort case has no single map change')
    k = changes[0]
    pushed = [op.args[0] for op in ops[k - 7:k]]
    if [op.op for op in ops[k - 7:k]] != [OP['PUSH_P_C']] * 7 or pushed != [0, *reversed(RESORT_ARRIVAL), 24]:
        raise ValueError(f'ferry: unexpected Battle Resort arrival {pushed}')
    for op, value in zip(ops[k - 6:k - 1], reversed(ARRIVAL)):
        op.args = [value]
    return [('label', 'frontier_ferry_island')] + out


def ferry_program(script):
    """Shared script 79 program with the «Isla del Frente» entry and case."""
    p = Program.from_script(script)
    adds = _menu_adds(p)
    if [(line, value) for _, line, value in adds] != [(6, 0), (8, 2), (9, 3), (6, 0), (7, 1), (9, 3),
                                                      (7, 1), (8, 2), (9, 3)]:
        raise ValueError(f'ferry: unexpected destination menus {adds}')
    # Slateport's and Lilycove's menus (the first two branches), before «Me quedo aquí».
    for n, (at, _, _) in reversed(list(enumerate([adds[2], adds[5]]))):
        p.items[at:at] = _menu_entry(p, f'frontier_ferry_skip_{n}')
    start = _index(p, FERRY_MENU)
    tables = [op for _, op in _ops(p.items, start, _routine_end(p, start)) if op.op == OP['CASETBL']]
    if len(tables) != 1 or tables[0].args[2::2] != [0, 1, 2]:
        raise ValueError('ferry: destination switch not found')
    table = tables[0]
    pairs = list(zip(table.args[2::2], table.args[3::2])) + [(MENU_ISLAND, 'frontier_ferry_island')]
    table.args = [len(pairs), table.args[1]] + [x for pair in pairs for x in pair]
    p.items.extend(_island_case(p))
    return p
