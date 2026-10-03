"""Dev-time assembler: turns src/*.s into the words shipped in tools/prebuilt/.

Needs devkitPPC (powerpc-eabi-as / -ld).  End users never run this -- the
patcher reads the prebuilt JSON, which gen_prebuilt.py regenerates and checks.
"""
import os
import shutil
import subprocess
import tempfile

DKP = os.environ.get('DEVKITPPC', '/opt/devkitpro/devkitPPC')


def _tool(name):
    p = os.path.join(DKP, 'bin', 'powerpc-eabi-' + name)
    if os.path.exists(p):
        return p
    return shutil.which('powerpc-eabi-' + name) or p


def assemble(source, base, syms=None, consts=None):
    """Assemble `source` (text) to bytes located at `base`.

    `syms` become link-time absolute symbols, so `bl helper` / `b RET` encode
    correctly relative to `base`.  `consts` are assemble-time numbers, usable in
    expressions such as `addi r3,r3,-DEAD`.
    """
    syms = syms or {}
    consts = consts or {}
    with tempfile.TemporaryDirectory() as t:
        s, o, bn = (os.path.join(t, n) for n in ('a.s', 'a.o', 'a.bin'))
        with open(s, 'w') as f:
            f.write('.globl _start\n_start:\n' + source + '\n')
        cmd_as = [_tool('as'), '-mbig', '-mgekko', s, '-o', o]
        for k, v in consts.items():
            cmd_as[1:1] = ['-defsym', '%s=%d' % (k, v)]
        subprocess.run(cmd_as, check=True)
        cmd = [_tool('ld'), '-Ttext=0x%X' % base, '--oformat', 'binary', o, '-o', bn]
        for k, v in syms.items():
            cmd[1:1] = ['--defsym', '%s=0x%X' % (k, v)]
        subprocess.run(cmd, check=True)
        return open(bn, 'rb').read()


def assemble_symbols(source, base, syms=None, consts=None):
    """Assemble source at base and return (binary_bytes, {symbol_name: address})."""
    syms = syms or {}
    consts = consts or {}
    with tempfile.TemporaryDirectory() as t:
        s, o, bn = (os.path.join(t, n) for n in ('a.s', 'a.o', 'a.bin'))
        with open(s, 'w') as f:
            f.write('.globl _start\n_start:\n' + source + '\n')
        cmd_as = [_tool('as'), '-mbig', '-mgekko', s, '-o', o]
        for k, v in consts.items():
            cmd_as[1:1] = ['-defsym', '%s=%d' % (k, v)]
        subprocess.run(cmd_as, check=True)
        cmd = [_tool('ld'), '-Ttext=0x%X' % base, '--oformat', 'binary', o, '-o', bn]
        for k, v in syms.items():
            cmd[1:1] = ['--defsym', '%s=0x%X' % (k, v)]
        subprocess.run(cmd, check=True)
        
        nm_out = subprocess.check_output([_tool('nm'), o]).decode()
        symbols = {}
        for line in nm_out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] in ('T', 't', 'D', 'd'):
                off = int(parts[0], 16)
                symbols[parts[2]] = base + off
        return open(bn, 'rb').read(), symbols


def words(data):
    import struct
    return list(struct.unpack('>%dI' % (len(data) // 4), data))

