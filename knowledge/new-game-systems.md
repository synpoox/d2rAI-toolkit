# Adding a new game system

How to plan a feature D2R has no rows for: a mapping system, a new crafting bench, a currency, a challenge mode, a
new panel. A new skill or item is one table row and a patch. A new **system** changes what the game does, so it is
always part data, part engine plugin, and usually a project of several lanes.

Read [engine-limits.md](engine-limits.md) first. Most designs that fail ignore a limit listed there. Then find each
part of the design in [d2rloader-capabilities.md](d2rloader-capabilities.md) (what the loader and SDK give you, and
what they lack on loader 1.3.1).

## 1. Write it as what the player sees

Before any table or hook, list the steps the player goes through and what the game must do at each one. Example, for
a mapping system (map items that open a portal to a scaled area):

| Player does | The game must |
|---|---|
| Finds a map item | Drop it (treasure classes), roll its tier and modifiers (affixes), show them (tooltip) |
| Puts it in the cube and transmutes | Accept the recipe, consume the map, open a portal |
| Enters the portal | Lead to the right area, at the area level of the map's tier |
| Fights | Spawn monsters with the map's modifiers |
| Finishes | Drop the rewards; close the portal; let the area be used again |

Each row becomes one or more lanes. Rows that the game can do from tables are **data**. The rest is **plugin**.

## 2. Split data from plugin

Data first: many "new" behaviours are an existing D2R function with different table values. Add only what D2R lacks.

| Usually data (modkit patches) | Usually plugin (D2RLoader, from `plugin-template/`) |
|---|---|
| New item bases and item types (misc, itemtypes) | What a cube **output** does beyond D2R's built-ins (the "portal" output opens only the Cow Level) |
| Affixes and the stats they roll (magicprefix/suffix, itemstatcost, properties) | Reading an item's stats at the moment something happens |
| Areas: levels, lvlprest / lvlmaze, area level (`MonLvl*`), monster lists, density | Changing monsters as they spawn, or anything per game rather than per row |
| Drops (treasureclassex), recipes (cubemain), vendors | New cube conditions (D2R checks player ops 1-14 and item ops 15+ only; unknown ops pass) |
| Strings, item tooltips (itemstatcost `descfunc`), HD art, layouts | A new skill function (`srvdofunc` slots 172-190), a new calc code, a new event |
| Existing D2R functions reused with new values | State that lives longer than one action: timers, counters, "this portal belongs to that map" |

A good rule: if the answer to "how does the game know?" is "a column says so", it is data. If it is "something
must decide at run time", it is plugin.

## 3. Find the engine code

Start from a vanilla feature that already does something close, and follow its code:

| You need | Vanilla feature to start from | Where to look |
|---|---|---|
| A portal to a special area | The Cow Level recipe, the Pandemonium portals | Cube output "Red Portal" and the portal maker in [the registry](d2r-93847-addresses.md) (*Portals and objects*), `D2Game\src\Items\ItemMode.cpp` |
| Something when a skill is used | Any skill's `srvdofunc` | The server skill dispatcher; `plugin-template/src/skill_functions.cpp` |
| Monsters changed as they appear | Champions and uniques (they get extra mods at spawn) | The spawn-monster function in the registry; `Refs.java` on it lists the callers. Confirm which path the level populator uses |
| Something when a unit dies | "Cast on death" properties | The death function (engine-limits.md, *Events and spawns*) |
| A cube rule D2R can't express | A recipe with `op` conditions | The recipe search and input matcher (engine-limits.md, *Items, inventory, sets, runes, cube*) |
| A new panel | The stash or cube panel | Its layout json ([ui-layouts.md](ui-layouts.md)), then the client code that opens it |

Method: [engine-re.md](engine-re.md). Dump the image (`tools/dump_image.py`), analyse it once
(`tools/ghidra_analyze.ps1`), then query it: `StringXrefs.java` on an assert source path, `Refs.java` for callers,
`Decompile.java` / `Disasm.java` for the shape and the entry bytes. Check that D2RLoader doesn't already hook the
function (`FF 25` at the entry). Every confirmed address goes into the plugin's `d2r.h` with its signature, and into
[d2r-93847-addresses.md](d2r-93847-addresses.md) for the next person.

**Do a research spike first.** One lane answers "where would each hook go, and is it hookable?" before anyone writes
data. A system whose key hook turns out to be impossible is cheaper to redesign on day one.

## 4. Decide where the state lives

