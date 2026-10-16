#!/usr/bin/env python3
"""Drive Super Mario Galaxy 2 in Dolphin with a scripted GameCube pad.

    [REGION=SB4P01] SMG2_IMAGE=<unpatched image> SMG2_DOLS=<dir with the DOLs> \
        python3 lab/drive.py <workdir>

Boots the image like gc_live.py (debug-feed build of the GameCube hooks
injected at the entry point, no Wii Remote, every frame dumped as a PNG), then
reads commands appended to <workdir>/cmd.txt, one per line:

    press A B ... SECS      hold buttons (A B X Y Z L R START UP DOWN LEFT RIGHT)
    stick X Y [CX CY] SECS  hold the control stick (and C-stick) at -100..100
    hold BTN.. X Y SECS     buttons and control stick together
    wait SECS               let the game run with nothing pressed
    shot NAME               copy the newest frame to <workdir>/NAME.png
    state                   log the hook counters and the game's controller
    regs                    log pc, lr and the stack's return addresses
    peek BTN.. SECS         hold buttons and log the Wii Remote buttons the game sees
    mem ADDR [LEN]          log memory
    quit

Everything it does is logged to <workdir>/log.txt.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gc_live
from gdbmem import Gdb

BTN = dict(LEFT=0x00010000, RIGHT=0x00020000, DOWN=0x00040000, UP=0x00080000, Z=0x00100000,
           R=0x00200000, L=0x00400000, A=0x01000000, B=0x02000000, X=0x04000000, Y=0x08000000,
           START=0x10000000)


def response(buttons=0, x=0, y=0, cx=0, cy=0):
    h = 0x00800000 | buttons | ((x + 128) & 0xFF) << 8 | ((y + 128) & 0xFF)
    trig = (0xFF if buttons & BTN['L'] else 0) << 8 | (0xFF if buttons & BTN['R'] else 0)
    l = ((cx + 128) & 0xFF) << 24 | ((cy + 128) & 0xFF) << 16 | trig
    return h, l


class Driver:
    def __init__(self, work):
        self.work = work
        self.frames = os.path.join(gc_live.user_dir(), 'Dump', 'Frames')
        self.logf = open(os.path.join(work, 'log.txt'), 'a', buffering=1)

    def log(self, msg):
        self.logf.write(msg + '\n')

    def run_for(self, h, l, secs):
        if os.environ.get('NOPATCH'):
            time.sleep(secs)
            return
        self.g.interrupt()
        gc_live.feed(self.g, h, l)
        self.g.cont()
        time.sleep(secs)
        self.g.interrupt()
        gc_live.feed(self.g, *gc_live.IDLE)
        self.g.cont()

    def shot(self, name):
        files = glob.glob(os.path.join(self.frames, '*.png'))
        if not files:
            self.log('shot %s: no frames yet' % name)
            return
        newest = max(files, key=os.path.getmtime)
        time.sleep(0.3)
        shutil.copy(newest, os.path.join(self.work, name + '.png'))
        self.log('shot %s <- %s' % (name, os.path.basename(newest)))

    def state(self):
        if os.environ.get('NOPATCH') or os.environ.get('REGION', 'SB4E01') != 'SB4E01':
            return                                      # the addresses below are the USA ones
        self.g.interrupt()
        st = self.g.read_mem(gc_live.STATE, 0x40)
        u = struct.unpack('>9I', st[:36])
        k = self.g.read_mem(gc_live.KPAD0, 0x80)
        try:
            c = gc_live.controller(self.g)
        except Exception:
            c = None
        self.g.cont()
        self.log('state: frames=%d samples=%d connected=%d  KPAD0 dev=%d fmt=%d cl.hold=%08X ls=%r rs=%r  game=%r'
                 % (u[5], u[6], st[38], k[0x5C], k[0x5F], struct.unpack('>I', k[0x60:0x64])[0],
                    struct.unpack('>2f', k[0x6C:0x74]), struct.unpack('>2f', k[0x74:0x7C]), c))

    def regs(self):
        """pc, lr and a back chain walk of the stopped thread"""
        self.g.interrupt()
        reg = lambda n: int(self.g.cmd('p%x' % n)[:8], 16)
        # Dolphin's stub numbers 0-31 GPRs, 32-63 FPRs, 64 pc, 65 msr, 66 cr, 67 lr
        gpr = {1: reg(1), 3: reg(3)}
        pc, lr = reg(64), reg(67)
        chain, sp = [], gpr[1]
        for _ in range(12):
            try:
                nxt, ret = struct.unpack('>II', self.g.read_mem(sp, 8))
            except Exception:
                break
            if not 0x80000000 <= nxt < 0x81800000:
                break
            chain.append('%08X' % struct.unpack('>I', self.g.read_mem(nxt + 4, 4))[0])
            sp = nxt
        self.g.cont()
        self.log('regs: pc=%08X lr=%08X r1=%08X r3=%08X  chain=%s' % (pc, lr, gpr[1], gpr[3], ' '.join(chain)))

    def threads(self):
        """saved context of every OS thread (active queue at 0x800000DC)"""
        self.g.interrupt()
        t = struct.unpack('>I', self.g.read_mem(0x800000DC, 4))[0]
        seen = 0
        while t and seen < 32:
            ctx = self.g.read_mem(t, 0x320)
            gpr = struct.unpack('>32I', ctx[:128])
            cr, lr, ctr, xer = struct.unpack('>4I', ctx[128:144])
            srr0, srr1 = struct.unpack('>2I', ctx[0x198:0x1A0])
            state = struct.unpack('>H', ctx[0x2C8:0x2CA])[0]
            prio = struct.unpack('>i', ctx[0x2D0:0x2D4])[0]
            self.log('thread %08X state=%d prio=%d srr0=%08X lr=%08X r1=%08X r3=%08X'
                     % (t, state, prio, srr0, lr, gpr[1], gpr[3]))
            t = struct.unpack('>I', ctx[0x2FC:0x300])[0]
            seen += 1
        self.g.cont()

    def do(self, line):
        w = line.split()
        if not w:
            return True
        cmd, args = w[0].lower(), w[1:]
        if cmd == 'quit':
            return False
        if cmd == 'wait':
            time.sleep(float(args[0]))
        elif cmd == 'press':
            b = sum(BTN[a.upper()] for a in args[:-1])
            self.run_for(*response(b), float(args[-1]))
        elif cmd == 'stick':
            n = [int(a) for a in args[:-1]] + [0, 0]
            self.run_for(*response(0, n[0], n[1], n[2], n[3]), float(args[-1]))
        elif cmd == 'hold':
            names = [a for a in args if a.upper() in BTN]
            nums = [int(a) for a in args[len(names):-1]] + [0, 0, 0, 0]
            b = sum(BTN[a.upper()] for a in names)
            self.run_for(*response(b, *nums[:4]), float(args[-1]))
        elif cmd == 'shot':
            self.shot(args[0])
        elif cmd == 'state':
            self.state()
        elif cmd == 'regs':
            self.regs()
        elif cmd == 'peek':
            # peek BTN.. SECS: hold buttons, then log the Wii Remote buttons the game itself sees
            b = sum(BTN[a.upper()] for a in args[:-1])
            self.g.interrupt()
            gc_live.feed(self.g, *response(b))
            self.g.cont()
            time.sleep(float(args[-1]))
            self.g.interrupt()
            obj = gc_live.controller_obj(self.g)
            st = struct.unpack('>I', self.g.read_mem(struct.unpack('>I', self.g.read_mem(obj + 4, 4))[0], 4))[0]
            hold = struct.unpack('>I', self.g.read_mem(st, 4))[0]
            gc_live.feed(self.g, *gc_live.IDLE)
            self.g.cont()
            self.log('peek %s: game status %08X hold=%08X' % (' '.join(args[:-1]), st, hold))
        elif cmd == 'mem':
            # mem ADDR [LEN]: log memory
            a, n = int(args[0], 16), int(args[1], 0) if len(args) > 1 else 4
            self.g.interrupt()
            data = self.g.read_mem(a, n)
            self.g.cont()
            self.log('mem %08X: %s' % (a, data.hex().upper()))
        elif cmd == 'threads':
            self.threads()
        else:
            self.log('?? ' + line)
        return True

    def main(self, image):
        os.environ['FEED'] = '1'
        os.environ['FRAMES'] = '1'
        user = gc_live.user_dir()
        shutil.rmtree(os.path.join(user, 'Dump'), ignore_errors=True)
        gc_live.config(user)
        dolphin = os.environ.get('DOLPHIN', '/Applications/Dolphin.app/Contents/MacOS/Dolphin')
        proc = subprocess.Popen([dolphin, '-u', os.path.abspath(user), '-b', '-e', image],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(40):
                try:
                    self.g = Gdb(port=gc_live.PORT, timeout=10)
                    break
                except OSError:
                    time.sleep(0.5)
            self.g.cmd('?')
            if not os.environ.get('NOPATCH'):           # NOPATCH=1: baseline run of the retail game
                for addr, data in gc_live.writes(os.environ.get('REGION', 'SB4E01'), ['gc']):
                    self.g.write_mem(addr, data)
                gc_live.feed(self.g, *gc_live.IDLE)
            self.g.cont()
            self.log('booted')
            cmdfile = os.path.join(self.work, 'cmd.txt')
            open(cmdfile, 'a').close()
            done = 0
            while proc.poll() is None:
                lines = open(cmdfile).read().splitlines()
                if len(lines) > done:
                    for line in lines[done:]:
                        self.log('> ' + line)
                        if not self.do(line):
                            return
                    done = len(lines)
                    self.log('ready %d' % done)
                time.sleep(0.2)
            self.log('dolphin exited')
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == '__main__':
    work = os.path.abspath(sys.argv[1])
    os.makedirs(work, exist_ok=True)
    Driver(work).main(os.environ['SMG2_IMAGE'])
