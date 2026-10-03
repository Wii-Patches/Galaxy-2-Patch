#!/usr/bin/env python3
"""Regenerate tools/prebuilt/*.json from src/ (needs devkitPPC and retail DOLs).

    python3 tools/gen_prebuilt.py [cc|gc ...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from dol import Dol
from features import PREBUILT, dump
from regions import REGIONS

def dol_for(region):
    env = os.environ.get('SMG2_DOL_' + region)
    if env and os.path.exists(env):
        return Dol(env)
    base = os.environ.get('SMG2_DOLS')
    if base:
        p = os.path.join(base, region + '.dol')
        if os.path.exists(p):
            return Dol(p)
    sys.exit('set SMG2_DOLS=<dir with %s.dol> or SMG2_DOL_%s=<path>' % (region, region))

def main(argv):
    which = argv or ['cc', 'gc']
    os.makedirs(PREBUILT, exist_ok=True)
    for name in which:
        mod = __import__('gen_' + name)
        for region in REGIONS:
            d = dol_for(region)
            f = mod.build(region, d)
            path = os.path.join(PREBUILT, '%s_%s.json' % (name, region))
            with open(path, 'w') as fh:
                json.dump(dump(f), fh, indent=1)
                fh.write('\n')
            print('%-3s %s  %d ops -> %s' % (name, region, len(f.ops), os.path.relpath(path)))

if __name__ == '__main__':
    main(sys.argv[1:])
