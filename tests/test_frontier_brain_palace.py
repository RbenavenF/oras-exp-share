"""Spenser, the Battle Palace's Frontier Brain (F8-CEREBRO-PALACIO; reports/diseno/cerebros.md): his fixed teams,
the Palace zone script's Brain routines (frontier/brains.py) run in scripts/pawn_vm.py over whole challenges (silver,
gold, rematches, losses) and its reception's «Symbols» consult. Checks the generated logic, not the game (Azahar:
reports/frontier.md §42)."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import brains  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
from pawn import OP, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

ROUTE = fp.ROUTE['palace']
SHIFT = 2 * (ROUTE - 1)


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def palace():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    import palace as pal
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = pal.palace_program(retail)
    return program.build_script(f'L{retail.main:x}'), program.layout()


class Game:
    """The works the Brain routines touch, the BP they give and the lines they say."""

    def __init__(self, script, labels, symbols=0):
        self.script, self.labels = script, labels
        self.works = {fp.WORK_ROUTE: ROUTE, brains.WORK_SYMBOLS: symbols, brains.WORK_BRAIN: 0}
        self.bp, self.said = 0, []

    def run(self, label, streak=0):
        works = self.works
        stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                         'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                         'GetMyWinCount': lambda vm, a: streak,
                         'GlobalCall': lambda vm, a: self.said.append(works.get(brains.WORK_MSG))})

        def bp(vm, a):
            self.bp += a[0]
            return 0
        return VM(self.script, stubs, {self.labels['L30']: bp}).run(self.labels[label])

    @property
    def symbols(self):
        return self.works[brains.WORK_SYMBOLS] >> SHIFT & 3

    def battle(self, streak, win=True):
        """One battle at `streak` wins: the Brain chosen before it (0 = an ordinary trainer), then the result."""
        self.run('brains_check', streak)
        brain = self.works[brains.WORK_BRAIN]
        if brain:
            assert self.run('brains_intro') == 1
        self.run('brains_won' if win else 'brains_lost')
        assert self.works[brains.WORK_BRAIN] == 0
        return brain >> 3 if brain else 0


def test_first_challenge_silver_then_gold_then_rematches(palace):
    game = Game(*palace, symbols=0x1001)              # other routes' symbols untouched throughout
    met = {}
    for streak in range(0, 105):
        variant = game.battle(streak)
        if variant:
            met[streak + 1] = (variant, game.symbols, game.bp)
    assert met == {21: (brains.SILVER, 1, 10), 42: (brains.GOLD, 3, 20), 63: (brains.GOLD, 3, 30),
                   84: (brains.GOLD, 3, 40), 105: (brains.GOLD, 3, 50)}
    assert game.works[brains.WORK_SYMBOLS] == 0x1001 | 3 << SHIFT
    base = 4 * (ROUTE - 1)
    assert game.said == [base, base + 2, base + 1, base + 3, base + 1, base + 3, base + 1, base + 3, base + 1, base + 3]


def test_lost_to_gold_keeps_silver_and_a_new_streak_skips_silver(palace):
    game = Game(*palace)
    for streak in range(0, 41):
        game.battle(streak)
    assert game.symbols == 1 and game.bp == 10
    assert game.battle(41, win=False) == brains.GOLD
    assert game.symbols == 1 and game.bp == 10 and game.said[-1] == brains.MORE + 4 * (ROUTE - 1)
    met = [streak + 1 for streak in range(0, 42) if game.battle(streak)]   # a new challenge from 0
    assert met == [42] and game.symbols == 3 and game.bp == 20


def test_lost_to_silver_gives_nothing_and_silver_comes_back(palace):
    game = Game(*palace)
    for streak in range(0, 20):
        game.battle(streak)
    assert game.battle(20, win=False) == brains.SILVER and game.symbols == 0 and game.bp == 0
    assert game.said[-1] == brains.MORE + 4 * (ROUTE - 1)
    assert game.battle(20) == brains.SILVER and game.symbols == 1 and game.bp == 10


def test_both_symbols_silver_rematch_keeps_gold(palace):
    game = Game(*palace, symbols=3 << SHIFT)
    assert game.battle(20) == brains.SILVER
    assert game.symbols == 3 and game.bp == 10 and game.said[-1] == 4 * (ROUTE - 1) + 2


def test_a_paused_challenge_keeps_the_brain_due(palace):
    """The check is made again before each battle (also after loading a paused save): same Brain, no prize."""
    game = Game(*palace, symbols=1 << SHIFT)
    for _ in range(3):
        game.run('brains_check', 41)
        assert game.works[brains.WORK_BRAIN] == ROUTE + 8 * brains.GOLD
    assert game.bp == 0 and game.symbols == 1


def test_other_routes_never_get_spenser(palace):
    for route in (0, 1, 2, 4, 5, 6, 7):
        game = Game(*palace)
        game.works[fp.WORK_ROUTE] = route
        for streak in (20, 41, 62):
            game.run('brains_check', streak)
            brain = game.works[brains.WORK_BRAIN]
            assert brain == 0 or (brain & 7 == route != ROUTE)     # Noland (route 1) or Anabel (route 2)
        assert game.symbols == 0


@pytest.mark.parametrize('word, k', [(0, 1), (1 << SHIFT, 2), (3 << SHIFT, 3), (2 << SHIFT, 3), (0x3FCF, 1),
                                     (0x3FDF, 2), (0x5555 ^ 1 << SHIFT | 3 << SHIFT, 3)])
def test_symbols_consult(palace, word, k):
    game = Game(*palace, symbols=word)
    game.run('brains_symbols')
    assert game.said == [brains.MORE + 4 * (ROUTE - 1) + k] and game.works[brains.WORK_SYMBOLS] == word


def test_symbols_menu_entry(palace):
    import tower as t
    script, labels = palace
    ins = decode(script.code)
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    add = s32(gf_hash('ListMenuAdd'))
    entries = [(ins[j - 1].args[0], ins[j - 2].args[0]) for j, x in enumerate(ins)
               if x.op == OP['SYSREQ_N'] and names[x.args[0]] == add and labels['L14f4'] < x.address
               < labels[factory.RECEPTION_RESULT]]
    assert entries == [(53, 0), (54, 1), (74, 2), (factory.LINE_SYMBOLS, brains.MENU_SYMBOLS), (55, 3)]
    assert t.RECEPTION_MENU == [53, 54, 74, 55]
    k = next(j for j, x in enumerate(ins) if x.address == labels[factory.RECEPTION_RESULT])
    assert ins[k + 1].args == [brains.MENU_SYMBOLS]
    assert ins[k + 4].op == OP['CALL'] and ins[k + 4].address + ins[k + 4].args[0] == labels['brains_symbols']
    assert ins[k + 5].op == OP['CONST_S'] and ins[k + 5].args == [factory.RECEPTION_AGAIN, 1]
    assert ins[k + 6].op == OP['JUMP'] and ins[k + 6].address + ins[k + 6].args[0] == labels[factory.RECEPTION_NEXT]
    # then the Tower's own «Combatir» dispatch (value 0) shared by the Palace, as before
    rest = ins[k + 7:k + 11]
    assert [x.op for x in rest[:2]] == [OP['LOAD_P_S_PRI'], OP['JNZ']] and rest[0].args == [-12]
    assert rest[3].op == OP['CALL'] and rest[3].address + rest[3].args[0] == labels['palace_reception']


def test_texts_cover_every_moment():
    for lang in ('es', 'en'):
        code = next(c for c, name in factory.LANG.items() if name == lang)
        lines = brains.lines(code)
        base, more = 4 * (ROUTE - 1), brains.MORE + 4 * (ROUTE - 1)
        intro_s, intro_g, won_s, won_g = lines[base:base + 4]
        lost, none, silver, gold = lines[more:more + 4]
        assert 'Spenser' in intro_s and 'Spenser' in intro_g and 'Spenser' not in won_s
        assert ('Palacio' if lang == 'es' else 'Palace') in intro_s and ('Palacio' if lang == 'es' else 'Palace') in lost
        assert all(len(line.split('\n')) <= 3 for line in lines[base:base + 4] + lines[more:more + 4])
        sym = brains.SYMBOL[lang]['palace']
        assert all(sym in x for x in (won_s, won_g, none, silver, gold))
        assert '10' in won_s and '10' in won_g
    assert fd.BRAIN_BONUS == 10


def test_spenser_sets_are_the_annex():
    """cerebros.md §7 (pokeemerald 731ad5bf sFrontierBrainsMons, BATTLE_PALACE), ORAS ids checked against the Spanish
    game text by test_frontier_brains.test_ids_match_the_game_text."""
    import struct
    sets = brains.sets()
    want = {brains.SILVER: (16, [(169, 213, 3, (109, 104, 92, 19)), (289, 232, 0, (89, 207, 247, 280)),
                                 (131, 217, 17, (58, 32, 109, 182))]),
            brains.GOLD: (31, [(59, 214, 11, (315, 245, 46, 182)), (289, 232, 0, (63, 89, 247, 281)),
                               (245, 221, 11, (59, 57, 44, 347))])}
    evs = {brains.SILVER: [(152, 0, 0, 152, 100, 106), (152, 152, 0, 106, 100, 0), (0, 0, 252, 0, 106, 152)],
           brains.GOLD: [(6, 252, 252, 0, 0, 0), (6, 252, 0, 252, 0, 0), (252, 0, 252, 6, 0, 0)]}
    rows = brains.brain_rows()
    for variant, (iv, team) in want.items():
        assert brains.TEAMS[('palace', variant)][0] == iv
        parsed = [fd.parse_set(sets[brains.set_index('palace', variant, k)]) for k in range(3)]
        assert [(s['species'], s['item'], s['nature'], s['moves']) for s in parsed] == team
        assert [s['evs'] for s in parsed] == [sum(1 << j for j, e in enumerate(ev) if e) for ev in evs[variant]]
        trainer = brains.trainer_id('palace', variant)
        assert trainer == 133 + variant - 1
        assert fd.parse_trainer(brains.trainers()[trainer]) == {
            'class': 31, 'sets': tuple(brains.set_index('palace', variant, k) for k in range(3))}
        at = brains.ENTRY * (2 * (ROUTE - 1) + variant - 1)
        assert struct.unpack_from('<HBB', rows, at) == (trainer, iv, 0)
        for k, (hp, atk, df, spe, spa, spd) in enumerate(evs[variant]):
            assert struct.unpack_from('<H6B', rows, at + 4 + 8 * k) == (
                brains.set_index('palace', variant, k), hp, atk, df, spa, spd, spe)    # pml order
    assert [brains.set_index('palace', v, k) for v in (1, 2) for k in range(3)] == list(range(235, 241))
    assert brains.trainer_names()[133 - 129:135 - 129] == ['Spenser', 'Spenser']


def test_spenser_is_enabled_on_the_palace_route():
    import palace as pal
    assert brains.route_of('palace') == pal.ROUTE == 3 and brains.APPEARANCES['palace'] == (21, 42, 21)
    assert 'palace' in brains.ENABLED and brains.CLASSES['palace'] == 31
