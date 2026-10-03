"""Where the hook trampolines and injected routines live.

0x80001800-0x80003000 is the Wii's boot-time scratch area, which the game itself
never touches (the game's own code starts at 0x80004000). The first 0x20 bytes
are skipped because 0x80001800 can be used by code handlers.
Each feature gets a fixed window so the patches can be combined freely without
colliding.
"""
CAVE_BASE = 0x80001820
CAVE_LIMIT = 0x80003000

CC_BASE = 0x80001820          # Classic Controller injected routines
CC_END = 0x80002400
GC_BASE = 0x80002400          # GameCube controller injected routines
GC_END = 0x80003000

WINDOWS = {'cc': (CC_BASE, CC_END), 'gc': (GC_BASE, GC_END)}
