# Saves (.d2s v105) and the D2RLoader sidecar

Edit test characters only while the game is closed, and **back up first** (copy the `.d2s` and its `.d2rl` to a
folder of your own, e.g. `Saved Games/Diablo II Resurrected/<mod>-manual-backups/<name>-before-<change>/`).

Save folder for a mod with `"savepath": "<Mod>/"` in its modinfo.json: `%USERPROFILE%\Saved Games\Diablo II
Resurrected\mods\<Mod>\` (kept apart from retail saves). D2RLoader also writes its own backups to
`Saved Games\Diablo II Resurrected\D2RLoader Backups\`.

## Header

| Offset | Size | Field |
|---|---|---|
| 0x00 | u32 | signature `0xaa55aa55` |
| 0x04 | u16 / u32 | retail: u16 version `0x69` (105) in 3.3, bytes 0x06-0x07 zero. D2RLoader extended format: u32 `0x44520000 \| extended version`, so bytes 0x06-0x07 read `RD`. Saves written by the loader here carry `0x44520005`; the PluginSDK 0.4.0 README documents `0x44520006` for saves written after its custom-page change ([the marker](#the-extended-save-marker)) |
| 0x08 | u32 | file size |
| 0x0c | u32 | checksum |
| 0x15 | u8 | progression. A test save sets `0x0f` to open every difficulty (observed on 3.3; used by `testing/save_edit.py`) |
| 0x18 | u8 | class |
| 0x1b | u8 | level (display) |
| 0x28 | u32[16] | skill hotkeys F1-F16: skill id, `0xffff` = none, `| 0x8000` = bound to the left button (observed) |
| 0x12b | char[] | character name |
| 0x98-0x9a | u8[3] | current location of Normal, Nightmare, Hell: `0x80 | (act - 1)` for the active difficulty, 0 for the others (observed on 3.3: `00 00 80` = Hell, act 1) |

**Checksum**: set the size field, zero the checksum field, then over every byte: `c = rotl32(c, 1) + byte`
(32-bit). Write `c` at 0x0c.

```python
def fix_checksum(d: bytearray) -> bytearray:
    d[8:12] = len(d).to_bytes(4, "little"); d[12:16] = b"\0\0\0\0"
    c = 0
    for b in d:
        c = (((c << 1) | (c >> 31)) + b) & 0xffffffff
    d[12:16] = c.to_bytes(4, "little"); return d
