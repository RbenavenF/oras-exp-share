@ F9 registration API, linked in the reserved DllField padding. No caller installed yet.
@ r0 = facility work, r1 = requested M, r2 = effective selection descriptor,
@ r3 = flags: bit0 accepted, bit1 resume. Other bits invalid.
@ Descriptor: byte +0 Box(1)/party(0), u32 slots at +4, u32 count at +0x1c
@ (the retail descriptor is work+0x2c). The Dome caller must provide ALL THREE
@ inscriptions, before its two-fighter replacement. Factory needs no descriptor.
@ Return CONFIG, or -1 on cancellation/invalid input. Only a successful NEW
@ registration writes CONFIG; resume returns its exact saved word, including 0.
@ No streak, ACTIVE, PB, party or Box write. AAPCS, 8-byte aligned calls.
    .syntax unified
    .arm
    .section .text
    .global mode_register
mode_register:
    push    {r4-r10, lr}
    mov     r4, r0
    mov     r5, r1
    mov     r6, r2
    mov     r7, r3
    cmp     r7, #3
    bhi     invalid
    tst     r7, #1
    beq     invalid
    cmp     r5, #4
    bhs     invalid
    ldrb    r0, [r4, #0x838]
    cmp     r0, #0                 @ Normal only; Super remains retail
    bne     invalid
    ldrb    r0, [r4, #0x839]
    cmp     r0, r5, lsr #1
    bne     invalid
    ldr     r1, [r4, #0xb78]
    ldr     r1, [r1, #0x1c]
    ldr     r1, [r1]
    add     r1, r1, #0x13000
    add     r1, r1, #0x144
    ldrh    r2, [r1, #ROUTE_OFF]
    sub     r2, r2, #1
    cmp     r2, #7
    bhs     invalid
    cmp     r5, #2
    cmphs   r2, #2
    bhs     invalid
    tst     r7, #2
    beq     new
    ldr     ip, =CODE_MODE_OF
    blx     ip
    bhs     invalid
    cmp     r5, ip, lsr #8
    bne     invalid
    mov     r0, ip
    pop     {r4-r10, pc}
new:
    adr     r0, configs
    add     r0, r0, r2, lsl #1
    ldrh    r0, [r0]
    add     r10, r1, r0            @ sole write target, committed after validation
    cmp     r2, #0
    moveq   r9, #100
    beq     commit                @ Factory: independent of real party
    cmp     r6, #0
    beq     invalid
    ldr     r0, [r6, #0x1c]
    mov     r1, #3
    cmp     r5, #2
    movhs   r1, #4
    cmp     r0, r1
    bne     invalid
    ldrb    r0, [r6]
    cmp     r0, #1
    bhi     invalid
    ldr     r8, [r4, #0xb84]
    cmp     r0, #0
    bne     source_ready
    ldr     r8, [r4, #0xb78]
    ldr     r8, [r8, #0x1c]
    ldr     r8, [r8, #0x14]
source_ready:
    cmp     r8, #0
    beq     invalid
    mov     r4, #0                 @ seen-slot bitmap (work no longer needed)
    mov     r7, #0                 @ selected member
    mov     r9, #60
member:
    add     r0, r6, r7, lsl #2
    ldr     r1, [r0, #4]
    cmp     r1, #6
    bhs     invalid
    mov     r0, #1
    lsl     r0, r0, r1
    tst     r4, r0
    bne     invalid
    orr     r4, r4, r0
    mov     r0, r8
    ldr     ip, =CODE_PARTY_SLOT
    blx     ip
    cmp     r0, #0
    beq     invalid
    ldr     ip, =CODE_GET_LEVEL
    blx     ip
    sub     r1, r0, #1
    cmp     r1, #100
    bhs     invalid
    cmp     r0, r9
    movhi   r9, r0
    add     r7, r7, #1
    ldr     r0, [r6, #0x1c]
    cmp     r7, r0
    blo     member
commit:
    tst     r5, #1
    moveq   r9, #50
    orr     r0, r9, r5, lsl #8
    strh    r0, [r10]
    pop     {r4-r10, pc}
invalid:
    mvn     r0, #0
    pop     {r4-r10, pc}
    .ltorg
configs:
    .hword CFG_1, CFG_2, CFG_3, CFG_4, CFG_5, CFG_6, CFG_7
    .align 2
