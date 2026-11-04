@ Battle Pike v1 (frontier/pike.py, reports/diseno/tubo.md): HP and status carry over between the Pike's battles.
@ The Battle Maison fights with a copy of the party, healed (0x3b5d34, PokePartyRecoverAll, on the real party) and
@ rebuilt for every battle, so the Pike keeps each fighter's HP and status in saved works, by position in the battle
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
    add     r8, r8, #1
    b       1b
9:
    ldrb    r0, [r4, #0x73c]
    cmp     r0, #1
    movne   r0, #0
    pop     {r4-r10, pc}
