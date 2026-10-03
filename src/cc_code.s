# Super Mario Galaxy 2: Classic Controller routines
# Injected into scratch cave (CC_BASE)

.global cc_get_status
cc_get_status:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    bl      GET_CONTROLLER_STATUS
    bl      cc_get_ext
    lwz     0, 20(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_get_ext
cc_get_ext:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    lwz     3, 4(3)
    lwz     3, 0(3)
    lbz     0, 95(3)
    li      3, 0
    cmpwi   0, 8
    beq     1f
    cmpwi   0, 5
    beq     2f
    b       3f
2:  li      3, 1
    b       3f
1:  li      3, 2
3:  lwz     0, 20(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_button_copy
cc_button_copy:
    lbz     0, 92(6)
    cmpwi   0, 2
    mflr    14
    bne     1f
    lwz     0, 96(6)
    bl      cc_remap
    stw     0, 0(5)
    lwz     0, 100(6)
    bl      cc_remap
    stw     0, 4(5)
    lwz     0, 104(6)
    bl      cc_remap
    stw     0, 8(5)
    b       2f
1:  lwz     0, 0(6)
    stw     0, 0(5)
    lwz     0, 4(6)
    stw     0, 4(5)
    lwz     0, 8(6)
    stw     0, 8(5)
2:  mtlr    14
    lis     12, COPY_BTN_RET@ha
    addi    12, 12, COPY_BTN_RET@l
    mtctr   12
    bctr

.global cc_remap
cc_remap:
    li      11, 0
    andi.   12, 0, 0x2000       # CC_L -> WM_C
    cmpwi   12, 0
    beq     1f
    ori     11, 11, 0x4000
1:  andi.   12, 0, 0x0200       # CC_R -> WM_B
    cmpwi   12, 0
    beq     2f
    ori     11, 11, 0x0400
2:  andi.   12, 0, 0x0080       # CC_ZL -> WM_Z
    cmpwi   12, 0
    beq     3f
    ori     11, 11, 0x2000
3:  andi.   12, 0, 0x0004       # CC_ZR -> WM_A
    cmpwi   12, 0
    beq     4f
    ori     11, 11, 0x0800
4:  andi.   12, 0, 0x0010       # CC_a -> WM_A
    cmpwi   12, 0
    beq     5f
    ori     11, 11, 0x0800
5:  andi.   12, 0, 0x0040       # CC_b -> WM_B
    cmpwi   12, 0
    beq     6f
    ori     11, 11, 0x0400
6:  andi.   12, 0, 0x0020       # CC_y -> WM_C
    cmpwi   12, 0
    beq     7f
    ori     11, 11, 0x4000
7:  andi.   12, 0, 0x0008       # CC_x -> WM_SHAKE (Spin)
    cmpwi   12, 0
    beq     8f
    ori     11, 11, 0x0020
8:  andi.   12, 0, 0x0001       # CC_UP -> WM_UP
    cmpwi   12, 0
    beq     9f
    ori     11, 11, 0x0008
9:  andi.   12, 0, 0x0002       # CC_LEFT -> WM_LEFT
    cmpwi   12, 0
    beq     10f
    ori     11, 11, 0x0001
10: andi.   12, 0, 0x8000       # CC_RIGHT -> WM_RIGHT
    cmpwi   12, 0
    beq     11f
    ori     11, 11, 0x0002
11: andi.   12, 0, 0x4000       # CC_DOWN -> WM_DOWN
    cmpwi   12, 0
    beq     12f
    ori     11, 11, 0x0004
12: andi.   12, 0, 0x0400       # CC_PLUS -> WM_PLUS
    cmpwi   12, 0
    beq     13f
    ori     11, 11, 0x0010
13: andi.   12, 0, 0x1000       # CC_MINUS -> WM_MINUS
    cmpwi   12, 0
    beq     14f
    ori     11, 11, 0x1000
14: andi.   12, 0, 0x0800       # CC_HOME -> WM_HOME
    cmpwi   12, 0
    beq     15f
    ori     11, 11, 0x8000
15: mr      0, 11
    blr

.global cc_left_stick
cc_left_stick:
    lbz     0, 92(6)
    cmpwi   0, 2
    beq     1f
    lwz     9, 4(11)
    lwzu    0, 8(11)
    lis     12, STICK_RET@ha
    addi    12, 12, STICK_RET@l
    mtctr   12
    bctr
1:  lwz     9, 16(11)
    lwzu    0, 20(11)
    stw     9, 4(12)
    stwu    0, 8(12)
    xoris   9, 9, 0x8000
    xoris   0, 0, 0x8000
    stw     9, 4(12)
    stwu    0, 8(12)
    xoris   9, 9, 0x8000
    xoris   0, 0, 0x8000
    stwu    0, 4(12)
    lis     12, STICK_RET@ha
    addi    12, 12, STICK_RET@l
    mtctr   12
    bctr

.global cc_ui1
cc_ui1:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    stw     31, 12(1)
    bl      GET_CONTROLLER_STATUS
    mr      31, 3
    lwz     3, 20(31)
    lbz     3, 12(3)
    cmpwi   3, 1
    beq     1f
    lwz     3, 8(31)
    lwz     0, 4(3)
    rlwinm  3, 0, 27, 31, 31
1:  lwz     0, 20(1)
    lwz     31, 12(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_ui2
cc_ui2:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    stw     31, 12(1)
    bl      GET_CONTROLLER_STATUS
    mr      31, 3
    lwz     3, 20(31)
    lbz     3, 24(3)
    cmpwi   3, 1
    beq     1f
    lwz     3, 8(31)
    lwz     0, 4(3)
    rlwinm  3, 0, 27, 31, 31
1:  lwz     0, 20(1)
    lwz     31, 12(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_ui3
cc_ui3:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    stw     31, 12(1)
    bl      GET_CONTROLLER_STATUS
    mr      31, 3
    bl      cc_get_ext
    cmpwi   3, 2
    beq     1f
    lwz     3, 40(31)
    lbz     3, 12(3)
    b       2f
1:  lwz     3, 8(31)
    lwz     0, 4(3)
    rlwinm  3, 0, 27, 31, 31
2:  lwz     0, 20(1)
    lwz     31, 12(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_ui4
cc_ui4:
    li      3, 0
    bl      cc_get_status
    cmpwi   3, 2
    lbz     31, 4110(30)
    bne     1f
    li      31, 0
1:  lis     12, UI4_RET@ha
    addi    12, 12, UI4_RET@l
    mtctr   12
    bctr

.global cc_ui5
cc_ui5:
    li      3, 0
    bl      cc_get_status
    cmpwi   3, 2
    beq     1f
    bl      UI5_CALL
    lis     12, UI5_RET1@ha
    addi    12, 12, UI5_RET1@l
    mtctr   12
    bctr
1:  lis     12, UI5_RET2@ha
    addi    12, 12, UI5_RET2@l
    mtctr   12
    bctr

.global cc_pointer_check
cc_pointer_check:
    stwu    1, -16(1)
    mflr    0
    stw     0, 20(1)
    stw     31, 12(1)
    mr      31, 3
    lbz     3, 20(31)
    cmpwi   3, 0
    bne     1f
    lbz     3, 8(31)
    bl      cc_get_status
    cmpwi   3, 2
    li      3, 0
    bne     1f
    li      3, 1
1:  lwz     0, 20(1)
    lwz     31, 12(1)
    mtlr    0
    addi    1, 1, 16
    blr

.global cc_pointer_math
cc_pointer_math:
    lbz     0, 95(6)
    cmpwi   0, 8
    beq     1f
    lwz     0, 36(6)
    lwz     9, 32(6)
    stw     9, 32(5)
    stw     0, 36(5)
    lis     12, PTR_MATH_RET@ha
    addi    12, 12, PTR_MATH_RET@l
    mtctr   12
    bctr
1:  lfs     0, 32(5)
    lfs     15, 116(6)
    lis     9, cc_floats@ha
    addi    9, 9, cc_floats@l
    lfs     14, 0(9)
    fdivs   15, 15, 14
    fadds   1, 0, 15
    lfs     2, 4(9)
    lfs     3, 8(9)
    bl      CLAMP
    stfs    1, 32(5)
    lfs     0, 36(5)
    lfs     15, 120(6)
    lis     9, cc_floats@ha
    addi    9, 9, cc_floats@l
    lfs     14, 0(9)
    fdivs   15, 15, 14
    fsubs   1, 0, 15
    lfs     2, 4(9)
    lfs     3, 8(9)
    bl      CLAMP
    stfs    1, 36(5)
    lis     12, PTR_MATH_RET@ha
    addi    12, 12, PTR_MATH_RET@l
    mtctr   12
    bctr

.global cc_pointer_valid
cc_pointer_valid:
    lbz     0, 95(6)
    cmpwi   0, 8
    lbz     0, 94(6)
    bne     1f
    li      0, 2
1:  lis     12, PTR_VALID_RET@ha
    addi    12, 12, PTR_VALID_RET@l
    mtctr   12
    bctr

.global cc_pointer_update
cc_pointer_update:
    lwz     3, 64(31)
    bl      cc_get_status
    cmpwi   3, 2
    bne     1f
    lis     12, PTR_UPDATE_RET1@ha
    addi    12, 12, PTR_UPDATE_RET1@l
    mtctr   12
    bctr
1:  lwz     0, 52(31)
    lis     12, PTR_UPDATE_RET2@ha
    addi    12, 12, PTR_UPDATE_RET2@l
    mtctr   12
    bctr

.align 4
cc_floats:
    .float 20.0
    .float -1.0
    .float 1.0
