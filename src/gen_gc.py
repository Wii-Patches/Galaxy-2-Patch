"""Build the GameCube controller feature for Super Mario Galaxy 2.

The pad is presented to the game as a Classic Controller (gcpad.c), so this
feature needs the Classic Controller feature alongside it (tools/patcher.py
adds it automatically).

Everything is written once against the USA main.dol; other releases are found
by matching the USA code with relocatable bits masked out (sig.py), and the
data addresses are read back from the matched code, never guessed.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import asm
from layout import GC_BASE, GC_END
from ops import Blob, Feature, Hook
from sig import find_unique, mask_loose

REF = 'SB4E01'
STATE = GC_BASE                 # hook state (zeroed), then the three routines
STATE_SIZE = 0x40

# USA addresses of what the hooks need
FRAME = 0x804CF840              # the game's per-frame controller update (KPADRead loop)
KPAD_READ = 0x8054B450          # KPADiRead
SAMPLE_COUNT = 0x8054B5F4       # lbz r0,0x17b(r21): "any samples queued?"
WPAD_PROBE = 0x805EB410
SI_GETTYPE = 0x805C2F90
OS_DISABLE = 0x805B99D0
OS_RESTORE = 0x805B9A10
SI_TYPES = 0x8071A5B0           # si:: cached device type per port
WPAD_TBL = 0x80791C10           # WPAD control block pointer per channel

# the instruction each hook replaces
EXPECT = {
    'FRAME': 0x9421FFD0,        # stwu r1,-0x30(r1)
    'SAMPLE': 0x8815017B,       # lbz r0,0x17b(r21)
    'PROBE': 0x9421FFF0,        # stwu r1,-0x10(r1)
}


def _imm(w):
    v = w & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _pair(dol, va, value, n=64):
    """True when a lis/addi pair within n words of va loads `value`."""
    return _pair_value(dol, va, lambda v: v == value, n) is not None


def _pair_value(dol, va, want, n=64):
    w = struct.unpack('>%dI' % n, dol.read(va, n * 4))
    for i in range(n):
        if w[i] >> 26 != 15:
            continue
        reg = (w[i] >> 21) & 31
        for j in range(i + 1, min(n, i + 16)):
            if w[j] >> 26 == 14 and (w[j] >> 16) & 31 == reg:
                v = (((w[i] & 0xFFFF) << 16) + _imm(w[j])) & 0xFFFFFFFF
                if want(v):
                    return i, j, v
    return None


def _data(ref, tgt, ref_fn, tgt_fn, ref_value):
    """The target's value of the address that ref_fn loads as ref_value."""
    i, j, _ = _pair_value(ref, ref_fn, lambda v: v == ref_value)
    tw = struct.unpack('>64I', tgt.read(tgt_fn, 256))
    return (((tw[i] & 0xFFFF) << 16) + _imm(tw[j])) & 0xFFFFFFFF


def resolve(region, dol):
    if region == REF:
        a = dict(Frame=FRAME, KPADiRead=KPAD_READ, WPADProbe=WPAD_PROBE, SIGetType=SI_GETTYPE,
                 OSDisableInterrupts=OS_DISABLE, OSRestoreInterrupts=OS_RESTORE,
                 SiTypes=SI_TYPES, WpadTbl=WPAD_TBL)
    else:
        from gen_prebuilt import dol_for
        ref = dol_for(REF)
        if ref is None:
            raise SystemExit('%s: the USA main.dol is needed to find the hook sites' % region)
        a = dict(Frame=find_unique(ref, dol, FRAME, 0, 40, mask_loose),
                 KPADiRead=find_unique(ref, dol, KPAD_READ, 0, 40, mask_loose),
                 WPADProbe=find_unique(ref, dol, WPAD_PROBE, 0, 40, mask_loose),
                 SIGetType=find_unique(ref, dol, SI_GETTYPE, 0, 40, mask_loose),
                 OSDisableInterrupts=find_unique(ref, dol, OS_DISABLE, 0, 6, mask_loose),
                 OSRestoreInterrupts=find_unique(ref, dol, OS_RESTORE, 0, 6, mask_loose))
        a['SiTypes'] = _data(ref, dol, SI_GETTYPE, a['SIGetType'], SI_TYPES)
        a['WpadTbl'] = _data(ref, dol, WPAD_PROBE, a['WPADProbe'], WPAD_TBL)
    a['SampleCount'] = a['KPADiRead'] + (SAMPLE_COUNT - KPAD_READ)    # same code in every release
    a['SiBusy'] = a['SiTypes'] - 0x18                                 # si::Si.chan
    a['SiShadow'] = a['SiBusy'] + 4                                   # si::Si.poll
    # sanity: the data really is what the code uses
    if not _pair(dol, a['SIGetType'], a['SiTypes']) or not _pair(dol, a['WPADProbe'], a['WpadTbl']):
        raise SystemExit('%s: SI type table / WPAD table not referenced where expected' % region)
    return a


