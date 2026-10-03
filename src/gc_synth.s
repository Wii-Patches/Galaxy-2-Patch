# hook: KPADReadEx ring count check, `lbz r0,0x17b(r21)`
# (r21 = channel KPAD struct, r25 = channel number).
#
# If the ring is empty and a GameCube pad answers on the matching port, synthesize
# a sample into the ring buffer right here and notify the game of the controller.
    lbz     0, 0x17b(21)
    cmpwi   0, 0
    bne     9f                          # samples already waiting from a Wii Remote

    cmplwi  25, 3
    bgt     9f

    lbz     0, 0x17a(21)                # next write index
    cmplwi  0, 16
    blt     1f
    li      0, 0
1:
    mulli   3, 0, 0x42
    add     3, 3, 21
    addi    3, 3, 0x180                 # address of the next ring slot

    # Zero the sample slot
    li      0, 0
    stw     0, 0x00(3)
    stw     0, 0x04(3)
    stw     0, 0x08(3)
    stw     0, 0x0c(3)
    stw     0, 0x10(3)
    stw     0, 0x14(3)
    stw     0, 0x18(3)
    stw     0, 0x1c(3)
    stw     0, 0x20(3)
    stw     0, 0x24(3)
    stw     0, 0x28(3)
    stw     0, 0x2c(3)
    stw     0, 0x30(3)
    stw     0, 0x34(3)
    stw     0, 0x38(3)
    stw     0, 0x3c(3)
    sth     0, 0x40(3)

    li      0, 0x68
    sth     0, 0x06(3)                  # accelerometer flat at rest

    .set    CHAN, 25
    .set    SMP, 3
#include gc_convert.s

    lbz     0, 0x41(3)
    andi.   0, 0, 2
    beq     9f                          # no pad answered

    # Advance ring write index
    lbz     5, 0x17a(21)
    addi    5, 5, 1
    cmplwi  5, 16
    blt     2f
    li      5, 0
2:  stb     5, 0x17a(21)

    # Set sample count to 1
    li      5, 1
    stb     5, 0x17b(21)

    # Fire connect callback once so SMG2 recognizes the controller
    lwz     12, 0x5f8(21)
    cmpwi   12, 0
    beq     9f
    lbz     0, 0x646(21)
    cmpwi   0, 0
    bne     9f
    li      0, 1
    stb     0, 0x646(21)
    mr      3, 25
    li      4, 0
    mtctr   12
    bctrl

9:
    lbz     0, 0x17b(21)                # displaced instruction
