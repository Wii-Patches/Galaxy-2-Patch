#!/usr/bin/env python3
"""Run the GameCube controller patch live in Dolphin, with no Wii Remote.

    SMG2_IMAGE=<retail SB4E01 image> python3 lab/gc_live.py [seconds]

Dolphin boots the *unpatched* image with its GDB stub on; while it is halted at
the entry point the patch (gc + what it needs) is written straight into MEM1,
so no rebuilt disc is needed.  Port 1 is a Standard Controller, no Wii Remote
is connected.  Every few seconds the hook counters and the game's controller
state are printed.

With FEED=1 the debug build of the hooks is used (needs devkitPPC and the USA
main.dol in SMG2_DOLS): the pad response is then written by this script, which
presses A every few seconds and pushes the stick, so the game can be driven
without anyone holding a pad.  PATCHED=1 boots an already patched image and
only checks that the patch is in memory; SIDEV0=0 leaves port 1 empty.  FRAMES=1 also dumps every frame as a PNG into
<user>/Dump/Frames.
"""
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from gdbmem import Gdb
import features
import patcher

PORT = int(os.environ.get('LAB_GDB_PORT', 2261))
STATE = 0x80002400
KPAD0 = 0x80750A00          # KPAD block, channel 0 (USA)
WPAD_TBL = 0x80791C10


def user_dir():
    return os.environ.get('DOLPHIN_USER', os.path.join(HERE, '..', 'work', 'dolphin_gc'))


def config(user):
    cfg = os.path.join(user, 'Config')
    os.makedirs(cfg, exist_ok=True)
    open(os.path.join(cfg, 'Dolphin.ini'), 'w').write(
        f"[General]\nGDBPort = {PORT}\n[Core]\nCPUThread = False\nEnableDebugging = True\n"
        f"EnableCheats = False\nSIDevice0 = {os.environ.get('SIDEV0', '6')}\nSIDevice1 = 0\nSIDevice2 = 0\nSIDevice3 = 0\n"
        f"WiimoteContinuousScanning = False\n"
        f"[Interface]\nConfirmStop = False\nUsePanicHandlers = False\nShowSplashScreen = False\n"
        f"[Display]\nRenderToMain = False\n"
        + ("[Movie]\nDumpFrames = True\nDumpFramesSilent = True\n" if os.environ.get('FRAMES') else ""))
    if os.environ.get('FRAMES'):
        open(os.path.join(cfg, 'GFX.ini'), 'w').write('[Settings]\nDumpFramesAsImages = True\nDumpFormat = png\n')
    open(os.path.join(cfg, 'WiimoteNew.ini'), 'w').write(
        ''.join('[Wiimote%d]\nSource = 0\n' % i for i in range(1, 5)) + '[BalanceBoard]\nSource = 0\n')
    src = os.path.join(HERE, '..', 'work', 'dolphin_user', 'Config', 'GCPadNew.ini')
    if os.path.exists(src):
        shutil.copy(src, os.path.join(cfg, 'GCPadNew.ini'))


def writes(region, which):
    out = []
    for n in patcher.with_deps(which):
        if n == 'gc' and os.environ.get('FEED'):
            sys.path.insert(0, os.path.join(HERE, '..', 'src'))
            os.environ['DEBUG_FEED'] = '1'
            import gen_gc
            from gen_prebuilt import dol_for
            out += gen_gc.build(region, dol_for(region)).writes()
        else:
            out += features.load(n, region).writes()
    return out


IDLE = (0x00808080, 0x80800000)      # pad response: nothing pressed, sticks centred
GC_A = 0x01000000


def feed(g, h, l):
    g.write_mem(STATE + 0x38, struct.pack('>II', h, l))


def controller_obj(g):
    """the game's player-1 controller object (USA)"""
    p = struct.unpack('>I', g.read_mem(0x807D0DA4, 4))[0]
    for off in (32, 36):
        p = struct.unpack('>I', g.read_mem(p + off, 4))[0]
    return struct.unpack('>I', g.read_mem(p + 4, 4))[0]


