@ Battle Dome v1 (frontier/dome.py, reports/diseno/domo.md) in the Battle Maison's party builders. Everything here
@ only acts while saved work WORK_ROUTE = DOME_ROUTE (the Dome's challenge; frontier/patch.py STREAK_ROUTES), so the
@ Maison, the Factory and the Tower keep their behaviour. Saved work N is at &work[0x4000] + 2*(N - 0x4000).
    .syntax unified
    .arm
    .section .text

@ Add a constant that is not an ARM immediate (bits 8-15, then 0-7).
    .macro ADDW reg, value
    add     \reg, \reg, #((\value) & 0xff00)
    add     \reg, \reg, #((\value) & 0xff)
    .endm

@ Player party: called by rental_hook's retail branch after PARTY_PREPARE (0x3b5d34), r0 = facility work, r1 =
@ &work[WORK_ROUTE]. With the Dome's route, the selection becomes its two fighters for this battle, saved works
@ DOME_FIGHT0/1 (party slots the zone script chose from the three entered): work+0x30, +0x34 and the count
@ work+0x48 = 2, which the original copy loop (0x1e3da0, 0x1e3db4) reads next. Uses r0-r2 and the flags only.
    .global dome_party
dome_party:
    ldrh    r2, [r1]
    cmp     r2, #DOME_ROUTE
    bxne    lr
    ADDW    r1, (2 * (DOME_FIGHT0 - WORK_ROUTE))
    ldrh    r2, [r1]
    str     r2, [r0, #0x30]
    ldrh    r2, [r1, #2]
    str     r2, [r0, #0x34]
    mov     r2, #DOME_FIGHTERS
    str     r2, [r0, #0x48]
    bx      lr

@ Rival party: jumped to by rival_hook (rival builder 0x1e4a94 at 0x1e4b34) with r0 = &work[0x4000], r4 = the set
@ index drawn from the trainer's list, r7 = rival slot, lr = the builder. For slots 0..DOME_FIGHTERS-1 the set is
@ the zone script's forced one, saved work DOME_FORCED0 + r7: bits 0-9 index, bit 15 Super archive (0xb8; else
@ 0xb6). r4 = index and r2 = archive, the builder's third argument to the archive open at 0x1e4b48 (it reloads r2
@ from its stack for every slot, 0x1e4b30). The builder redraws a slot forever if its species repeats an earlier
@ slot's (0x1e4bdc): the script never forces two sets of one species. Uses r0, r1, r2, r4 and the flags.
    .global dome_rival
dome_rival:
    cmp     r7, #DOME_FIGHTERS
    bxge    lr
    ADDW    r0, (2 * (DOME_FORCED0 - 0x4000))
    add     r0, r0, r7, lsl #1
    ldrh    r1, [r0]
    tst     r1, #0x8000
    moveq   r2, #ARCHIVE_NORMAL
    movne   r2, #ARCHIVE_SUPER
    bic     r4, r1, #0xfc00
    bx      lr

@ Rival count: replaces `mov r6, #3` at 0x1e3548 (trainer party 0x1e3480, Singles row of its jump table on work+0x839;
@ r6 goes to the builder as the number of members and to the AddMember loop at 0x1e35b8). r5 = facility work. The
@ Dome's rival brings DOME_FIGHTERS. Uses ip and the flags (0x1e3568 sets them again).
    .global dome_count
dome_count:
    mov     r6, #3
    ldr     ip, [r5, #0xb78]
    ldr     ip, [ip, #0x1c]
    ldr     ip, [ip]                @ save data
    add     ip, ip, #0x13000
    add     ip, ip, #0x144
    ldrh    ip, [ip, #(2 * (WORK_ROUTE - 0x4000))]
    cmp     ip, #DOME_ROUTE
    moveq   r6, #DOME_FIGHTERS
    bx      lr
