"""Old Sea Map / Faraway Island event: identifiers, texts and field scripts.

Every number here was measured on the Omega Ruby 1.0 + Repolished dump; reports/faraway.md says where.
Scripts are assembled with scripts/pawn.py: the harbor keeps its retail script and gains cases, the
island zones get new scripts built from retail helper routines (the ferry's dialogue and travel
routines from shared script 79, the item-give routine from shared script 10).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pawn import OP, Op, Program, Script, decode  # noqa: E402

# --- Story state ------------------------------------------------------------------------------
FLAG_DELTA_DONE = 2729       # PKHeX flags_oras: "Completed Delta Episode"
FLAG_MAP_RECEIVED = 3026     # free: no script, NPC, PKHeX entry or code literal uses 3026/3031/3034/3037/3039
FLAG_MEW_CAPTURED = 3031
FLAG_MEW_BATTLED = 3034
FLAG_HIDE_GIVER = 3037       # recomputed on every harbor load
FLAG_HIDE_BRINEY = 3039      # recomputed on every harbor load
WORK_PROGRESS = 16665        # saved work; 0 none, 1 map received, 2 island unlocked, 3 Mew seen
WORK_MEW_SPOT = 16667        # free saved work (no script, trigger or code literal): Mew's current hiding spot
PROGRESS_MAP, PROGRESS_ISLAND, PROGRESS_MEW_SEEN = 1, 2, 3

ITEM_OLD_SEA_MAP = 442       # Gen 4 "Town Map": no ORAS script gives, takes or checks it
STATIC_MEW = 29              # DllField static table: duplicate Deoxys no script or code reaches
SPECIES_MEW = 151
RESULT_CAPTURED = 4          # WildBattleResultGet, as every retail legendary script reads it

ZONE_HARBOR = 317            # Lilycove harbor (story text 523)
ZONE_ISLAND = 473            # placeholder "???" slot -> Faraway Island shore (cloned from Southern Island 214)
ZONE_MEADOW = 474            # placeholder "???" slot -> Faraway Island interior (cloned from 215)
TEXT_HARBOR, TEXT_ISLAND, TEXT_MEADOW = 523, 278, 277
HARBOR_TEXT_BASE = 30         # lines already in text 523 in every language; ours are appended after them
LOCATION_FARAWAY = 277       # empty odd location-name slot

MODEL_BRINEY = 283           # MoveModels 283 (rstr0166), as on the S.S. Tidal
MODEL_PEEKO = 4134           # uid of MoveModels 484 (pm0278, Wingull)
MODEL_SAILOR = 232           # MoveModels 232 (rstr0115), the harbor's own sailor
MODEL_MEW = 4247             # new registry uid (4096 + species, as Pokemon uids are) for the built field model
MOVEMODEL_MEW = 544          # appended after the 544 retail MoveModels

# Event ids (NPC script numbers) added to the zone scripts.
EV_GIVER, EV_BRINEY = 40, 41
HARBOR_NPC_GIVER, HARBOR_NPC_BRINEY = 3, 4   # entity indices: after the harbor's three retail NPCs
MEADOW_NPC_MEW = 0                           # Mew is the meadow's only NPC
EV_ISLAND_BRINEY, EV_MEW = 40, 41
EV_MEW_FLEE = 42             # trigger script: the player came close to Mew's current spot

# Hide-and-seek (meadow, zone 474), in tiles. Mew starts at spot 0 and flees one spot each time the player
# steps into the trigger area of its current spot; the last spot is backed against the cliff: there it stays,
# and talking to it starts the battle. (spot, trigger rectangle x, y, width, height)
MEW_SPOTS = [((20, 19), (17, 21, 7, 2)),
             ((25, 17), (21, 19, 7, 2)),
             ((16, 21), (15, 23, 5, 2)),
             ((25, 23), (21, 24, 6, 2)),
             ((20, 14), None)]
MEW_SPOT_INACTIVE = len(MEW_SPOTS)  # no trigger matches while Mew is absent
MEW_MOVE_A, MEW_MOVE_B = 19, 38   # MdlAcmdMakeMoveEx constants copied from retail calls (shared script 55)

# Arrival points for _MapChangeCore: (zone, tile x, height, tile y, direction). Measured in Azahar.
ARRIVE_ISLAND = (ZONE_ISLAND, 24, 126, 6, 1)
ARRIVE_HARBOR = (ZONE_HARBOR, 24, 0, 26, 1)

FERRY = {'msg': 0xD8, 'keywait': 0x1B0, 'close': 0x1F4, 'yesno': 0x260, 'talk_se': 0x2C8,
         'eye': 0x644, 'face': 0x510, 'wait_acmd': 0x4BC, 'wait_frames': 0x668, 'wait_fade': 0x210,
         'wait_se': 0x6D0, 'mapchange': 0x724, 'fade_in': 0x30}
FERRY_FADE_NATIVE = 33       # unnamed native the ferry calls as (1, 2, 45) before waiting on the fade
GIVE_ROUTINE = 0xC0C         # shared script 10: MsgLoad, ItemAddCheck, ItemAdd + fanfare + messages
# Captain Briney's boat scene. Shared script 41 (GlobalCall 10290), the retail Briney routine, plays it from his
# Route 104 dock through sub_1FC: CallApplicationDemo(9, 0 x7, 30), then a one-frame yield, then the map change.
# Before it, the routine sets the saved work 16697 (Briney's boat state) to 6 (to Dewford) or 7 (to Route 109).
APP_DEMO_BOAT, APP_DEMO_BOAT_ARG = 9, 30
WORK_BRINEY_BOAT, BRINEY_BOAT_DEMO_STATE = 16697, 6
WORK_TALK_TARGET = 32785     # temporary work: the NPC being talked to
WORK_YESNO = 32784           # temporary work the yes/no window answers in

# --- Texts ------------------------------------------------------------------------------------
# One list per zone text file; index = message number. Spanish and English are written for this
# event; other languages fall back to English until translated.
TEXT = {
    'harbor': {
        'es': [
            'Aquí no se ve más que mar y más mar...',
            '¡Eh, tú! Tienes pinta de ser alguien que no le teme\na nada. '
            'Hace poco, una marea muy rara arrastró esto hasta el\nmuelle.',
            'Es un mapa viejísimo... Marca una isla que no figura\nen ninguna carta de navegación de Hoenn.',
            'Yo ya no estoy para aventuras. Quédatelo tú.',
            'Si quieres saber adónde lleva, pregúntale al capitán\nArenque. ¡Mira, justo por ahí viene!',
            '¿Has ido ya a ver al capitán Arenque?',
            '¡Hombre, [VAR 0100 0]! ¿Qué me traes ahí?',
            '¡Pero si es un mapa antiquísimo!\nEsa isla... ¡Es la Isla Suprema!',
            'Los viejos marineros contaban que allí vive un\nPokémon que nadie ha logrado ver de cerca.',
            'El S.S. Marea es muy grande para esas aguas, pero\nmi viejo bote sí puede llegar.\n¿Zarpamos ahora mismo?',
            '¡Así me gusta! ¡Rumbo a la Isla Suprema!',
            'Cuando quieras ir, aquí me tendrás.',
            '¿Volvemos a la Isla Suprema?',
            '¡Pii, piii!',
        ],
        'en': [
            'Nothing but sea as far as the eye can see...',
            'Hey, you! You look like you fear nothing.\n'
            'A strange tide washed this up on the pier a\nwhile ago.',
            'It is an ancient map... It shows an island that is\nnot on any chart of Hoenn.',
            'My adventuring days are over. You keep it.',
            'If you want to know where it leads, ask Captain\nBriney. Look, here he comes now!',
            'Have you been to see Captain Briney yet?',
            'Well, if it isn\'t [VAR 0100 0]! What have you got there?',
            'Why, that is a very old map!\nThat island... It is Faraway Island!',
            'Old sailors used to say a Pokémon lives there that\nno one has ever seen up close.',
            'The S.S. Tidal is too big for those waters, but my old\nboat can make it.\nShall we set sail right now?',
            'That\'s the spirit! Next stop, Faraway Island!',
            'Whenever you want to go, you know where to find me.',
            'Shall we head back to Faraway Island?',
            'Peeko!',
        ],
    },
    'island': {
        'es': [
            '¡Tierra a la vista! Esta es la Isla Suprema.\nTe espero aquí con el bote.',
            '¿Volvemos a Ciudad Calagua?',
            '¡Leven anclas! ¡Rumbo a Calagua!',
            'Tómate el tiempo que necesites.',
        ],
        'en': [
            'Land ho! This is Faraway Island.\nI will wait for you here with the boat.',
            'Shall we head back to Lilycove City?',
            'Anchors aweigh! Next stop, Lilycove!',
            'Take as long as you need.',
        ],
    },
    'meadow': {
        'es': ['¡Miu!', 'Mew ha desaparecido entre la hierba...', '¡Mew ha huido entre la hierba!',
               '¡Mew no tiene adónde huir!'],
        'en': ['Mew!', 'Mew vanished into the grass...', 'Mew fled into the grass!', 'Mew has nowhere left to run!'],
    },
}
H = {k: HARBOR_TEXT_BASE + i for i, k in enumerate(['sea', 'giver_intro', 'giver_map', 'giver_keep', 'giver_briney', 'giver_after',
                                 'briney_hi', 'briney_map', 'briney_legend', 'briney_ask', 'briney_go',
                                 'briney_no', 'briney_again', 'peeko'])}
I = {k: i for i, k in enumerate(['arrive', 'ask_back', 'go_back', 'stay'])}
M = {k: i for i, k in enumerate(['cry', 'vanished', 'fled', 'cornered'])}


# --- Script building --------------------------------------------------------------------------
class Writer:
    """Conversation and travel idioms of the ferry script, emitted into a Program."""

    def __init__(self, program, ferry, helpers, fade_native):
        self.p, self.ferry, self.h, self.fade_native = program, ferry, helpers, fade_native
        self.yield_label = 'L4'   # the base script's yield stub (native 0 + HALT), as import_helpers assumes
        self.serial = 0

    def label(self, stem):
        self.serial += 1
        return f'{stem}_{self.serial}'

    def talk_begin(self, npc):
        p, h = self.p, self.h
        p.sysreq('WorkGet', WORK_TALK_TARGET)
        p.emit('STOR_P_S_PRI', npc)
        p.sysreq('_WordSetRegister', 1, 0, 0)  # buffer 0 = player name, as retail sub_B8 does before [VAR 0100 0]
        p.call(h['talk_se'])
        p.call(h['eye'], ('local', npc))
        p.sysreq('TalkMdlSetEye', 255, ('local', npc), 0)
        p.call(h['face'], ('local', npc), 255, 6, 0)
        p.call(h['wait_acmd'], -1)

    def say(self, npc, line):
        self.p.call(self.h['msg'], line, ('local', npc), 0, 256, 0)
        self.p.call(self.h['keywait'])

    def last(self, npc, line):
        self.p.call(self.h['msg'], line, ('local', npc), 0, 256, 0)
        self.p.sysreq('LastKeyWait')

    def talk_end(self, npc):
        p = self.p
        p.call(self.h['close'], 0)
        p.sysreq('TalkMdlClearEye', 255)
        p.sysreq('TalkMdlClearEye', ('local', npc))
        p.call(self.h['wait_frames'], 1)

    def if_zero(self, target):
        self.p.emit('JZER', target)

    def if_nonzero(self, target):
        self.p.emit('JNZ', target)

    def travel(self, zone, x, height, y, direction):
        p, h = self.p, self.h
        p.sysreq(self.fade_native, 1, 2, 45)
        p.call(h['wait_fade'])
        # Briney's boat scene, set up as his retail routine does. His story state (work 16697) is kept on the
        # stack and written back afterwards, so his boat stays wherever the player's story left it.
        p.sysreq('WorkGet', WORK_BRINEY_BOAT)
        p.emit('PUSH_PRI', 0)
        p.sysreq('WorkSet', WORK_BRINEY_BOAT, BRINEY_BOAT_DEMO_STATE)
        p.sysreq('CallApplicationDemo', APP_DEMO_BOAT, 0, 0, 0, 0, 0, 0, 0, APP_DEMO_BOAT_ARG)
        p.call(self.yield_label, 1)
        p.push(WORK_BRINEY_BOAT)
        p.emit('SYSREQ_N', 'WorkSet', 8)   # WorkSet(16697, saved value still on the stack)
        p.call(h['mapchange'], zone, x, height, y, direction, 0)


def import_helpers(program, ferry, shared10, yield_label):
    helpers = {name: program.transplant(ferry, address, f'f{name}_', yield_label)
               for name, address in FERRY.items()}
    helpers['give'] = program.transplant(shared10, GIVE_ROUTINE, 'give_', yield_label)
    return helpers


def add_cases(program, main_label, cases):
    """Add (event id -> label) entries to the CASETBL the main dispatcher switches on."""
    start = next(i for i, item in enumerate(program.items) if item == ('label', main_label))
    index = next(i for i in range(start, len(program.items))
                 if not isinstance(program.items[i], tuple) and program.items[i].op == OP['CASETBL'])
    table = program.items[index]
    pairs = [(table.args[2 + 2 * k], table.args[3 + 2 * k]) for k in range(table.args[0])]
    taken = {value for value, _ in pairs}
    for value, label in cases.items():
        if value in taken:
            raise ValueError(f'Event id {value} already dispatched')
        pairs.append((value, label))
    pairs.sort()
    table.args = [len(pairs), table.args[1]] + [x for pair in pairs for x in pair]
    end = next(i for i in range(index + 1, len(program.items)) if not isinstance(program.items[i], tuple))
    end_label = f'case_end_{main_label}'
    program.items.insert(end, ('label', end_label))
    return end_label


def case_stub(program, label, routine, end_label):
    program.label(label)
    program.emit('PUSH_P_C', 0)
    program.emit('CALL', routine)
    program.emit('JUMP', end_label)


def begin_routine(program, label, locals_=1):
    program.label(label)
    program.emit('PROC', 0)
    program.emit('STACK_P', -4 * locals_)


def end_routine(program, locals_=1):
    program.emit('STACK_P', 4 * locals_)
    program.emit('ZERO_PRI', 0)
    program.emit('RETN', 0)


def harbor_script(base, ferry, shared10):
    """Lilycove harbor: the old sailor who hands over the map, and Captain Briney's crossing."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    h = import_helpers(p, ferry, shared10, 'L4')
    w = Writer(p, ferry, h, ferry.natives[FERRY_FADE_NATIVE][1])
    end = add_cases(p, main, {EV_GIVER: 'case_giver', EV_BRINEY: 'case_briney'})
    case_stub(p, 'case_giver', 'giver', end)
    case_stub(p, 'case_briney', 'briney', end)
    npc = -4

    begin_routine(p, 'giver')
    w.talk_begin(npc)
    w.p.sysreq('FlagGet', FLAG_MAP_RECEIVED)
    w.if_nonzero('giver_done')
    w.p.sysreq('FlagGet', FLAG_DELTA_DONE)
    w.if_nonzero('giver_give')
    w.last(npc, H['sea'])
    p.emit('JUMP', 'giver_end')
    p.label('giver_give')
    w.say(npc, H['giver_intro'])
    p.call(h['give'], ITEM_OLD_SEA_MAP, 1, 1)
    p.sysreq('ItemGetNum', ITEM_OLD_SEA_MAP)
    w.if_zero('giver_end')
    p.sysreq('FlagSet', FLAG_MAP_RECEIVED)
    p.sysreq('WorkSet', WORK_PROGRESS, PROGRESS_MAP)
    w.say(npc, H['giver_map'])
    w.say(npc, H['giver_keep'])
    # Captain Briney comes onto the pier now, as the retail scripts bring NPCs in: clear the hide flag, add it.
    p.sysreq('FlagReset', FLAG_HIDE_BRINEY)
    p.sysreq('MdlAdd', HARBOR_NPC_BRINEY)
    w.last(npc, H['giver_briney'])
    p.emit('JUMP', 'giver_end')
    p.label('giver_done')
    w.last(npc, H['giver_after'])
    p.label('giver_end')
    w.talk_end(npc)
    end_routine(p)

    begin_routine(p, 'briney')
    w.talk_begin(npc)
    p.sysreq('WorkGet', WORK_PROGRESS)
    p.emit('CONST_P_ALT', PROGRESS_ISLAND)
    p.emit('JSGEQ', 'briney_again')
    w.say(npc, H['briney_hi'])
    w.say(npc, H['briney_map'])
    w.say(npc, H['briney_legend'])
    p.sysreq('WorkSet', WORK_PROGRESS, PROGRESS_ISLAND)
    w.say(npc, H['briney_ask'])
    p.emit('JUMP', 'briney_ask')
    p.label('briney_again')
    w.say(npc, H['briney_again'])
    p.label('briney_ask')
    p.call(h['yesno'], 0)
    w.if_zero('briney_no')
    w.last(npc, H['briney_go'])
    w.talk_end(npc)
    w.travel(*ARRIVE_ISLAND)
    p.emit('JUMP', 'briney_end')
    p.label('briney_no')
    w.last(npc, H['briney_no'])
    w.talk_end(npc)
    p.label('briney_end')
    end_routine(p)
    return p.build_script(main)


