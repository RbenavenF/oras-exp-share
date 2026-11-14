@ F9 modes (reports/diseno/modos.md §2-§3, frontier/modes.py): which bank holds a facility's streak and record, and
@ the level of a challenge, from (route, M). Route = saved work WORK_ROUTE (1..ROUTES while a facility's challenge
@ runs, 0 = the Maison); M = bits 8-9 of the route's CONFIG work (modes.CONFIG, 0 = a save older than F9: Level 50
@ Singles), L = its bits 0-7. M: 0 Singles Level 50, 1 Singles Open, 2 Doubles Level 50, 3 Doubles Open (routes 1-2
@ only). The retail rank byte (+0x838) never carries M: rank Super is always the Maison's own streak.
@
@ Saved work N is at &work[0x4000] + 2*(N - 0x4000); &work[0x4000] = save + 0x13144 = Maison base - MAISON_TO_WORKS.
    .syntax unified
    .arm
    .section .text

    .equ ROUTE_OFF, 2 * (WORK_ROUTE - 0x4000)

@ r0 = facility work -> r1 = &work[0x4000]. Uses r1 only.
works_of:
    ldr     r1, [r0, #0xb78]
    ldr     r1, [r1, #0x1c]
    ldr     r1, [r1]                @ save data
    add     r1, r1, #0x13000
    add     r1, r1, #0x144
    bx      lr

@ r1 = &work[0x4000] -> r2 = route - 1, r3 = &CONFIG[route], ip = CONFIG; flags hs = no mode (route 0 or unknown,
@ M > 3, a bit above M set, or Doubles off the Factory/Tower): the caller takes the retail path. Uses r0, r2, r3, ip.
    .global mode_of
mode_of:
    ldrh    r2, [r1, #ROUTE_OFF]
    sub     r2, r2, #1
    cmp     r2, #ROUTES
    bxhs    lr
    adr     r3, mode_config
    add     r3, r3, r2, lsl #1
    ldrh    r3, [r3]
    add     r3, r1, r3
    ldrh    ip, [r3]
    cmp     ip, #0x200
    blo     validate_level          @ M 0 or 1: every route
    cmp     ip, #0x400
    cmplo   r2, #2                  @ M 2 or 3: routes 1 and 2 only
    bxhs    lr
validate_level:
    cmp     ip, #1
    bxlo    lr                      @ legacy CONFIG=0, carry clear
    and     r0, ip, #0xff
    tst     ip, #0x100
    subeq   r0, r0, #50
    beq     exact_level
    cmp     r2, #0
    subeq   r0, r0, #100
    beq     exact_level            @ Factory Open: exactly 100
    sub     r0, r0, #60
    cmp     r0, #41                 @ own-team Open: 60..100, unsigned
    bx      lr
exact_level:
    cmp     r0, #1                  @ only the exact level is valid
    bx      lr

@ r0 = facility work -> r0 = the level of the challenge's rivals: validated L in an Open Level mode,
@ else 50. Called by the rival builder (pike_level), the rentals (rental_hook) and the Brains (DllField brains_cro.s,
@ by absolute address). Uses r1-r3, ip.
    .global mode_level
mode_level:
    push    {lr}
    bl      works_of
    bl      mode_live
    mov     r0, #50
    pophs   {pc}
    tst     ip, #0x100
    andne   r0, ip, #0xff
    pop     {pc}

@ Player party tail 0x1e3ddc, per member (r0 = its level, r6 = facility work, r7 = StartBattle's second argument):
@ replaces `cmp r0, #50` at 0x1e3e00, followed by `cmple r7, #0; beq keep`. In an Open Level mode the member keeps
@ its level (Z set, so `cmple r7, #0` decides as retail) and CONFIG's L becomes max(L, 60, its level):
@ the first battle fixes L = max(60, highest selected level), and later battles of the same selection keep it.
@ Otherwise the retail comparison. Uses r0-r3, ip (none live at the site: 0x1e3e0c and 0x1e3e44 reload them).
    .global mode_cap
mode_cap:
    push    {r4, lr}
    mov     r4, r0
    mov     r0, r6
    bl      works_of
    bl      mode_live
    bhs     1f
    tst     ip, #0x100
    beq     1f                      @ a Level 50 mode
    and     r0, ip, #0xff
    cmp     r0, r4
    biclo   ip, ip, #0xff
    orrlo   ip, ip, r4
    strhlo  ip, [r3]
    cmp     r0, r0                  @ Z: keep the level
    pop     {r4, pc}
1:  cmp     r4, #50
    pop     {r4, pc}

@ Maison streak accessors (code.bin 0x45cd98 increment, 0x45cee8 get, 0x45cf8c clear, 0x45d010 record; r0 = Maison
@ base = save + 0x195e0, r1 = type, r2 = rank normalised to 0/1, r3 = 9999 for the increment, 0 for the clear). Each
@ one jumps through a table by type; the entries of types 0 (Singles) and 1 (Doubles) point at a stub here instead
@ of the retail bodies, so r1 is the format: ip = operation (0 inc, 1 clear, 2 get, 3 record). The retail slots are
@ S = base + 0x1c4 + 2*rank + 8*format and R = S + 4. With rank Normal, a valid route and a mode of that format, S
@ and R are the mode's works instead (mode_banks: any two works, not S/S+2). Any other case (route 0, rank Super,
@ corrupt CONFIG, a mode of the other format) is the retail slot, never a guessed one.
    .macro STREAK_STUB name, code
    .global \name
\name:
    mov     ip, #\code
    b       mode_streak
    .endm
    STREAK_STUB streak_inc, 0
    STREAK_STUB streak_set, 1
    STREAK_STUB streak_get, 2
    STREAK_STUB streak_record, 3

mode_streak:
    push    {r4-r7}
    add     r4, r0, r2, lsl #1
    add     r4, r4, r1, lsl #3
    add     r4, r4, #0x1c4          @ S (retail)
    add     r5, r4, #4              @ R (retail)
    cmp     r2, #0
    bne     2f                      @ rank Super: the Maison's
    mov     r7, r1                  @ format
    sub     r1, r0, #(MAISON_TO_WORKS & 0xff00)
    sub     r1, r1, #(MAISON_TO_WORKS & 0xff)
    push    {r3, ip, lr}
    bl      mode_of
    mov     r6, ip
    pop     {r3, ip, lr}            @ ldm keeps the flags
    bhs     2f
    lsr     r6, r6, #8              @ M
    cmp     r7, r6, lsr #1
    bne     2f                      @ the other format's mode
    adr     r7, mode_first
    ldrb    r7, [r7, r6]
    add     r7, r7, r2              @ bank: mode_first[M] + route - 1
    adr     r6, mode_banks
    add     r6, r6, r7, lsl #2
    ldrh    r7, [r6]
    add     r4, r1, r7
    ldrh    r7, [r6, #2]
    add     r5, r1, r7
2:  cmp     ip, #3
    moveq   r4, r5                  @ record: R
    mov     r0, r4
    cmp     ip, #1
    strheq  r3, [r4]                @ clear
    ldrhhi  r0, [r4]                @ get, record
    movlo   r2, r5                  @ inc: r0 = S, r2 = R
    pop     {r4-r7}
    blo     STREAK_INC_BODY         @ the retail increment, r3 = limit (0x45cdd0)
    bxeq    lr                      @ clear: no frame
    pop     {r4, pc}                @ get, record: the accessor's own push {r4, lr}

    .align 2
mode_config:                        @ by route - 1: 2*(CONFIG work - 0x4000)
    .hword CFG_1, CFG_2, CFG_3, CFG_4, CFG_5, CFG_6, CFG_7
mode_first:                         @ by M: first mode_banks row (M 2 and 3: routes 1-2 only, mode_of)
    .byte 0, 7, 14, 16
    .align 2
mode_banks:                         @ 2*(work - 0x4000) of streak, record; rows M0 r1-7, M1 r1-7, M2 r1-2, M3 r1-2
    .hword S_0, R_0, S_1, R_1, S_2, R_2, S_3, R_3, S_4, R_4, S_5, R_5, S_6, R_6
    .hword S_7, R_7, S_8, R_8, S_9, R_9, S_10, R_10, S_11, R_11, S_12, R_12, S_13, R_13
    .hword S_14, R_14, S_15, R_15, S_16, R_16, S_17, R_17