def compile_hook(name, defs):
    tools = os.path.dirname(asm._tool('gcc'))
    pre = os.path.join(tools, 'powerpc-eabi-')
    D = ['-D%s=%s' % kv for kv in defs.items()] + ['-DHOOK_' + name]
    if os.environ.get('DEBUG_FEED'):
        D.append('-DDEBUG_FEED')
    D += os.environ.get('GC_DEFS', '').split()        # dev only, e.g. GC_DEFS=-DNO_CALLBACKS
    cflags = ['-O2', '-fno-unroll-loops', '-mbig-endian', '-mcpu=750', '-msoft-float', '-msdata=none',
              '-ffreestanding', '-fno-pic', '-fno-asynchronous-unwind-tables', '-fno-stack-protector',
              '-fno-builtin', '-nostdlib', '-Wall', '-Werror']
    with tempfile.TemporaryDirectory() as t:
        subprocess.check_call([pre + 'gcc'] + cflags + D + ['-c', os.path.join(HERE, 'gcpad.c'), '-o', t + '/g.o'])
        subprocess.check_call([pre + 'gcc', '-mbig-endian', '-c', '-x', 'assembler-with-cpp'] + D +
                              [os.path.join(HERE, 'hooks.S'), '-o', t + '/h.o'])
        subprocess.check_call([pre + 'ld', '-T', os.path.join(HERE, 'link.ld'), '-o', t + '/b.elf', t + '/h.o', t + '/g.o'])
        subprocess.check_call([pre + 'objcopy', '-O', 'binary', '-j', '.text', t + '/b.elf', t + '/b.bin'])
        b = open(t + '/b.bin', 'rb').read()
    w = list(struct.unpack('>%dI' % (len(b) // 4), b))
    if w[-1] != 0x60000000:
        raise SystemExit('%s hook does not end in the branch-back slot' % name)
    w[-1] = 0
    return w


def build(region, dol):
    a = resolve(region, dol)
    sites = {'FRAME': a['Frame'], 'SAMPLE': a['SampleCount'], 'PROBE': a['WPADProbe']}
    for name, site in sites.items():
        got = struct.unpack('>I', dol.read(site, 4))[0]
        if got != EXPECT[name]:
            raise SystemExit('%s %s hook at 0x%08X: expected %08X, found %08X'
                             % (region, name, site, EXPECT[name], got))
    defs = {
        'STATE': '0x%08Xu' % STATE,
        'SI_TYPES': '0x%08Xu' % a['SiTypes'],
        'SI_BUSY': '0x%08Xu' % a['SiBusy'],
        'SI_SHADOW': '0x%08Xu' % a['SiShadow'],
        'FN_SIGETTYPE': '0x%08Xu' % a['SIGetType'],
        'FN_OSDISABLE': '0x%08Xu' % a['OSDisableInterrupts'],
        'FN_OSRESTORE': '0x%08Xu' % a['OSRestoreInterrupts'],
        'WPAD_TBL': '0x%08Xu' % a['WpadTbl'],
    }
    notes = {
        'FRAME': 'Per-frame controller update: poll the GameCube pad, announce it to the game',
        'SAMPLE': 'KPAD sample ring: GameCube pad as Classic Controller samples',
        'PROBE': 'WPADProbe: report a Classic Controller while the pad answers',
    }
    ops = [Blob(STATE, bytes(STATE_SIZE), note='GameCube controller state')]
    at = STATE + STATE_SIZE
    for name in ('FRAME', 'SAMPLE', 'PROBE'):
        words = compile_hook(name, defs)
        ops.append(Hook(sites[name], EXPECT[name], words, at, note=notes[name]))
        at += (len(words) * 4 + 15) & ~15
    if at > GC_END:
        raise SystemExit('gc code overflows its window: 0x%08X > 0x%08X' % (at, GC_END))
    return Feature('gc', 'GameCube controller', region, ops)
