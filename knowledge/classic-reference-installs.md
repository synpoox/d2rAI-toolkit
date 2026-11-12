# Classic 1.09d reference install: which files are stock

How to tell stock Lord of Destruction 1.09d files from a modded or cracked install, where a stock copy comes from, and
what is and is not proven. A port compares against one frozen, hash-recorded set (its **reference install**, see the
glossary in [porting-classic-mods.md](porting-classic-mods.md)). The per-file SHA-256 list is
`shared/classic_import/baselines/109d.json` (read by `shared/classic_import/extract.py`, which refuses an archive whose
hash differs); this file holds the provenance and the traps. Never commit these files (they are Blizzard's).

## Answer

- **Stock set.** A version-switching tool (Version Changer 4.6) stores one complete file set per version and mode in
  `VersionChanger\<Classic|LoD>\<version>\`. Every `Diablo II.exe`, `D2VidTst.exe`, DLL and `Patch_D2.mpq` of an install
  that was switched to 1.09d is byte-identical to the tool's `LoD\1.09d\` set. The DLLs also match the tool's
  `Classic\1.09d\` copies. The Blizzard-built files carry PE link timestamps of 2001-11-30, five days before the 1.09d
  PC release.
- **Where a stock copy comes from:** for every file, the copy in the tool's `LoD\1.09d\`. That includes the original
  `Game.exe` if a copy-protected binary is ever needed.
- **`D2Game.dll` stock is `477c14010cde02a186485b41f91229e5c9231cd49c7f2db92cd226d5f0c173f9`** (MD5
  `3c640c3f16f76f7adc991295f31c9558`, 1,028,146 bytes, PE timestamp 2001-11-30T03:36:56Z).
- **`Game.exe` is the trap.** The `Game.exe` in an install is often the 1.09d LoD **NoCD** build (90,112 bytes, SHA-256
  `2b7391519396228f4f7f902426c67157f35fbeef95c9e1f64014d8f70554e182`; decrypted, copy protection removed), not the
  stock one (448,675 bytes, SHA-256 `b211b8ad79e9f2bbb29f6e7b0d861cadbd1fe63438a12d740f01404fd2ce8df6`). Both report
  the same file version resource (1.0.9 build 22) and share the PE timestamp 2001-11-30T03:47:54Z. The tool copies the NoCD one over `Game.exe`
  with its "Use NoCD" option. For reverse engineering the NoCD file is the more useful (its readme says it is identical
  to the way it was before being protected). Record which one a baseline holds.
- **Base MPQs are installer data, not 1.09d patch files.** `d2data`, `d2char` and `d2sfx.mpq` are exactly the three
  archives the tool's "Fix 1.14 Installer MPQs" option edits (it deletes the `(attributes)` entry with an MPQ editor), so
  they are the later downloadable-installer archives with one metadata entry removed. They are not proven byte-equal to
  the 2001 discs. `Patch_D2.mpq` loads first and overrides them, so this matters only for files 1.09d did not patch.
- **External confirmation: none.** No high-trust source publishes per-file 1.09d hashes, and searches for the
  `D2Game.dll` hash returned nothing. The official patch installer was not downloaded, so there is no byte comparison
  with it. The tool's own sourcing is undocumented; its store agrees with the PE timestamps and version resources, but
  that is internal consistency, not provenance.

## How the version tool stores versions

Applying a version deletes `Patch_D2.mpq` and copies `VersionChanger\<mode>\<version>\*.*` into the game root. Optional
steps then: copy `VersionChanger\NoCD\<mode>\<version>\Game.exe` over `Game.exe`; copy a third-party single-player
extender into the root; and, in one mode, patch a game DLL with a file patcher. An install whose `D2gfx.dll` matches the
stored copy did not use the DLL-patching mode. The tool never touches the base MPQs except through the MPQ-fix option.

## Key files

SHA-256; "stock" = the tool's `LoD\1.09d\` copy.

| File | Size | SHA-256 | Note |
|---|---|---|---|
| D2Game.dll | 1,028,146 | `477c14010cde02a186485b41f91229e5c9231cd49c7f2db92cd226d5f0c173f9` | stock |
| D2Client.dll | 1,134,644 | `c7de352d3857d03f8f8d6a6649254f63c16fd835e84816785af298e56e3f51bf` | stock |
| D2Common.dll | 692,276 | `cf1d735a2d6f6747f31158967466e4f049c7b00562b5dcede1565421f4940cd8` | stock |
| Patch_D2.mpq | 1,338,671 | `5dd67faff6c06eaa8e9c9e55dbf302e53a21dc2fd722d537cf2a279944ba3fdd` | stock |
| Game.exe (NoCD) | 90,112 | `2b7391519396228f4f7f902426c67157f35fbeef95c9e1f64014d8f70554e182` | not the stock file |
| Game.exe (stock) | 448,675 | `b211b8ad79e9f2bbb29f6e7b0d861cadbd1fe63438a12d740f01404fd2ce8df6` | |
| Diablo II.exe | 36,864 | `147e33cc5d2dd9520d143847b35c1c8410a432c605155e0d9678b5b9450a7938` | the LoD set; the Classic set differs |
| d2data.mpq | 269,191,615 | `5cbfb794a990709bcb11dec4e3ed6b7656c49ea28957c4753cb25263cdd8208a` | installer data, attributes entry removed |
| d2exp.mpq | 250,156,780 | `04e35bffeae8d9959042832055702f8b5b4567ca5505ff1df0cf3fd6d5beb6c2` | installer data |

The other DLLs (Bnclient, D2CMP, D2DDraw, D2Direct3D, D2Gdi, D2gfx, D2Glide, D2Lang, D2Launch, D2MCPClient, D2Multi,
D2Net, D2sound, D2Win, Fog, Storm 1.08b, ijl11, SmackW32, binkw32), the remaining base MPQs (`d2char`, `d2sfx`,
`d2music`, `d2speech`, `d2video`, `d2xmusic`, `d2xtalk`, `d2xvideo`) and `D2VidTst.exe` are in the baseline JSON. Files
in an install that are not part of 1.09d, to leave out of a freeze: third-party DLLs, extenders and their patchers, an
original-`Fog.dll` backup, a mod's own data archive, a game-launcher or error-reporter executable.

## A code-cave patch, for recognising a hooked DLL

A mod's `D2Game.dll` can be stock plus a code-cave hook. One seen: same PE timestamp and sections (`.text .rdata .data
.reloc`), 3 runs of differing bytes, 460 bytes in all (3 + 4 + 453; the 453-byte block may contain bytes equal to the original):

- 3 bytes at file offset `0x0B52EF` and 4 bytes at `0x0B538E` in `.text` change the operand bytes of existing branches
  or calls, which retargets them.
- 453 bytes at `0x0D6060`, at the end of `.rdata`, where the stock file has **zero padding**: x86 code
  (`83 EC 0C 55 56 8B F1 57 ...`, `sub esp,0Ch; push ebp; push esi; mov esi,ecx; push edi ...`).

New code goes into unused padding and existing calls are redirected to it. The unhooked file is the stock one: its
padding is untouched. To test an install file, hash it against the baseline, and if it differs diff it against the
stock copy to see whether the difference is a cave like this one (a few runs plus a block of code in padding).

## Not checked

- No byte comparison against the official 1.09d patch. It would need an approved download of the patch installer, then
  extracting its embedded MPQ without running it and hashing the contents (if some files are stored as diffs, rebuild
  them before comparing; not checked).
- Base MPQ contents against the 2001 retail discs.