def controller(g):
    """the game's player-1 controller object: (connected, attachment ok)"""
    obj = controller_obj(g)
    b = g.read_mem(obj + 52, 3)
    return b[1], b[2]


def snapshot(g):
    st = g.read_mem(STATE, 0x40)
    u = struct.unpack('>9I', st[:36])
    blk = struct.unpack('>I', g.read_mem(WPAD_TBL, 4))[0]
    wstat = struct.unpack('>i', g.read_mem(blk + 0x900, 4))[0] if blk else None
    k = g.read_mem(KPAD0, 0x180)
    shadow = struct.unpack('>I', g.read_mem(0x8071A59C, 4))[0]
    sitype = struct.unpack('>I', g.read_mem(0x8071A5B0, 4))[0]
    print('  frames=%d samples=%d/%d probes=%d  norep=%d ours=%d connected=%d  last=%08X %08X'
          % (u[5], u[7], u[6], u[8], st[36], st[37], st[38], u[3], u[4]))
    print('  KPAD0: hold=%08X dev=%d err=%d fmt=%d  cl.hold=%08X lstick=%r rstick=%r  ring idx=%d cnt=%d'
          % (struct.unpack('>I', k[0:4])[0], k[0x5C], struct.unpack('b', k[0x5D:0x5E])[0], k[0x5F],
             struct.unpack('>I', k[0x60:0x64])[0],
             struct.unpack('>2f', k[0x6C:0x74]), struct.unpack('>2f', k[0x74:0x7C]), k[0x17A], k[0x17B]))
    print('  WPAD0 status=%r  si:: poll shadow=%08X type[0]=%08X' % (wstat, shadow, sitype))


def main():
    dolphin = os.environ.get('DOLPHIN', '/Applications/Dolphin.app/Contents/MacOS/Dolphin')
    image = os.environ.get('SMG2_IMAGE')
    if not image:
        sys.exit('set SMG2_IMAGE to an unpatched SB4E01 image')
    user = user_dir()
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    config(user)
    proc = subprocess.Popen([dolphin, '-u', os.path.abspath(user), '-b', '-e', image],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        g = None
        for _ in range(40):
            try:
                g = Gdb(port=PORT, timeout=10)
                break
            except OSError:
                time.sleep(0.5)
        if g is None:
            sys.exit('no GDB stub')
        print('stub:', g.cmd('?'))
        for addr, data in writes('SB4E01', ['gc']):
            if os.environ.get('PATCHED'):       # the image is already patched: only check it
                assert g.read_mem(addr, len(data)) == data, 'image not patched at %08X' % addr
                continue
            g.write_mem(addr, data)
            assert g.read_mem(addr, len(data)) == data
        fed = bool(os.environ.get('FEED'))
        if fed:
            feed(g, *IDLE)
        print('patch written%s' % (' (debug feed)' if fed else ''))
        g.cont()
        t0 = time.time()
        n = 0
        while time.time() - t0 < secs:
            time.sleep(4)
            n += 1
            g.interrupt()
            print('t=%ds' % (time.time() - t0))
            snapshot(g)
            try:
                print('  game controller 1: connected=%d attachment=%d' % controller(g))
            except Exception as e:
                print('  game controller 1: not up yet (%s)' % e)
            if fed:
                # tap A; every third round hold the stick up-right and the C-stick left instead
                if n % 3 == 0:
                    feed(g, 0x0080E0E0, 0x30800000)
                else:
                    feed(g, IDLE[0] | GC_A, IDLE[1])
                g.cont()
                time.sleep(0.4)
                g.interrupt()
                print('  pressed:')
                snapshot(g)
                feed(g, *IDLE)
            g.cont()
        g.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == '__main__':
    main()