def harbor_entity_script(base):
    """On harbor load: the sailor shows after the Delta Episode until he gives the map; Briney once it is held."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    loader = _case_label(p, main, 0)
    p.items.insert(p.items.index(('label', loader)) + 1, Op(OP['CALL'], ['harbor_flags']))
    p.items.insert(p.items.index(('label', loader)) + 1, Op(OP['PUSH_P_C'], [0]))
    p.label('harbor_flags')
    p.emit('PROC', 0)
    p.sysreq('FlagSet', FLAG_HIDE_GIVER)
    p.sysreq('FlagSet', FLAG_HIDE_BRINEY)
    p.sysreq('FlagGet', FLAG_DELTA_DONE)
    p.emit('JZER', 'harbor_flags_end')
    p.sysreq('FlagGet', FLAG_MAP_RECEIVED)
    p.emit('JNZ', 'harbor_show_briney')
    p.sysreq('FlagReset', FLAG_HIDE_GIVER)
    p.emit('JUMP', 'harbor_flags_end')
    p.label('harbor_show_briney')
    p.sysreq('FlagReset', FLAG_HIDE_BRINEY)
    p.label('harbor_flags_end')
    p.emit('ZERO_PRI', 0)
    p.emit('RETN', 0)
    return p.build_script(main)


def meadow_entity_script(base):
    """On meadow load: restart the chase unless Mew has already been captured."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    loader = _case_label(p, main, 0)
    p.items.insert(p.items.index(('label', loader)) + 1, Op(OP['CALL'], ['meadow_reset']))
    p.items.insert(p.items.index(('label', loader)) + 1, Op(OP['PUSH_P_C'], [0]))
    p.label('meadow_reset')
    p.emit('PROC', 0)
    p.sysreq('WorkSet', WORK_MEW_SPOT, MEW_SPOT_INACTIVE)
    p.sysreq('FlagGet', FLAG_MEW_CAPTURED)
    p.emit('JNZ', 'meadow_reset_end')
    p.sysreq('WorkSet', WORK_MEW_SPOT, 0)
    p.label('meadow_reset_end')
    p.emit('ZERO_PRI', 0)
    p.emit('RETN', 0)
    return p.build_script(main)