| Where | Lasts | Good for | Watch out |
|---|---|---|---|
| Item stats (itemstatcost rows on the item) | As long as the item; saved with the character | A map's tier and modifiers, charges, counters on gear | New stats need `Save Bits`/`Save Add` that fit the values; the extended save format needs D2RLoader ([saves.md](saves.md)) |
| Table rows | The whole mod | Anything fixed: tiers, reward tables | Indexed tables: append only, never reorder ([tables.md](tables.md)) |
| Plugin memory, per game | Until the game closes | Which area a portal belongs to, which modifiers are active, timers | Lost on exit. Fine for a map run, wrong for progress |
| Quest flags, waypoints | Saved with the character | Unlocks ("map device opened") | Few free bits; decide them once |
| A plugin's own file | Whatever you design | Account-wide progress | Your format, your bugs. Keep it next to the save, version it, never corrupt a `.d2s` |

Never move or resize D2R's save structures or unit state arrays (see plugin-template's *Rules*).

## 5. Server, client and multiplayer

- Game rules run on the **server** side of the game, even in single player. Spawns, drops, portals and skill effects
  are server work. Hook server functions for them.
- The client sees the results through D2R's normal sync: units, stats it already sends, states, items. Something only
  your plugin knows on the server is invisible to the client unless it maps onto those.
- Mark the plugin `Shared` (the template does) and bump its version with every release: host and client must run the
  same one in TCP/IP games.
- Split plugins by multiplayer scope, not by feature: gameplay in a `Shared` plugin, client-only code (panels,
  pictures, numbers) in a client-only one, which never forces a version match. A system gets **its own** plugin only
  when a player or mod would switch it on or off as a whole, it shares no hook point or function slot with another
  plugin, and it never calls another plugin; a large plugin is split into source files instead
  ([d2rloader.md](d2rloader.md), *Which plugin holds what*). What the loader and SDK can do for each part of a system:
  [d2rloader-capabilities.md](d2rloader-capabilities.md). Items with charges that are not used up:
  [charged-items.md](charged-items.md).

## 6. UI

Try these in order. Each one costs much less than the next.

1. **No new UI**: a cube recipe, an item, a tooltip line, an NPC's store.
2. **A changed panel**: an existing layout with new art or grids ([ui-layouts.md](ui-layouts.md), the `layout` and
   `panel` ops).
3. **A new panel**: a layout json plus client code that opens it and fills it. That is real RE work on the client
   side. Plan it as a separate lane, after the system works through the cube.

## 7. Check the limits

The ones new systems hit most (all in [engine-limits.md](engine-limits.md)):

- Level ids: portal links store a byte in many places, so keep new levels at id 255 or below. That leaves few free
  ids: count them before you design "one area per tier".
- levels.txt `Layer` below 100; clear `Position` on new maze levels; ship every tile file a level type uses.
- Portals link levels **within one act** only.
- The cube "portal" output opens only the Cow Level; unknown cube `op` values are ignored.
- Indexed tables: append only. Item type numbers D2R tests in code stay where they are.
- 30 skills per class; new events are never raised by D2R itself.

## 8. Split it into lanes

A typical order, with one PR each ([docs/ai-workflow.md](../docs/ai-workflow.md)):

1. **RE spike** (strong model): find and confirm every hook, write them into `d2r.h` and the registry.
2. **Data** (routine): items, affixes, stats, levels, recipes, drops, strings, art stand-ins. It builds and validates
   on its own and can be tested in game with no plugin (the items drop, the recipe is accepted).
3. **Plugin parts** (strong model), one part and one off-switch word each: for example `mapportal`, `mapmods`,
   `maplevel`.
4. **Tests**: one named check per row of the table in step 1 ([docs/testing.md](../docs/testing.md)).
5. **Art and polish**: real HD art, tooltips, a panel if wanted.
6. **Release** ([docs/release.md](../docs/release.md), [docs/distribution.md](../docs/distribution.md)).

## 9. Make it debuggable from day one

- One part word per hook in `g_parts`, so `<name>-off.txt` can turn each one off.
- A log line per part at load (`mapportal on`, or why it is off), and the part's counters in the status command.
- Refuse, don't guess: a hook whose entry bytes differ is not installed, and the system says which part is missing.

## Map hosting: repeatable maps on stock terrain

For a system that sends players to repeatable maps (build 93847, read from D2R's data and static code reading; nothing
here was run unless marked). Evidence tags: **[S]** data or static code, **[G]** a released mod's recorded in-game
behaviour or a shipped stock row, **[U]** unverified.

**Two ways to host a map:** send the player to a stock level, or append a **cloned `levels` row** that reuses a stock
`LevelType`, `lvlprest` DS1 or `lvlmaze`. D2R ships the clone pattern: Pandemonium 1-3 and the Finale (133-136) are
Act V rows on Act I/II/V tile sets that share their template's automap `Layer`, reached by a red portal from
Harrogath [S]. Stock DS1s already have HD presets, so a clone needs no new art.

- **Same-act rule.** Portals link levels within one act, so give every map level `Act=4` (Act V) whatever its tile
  set; Pandemonium and released mods do [S, G]. Terror Zones avoid the rule: nothing teleports ([tables.md](tables.md),
  "Terror Zones").
