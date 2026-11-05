@ Arena B engine experiment (reports/frontier.md §31).
@ Pure Cuerpo judge only, not linked into the release patch yet: M1 and the CRO
@ bridge must be finished before enabling the engine hooks. No game state writes.
    .syntax unified
    .arm
    .section .text

@ r0/r1 = player's current/entry HP; r2/r3 = opponent's current/entry HP.
@ Compare floor(100 * current / entry), as Cuerpo's integer percentages.
@ Return a fainting mask: 1 player loses, 2 opponent loses, 3 both (tie).
@ Missing entry HP (zero) returns 0: never faint anyone with an invalid snapshot.
@ ARENA_UDIV = code.bin 0x15ec10 (DllBattle import thunk 0x420, literal 0x424).
    .global arena_judge
arena_judge:
    push    {r3-r7, lr}
    mov     r4, r2
    mov     r5, r3
    cmp     r1, #0
    cmpne   r5, #0
    moveq   r0, #0
    beq     1f
    mov     r7, #100
    mul     r0, r7, r0
    bl      ARENA_UDIV
    mov     r6, r0
    mul     r0, r7, r4
    mov     r1, r5
    bl      ARENA_UDIV
    cmp     r6, r0
    mov     r0, #3
    movhi   r0, #2
    movlo   r0, #1
1:
    pop     {r3-r7, pc}
