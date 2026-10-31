#!/usr/bin/env python3
"""Execute the game's EXP/EV routine in Unicorn with synthetic battle fixtures.

This is not an emulator gameplay test: save data, personal data loading, affection,
trainer identity and evolution data are supplied by controlled stubs. Selection,
HP checks, the game's formula, modifiers, and EV assignment execute original ARM.
"""
import json
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)

from analyze_assets import CRO_BASE, main as make_analysis
from build_patch import patched_assets

ROOT = Path(__file__).resolve().parents[1]
HEAP, STACK, STOP = 0x02000000, 0x03010000, 0x03000000
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]


def emulator():
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x00100000, 0x00600000)
    uc.mem_map(CRO_BASE, 0x00200000)
    uc.mem_map(HEAP, 0x00100000)
    uc.mem_map(STOP, 0x00020000)
    image = (ROOT / 'analysis/repolished-battle.elf').read_bytes()
    for i in range(struct.unpack_from('<H', image, 44)[0]):
        _, offset, va, _, size, _, _, _ = struct.unpack_from('<8I', image, 52 + i * 32)
        uc.mem_write(va, image[offset:offset + size])
    return uc


def execute(patched, members, *, share_on=True, base_yield=70, enemy_level=10,
            trainer_battle=False, affection=0, ev_yields=(1, 0, 0, 0, 0, 0), apply_rewards=False):
    uc = emulator()
    if patched:
        # These are precisely the bytes emitted by the guarded patch generator.
        _, assets = patched_assets()
        spec = json.loads((ROOT / 'reports/held-exp-share-spec.json').read_text())
        for write in spec['patches'][0]['writes']:
            start, end = write['offset'], write['offset'] + len(bytes.fromhex(write['after']))
            uc.mem_write(CRO_BASE + start, assets['romfs/DllBattle.cro'][start:end])

    def write(address, fmt, *values):
        uc.mem_write(address, struct.pack(fmt, *values))

    context, party, defeated, output = HEAP, HEAP + 0x100, HEAP + 0x2000, HEAP + 0x3000
    engine, settings, trainer = HEAP + 0x4000, HEAP + 0x5000, HEAP + 0x6000
    write(context + 4, '<I', engine)
    write(engine + 0x10, '<I', settings)
    write(engine + 0x7C, '<I', trainer)
    write(settings, '<B', int(trainer_battle))
    write(settings + 0x8C, '<B', int(share_on))
    write(party + 0x18, '<B', len(members))
    by_pokemon = {}
    blocks_by_core = {}
    delivered_exp = {}
    participants = []
    for slot, member in enumerate(members):
        address = HEAP + 0x8000 + slot * 0x400
        pokemon = HEAP + 0xB000 + slot * 0x200
        by_pokemon[pokemon] = member
        core = HEAP + 0xC000 + slot * 0x200
        block_b = HEAP + 0xD000 + slot * 0x100
        header = HEAP + 0xE000 + slot * 0x100
        blocks_by_core[core] = block_b
        write(pokemon + 0xC, '<I', core)
        write(core + 8, '<I', header)
        write(block_b + 0x34, '<I', (1 << 30) if member.get('egg', False) else 0)
        write(header + 4, '<H', 4 if member.get('bad_egg', False) else 0)
        delivered_exp[address] = 0
        write(party + slot * 4, '<I', address)
        write(address, '<I', pokemon)
        write(address + 0xC, '<H', 1)  # Species, irrelevant to the stub personal table.
        write(address + 0x10, '<H', member.get('hp', 20))
        write(address + 0x12, '<H', member.get('item', 0))
        write(address + 0x18, '<B', member.get('level', 10))
        write(address + 0x19, '<B', slot)
        write(address + 0x114, '<B', int(member.get('pokerus', False)))
        ev = member.get('ev', [0] * 6)
        write(address + 0x10C, '<H', sum(ev))
        uc.mem_write(address + 0x10E, bytes(ev))
        if member.get('participant', False):
            participants.append(slot)
    write(defeated + 0xC, '<H', 1)
    write(defeated + 0x18, '<B', enemy_level)
    write(defeated + 0xDA, '<B', len(participants))
    uc.mem_write(defeated + 0xDB, bytes(participants))
    write(STACK, '<I', output)
    for reg, value in zip(REGS, [0, context, party, defeated]):
        uc.reg_write(reg, value)
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.reg_write(UC_ARM_REG_LR, STOP)

    def return_value(value):
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    stub_calls = {}
    messages = []

    def hook(uc, address, size, unused):
        r0, r1 = uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)
        if address == 0x14EB30:  # Load defeated species/form's personal data.
            value = 0
        elif address == 0x14EB08:  # Read personal-data field.
            if r0 == 9:
                value = base_yield
            elif 10 <= r0 <= 15:
                value = ev_yields[r0 - 10]
            else:
                raise AssertionError(f'Unexpected personal field {r0}')
        elif address == 0x4EA710:  # Original trainer identity check.
            value = 0 if by_pokemon[r1].get('traded', False) else 1
        elif address in (0x4D2480, 0x4EA894):  # Equal languages: domestic trade bonus.
            value = 1
        elif address in (0x3B0E7C, 0x3B1004):  # No available level-up evolution in this fixture.
            value = 0
        elif address == CRO_BASE + 0x77A2C:  # Controlled affection.
            value = affection
        elif address == 0x453138:  # Power-item EV increment, when present.
            value = 4
        elif apply_rewards and address in (0x168EC0, 0x168E50):
            value = 0  # Fixture block is already decrypted; the actual eligibility getters execute.
        elif apply_rewards and address == 0x16BD00:
            value = blocks_by_core[r0]
        elif apply_rewards and address in (CRO_BASE + 0x71BD8, CRO_BASE + 0x70F8C, CRO_BASE + 0x6D560):
            if address == CRO_BASE + 0x70F8C:  # Per-Pokemon EXP message 0x2B/0x2C.
                messages.append(('individual', uc.reg_read(UC_ARM_REG_R2), uc.reg_read(UC_ARM_REG_R3)))
            elif address == CRO_BASE + 0x6D560:  # Team summary message 0x2D.
                messages.append(('summary', r1, None))
            value = 0  # UI/event queue: no side effects in these fixtures.
        elif apply_rewards and address == CRO_BASE + 0x78834:
            # Boundary of EXP application: record dispatch, do not simulate a save or level-up.
            delivered_exp[r0] += struct.unpack('<I', uc.mem_read(r1, 4))[0]
            write(r1, '<I', 0)
            value = 0
        else:
            return
        stub_calls[f'{address:08x}'] = stub_calls.get(f'{address:08x}', 0) + 1
        return_value(value)

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(CRO_BASE + 0x324D0, STOP, count=100000)
    if uc.reg_read(UC_ARM_REG_PC) != STOP or uc.reg_read(UC_ARM_REG_SP) != STACK:
        raise AssertionError('ARM routine did not return with a balanced stack')
    if apply_rewards:
        # Callers (DllBattle+0x2573C, +0x6BEC8) clear the group-message flag
        # +0x12 when the share flag +0x11 is zero.
        for i in range(len(members)):
            if uc.mem_read(output + i * 20 + 0x11, 1)[0] == 0:
                write(output + i * 20 + 0x12, '<B', 0)
        write(settings + 0x4B, '<B', 1)  # Suppress unrelated trainer-statistics accounting.
        for reg, value in zip(REGS, [context, party, output, 0]):
            uc.reg_write(reg, value)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.emu_start(CRO_BASE + 0x6A39C, STOP, count=100000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        assert uc.reg_read(UC_ARM_REG_SP) == STACK
    result = []
    for i in range(len(members)):
        row = bytes(uc.mem_read(output + i * 20, 20))
        result.append({'exp': struct.unpack_from('<I', row)[0],
                       'ev': list(struct.unpack_from('<6H', row, 4)), 'shared': row[17]})
        if apply_rewards:
            address = HEAP + 0x8000 + i * 0x400
            result[-1]['dispatched_exp'] = delivered_exp[address]
            result[-1]['battle_ev'] = list(uc.mem_read(address + 0x10E, 6))
            result[-1]['battle_ev_total'] = struct.unpack('<H', uc.mem_read(address + 0x10C, 2))[0]
    if apply_rewards:
        stub_calls['messages'] = messages
    return result, stub_calls


def item_fields(record):
    """Execute the real item getter and item-ID permission check."""
    uc = emulator()
    uc.mem_write(HEAP, record)
    values = {}
    for field in (9, 10, 11, 13):
        uc.reg_write(UC_ARM_REG_R0, HEAP)
        uc.reg_write(UC_ARM_REG_R1, field)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.emu_start(0x4D3A88, STOP, count=1000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        values[str(field)] = uc.reg_read(UC_ARM_REG_R0)
    uc.reg_write(UC_ARM_REG_R0, 216)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(0x3B6F30, STOP, count=1000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    values['item_id_permitted'] = uc.reg_read(UC_ARM_REG_R0)
    return values


def main():
    make_analysis()
    active = {'participant': True}
    holder = {'item': 216}
    cases = [
        ('reserve_holder', [active, holder, {}], {}, [100, 50, 0]),
        ('participating_holder', [{'participant': True, 'item': 216}, {}, {}], {}, [100, 0, 0]),
        ('fainted_holder', [active, {'item': 216, 'hp': 0}, {}], {}, [100, 0, 0]),
        ('no_holder', [active, {}, {}], {}, [100, 0, 0]),
        ('global_switch_off', [active, holder, {}], {'share_on': False}, [100, 50, 0]),
        ('two_participants', [active, {'participant': True, 'item': 216}, {}], {}, [100, 100, 0]),
        ('last_party_slot', [active, {}, {}, {}, {}, holder], {}, [100, 0, 0, 0, 0, 50]),
        ('odd_amount', [active, holder, {}], {'base_yield': 63, 'enemy_level': 7}, [63, 31, 0]),
        ('minimum_one', [active, holder, {}], {'base_yield': 7, 'enemy_level': 1}, [1, 1, 0]),
        ('trainer_battle', [active, holder, {}], {'trainer_battle': True}, [150, 75, 0]),
        ('traded_holder', [active, {'item': 216, 'traded': True}, {}], {}, [100, 75, 0]),
        ('lucky_egg_participant', [{'participant': True, 'item': 231}, holder, {}], {}, [150, 50, 0]),
        ('affection_bonus', [active, holder, {}], {'affection': 50}, [120, 60, 0]),
        ('pokerus_holder', [active, {'item': 216, 'pokerus': True}, {}], {}, [100, 50, 0]),
        ('two_holders', [active, holder, holder], {}, [100, 50, 50]),
        ('all_fainted', [{'participant': True, 'hp': 0}, {'item': 216, 'hp': 0}], {}, [0, 0]),
        ('empty_party', [], {}, []),
    ]
    report = {'method': 'Unicorn 2.1.4 executing original/patched ARM with external fixtures',
              'limitations': 'Not a full game run: external data and crypto helpers are fixtures. Original egg getters, reward dispatch and EV caps execute as ARM; EXP application is recorded by a stub. No save writes, menus, CRO loading or battle-party construction tested here.',
              'cases': []}
    originals, changed = patched_assets()
    original_item = item_fields(originals['romfs/a/1/9/7'][0x5B40:0x5B64])
    patched_item = item_fields(changed['romfs/a/1/9/7'][0x5B40:0x5B64])
    assert original_item == {'9': 1, '10': 1, '11': 4, '13': 5, 'item_id_permitted': 1}
    assert patched_item == {'9': 0, '10': 0, '11': 0, '13': 0, 'item_id_permitted': 1}
    report['item_fields'] = {'original': original_item, 'patched': patched_item, 'passed': True}
    print('PASS item field getters and item-ID permission')
    for name, members, options, expected in cases:
        original, _ = execute(False, members, **options)
        result, stubs = execute(True, members, **options)
        assert [r['exp'] for r in result] == expected, (name, result, expected)
        for member, before, after in zip(members, original, result):
            if member.get('participant', False):
                assert before == after, (name, 'participant changed', before, after)
            if after['exp'] == 0:
                assert after['ev'] == [0] * 6 and after['shared'] == 0, (name, after)
            else:
                assert after['ev'] == [2 if member.get('pokerus') else 1, 0, 0, 0, 0, 0], (name, after)
                assert after['shared'] == 0, (name, after)  # holder gets an individual message
        report['cases'].append({'name': name, 'original': original, 'patched': result,
                                 'stub_calls': stubs, 'passed': True})
        print(f'PASS {name}: {expected}')
    report['application_cases'] = []
    application_cases = [
        ('application_normal', [active, holder, {}], {}, [100, 50, 0], [[1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], [0] * 6]),
        ('application_level_100', [active, {'item': 216, 'level': 100}, {}], {}, [100, 0, 0], [[1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], [0] * 6]),
        ('application_egg', [active, {'item': 216, 'egg': True}, {}], {}, [100, 0, 0], [[1, 0, 0, 0, 0, 0], [0] * 6, [0] * 6]),
        ('application_bad_egg', [active, {'item': 216, 'bad_egg': True}, {}], {}, [100, 0, 0], [[1, 0, 0, 0, 0, 0], [0] * 6, [0] * 6]),
        ('application_stat_cap', [active, {'item': 216, 'ev': [252, 0, 0, 0, 0, 0]}], {}, [100, 50], [[1, 0, 0, 0, 0, 0], [252, 0, 0, 0, 0, 0]]),
        ('application_total_cap', [active, {'item': 216, 'ev': [251, 252, 7, 0, 0, 0]}], {}, [100, 50], [[1, 0, 0, 0, 0, 0], [251, 252, 7, 0, 0, 0]]),
        ('application_partial_total', [active, {'item': 216, 'ev': [250, 252, 7, 0, 0, 0], 'pokerus': True}], {}, [100, 50], [[1, 0, 0, 0, 0, 0], [251, 252, 7, 0, 0, 0]]),
    ]
    for name, members, options, expected_exp, expected_ev in application_cases:
        result, stubs = execute(True, members, apply_rewards=True, **options)
        assert [row['dispatched_exp'] for row in result] == expected_exp, (name, result)
        assert [row['battle_ev'] for row in result] == expected_ev, (name, result)
        assert all(row['battle_ev_total'] == sum(row['battle_ev']) for row in result)
        shown = [(kind, slot) for kind, _, slot in stubs['messages']]
        expected_messages = [('individual', slot) for slot, exp in enumerate(expected_exp) if exp]
        assert shown == expected_messages, (name, stubs['messages'])
        assert all(message in (0x2B, 0x2C) for _, message, _ in stubs['messages'])
        report['application_cases'].append({'name': name, 'patched': result, 'stub_calls': stubs, 'passed': True})
        print(f'PASS {name}: dispatched EXP {expected_exp}, messages {shown}')
    (ROOT / 'reports/arm-validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
