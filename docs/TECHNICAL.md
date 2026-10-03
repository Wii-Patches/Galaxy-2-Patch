# Technical Notes

How the patches work, where they hook, and how one set of data becomes a
patched `main.dol`, a Gecko code list, and a Riivolution patch. For installing
and playing, see the [README](../README.md).

Addresses below are the **USA** `main.dol` (`SB4E01`) unless noted; the table at
the end lists the other regional releases.

## One Data Set, Three Outputs

Every patch is a list of operations on one release's `main.dol`:

| Operation | Static (`main.dol`) | Gecko | Riivolution |
| --- | --- | --- | --- |
| **Blob** — injected routine or lookup table in low memory | text section at `0x80001820` | `06` write code | `<memory>` element |
| **Patch** — replace instructions at a known game site | overwrite at offset | `04` / `06` code | `<memory>` element |
| **Hook** — branch to a routine that executes displaced instructions | branch + trampoline | `C2` code | branch + `<memory>` |

`tools/prebuilt/<feature>_<disc id>.json` holds those operations, including the
retail bytes expected at every site. `tools/ops.py` turns them into each
format, `tools/patcher.py` applies them (and refuses a `main.dol` whose sites do
not match, so already-modified or foreign dumps are never touched), and
`tools/build.py` writes `codes/` and `riivolution/`. `tools/check.py` validates
consistency; `tools/verify.py` checks the data against real retail DOLs for
every combination of patches (CC alone, GC alone, CC+GC together, and stepwise).

## Low-Memory Layout

Routines live in the Wii's boot-time scratch area (`0x80001800 - 0x80003000`), which
the game's own code never touches (game code starts at `0x80004000`):

| Window | Size | Purpose |
| --- | --- | --- |
| `0x80001820 - 0x80002400` | 0xBE0 | Classic Controller driver routines and UI trampolines |
| `0x80002400 - 0x80003000` | 0xC00 | GameCube controller driver and stick calibration table |

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

GameCube controllers connect via the physical Serial Interface (SI) ports on top of the original Wii console:
1. Auto-polling is initialized on the SI registers (`0xCD006400`).
2. Input buffer `0x6404` (`INBUFH`) and `0x6408` (`INBUFL`) are read each frame.
3. The 256-entry float lookup table calibrates analog stick deadzones and scales axes to `[-1.0, 1.0]`.
4. Buttons and C-stick values are injected directly into `KPADStatus` with extension type 2 (Classic Controller).
5. `WPADProbe` (`0x805EB410`) reports a connected controller even if no Wii Remote is paired.
6. Panic handlers at `0x804B7D90`, `0x804B7E54`, and `0x805B66B4` are disabled (`nop`) to prevent "Please connect Nunchuk" freezes.

## Supported Releases

| Disc ID | Region | Title | main.dol Size |
| --- | --- | --- | --- |
| `SB4E01` | USA | Super Mario Galaxy 2 (USA) | 7,546,080 |
| `SB4P01` | Europe | Super Mario Galaxy 2 (Europe/Australia) | 7,568,352 |
| `SB4J01` | Japan | Super Mario Galaxy 2 (Japan) | 7,544,000 |
| `SB4W01` | Taiwan/Asia | Super Mario Galaxy 2 (Taiwan/Hong Kong) | 7,546,784 |
| `SB4K01` | Korea | Super Mario Galaxy 2 (Korea) | 7,581,952 |
