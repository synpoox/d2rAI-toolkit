# Cheat commands: setting up an in-game test fast

D2RLoader's in-game console takes every cheat below as `cheat <command> <arguments>`, after `debug_mode` turns cheats
on. Use them to set up a test (spawn the item, the monster, the level, the stats) instead of playing to the spot: an
agent drives the console far more reliably than clicks and movement ([testing.md](../docs/testing.md), "Controlling
the game").

## What we saw in game (observed)

- **The Item Spawner's lines.** The debug menu's Item Spawner sends console lines; its window needs double-clicks, which
  the test harness cannot send, so type the lines yourself. `cheat item` does nothing.
  - A base item: `cheat spawn <item code>,inv 0` (for example `cheat spawn wnd,inv 0`) puts it in the inventory.
    Without `inv 0`, or with no room, it drops on the ground ("I am overburdened").
  - Quality: `typ <letter>` with a space, `cheat spawn t11,typ m,inv 0` for magic, `typ r` for rare (D2R's own test
    lines use `typ m`). `typ=<letter>` did not change the quality: read the tooltip.
  - A unique: `cheat uniques <row>`, the row zero-based in the mod's built `uniqueitems.txt`
    (`out/data/global/excel/`). It drops on the ground.
  - `cheat idall` identifies every item you carry. An unidentified item can't be equipped ("I can't use this yet").
- **Durability after a reload.** Spawned items come with normal durability and keep it while you play, but every item
  reads `Durability: 0` after the game is saved and loaded again, and a 0-durability item has its stats switched off.
  Spawn fresh items after each load, and hover them before a test.
- `cheat gold <n>` did not add gold, although D2RLoader's list below says it does.
- **The cursor item (verified in game, #316).** A click on an inventory item picks it up; a second click puts it down
  (an occupied target swaps). `shift`+click equips it (`game_ctl click FX FY left shift`; right-click did nothing,
  `ctrl`+click drops it). The held item hides tooltips and is drawn as a ghost under the cursor, on a dark green cell
  block (about 17,48,15) where it fits. Tinted cells show only while the inventory is open, so a shot with the
  inventory closed shows nothing of a held item, and a hovered item (cursor empty) gets the same green cell, with its
  tooltip. **A shot never proves an empty cursor.** Before each click open the inventory (I) and run
  `game_ctl cursor`: it parks the cursor on a free 2 x 4 block and prints `ITEM HELD`, `empty`, or `unknown` (inventory
  closed or no free block). It cannot name the held item: there is no console or harness read of the cursor item
  (the SDK's `getCursorItem` needs a plugin; not built). A held item turning cells tinted is not a mod bug.
- To pick up a ground item, hold Alt so the item labels show, then click the label.
- Escape twice saves and exits to the character screen.
- **Warp to an exact spot:** `cheat goto <levelId>,<x>,<y>` takes absolute world subtile coordinates, not
  level-relative ones. `x = OffsetX*5 + tileX*5 + 2`, `y = OffsetY*5 + tileY*5 + 2`, where `OffsetX`/`OffsetY` are the
  level's row (by `Id`) in the mod's built `levels.txt` (`out/data/global/excel/`) and `tileX`/`tileY` is the DS1 tile
  (a tile in a coverage PNG). The `+2` lands mid-tile. Example: level 144, a mod-added level whose levels.txt row has fixed OffsetX 3000,
  OffsetY 2550: tile (109,75) is `cheat goto 144,15547,13127`. The rule holds for any level with fixed offsets in the table; a
  randomly placed level's origin isn't in the table. `cheat goto <levelId>` alone lands at the level's entry.
  From an HD preset position (10 units per tile): `x = OffsetX*5 + hdX/2`, `y = OffsetY*5 + hdZ/2`. A map with several
  DS1 variants rolls one per game, so a spot only lands where intended if that variant loaded.

## Test characters and game versions

- **Use a Reign of the Warlock (RotW) character** (character creation's Game Version, the default). A Classic or Lord of
  Destruction (LoD) character plays D2R's vanilla `excel/base/` tables, which a RotW-only mod never writes: the vanilla
  skill tree, none of the mod's skills, and `cheat sklvl` of a mod skill does nothing. On the character select screen an
  LoD character's banner shows an X badge.
- **`cheat expansion 2` does not convert a character to RotW: it crashed the game.** Make a new RotW character instead.
  (Observed in a game slot; see also the `expansion` warning below.)
- The test character's level, experience and points: [testing.md](../docs/testing.md), "The test character".

## Warnings

- `expansion` can change the character's version on save: do not use it on a test character you keep.
- `debugbreak` executes an `int3` and kills the game without a debugger attached. Do not run it.
- Item-quality toggles (`sio`, `uio`, `mio`, `rio`, `normalitemsonly`, ...) stay on until set back to 0.

## Common commands

The ones tests use. All 157, one grep away: [cheat-commands-all.md](cheat-commands-all.md).

| Command | Arguments | Description |
|---|---|---|
| `itemspawnlevel` | `<level>` | Sets the global default item-spawn level; accepts 1 through 120. |
| `clearinventory` | `—` | Removes carried/equipped items through native item-location validation and destruction. |
| `savecheatitems` | `<0\|1>` | Sets whether cheat-spawned items remain saveable; prefer the ImGui Cheat Settings toggle. |
| `experience` | `<amount>` | Adds the signed amount to the player's Experience stat. |
| `waypoints` | `—` | Unlocks every valid waypoint row for the current game version/difficulty. |
| `ospawn` | `<Objects.txt row\|name>[,<count>] [@ <x>,<y>]` | Spawns a valid Objects.txt row at the selected location; names are resolved to rows and count defaults to 1. |
| `mspawn` | `<MonStats.Id\|row>[,<count>[,<ai>]] [@ <x>,<y>]` | Spawns monsters using an exact MonStats.Id or numeric row id. |
| `stat` | `<statName>,<amount>` | Sets an ItemStatCost stat with layer/parameter 0; HP/mana stats 6–9 are shifted by 8. |
| `sklvl` | `<skillName>,<level>` | Looks up a skill by name and sets/adds it at the requested level. |
| `skadd` | `<skillName>[,<level>]` | Looks up a skill, adds it, and optionally sets its level. |
| `skdel` | `<skillName>` | Looks up a skill and sends the native level-0 delete update. |
| `sockets` | `<0-6>` | Sets the forced socket count for newly generated eligible items. |
| `ethereal` | `<0\|1>` | Toggles the forced ethereal override for newly generated eligible items. |
| `uniques` | `[destroy,][start][,end]` | Spawns forced unique items over an optional UniqueItems range. |
| `sets` | `[!setIndex\|destroy,][start][,end]` | Spawns forced set items over an optional SetItems range. |
| `durability` | `<amount>` | Sets carried inventory-grid item durability, clamped by max durability. |
| `quantity` | `<amount>` | Sets carried stack quantity, clamped by max stack size, and sends an update. |
| `invincible` | `<0\|1>` | Sets the raw player no-damage/invincibility helper. |
| `mongod` | `<0\|1>` | Sets the monster receive-no-damage flag. |
| `monfreeze` | `<0\|1>` | Sets the monster freeze flag. |
| `goto` | `<level>[,<x>[,<y>]]` | Warps to a level by name/id, optionally resolving the room from x/y. |
| `spawn` | `<code>[,<option>...]` | Spawns items by Inventory.txt code; supports num, qty, lvl, nid, typ, pre/suf, seeds, inv, and spc. |
| `idall` | `—` | Identifies carried inventory items in native inventory modes 1 or 3. |
| `monster` | `[player] [dead] <monster\|!id\|unique:id\|super:id\|form:id> [@ <x>,<y>]` | Spawns monsters with player/dead and unique/super/form test branches. |
| `mspawnwithstats` | `<monster>[;option...][;stat=value...] [@ <x>,<y>]` | Spawns custom-stat monster/dummy tests. |
| `skillpoints` | `<amount>` | Grants unspent skill points when amount is positive. |
| `resetskills` | `—` | Calls the native player skill reset helper. |
| `save` | `<anything>` | Saves all players when any non-empty argument is supplied. |
| `nogethit` | `<0\|1>` | Toggles the raw no-get-hit reaction debug flag. |
| `quests` | `—` | Completes quest progress through Act 5 Quest 6 for the current difficulty. |
| `level` | `<level>` | Raises the player up to the class-clamped level through level-up side effects. |
| `god` | `[0\|1]` | Sets player no-damage, stamina cheat, and mana cheat; no argument toggles. |
| `speedup` | `<amount>` | Sets VelocityPercent, AttackRate, and FasterCastRate to amount. |
| `itemgridclear` | `[bodyLocation]` | Removes inventory-mode 0 items, optionally filtered by body location. |
| `killmonster` | `—` | Finds a nearby monster and kills it. |
| `shrine` | `<id> [@ <x>,<y>]` | Spawns object id 86, maps/clamps shrine type, and attaches Shrines.txt data. |
| `cubemake` | `<recipe>[,<count>]` | Creates Horadric Cube recipe output items directly; refuses recipes manipulating inputs. |
| `setmana` | `<amount>` | Alias for depletemana. |
| `sethealth` | `<amount>` | Alias for depletehealth. |
| `heal` | `—` | Legacy raw heal helper: sets current HitPoints to max HitPoints. |
| `stashfill` | `[count]` | Asynchronously fills stash space with random valid stashable weapon/armor items. |
