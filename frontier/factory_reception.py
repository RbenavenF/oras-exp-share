"""Factory Singles registration in shared script 5; no real-party selector.

Case 9779 is reserved in REPARTO. The zone retains all Maison-only natives and
calls this preflight before CHALLENGE. Its menus use shared text 637.
"""
import factory
import factory_open as fo
import modes
import patch

GLOBAL_PREPARE = 9779
LINE_BASE = 1178
TEXT = {
    'es': ('Nivel 50', 'Nivel Libre',
           'Elige el nivel de los alquileres.\nNivel Libre: tú y tu rival al nivel 100.',
           'Reanudar', 'Abandonar', 'Cancelar',
           'Hay un desafío en pausa.\n¿Quieres reanudarlo o abandonarlo?',
           'La modalidad guardada no es compatible.\nEl desafío se ha conservado.'),
    'en': ('Level 50', 'Open Level',
           'Choose the rental level.\nOpen Level: your rentals and opponent at level 100.',
           'Resume', 'Retire', 'Cancel',
           'A challenge is paused.\nResume or retire?',
           'The saved format is not supported.\nYour challenge has been kept.'),
}


def shared_routine(p, helpers):
    r = factory.Routine(p, 'factory_prepare', ['x', 'config', 'count', 'old_streak'])
    done, paused, invalid, cancel, restore = (f'factory_prepare_{x}' for x in
                                             ('done', 'paused', 'invalid', 'cancel', 'restore'))

    def menu(prompt, entries):
        r.call(helpers['msg'], LINE_BASE + prompt, 1, 0, 256, 0)
        r.call(helpers['msg_wait'])
        r.call(helpers['menu_init'], 180, 112, 0, 1, 0, 0)
        for line, value in entries:
            r.sysreq('ListMenuAdd', LINE_BASE + line, value, 0)
        r.call(helpers['menu_run'])
        r.store('x')
        r.call(helpers['msg_close'], 0)
        r.load('x')

    r.sysreq('WorkGet', modes.CONFIG[1])
    r.store('config')
    r.sysreq('WorkGet', patch.WORK_IV)
    r.op('JNZ', paused)
    menu(2, ((0, 0), (1, 1), (5, 2)))
    r.const_alt(0)
    r.op('JSLESS', cancel)
    r.const_alt(1)
    r.op('JSGRTR', cancel)
    r.load('x')
    r.op('SMUL_P_C', 0x164)
    r.store('x')
    r.sysreq('WorkSet', modes.CONFIG[1], 'x')
    # Temporarily clear the new mode's counter for an unpromoted first draft.
    # Roll it and CONFIG back if any of the three draft menus is cancelled.
    for mode, config in ((0, 0), (1, 0x164)):
        skip = r.new_label(f'prepare_mode{mode}')
        r.load('x')
        r.op('EQ_P_C_PRI', config)
        r.op('JZER', skip)
        r.sysreq('WorkGet', modes.FACTORY_RENTS[mode])
        r.store('count')
        r.sysreq('WorkSet', modes.FACTORY_RENTS[mode], 0)
        r.p.label(skip)
    r.sysreq('WorkGet', factory.WORK_STREAK)
    r.store('old_streak')
    r.sysreq('WorkSet', factory.WORK_STREAK, 0)
    r.call('factory_draft')
    r.op('JZER', restore)
    for mode, config in ((0, 0), (1, 0x164)):
        skip = r.new_label(f'prepare_bank{mode}')
        r.load('x')
        r.op('EQ_P_C_PRI', config)
        r.op('JZER', skip)
        r.sysreq('WorkSet', modes.bank(1, mode)[0], 0)
        r.p.label(skip)
    r.op('JUMP', done)
    r.p.label(restore)
    for mode, config in ((0, 0), (1, 0x164)):
        skip = r.new_label(f'prepare_restore{mode}')
        r.load('x')
        r.op('EQ_P_C_PRI', config)
        r.op('JZER', skip)
        r.sysreq('WorkSet', modes.FACTORY_RENTS[mode], 'count')
        r.p.label(skip)
    r.sysreq('WorkSet', modes.CONFIG[1], 'config')
    r.sysreq('WorkSet', factory.WORK_STREAK, 'old_streak')
    r.op('JUMP', cancel)
    r.p.label(paused)
    valid = r.new_label('prepare_config_valid')
    for config in (0, 50, 0x164):
        r.load('config')
        r.op('EQ_P_C_PRI', config)
        r.op('JNZ', valid)
    r.op('JUMP', invalid)
    r.p.label(valid)
    menu(6, ((3, 0), (4, 1), (5, 2)))
    r.op('JZER', done)
    r.op('EQ_P_C_PRI', 1)
    r.op('JZER', cancel)
    # An explicit retirement clears only the active bank, never its record.
    for mode in (0, 1):
        skip = r.new_label(f'prepare_retire{mode}')
        r.load('config')
        r.op('EQ_P_C_PRI', 0x164)
        r.op('JZER' if mode else 'JNZ', skip)
        r.sysreq('WorkSet', modes.bank(1, mode)[0], 0)
        r.sysreq('WorkSet', modes.FACTORY_RENTS[mode], 0)
        r.p.label(skip)
    for work in (patch.WORK_IV, fo.WORK_PENDING_RENT, fo.WORK_DRAFT_RENTS,
                 factory.WORK_RNG, factory.WORK_STREAK, *patch.WORK_SETS, *patch.WORK_RIVAL):
        r.sysreq('WorkSet', work, 0)
    r.op('JUMP', cancel)
    r.p.label(invalid)
    r.call(helpers['msg'], LINE_BASE + 7, 1, 0, 256, 0)
    r.call(helpers['msg_wait'])
    r.call(helpers['msg_close'], 0)
    r.p.label(cancel)
    r.sysreq('GlobalSetParentParam', 0, 0)
    r.const(0)
    r.ret()
    r.p.label(done)
    r.sysreq('GlobalSetParentParam', 0, 1)
    r.const(1)
    r.ret()
