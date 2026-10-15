"""Shared pieces of the Classic Controller and GameCube controller builders for Super Mario Galaxy 2."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))

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
