"""Frontier Brains, common part (frontier/brains.py, frontier/asm/brains_cro.s): appearance rule, data, the zone
script routines in scripts/pawn_vm.py and the DllField.cro routines in Unicorn with the code.bin functions stubbed.
Checks the generated logic, not the game (Azahar: reports/frontier.md §39)."""
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import brains  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
from pawn import OP, Op, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

FACILITIES = list(fp.ROUTE)


# --- appearance rule ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize('facility', FACILITIES)
def test_due_follows_the_source_rule(facility):
    silver, gold, period = brains.APPEARANCES[facility]
    for unit in range(1, gold + 4 * period):
        assert brains.due(facility, unit, 0) == (brains.SILVER if unit == silver else 0)
        assert brains.due(facility, unit, 1) == (brains.GOLD if unit == gold else 0)
        both = brains.SILVER if unit == silver else brains.GOLD if unit >= gold and (unit - gold) % period == 0 else 0
        assert brains.due(facility, unit, 3) == both
    # S-1 / S / S+1 around both thresholds, from the design table (cerebros.md §1)
    for s in (silver, gold):
        assert brains.due(facility, s - 1, 0) == brains.due(facility, s + 1, 0) == 0


def test_design_table_values():
    assert brains.APPEARANCES['tower'] == (35, 70, 35)
    reps = [u for u in range(1, 200) if brains.due('tower', u, 3)]
    assert reps == [35, 70, 105, 140, 175]
    assert [u for u in range(1, 300) if brains.due('pike', u, 3)] == [28, 140, 196, 252]
    assert [u for u in range(1, 150) if brains.due('pyramid', u, 3)] == [21, 70, 105, 140]
    assert brains.ENABLED == ('factory', 'tower', 'palace', 'arena', 'dome')


def test_symbols_work():
    word = 0
    word = brains.won(word, 2, brains.SILVER)
    assert brains.symbols_of(word, 2) == 1 and word == 1 << 2
    word = brains.won(word, 2, brains.GOLD)
    assert brains.symbols_of(word, 2) == 3
    assert brains.won(word, 2, brains.SILVER) == word          # a silver repeat keeps gold
    word = brains.won(word, 7, brains.GOLD)
    assert brains.symbols_of(word, 7) == 3 and word < 1 << 14   # bits 14-15 stay 0
    assert brains.symbols_of(2 << 4, 3) == 3                    # invalid 2 reads as both


# --- data ---------------------------------------------------------------------------------------------------------

def test_works_and_ids_are_distinct_and_free():
    import ids
    used = {fp.WORK_IV, fp.WORK_ROUTE, *fp.WORK_SETS, *fp.WORK_RIVAL, fp.PIKE_WILD, *fp.PIKE_HP, *fp.PIKE_ST,
            *fp.DOME_FIGHT, *fp.DOME_FORCED, *fp.PYRAMID_SEL, fp.PYRAMID_COUNT,
            *(w for _, s in fp.STREAK_ROUTES.values() for w in (s, s + 1, s + 2))}
    mine = {brains.WORK_SYMBOLS, brains.WORK_BRAIN, brains.WORK_PYRAMID, brains.WORK_MSG}
    assert len(mine) == 4 and not mine & used
    assert not mine & set(range(0x4010, 0x4020))                # the block the game clears (§25)
    assert brains.GLOBAL_SAY not in (factory.GLOBAL_DRAFT, factory.GLOBAL_SWAP, 9773, 9774, 9775, 9776, 9777)
    assert 9770 < brains.GLOBAL_SAY <= 9779
    if hasattr(ids, 'RESERVED'):
        assert not mine & set(ids.RESERVED)


@pytest.fixture(scope='module')
def game_names():
    if not (Path(fd.GAME) / fd.GAMETEXT_ES).exists():
        pytest.skip('Local baseline required')
    return {k: fd.names(fd.GAME, i) for k, i in (('species', 98), ('moves', 14), ('items', 114), ('natures', 51),
                                                  ('classes', 21), ('trainers', brains.TEXT_TRAINER_NAMES))}


