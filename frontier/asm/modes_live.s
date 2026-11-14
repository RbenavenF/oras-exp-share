@ F9: reclaimed, unreachable retail Doubles increment body 0x45cdfc..0x45ce30.
@ Its jump-table entry now targets streak_inc (modes.s); no other inbound references.
@ Level hooks require ACTIVE, while streak hooks must still clear the mode's bank after LOST clears ACTIVE.
@ Same interface as mode_of: carry set = invalid/inactive, r1 works, r2 route-1, r3 CONFIG address, ip CONFIG.
    .syntax unified
    .arm
    .section .text
    .global mode_live
mode_live:
    push    {lr}
    bl      MODE_OF
    pophs   {pc}
    adr     r0, active_offsets
    ldrb    r0, [r0, r2]
    ldrh    r0, [r1, r0]
    rsbs    r0, r0, #0              @ carry iff ACTIVE == 0
    pop     {pc}
active_offsets:
    .byte ACTIVE_1, ACTIVE_2, ACTIVE_3, ACTIVE_4, ACTIVE_5, ACTIVE_6, ACTIVE_7
    .align 2
