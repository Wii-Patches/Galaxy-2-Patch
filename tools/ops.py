"""The patch model shared by every output format.

A feature (SDHC, GameCube pad, Classic Controller) is a list of operations
against one region's main.dol.  It is applied statically: trampolines live in
the injected section of a patched main.dol.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from layout import CAVE_BASE, CAVE_LIMIT


def b_insn(target, frm, link=False):
    off = target - frm
    if not -0x2000000 <= off < 0x2000000 or off & 3:
        raise ValueError('branch 0x%08X -> 0x%08X out of range' % (frm, target))
    return 0x48000000 | (off & 0x03FFFFFC) | (1 if link else 0)


@dataclass
class Patch:
    """Overwrite bytes in place; `orig` is what retail has there."""
    addr: int
    new: bytes
    orig: bytes
    note: str = ''


@dataclass
class Hook:
    """Replace the instruction at `site` with a branch to a trampoline.

    payload[:-1] is the trampoline body (it must itself execute the displaced
    instruction `orig`); payload[-1] is a placeholder that becomes the branch
    back to site+4.  `tramp` is where the static build puts it.
    """
    site: int
    orig: int
    payload: list
    tramp: int
    note: str = ''


@dataclass
class Blob:
    """New code/data in the injected section (zero in retail by construction)."""
    addr: int
    data: bytes
    note: str = ''


@dataclass
class Feature:
    name: str
    title: str
    region: str
    ops: list = field(default_factory=list)

    # ------------------------------------------------------------ static view
    def writes(self):
        """(addr, bytes) for a permanent main.dol patch."""
        out = []
        for op in self.ops:
            if isinstance(op, Patch):
                out.append((op.addr, op.new))
            elif isinstance(op, Blob):
                out.append((op.addr, op.data))
            elif isinstance(op, Hook):
                body = list(op.payload[:-1]) + [b_insn(op.site + 4, op.tramp + 4 * (len(op.payload) - 1))]
                out.append((op.tramp, b''.join(struct.pack('>I', w) for w in body)))
                out.append((op.site, struct.pack('>I', b_insn(op.tramp, op.site))))
        return out

    def check_pristine(self, dol):
        """Names of ops whose retail bytes do not match (empty = good to patch)."""
        bad = []
        for op in self.ops:
            if isinstance(op, Patch):
                cur = dol.read(op.addr, len(op.orig))
                if cur != op.orig and cur != op.new:
                    bad.append('0x%08X' % op.addr)
            elif isinstance(op, Hook):
                if dol.read(op.site, 4) != struct.pack('>I', op.orig):
                    bad.append('0x%08X' % op.site)
        return bad

    def is_applied(self, dol):
        """True when every site already carries this feature's bytes."""
        for addr, data in self.writes():
            if addr >= CAVE_BASE and addr < CAVE_LIMIT:
                cur = dol.read(addr, len(data))
                if cur is not None and cur != data:
                    return False
                if cur is None:
                    return False
            elif dol.read(addr, len(data)) != data:
                return False
        return True


def apply_static(dol, features):
    """Write every feature into `dol` (a dol.Dol), adding the injected section.

    Raises if a site does not hold the retail bytes (wrong build, or already
    patched).  Returns the number of bytes added in the new section.
    """
    for f in features:
        bad = f.check_pristine(dol)
        if bad:
            raise ValueError('%s: unexpected bytes at %s (already patched, or not this game build)'
                             % (f.title, ', '.join(bad)))
    writes = []
    for f in features:
        for w in f.writes():
            if w not in writes:
                writes.append(w)
    cave = [(a, d) for a, d in writes if CAVE_BASE <= a < CAVE_LIMIT]
    rest = [(a, d) for a, d in writes if not CAVE_BASE <= a < CAVE_LIMIT]
    if cave:
        end = max(a + len(d) for a, d in cave)
        if end > CAVE_LIMIT:
            raise ValueError('injected section would run past 0x%08X' % CAVE_LIMIT)
        existing = next((s for s in dol.secs if s[1] == CAVE_BASE and s[3] < 7), None)
        blob = bytearray(max(end - CAVE_BASE, existing[2] if existing else 0))
        if existing:
            blob[:existing[2]] = dol.read(CAVE_BASE, existing[2])
        for a, d in cave:
            seg = blob[a - CAVE_BASE:a - CAVE_BASE + len(d)]
            if any(seg):
                raise ValueError('overlapping cave writes at 0x%08X' % a)
            blob[a - CAVE_BASE:a - CAVE_BASE + len(d)] = d
        if existing:
            dol.replace_text_section(CAVE_BASE, bytes(blob))
        else:
            dol.add_text_section(CAVE_BASE, bytes(blob))
    for a, d in rest:
        dol.write(a, d)
    return len(cave) and (max(a + len(d) for a, d in cave) - CAVE_BASE)