def _case_label(program, main_label, value):
    start = next(i for i, item in enumerate(program.items) if item == ('label', main_label))
    table = next(item for item in program.items[start:] if not isinstance(item, tuple) and item.op == OP['CASETBL'])
    pairs = {table.args[2 + 2 * k]: table.args[3 + 2 * k] for k in range(table.args[0])}
    return pairs[value]


def skeleton(placeholder, donor):
    """A fresh zone script: the placeholder's tables and public variables, the donor's yield routine."""
    p = Program(placeholder)
    p.native_hashes = []
    p.emit('HALT_P', 0)
    p.transplant(donor, 4, 'yield_', None)
    return p, 'yield_4'


def island_script(base, ferry, shared10):
    """Faraway Island shore: Captain Briney waits with the boat. Built on the donor zone's retail script."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    h = import_helpers(p, ferry, shared10, 'L4')
    w = Writer(p, ferry, h, ferry.natives[FERRY_FADE_NATIVE][1])
    end = add_cases(p, main, {EV_ISLAND_BRINEY: 'case_island_briney'})
    case_stub(p, 'case_island_briney', 'island_briney', end)
    npc = -4
    begin_routine(p, 'island_briney')
    w.talk_begin(npc)
    w.say(npc, I['ask_back'])
    p.call(h['yesno'], 0)
    w.if_zero('island_stay')
    w.last(npc, I['go_back'])
    w.talk_end(npc)
    w.travel(*ARRIVE_HARBOR)
    p.emit('JUMP', 'island_end')
    p.label('island_stay')
    w.last(npc, I['stay'])
    w.talk_end(npc)
    p.label('island_end')
    end_routine(p)
    return p.build_script(main)


def meadow_script(base, ferry, shared10):
    """Faraway Island interior: Mew hides in the grass and flees from spot to spot until it is cornered."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    h = import_helpers(p, ferry, shared10, 'L4')
    w = Writer(p, ferry, h, ferry.natives[FERRY_FADE_NATIVE][1])
    end = add_cases(p, main, {EV_MEW: 'case_mew', EV_MEW_FLEE: 'case_mew_flee'})
    case_stub(p, 'case_mew', 'mew', end)
    case_stub(p, 'case_mew_flee', 'mew_flee', end)
    npc, result = -4, -8
    last = len(MEW_SPOTS) - 1

    # Talking to Mew: before it is cornered it just slips away; at the last spot the battle starts.
    begin_routine(p, 'mew', 2)
    p.sysreq('WorkGet', WORK_TALK_TARGET)
    p.emit('STOR_P_S_PRI', npc)
    p.sysreq('VoicePlay', SPECIES_MEW, 0)
    p.call(h['wait_frames'], 40)
    p.sysreq('WorkGet', WORK_MEW_SPOT)
    p.emit('EQ_P_C_PRI', last)
    p.emit('JNZ', 'mew_cornered')
    p.emit('PUSH_P_C', 0)
    p.emit('CALL', 'mew_flee')
    p.emit('JUMP', 'mew_end')
    p.label('mew_cornered')
    w.last(npc, M['cornered'])
    p.call(h['close'], 0)
    p.sysreq('FlagSet', FLAG_MEW_BATTLED)
    p.sysreq('CallWildBattle', STATIC_MEW)
    p.sysreq('WildBattleResultGet')
    p.emit('STOR_P_S_PRI', result)
    p.sysreq('MdlDel', ('local', npc))
    # Mew is absent for the rest of this visit; only the next map load may restart the chase.
    p.sysreq('WorkSet', WORK_MEW_SPOT, MEW_SPOT_INACTIVE)
    p.emit('LOAD_P_S_PRI', result)
    p.emit('EQ_P_C_PRI', RESULT_CAPTURED)
    p.emit('JZER', 'mew_escaped')
    p.sysreq('FlagSet', FLAG_MEW_CAPTURED)
    p.emit('JUMP', 'mew_end')
    p.label('mew_escaped')
    # CallWildBattle returns with the field faded out. Retail Registeel (zone 159, sub_840)
    # restores it with the same helper before showing the non-capture message.
    p.call(h['fade_in'], 2, 4)
    p.call(h['wait_fade'])
    # Narrate from the player: the former speaker was removed by MdlDel above.
    p.call(h['msg'], M['vanished'], 255, 0, 256, 0)
    p.sysreq('LastKeyWait')
    p.call(h['close'], 0)
    p.label('mew_end')
    end_routine(p, 2)

    # Flee: Mew darts to the next spot and the trigger of that spot becomes the armed one.
    begin_routine(p, 'mew_flee', 1)
    p.sysreq('FlagGet', FLAG_MEW_CAPTURED)
    p.emit('JNZ', 'flee_end')
    p.sysreq('WorkGet', WORK_MEW_SPOT)
    p.emit('SWITCH', 'flee_table')
    targets = []
    for k in range(last):
        (x, y), _ = MEW_SPOTS[k + 1]
        p.label(f'flee_{k}')
        p.sysreq('VoicePlay', SPECIES_MEW, 0)
        p.sysreq('MdlAcmdInit', MEADOW_NPC_MEW)
        p.sysreq('MdlAcmdMakeMoveEx', MEW_MOVE_A, x, MEW_MOVE_B, y, 0, 1, 1)
        p.sysreq('MdlAcmdSetEnd')
        p.call(h['wait_acmd'], MEADOW_NPC_MEW)
        p.sysreq('WorkSet', WORK_MEW_SPOT, k + 1)
        p.emit('JUMP', 'flee_done')
        targets.append((k, f'flee_{k}'))
    p.label('flee_default')
    p.emit('JUMP', 'flee_end')
    p.label('flee_table')
    table = [len(targets), 'flee_default']
    for k, label in targets:
        table += [k, label]
    p.items.append(Op(OP['CASETBL'], table))
    p.label('flee_done')
    p.call(h['msg'], M['fled'], 255, 0, 256, 0)
    p.sysreq('LastKeyWait')
    p.call(h['close'], 0)
    p.label('flee_end')
    end_routine(p, 1)
    return p.build_script(main)


