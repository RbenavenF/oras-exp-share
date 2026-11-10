#!/usr/bin/env python3
"""Lab only: the clock seconds that make pike_room give a wanted room through the left door (door 0, what A picks).

Runs the built shared script 5 in the pawn VM with the room's inputs as the game has them (streak, generator work,
HP/status works, selected Pokémon traits) and tries seconds from --start on. Prints JSON {seconds, kind, log}.
want: wild | immune | single | status | npc | healfull | healpart | hard.
Usage (after source scripts/env.sh):
  python frontier/probes/pike/seconds.py --streak 15 --rng 45892 --hp 137 184 156 --st 0 0 0 \
      --traits 8,13,29 9,1,66 15,4,24 --want immune
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import dome  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch  # noqa: E402
import pike  # noqa: E402
import pyramid  # noqa: E402
from formats import garc_entries  # noqa: E402
from pawn import Script, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

KINDS = {pike.LINE_SINGLE: 'single', pike.LINE_HARD: 'hard', pike.LINE_NPC: 'npc', pike.LINE_HEAL_FULL: 'healfull',
         pike.LINE_STATUS_INTRO: 'status', pike.LINE_WILD: 'wild'}


def shared():
    sets, table, levels, cells = overlay.rentals()
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    data = (overlay.ROMFS / overlay.SHARED).read_bytes()
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    script5 = Script.parse(data[offset:offset + length])
    program = factory.shared_program(script5, retail, cells, levels,
                                     dome.shared_cases(levels) + pike.shared_cases() + pyramid.shared_cases())
    labels = program.layout()
    return program.build_script(f'L{script5.main:x}'), labels


def run(script, labels, streak, rng, hp, st, traits, seconds):
    works = {pike.STREAK: streak, pike.WORK_RNG: rng}
    for k in range(3):
        works[patch.PIKE_HP[k]], works[patch.PIKE_ST[k]] = hp[k], st[k]
    log = []
    natives = {s32(gf_hash(n)): f for n, f in {
        'PokePartyGetParam': lambda vm, a: traits[a[0] - pike.SELECTED_SLOT][{6: 0, 7: 1, 22: 2}[a[1]]],
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        '_GetRealTimeToSecond': lambda vm, a: seconds,
        'ListMenuAdd': lambda vm, a: 0,
        'WordSetNumber': lambda vm, a: 0,
        'GlobalSetParentParam': lambda vm, a: log.append(('result', a[1])),
    }.items()}
    h = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {h['msg']: lambda vm, a: log.append(('msg', a[0])) or 0, h['msg_wait']: lambda vm, a: 0,
             h['msg_close']: lambda vm, a: 0, h['menu_init']: lambda vm, a: 0, h['menu_run']: lambda vm, a: 0}
    VM(script, natives, calls).run(labels['pike_room'])
    msgs = [m for t, m in log if t == 'msg']
    kind = next((KINDS[m] for m in msgs if m in KINDS), 'healpart' if any(
        pike.LINE_HEALED <= m < pike.LINE_HEALED + 3 for m in msgs) else 'last')
    if kind == 'status' and pike.LINE_IMMUNE in msgs:
        kind = 'immune'
    return kind, msgs, works


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--streak', type=int, required=True)
    parser.add_argument('--rng', type=int, required=True)
    parser.add_argument('--hp', type=int, nargs=3, required=True)
    parser.add_argument('--st', type=int, nargs=3, required=True)
    parser.add_argument('--traits', nargs=3, required=True, help='type0,type1,ability per position')
    parser.add_argument('--want', required=True)
    parser.add_argument('--start', type=int, default=100000)
    args = parser.parse_args()
    traits = [tuple(int(x) for x in t.split(',')) for t in args.traits]
    script, labels = shared()
    for seconds in range(args.start, args.start + 3000):
        kind, msgs, works = run(script, labels, args.streak, args.rng, args.hp, args.st, traits, seconds)
        if kind == args.want:
            print(json.dumps(dict(seconds=seconds, kind=kind, msgs=msgs, wild=works.get(patch.PIKE_WILD),
                                  st=[works[w] for w in patch.PIKE_ST], rng=works[pike.WORK_RNG])))
            return
    sys.exit(f'no seconds in {args.start}..+3000 give {args.want}')


if __name__ == '__main__':
    main()
