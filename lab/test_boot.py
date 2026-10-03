import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gdbmem import Gdb

PORT = int(os.environ.get('LAB_GDB_PORT', 2260))

def main():
    dolphin = os.environ.get('DOLPHIN', '/Applications/Dolphin.app/Contents/MacOS/Dolphin')
    user = os.environ.get('DOLPHIN_USER', os.path.join(HERE, '..', 'work', 'dolphin_user'))
    image = os.environ.get('SMG2_IMAGE')
    if not image:
        sys.exit('set SMG2_IMAGE to path of patched Super Mario Galaxy 2 image')
    cmd = [dolphin, '-u', user, '-b', '-e', image]
    print('Starting Dolphin...')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        g = None
        for i in range(25):
            try:
                g = Gdb(port=PORT, timeout=10)
                print('Connected to Dolphin GDB stub!')
                break
            except OSError:
                time.sleep(0.5)
        if not g:
            raise RuntimeError('Could not connect to GDB stub')

        print('Emulating for 15 seconds...')
        g.cont()
        time.sleep(15)

        print('Interrupting to inspect memory...')
        g.interrupt()

        # Check injected code at CC_BASE and GC_BASE
        cc_bytes = g.read_mem(0x80001820, 16)
        print(f'CC_BASE (0x80001820): {cc_bytes.hex().upper()}')
        gc_bytes = g.read_mem(0x80002400, 16)
        print(f'GC_BASE (0x80002400): {gc_bytes.hex().upper()}')

        # Check hook sites
        hook_kpad = g.read_mem(0x804CF884, 4)
        print(f'kpad_read hook (0x804CF884): {hook_kpad.hex().upper()}')
        hook_probe = g.read_mem(0x805EB410, 4)
        print(f'probe hook (0x805EB410): {hook_probe.hex().upper()}')

        # Check panic handlers (should be nop 60000000)
        p1 = g.read_mem(0x804B7D90, 4)
        p2 = g.read_mem(0x804B7E54, 4)
        p3 = g.read_mem(0x805B66B4, 4)
        print(f'Panic 1 (0x804B7D90): {p1.hex().upper()}')
        print(f'Panic 2 (0x804B7E54): {p2.hex().upper()}')
        print(f'Panic 3 (0x805B66B4): {p3.hex().upper()}')

        g.close()
        print('SUCCESS: Verified live in Dolphin MEM1!')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

if __name__ == '__main__':
    main()
