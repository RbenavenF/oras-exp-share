@ Battle Factory rentals in the Battle Maison party builder (code.bin 0x1e3d2c; reports/frontier.md §4, §8, §9).
@ Called from its player-party branch (0x1e3d8c) with r0 = facility work, r1 = the new battle PokeParty.
@
@ Saved work WORK_IV (Factory state) = 0: the original branch, unchanged: r8 = player party,
@   0x3b5d34(player party), return r0 = player party to 0x1e3d98 (the site moves it to r8 and the
@   original copy loop at 0x1e3da0 runs).
@ WORK_IV = 1..31: add the 3 rentals of saved works WORK_SET0..2 with that IV (whatever the player
@   selected), store 3 as the selection count (work+0x48) and continue at the builder's common tail
@   0x1e3ddc with r0 = 3, as the original loop does.
@ Rental work value: bit 15 = Super archive (0xb8), else Normal (0xb6); bits 10-11 = ability slot
@   (0-2; 3 = random, as the Maison rivals); bits 0-9 = set index.
@ Saved work N lives at [[[work+0xb78]+0x1c]] + 0x13144 + 2*(N - 0x4000) (WorkGet, code.bin 0x3fe118 /
@ 0x11fa90). Game functions and constants come from frontier/patch.py.
    .syntax unified
    .arm
    .section .text
    .global rental_hook

rental_hook:
    push    {r4-r8, lr}
    sub     sp, sp, #0x18           @ [sp] ability, [sp+4] u16 spec+0x1e, [sp+8] 16-byte set
    mov     r4, r0                  @ work
    mov     r5, r1                  @ battle party
    ldr     r0, [r4, #0xb78]
    ldr     r0, [r0, #0x1c]         @ game data
    ldr     r1, [r0]                @ save data
    add     r8, r1, #0x13000
    add     r8, r8, #(0x144 + 2 * (WORK_IV - 0x4000))   @ r8 = &work[WORK_IV]
    ldrh    r7, [r8]                @ IV, 0 = Factory inactive
    cmp     r7, #0
    bne     rentals

    ldr     r6, [r0, #0x14]         @ player party (original 0x1e3d94)
    mov     r0, r6
    bl      PARTY_PREPARE           @ original 0x1e3d9c
    mov     r0, r6
    add     sp, sp, #0x18
    pop     {r4-r8, pc}

rentals:
    mov     r6, #RENTALS
    str     r6, [r4, #0x48]         @ selection count
    mov     r6, #0
1:
    ldr     r0, [r4, #0x48]
    cmp     r6, r0
    bge     3f
    add     r2, r8, #2
    add     r2, r2, r6, lsl #1
    ldrh    r2, [r2]                @ rental work value
    tst     r2, #0x8000
    moveq   r1, #ARCHIVE_NORMAL
    movne   r1, #ARCHIVE_SUPER
    lsr     r0, r2, #10
    and     r0, r0, #3              @ ability slot (ARMv6K: no ubfx)
    cmp     r0, #3
    mvneq   r0, #0                  @ 3 -> -1: random among the three (as the rival builder, 0x1e4e70)
    str     r0, [sp]
    bic     r2, r2, #0xfc00
    ldr     r0, [r4, #0xb70]        @ heap
    add     r3, sp, #8
    bl      LOAD_SET                @ (heap, archive, index, out)
    mov     r1, #0xff               @ spec+0x1e = sex, 0xff as the rival builder (not fixed yet)
    str     r1, [sp, #4]
    add     r0, sp, #8
    mov     r1, #RENTAL_LEVEL
    ldrh    r2, [r8]                @ IV
    ldr     r3, [r4, #0xb70]
    bl      MAKE_PARAM              @ (set, level, IV, heap, ability, u16) -> PokemonParam*
    movs    r7, r0
    beq     2f
    mov     r1, r7
    mov     r0, r5
    bl      ADD_MEMBER              @ PokeParty copies the Pokémon
    ldr     r1, [r7]
    ldr     r1, [r1, #8]
    mov     r0, r7
    blx     r1                      @ free the temporary, as the Multi partner path (0x1e35c4)
2:
    add     r6, r6, #1
    b       1b
3:
    ldr     r0, [r4, #0x48]         @ count for the common tail
    add     sp, sp, #0x18
    pop     {r4-r8, lr}
    b       RESUME

@ Rival party builder 0x1e4a94, at 0x1e4b34 (original: ldrh r4, [r0, #4], the set index drawn from the trainer's
@ list for rival slot r7; fp = facility work). Called with bl from the site, so lr is the return (the builder
@ never uses lr). While the Factory is active, also store the index in saved work WORK_RIVAL + r7 (r7 < RENTALS):
@ a rejected draw is redrawn for the same r7 and overwrites it, so the last value is the accepted set. The
@ zone script offers these sets for the swap after a win. r0, r1 are free here (reloaded before use); r2, r3
@ and the flags are not touched before the builder sets them again.
    .global rival_hook
rival_hook:
    ldrh    r4, [r0, #4]
    cmp     r7, #RENTALS
    bxge    lr
    ldr     r0, [fp, #0xb78]
    ldr     r0, [r0, #0x1c]
    ldr     r0, [r0]                @ save data
    add     r0, r0, #0x13000
    add     r0, r0, #(0x144 + 2 * (WORK_IV - 0x4000))
    ldrh    r1, [r0]
    cmp     r1, #0
    bxeq    lr                      @ Factory inactive: retail behaviour
    add     r0, r0, #(2 * (WORK_RIVAL - WORK_IV))
    add     r0, r0, r7, lsl #1
    strh    r4, [r0]
    bx      lr