def test_ids_match_the_game_text(game_names):
    spanish = {'ALAKAZAM': 'Alakazam', 'ENTEI': 'Entei', 'SNORLAX': 'Snorlax', 'RAIKOU': 'Raikou', 'LATIOS': 'Latios',
               'CROBAT': 'Crobat', 'SLAKING': 'Slaking', 'LAPRAS': 'Lapras', 'ARCANINE': 'Arcanine',
               'SUICUNE': 'Suicune', 'HERACROSS': 'Heracross', 'UMBREON': 'Umbreon', 'SHEDINJA': 'Shedinja',
               'GENGAR': 'Gengar', 'BRELOOM': 'Breloom', 'SWAMPERT': 'Swampert', 'SALAMENCE': 'Salamence',
               'CHARIZARD': 'Charizard', 'METAGROSS': 'Metagross', 'LATIAS': 'Latias'}
    assert {k: game_names['species'][v] for k, v in brains.SPECIES.items()} == spanish
    assert game_names['moves'][brains.MOVES['RETURN']] == 'Retribución'
    assert game_names['moves'][brains.MOVES['THUNDER_PUNCH']] == 'Puño Trueno'
    assert game_names['moves'][brains.MOVES['CALM_MIND']] == 'Paz Mental'
    assert game_names['moves'][brains.MOVES['BELLY_DRUM']] == 'Tambor'
    assert {k: game_names['items'][v] for k, v in brains.ITEMS.items()} == {
        'BRIGHT_POWDER': 'Polvo Brillo', 'LUM_BERRY': 'Baya Ziuela', 'QUICK_CLAW': 'Garra Rápida',
        'CHESTO_BERRY': 'Baya Atania', 'SCOPE_LENS': 'Periscopio', 'WHITE_HERB': 'Hierba Blanca',
        'KINGS_ROCK': 'Roca del Rey', 'SALAC_BERRY': 'Baya Aslac', 'LEFTOVERS': 'Restos', 'FOCUS_BAND': 'Cinta Focus'}
    assert {k: game_names['natures'][v] for k, v in brains.NATURES.items()} == {
        'HARDY': 'fuerte', 'LONELY': 'huraña', 'ADAMANT': 'firme', 'HASTY': 'activa', 'MODEST': 'modesta',
        'QUIET': 'mansa', 'JOLLY': 'alegre', 'CALM': 'serena', 'BRAVE': 'audaz'}
    spanish_moves = {'CONFUSE_RAY': 'Rayo Confuso', 'DOUBLE_TEAM': 'Doble Equipo', 'TOXIC': 'Tóxico', 'FLY': 'Vuelo',
                     'EARTHQUAKE': 'Terremoto', 'SWAGGER': 'Contoneo', 'SHADOW_BALL': 'Bola Sombra',
                     'BRICK_BREAK': 'Demolición', 'ICE_BEAM': 'Rayo Hielo', 'HORN_DRILL': 'Perforador',
                     'PROTECT': 'Protección', 'OVERHEAT': 'Sofoco', 'EXTREME_SPEED': 'Veloc. Extrema',
                     'ROAR': 'Rugido', 'HYPER_BEAM': 'Hiperrayo', 'YAWN': 'Bostezo', 'BLIZZARD': 'Ventisca',
                     'SURF': 'Surf', 'BITE': 'Mordisco',
                     'MEGAHORN': 'Megacuerno', 'ROCK_TOMB': 'Tumba Rocas', 'ENDURE': 'Aguante',
                     'REVERSAL': 'Inversión', 'FAINT_ATTACK': 'Finta', 'AERIAL_ACE': 'Golpe Aéreo',
                     'DOUBLE_EDGE': 'Doble Filo', 'HYPNOSIS': 'Hipnosis', 'DREAM_EATER': 'Come Sueños',
                     'DESTINY_BOND': 'Mismo Destino', 'SPORE': 'Espora', 'FOCUS_PUNCH': 'Puño Certero',
                     'GIGA_DRAIN': 'Gigadrenado', 'HEADBUTT': 'Golpe Cabeza'}
    assert {k: game_names['moves'][brains.MOVES[k]] for k in spanish_moves} == spanish_moves
    assert game_names['classes'][brains.CLASSES['palace']] == 'Médium'
    assert game_names['classes'][brains.CLASSES['tower']] == 'Entrenadora Guay'
    assert len(game_names['trainers']) == brains.TRAINER_FIRST       # names of the 129 retail Normal trainers


