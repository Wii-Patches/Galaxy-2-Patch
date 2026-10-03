#!/usr/bin/env python3
"""Emit the Gecko code lists and Riivolution XML from the prebuilt features.

    python3 tools/build.py            # writes codes/<ID>.ini, codes/<ID>.txt, riivolution/<ID>.xml

The patched-DOL path (tools/patcher.py, the GUI) uses the very same ops, so the
three install methods cannot disagree.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
from regions import REGIONS

ROOT = os.path.join(HERE, '..')

CREDIT = {
    'cc': 'quatric',
    'gc': 'quatric',
}
BLURB = {
    'cc': ['Play with a Classic Controller plugged into the Wii Remote: left stick moves, right stick aims the cursor.',
           'A jump, B crouch/ground pound, X/Y spin attack, ZR shoot star bits, L/ZL crouch/long jump, R reset camera.'],
    'gc': ['Play with a GameCube controller in port 1 (no Wii Remote needed):',
           'Control stick moves Mario, C-stick aims the star pointer, A jump, B crouch/ground pound,',
           'X/Y spin attack, Z shoot star bits, L/R crouch/long jump, Start pause, D-pad camera.'],
}
COMBINED_WARNING = []


def gecko_ini(region):
    lines = ['[Gecko]']
    for name in features.FEATURES:
        if not features.available(name, region):
            continue
        f = features.load(name, region)
        lines.append('$%s' % f.title)
        lines.append('*By %s' % CREDIT[name])
        lines.append('*%s (%s)' % (REGIONS[region]['label'], region))
        lines += ['*' + b for b in BLURB[name]]
        lines += COMBINED_WARNING if any(hasattr(o, 'data') for o in f.ops) else []
        lines += f.gecko_lines()
    return '\n'.join(lines) + '\n'


def riivolution_xml(region):
    r = REGIONS[region]
    out = ['<!-- %s: patches by quatric -->' % r['label'],
           '<wiidisc version="1" root="/">',
           '  <id game="%s" version="%d" />' % (region, r['version']),
           '  <options>',
           '    <section name="%s">' % r['label']]
    for name in features.FEATURES:
        if features.available(name, region):
            out.append('      <option name="%s" default="1">' % features.TITLES[name])
            out.append('        <choice name="Enabled"><patch id="%s" /></choice>' % name)
            out.append('      </option>')
    out += ['    </section>', '  </options>']
    for name in features.FEATURES:
        if not features.available(name, region):
            continue
        f = features.load(name, region)
        out.append('  <patch id="%s">' % name)
        out += ['    ' + e for e in f.memory_elements()]
        out.append('  </patch>')
    out.append('</wiidisc>')
    return '\n'.join(out) + '\n'


def main():
    for d in ('codes', 'riivolution'):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    for region in REGIONS:
        ini = gecko_ini(region)
        with open(os.path.join(ROOT, 'codes', region + '.ini'), 'w') as fh:
            fh.write(ini)
        # same codes in the plain cheat-file layout loaders read (no [Gecko] header)
        with open(os.path.join(ROOT, 'codes', region + '.txt'), 'w') as fh:
            fh.write(ini.split('\n', 1)[1])
        with open(os.path.join(ROOT, 'riivolution', region + '.xml'), 'w') as fh:
            fh.write(riivolution_xml(region))
        print(region, REGIONS[region]['label'])


if __name__ == '__main__':
    main()
