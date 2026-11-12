# D2RLoader 1.3.1 and PluginSDK 0.4.0: capability matrix

Find a system in the matrix, read the verdict, follow the source. Target: D2R 3.3 build 93847 (PE `TimeDateStamp`
`0x6ab3782c`), D2RLoader 1.3.1.

Sources (tags used in the tables):

| Tag | Source | Trust |
|---|---|---|
| SDK | The PluginSDK README (SDK 0.4.0, plugin ABI 4; the loader accepts ABI 2 and 3) | Primary, official. Only the README was read, not each header |
| NOTES | D2RLoader's published release notes and download page | Primary, official |
| [d2rloader.md](d2rloader.md) | Observed on 1.3.1 / build 93847 | Local |
| [engine-limits.md](engine-limits.md) | Observed on build 93847 | Local |
| [new-game-systems.md](new-game-systems.md), [saves.md](saves.md), [d2r-93847-addresses.md](d2r-93847-addresses.md) | Design guidance, saves, RVAs for 93847 only | Local |
| TPL | `plugin-template/` | Local, working template |
| TEST | [docs/testing.md](../docs/testing.md), `testing/` | Local |

Caveat: the README describes SDK 0.4.0, but loader 1.3.1 ships SDK 0.3.0 services (see *Loader, SDK and game
versions* below), so some service fields are missing; they are marked in the matrix. Per-header detail needs a read
of the header before a feature relies on it.

## 1. How a plugin is built, loaded and tested

| Topic | Fact | Source |
|---|---|---|
| Toolchain | C++ DLL, Windows x64, CMake 3.29+, MSVC or clang-cl. Static CRT works | SDK, TPL |
| Minimum plugin | Embedded manifest resource (RCDATA id 1001 = ABI DWORD), exports `D2RLoaderGetPluginInfo`, `D2RLoaderLoadPlugin`, optional `D2RLoaderUnloadPlugin`. Without the resource the loader rejects the DLL as an "old alpha plugin" | SDK, [d2rloader.md](d2rloader.md) |
| Roles / flags | Exactly one of `Client`, `Server`, `Shared`; optional `ModScopedOnly`, `NativeHooks` (needed for inline hooks) | SDK |
| Where it loads | `<game>/mods/<mod>/d2rloader/plugins/` (mod-scoped, loaded first, replaces a same-id global copy) or `<game>/d2rloader/plugins/` (global, loads with every mod) | SDK, [d2rloader.md](d2rloader.md) |
| Which mod runs | `d2rloader.toml` `default_mod` (game-wide); a mod's own toml only overrides `[d2rcore.*]` | [d2rloader.md](d2rloader.md) |
| Config | One embedded default TOML (non-empty, <= 1 MiB); user config created once, never overwritten | SDK |
| Tables | The loader compiles the mod's `.txt` tables itself (no `-txt`); a shipped `.bin` becomes a "custom BIN set" that must be complete | [d2rloader.md](d2rloader.md) |
| First start | The first start after install or update builds a compiler snapshot and loads only D2R's own sounds table; mod sounds resolve to -1 (silent, can crash). Needs a second start; guard via `DataTablesLoaded` | [d2rloader.md](d2rloader.md) |
| Packaging | `d2rl plugin pack` builds the DLL and a companion MPQ (`d2rloader/<plugin-id>/`) | SDK |
| Logs | `<game>\d2rloader\logs\d2rloader.log`; crashes in `<game>\d2rloader\crashes\`; plugin log in `mods\<Mod>\d2rloader\logs\` | [d2rloader.md](d2rloader.md) |
| Build specificity | Engine hooks use RVAs valid for one image. The template checks the PE timestamp and each hook's entry bytes and turns parts off on a mismatch. Check game major.minor, not a build number | [d2rloader.md](d2rloader.md), [d2r-93847-addresses.md](d2r-93847-addresses.md), TPL |
| Debugging | Per-part off-switch file `<name>-off.txt`, a status console command, guards (build, environment, sound, item type ids) | TPL |
| Testing | Python harness: separate game "slots", locks, scripted launch, screenshots, keys, console lines, named checks with a results JSON. Click, key and console control need a plugin that implements the harness protocol | TEST |
| Reverse engineering | Ghidra workflow; each confirmed address is recorded in the plugin's `d2r.h` and the registry | [new-game-systems.md](new-game-systems.md), [engine-re.md](engine-re.md) |

## 2. Capability matrix

Verdict: **Yes** = a supported service or documented path. **Plugin** = possible with native hook / RE work.
**Data** = a table change only. **Limit** = a hard limit or a partial service.

| Area | Capability | Verdict | Detail | Source |
|---|---|---|---|---|
| Data | Read compiled tables from a plugin | Yes | `data_tables.h`, read-only | SDK |
| Data | Plugin-owned custom TXT/BIN tables | Yes | Staged activation; V1 columns `Ascii`, `Byte`, `Word`, `Dword`; strict TXT format | SDK |
| Data | Table rows | Limit | 32,768 per table; indexed tables are append-only (never reorder); D2R-only rows keep D2R numbers; mod stats go after itemstatcost row 368 | [engine-limits.md](engine-limits.md) |
| Data | Field widths, key lengths | Limit | Per dataguide `memSize` / `dataLength`; signed values must be written signed | [engine-limits.md](engine-limits.md) |
| Items | Discover, create, edit items; transactions | Yes | `item.h`, `item_interactions.h`; batches <= 4,096 ops; no equipment, cursor, belt, trade, corpse or ground moves in atomic moves. Scope notes: [charged-items.md](charged-items.md) | SDK |
| Items | Add properties to an existing item | Limit | `editItem` and existing-item transactions cannot. A unique can be rebuilt from its seeds with an added `PropertySpec` (a new item) | [d2rloader.md](d2rloader.md) |
| Items | Custom inventory pages | Yes | Retail save: 1 page. Extended save: up to 247 pages (numbers to 252), grid 1-16 x 1-16 | SDK, [d2rloader.md](d2rloader.md) |
| Items | Item details and tooltip getters | Limit | `ItemService` is 88 bytes on loader 1.3.1 against 112 in SDK 0.4.0. `getItemDetails`, `getItemTooltip`, `getItemPreviewTooltip` are missing (they crash if called). Check `HasItemServiceField` | [d2rloader.md](d2rloader.md) |
| Items | Tooltip lines | Limit | Listeners add lines; colour codes print literally; the client's copy of the item reads no custom stats | [d2rloader.md](d2rloader.md) |
| Items | Socket, stack, skill rules | Yes | `game_rules.h` | SDK |
| Items | Affix augmentation | Yes | Magic 1+1, rare 3+3 (6 total), rare jewel 4 | SDK |
| Items | Set items per set | Limit | 6 | [engine-limits.md](engine-limits.md) |
| Items | Runeword properties | Limit | 7 slots (`T1Code1-7`) | [engine-limits.md](engine-limits.md) |
| Items | Item spells (`pSpell`) | Plugin | 20 entries; 16-19 free; 20+ does nothing; hook the dispatchers for custom ones. Details: [charged-items.md](charged-items.md) | [engine-limits.md](engine-limits.md) |
| Items | New item stats | Limit | A new itemstatcost row needs `Save Bits` (stock maximum 24) or it is lost on reload; function-28 stats need `Save Param Bits` | [d2rloader.md](d2rloader.md), [engine-limits.md](engine-limits.md) |
| Cube | Custom recipe conditions (`op`) | Plugin | Unknown ops pass silently; hook the recipe search (`0x529090` / `0x529d50`) | [engine-limits.md](engine-limits.md) |
| Cube | Transmute interception | Yes | UI message `HoradricCubePanelMessage` / `Convert` can be consumed; the plugin does its own work on the game thread | [d2rloader.md](d2rloader.md) |
| Cube | Portal output | Data | `"Red Portal,lvl=<id>"` opens a portal to any level in the same act; only the `Cow Portal` output is fixed to the Cow Level | [engine-limits.md](engine-limits.md) |
| Skills | New server do-functions | Plugin | `srvdofunc` slots 172-190 free (191 total) | [engine-limits.md](engine-limits.md), TPL |
| Skills | New client do-functions | Plugin | `cltdofunc` 110-129 free | [engine-limits.md](engine-limits.md) |
| Skills | Skills per class | Limit | 30 in the retail save; more with the extended save format | [engine-limits.md](engine-limits.md), [saves.md](saves.md) |
| Skills | New calc codes | Plugin | The switch returns 0 for unknown rows; hook `0x33b3b0` / `0x3b9dc0`; keep ids < 256 | [engine-limits.md](engine-limits.md) |
| Skills | Formula limits | Limit | 255 chars; functions fixed (`min max rand skill miss stat sklvl sksrc cond`); no "has state" test | [engine-limits.md](engine-limits.md) |
| Skills | HD skill icons | Limit | <= 62 per class strip; class-less skills share one sheet | [engine-limits.md](engine-limits.md) |
| Skills | Skill tree layout | Limit | 6x3 per tab; more than 3 tabs works in HD, titles need art | [engine-limits.md](engine-limits.md) |
| Missiles | New hit / do functions | Plugin | Free slots: srvhit 61-70, srvdo 46-54, clthit 66-80 | [engine-limits.md](engine-limits.md) |
| States | State count | Yes | The assert above 511 is harmless; D2RCore syncs wide states up to 1,024; never patch state arrays | [engine-limits.md](engine-limits.md) |
| Events | Lifecycle events | Yes | Table loads, game state, quests, monster deaths (`lifecycle_events.h`) | SDK |
| Events | Unit-death property events | Plugin | D2R raises only its own events; hook `0x44db20`, raise via `0x44d570` | [engine-limits.md](engine-limits.md) |
| Spawns | Change monsters as they spawn | Plugin | Hook the spawn function `0x492cf0`; confirm which path the level populator uses | [new-game-systems.md](new-game-systems.md), [d2r-93847-addresses.md](d2r-93847-addresses.md) |
| Spawns | Boss and herald modifiers | Yes | `ModifierPolicy` in `encounters.h`: 0-9 modifiers, 0-2 auras, 0-10000 percent damage; the game may add fewer | SDK |
| Levels | New areas | Data + Limit | Level id <= 255; `Layer` < 100; clear `Position` on new mazes; ship every tile file; portals within one act only; automap level types fixed at 36; automap cels < the HD tiles' frame count (1499; more frames raise it) | [engine-limits.md](engine-limits.md) |
| Levels | Portals to ids > 255 | Plugin | The setter clears the high byte; write it afterwards | [engine-limits.md](engine-limits.md) |
| UI | Plugin panels and widgets | Limit | `panels.h`, `widgets.h`. On 1.3.1: no `setText` (fixed text only; show/hide works), `setWidgetEventMessage` is null (crash), no screen rect, buttons need a stock target `PanelManager:OpenPanel:<id>/<name>`. See [d2rloader.md](d2rloader.md), *Loader gaps* | SDK, [d2rloader.md](d2rloader.md) |
| UI | Overlay drawing | Limit | SDK: display-only, after the game UI, no input. On 1.3.1 the overlay service draws nothing (*Loader gaps*) | SDK, [d2rloader.md](d2rloader.md) |
| UI | Widget text, tooltip size | Limit | 4,095 / 16,383 UTF-8 bytes | SDK |
| UI | UI message and tooltip hooks | Yes | `shared_events.h` | SDK |
| UI | Edit existing layouts (HD json) | Data | Grid size on every inventory row plus the layout `cellCount` | [engine-limits.md](engine-limits.md), [ui-layouts.md](ui-layouts.md) |
| Input | Named actions and key listeners | Yes | Not during chat or text entry. Default keys are stored on first register in `input-bindings.toml`; later default changes do not reach existing players | SDK, [d2rloader.md](d2rloader.md) |
| Input | Mouse events | Limit | None in the SDK; watch the cursor item each UI update instead (*Loader gaps*) | [d2rloader.md](d2rloader.md) |
| State | Item stats | Yes | Saved with the character; needs Save Bits | [new-game-systems.md](new-game-systems.md), [engine-limits.md](engine-limits.md) |
| State | Plugin memory per game | Yes | Lost on exit | [new-game-systems.md](new-game-systems.md) |
| State | Quest flags, waypoints | Yes | Few free bits | [new-game-systems.md](new-game-systems.md) |
| State | Own file | Plugin | Your format; keep it next to the save; never touch a `.d2s` | [new-game-systems.md](new-game-systems.md) |
| Saves | Save format | Limit | `.d2s` v105 plus the D2RLoader `.d2rl` sidecar (SHA-256 hashes, size, checksum). Extended format: 16-bit stat ids, more class skills, plugin-owned pages. A mismatch makes the character vanish or grey out; hand-built items are rejected. An extended save cannot load in retail D2R or with extended mode off | [saves.md](saves.md), [engine-limits.md](engine-limits.md), SDK, NOTES |
| Saves | Missing page plugin | Yes | The loader backs up the save and loads without those items | SDK |
| Saves | Loader backups | Yes | `Saved Games\Diablo II Resurrected\D2RLoader Backups\` | [saves.md](saves.md) |
| Strings | String overrides | Yes | `localization.h`, namespaced JSON | SDK |
| Strings | Mod string ids | Limit | Matched on the low 16 bits; new ids from `next_string_id.txt` (28106) upward; printf placeholders must match | [engine-limits.md](engine-limits.md) |
| Resources | In-memory files, companion MPQ | Yes | `resources.h`; a mod can override plugin resources | SDK |
| Engine | Inline hooks, byte patches | Yes | Atomic, with rollback; needs `NativeHooks`; RVAs are build-specific | SDK, [d2r-93847-addresses.md](d2r-93847-addresses.md) |
| Engine | Detect patched bytes | Yes | `diagnostics.h` | SDK |
| Engine | Low-level D2RCore exports | Yes | `core_exports.h` (1-99), `reimplementation_exports.h` (2000-2999) | SDK |
| Engine | Renderer pool | Limit | 12 MB at start; it grows only if a plugin adds memory (tlsf_add_pool, from a classic port's plugin code, not re-tested here) or falls back to the heap; busy scenes crash without either | [engine-limits.md](engine-limits.md) |
| Engine | Coexisting with other gameplay plugins | Limit | The same hooks conflict; detect and warn, do not try to support. Method: [d2rloader.md](d2rloader.md), *Other plugins* | [d2rloader.md](d2rloader.md) |
| Misc | HTTP | Yes | Async HTTPS and loopback HTTP | SDK |
| Misc | Threading, inter-plugin events | Yes | `threads.h`, `plugin_communication.h`; payloads <= 1 MiB; keep callbacks short | SDK |
| Misc | Item types tested by number | Limit | Keep D2R's ids (jewl 58, rune 75, ...) | [engine-limits.md](engine-limits.md) |

## 3. Multiplayer implications

| Topic | Fact | Source |
|---|---|---|
| Scope | Local and TCP/IP games. The plugin network service is not available on Battle.net. TCP/IP uses local offline characters (public, unlisted/direct and LAN modes); default port TCP 4000 | SDK, NOTES |
| Server-side rules | Spawns, drops, portals and skills run on the server side, even in single player. The client sees only what D2R syncs (units, stats, states, items) | [new-game-systems.md](new-game-systems.md) |
| Roles | `Client` = presentation, `Server` = gameplay and saves, `Shared` = both. The host performs both roles, so a passing single-player check does not prove a change syncs over TCP/IP | SDK |
| Matching | `Shared` plugins must match host and client on id, version, ABI, scope and flags: bump the version every release. Client-only plugins are not recorded | SDK, [new-game-systems.md](new-game-systems.md) |
| Config | Settings in `[d2rl] match` (<= 64 paths) must be equal; the embedded list is authoritative | SDK |
| Compatibility token | A 64-bit token must match on both sides. The loader also checks loader, mod, shared-plugin and item-data compatibility | SDK, NOTES |
| Item changes | Only local games or the TCP/IP host change items; clients message the host (`getPeerPlayer`) | SDK |
| Game thread | A TCP/IP client has no game thread (*Loader gaps*) | [d2rloader.md](d2rloader.md) |
| Messages | Private plugin messages, <= 224 bytes | SDK |
| Save history | Server and Shared plugins are recorded in the character's plugin history | SDK |
| Implication | Private TCP/IP multiplayer works if all gameplay hooks are `Shared` and the versions match. State only the server plugin knows is invisible to clients unless it maps onto D2R's sync. Battle.net online play is out of scope. Which plugin holds what: [d2rloader.md](d2rloader.md), *Plugin flags* | SDK, [new-game-systems.md](new-game-systems.md) |

## Loader, SDK and game versions

Facts a release and its requirement checks depend on. Each is the loader's published word unless marked observed.

| Fact | Detail |
|---|---|
| Loader and SDK differ | The release notes pair loader 1.3.1 with SDK **0.3.0** (ABI 4). The SDK README and headers are **0.4.0** (ABI 4). Services new in 0.4.0 can be shorter or missing in the 1.3.1 binary: an 88-byte `ItemService` against 112, a 64-byte `WidgetService` against 208 (observed on build 93847). Compile against 0.4.0, but treat every optional field as maybe absent: check the service size (`HasItemServiceField`, `HasWidgetServiceField`) and never call past it |
| Four versions | SDK version, plugin ABI, service ABI and plugin version are separate. Ask the service for its size at load; do not infer it from the SDK version |
| Release | D2RLoader 1.3.1-beta (24 September 2026); D2R 3.3 support was added in 1.3.0-beta. The published ZIP's SHA-256 is `9286c6b5bff7f1043658411dbea305faa9698b6a455e6441668fc6d02c22aad7` (identifies the artifact on the download page; not re-verified here) |
| Game builds | Battle.net 3.3 build **93847** (the build every address in this toolkit is for). Steam builds seen: 3.3.**94995** ran the same unpacked image as 93847 (observed, [d2rloader.md](d2rloader.md)); 3.3.**93787** appears in a third-party plugin's requirement list beside Battle.net 93847 and is unverified here. Packed `D2R.exe` files differ per store, so hashes and build numbers differ; compare the image's PE timestamp |
| Conflicting docs | The loader wiki's overview still names an older 3.1 target, while its own build-93847 research and the release notes name 3.3. Treat the overview as stale |
| Closed source | The loader is closed source. Its installer is public and GPL, but that licence covers neither the loader nor the game, and no permission to redistribute the loader or game binaries was found. Do not ship them in a mod or release: point players to the official download. Players need their own game install |
| Updates | The loader's update check does not update mods or plugins. The download page marks its automatic installer as coming soon. A reproducible release records the game, loader, mod, plugin, data and config identities, and cannot assume an auto-update keeps the pinned target |
| Loader changes behaviour | Its release notes list gameplay fixes and backports, so the loader itself can change behaviour beyond a mod's choices. Record the loader version and enabled settings with every test |

## 4. Hard limits (for triage)

- Table rows 32,768; append-only indexed tables; D2R-fixed item type numbers.
- 30 class skills unless the extended save format; 62 HD icons per class strip.
- Free slots: srvdo 172-190, cltdo 110-129, item spell 16-19, missile srvhit 61-70.
- Level ids <= 255 for portals; `Layer` < 100; 36 automap level types; portals within an act.
- 511 states assert (harmless), 1,024 wide states supported, beyond that unexplored.
- Set 6 items; runeword 7 properties; formula 255 chars.
- All RVAs are build 93847 only.
- On loader 1.3.1: panel text cannot change; no widget screen rect; the overlay draws nothing; item tooltip getters
  missing; a TCP/IP client has no game thread.

## 5. Open

- Per-header detail of the 0.4.0 services (only the README summary was read).
- Whether the wiki or the plugin-samples repository documents services beyond the README.
- Behaviour above 1,024 states.
- Whether client-only visuals that D2R does not sync can be shown through the overlay or panels alone (on 1.3.1 the
  overlay draws nothing).
- Which listed hook points D2RLoader already hooks itself (check for `FF 25` at the entry before hooking).
- Maximum player count and dedicated-server support over TCP/IP.
