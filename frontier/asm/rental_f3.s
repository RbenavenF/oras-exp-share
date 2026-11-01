@ F3 prototype: the Battle Maison battle party is built from fixed rental sets instead of the player's party.
@ Called from the player-party branch of the party builder (code.bin 0x1e3d8c, reports/frontier.md §4/§8)
@ with r0 = facility work, r1 = the new battle PokeParty. Adds work+0x48 (selection count) rentals.
@ Game functions are passed by frontier/f3_patch.py with --defsym (addresses measured in F1/F3).
    .syntax unified
    .arm
    .section .text
    .global rental_hook

rental_hook:
    push    {r4-r8, lr}
    sub     sp, sp, #0x18           @ [sp] ability, [sp+4] u16 spec+0x1e, [sp+8] 16-byte set
    mov     r4, r0                  @ work
    mov     r5, r1                  @ battle party
    ldr     r7, [r4, #0x48]         @ selection count
    cmp     r7, #6
    movgt   r7, #6
    mov     r6, #0
1:
    cmp     r6, r7
    bge     3f
    ldr     r0, [r4, #0xb70]        @ heap
    mov     r1, #SET_ARCHIVE
    adr     r2, rental_sets
    add     r2, r2, r6, lsl #1
    ldrh    r2, [r2]
    add     r3, sp, #8
    bl      LOAD_SET                @ (heap, archive, index, out)
    mvn     r0, #0                  @ ability slot -1: random (as the rival builder, 0x1e4e70)
    mov     r1, #0xff               @ spec+0x1e default (as the rival builder)
    str     r0, [sp]
    str     r1, [sp, #4]
    add     r0, sp, #8
    mov     r1, #RENTAL_LEVEL
    mov     r2, #RENTAL_IV
    ldr     r3, [r4, #0xb70]
    bl      MAKE_PARAM              @ (set, level, IV, heap, ability, u16) -> PokemonParam*
    movs    r8, r0
    beq     2f
    mov     r1, r8
    mov     r0, r5
    bl      ADD_MEMBER              @ PokeParty copies the Pokémon
    ldr     r1, [r8]
    ldr     r1, [r1, #8]
    mov     r0, r8
    blx     r1                      @ free the temporary, as the Multi partner path (0x1e35c4)
2:
    add     r6, r6, #1
    b       1b
3:
    add     sp, sp, #0x18
    pop     {r4-r8, pc}

    .balign 4
rental_sets:
    .hword  SET0, SET1, SET2, SET3, SET4, SET5