- **Original levels** (Worldstone Keep 128-130, Halls 122-123, Frozen Tundra 117, ...): no table work, stock HD terrain
  and waypoints, but they carry campaign state (quests, superuniques, waypoint flags). Levels are built once per game
  and a new game resets them, so "repeatable" means a new game or a different level; modifiers reach campaign content
  on that level for the rest of the game.

### Cloned `levels` rows

| Constraint | Value | Tag |
|---|---|---|
| Level ids | 138 rows (0-137, last Colossal Summit). The portal destination setter `0x34e9d0` keeps one byte: ids **<= 255**, about 118 free | S |
| Automap `Layer` | **< 100** (100-bucket map memory). Stock already uses 99, so clones **share** a template's layer, as Pandemonium does | S |
| Level types | fixed 36 for the automap; clones use stock types | S |
| Automap cels | <= 1498 | S |
| `Position` | 0 on new maze levels, or a null read on entry | S |
| World space | one Act V rectangle per level; overlapping rectangles swap stored units | G, not checked here |
| Mazes | some maze routines place stairs only for hard-coded ids (Tomb, Durance, sewers): clone tile sets that work for any id | G |
| Arrival | a red portal lands at the maze's first special room; a released mod adds a self-linked entry warp | G |
| Second entrance to an arena | client assert on mouse-over | G |
| Town ids | hard-coded (1, 40, 75, 103, 109): append only | S, G |

A clone carries its own `MonLvl*`, `MonDen*`, monster lists and treasure, so it can be a fixed tier as data and gives
a plugin a clean id test. It carries no quest scripts (those key on stock ids). Ids above 255 need the high byte
written after the setter, and the client packets are unverified [U]. Clones on other-act tile sets, entry warps and
world rectangles were not run on this build.

### Getting there

| Route | How | Notes |
|---|---|---|
| Data only | cube output `Red Portal,lvl=<id>` reaches any same-act level, no plugin | a released mod uses it for a labyrinth [G]. Modifiers are fixed per level row; gating is limited to recipe filters (`min diff`, player ops 1-14) |
| Plugin item use | hook the item-spell check and use dispatchers for spell 16; take the destination from misc `len`; check gates and free space before the item is consumed; call the cube Red Portal output `0x5da800(game, player, key, level, max)` (places object 60 and a return portal, counts per game) | recorded in game: town to a map and back, a second map refused, wrong town and wrong difficulty refused [G] |
| Cross-act | the portal routines refuse other acts (`0x3e2b5c8`) | an unofficial plugin hints the check can change; no source [U] |
| No portal (Terror Zone style) | mark a level the player already reaches as this game's map | the same-act rule never applies; needs campaign waypoints [U] |

### Modifiers, completion, reward

- A per-game stat list on monsters as they spawn (spawn-core hook `0x494a60`, max life multiplied directly) and on
  players while in the map (a per-frame add and remove), plus rewrites of the level's monster region (`MonDen`
  scaling, champion and unique packs, up to 13 groups; an added group was never seen to spawn) and an area-level hook on
  `0x508f80` [G]. A drop hook makes drops ethereal, socketed or corrupted [G]. Per-game state lives in D2R's per-game
  counter map (`game+0x1aac8`); a new game resets it [S].
- **Completion** has a hook but no "cleared" signal. The SDK reports monster deaths after the native drop (server
  thread, with level, monster and killer ids) and level changes, so a boss kill can end a map [S]. Nobody has located an
  area-cleared or progress counter: a region field at `+0x04` is unread and the Terror Zone `zone_completion_weight`
  has no known reader [U]. Same-game re-entry of a cleared level stays cleared.
- **Reward:** data (boss treasure classes, `TreasureClassDesecrated*`) or a plugin on the drop hook `0x43cd50` and
  SDK item creation.
- The one seam to cut when reusing a map plugin: its "is this a map level" range test. Replace it with a set of ids, or
  "this game's active map level", and monsters, players, drops and area level follow. Its RVAs are pinned to the 93847
  image.

### Options, cheapest first

| Approach | New work | Risks |
|---|---|---|
| Data-only `Red Portal,lvl=` to stock or cloned levels | cube rows, items | no per-map rolls, no completion or one-per-game state beyond recipe filters |
| Red portal to original Act V levels + plugin modifiers | gates, level set, map items | modifiers touch campaign content; repeat only by new game or rotating levels |
| Cloned Act V rows + plugin modifiers | `levels` rows, monster lists, treasure, map items | world-space overlap, entry landing, shared automap memory, per-clone validation |
| "Terrorize" a level the player reaches by waypoint | plugin "active map level" per game | needs campaign waypoints; collides with D2R's own Terror Zone; untried |
| Edit `desecratedzones.json` | JSON edits | time-scheduled, not player-driven; no zone API; modded ids offline untried |
| Cross-act portal | hook the act check | unknown client behaviour |
