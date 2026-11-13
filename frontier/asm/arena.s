@ Arena B (reports/frontier.md §31): the code.bin part. Only setup+0xa8 bit 31 enables the DllBattle.cro hooks
@ (frontier/asm/arena_cro.s); code.bin StartBattle sets it after constructing a Singles Arena setup.
    .syntax unified
    .arm
    .section .text

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
