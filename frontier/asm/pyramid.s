@ Battle Pyramid v1 (frontier/pyramid.py, reports/diseno/piramide.md) in the Battle Maison's facility work. The
@ facility work does not survive a map change (Azahar, reports/frontier.md §30: after _MapChangeCore the work's
@ memory was reused and its selection read 0), and every floor is a map change. So the party the player chose in
@ the lobby is kept in saved works: `pyramid_save` copies it there when the lobby's work is deleted, and
@ `pyramid_party` puts it back in the fresh work each floor creates for a battle. Everything here only acts while
@ saved work WORK_ROUTE = PYRAMID_ROUTE (the Pyramid's challenge; frontier/patch.py STREAK_ROUTES), so the Maison
@ and the other facilities keep their behaviour. Saved work N is at &work[0x4000] + 2*(N - 0x4000).
    .syntax unified
    .arm
    .section .text

@ Add a constant that is not an ARM immediate (bits 8-15, then 0-7).
    .macro ADDW reg, value
    add     \reg, \reg, #((\value) & 0xff00)
    add     \reg, \reg, #((\value) & 0xff)
    .endm

@ Player party: called by rental_hook's retail branch after dome_party, r0 = facility work, r1 = &work[WORK_ROUTE].
@ With the Pyramid's route, the selection becomes the three party slots of saved works PYRAMID_SEL0..2: work+0x30,
@ +0x34, +0x38 and the count work+0x48 = 3, which the original copy loop (0x1e3da0, 0x1e3db4) reads next.
@ Uses r0-r2 and the flags only.
    .global pyramid_party
pyramid_party:
    ldrh    r2, [r1]
    cmp     r2, #PYRAMID_ROUTE
    bxne    lr
    ADDW    r1, (2 * (PYRAMID_SEL0 - WORK_ROUTE))
    ldrh    r2, [r1]
    str     r2, [r0, #0x30]
    ldrh    r2, [r1, #2]
    str     r2, [r0, #0x34]
    ldrh    r2, [r1, #4]
    str     r2, [r0, #0x38]
    mov     r2, #PYRAMID_PICKS
    str     r2, [r0, #0x48]
    bx      lr

@ BattleInstWorkDelete's code.bin function 0x1e5c48(holder): r4 = the work ([holder+0x64], may be 0), r5 = holder;
@ replaces its `bl WORK_DELETE_CALL` at 0x1e5c54 (a getter without arguments; r0-r3 are free there). With the
@ Pyramid's route and a party selection of PYRAMID_PICKS members (work+0x48) from the party (work+0x2c = 0, not the
@ Battle Box), each in 0..5: saved works PYRAMID_SEL0..2 = work+0x30..0x38 and PYRAMID_COUNT = PYRAMID_PICKS.
@ Anything else writes nothing (the lobby sets PYRAMID_COUNT = 0 first and refuses unless it reads 3 after the
@ delete). Then the getter, as the original call (tail call: it returns to 0x1e5c58).
    .global pyramid_save
pyramid_save:
    push    {r4, r5, lr}
    cmp     r4, #0
    beq     9f
    ldr     r0, [r4, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]                @ save data
    add     r0, r0, #0x13000
    add     r0, r0, #0x144          @ &work[0x4000]
    ADDW    r0, (2 * (WORK_ROUTE - 0x4000))
    ldrh    r1, [r0]
    cmp     r1, #PYRAMID_ROUTE
    bne     9f
    ldrb    r1, [r4, #0x2c]         @ the selection came from the Battle Box
    cmp     r1, #0
    bne     9f
    ldr     r1, [r4, #0x48]
    cmp     r1, #PYRAMID_PICKS
    bne     9f
    ldr     r1, [r4, #0x30]
    cmp     r1, #6
    bhs     9f
    ldr     r2, [r4, #0x34]
    cmp     r2, #6
    bhs     9f
    ldr     r3, [r4, #0x38]
    cmp     r3, #6
    bhs     9f
    ADDW    r0, (2 * (PYRAMID_SEL0 - WORK_ROUTE))
    strh    r1, [r0]
    strh    r2, [r0, #2]
    strh    r3, [r0, #4]
    add     r0, r0, #(2 * (PYRAMID_COUNT - PYRAMID_SEL0))
    mov     r1, #PYRAMID_PICKS
    strh    r1, [r0]
9:
    pop     {r4, r5, lr}
    b       WORK_DELETE_CALL
