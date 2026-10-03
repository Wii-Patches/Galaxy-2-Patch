# Shared assembler macros for the Super Mario Galaxy 2 controller patches.
# Scratch registers: r0 and r12.

# r7 |= DST if any SRC bit is set in r5 (the pad's button word)
.macro mapbit src, dst
    andi.   0, 5, \src
    beq     .Lm\@a
    ori     7, 7, \dst
.Lm\@a:
.endm

# dst = |src|
.macro absr dst, src
    srawi   12, \src, 31
    xor     \dst, \src, 12
    subf    \dst, 12, \dst
.endm

# clamp reg to [-lim, lim]
.macro clamp reg, lim
    cmpwi   \reg, \lim
    ble     .Lm\@a
    li      \reg, \lim
.Lm\@a:  cmpwi   \reg, -\lim
    bge     .Lm\@b
    li      \reg, -\lim
.Lm\@b:
.endm

# zero reg when |reg| < th
.macro dead reg, th
    absr    0, \reg
    cmplwi  0, \th
    bge     .Lm\@a
    li      \reg, 0
.Lm\@a:
.endm
