# D2R 3.3 conveniences a classic port can keep or turn off

D2R adds comforts that a 1.09d to 1.13c-era game never had. A port decides, feature by feature, whether to keep each
one. This page lists the candidates, what the toolkit knows about where each lives, and what to check on the target
runtime (build 93847) before deciding. It holds no mod's choices: every "keep or cut" is the mod owner's call, and a
kept convenience is a deliberate departure from the classic game's economy and pace.

Status words: **data** = a table or file the mod can edit; **code** = the engine decides, so a plugin or nothing;
**unverified** = not tested on 93847 here. Inclusion in the list does not establish that a feature is available in the
mode you ship.

| Convenience | Where it lives | Keep or turn off | To verify on the runtime |
|---|---|---|---|
| Automatic gold pickup | code (no table column known) | no switch found: treat as part of the client | whether it works in your mode and whether a plugin can disable it |
| Personal stash capacity | data: `inventory.txt` stash rows and the stash layout grid (`bankexpansionlayouthd.json` `grid`); retail expansion stash is 10 x 10 ([engine-limits.md](engine-limits.md)) | resize the grid and the inventory row together, or ship a smaller stash page | the capacity D2R really gives in your mode before you write acceptance checks |
| Shared stash | state 186 `sharedstash` set on the player at game join; the stash proxy needs it ([debugging.md](debugging.md)); one `SharedStashSoftCoreV2.d2i` per mod save folder ([saves.md](saves.md)); layout tab `BankTabs` (personal, shared, gems, materials, runes) ([ui-layouts.md](ui-layouts.md)) | the tab count is a layout and loader-config matter (`[d2rcore.*]` stash tabs, [d2rloader.md](d2rloader.md)); the state is set by code | what a RotW-only shared stash does for LoD characters; do not assume it is shared across modes |
| Transfers between your own characters | follows from the shared stash | removing the shared stash tab removes the easy route | the transfer limits you want, and how they differ in LoD and RotW |
| Stackable advanced-stash tabs (gems, materials, runes) | data: `AdvancedStashStackable` on misc rows, set only in the RotW bank (`excel/`) ([tables.md](tables.md), "Two banks") | clear the flag per item | whether the tabs show in LoD mode (unverified) |
| Quick Cast | per mod, in the save folder's `Settings.json` ([saves.md](saves.md)); the skill picker honours `leftskill` / `rightskill`, and a targeted melee skill is not cast by it ([engine-limits.md](engine-limits.md)) | a player option; the mod can only shape which skills it suits through those columns | each skill that needs a target |
| Controller targeting and layouts | `controller/*.json` layouts, `basedOn` the PC layout, focus names must match widgets ([ui-layouts.md](ui-layouts.md)) | change a panel and its controller layout together | which targeting rules are code (unverified) |
| Extra item and stat information | the item tooltip, `ShowLevel` on bases, string keys ([strings.md](strings.md)) | partly data (columns, strings); the rest is client code | exactly which lines are data |
| Chronicle (RotW) | data column `disableChronicle` on unique, set and rune rows, present only in `excel/`; the UI is code ([tables.md](tables.md)) | set the column per row | whether it shows in LoD mode (unverified) |
| Loot Filter (RotW) | code and UI; filter files `*.fltr` in the mod's save folder ([saves.md](saves.md)) | no switch found | whether it shows in LoD mode (unverified) |
| Terror Zones and Heralds | data: `desecratedzones.json`, `Desecrated*` columns ([tables.md](tables.md), "Terror Zones") | off by data; patch: [examples/patches/no-terror-zones.json](../examples/patches/no-terror-zones.json) | the offline create screen toggle |
| Ladder-season item flags | data: `firstLadderSeason`, `lastLadderSeason` on unique, set, rune and treasure rows | edit the columns | which flagged rows still drop with no season running |

How to decide, per feature:

1. Find the reference behaviour in the classic game and the target behaviour in D2R 3.3, in the mode you ship.
2. Write what keeping it changes (storage pressure, wealth carried between characters, transfer friction, pace).
3. Check it on the runtime. Capacity and availability numbers from memory are not evidence.
4. Record the decision and an acceptance check in your mod's deviation list, so the departure is on purpose.
