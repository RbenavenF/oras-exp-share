"""Anabel, the Battle Tower's Frontier Brain (F8-CEREBRO-TORRE; reports/diseno/cerebros.md): the Tower zone script's
Brain routines (frontier/brains.py) run in scripts/pawn_vm.py over whole challenges (silver, gold, rematches,
losses) and its reception's «Symbols» consult. Checks the generated logic, not the game (Azahar: reports/frontier.md
§39 for BASE's silver/gold-loss, §41 for this task)."""
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

ROUTE = fp.ROUTE['tower']
SHIFT = 2 * (ROUTE - 1)


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def tower():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    import tower as t
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = t.tower_program(retail)
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


def test_first_challenge_silver_then_gold_then_rematches(tower):
    game = Game(*tower, symbols=0x1001)              # other routes' symbols untouched throughout
    met = {}
    for streak in range(0, 174):
        variant = game.battle(streak)
        if variant:
            met[streak + 1] = (variant, game.symbols, game.bp)
    assert met == {35: (brains.SILVER, 1, 10), 70: (brains.GOLD, 3, 20), 105: (brains.GOLD, 3, 30),
                   140: (brains.GOLD, 3, 40)}
    assert game.works[brains.WORK_SYMBOLS] == 0x1001 | 3 << SHIFT
    base = 4 * (ROUTE - 1)
    assert game.said == [base, base + 2, base + 1, base + 3, base + 1, base + 3, base + 1, base + 3]


def test_lost_to_gold_keeps_silver_and_a_new_streak_skips_silver(tower):
    game = Game(*tower)
    for streak in range(0, 69):
        game.battle(streak)
    assert game.symbols == 1 and game.bp == 10
    assert game.battle(69, win=False) == brains.GOLD
    assert game.symbols == 1 and game.bp == 10 and game.said[-1] == brains.MORE + 4 * (ROUTE - 1)
    met = [streak + 1 for streak in range(0, 70) if game.battle(streak)]   # a new challenge from 0
    assert met == [70] and game.symbols == 3 and game.bp == 20


def test_lost_to_silver_gives_nothing_and_silver_comes_back(tower):
    game = Game(*tower)
    for streak in range(0, 34):
        game.battle(streak)
    assert game.battle(34, win=False) == brains.SILVER and game.symbols == 0 and game.bp == 0
    assert game.battle(34) == brains.SILVER and game.symbols == 1 and game.bp == 10


def test_both_symbols_silver_rematch_keeps_gold(tower):
    game = Game(*tower, symbols=3 << SHIFT)
    assert game.battle(34) == brains.SILVER
    assert game.symbols == 3 and game.bp == 10 and game.said[-1] == 4 * (ROUTE - 1) + 2


def test_a_paused_challenge_keeps_the_brain_due(tower):
    """The check is made again before each battle (also after loading a paused save): same Brain, no prize."""
    game = Game(*tower, symbols=1 << SHIFT)
    for _ in range(3):
        game.run('brains_check', 69)
        assert game.works[brains.WORK_BRAIN] == ROUTE + 8 * brains.GOLD
    assert game.bp == 0 and game.symbols == 1


def test_other_routes_never_get_anabel(tower):
    for route in (0, 1, 3, 4, 5, 6, 7):
        game = Game(*tower)
        game.works[fp.WORK_ROUTE] = route
        for streak in (34, 69, 104):
            game.run('brains_check', streak)
            brain = game.works[brains.WORK_BRAIN]
            assert brain == 0 or (brain & 7 == route != ROUTE)     # the Factory's Noland on route 1
        assert game.symbols == 0


@pytest.mark.parametrize('word, k', [(0, 1), (1 << SHIFT, 2), (3 << SHIFT, 3), (2 << SHIFT, 3), (0x3FF3, 1),
                                     (0x3FF7, 2), (0x5555 ^ 1 << SHIFT | 3 << SHIFT, 3)])
def test_symbols_consult(tower, word, k):
    game = Game(*tower, symbols=word)
    game.run('brains_symbols')
    assert game.said == [brains.MORE + 4 * (ROUTE - 1) + k] and game.works[brains.WORK_SYMBOLS] == word


def test_symbols_menu_entry(tower):
    import tower as t
    script, labels = tower
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
    # then the Tower's own «Combatir» dispatch (value 0), as before
    rest = ins[k + 7:k + 11]
    assert [x.op for x in rest[:2]] == [OP['LOAD_P_S_PRI'], OP['JNZ']] and rest[0].args == [-12]
    assert rest[3].op == OP['CALL'] and rest[3].address + rest[3].args[0] == labels['tower_reception']


def test_texts_cover_every_moment():
    for lang in ('es', 'en'):
        code = next(c for c, name in factory.LANG.items() if name == lang)
        lines = brains.lines(code)
        base, more = 4 * (ROUTE - 1), brains.MORE + 4 * (ROUTE - 1)
        intro_s, intro_g, won_s, won_g = lines[base:base + 4]
        lost, none, silver, gold = lines[more:more + 4]
        assert 'Anabel' in intro_s and 'Anabel' in intro_g and 'Anabel' not in won_s
        assert all(len(line.split('\n')) <= 3 for line in lines[base:base + 4] + lines[more:more + 4])
        sym = brains.SYMBOL[lang]['tower']
        assert all(sym in x for x in (won_s, won_g, none, silver, gold))
        assert '10' in won_s and '10' in won_g
    assert fd.BRAIN_BONUS == 10