def test_anabel_sets_are_the_annex():
    sets = brains.sets()
    silver = [fd.parse_set(sets[brains.set_index('tower', brains.SILVER, k)]) for k in range(3)]
    gold = [fd.parse_set(sets[brains.set_index('tower', brains.GOLD, k)]) for k in range(3)]
    assert [s['species'] for s in silver] == [65, 244, 143] and [s['species'] for s in gold] == [243, 381, 143]
    assert silver[0]['moves'] == (9, 7, 8, 50) and silver[0]['item'] == 213 and silver[0]['nature'] == 15
    assert silver[1]['moves'] == (126, 347, 216, 46) and silver[1]['nature'] == 1
    assert gold[2]['moves'] == (174, 216, 156, 247) and gold[2]['item'] == 150 and gold[2]['nature'] == 3
    assert silver[0]['evs'] == 0b011101                      # HP, Def, Spe, SpA (source order HP Atk Def Spe SpA SpD)
    assert sorted(sets) == list(range(229, 253))            # the Tower's, Palace's and Arena's blocks of 6 in 223-264
    assert brains.SET_FIRST == fp.PIKE_WILD_FIRST + 6 == 223


def test_trainers_and_rows():
    trainers = brains.trainers()
    assert sorted(trainers) == list(range(129, 129 + 14))
    anabel = fd.parse_trainer(trainers[brains.trainer_id('tower', brains.SILVER)])
    assert anabel == {'class': 9, 'sets': (229, 230, 231)}
    assert fd.parse_trainer(trainers[132])['sets'] == (232, 233, 234)      # gold
    assert brains.trainer_id('tower', brains.SILVER) == 131
    names = brains.trainer_names()
    assert len(names) == 14 and names[131 - 129] == names[132 - 129] == 'Anabel'
    rows = brains.brain_rows()
    assert len(rows) == brains.ENTRY * 14
    k = 2 * (fp.ROUTE['tower'] - 1)
    trainer, iv, _ = struct.unpack_from('<HBB', rows, brains.ENTRY * k)
    assert (trainer, iv) == (131, 24)
    first = struct.unpack_from('<H6B', rows, brains.ENTRY * k + 4)
    assert first == (229, 106, 0, 152, 100, 0, 152)          # pml order HP Atk Def SpA SpD Spe
    trainer, iv, _ = struct.unpack_from('<HBB', rows, brains.ENTRY * (k + 1))
    assert (trainer, iv) == (132, 31)
    assert all(struct.unpack_from('<H', rows, brains.ENTRY * j)[0] == 0 for j in range(14) if j not in (0, 1, k, k + 1, k + 2, k + 3, k + 4, k + 5, k + 6, k + 7))


def test_texts():
    for lang in factory.STORYTEXT:
        lines = brains.lines(lang)
        assert len(lines) == (len(brains.KEYS) + len(brains.MORE_KEYS)) * brains.ROUTES + 6
        assert all(len(row) <= 44 for line in lines for row in line.split('\n')) and all(line.count('\n') <= 2
                                                                                        for line in lines)
    es = brains.lines(7)
    assert brains.MORE == 4 * brains.ROUTES
    more = brains.MORE                                       # route 1, the Factory
    assert 'Fábrica' in es[more] and 'Aún no' in es[more + 1] and 'Conocimiento' in es[more + 1]
    assert 'plata' in es[more + 2] and 'oro' in es[more + 3] and 'Habilidad' in es[more + 4 + 3]
    assert 'Anabel' in es[4 * 1] and 'Habilidad' in es[4 * 1 + 2] and 'plata' in es[4 * 1 + 2]
    assert 'oro' in es[4 * 1 + 3] and '10 PB' in es[4 * 1 + 3]


# --- zone scripts -------------------------------------------------------------------------------------------------

def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def scripts():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    import arena
    import dome
    import palace
    import pike
    import tower
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    out = {}
    for name, program in (('tower', tower.tower_program(retail)), ('palace', palace.palace_program(retail)),
                          ('arena', arena.arena_program(retail)), ('pike', pike.pike_program(retail)),
                          ('dome', dome.dome_program(retail)), ('factory', overlay.maison_program(retail))):
        out[name] = (program.build_script(f'L{retail.main:x}'), program.layout())
    out['retail'] = (retail, None)
    return out


def check(scripts, facility, route, streak, symbols=0):
    script, labels = scripts[facility]
    works = {fp.WORK_ROUTE: route, brains.WORK_SYMBOLS: symbols, brains.WORK_BRAIN: 77}
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GetMyWinCount': lambda vm, a: streak,
                     'GlobalCall': lambda vm, a: 0})
    VM(script, stubs, {}).run(labels['brains_check'])
    return works[brains.WORK_BRAIN]


@pytest.mark.parametrize('symbols', [0, 1, 3, 2])
def test_check_marks_the_tower_brain_as_due(scripts, symbols):
    route = fp.ROUTE['tower']
    sym = symbols << 2 * (route - 1) | 0x3003          # other routes' symbols do not matter
    for streak in list(range(0, 40)) + [68, 69, 70, 71, 103, 104, 105, 139]:
        variant = brains.due('tower', streak + 1, 3 if symbols == 2 else symbols)
        assert check(scripts, 'tower', route, streak, sym) == (route + 8 * variant if variant else 0), streak


