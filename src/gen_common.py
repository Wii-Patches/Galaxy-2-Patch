"""Shared pieces of the Classic Controller and GameCube controller builders for Super Mario Galaxy 2."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import asm
from ops import Hook, Patch, Blob
from sig import find_unique

# Button constants
WM = dict(
    WM_LEFT=0x0001, WM_RIGHT=0x0002, WM_DOWN=0x0004, WM_UP=0x0008, WM_PLUS=0x0010,
    WM_SHAKE=0x0020, WM_2=0x0100, WM_1=0x0200, WM_B=0x0400, WM_A=0x0800,
    WM_MINUS=0x1000, WM_Z=0x2000, WM_C=0x4000, WM_HOME=0x8000
)

CC = dict(
    CC_UP=0x0001, CC_LEFT=0x0002, CC_ZR=0x0004, CC_X=0x0008, CC_A=0x0010, CC_Y=0x0020,
    CC_B=0x0040, CC_ZL=0x0080, CC_R=0x0200, CC_PLUS=0x0400, CC_HOME=0x0800,
    CC_MINUS=0x1000, CC_L=0x2000, CC_DOWN=0x4000, CC_RIGHT=0x8000
)

PAD = dict(
    PAD_LEFT=0x0001, PAD_RIGHT=0x0002, PAD_DOWN=0x0004, PAD_UP=0x0008, PAD_Z=0x0010,
    PAD_R=0x0020, PAD_L=0x0040, PAD_A=0x0100, PAD_B=0x0200, PAD_X=0x0400, PAD_Y=0x0800,
    PAD_START=0x1000
)

def read(name):
    path = os.path.join(HERE, name)
    out = []
    for line in open(path).read().split('\n'):
        if line.startswith('#include '):
            inc_file = line.split()[1]
            out.append(read(inc_file))
        else:
            out.append(line)
    return '\n'.join(out)

def decode_branch(word, at):
    li = word & 0x03FFFFFC
    if li & 0x02000000:
        li -= 0x04000000
    return (at + li) & 0xFFFFFFFF

def hook(site, orig, base, source, syms, consts, note=''):
    words = asm.words(asm.assemble(read('macros.s') + source, base, syms, consts)) + [0]
    return Hook(site, orig, words, base, note=note), (len(words) * 4 + 15) & ~15
