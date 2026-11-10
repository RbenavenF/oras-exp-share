@ Battle Palace stage C (reports/frontier.md §36): the nature picks a move group each turn and the AI of the
@ player's Pokemon may only choose a move of that group (pokeemerald 731ad5bf ChooseMoveAndTargetInBattlePalace).
@
@ Linked at its DllBattle.cro FILE offset (PALACE_CRO_AT, the zero padding of the declared code region between
@ the end of .text 0xd7628 and .rodata 0xd8000), so the `bl`s to CRO functions are plain relative branches and
@ the code does not depend on where the CRO is loaded. Only code.bin addresses are absolute (no ASLR).
@
@ Called from CRO 0xd468 (AI proc of command 3, 0xd0c8) instead of `bl 0xe044`:
@   0xe044(client r0, BattleMon r1, u8 usable[4] r2) -> first usable slot, or 4 if none (then Struggle).
@ The caller copies usable[] to AI+0x198; the AI scripts skip slots with 0 there (0xa88c0) and the fallback
@ chooser 0xa9438 also picks among them. Clearing a slot is therefore "the AI may not choose it".
@
@ Only for the Palace's client 0 (ident 0, thinker 0 = the UI client that gets an AI object, palace.s) with
@ setup+0xa8 bit 30. Everything else returns the retail result untouched. The rival is client 1 (thinker 1).
    .syntax unified
    .arm
    .section .text

    .global palace_moves
palace_moves:
    push    {r4-r10, lr}
    mov     r4, r0                  @ client
    mov     r5, r1                  @ BattleMon
    mov     r6, r2                  @ usable[4]
    bl      CRO_USABLE_MOVES
    mov     r9, r0                  @ retail result, returned as is
    cmp     r9, #4
    beq     9f                      @ nothing usable: retail Struggle
    ldrb    r0, [r4, #0x91]
    ldrb    r1, [r4, #0x90]
    orrs    r0, r0, r1              @ thinker 0 (UI) and client 0
    bne     9f
    ldr     r0, [r4]                @ BattleMain
    ldr     r0, [r0, #0x10]         @ BattleSetup
    ldr     r0, [r0, #0xa8]
    tst     r0, #PALACE_RULE
    beq     9f

    mov     r0, #100
    bl      CRO_RAND                @ rand(100), the AI's own generator (thunk -> code 0x48ad84)
    mov     r8, r0                  @ percent
    ldr     r0, [r5]                @ PokemonParam (as CRO 0x50fe4 does for the berries)
    ldr     r0, [r0, #0xc]          @ CoreParam
    ldr     ip, =CODE_NATURE        @ code.bin CoreParam nature getter (PK6 0x1C)
    blx     ip
    cmp     r0, #NATURES
    movhs   r0, #0
    adr     r1, palace_nature_odds
    add     r1, r1, r0, lsl #2
    ldrh    r2, [r5, #0x10]         @ HP
    ldrh    r3, [r5, #0xe]          @ max HP
    cmp     r2, r3, lsr #1          @ Emerald: maxHP / 2 >= hp -> second column
    addls   r1, r1, #2
    ldrb    r2, [r1]                @ attack below this
    ldrb    r3, [r1, #1]            @ defense below this, support from here
    mov     r7, #0
    cmp     r8, r2
    movhs   r7, #1
    cmphs   r8, r3
    movhs   r7, #2                  @ r7 = drawn group

    mov     r10, #0                 @ kept mask
    mov     r3, #0                  @ slot
1:
    ldrb    r0, [r6, r3]
    cmp     r0, #0
    beq     2f
    rsb     r0, r3, r3, lsl #3
    add     r0, r5, r0, lsl #1
    add     r0, r0, #0x100
    ldrh    r0, [r0, #0x1c]         @ move id of the slot (as 0xa9274, 0xd774)
    bl      palace_group
    cmp     r0, r7
    moveq   r0, #1
    orreq   r10, r10, r0, lsl r3
2:
    add     r3, r3, #1
    cmp     r3, #4
    blo     1b
    cmp     r10, #0
    beq     9f                      @ no usable move of the group: another group (all usable ones stay)
    mov     r3, #0
    mov     r1, #0
3:
    mov     r0, #1
    tst     r10, r0, lsl r3
    strbeq  r1, [r6, r3]
    add     r3, r3, #1
    cmp     r3, #4
    blo     3b
9:
    mov     r0, r9
    pop     {r4-r10, pc}

@ r0 move id -> r0 group (0 attack, 1 defense, 2 support). Ids past the table: attack. Keeps r1-r3.
    .global palace_group
palace_group:
    cmp     r0, #((MOVES + 3) / 4 * 4)   @ table size; the padding ids read attack
    movhs   r0, #0
    bxhs    lr
    adr     ip, palace_move_groups
    ldrb    ip, [ip, r0, lsr #2]
    and     r0, r0, #3
    lsl     r0, r0, #1
    lsr     r0, ip, r0
    and     r0, r0, #3
    bx      lr

    .ltorg
    .balign 4
    .global palace_nature_odds
palace_nature_odds:                 @ NATURES x {attack, attack+defense} for HP > 1/2, then for HP <= 1/2
    .space  NATURES * 4
    .global palace_move_groups
palace_move_groups:                 @ 2 bits per move id, low bits first
    .space  (MOVES + 3) / 4
    .balign 4
    .global palace_cro_end
palace_cro_end:
