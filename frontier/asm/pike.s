@ Battle Pike (frontier/pike.py, reports/diseno/tubo.md): HP, status and PP carry over between the Pike's battles.
@ The Battle Maison rebuilds a copy for every battle. Pike skips healing the real party in rental_hook and
@ heals only that copy (0x3b5d34), then restores each fighter's HP, status and PP from saved works, by position in the battle
@ party: PIKE_HP0 + i (0xFFFF = full) and PIKE_ST0 + i (the u32 status field of the battle block, low half).
@ Everything here only acts while saved work WORK_ROUTE = PIKE_ROUTE (the Pike's challenge; patch.STREAK_ROUTES).
@
@ PokemonParam: +0xc = core. Core accessors (code.bin, reports/frontier.md §28): GET_HP 0x153174, GET_MAX_HP
@ 0x153254, SET_HP 0x14f450(core, hp), GET_SICK 0x4d22e4, SET_SICK 0x14f814(core, value). PokeParty: members at
@ +0..+0x14, count u8 at +0x18. Saved work N is at &work[0x4000] + 2*(N - 0x4000).
    .syntax unified
    .arm
    .section .text

    .macro ADDW reg, value
    add     \reg, \reg, #((\value) & 0xff00)
    add     \reg, \reg, #((\value) & 0xff)
    .endm

@ r6 = &work[PIKE_HP0] if WORK_ROUTE is the Pike's, else Z clear (ne). Needs r4 = facility work. Uses r0.
    .macro PIKE_WORKS
    ldr     r0, [r4, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]                @ save data
    add     r6, r0, #0x13000
    add     r6, r6, #0x144          @ &work[0x4000]
    ldrh    r0, [r6, #(2 * (WORK_ROUTE - 0x4000))]
    cmp     r0, #PIKE_ROUTE
    .endm

@ H1: replaces `bl 0x1e3d2c` at 0x1e3110 in StartBattle's 0x1e30b8 (r0 = facility work, r3 = the new battle party,
@ which 0x1e0634 copies into the battle setup next). Builds it as before, then, with the Pike's route, sets each
@ member's HP (capped to its max HP; 0xFFFF leaves it full) and status from the works. r0 is not used after the call.
    .global pike_build
pike_build:
    push    {r4-r10, lr}
    mov     r4, r0
    mov     r5, r3
    bl      BUILD_PARTY
    PIKE_WORKS
    bne     9f
    mov     r0, r5
    bl      PARTY_PREPARE           @ heal the copy, never the original party (rental_hook)
    ADDW    r6, (2 * (PIKE_HP0 - 0x4000))
    ldrb    r7, [r5, #0x18]         @ members
    cmp     r7, #PIKE_FIGHTERS
    movhi   r7, #PIKE_FIGHTERS
    mov     r8, #0
1:
    cmp     r8, r7
    bge     9f
    ldr     r0, [r5, r8, lsl #2]
    ldr     r4, [r0, #0xc]          @ core (the work is not needed any more)
    add     r0, r6, r8, lsl #1
    ldrh    r1, [r0]                @ saved HP
    add     r0, r1, #1
    cmp     r0, #0x10000
    beq     2f                      @ 0xFFFF: full
    mov     r9, r1
    mov     r0, r4
    bl      GET_MAX_HP
    mov     r1, r9
    cmp     r1, r0
    movhi   r1, r0
    mov     r0, r4
    bl      SET_HP
2:
    add     r0, r6, r8, lsl #1
    ldrh    r1, [r0, #(2 * (PIKE_ST0 - PIKE_HP0))]
    mov     r0, r4
    bl      SET_SICK
    mov     r0, r4
    add     r1, r6, r8, lsl #1
    add     r1, r1, #(2 * (PIKE_PP0 - PIKE_HP0))
    mov     r2, #0                  @ restore PP, capped to the freshly healed copy
    bl      pike_pp
    add     r8, r8, #1
    b       1b
9:
    pop     {r4-r10, pc}

@ H2: replaces the first instruction of IsWin 0x1e5664 (ldrb r0, [r0, #0x73c]; cmp r0, #1; movne r0, #0; bx lr),
@ which the zone script calls right after StartBattle. With the Pike's route, copies the HP and status of the
@ player's battle party (battle setup work+0x620, its +0x4c: 0x1e06dc) back to the works, then returns IsWin's value.
    .global pike_iswin
pike_iswin:
    push    {r4-r10, lr}
    mov     r4, r0
    PIKE_WORKS
    bne     9f
    ADDW    r6, (2 * (PIKE_HP0 - 0x4000))
    ldr     r5, [r4, #0x66c]        @ the battle's player party
    cmp     r5, #0
    beq     9f
    ldrb    r7, [r5, #0x18]
    cmp     r7, #PIKE_FIGHTERS
    movhi   r7, #PIKE_FIGHTERS
    mov     r8, #0
1:
    cmp     r8, r7
    bge     9f
    ldr     r0, [r5, r8, lsl #2]
    ldr     r9, [r0, #0xc]          @ core
    mov     r0, r9
    bl      GET_HP
    add     r1, r6, r8, lsl #1
    strh    r0, [r1]
    mov     r0, r9
    bl      GET_SICK
    add     r1, r6, r8, lsl #1
    strh    r0, [r1, #(2 * (PIKE_ST0 - PIKE_HP0))]
    mov     r0, r9
    add     r1, r6, r8, lsl #1
    add     r1, r1, #(2 * (PIKE_PP0 - PIKE_HP0))
    mov     r2, #1                  @ save PP
    bl      pike_pp
    add     r8, r8, #1
    b       1b
9:
    ldrb    r0, [r4, #0x73c]
    cmp     r0, #1
    movne   r0, #0
    pop     {r4-r10, pc}

@ Transfer four PP bytes using retail core accessors (decrypt/checksum/encrypt).
@ r0 = core, r1 = &work[PP low pair + fighter], r2 = 0 restore / 1 save.
@ Each byte 0xff restores the full PP; smaller values are capped to the healed PP.
@ Saved PP positions follow the selected party positions, as HP/status do in v1.
    .global pike_pp
pike_pp:
    push    {r4-r8, lr}
    mov     r4, r0
    mov     r5, r1
    mov     r6, r2
    mov     r7, #0
1:
    mov     r0, r4
    mov     r1, r7
    bl      GET_PP
    add     r8, r5, r7
    tst     r7, #2
    addne   r8, r8, #PIKE_PP_GAP
    cmp     r6, #0
    strbne  r0, [r8]
    bne     2f
    ldrb    r2, [r8]
    cmp     r2, r0
    movhi   r2, r0
    mov     r0, r4
    mov     r1, r7
    bl      SET_PP
2:
    add     r7, r7, #1
    cmp     r7, #4
    blo     1b
    pop     {r4-r8, pc}

@ DllField 0x4e644 PokePartyGetParam: virtual slots 256..258 mean Pike
@ selected positions. Ordinary slots keep retail semantics on every route.
@ r5 field context, r6 slot, r8 real party. Bridge LR = CRO base+0x4e64c.
@ The selected source can be the real party or the Battle Box, as BUILD_PARTY.
    .global pike_param
pike_param:
    sub     r0, r6, #0x100
    cmp     r0, #PIKE_FIGHTERS
    bhs     1f
    ldr     ip, [r5, #0x64]
    cmp     ip, #0
    beq     1f
    ldr     r1, [r5, #0x1c]
    ldr     r1, [r1]
    add     r1, r1, #0x13000
    add     r1, r1, #0x144
    ldrh    r1, [r1, #(2 * (WORK_ROUTE - 0x4000))]
    cmp     r1, #PIKE_ROUTE
    bne     1f
    ldrb    r1, [ip, #0x2c]
    cmp     r1, #0
    ldrne   r8, [ip, #0xb84]
    add     ip, ip, #0x30
    ldr     r6, [ip, r0, lsl #2]
1:
    mov     r0, r8
    push    {r3, lr}
    bl      PARTY_COUNT
    cmp     r0, r6
    pop     {r3, lr}
    addhi   lr, lr, #8             @ valid: next instruction, CRO+0x4e654
    addls   lr, lr, #0x460         @ invalid: retail zero, CRO+0x4eaac
    bx      lr
