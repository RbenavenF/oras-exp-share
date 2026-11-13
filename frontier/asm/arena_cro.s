@ Arena B (reports/frontier.md §31): the battle-time hooks, in DllBattle.cro (F7-CUEVA-LUMA, 2026-11-13).
@ Linked at their DllBattle.cro FILE offset after palace_cro.s (patch.BATTLE_CRO_AT, the zero padding of the
@ declared code region before .rodata 0xd8000), like palace_cro.s: `bl`s to CRO code are relative and only
@ code.bin addresses are absolute. Until 2026-11-13 they lived in the code.bin cave, whose start Luma3DS
@ overwrites with its LayeredFS payload on a console (patch.LUMA_RESERVED).
@ The bridges (arena_engine.cro_writes) are `nop; bl stub; b +0; nop`: LR = site + 8, as with the former
@ `ldr ip; blx ip; b +0; .word`, so returning to LR resumes at site + 16.
    .syntax unified
    .arm
    .section .text

@ Flag/state getter for a server flow. OUT = &saved work ARENA_HP0,
@ Z clear on success. TMP and OUT are scratch; caller owns all other registers.
    .macro ARENA_STATE out, tmp, server
    ldr     \out, [\server, #4]
    ldr     \out, [\out, #0x10]     @ BattleMain -> BattleSetup
    ldr     \tmp, [\out, #0xa8]
    tst     \tmp, #ARENA_RULE
    beq     99f
    ldr     \out, [\out, #0x7c]     @ game data -> save
    ldr     \out, [\out]
    add     \out, \out, #0x13000
    add     \out, \out, #0x144
    add     \out, \out, #(ARENA_HP_OFFSET & 0xff00)
    add     \out, \out, #(ARENA_HP_OFFSET & 0xff)
99:
    .endm

    .macro ARENA_CRO_CALL offset
    ldr     ip, =\offset
    add     ip, r11, ip
    blx     ip
    .endm

@ CRO 0x724c0, r4 server / r5 entrant / fp global turn. Reproduce all displaced
@ instructions, including the native age reset, then snapshot the entrant's HP.
    .global arena_enter
arena_enter:
    add     r0, r5, #0x100
    mov     r1, #0
    strh    fp, [r0, #0x5a]
    strh    r1, [r0, #0x58]
    push    {r2, r3, r6, lr}
    ARENA_STATE r6, r2, r4
    beq     1f
    ldrb    r2, [r5, #0x19]         @ ids 0..5 player, 12..17 opponent
    cmp     r2, #12
    movlo   r2, #0
    movhs   r2, #2
    ldrh    r3, [r5, #0x10]
    strh    r3, [r6, r2]
1:
    pop     {r2, r3, r6, pc}

@ CRO 0x7945c, AFTER its push {r4-r11,lr}, BEFORE its Ghost exception.
@ A fainted active mon must still be replaceable. Return retail rejection 3;
@ its output fields are required by the party UI even without referee text.
    .global arena_switch
arena_switch:
    ldr     ip, [r0]               @ client -> BattleMain
    ldr     ip, [ip, #0x10]
    ldr     ip, [ip, #0xa8]
    tst     ip, #ARENA_RULE
    beq     1f
    ldrh    ip, [r1, #0x10]
    cmp     ip, #0
    beq     1f
    ldrb    ip, [r1, #0x19]
    strb    ip, [r2]
    mov     ip, #0
    strh    ip, [r3]
    mov     r0, #3
    pop     {r4-r11, pc}
1:
    mov     r6, r0
    mov     r8, r1
    sub     sp, sp, #12
    mov     sl, r2
    bx      lr

@ CRO 0x1d21c, once after all residual effects and age increments. The smaller
@ age is the time since the last entrant, so the survivor need not be reset.
@ Both HP are cleared before either KO is processed, including a last-mon tie.
    .global arena_turn_end
arena_turn_end:
    push    {r3-r11, lr}
    mov     r4, r6
    ldr     r11, =(ARENA_END_SITE + 8)
    sub     r11, lr, r11           @ loaded CRO base, independent of ASLR
    ARENA_STATE r5, r0, r4
    beq     9f
    add     r0, r4, #0x1000
    ldr     r0, [r0, #0x254]        @ ordered active BattleMon list
    ldrb    r1, [r0, #0x6e]
    cmp     r1, #2
    bne     9f
    ldr     r8, [r0]
    ldr     r9, [r0, #4]
    ldrb    r1, [r8, #0x19]
    cmp     r1, #12
    movhs   r1, r8
    movhs   r8, r9
    movhs   r9, r1
    ldrh    r0, [r8, #0x10]
    cmp     r0, #0
    beq     9f
    ldrh    r2, [r9, #0x10]
    cmp     r2, #0
    beq     9f
    add     r1, r8, #0x100
    ldrh    r1, [r1, #0x58]
    cmp     r1, #3
    blo     9f
    add     r1, r9, #0x100
    ldrh    r1, [r1, #0x58]
    cmp     r1, #3
    blo     9f
    ldrh    r1, [r5]
    ldrh    r3, [r5, #2]
    bl      arena_judge
    mov     r10, r0
    mov     r0, #0
    tst     r10, #1
    strhne  r0, [r8, #0x10]
    tst     r10, #2
    strhne  r0, [r9, #0x10]
    tst     r10, #1
    movne   r6, r8
    blne    arena_queue_ko
    tst     r10, #2
    movne   r6, r9
    blne    arena_queue_ko
9:
    mov     r0, r4
    ARENA_CRO_CALL 0x6b6fc          @ displaced retail call, also with Arena off
    pop     {r3-r11, pc}

@ r4 server, r6 mon, r11 CRO base. Event 0x12, force=1 because its HP was
@ cleared along with the other side before dispatch. Normal KO owns the rest.
arena_queue_ko:
    push    {r3, lr}
    mov     r0, r4
    mov     r1, #0x12
    ldrb    r2, [r6, #0x19]
    ARENA_CRO_CALL 0x6f920
    ldrb    r2, [r6, #0x19]
    strb    r2, [r0, #4]
    mov     r2, #1
    strb    r2, [r0, #5]
    mov     r1, r0
    mov     r0, r4
    ARENA_CRO_CALL 0x6d4ec
    pop     {r3, pc}

@ r0/r1 = player's current/entry HP; r2/r3 = opponent's current/entry HP.
@ Compare floor(100 * current / entry), as Cuerpo's integer percentages.
@ Return a fainting mask: 1 player loses, 2 opponent loses, 3 both (tie).
@ Missing entry HP (zero) returns 0: never faint anyone with an invalid snapshot.
@ ARENA_UDIV = code.bin 0x15ec10 (DllBattle imports it through thunk 0x420), called by absolute address.
    .global arena_judge
arena_judge:
    push    {r3-r7, lr}
    mov     r4, r2
    mov     r5, r3
    cmp     r1, #0
    cmpne   r5, #0
    moveq   r0, #0
    beq     1f
    mov     r7, #100
    mul     r0, r7, r0
    ldr     ip, =ARENA_UDIV         @ code.bin, absolute (this code runs from the CRO)
    blx     ip
    mov     r6, r0
    mul     r0, r7, r4
    mov     r1, r5
    ldr     ip, =ARENA_UDIV
    blx     ip
    cmp     r6, r0
    mov     r0, #3
    movhi   r0, #2
    movlo   r0, #1
1:
    pop     {r3-r7, pc}

    .ltorg
