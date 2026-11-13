@ Frontier Brains (reports/diseno/cerebros.md §3, frontier/brains.py): rival identity and team of a Brain battle,
@ and no retail Maison boss on a Frontier route.
@
@ Linked at its DllField.cro FILE offset (BRAINS_AT, the zero padding of the declared code region after .text
@ 0xf03f0 and the DexNav routine 0xf0400-0xf046c, before .rodata 0xf1000), so the `bl`s from the CRO's own natives
@ are plain relative branches and nothing depends on where the CRO is loaded. code.bin functions are called by
@ absolute address (code.bin has no ASLR).
@
@ Three calls of DllField's natives are redirected here (frontier/brains.py SITES):
@   SetTrainer (0x94edc), Singles path:  0x94f04 bl thunk(0x1e3aac chooser)   -> brain_choose
@                                        0x94f18 bl thunk(0x1e54a0 load)      -> brain_load
@   StartBattle (0x9500c):               0x95044 bl thunk(0x1e30b8 core)      -> brain_start
@ Each one calls the code.bin function first, with the same arguments, and only then acts, and only while saved
@ work WORK_ROUTE is a Frontier route 1..ROUTES. With route 0 (the Maison) all three are the retail call.
@
@ Saved work N is at &work[0x4000] + 2*(N - 0x4000), &work[0x4000] = [[[facility work+0xb78]+0x1c]] + 0x13144.
@ WORK_BRAIN (the Brain of the coming battle, written by the zone script's brains_check): route + 8*variant,
@ variant 1 silver, 2 gold; 0 = none.
    .syntax unified
    .arm
    .section .text

    .equ ROUTE_OFF, 2 * (WORK_ROUTE - 0x4000)
    .equ BRAIN_OFF, 2 * (WORK_BRAIN - 0x4000)
    .equ ENTRY, 4 + 3 * 8                  @ brain_table row: u16 trainer, u8 iv, u8 pad, 3 x (u16 set, u8 ev[6])

@ r0 = facility work -> r0 = &work[0x4000]. Uses r0 only.
works:
    ldr     r0, [r0, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]
    add     r0, r0, #0x13000
    add     r0, r0, #0x144
    bx      lr

@ r0 = facility work -> r0 = brain_table row of the Brain due on the current route, or 0. Uses r0-r3.
row:
    push    {r4, lr}
    bl      works
    ldrh    r1, [r0, #ROUTE_OFF]
    sub     r2, r1, #1
    cmp     r2, #(ROUTES - 1)
    bhi     8f                             @ route 0 (Maison) or unknown
    add     r3, r0, #(BRAIN_OFF & 0xff00)
    ldrh    r3, [r3, #(BRAIN_OFF & 0xff)]
    and     r4, r3, #7
    cmp     r4, r1
    bne     8f                             @ no Brain, or another facility's
    lsr     r3, r3, #3
    sub     r3, r3, #1
    cmp     r3, #1
    bhi     8f                             @ variant not 1 (silver) or 2 (gold)
    add     r3, r3, r2, lsl #1             @ row (route - 1) * 2 + variant - 1
    mov     r4, #ENTRY
    adrl    r0, brain_table
    mla     r0, r3, r4, r0
    ldrh    r1, [r0]
    cmp     r1, #0
    popne   {r4, pc}                       @ a Brain with a trainer
8:  mov     r0, #0
    pop     {r4, pc}

@ SetTrainer's chooser: (work, r1) -> trainer id. On a Frontier route: the Brain's trainer when one is due; else, in
@ rank Normal from the 19th win on, a trainer of the 70-109 bracket (0x1e3aac returns the Maison's boss at 19 and
@ trainer 0 above it). Elsewhere the retail id.
    .global brain_choose
brain_choose:
    push    {r4-r6, lr}
    mov     r4, r0
    mov     r5, r1
    ldr     ip, =CODE_CHOOSER
    blx     ip
    mov     r6, r0
    mov     r0, r4
    bl      row
    cmp     r0, #0
    ldrhne  r6, [r0]                       @ the Brain
    bne     9f
    mov     r0, r4
    bl      works
    ldrh    r1, [r0, #ROUTE_OFF]
    sub     r2, r1, #1
    cmp     r2, #(ROUTES - 1)
    bhi     9f                             @ the Maison: retail
    ldrb    r3, [r4, #0x838]
    cmp     r3, #0
    bne     9f                             @ rank Super: not a Frontier rank
    add     r0, r0, #(MAISON_TO_WORKS & 0xff00)
    add     r0, r0, #(MAISON_TO_WORKS & 0xff)   @ Maison base
    ldrb    r1, [r4, #0x839]               @ type
    mov     r2, #0                         @ rank Normal (r3)
    ldr     ip, =CODE_WIN_GET
    blx     ip                             @ the route's streak in its mode's bank (frontier/asm/modes.s)
    mov     r2, r0
    cmp     r2, #BOSS_STREAK
    blo     9f
    mov     r0, r4
    mov     r1, r5
    mov     r2, #LATE_FIRST
    mov     r3, #LATE_COUNT
    ldr     ip, =CODE_PICK
    blx     ip
    mov     r6, r0
9:  mov     r0, r6
    pop     {r4-r6, pc}

@ SetTrainer's load: (work, n, id). The load sets work+1 (IsBoss, the boss battle flag) at the Maison's boss
@ streaks; on a Frontier route it is cleared: no ribbon, diary or boss flow (cerebros.md §3.3).
    .global brain_load
brain_load:
    push    {r4, lr}
    mov     r4, r0
    ldr     ip, =CODE_LOAD
    blx     ip
    mov     r0, r4
    bl      works
    ldrh    r1, [r0, #ROUTE_OFF]
    sub     r1, r1, #1
    cmp     r1, #(ROUTES - 1)
    movls   r1, #0
    strbls  r1, [r4, #1]
    pop     {r4, pc}

@ StartBattle's core: (work, a, b). Once the battle setup (work+0x620) and the rival's party (setup+0x50) exist,
@ before the battle runs: with a Brain due on this route and its trainer chosen (work+4), every rival member is
@ remade in order from the Brain's row: its set from maisonpkN, level 50 (the Open Level L in that mode), the row's IV for all six, ability slot 0,
@ then the six EV exactly (all set to 0, then each value; 0x3b4b64 caps at 252 and 510 in total), full HP; and
@ copied over the party member (as AddMember does).
    .global brain_start
brain_start:
    push    {r4-r11, lr}
    sub     sp, sp, #0x24                  @ args, 16-byte set, 3 preserved Noland IDs
    mov     r4, r0
    bl      works                         @ CODE_START's existing rival hook overwrites WORK_RIVAL
    add     r0, r0, #(2 * (WORK_RIVAL - 0x4000))
    ldrh    r3, [r0]
    str     r3, [sp, #0x18]
    ldrh    r3, [r0, #2]
    str     r3, [sp, #0x1c]
    ldrh    r3, [r0, #4]
    str     r3, [sp, #0x20]
    mov     r0, r4
    ldr     ip, =CODE_START
    blx     ip
    mov     r11, r0
    mov     r0, r4
    bl      row
    movs    r5, r0
    beq     9f
    ldrh    r0, [r5]
    ldr     r1, [r4, #4]                   @ trainer of rival 0
    cmp     r0, r1
    bne     9f                             @ not the Brain's trainer: leave the party alone
    sub     r0, r0, #129                   @ factory's private trainers 129, 130
    cmp     r0, #1
    mov     r10, #0
    movls   r10, #1
    ldr     r6, [r4, #0x670]               @ setup+0x50: the rival's party
    ldrb    r0, [r6, #0x18]
    ldrh    r1, [r5]
    sub     r1, r1, #137                   @ Tucker's private silver/gold trainers
    cmp     r1, #1
    bhi     14f
    mov     r10, #2                       @ Dome: two members, selected from the preview trio
    cmp     r0, #2
    bne     9f
    mov     r0, r4
    bl      works
    add     r0, r0, #(2 * (DOME_FORCED - 0x4000) & 0xff00)
    add     r0, r0, #(2 * (DOME_FORCED - 0x4000) & 0xff)
    ldrh    r1, [r0]
    ldrh    r2, [r0, #2]
    cmp     r1, r2
    beq     9f                             @ malformed selection: never index outside the row
    ldrh    r3, [r5, #4]
    sub     r1, r1, r3
    sub     r2, r2, r3
    cmp     r1, #2
    cmpls   r2, #2
    bhi     9f
    str     r1, [sp, #0x18]                @ keep trio indices across CODE_* calls
    str     r2, [sp, #0x1c]
    b       15f
14:
    cmp     r0, #3
    bne     9f
15:
    mov     r7, #0                         @ member
1:  add     r8, r5, #4
    mov     r0, r7
    cmp     r10, #2
    addeq   r1, sp, #0x18
    ldreq   r0, [r1, r7, lsl #2]
    add     r8, r8, r0, lsl #3             @ selected member's (u16 set, u8 ev[6])
    ldr     r0, [r4, #0xb70]               @ heap
    mov     r1, #ARCHIVE_NORMAL
    ldrh    r2, [r8]
    cmp     r10, #1
    bne     10f
    mov     r0, r4
    bl      works
    add     r0, r0, #(2 * (WORK_RIVAL - 0x4000))
    add     r0, r0, r7, lsl #1
    add     r3, sp, #0x18
    ldr     r2, [r3, r7, lsl #2]
    strh    r2, [r0]                       @ record the actual Noland rival; leave rentals/IV untouched
    tst     r2, #0x8000
    moveq   r1, #ARCHIVE_NORMAL
    movne   r1, #ARCHIVE_SUPER
    bic     r2, r2, #0xfc00
    ldr     r0, [r4, #0xb70]
10:
    add     r3, sp, #8
    ldr     ip, =CODE_LOAD_SET
    blx     ip
    cmp     r10, #1
    bne     12f
    mov     r6, #0
11: add     r0, sp, #10                    @ Return -> Frustration in Noland's temporary set only
    add     r0, r0, r6, lsl #1
    ldrh    r1, [r0]
    cmp     r1, #216
    moveq   r1, #218
    strheq  r1, [r0]
    add     r6, r6, #1
    cmp     r6, #4
    blt     11b
12:
    mov     r0, #0                         @ ability slot 0
    mov     r1, #0xff                      @ as the rival builder (0x1e4e70)
    str     r0, [sp]
    str     r1, [sp, #4]
    mov     r0, r4
    ldr     ip, =CODE_MODE_LEVEL
    blx     ip                             @ 50, or the challenge's Open Level L (frontier/asm/modes.s)
    mov     r1, r0
    add     r0, sp, #8
    ldrb    r2, [r5, #2]                   @ IV
    ldr     r3, [r4, #0xb70]
    ldr     ip, =CODE_MAKE_PARAM
    blx     ip
    movs    r9, r0
    beq     8f
    cmp     r10, #1
    bne     13f
    mov     r1, #0
    ldr     ip, =CODE_FRIENDSHIP
    blx     ip
    b       4f                            @ keep the rental set's EV distribution from MAKE_PARAM
13:
    mov     r6, #0
2:  mov     r0, r9                         @ every EV to 0 first (lowering is never limited); outside fast mode, as 0x1ef904
    mov     r1, r6
    mov     r2, #0
    ldr     ip, =CODE_EV_SET
    blx     ip
    add     r6, r6, #1
    cmp     r6, #6
    blt     2b
    mov     r6, #0
3:  add     r0, r8, #2
    ldrb    r2, [r0, r6]                   @ EV in pml order: HP, Atk, Def, SpA, SpD, Spe
    mov     r0, r9
    mov     r1, r6
    ldr     ip, =CODE_EV_SET
    blx     ip
    add     r6, r6, #1
    cmp     r6, #6
    blt     3b
4:  ldr     r6, [r9, #0xc]                 @ core
    mov     r0, r6
    ldr     ip, =CODE_GET_MAX_HP
    blx     ip
    mov     r1, r0
    mov     r0, r6
    ldr     ip, =CODE_SET_HP
    blx     ip
    ldr     r6, [r4, #0x670]
    ldr     r0, [r6, r7, lsl #2]           @ the party's own member object
    mov     r1, r9
    ldr     ip, =CODE_COPY
    blx     ip
    ldr     r0, [r9]
    ldr     r1, [r0, #8]
    mov     r0, r9
    blx     r1                             @ free the temporary (as 0x1e35d0)
8:  add     r7, r7, #1
    mov     r0, #3
    cmp     r10, #2
    moveq   r0, #2
    cmp     r7, r0
    blt     1b
9:  mov     r0, r11
    add     sp, sp, #0x24
    pop     {r4-r11, pc}

    .ltorg
    .balign 4
brain_table:                               @ by (route - 1) * 2 + variant - 1, filled by brains.py
    .space ENTRY * 2 * ROUTES
    .global brains_cro_end
brains_cro_end:
