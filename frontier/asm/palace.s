@ Battle Palace stage B (reports/frontier.md §32): the game's AI decides for the player's Pokemon.
@ Only setup+0xa8 bit 30 (PALACE_RULE) enables the CRO bridges; code.bin StartBattle sets it for a
@ Singles Palace challenge (route PALACE_ROUTE, work PALACE_ACTIVE not 0) and clears it otherwise.
@
@ Measured in Azahar (2026-11-05): a client's thinker type is byte +0x91 (0 UI, 1 AI, 2 replay) and selects
@ the column of the command table DllBattle 0xdbc68 (rows of 0x1c: command, three {proc, adj}). Making the
@ player's client 0 an AI client hangs on a black screen: server commands (animations, messages) only have
@ a UI proc. So client 0 stays UI and gets, as AI clients do, an AI object (+0x1c8, AI flags PALACE_AI);
@ only its decisions use the AI column: 3 (choose an action) and 5/6 (choose a Pokemon to send in).
    .syntax unified
    .arm
    .section .text

@ code.bin 0x1e33d8, reached from arena_start: r4 work, r5 the value for r0; r0/ip/flags scratch.
    .global palace_start
palace_start:
    ldr     ip, [r4, #0x6c8]        @ setup+0xa8
    bic     ip, ip, #PALACE_RULE
    str     ip, [r4, #0x6c8]
    ldrb    r0, [r4, #0x621]        @ battle style: Singles only
    cmp     r0, #0
    bne     1f
    ldr     r0, [r4, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]
    add     r0, r0, #0x13000
    add     r0, r0, #0x144
    ldrh    ip, [r0, #(2 * (WORK_ROUTE - 0x4000))]
    cmp     ip, #PALACE_ROUTE
    bne     1f
    ldrh    r0, [r0, #(2 * (PALACE_ACTIVE - 0x4000))]
    cmp     r0, #0
    ldrne   ip, [r4, #0x6c8]
    orrne   ip, ip, #PALACE_RULE
    strne   ip, [r4, #0x6c8]
1:
    mov     r0, r5
    b       ARENA_START_RESUME

@ CRO 0x731f0 in the client constructor 0x72f40, r4 client, sp its frame (untouched before the reads).
@ Returns Z set to create the AI object. Retail: thinker 1 and argument [sp,#0x6c] 0. Palace: also the
@ UI client 0 with that argument 0. r0/ip/flags scratch (both continuations reload r0).
    .global palace_ai_want
palace_ai_want:
    ldrb    r0, [r4, #0x91]
    cmp     r0, #1
    ldreq   r0, [sp, #0x6c]
    cmpeq   r0, #0
    bxeq    lr
    ldrb    r0, [r4, #0x91]
    ldrb    ip, [r4, #0x90]
    orrs    r0, r0, ip              @ thinker 0 (UI) and client 0
    bxne    lr
    ldr     r0, [sp, #0x6c]
    cmp     r0, #0
    bxne    lr
    ldr     r0, [r4]                @ BattleMain
    ldr     r0, [r0, #0x10]         @ BattleSetup
    ldr     r0, [r0, #0xa8]
    and     r0, r0, #PALACE_RULE
    eors    r0, r0, #PALACE_RULE    @ Z set iff the bit is set
    bx      lr

@ CRO 0x73258, r4 client, r5 BattleMain, r6 the AI flags just chosen. For the Palace's client 0 use
@ PALACE_AI (the Maison trainers' 7). Replaces `ldr r0,[r5,#0x820]; cmp r0,#0; bne 0x732c0; b 0x732b0`:
@ returns to 0x732c0, or to 0x732b0 (retail assertion) if that object is missing. LR = CRO 0x73260.
    .global palace_ai_flags
palace_ai_flags:
    ldrb    r0, [r4, #0x90]
    ldrb    ip, [r4, #0x91]
    orrs    r0, r0, ip
    bne     1f
    ldr     r0, [r5, #0x10]
    ldr     r0, [r0, #0xa8]
    tst     r0, #PALACE_RULE
    movne   r6, #PALACE_AI
1:
    ldr     r0, [r5, #0x820]
    cmp     r0, #0
    addne   lr, lr, #(0x732c0 - 0x73260)
    addeq   lr, lr, #(0x732b0 - 0x73260)
    bx      lr

@ CRO 0x49ec, the command dispatch of client proc 0x4914: r0 row, r2 table, r4 client. r1 is NOT the
@ command here: 0x49d4..0x49e8 left in it the row's byte 1 != 0 (and 0x4a00 overwrites it). The command is the
@ row's byte 0 (0x49c0 `ldrb r3,[r2,r0*28]`; e.g. 0x101 = command 1 with byte 1 set). Reproduces
@ `ldrb r3,[r4,#0x91]; rsb r0,r0,r0,lsl#3; add r5,r4,#0x1e4; add r2,r2,r0,lsl#2`, with column 1 (AI) for the
@ Palace's client 0 on commands 3, 5 and 6. ip/flags scratch.
    .global palace_dispatch
palace_dispatch:
    rsb     r0, r0, r0, lsl #3
    add     r5, r4, #0x1e4
    add     r2, r2, r0, lsl #2
    ldrb    r3, [r4, #0x91]
    ldrb    ip, [r4, #0x90]
    orrs    ip, ip, r3              @ thinker 0 (UI) and client 0
    bxne    lr
    ldrb    ip, [r2]                @ the row's command
    cmp     ip, #3
    cmpne   ip, #5
    cmpne   ip, #6
    bxne    lr
    ldr     ip, [r4]
    ldr     ip, [ip, #0x10]
    ldr     ip, [ip, #0xa8]
    tst     ip, #PALACE_RULE
    movne   r3, #1
    bx      lr