@pytest.mark.parametrize('facility', ['tower', 'palace', 'arena', 'pike'])
def test_check_never_marks_routes_without_a_brain(scripts, facility):
    for route in range(0, 9):
        if route in [fp.ROUTE[f] for f in brains.ENABLED]:
            continue
        for streak in (19, 20, 27, 34, 41, 55, 139):
            for symbols in (0, 0x5555, 0x3FFF):
                assert check(scripts, facility, route, streak, symbols) == 0


def won(scripts, brain, route, symbols=0):
    script, labels = scripts['tower']
    works = {fp.WORK_ROUTE: route, brains.WORK_SYMBOLS: symbols, brains.WORK_BRAIN: brain}
    log = []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: log.append(('set', a[0], a[1])) or works.__setitem__(a[0], a[1]),
                     'GlobalCall': lambda vm, a: log.append(('global', a[0], works.get(brains.WORK_MSG)))})
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    VM(script, stubs, calls).run(labels['brains_won'])
    return works, log


def test_won_gives_the_symbol_bonus_and_line(scripts):
    route = fp.ROUTE['tower']
    works, log = won(scripts, route + 8, route)
    assert brains.symbols_of(works[brains.WORK_SYMBOLS], route) == 1 and works[brains.WORK_BRAIN] == 0
    assert ('bp', fd.BRAIN_BONUS) in log
    assert ('global', brains.GLOBAL_SAY, 4 * (route - 1) + 2) in log
    works, log = won(scripts, route + 16, route, symbols=0x1001 | 1 << 2)
    assert works[brains.WORK_SYMBOLS] == 0x1001 | 3 << 2 and ('global', brains.GLOBAL_SAY, 4 * (route - 1) + 3) in log
    works, log = won(scripts, route + 8, route, symbols=3 << 2)
    assert works[brains.WORK_SYMBOLS] == 3 << 2 and ('bp', 10) in log    # a silver repeat: gold kept, bonus again


@pytest.mark.parametrize('brain, route', [(0, 2), (2 + 8, 3), (3 + 8, 2), (0, 0)])
def test_won_does_nothing_without_the_routes_brain(scripts, brain, route):
    works, log = won(scripts, brain, route, symbols=0x15)
    assert works[brains.WORK_SYMBOLS] == 0x15 and works[brains.WORK_BRAIN] == 0
    assert [e for e in log if e[0] != 'set' or e[1] != brains.WORK_BRAIN] == []


def test_intro(scripts):
    script, labels = scripts['tower']
    for brain, route, said in ((2 + 16, 2, 4 + 1), (2 + 8, 2, 4), (0, 2, None), (2 + 8, 3, None)):
        works = {fp.WORK_ROUTE: route, brains.WORK_BRAIN: brain}
        log = []
        stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                         'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                         'GlobalCall': lambda vm, a: log.append((a[0], works[brains.WORK_MSG]))})
        result = VM(script, stubs, {}).run(labels['brains_intro'])
        assert (result, log) == ((1, [(brains.GLOBAL_SAY, said)]) if said is not None else (0, []))


@pytest.mark.parametrize('facility', ['tower', 'factory'])
def test_lost_says_the_brains_line_once(scripts, facility):
    script, labels = scripts[facility]
    for brain, route, said in ((1 + 8, 1, brains.MORE), (1 + 16, 1, brains.MORE), (2 + 16, 2, brains.MORE + 4),
                               (0, 1, None), (2 + 8, 1, None), (1 + 8, 0, None)):
        works = {fp.WORK_ROUTE: route, brains.WORK_BRAIN: brain, brains.WORK_SYMBOLS: 0x15}
        log = []
        stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                         'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                         'GlobalCall': lambda vm, a: log.append((a[0], works[brains.WORK_MSG]))})
        VM(script, stubs, {}).run(labels['brains_lost'])
        assert log == ([(brains.GLOBAL_SAY, said)] if said is not None else [])
        assert works[brains.WORK_BRAIN] == 0 and works[brains.WORK_SYMBOLS] == 0x15   # no symbol, no prize


