@ Arena B (reports/frontier.md §31). Only setup+0xa8 bit 31 enables the hooks.
@ code.bin StartBattle sets it after constructing a Singles Arena setup.
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

@ code.bin 0x1e33d8: r0/ip/flags are scratch. Shared Arena/Palace setup:
@ clear both stale marks, select only this route's active Singles challenge.
@ Both public names enter the same routine (no duplicate save/route traversal).
    .global arena_start, palace_start
arena_start:
palace_start:
    ldr     ip, [r4, #0x6c8]
    bic     ip, ip, #(ARENA_RULE | PALACE_RULE)
    str     ip, [r4, #0x6c8]
    ldrb    r0, [r4, #0x621]
    cmp     r0, #0
    bne     9f
    ldr     r0, [r4, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]
    add     r0, r0, #0x13000
    add     r0, r0, #0x144
    ldrh    ip, [r0, #(2 * (WORK_ROUTE - 0x4000))]
    cmp     ip, #ARENA_ROUTE
    beq     1f
    cmp     ip, #PALACE_ROUTE
    bne     9f
    ldrh    r0, [r0, #(2 * (PALACE_ACTIVE - 0x4000))]
    cmp     r0, #0
    ldrne   ip, [r4, #0x6c8]
    orrne   ip, ip, #PALACE_RULE
    b       2f
1:
    ldrh    r0, [r0, #(2 * (ARENA_ACTIVE - 0x4000))]
    cmp     r0, #0
    ldrne   ip, [r4, #0x6c8]
    orrne   ip, ip, #ARENA_RULE
2:
    strne   ip, [r4, #0x6c8]
9:
    mov     r0, r5
    b       ARENA_START_RESUME

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
@ ARENA_UDIV = code.bin 0x15ec10 (DllBattle import thunk 0x420, literal 0x424).
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
    bl      ARENA_UDIV
    mov     r6, r0
    mul     r0, r7, r4
    mov     r1, r5
    bl      ARENA_UDIV
    cmp     r6, r0
    mov     r0, #3
    movhi   r0, #2
    movlo   r0, #1
1:
    pop     {r3-r7, pc}
