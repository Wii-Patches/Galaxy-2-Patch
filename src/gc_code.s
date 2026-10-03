# Super Mario Galaxy 2: GameCube Controller routines
# Injected into scratch cave (GC_BASE)

.global gc_kpad_read_hook
gc_kpad_read_hook:
    # Check if channel is 0..3
    cmplwi  28, 3
    bgt     9f

    # Ensure hardware auto-polling is active for port r28
    lis     6, 0xCD00                   # r6 = 0xCD000000 base IO
    mulli   5, 28, 12                   # r5 = chan * 12
    add     7, 6, 5                     # r7 = 0xCD006400 + chan * 12
    lis     8, 0x0040
    ori     8, 8, 0x0300
    stw     8, 0x6400(7)                # SIC<chan>OUTBUF
    lis     8, 0x8000
    stw     8, 0x6438(6)                # SISR WR latch (at 0xCD006438)
    lwz     8, 0x6430(6)                # SIPOLL (at 0xCD006430)
    ori     8, 8, 0x00F0
    stw     8, 0x6430(6)

    # Read SI input buffer
    lwz     8, 0x6404(7)                # INBUFH (buttons + main stick)
    cmpwi   8, 0
    blt     9f                          # error or no controller
    andis.  0, 8, 0x0080
    beq     9f                          # not a standard GC pad

    # GameCube controller is active!
    # Retrieve KPADStatus buffer pointer for this channel:
    lwz     12, 12(27)
    lwzx    4, 31, 12                   # r4 = KPADStatus buffer

    lwz     9, 0x6408(7)                # INBUFL (C-stick + triggers)

    # Decode and map buttons
    srwi    5, 8, 16                    # raw GC buttons
    # Check analog L trigger (threshold > 40)
    rlwinm  7, 9, 24, 24, 31
    cmplwi  7, 40
    blt     1f
    ori     5, 5, 0x0040                # PAD_L
1:  # Check analog R trigger (threshold > 40)
    rlwinm  7, 9, 0, 24, 31
    cmplwi  7, 40
    blt     2f
    ori     5, 5, 0x0020                # PAD_R
2:
    li      10, 0                       # mapped CC buttons

    andi.   0, 5, 0x0100                # PAD_A (Jump)
    beq     1f
    ori     10, 10, 0x0010              # CC_a
1:  andi.   0, 5, 0x0200                # PAD_B (Crouch / Ground Pound)
    beq     1f
    ori     10, 10, 0x0040              # CC_b
1:  andi.   0, 5, 0x0400                # PAD_X (Spin Attack)
    beq     1f
    ori     10, 10, 0x0008              # CC_x
1:  andi.   0, 5, 0x0800                # PAD_Y (Spin Attack)
    beq     1f
    ori     10, 10, 0x0008              # CC_x
1:  andi.   0, 5, 0x0010                # PAD_Z (Star Bits / Shoot)
    beq     1f
    ori     10, 10, 0x0004              # CC_ZR
1:  andi.   0, 5, 0x1000                # PAD_START (Pause)
    beq     1f
    ori     10, 10, 0x0400              # CC_PLUS
1:  andi.   0, 5, 0x0008                # PAD_UP (Camera)
    beq     1f
    ori     10, 10, 0x0001              # CC_UP
1:  andi.   0, 5, 0x0004                # PAD_DOWN (Camera)
    beq     1f
    ori     10, 10, 0x4000              # CC_DOWN
1:  andi.   0, 5, 0x0001                # PAD_LEFT (Camera)
    beq     1f
    ori     10, 10, 0x0002              # CC_LEFT
1:  andi.   0, 5, 0x0002                # PAD_RIGHT (Camera)
    beq     1f
    ori     10, 10, 0x8000              # CC_RIGHT
1:  andi.   0, 5, 0x0040                # PAD_L (Crouch / Long Jump)
    beq     1f
    ori     10, 10, 0x0080              # CC_ZL
1:  andi.   0, 5, 0x0020                # PAD_R (Crouch / Long Jump)
    beq     1f
    ori     10, 10, 0x2000              # CC_L
1:
    # Merge mapped buttons into KPADStatus cl.hold (0x60)
    lwz     0, 0x60(4)
    or      0, 0, 10
    stw     0, 0x60(4)

    # Sticks via float lookup table:
    lis     12, gc_stick_table@ha
    addi    12, 12, gc_stick_table@l

    # Control stick X (byte 2 of INBUFH):
    rlwinm  5, 8, 24, 24, 31
    slwi    5, 5, 2
    lwzx    0, 12, 5
    stw     0, 0x6C(4)                  # cl.lstick.x

    # Control stick Y (byte 3 of INBUFH):
    rlwinm  7, 8, 0, 24, 31
    slwi    7, 7, 2
    lwzx    0, 12, 7
    stw     0, 0x70(4)                  # cl.lstick.y

    # C-stick X (byte 1 of INBUFL):
    rlwinm  10, 9, 8, 24, 31
    slwi    10, 10, 2
    lwzx    0, 12, 10
    stw     0, 0x74(4)                  # cl.rstick.x

    # C-stick Y (byte 2 of INBUFL):
    rlwinm  11, 9, 16, 24, 31
    slwi    11, 11, 2
    lwzx    0, 12, 11
    stw     0, 0x78(4)                  # cl.rstick.y

    # Mark controller as Classic Controller format so SMG2 processes it
    li      0, 2
    stb     0, 92(4)                    # dev = 2 (Classic Controller)
    li      0, 8
    stb     0, 95(4)                    # data_format = 8 (WPAD_FMT_CLASSIC)
    li      0, 2
    stb     0, 94(4)                    # dpd_valid = 2

    # Set sample count to 1 if no Wiimote produced samples
    cmpwi   3, 1
    bge     9f
    li      3, 1

9:  # Execute displaced instruction: addi r28, r28, 1
    addi    28, 28, 1
    # Return to loop at 0x804CF888 (stw r3, 4(r29))
    lis     12, KPAD_READ_RET@ha
    addi    12, 12, KPAD_READ_RET@l
    mtctr   12
    bctr

.global gc_probe_hook
gc_probe_hook:
    stwu    1, -0x20(1)
    mflr    0
    stw     0, 0x24(1)
    stw     3, 0x08(1)                  # save channel
    stw     4, 0x0c(1)                  # save p_ext

    # Run real WPADProbe: displaced instruction stwu r1,-16(r1)
    stwu    1, -16(1)
    lis     12, WPAD_PROBE_BODY@ha
    addi    12, 12, WPAD_PROBE_BODY@l
    mtctr   12
    bctrl

    cmpwi   3, 0
    beq     1f                          # Wiimote is connected!

    # No Wiimote: check GameCube controller on this channel
    lwz     5, 0x08(1)                  # channel
    cmplwi  5, 3
    bgt     1f
    mulli   5, 5, 12
    lis     6, 0xCD00
    add     6, 6, 5
    lwz     7, 0x6404(6)                # INBUFH
    cmpwi   7, 0
    blt     1f
    andis.  0, 7, 0x0080
    beq     1f

    # GC pad connected! Report connected with Classic Controller extension
    li      3, 0                        # WPAD_ERR_NONE (connected)
    lwz     4, 0x0c(1)
    cmpwi   4, 0
    beq     1f
    li      0, 2                        # extension type 2 (Classic Controller)
    stw     0, 0(4)

1:  lwz     0, 0x24(1)
    addi    1, 1, 0x20
    mtlr    0
    blr

.align 4
.global gc_stick_table
gc_stick_table:
    # 256 pre-computed float values generated by gen_gc.py