def test_factory_symbols_consult(scripts):
    script, labels = scripts['factory']
    route = fp.ROUTE['factory']
    for word, k in ((0, 1), (1, 2), (3, 3), (2, 3), (0x3FFC, 1), (0x3FFD, 2), (0x5557, 3)):
        works = {brains.WORK_SYMBOLS: word}
        log = []
        stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                         'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                         'GlobalCall': lambda vm, a: log.append((a[0], works[brains.WORK_MSG]))})
        VM(script, stubs, {}).run(labels['brains_symbols'])
        assert log == [(brains.GLOBAL_SAY, brains.MORE + 4 * (route - 1) + k)], word
        assert works[brains.WORK_SYMBOLS] == word


def test_factory_symbols_menu_entry(scripts):
    script, labels = scripts['factory']
    ins = decode(script.code)
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    add = s32(gf_hash('ListMenuAdd'))
    entries = [(ins[j - 1].args[0], ins[j - 2].args[0]) for j, x in enumerate(ins)
               if x.op == OP['SYSREQ_N'] and names[x.args[0]] == add and labels['L14f4'] < x.address
               < labels[factory.RECEPTION_RESULT]]
    assert entries == [(53, 0), (54, 1), (74, 2), (factory.LINE_OPTION, factory.MENU_FACTORY),
                       (factory.LINE_SYMBOLS, brains.MENU_SYMBOLS), (55, 3)]
    # value 5 calls brains_symbols and goes back to the menu, ahead of every other value
    k = next(j for j, x in enumerate(ins) if x.address == labels[factory.RECEPTION_RESULT])
    assert [ins[k + j].op for j in (0, 1, 2, 4)] == [OP['LOAD_P_S_PRI'], OP['EQ_P_C_PRI'], OP['JZER'],
                                                 OP['CALL']]
    assert ins[k + 2].args[0] and ins[k + 1].args == [brains.MENU_SYMBOLS]
    assert ins[k + 4].address + ins[k + 4].args[0] == labels['brains_symbols']
    assert ins[k + 5].op == OP['CONST_S'] and ins[k + 5].args == [factory.RECEPTION_AGAIN, 1]
    assert ins[k + 6].op == OP['JUMP'] and ins[k + 6].address + ins[k + 6].args[0] == labels[factory.RECEPTION_NEXT]
    for other in ('pike',):         # other receptions connect theirs in their own tasks
        assert 'brains_symbols' not in scripts[other][1]


@pytest.mark.parametrize('facility', ['tower', 'palace', 'arena', 'pike', 'dome', 'factory'])
def test_maison_boss_check_is_off_on_frontier_routes(scripts, facility):
    script, labels = scripts[facility]
    for route, rank, wins, expected in ((0, 0, 20, 1), (0, 1, 50, 1), (0, 0, 19, 0), (1, 0, 20, 0), (2, 0, 20, 0),
                                        (7, 1, 50, 0)):
        stubs = natives({'WorkGet': lambda vm, a: route if a[0] == fp.WORK_ROUTE else 0})
        assert VM(script, stubs, {}).run(labels[brains.BOSS_CHECK], rank, wins) == expected


def test_install_points(scripts):
    script, labels = scripts['tower']
    ins = decode(script.code)
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    at = {x.address: k for k, x in enumerate(ins)}
    # 0x2b98 starts by calling brains_check
    k = at[labels[brains.CHOOSE]]
    assert [ins[k + j].op for j in range(4)] == [OP['PROC'], OP['PUSH_P_C'], OP['CALL'], OP['PUSH_C']]
    assert ins[k + 2].address + ins[k + 2].args[0] == labels['brains_check']
    # brains_won right before IsBoss
    boss = next(j for j, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == s32(gf_hash('IsBoss')))
    assert ins[boss - 1].op == OP['CALL'] and ins[boss - 1].address + ins[boss - 1].args[0] == labels['brains_won']
    # intro before the start message, which it skips when it says the Brain's line
    msg = next(j for j, x in enumerate(ins) if x.op == OP['SYSREQ_N']
               and names[x.args[0]] == s32(gf_hash(brains.START_MSG)))
    assert ins[msg - 2].op == OP['JNZ'] and ins[msg - 3].op == OP['CALL']
    assert ins[msg - 3].address + ins[msg - 3].args[0] == labels['brains_intro']
    # brains_lost (its line, WORK_BRAIN = 0) on the lost path; WORK_BRAIN = 0 in the cleanup
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for j, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[j - 1].args == [brains.WORK_BRAIN] and ins[j - 2].args == [0]]
    lost = [x.address for x in ins if x.op == OP['CALL'] and x.address + x.args[0] == labels['brains_lost']]
    assert len(lost) == 1 and labels[factory.LOST] < lost[0] < labels[factory.LOST] + 0x30
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x40 for a in clears)


