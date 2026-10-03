#!/usr/bin/env python3
"""Consistency checks that need no game files (CI runs this).

  * every prebuilt feature loads, stays inside its window of the injected
    section, and its hook trampolines end where they should
  * the committed codes/ and riivolution/ files are exactly what build.py
    generates from the prebuilt data
  * Gecko output parses back into the same operations

    python3 tools/check.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import build
import features
from layout import CAVE_BASE, CAVE_LIMIT, WINDOWS
from ops import Hook, Patch, b_insn
from regions import REGIONS

fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
        print('  FAIL', msg)


def main():
    for region in REGIONS:
        taken = []
        for name in features.FEATURES:
            check(features.available(name, region), 'missing prebuilt %s_%s.json' % (name, region))
            if not features.available(name, region):
                continue
            f = features.load(name, region)
            lo, hi = WINDOWS[name]
            for op in f.ops:
                if isinstance(op, Hook):
                    n = len(op.payload) * 4
                    check(lo <= op.tramp and op.tramp + n <= hi,
                          '%s/%s: trampoline 0x%08X..0x%08X outside its window' % (name, region, op.tramp, op.tramp + n))
                    check(op.payload[-1] == 0, '%s/%s: hook 0x%08X has no branch-back slot' % (name, region, op.site))
                    check(all(op.payload[:-1]), '%s/%s: hook 0x%08X contains a zero word' % (name, region, op.site))
                    for a, b in taken:
                        check(op.tramp + n <= a or b <= op.tramp, '%s/%s: trampolines overlap at 0x%08X' % (name, region, op.tramp))
                    taken.append((op.tramp, op.tramp + n))
                    # the static form must branch back to site+4
                    writes = dict(f.writes())
                    body = writes[op.tramp]
                    back = struct.unpack('>I', body[-4:])[0]
                    check(back == b_insn(op.site + 4, op.tramp + len(body) - 4), '%s/%s: bad branch-back at 0x%08X' % (name, region, op.site))
                    check(CAVE_BASE <= op.tramp and op.tramp + n <= CAVE_LIMIT, 'trampoline outside the injected section')
                    # a Gecko code handler runs the routine from somewhere else, so every relative
                    # branch must stay inside it (calls to the game go through absolute addresses)
                    for i, w in enumerate(op.payload):
                        opc = w >> 26
                        if opc in (16, 18) and not w & 2:
                            li = (w & 0xFFFC) if opc == 16 else (w & 0x03FFFFFC)
                            li = li - (0x8000 << 1 if li & 0x8000 else 0) if opc == 16 else (li - 0x04000000 if li & 0x02000000 else li)
                            tgt = i * 4 + li
                            check(0 <= tgt <= n, '%s/%s: relative branch out of the routine at 0x%08X+0x%X' % (name, region, op.tramp, i * 4))
                elif isinstance(op, Patch):
                    check(len(op.new) == len(op.orig), '%s/%s: patch size mismatch at 0x%08X' % (name, region, op.addr))
            # gecko -> ops round trip
            import gecko
            text = '\n'.join(f.gecko_lines())
            for kind, addr, body in gecko.parse('\n'.join(l for l in text.splitlines() if not l.startswith('*'))):
                if kind == 'C2':
                    hooks = [o for o in f.ops if isinstance(o, Hook) and o.site == addr]
                    check(len(hooks) == 1 and body[:len(hooks[0].payload) - 1] == hooks[0].payload[:-1],
                          '%s/%s: C2 at 0x%08X does not round-trip' % (name, region, addr))
    # committed outputs are current
    root = os.path.join(HERE, '..')
    for region in REGIONS:
        ini = build.gecko_ini(region)
        check(open(os.path.join(root, 'codes', region + '.ini')).read() == ini, 'codes/%s.ini is stale (run tools/build.py)' % region)
        check(open(os.path.join(root, 'riivolution', region + '.xml')).read() == build.riivolution_xml(region),
              'riivolution/%s.xml is stale (run tools/build.py)' % region)
    print('FAILED: %d' % len(fail) if fail else 'ok: all checks passed')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
