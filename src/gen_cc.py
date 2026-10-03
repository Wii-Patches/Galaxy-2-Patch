"""Build the Classic Controller feature for Super Mario Galaxy 2."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asm
import gen_common as g
from layout import CC_BASE, CC_END
from ops import Blob, Feature, Hook, Patch, b_insn

SITES = {
    'SB4E01': dict(
        get_ctrl=0x804CFC50,
        btn_copy_ret=0x804CF5DC,
        stick_ret=0x804CF6C0,
        ui4_ret=0x803CDFD8,
        ui5_call=0x80488A50,
        ui5_ret1=0x80448398,
        ui5_ret2=0x804484DC,
        clamp=0x8002E750,
        ptr_math_ret=0x804CF628,
        ptr_valid_ret=0x804CF6A8,
        ptr_upd_ret1=0x8049DF80,
        ptr_upd_ret2=0x8049DF48,
        
        ui1_hook=0x8002A770,
        ui2_hook=0x8002A7D0,
        ui3_hook=0x8002A900,
        ui3_func=0x8002A930,
        ptr_check_hook=0x8005BCA0,
        ui4_hook=0x803CDFD4,
        ui_helper1=0x804307FC,
        ui_helper2=0x80432238,
        ui_helper3=0x80432250,
        ui_helper4=0x804407B8,
        ui_helper5=0x8044096C,
        ui_helper6=0x80440B94,
        ui5_hook=0x80448394,
        ptr_upd_hook=0x8049DF3C,
        ext_check=0x804CE3B0,
        btn_hook=0x804CF5D8,
        btn_skip=0x804CF5E4,
        ptr_math_hook=0x804CF61C,
        ptr_flag=0x804CF694,
        ptr_valid_hook=0x804CF6A4,
        stick_hook=0x804CF6BC,
        panic1=0x804B7D90,
        panic2=0x804B7E54,
        panic3=0x805B66B4,
    ),
    'SB4P01': dict(
        get_ctrl=0x804CFC50,
        btn_copy_ret=0x804CF5DC,
        stick_ret=0x804CF6C0,
        ui4_ret=0x803CDFD8,
        ui5_call=0x80488A50,
        ui5_ret1=0x80448398,
        ui5_ret2=0x804484DC,
        clamp=0x8002E750,
        ptr_math_ret=0x804CF628,
        ptr_valid_ret=0x804CF6A8,
        ptr_upd_ret1=0x8049DF80,
        ptr_upd_ret2=0x8049DF48,
        
        ui1_hook=0x8002A770,
        ui2_hook=0x8002A7D0,
        ui3_hook=0x8002A900,
        ui3_func=0x8002A930,
        ptr_check_hook=0x8005BCA0,
        ui4_hook=0x803CDFD4,
        ui_helper1=0x804307FC,
        ui_helper2=0x80432238,
        ui_helper3=0x80432250,
        ui_helper4=0x804407B8,
        ui_helper5=0x8044096C,
        ui_helper6=0x80440B94,
        ui5_hook=0x80448394,
        ptr_upd_hook=0x8049DF3C,
        ext_check=0x804CE3B0,
        btn_hook=0x804CF5D8,
        btn_skip=0x804CF5E4,
        ptr_math_hook=0x804CF61C,
        ptr_flag=0x804CF694,
        ptr_valid_hook=0x804CF6A4,
        stick_hook=0x804CF6BC,
        panic1=0x804B7D90,
        panic2=0x804B7E54,
        panic3=0x805B66B4,
    ),
    'SB4J01': dict(
        get_ctrl=0x804CFC50,
        btn_copy_ret=0x804CF5DC,
        stick_ret=0x804CF6C0,
        ui4_ret=0x803CDFD8,
        ui5_call=0x80488A50,
        ui5_ret1=0x80448398,
        ui5_ret2=0x804484DC,
        clamp=0x8002E750,
        ptr_math_ret=0x804CF628,
        ptr_valid_ret=0x804CF6A8,
        ptr_upd_ret1=0x8049DF80,
        ptr_upd_ret2=0x8049DF48,
        
        ui1_hook=0x8002A770,
        ui2_hook=0x8002A7D0,
        ui3_hook=0x8002A900,
        ui3_func=0x8002A930,
        ptr_check_hook=0x8005BCA0,
        ui4_hook=0x803CDFD4,
        ui_helper1=0x804307FC,
        ui_helper2=0x80432238,
        ui_helper3=0x80432250,
        ui_helper4=0x804407B8,
        ui_helper5=0x8044096C,
        ui_helper6=0x80440B94,
        ui5_hook=0x80448394,
        ptr_upd_hook=0x8049DF3C,
        ext_check=0x804CE3B0,
        btn_hook=0x804CF5D8,
        btn_skip=0x804CF5E4,
        ptr_math_hook=0x804CF61C,
        ptr_flag=0x804CF694,
        ptr_valid_hook=0x804CF6A4,
        stick_hook=0x804CF6BC,
        panic1=0x804B7D90,
        panic2=0x804B7E54,
        panic3=0x805B66B4,
    ),
    'SB4K01': dict(
        get_ctrl=0x804CFCE0,
        btn_copy_ret=0x804CF66C,
        stick_ret=0x804CF750,
        ui4_ret=0x803CDFD8,
        ui5_call=0x80488A60,
        ui5_ret1=0x80448398,
        ui5_ret2=0x804484DC,
        clamp=0x8002E750,
        ptr_math_ret=0x804CF6B8,
        ptr_valid_ret=0x804CF738,
        ptr_upd_ret1=0x8049DFF0,
        ptr_upd_ret2=0x8049DFB8,
        
        ui1_hook=0x8002A770,
        ui2_hook=0x8002A7D0,
        ui3_hook=0x8002A900,
        ui3_func=0x8002A930,
        ptr_check_hook=0x8005BCA0,
        ui4_hook=0x803CDFD4,
        ui_helper1=0x804307FC,
        ui_helper2=0x80432238,
        ui_helper3=0x80432250,
        ui_helper4=0x804407B8,
        ui_helper5=0x8044096C,
        ui_helper6=0x80440B94,
        ui5_hook=0x80448394,
        ptr_upd_hook=0x8049DFAC,
        ext_check=0x804CE440,
        btn_hook=0x804CF668,
        btn_skip=0x804CF674,
        ptr_math_hook=0x804CF6AC,
        ptr_flag=0x804CF724,
        ptr_valid_hook=0x804CF734,
        stick_hook=0x804CF74C,
        panic1=0x804B7E00,
        panic2=0x804B7EC4,
        panic3=0x805B67B4,
    ),
    'SB4W01': dict(
        get_ctrl=0x804CFCE0,
        btn_copy_ret=0x804CF66C,
        stick_ret=0x804CF750,
        ui4_ret=0x803CDFD8,
        ui5_call=0x80488A60,
        ui5_ret1=0x80448398,
        ui5_ret2=0x804484DC,
        clamp=0x8002E750,
        ptr_math_ret=0x804CF6B8,
        ptr_valid_ret=0x804CF738,
        ptr_upd_ret1=0x8049DFF0,
        ptr_upd_ret2=0x8049DFB8,
        
        ui1_hook=0x8002A770,
        ui2_hook=0x8002A7D0,
        ui3_hook=0x8002A900,
        ui3_func=0x8002A930,
        ptr_check_hook=0x8005BCA0,
        ui4_hook=0x803CDFD4,
        ui_helper1=0x804307FC,
        ui_helper2=0x80432238,
        ui_helper3=0x80432250,
        ui_helper4=0x804407B8,
        ui_helper5=0x8044096C,
        ui_helper6=0x80440B94,
        ui5_hook=0x80448394,
        ptr_upd_hook=0x8049DFAC,
        ext_check=0x804CE440,
        btn_hook=0x804CF668,
        btn_skip=0x804CF674,
        ptr_math_hook=0x804CF6AC,
        ptr_flag=0x804CF724,
        ptr_valid_hook=0x804CF734,
        stick_hook=0x804CF74C,
        panic1=0x804B7E00,
        panic2=0x804B7EC4,
        panic3=0x805B67B4,
    ),
}

def build(region, dol):
    sites = SITES[region]
    
    syms = {
        'GET_CONTROLLER_STATUS': sites['get_ctrl'],
        'COPY_BTN_RET': sites['btn_copy_ret'],
        'STICK_RET': sites['stick_ret'],
        'UI4_RET': sites['ui4_ret'],
        'UI5_CALL': sites['ui5_call'],
        'UI5_RET1': sites['ui5_ret1'],
        'UI5_RET2': sites['ui5_ret2'],
        'CLAMP': sites['clamp'],
        'PTR_MATH_RET': sites['ptr_math_ret'],
        'PTR_VALID_RET': sites['ptr_valid_ret'],
        'PTR_UPDATE_RET1': sites['ptr_upd_ret1'],
        'PTR_UPDATE_RET2': sites['ptr_upd_ret2'],
    }
    
    src = g.read('cc_code.s')
    cc_bytes, symbols = asm.assemble_symbols(src, CC_BASE, syms, {})
    
    if CC_BASE + len(cc_bytes) > CC_END:
        raise SystemExit(f'cc code overflows window: 0x{CC_BASE + len(cc_bytes):X} > 0x{CC_END:X}')
        
    ops = []
    # 1. Injected blob in cave
    ops.append(Blob(CC_BASE, cc_bytes, note='Classic Controller driver routines'))
    
    # 2. Hooks jumping to routines
    def make_b_patch(site, target_sym, note):
        target = symbols[target_sym]
        ins = b_insn(target, site)
        orig = dol.read(site, 4)
        return Patch(site, struct.pack('>I', ins), orig, note=note)

    ops.append(make_b_patch(sites['ui1_hook'], 'cc_ui1', 'UI prompt hook 1'))
    ops.append(make_b_patch(sites['ui2_hook'], 'cc_ui2', 'UI prompt hook 2'))
    ops.append(make_b_patch(sites['ui3_hook'], 'cc_ui3', 'UI prompt hook 3'))
    ops.append(make_b_patch(sites['ptr_check_hook'], 'cc_pointer_check', 'Pointer check hook'))
    ops.append(make_b_patch(sites['ui4_hook'], 'cc_ui4', 'UI prompt hook 4'))
    ops.append(make_b_patch(sites['ui5_hook'], 'cc_ui5', 'UI prompt hook 5'))
    ops.append(make_b_patch(sites['ptr_upd_hook'], 'cc_pointer_update', 'Pointer update hook'))
    ops.append(make_b_patch(sites['btn_hook'], 'cc_button_copy', 'Button copy and remap hook'))
    ops.append(make_b_patch(sites['ptr_valid_hook'], 'cc_pointer_valid', 'Pointer valid flag hook'))
    ops.append(make_b_patch(sites['stick_hook'], 'cc_left_stick', 'Left stick copy hook'))

    # 3. Pointer math 4-word replacement at ptr_math_hook:
    # 60000000 (nop), mflr r7 (7ce802a6), b cc_pointer_math, mtlr r7 (7ce803a6)
    b_ptr_math = b_insn(symbols['cc_pointer_math'], sites['ptr_math_hook'] + 8)
    math_patch_words = [0x60000000, 0x7CE802A6, b_ptr_math, 0x7CE803A6]
    math_patch_bytes = b''.join(struct.pack('>I', w) for w in math_patch_words)
    ops.append(Patch(
        sites['ptr_math_hook'],
        math_patch_bytes,
        dol.read(sites['ptr_math_hook'], 16),
        note='Pointer right stick math hook'
    ))

    # 4. Skip button write: b +0x10 (48000010)
    ops.append(Patch(
        sites['btn_skip'],
        bytes.fromhex('48000010'),
        dol.read(sites['btn_skip'], 4),
        note='Skip button write'
    ))

    # 5. Pointer flag: li r0, 1 (38000001)
    ops.append(Patch(
        sites['ptr_flag'],
        bytes.fromhex('38000001'),
        dol.read(sites['ptr_flag'], 4),
        note='Pointer flag init'
    ))

    # 6. UI helper functions
    # 0x8002a930 (100 bytes)
    ui3_words = [
        0x9421fff0, 0x7c0802a6, 0x90010014, 0x93e1000c, 0x93c10008,
        b_insn(sites['get_ctrl'], sites['ui3_func'] + 20, link=True),
        0x7c7e1b78, 0x807e0014, 0x8803000c, 0x2c000000, 0x40820020,
        0x807e0028, 0x8803000c, 0x2c000000, 0x40820010, 0x807e0008,
        0x80030004, 0x541fdffe, 0x7fe3fb78, 0x83e1000c, 0x83c10008,
        0x80010014, 0x7c0803a6, 0x38210010, 0x4e800020
    ]
    ui3_bytes = b''.join(struct.pack('>I', w) for w in ui3_words)
    ops.append(Patch(sites['ui3_func'], ui3_bytes, dol.read(sites['ui3_func'], len(ui3_bytes)), note='UI function 0x8002a930'))

    # Helper 1 (0x804307fc)
    bl_h4 = b_insn(sites['ui_helper4'], sites['ui_helper1'] + 8, link=True)
    h1_bytes = struct.pack('>3I', 0x38A10050, 0x38C00000, bl_h4)
    ops.append(Patch(sites['ui_helper1'], h1_bytes, dol.read(sites['ui_helper1'], len(h1_bytes)), note='UI helper 1'))

    # Helper 2 (0x80432238)
    ops.append(Patch(sites['ui_helper2'], bytes.fromhex('38c00000'), dol.read(sites['ui_helper2'], 4), note='UI helper 2'))

    # Helper 3 (0x80432250)
    bl_h4_from_h3 = b_insn(sites['ui_helper4'], sites['ui_helper3'] + 4, link=True)
    h3_bytes = struct.pack('>2I', 0x38A300B8, bl_h4_from_h3)
    ops.append(Patch(sites['ui_helper3'], h3_bytes, dol.read(sites['ui_helper3'], len(h3_bytes)), note='UI helper 3'))

    # Helper 4 (0x804407b8)
    bl_status = b_insn(symbols['cc_get_status'], sites['ui_helper4'] + 8, link=True)
    h4_words = [
        0x7cc33378, 0x7ce802a6, bl_status, 0x2c030002,
        0x7ce803a6, 0x7ca32b78, 0x7cc43378, 0x41820008,
        b_insn(0x80029f20, sites['ui_helper4'] + 32),
        b_insn(0x8002a8c0, sites['ui_helper4'] + 36)
    ]
    h4_bytes = b''.join(struct.pack('>I', w) for w in h4_words)
    ops.append(Patch(sites['ui_helper4'], h4_bytes, dol.read(sites['ui_helper4'], len(h4_bytes)), note='UI helper 4'))

    # Helper 5 (0x8044096c)
    b_h6 = b_insn(sites['ui_helper6'], sites['ui_helper5'])
    bl_h4_from_h5 = b_insn(sites['ui_helper4'], sites['ui_helper5'] + 4, link=True)
    h5_bytes = struct.pack('>2I', b_h6, bl_h4_from_h5)
    ops.append(Patch(sites['ui_helper5'], h5_bytes, dol.read(sites['ui_helper5'], len(h5_bytes)), note='UI helper 5'))

    # Helper 6 (0x80440b94)
    b_back = b_insn(sites['ui_helper5'] + 4, sites['ui_helper6'] + 8)
    h6_bytes = struct.pack('>3I', 0x38A10020, 0x38C00000, b_back)
    ops.append(Patch(sites['ui_helper6'], h6_bytes, dol.read(sites['ui_helper6'], len(h6_bytes)), note='UI helper 6'))

    # 7. Extension check: allow extension 2
    orig_ext = dol.read(sites['ext_check'], 8)
    ops.append(Patch(
        sites['ext_check'],
        bytes.fromhex('2c1e000240810014'),
        orig_ext,
        note='Controller manager: allow extension type 2 (Classic Controller)'
    ))

    # 8. Panic handlers nop
    nop = bytes.fromhex('60000000')
    ops.append(Patch(sites['panic1'], nop, dol.read(sites['panic1'], 4), note='Panic handler 1 disable'))
    ops.append(Patch(sites['panic2'], nop, dol.read(sites['panic2'], 4), note='Panic handler 2 disable'))
    ops.append(Patch(sites['panic3'], nop, dol.read(sites['panic3'], 4), note='Panic handler 3 disable'))

    return Feature('cc', 'Classic Controller', region, ops)