@pytest.mark.parametrize('facility', ['tower', 'palace', 'arena', 'pike', 'dome', 'factory'])
def test_zone_scripts_fit(scripts, facility):
    from formats import zo_build
    script, _ = scripts[facility]
    files, _ = overlay.maison_retail(overlay.ZONES.read_bytes())
    assert len(zo_build([*files[:2], script.build(), *files[3:]])) <= 17248


# --- shared script 5 ----------------------------------------------------------------------------------------------

def test_say_routine_shows_the_line(scripts):
    import overlay as o
    sets, table, levels, cells = o.rentals()
    retail = scripts['retail'][0]
    program = factory.shared_program(o.shared_script(o.source(o.ROMFS, o.SHARED), factory.SHARED_SCRIPT), retail,
                                     cells, levels, brains.shared_cases())
    script, labels = program.build_script(f'L{program.script.main:x}'), program.layout()
    log = []
    stubs = natives({'WorkGet': lambda vm, a: 5 if a[0] == brains.WORK_MSG else 0})
    h = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {h['msg']: lambda vm, a: log.append(('msg', a[0])), h['msg_wait']: lambda vm, a: log.append(('wait',)),
             h['msg_close']: lambda vm, a: log.append(('close',))}
    VM(script, stubs, calls).run(labels['brains_say'])
    assert log == [('msg', brains.line_base() + 5), ('wait',), ('close',)]


# --- native (DllField.cro) ----------------------------------------------------------------------------------------

CRO, WORK, CTX, SAVE, PARTY, STACK, HEAP = 0x02000000, 0x08000000, 0x08100000, 0x08200000, 0x08300000, 0x08400000, 0x6
MEMBERS = (0x08310000, 0x08311000, 0x08312000)
TEMPS = (0x08320000, 0x08321000, 0x08322000)
VTABLE, FREE = 0x08330000, 0x08331000


def machine(route, brain=0, streak=0, rank=0, trainer=0):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn import arm_const as AR
    blob, symbols = brains.assemble()
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(CRO, 0x100000)
    uc.mem_map(0x100000, 0x400000)                 # code.bin stubs (hooked before they run)
    uc.mem_map(WORK, 0x500000)
    uc.mem_write(CRO + brains.AT, blob)
    for site, (name, _) in brains.SITES.items():
        uc.mem_write(CRO + site, brains.bl(site, symbols[name]))
    put = lambda at, v, f='<I': uc.mem_write(at, struct.pack(f, v))
    put(WORK + 0xb78, CTX)
    put(CTX + 0x1c, CTX + 0x100)
    put(CTX + 0x100, SAVE)
    works = SAVE + 0x13144
    put(works + 2 * (fp.WORK_ROUTE - 0x4000), route, '<H')
    put(works + 2 * (brains.WORK_BRAIN - 0x4000), brain, '<H')
    for r, (_, s) in fp.STREAK_ROUTES.items():
        put(works + 2 * (s - 0x4000), streak if r == route else 999, '<H')
    put(WORK + 0x838, rank, '<B')
    put(WORK + 1, 1, '<B')
    put(WORK + 4, trainer)
    put(WORK + 0xb70, HEAP)
    put(WORK + 0x670, PARTY)
    for k, m in enumerate(MEMBERS):
        put(PARTY + 4 * k, m)
    put(PARTY + 0x18, 3, '<B')
    for t in TEMPS:
        put(t, VTABLE)
        put(t + 0xc, t + 0x800)                    # core
    put(VTABLE + 8, FREE)
    uc.reg_write(AR.UC_ARM_REG_SP, STACK)
    return uc, AR, put