def meadow_probe_script(base, ferry, shared10, calls):
    """LABORATORY: talking to Mew runs MdlAcmdMakeMoveEx with each argument tuple in `calls`, then waits."""
    p = Program.from_script(base)
    main = f'L{base.main:x}'
    h = import_helpers(p, ferry, shared10, 'L4')
    end = add_cases(p, main, {EV_MEW: 'case_probe'})
    case_stub(p, 'case_probe', 'probe', end)
    npc = -4
    begin_routine(p, 'probe')
    p.sysreq('WorkGet', WORK_TALK_TARGET)
    p.emit('STOR_P_S_PRI', npc)
    for args in calls:
        p.sysreq('MdlAcmdInit', ('local', npc))
        p.sysreq('MdlAcmdMakeMoveEx', *args)
        p.sysreq('MdlAcmdSetEnd')
        p.call(h['wait_acmd'], ('local', npc))
        p.call(h['wait_frames'], 60)
    end_routine(p)
    return p.build_script(main)


def _dispatcher(p, cases):
    """main: switch on the event id the engine writes into data cell 0."""
    p.label('main')
    p.emit('PROC', 0)
    p.emit('LOAD_P_PRI', 0)
    p.emit('SWITCH', 'main_table')
    p.label('main_default')
    p.emit('SYSREQ_N', 'CommandNOP', 0)
    p.emit('JUMP', 'main_end')
    for value, routine in cases.items():
        p.label(f'main_case_{value}')
        p.emit('PUSH_P_C', 0)
        p.emit('CALL', routine)
        p.emit('JUMP', 'main_end')
    p.label('main_table')
    table = [len(cases), 'main_default']
    for value in sorted(cases):
        table += [value, f'main_case_{value}']
    p.items.append(Op(OP['CASETBL'], table))
    p.label('main_end')
    p.emit('ZERO_PRI', 0)
    p.emit('RETN', 0)
