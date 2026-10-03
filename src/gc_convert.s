# The GameCube pad -> Wii Remote + Nunchuk conversion shared by the sampling-callback
# hook and the remote-less sample generator.  Assembled with
#   CHAN = register holding channel number, SMP = register holding sample pointer
# and ends at local label 9. Scratch: r0, r4-r12.

    cmplwi  CHAN, 3
    bgt     9f
    mulli   5, CHAN, 12
    lis     6, 0xCD00
    add     6, 6, 5

    # Ensure hardware auto-polling is turned on
    lis     4, 0x0040
    ori     4, 4, 0x0300
    stw     4, 0x6400(6)                # SIC<n>OUTBUF = poll command
    lis     4, 0x8000
    stw     4, 0x6438(6)                # SISR = 0x80000000 (WR latch)
    lwz     4, 0x6430(6)                # SIPOLL
    ori     4, 4, 0x00F0                # poll enable channels 0-3
    stw     4, 0x6430(6)

    lwz     8, 0x6404(6)                # INBUFH
    cmpwi   8, 0
    blt     9f                          # error / no pad
    andis.  9, 8, 0x0080
    beq     9f                          # not a pad response
    lbz     4, 0x29(SMP)
    cmplwi  4, 0
    bne     9f                          # only a good sample

    lwz     12, 0x6408(6)               # INBUFL
    srwi    5, 8, 16                    # PAD buttons (r5 for mapbit)

    # Check analog triggers: if pressed past threshold, set button bits
    rlwinm  4, 12, 24, 24, 31           # L analog byte
    cmplwi  4, 40
    blt     1f
    ori     5, 5, PAD_L
1:  rlwinm  4, 12, 0, 24, 31            # R analog byte
    cmplwi  4, 40
    blt     2f
    ori     5, 5, PAD_R
2:
    # Sticks: 0-255 with center ~128 -> signed displacement
    rlwinm  10, 8, 24, 24, 31
    addi    10, 10, -128                # Control stick X
    rlwinm  11, 8, 0, 24, 31
    addi    11, 11, -128                # Control stick Y
    rlwinm  8, 12, 8, 24, 31
    addi    8, 8, -128                  # C stick X
    rlwinm  9, 12, 16, 24, 31
    addi    9, 9, -128                  # C stick Y

    lhz     6, 0x00(SMP)                # existing Wii Remote buttons
    li      7, 0

    mapbit  PAD_A,     WM_A             # Jump
    mapbit  PAD_B,     WM_Z             # Crouch / Ground Pound
    mapbit  PAD_X,     WM_SHAKE         # Spin Attack
    mapbit  PAD_Y,     WM_SHAKE         # Spin Attack
    mapbit  PAD_Z,     WM_B             # Shoot Star Bits / Trigger
    mapbit  PAD_L,     WM_Z             # Crouch / Long Jump
    mapbit  PAD_R,     WM_Z             # Crouch / Long Jump
    mapbit  PAD_START, WM_PLUS          # Pause
    mapbit  PAD_UP,    WM_UP            # Camera Up
    mapbit  PAD_DOWN,  WM_DOWN          # Camera Down
    mapbit  PAD_LEFT,  WM_LEFT          # Camera Left
    mapbit  PAD_RIGHT, WM_RIGHT         # Camera Right

    or      6, 6, 7
    sth     6, 0x00(SMP)

    # Control stick (+-100) -> Nunchuk stick (+-71 is full deflection)
    mulli   10, 10, 205
    srawi   10, 10, 8
    clamp   10, 127
    mulli   11, 11, 205
    srawi   11, 11, 8
    clamp   11, 127

    # C-stick pointer in 1/1000ths
    dead    8, 8
    mulli   8, 8, 10
    clamp   8, 1000
    dead    9, 8
    mulli   9, 9, 10
    clamp   9, 1000

    li      0, 1
    stb     0, 0x28(SMP)                # device: Nunchuk
    li      0, 4
    stb     0, 0x40(SMP)                # data format: Nunchuk buttons + accel
    stb     10, 0x30(SMP)               # stick X
    stb     11, 0x31(SMP)               # stick Y
    sth     8, 0x2a(SMP)                # pointer X (1/1000ths)
    sth     9, 0x2c(SMP)                # pointer Y (1/1000ths)
    lbz     0, 0x41(SMP)
    ori     0, 0, 2
    stb     0, 0x41(SMP)                # marker bit 1: GameCube pointer
9:
