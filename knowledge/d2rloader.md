# D2RLoader: facts and traps

What a mod that ships through D2RLoader 1.3.1 (PluginSDK 0.4.0) runs into on players' machines. Seen in a large
overhaul released to players. Plugin API details: [engine-re.md](engine-re.md) and
`third_party/PluginSDK`. What the loader and SDK can do, system by system, with the versions they ship:
[d2rloader-capabilities.md](d2rloader-capabilities.md).

## Starting a mod

After install, restart the game fully. For plugins or extended saves start `D2RLoader.exe` and select the mod;
otherwise `D2R.exe -mod <Name> -txt` also works. Use the slot harness for agent tests. For a player install,
set Default Mod and restart after the first cache-building start. See the first-start and Default Mod
sections below for the evidence and failure cases.

## How D2RLoader picks the mod

| Fact | Detail |
|---|---|
| `D2RLoader.exe` with no arguments reads `<game>\d2rloader\config\d2rloader.toml`, section `[d2rloader]` | It starts D2R with `<launch_arguments> -mod <default_mod>`. `-mod` is not allowed inside `launch_arguments`. The log shows the command line |
| `default_mod` is set in D2RLoader's own options | Gear on the character screen, Default Mod, Apply. It writes the game-wide file |
| A mod's own `mods\<Mod>\d2rloader\config\d2rloader.toml` | Overrides the `[d2rcore.*]` settings (save format, stash tabs, ...) and `[d2rloader.plugins] load_order`. It **cannot choose the mod** |
| `-txt` is not needed with 1.3.1 | D2RLoader compiles the mod's `.txt` tables itself ("Compiled N tables from TXT"). Shipping a `.bin` switches it to a "custom BIN set" that must be complete |

**Trap: `default_mod` names another mod.** A player with an old or renamed mod folder in `default_mod` runs that
folder, not what your installer just wrote. Your new build looks broken ("the fix didn't work"). Your installer or
plugin should read `default_mod` and warn when it is not your mod. If your installer offers to change it, change
only that key (keep comments, other keys, line endings, BOM), ask first, and never while the game runs (D2RLoader
rewrites the file).

## The first start builds a cache

The first start after installing or updating D2RLoader or D2R builds the **base compiler snapshot**
(`<game>\d2rloader\data\compiler\<version>\`). The log says "Preparing base compiler snapshot ... because no valid
snapshot exists". On that start the sound step compiles **only D2R's own sounds table**, not the mod's (with or
without `-txt`). Every mod sound name then resolves to -1:

- all new sounds are silent;
- D2R's client sound readers do not skip a bad id: a monster whose sound is -1 can crash the client when it comes
  into view.

Later starts log "Validated the current base compiler snapshot" and load the mod's sounds. The fix is a restart.
Make your plugin check the loaded sounds row count after each table load (D2RLoader's lifecycle service,
`DataTablesLoaded`) and tell the player to restart when it is lower than the mod's
(`plugin-template/src/sound_guard.cpp`). Put "start the game twice the first time" in your install notes.

## A plugin DLL needs its manifest resource

D2RLoader 1.3.1 reads a resource from the DLL before it calls anything in it: `RCDATA` id 1001
(`D2RL_PLUGIN_MANIFEST_RESOURCE_ID`) holding the plugin ABI version as a DWORD (`04 00 00 00` for PluginSDK 0.4.0).
A DLL without it is rejected even when its exports and `PluginInfo` are right; the startup list shows:

```text
[ERROR]      <name>.dll [global] — Plugin is not compatible with this D2RLoader version
  └ [DETAIL]     This looks like an old alpha plugin. Update the plugin before using it
```

Every plugin needs a `.rc` like `plugin-template/src/plugin.rc` (the SDK examples each have one) in its target
sources, with `RC` in the CMake project's languages. Keep `/W4 /utf-8` and other C++ flags behind
`$<COMPILE_LANGUAGE:CXX>` or `rc.exe` gets them.

**Also:** a plugin flagged `ModScopedOnly` loads only from `mods\<Mod>\d2rloader\plugins\` while that mod runs, not
from the game-wide `d2rloader\plugins\` folder.

## Other plugins

D2RLoader loads the active mod's plugins (`mods\<Mod>\d2rloader\plugins\`) first, then the game-wide ones
(`<game>\d2rloader\plugins\`), which load with **every** mod.

| Trap | What happens | What to do |
|---|---|---|
| A stray copy of your own plugin in the game-wide folder (an old manual install, or an old build without `ModScopedOnly`) or in another mod's folder | Two copies run, or the old one runs | Detect it at load and warn (log, screen, status command) |
| Another mod's gameplay plugin that hooks the same code, or rewrites tooltips, item spells, vendors | Wrong text, crashes that you can't reproduce | **Don't make your plugin compatible with them.** Detect and name them in your log and status command; tell players to disable them for your mod. If players want what they offer, add it to your mod |
| The game-wide plugins load after yours | A check at your load sees none of them | Check again later (a one-shot thread after ~15 s, and in your status command) |

How to detect: list the process's modules (`CreateToolhelp32Snapshot` / `Module32First`) and keep those whose path
contains `\d2rloader\plugins\`; ask each for `D2RLoaderGetPluginInfo` to read its `id`. d2rloader.log's `[PLUGIN]`
lines list them too. See `shared/plugin-common/src/env_guard.cpp`.

## How to check that another plugin's hooks coexist with yours

Do this before you bundle, recommend or merely tolerate a companion plugin. It is a reading task first, a game check
second.

1. **List its hook sites.** From its source (the `*Rva` constants and `InstallInlineHook` calls) or, without source,
   from its DLL (disassemble the install code; a hook writes `FF 25` or `E9` at a function entry). Also list the table
   slots it writes: function-table slots (`srvdofunc`, missile, aura and property tables), item event slots, and the
   itemstatcost rows and stat ids it claims.
2. **Compare with yours, by byte span, not by function name.** A hook at `function+24` and one at `function+30` clash
   when their patched spans overlap. A shared function entry, a shared table slot or a shared event slot is a hard
   clash: only one of the two can work.
3. **Read what each does on a clash.** Both check the entry bytes before they hook. The plugin that installs second
   sees bytes that differ from stock and either refuses that part or turns itself off (some accept one named owner).
   Load order decides the winner: mod-scoped plugins load before game-wide ones. Never "fix" this by skipping the
   byte check.
4. **Write the result down per plugin:** its hooks, which of them you share, and which of its features overlap yours
   as data (the same stat, the same table row). Shared hooks mean the two cannot run together; shared data means one
   must give way.
5. **Prove it in the game.** Load both, in the order players will have, and read the loader log and both plugins' logs:
   every part `on`, no "bytes differ" line. Repeat after you add a hook of your own.

If two plugins share a hook, do not try to make yours compatible: pick one, or move the feature into one plugin
(*Other plugins* above). If a companion is bundled with the mod, pin one version of it per release, so host and client
run the same one in TCP/IP games.

## Item service on D2RCore 1.3.1-beta

The SDK is newer than this loader (the release notes pair loader 1.3.1 with SDK 0.3.0; see
[d2rloader-capabilities.md](d2rloader-capabilities.md)). `ItemService` is 88 bytes here against 112 in PluginSDK 0.4.0, so `getItemDetails`,
`getItemTooltip` and `getItemPreviewTooltip` are missing, and calling them crashes the plugin. Check
`HasItemServiceField` before any optional field.

- Transmute reaches a UI message listener as target `HoradricCubePanelMessage`, command `Convert` (build 93847). The
  listener can return `Consume` and do its own work on the game thread.
- The `UniqueItems` row (Rotw bank, build 93847) is 348 bytes, with 12 property slots from offset 152, each
  `int32 id, par, min, max` (empty id -1). `id` is the Properties.txt `*Id` that `PropertySpec` takes.
- Without `getItemDetails`, a rolled value needs `editNativeItem` (`NativeHooks` flag) and a native stat read.
- Inventory item info has real seeds and item level on the game thread only; on the UI thread they read 0 and 1.
- `executeTransaction` can rebuild a unique from its own seeds with an added `PropertySpec`; the property survives
  save and reload and the unique's rolls stay. It is a new item, so socketed inputs must be refused or their contents
  destroyed.
- `editItem` and `executeExistingItemTransaction` cannot add properties.
- `ItemTooltipEvent.item` is the client's copy of the item. It reads no custom stats, and the handle differs from the
  player's. Use `getItemInfo` on the UI thread, then find the player's item by `runtimeId` on the game thread.
- A new itemstatcost row needs `Save Bits` to reach the save file; without them the stat is lost on reload. The
  largest `Save Bits` in the stock table is 24. Save Add lets it hold negative values.
- Rebuilding an already rebuilt unique from its seeds rerolls it (build 93847).
- Item tooltip listeners add lines, but `ÿc3`, `%c3` and `ÿc;` print literally there, and raw `\xFF` changes the
  tooltip's font.

## Versions and builds

| Fact | Detail |
|---|---|
| **Check the game version (major.minor, e.g. `3.3`), never a build number**, in installers and requirement checks | D2R ships the same program under different build numbers (advice from D2RLoader's author) |
| Steam and Battle.net builds | Steam's 3.3 build 94995 ran the **same unpacked image** (PE timestamp `0x6ab3782c`) as Battle.net's 93847. The packed `D2R.exe` files differ on disk, so file hashes and build numbers differ |
| What a plugin checks | The image itself: the PE `TimeDateStamp` of `context->exeBase` (plus the entry bytes of every hook). That is the real "same code" test. `context->buildVersion` / `buildName` are labels for the log |
| `context->buildVersion` | e.g. `3.3.94995` on Steam. Print it in your log and status command: it is the first thing to read in a player's log |

## Files D2RLoader keeps

| File | What it is | Trap |
|---|---|---|
| `<game>\d2rloader\logs\d2rloader.log` | Loader log: plugins, table compile, asserts after "startup complete" | Ask players for it with every crash |
| `<game>\d2rloader\crashes\` | Crash reports (`d2r-crash-report ...`, `d2r-lastresort-crash-report (<date> UTC pid-N).log`) | See [crash-triage.md](crash-triage.md) |
| `<game>\d2rloader\config\input-bindings.toml` | The key of every action a plugin registers, stored **the first time** it is registered (`primary_key = <virtual-key code>`) | Changing a default key in a new plugin version does **not** reach players who ran the old one. Your installer must drop the stale entry, or tell players to rebind |
| `<game>\d2rloader\data\compiler\<version>\` | Table compiler snapshot | Missing = the next start is a cache-building start |
| `<game>\mods\<Mod>\d2rloader\logs\` | Your plugin's own log (`context->pluginLogPath`), written by `LogInfo` / `LogWarn` / `LogError` | Ask players for it too. Write one line per part at load, your version, D2R's version, the image stamp, the mod and your DLL's path |

## The plugin's own log: what to put in it

A player's log is often all you get. Make it answer the first questions without a reply:

- `<plugin> <version> loaded (mod <Mod>, D2R <buildVersion>, image 0x<stamp>, file <path>)`
- one line per part: `on` / `off: <why>` / `partial: <what failed>`
- the off-switch words in effect
- the other plugins (after they have loaded)
- warnings that point at the fix ("Close the game and start it again")
- before risky actions (spawning a rare monster, opening a portal), one line saying what is about to happen, so a
  log that ends there shows it

Keep it short in normal play: count repeated events and log the 1st, 100th, 10,000th.

## Plugin flags

The template declares `Shared | ModScopedOnly | NativeHooks`:

- **Shared**: runs on server and client; recorded in the character's plugin history; must match between host and
  client in TCP/IP games, so bump the version with every release.
- **ModScopedOnly**: loads only from the mod's plugin folder while that mod runs.
- **NativeHooks**: may patch game code.

### Which plugin holds what: split by multiplayer scope

D2RLoader requires `Shared` plugins to match between host and client, so a plugin that is only a client change must
never force that match. A way to cut a mod's engine code into plugins:

- **One plugin per multiplayer scope, not per feature.** Gameplay rules (skill and hit functions, cube ops, item
  rules, server hooks) go in a `Shared` plugin that is host-authoritative from the start. Client-only code (panels,
  pictures, quantity numbers, automap) goes in a client-only plugin, so it can be dropped without changing gameplay and
  never forces a version match. One DLL for everything makes everything `Shared`; one DLL per feature leaves dozens of
  versions to keep matched.
- **A system gets its own plugin only when all three hold:** (1) a player or another mod would turn it on or off as a
  whole; (2) it shares no hook point or function slot with another plugin; (3) it never calls another plugin. If the
  second fails, the code stays together: for example item rules that share one event slot and the damage path.
- **Size is no reason to split.** Split a large plugin into source files; the off-switch words already leave single
  parts out ([new-game-systems.md](new-game-systems.md), *Make it debuggable from day one*).
- **Plugins do not call each other.** A client-only plugin reads what it needs from the tables or from D2R's synced unit
  state. The SDK has plugin-to-plugin events (`plugin_communication.h`); this is a design choice to keep each plugin
  removable, not a loader rule.
- **Per-build RVAs live in one header per build**, shared by all plugins as a static library. On an unknown build a
  plugin logs and leaves the feature off.
- A bundled companion may be `Shared`; pin one version of each per release.

## Plugin panels (D2RLoader 1.3.1-beta, build 93847)

- `setWidgetEventMessage` is a null entry on this loader, and calling it crashes: check `HasWidgetServiceField` first.
- The widget service has no `setText`: its table ends at `getInputText`, and calling past the end crashes. `setWidgetVisible`,
  `setWidgetEnabled`, `findPanel` and `findWidget` work, so a panel can show or hide fixed text but not change it.
- A button whose `onClickMessage` has an unknown target is never dispatched. Use a stock target,
  `PanelManager:OpenPanel:<plugin-id>/<name>`, then read `event->text` in a UI message listener and consume it.
- Retail saves allow one custom player page: a second `registerPlayerPage` returns `Conflict`. Items on a page are saved
  with the character and stay there when the panel closes.

## TCP/IP multiplayer through D2RLoader (1.3.x)

Blizzard's game has no TCP/IP; D2RLoader adds it (its TCP/IP page, https://d2rloader.net/tcp-ip.html, and changelog).
Read from those pages, not run here: **unconfirmed** marks what no page states.

- Turn on *Show TCP/IP Button* (Settings, General), pick an **offline character**, then *Multiplayer* beside *Play*.
  Battle.net characters are not used. A mod is started with `-mod <name>` (`-txt` is not needed with 1.3.1).
- Since 1.2.0-beta a Multiplayer screen offers *Browse Games* and *Host Game*, with three host modes: **Public**
  (listed in the browser by heartbeat, filter by mod, difficulty, Terrorized), **Unlisted/Direct** (join by Game ID or
  address) and **LAN Only** (Direct Join). The game itself runs on the host's PC.
- Default **TCP port 4000** (`game_port`). The loader tries automatic router setup (NAT-PMP since 1.2.1) and shows a
  *Hosting status*; some routers still need a manual forward. IPv4 only (1.2.1-beta).
- What the host checks before a client enters: loader version, active mod, Shared plugins, the `ItemStatCost` schema
  (1.1.0), memory patches, map layout, movement, collision and animation timing data (1.2.1) and the save format
  (1.3.0). It does not make different mods compatible. Clients older than 1.2.1-beta cannot join a 1.2.1 host.
- Plugin roles and matching are in [d2rloader-capabilities.md](d2rloader-capabilities.md), *Multiplayer implications*:
  `Shared` plugins must match by id, version, ABI, scope and flags; `[d2rl] match` lists up to 64 config paths that must
  be equal; only the local game or the host changes items (a client sends a plugin message of 224 bytes at most), and a
  TCP/IP client has no game thread.
- Saves are each player's own local characters, so nothing stops an edited character joining (no page claims
  otherwise). Server and Shared plugins go into the character's plugin history.
- Player count per game: **unconfirmed**. VPN tools are not mentioned by D2RLoader; a virtual LAN with LAN Only or
  Direct Join should work the same way, **unconfirmed**. The loader is Windows only; consoles have no route.

## Loader gaps (D2RLoader 1.3.1-beta, build 93847)

Things the SDK 0.4.0 headers promise or imply that this loader does not do. Found by building client UI and item
handling on it. Each has a native workaround, so check the service first and keep the SDK path as the plan.

| Gap | What happens | Workaround |
|---|---|---|
| `WidgetService` has no screen rect | The service is 64 bytes and the headers need 208 (the log reads `widget 1 (size 64, needs 208)`). There is no `getWidgetScreenRect`, so a plugin cannot learn where a widget is on screen | Hook D2R's item draw `0x2A72D0` (widget, item), which every item widget calls once per item: do what it does, then draw. The position comes from the grid's vtable ([d2r-93847-addresses.md](d2r-93847-addresses.md), *Inventory grid widget*). The loader's author has said the call is coming: re-check the service size on each loader update |
| `OverlayService` draws nothing | The service exists and accepts calls, but nothing appears on screen | Draw with D2R's own text draw `0x902E20` (text, int32 rect[4] in screen px, font block, scale) from a hook; build the font block like D2R's defaults |
| TCP/IP clients have no game thread | `runOnGameThread` returns `Unavailable` on a TCP/IP client, so work queued to the game thread (finding the server's copy of an item, `splitStack`) does nothing there | Send a plugin message to the host (<= 224 bytes) and do the work on its game thread. Until then, say in the status line that the feature is host-only |
| No mouse event, and no event for an item put down from the cursor | `ItemInteractionService` skips cursor paths, so a plugin cannot see a click or a drop | Watch the cursor item on every UI update (UI thread), note what left it and which modifier keys were down, then act in a game-thread job |
| UI-thread handles are stale on the game thread | The UI thread's player handle points at the client's unit; item seeds and item level read 0 and 1 there | Find the server's item by `runtimeId` on the game thread |
