# Technical Notes

How the patches work, where they hook, and how one set of data becomes a
patched `main.dol`. For installing
and playing, see the [README](../README.md).

Addresses below are the **USA** `main.dol` (`SB4E01`) unless noted; the table at
the end lists the other regional releases.

## One Data Set

Every patch is a list of operations on one release's `main.dol`:

| Operation | Effect |
| --- | --- |
| **Blob** — injected routine or lookup table in low memory | text section at `0x80001820` |
| **Patch** — replace instructions at a known game site | overwrite at offset |
| **Hook** — branch to a routine that executes displaced instructions | branch + trampoline |

`tools/prebuilt/<feature>_<disc id>.json` holds those operations, including the
retail bytes expected at every site. `tools/patcher.py` applies them (and refuses
a `main.dol` whose sites do not match, so already-modified or foreign dumps are
never touched). `tools/check.py` validates consistency; `tools/verify.py` checks
the data against real retail DOLs for every combination of patches (CC alone, GC
alone, CC+GC together, and stepwise).

## Low-Memory Layout

Routines live in the Wii's boot-time scratch area (`0x80001800 - 0x80003000`), which
the game's own code never touches (game code starts at `0x80004000`):

| Window | Size | Purpose |
| --- | --- | --- |
| `0x80001820 - 0x80002400` | 0xBE0 | Classic Controller driver routines and UI trampolines |
| `0x80002400 - 0x80003000` | 0xC00 | GameCube controller state and hook routines |

The first `0x20` bytes (`0x80001800 - 0x80001820`) are skipped because `0x80001800` is
reserved by OS exception and debug handlers.

## Classic Controller Architecture

Super Mario Galaxy 2 connects to the Wii Remote via Nintendo's `KPAD` library.
When an extension controller is detected:
1. `btn_hook` (`0x804CF5D8`) remaps Classic Controller face buttons and triggers into Mario's action bits.
2. `ptr_math_hook` (`0x804CF61C`) integrates right stick displacement into the Star Pointer screen coordinates `[-1.0, 1.0]`.
3. `ptr_valid_hook` (`0x804CF6A4`) sets the pointer valid flag to 2 so the game draws the star cursor without an IR sensor bar.
4. UI prompt helpers (`0x804307FC`, `0x80432250`, `0x804407B8`, `0x8044096C`, `0x80440B94`) adjust on-screen button prompts from Wiimote swing icons to button badges.

## GameCube Controller Architecture

The game links Nintendo's `SI` library but not `PAD`, so nothing ever polls the
GameCube ports, and its controller manager only treats a player as present once
WPAD's connect callback fires, which never happens without a Wii Remote. The
patch (`src/gcpad.c`, entry stubs in `src/hooks.S`) therefore presents a pad in
port 1 as a Wii Remote with a Classic Controller on channel 0, and leaves the
rest to the Classic Controller patch, which it requires.

| Hook | USA site | Replaced instruction | Job |
| --- | --- | --- | --- |
| `FRAME` | `0x804CF840` | `stwu r1,-0x30(r1)` | Per-frame controller update (the loop that calls `KPADRead` for each channel): drive the SI poller; when a pad appears and no Wii Remote owns channel 0, fire WPAD's connect callback and the extension callback (type 2) as WPAD would; fire the disconnect when it goes |
| `SAMPLE` | `0x8054B5F4` | `lbz r0,0x17b(r21)` | `KPADiRead`'s "samples queued?" check: write two Classic Controller samples into the ring (`+0x180`, `0x42` bytes each); with a bare Wii Remote, fill its samples' extension fields instead |
| `PROBE` | `0x805EB410` | `stwu r1,-0x10(r1)` | `WPADProbe`: report "connected, Classic Controller" for channel 0 while the pad answers, unless a real Nunchuk/Classic Controller is there |

The poller (after Barrel Blast Patch, hardware-tested there):

1. Probe port 1 with `SIGetType` at most every 0.25 s until the cached type is a standard pad (`(type & 0x18000000) == 0x08000000`).
2. Write the poll command `0x00400300` to `SIC0OUTBUF` (`0xCD006400`; the Wii's SI, not `0xCC006400`).
3. Write `SISR` with the error bits acknowledged plus `WR` (bit 31), which latches the command.
4. Enable polling and copy-on-vblank for port 1 in `SIPOLL` **and** in `si::`'s shadow copy (`0x8071A59C`), which `SISetXY` writes back on every retrace.
5. Copy a persistent `NOREP` into the type cache (`0x8071A5B0`) so an unplugged pad is probed again, and un-wedge `si::`'s busy flag after a second.

A response counts when `ERRSTAT` (bit 31) is clear and `PAD_USE_ORIGIN` (bit 23) is set.

Button mapping (GameCube → Classic Controller, which the Classic Controller patch then maps onto the Wii Remote + Nunchuk): A→a, B→b, X/Y→x, Z→ZL, L→L, R→R, Start→+, D-pad→D-pad, Start+Z→HOME. The analog L/R count as pressed past `0xA0`. Sticks are scaled ×3 around the centre (KPAD maps 60–308 to 0–1), so a pad's dead zone is about ±20.

State (`0x80002400`, 0x40 bytes) holds the poller's timers, the previous frame's buttons and hook counters that `lab/gc_live.py` reads over Dolphin's GDB stub.

The other releases are found by matching the USA code with relocatable bits masked (`tools/sig.py`); data addresses are read from the matched `lis`/`addi` pairs (`src/gen_gc.py`).

## Supported Releases

| Disc ID | Region | Title | main.dol Size |
| --- | --- | --- | --- |
| `SB4E01` | USA | Super Mario Galaxy 2 (USA) | 7,546,080 |
| `SB4P01` | Europe | Super Mario Galaxy 2 (Europe/Australia) | 7,568,352 |
| `SB4J01` | Japan | Super Mario Galaxy 2 (Japan) | 7,544,000 |
| `SB4W01` | Taiwan/Asia | Super Mario Galaxy 2 (Taiwan/Hong Kong) | 7,546,784 |
| `SB4K01` | Korea | Super Mario Galaxy 2 (Korea) | 7,541,568 |