def run(uc, AR, site, args, stubs):
    """Executes the `bl` at CRO + site with r0-r2 = args; stubs {code.bin address: fn(uc, r0..r3, sp) -> r0}."""
    from unicorn import UC_HOOK_CODE
    calls = []

    def hook(m, address, size, data):
        if address in stubs or address == FREE:
            regs = [m.reg_read(r) for r in (AR.UC_ARM_REG_R0, AR.UC_ARM_REG_R1, AR.UC_ARM_REG_R2, AR.UC_ARM_REG_R3)]
            sp = m.reg_read(AR.UC_ARM_REG_SP)
            stack = struct.unpack('<2I', m.mem_read(sp, 8))
            name = 'free' if address == FREE else address
            calls.append((name, *regs, *stack))
            result = stubs[address](m, regs) if address in stubs else 0
            m.reg_write(AR.UC_ARM_REG_R0, result if result is not None else regs[0])
            m.reg_write(AR.UC_ARM_REG_PC, m.reg_read(AR.UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE, hook)
    for reg, value in zip((AR.UC_ARM_REG_R0, AR.UC_ARM_REG_R1, AR.UC_ARM_REG_R2), args):
        uc.reg_write(reg, value)
    keep = [uc.reg_read(r) for r in (AR.UC_ARM_REG_R4, AR.UC_ARM_REG_R5, AR.UC_ARM_REG_R6, AR.UC_ARM_REG_R7,
                                     AR.UC_ARM_REG_R8, AR.UC_ARM_REG_R9, AR.UC_ARM_REG_R10, AR.UC_ARM_REG_R11)]
    uc.emu_start(CRO + site, CRO + site + 4, count=20000)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == CRO + site + 4
    assert keep == [uc.reg_read(r) for r in (AR.UC_ARM_REG_R4, AR.UC_ARM_REG_R5, AR.UC_ARM_REG_R6, AR.UC_ARM_REG_R7,
                                             AR.UC_ARM_REG_R8, AR.UC_ARM_REG_R9, AR.UC_ARM_REG_R10,
                                             AR.UC_ARM_REG_R11)]
    assert uc.reg_read(AR.UC_ARM_REG_SP) == STACK
    return uc.reg_read(AR.UC_ARM_REG_R0), calls


CHOOSE_SITE, LOAD_SITE, START_SITE = sorted(brains.SITES)
C = brains.CODE


def choose(route, brain=0, streak=0, rank=0, retail=42):
    uc, AR, _ = machine(route, brain, streak, rank)
    stubs = {C['CODE_CHOOSER']: lambda m, r: retail, C['CODE_PICK']: lambda m, r: 77}
    return run(uc, AR, CHOOSE_SITE, (WORK, 0xFFFFFFFF), stubs)


@pytest.mark.parametrize('route', range(0, 9))
def test_choose_is_retail_without_a_brain_below_the_boss_streak(route):
    for streak in (0, 5, 18):
        result, calls = choose(route, streak=streak)
        assert result == 42 and calls == [(C['CODE_CHOOSER'], WORK, 0xFFFFFFFF, 0, 0) + calls[0][5:]]


@pytest.mark.parametrize('route', range(1, 8))
def test_choose_replaces_the_maison_boss_on_frontier_routes(route):
    for streak in (19, 20, 34, 200):
        result, calls = choose(route, streak=streak, retail=0x73)
        assert result == 77 and calls[1][:5] == (C['CODE_PICK'], WORK, 0xFFFFFFFF, 70, 40)
    assert choose(route, streak=19, rank=1, retail=0x73)[0] == 0x73      # rank Super: not a Frontier rank


def test_choose_keeps_the_maison_boss_on_route_0():
    assert choose(0, streak=19, retail=0x73)[0] == 0x73


def test_choose_gives_the_brain():
    tower = fp.ROUTE['tower']
    assert choose(tower, brain=tower + 8, streak=34)[0] == 131
    assert choose(tower, brain=tower + 16, streak=69)[0] == 132
    assert choose(tower, brain=3 + 8, streak=5)[0] == 42                  # another route's Brain
    assert choose(5, brain=5 + 8, streak=19)[0] == 137                      # a route without a Brain
    assert choose(3, brain=3 + 8, streak=20)[0] == 133                    # Spenser (Palace, route 3)
    assert choose(tower, brain=tower + 24, streak=5)[0] == 42             # invalid variant


@pytest.mark.parametrize('route, flag', [(0, 1), (1, 0), (2, 0), (7, 0), (8, 1)])
def test_load_clears_the_boss_flag_on_frontier_routes(route, flag):
    uc, AR, _ = machine(route)
    _, calls = run(uc, AR, LOAD_SITE, (WORK, 0, 131), {C['CODE_LOAD']: lambda m, r: None})
    assert [c[:4] for c in calls] == [(C['CODE_LOAD'], WORK, 0, 131)]
    assert uc.mem_read(WORK + 1, 1)[0] == flag


def start(route, brain, trainer, count=3, forced=None):
    uc, AR, put = machine(route, brain, trainer=trainer)
    put(PARTY + 0x18, count, '<B')
    if forced is not None:
        for work, value in zip(fp.DOME_FORCED, forced):
            put(SAVE + 0x13144 + 2 * (work - 0x4000), value, '<H')
    made = iter(TEMPS)
    sets = {}

    def load_set(m, r):
        m.mem_write(r[3], struct.pack('<H', r[2]) + bytes(14))
        sets[r[3]] = r[2]
    stubs = {C['CODE_START']: lambda m, r: 0x55, C['CODE_LOAD_SET']: load_set,
             C['CODE_MAKE_PARAM']: lambda m, r: next(made), C['CODE_EV_SET']: lambda m, r: None,
             C['CODE_GET_MAX_HP']: lambda m, r: 0x99, C['CODE_SET_HP']: lambda m, r: None,
             C['CODE_COPY']: lambda m, r: None}
    result, calls = run(uc, AR, START_SITE, (WORK, 1, 0), stubs)
    return result, calls


@pytest.mark.parametrize('route, brain, trainer, count', [
    *[(route, 0, 131, 3) for route in range(1, 8)],
    (0, 0, 0, 3), (2, 2 + 8, 5, 3), (3, 3 + 8, 131, 3), (4, 4 + 8, 133, 3), (2, 2 + 8, 131, 2), (5, 0, 0, 2)])
def test_start_leaves_the_party_alone_without_its_brain(route, brain, trainer, count):
    result, calls = start(route, brain, trainer, count)
    assert result == 0x55 and [c[:4] for c in calls] == [(C['CODE_START'], WORK, 1, 0)]


@pytest.mark.parametrize('facility', ['tower', 'palace'])
@pytest.mark.parametrize('variant', [brains.SILVER, brains.GOLD])
def test_start_remakes_the_brain_team_in_order(variant, facility):
    route = fp.ROUTE[facility]
    result, calls = start(route, route + 8 * variant, brains.trainer_id(facility, variant))
    assert result == 0x55 and calls[0][:4] == (C['CODE_START'], WORK, 1, 0)
    iv, team = brains.TEAMS[(facility, variant)]
    rest = calls[1:]
    per = len(rest) // 3
    assert per * 3 == len(rest)
    for k, temp in enumerate(TEMPS):
        part = rest[per * k:per * (k + 1)]
        assert part[0][:4] == (C['CODE_LOAD_SET'], HEAP, 0xB6, brains.set_index(facility, variant, k))
        make = part[1]
        assert make[0] == C['CODE_MAKE_PARAM'] and make[2:5] == (50, iv, HEAP) and make[5:7] == (0, 0xFF)
        evs = [c[2:4] for c in part if c[0] == C['CODE_EV_SET']]
        hp, atk, df, spe, spa, spd = team[k][3]
        assert evs == [(s, 0) for s in range(6)] + list(enumerate((hp, atk, df, spa, spd, spe)))
        assert all(c[1] == temp for c in part if c[0] == C['CODE_EV_SET'])
        assert len(part) == 2 + 12 + 4
        assert part[-4][:2] == (C['CODE_GET_MAX_HP'], temp + 0x800)
        assert part[-3][:3] == (C['CODE_SET_HP'], temp + 0x800, 0x99)
        assert part[-2][:3] == (C['CODE_COPY'], MEMBERS[k], temp)
        assert part[-1][:2] == ('free', temp)


def test_blob_fits_the_dllfield_padding():
    blob, symbols = brains.assemble()
    assert brains.AT >= brains.DEXNAV_END and brains.AT + len(blob) <= brains.FIELD_RODATA
    if not (fp.MOD_ROMFS / fp.FIELD_CRO).exists():
        pytest.skip('Local v0.5 build required')
    from cro import Cro
    original = (fp.MOD_ROMFS / fp.FIELD_CRO).read_bytes()
    cro = Cro(original)
    assert cro.segments[0][0] + cro.segments[0][1] == brains.FIELD_TEXT_END
    assert cro.segments[1][0] == brains.FIELD_RODATA
    assert not any(original[brains.AT:brains.FIELD_RODATA])
    assert any(original[0xF0400:brains.DEXNAV_END]) and not any(original[brains.DEXNAV_END:brains.AT])
    assert not any(brains.AT <= t < brains.FIELD_RODATA for t, _, _ in cro.relocs)
    for site, (_, thunk) in brains.SITES.items():
        assert original[site:site + 4] == brains.bl(site, thunk)


def test_code_bin_functions_are_the_measured_ones():
    if not fp.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    code = fp.REPOLISHED.read_bytes()
    for va, head in brains.CODE_HEADS.items():
        assert fp.word(code, va) == head, hex(va)
    assert set(brains.CODE.values()) <= set(brains.CODE_HEADS)
