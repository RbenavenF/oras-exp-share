@ SUPERSEDED 2026-11-10 by frontier/asm/pike.s pike_wild/pike_rival/pike_level (competitor stays 2). Kept as a record.
@ Size-only candidate, NOT linked into the production patch or installed in Azahar.
@ WORK 16675 is provisional, NOT reserved: 0 normal, 209..214 = custom set index + 1.
@ A complete integration still needs guarded sites, appended sets, script/VM tests,
@ no-capture validation, and regression. Never treat assembly size as runtime evidence.
.syntax unified
.arm
.section .text
.global candidate_wild
candidate_wild:                    @ r0 facility work -> r0 encoded set, zero outside Pike
    ldr ip, [r0, #0xb78]
    ldr ip, [ip, #0x1c]
    ldr ip, [ip]
    add ip, ip, #0x13000
    add ip, ip, #0x144
    ldrh r0, [ip, #(2*(WORK_ROUTE-0x4000))]
    cmp r0, #PIKE_ROUTE
    addeq ip, ip, #0x200
    ldrheq r0, [ip, #0x46]
    movne r0, #0
    cmp r0, #0
    bx lr

.global candidate_start
candidate_start:                   @ reached from palace_start's last two instructions
    push {r3, lr}
    mov r0, r4
    bl candidate_wild
    movne r0, #0
    strbne r0, [r4, #0x620]         @ wild competitor, no trainer capture semantics
    movne r0, #1
    strbne r0, [r4, #0x6d3]         @ setup+0xb3: no experience (capture still unmeasured)
    pop {r3, lr}
    mov r0, r5
    b ARENA_START_RESUME

.global candidate_count
candidate_count:                   @ appended to dome_count before its bx lr
    push {r0, lr}
    mov r0, r5
    bl candidate_wild
    movne r6, #1
    pop {r0, pc}

.global candidate_set
candidate_set:                     @ inserted in rival_hook with r0=&work[0x4000], r1=route
    @ Entered ONLY from route 6, by a new beq after rival_hook's existing route read.
    add ip, r0, #0x200
    ldrh r1, [ip, #0x46]
    cmp r1, #0
    subne r4, r1, #1
    movne r2, #ARCHIVE_NORMAL
    bx lr                         @ conditional caller continues the existing hook on zero

.global candidate_level
candidate_level:                   @ hook code.bin 0x1e4e80: mov r1,#50 (r0 dead until +4)
    push {r3, lr}
    mov r0, fp
    bl candidate_wild
    mov r1, #50
    cmp r0, #209
    movhs r1, #46
    cmp r0, #211
    movhs r1, #45
    pop {r3, pc}