```

## D2RLoader sidecar `<name>.d2rl`

| Offset | Size | Field |
|---|---|---|
| 0x00 | char[4] | `D2RL` |
| 0x04 | u16 | version 2 |
| 0x06 | u16 | header size `0x2c` |
| 0x08 | u32 | body length |
| 0x0c | 32 | SHA-256 of the body (file offset 0x2c to the end) |
| 0x2c | | body |
| 0x34 | u32 | copy of the `.d2s` checksum |
| 0x38 | u32 | copy of the `.d2s` file size |
| 0x3c | 32 | SHA-256 of the whole `.d2s` |

All offsets are file offsets (verified on real sidecars: version 2, header 0x2c, body 529 bytes, file 573 bytes).
**After any `.d2s` edit, update in this order**: `.d2s` size and checksum, sidecar
checksum copy (0x34) and size copy (0x38), sidecar `.d2s` hash (0x3c), then the body hash (0x0c). A mismatch makes
the character **silently disappear** from character select (a sidecar-only mismatch greys it out, per the D2RLoader
guide's "Environment badges").

## Character stats ("gf")

After the marker `gf`: a bit-packed list (LSB first) of `stat id`, then the parameter (itemstatcost `CSvParam`
bits, if any), then the value in itemstatcost **`CSvBits`** bits. Under D2RLoader's **extended** save format the
stat id is **16 bits** and the list ends with `0xffff` (retail D2: 9-bit ids, end `0x1ff`). Life/mana/stamina are
stored `<< 8`. Pad to a byte at the end.

Useful rules: experience.txt row L is the experience at which level L+1 starts; charstats
`LifePerLevel`/`ManaPerLevel`/`StaminaPerLevel` are quarter points per level; `StatPerLevel` and
`SkillsPerLevel` give unspent points.

## Class skills ("if")

After `if`: **one byte per class skill** (hard points), in the order of that class's skills by skill ID. Retail:
30 bytes (30 class skills). With D2RLoader's extended format a class can have more (an overhaul ran several times 30).
Setting a byte works with the checksum and sidecar updates.

## Items ("JM" + u16 count)

Bit-packed (LSB first), each item padded to a byte. Retail 3.3 layout, as decoded:

| Field | Bits | Notes |
|---|---|---|
| flags | 32 | 0x10 identified, 0x800 socketed, 0x10000 ear, 0x20000 starter, 0x200000 simple, 0x400000 ethereal, 0x1000000 personalized, 0x4000000 runeword |
| (3.3) | 8 | 0x05 on every item seen |
| version | 3 | 5 |
| location, equip slot, x, y, page | 3, 4, 4, 4, 3 | |
| code | Huffman, 4 chars | D2R's item-code tree |
| simple items | 1 + 128, then 1 | unique-id flag + 128-bit id, socket bit; done |
| sockets filled | 3 | |
| item id | 32 | |
| item level, quality | 7, 4 | |
| picture flag, class-specific flag | +3, +16 | auto-affix id is 16 bits in 3.3 (11 in 2.x) |
| quality fields | | set/unique id, affixes, rare names (3.3 widths not verified) |
| defense / durability | itemstatcost `Save Bits` / `Save Add` | |
| stats | 16-bit id, `Save Param Bits`, `Save Bits` (value + `Save Add`) | end `0xffff` |

## What is safe to hand-edit

| Edit | Safe? |
|---|---|
| Level (header + stat 12), experience, stat points, skill points, base stats | Yes (fix checksum, size, sidecar) |
| Class skill bytes ("if") | Yes |
| Gold, waypoints, quests | Likely (not tested) |
| **Items under the extended format** | **No.** The extended format stores wider item/stat/affix/skill IDs whose exact widths are not documented; two hand-built items made the characters vanish even with correct checksums and hashes |
| Item widths after changing itemstatcost `Save Bits`/`CSvBits` | Existing saves break: decide widths before release |
| Quest words, for test characters | Yes, closed save. Reset the quests a test needs: D2R runs a quest's kill handler only while the quest is open in that difficulty, so a test that passed once fails on the same character later |

Get test items with D2RLoader's debug-mode **Item Spawner** instead of writing items.

## Notes

- Retail starter items may not decode with the retail Huffman table under the extended format (a Paladin starter
  item did not), another sign the extended item layout differs.
- **Item stats must fit their save widths.** A property with function 28 (stat layer = param) on a stat that has
  no `Save Param Bits` makes D2R's item writer assert (`Items.cpp` `ptItemStats`) and write nothing: the item packet
  is an empty header and the client crashes (`BC_ASSERT: hUnit`, then a null read in the item packet handler) the
  moment such an item drops, is gambled or comes out of the cube. 1.13c's writer skipped the layer instead. Fix the
  data: clear the parameter, or give the stat param bits before players have saves.
- Files next to `<name>.d2s`: `<name>.d2rl` (D2RLoader sidecar), `<name>.key` (key bindings), `<name>.map` and
  `.ma0`-`.ma3` (explored automap per level `Layer`; a cel above the atlas's 1,498 or a `Layer` of 100+ corrupts it,
  [engine-limits.md](engine-limits.md)). The mod's save folder also holds its own `Settings.json` (Quick Cast and
  the other options are per mod).
- The shared stash is a separate file per mod save folder (`SharedStashSoftCoreV2.d2i`); it must stay valid (an
  empty valid stash is fine). The folder also holds `Settings.json` and loot-filter files (`*.fltr`).

## The extended-save marker

The first four bytes after the signature tell the formats apart.

| Source | What it says |
|---|---|
| PluginSDK 0.4.0 README ("Inventory and Custom Player Pages") | Extended character version `0x44520006` and item version 6. Earlier extended saves (`0x44520005`, item version 5) still load and use the new format after their next save |
| A scan of the first 8 bytes of 1,051 `.d2s` files (test-slot characters and loader backups, written up to 2026-11-12 by loader 1.3.1) | 844 read `69 00 00 00` (retail: u16 `0x69`, then zero). 207 read `05 00 52 44` (u32 `0x44520005`, extended). **None** read `0x44520069` or `0x44520006` |

So the u32 at 0x04 is `0x44520000 | extended version`: `RD` (`0x52 0x44`) in bytes 0x06-0x07, the version in the low
16 bits. Both numbers are right for their loader version: **5** on saves from the loader and SDK this toolkit
targets, **6** after the SDK 0.4.0 custom-page change. A tool must not compare the whole u32 to one constant. Test
bytes 0x06-0x07 for `RD` to tell extended from retail, and read the low 16 bits as the extended version
(`testing/lod_checks.py` does the first).

`0x44520069` was an earlier note, never seen in a scan. It is most likely the retail version value `0x69` read
together with the `RD` bytes (inference). If a save ever shows `0x06`, it was rewritten by a newer loader, one-way
(below).

## Retail and extended compared

The format is chosen per mod with `[d2rcore.save_format] mode = "extended"` in the mod's
`d2rloader/config/d2rloader.toml` ([tables.md](tables.md)); retail is the default. Source tags: **doc** = the loader's
changelog (1.3.0-beta, 1.1.0-beta), guide or the PluginSDK README; **code** = read in this toolkit or in a public
Rust `.d2s` parser (v96-v105); **unverified** = not tested in game.

| Fact | Retail (`.d2s` v105) | D2RLoader extended | Source |
|---|---|---|---|
| Loads where | Retail D2R and D2RLoader | D2RLoader with extended mode on, nowhere else ("cannot load in retail D2R or with extended mode disabled") | doc |
| Character stat id ("gf") | 9 bits, list ends `0x1ff` (ids 0-510) | 16 bits, ends `0xffff` | code |
| Item stat id | 9 bits, ends `0x1ff` | wider (exact width not documented) | code / unverified |
| Class skills ("if") | exactly 30 bytes, one per class skill | more than 30 allowed | doc |
| Skill ids inside items (oskill, charges, chance-to-cast) | bounded by the stat's `Save Param Bits` | full skill id up to 32,767 | doc |
| Magic prefix / suffix id | 11 bits (rows 0-2047) | wider ("preserve the wider affix IDs") | code; doc |
| Rare name ids | 8 bits each | not stated | code |
| Unique / set id | 12 bits, shared field (rows 0-4095) | high ids need extended (tables go to 32,768 rows) | code; doc |
| Runeword id | 16-bit field | not stated | code |
| Item x / y | 4 bits per axis, so a grid is at most 16 x 16 | same | doc |
| Character file size | 65,535 bytes | **1 MiB** | doc |
| Custom player pages (plugin inventories) | 1, and the save does not record which plugin owns it | **up to 247**, each identified by plugin scope + plugin id + `logicalId` | doc |
| Hand-built items | retail layout decoded here | rejected: two hand-built items made characters vanish with correct checksums | observed |
| Public parsers | read v96-v105, widths from `itemstatcost` | none found | code; unverified |

Retail D2R character stat ids in 3.3 use ids 0-367 (build 93847 `itemstatcost` has 368 rows), well inside 510.

**The sidecar** `<name>.d2rl` (written beside both formats) records the saved mod, plugins, native save identity and
the `itemstatcost` schema (changelog 1.1.0-beta), plus the hashes above. A save from a missing, different, older or
incompatible environment gets one combined warning. The body layout beyond the hashes is not documented.

**Format is permanent per character.** Nothing documents a retail-to-extended or extended-to-retail conversion, and
the loader guide says changing the default mod does not convert a character. Turning extended on after players made
characters is therefore unverified at best: decide before the first release. The toolkit installer writes the extended
`d2rloader.toml` only when the file is missing, and never overwrites an edited one. The validator checks the 30-class-
skill rule only when extended saves are allowed; it does not check ids above the retail widths (511 stats, 2047
affixes, 4095 uniques and sets).

## Loader updates and extended saves

| Fact | Source |
|---|---|
| The extended format first shipped in loader 1.3.0-beta (2026-09-15); 1.3.1-beta followed on 2026-09-24. Every release is labelled beta | doc |
| It has changed once: SDK 0.4.0 moved the character version `0x44520005` to `0x44520006` and the item version 5 to 6. Older saves still load and **are rewritten in the new format on their next save**. Old custom-page items do not name their plugin: load and save them once with only their original page active | doc |
| Whether an older loader reads a save written by a newer one is not documented: assume one-way | unverified |
| Multiplayer checks the save format; TCP/IP also checks loader version, mod, shared plugins and the `itemstatcost` schema | doc |
| Server and shared plugins are recorded in the character's plugin history; client-only plugins are not | doc |
| A missing custom-page provider: the loader copies the save to `D2RLoader Backups\Recovery`, loads the character **without those items** and warns. If the copy fails the load stops; other placement errors also stop it | doc |
| The loader backs up offline characters and shared stashes before each session's first save, keeping 1-100 snapshots in `D2RLoader Backups` (one folder for every mod, not per savepath) | doc |

The extended layout belongs to the loader's authors: a loader update can migrate saves forward without asking. Keep a
corpus of test characters and load them in every candidate loader before a release.

## Savepath

`"savepath": "<X>/"` in modinfo.json sets the folder (`...\Saved Games\Diablo II Resurrected\mods\<X>\`), apart from
retail. It holds the mod's shared stash, `Settings.json`, loot filters, and beside each character its `.d2rl`, `.key`,
`.map` and `.ma0`-`.ma3`. **Changing `savepath` hides the old characters**: nothing moves or converts them, and
character select shows only the new folder. The same savepath under another mod loads these characters against
foreign tables (unverified; the default-mod trap is in [d2rloader.md](d2rloader.md)). Treat the value as frozen with
the tables ([tables.md](tables.md), "Freeze before release"). If a project's install step rewrites both modinfo files
from `mod.json`'s `savepath` on every install, `mod.json` is the value to freeze.
