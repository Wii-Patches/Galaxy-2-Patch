# hook: WPADProbe, the first instruction (r3 = channel, r4 = where to put extension type).
#
# Runs the real WPADProbe; if it says "no controller" (-1) and a GameCube pad answers
# on the matching port, report "connected, Nunchuk" instead.
    stwu    1, -0x20(1)
    mflr    0
    stw     0, 0x24(1)
    stw     3, 0x08(1)
    stw     4, 0x0c(1)
    stwu    1, -0x10(1)                 # displaced instruction
    lis     12, PROBE_BODY@ha
    addi    12, 12, PROBE_BODY@l
    mtctr   12
    bctrl                               # the rest of WPADProbe
    cmpwi   3, -1
    bne     9f
    lwz     5, 0x08(1)
    cmplwi  5, 3
    bgt     9f
    mulli   5, 5, 12
    lis     6, 0xCD00
    add     6, 6, 5
    lwz     7, 0x6404(6)                # INBUFH
    cmpwi   7, 0
    blt     9f                          # error / no pad
    andis.  0, 7, 0x0080
    beq     9f                          # not a pad response
    li      3, 0                        # connected!
    lwz     4, 0x0c(1)
    cmpwi   4, 0
    beq     9f
    li      0, 1
    stw     0, 0(4)                     # ... with extension type 1 (Nunchuk)
9:
    lwz     0, 0x24(1)
    addi    1, 1, 0x20
    mtlr    0
    blr
