# HD graphics: formats and rules

D2R draws HD from `data/hd/...` and classic ("legacy", G key) from `data/global/...`. Both are loaded: some classic
files are needed even in HD. A mod overrides any file by shipping the same path in its MPQ folder.

## `.sprite` (SpA1) format

All HD UI pictures (items, panels, skill icons, buttons) are `.sprite` files, plus a `.lowend.sprite` at half size
for the low graphics setting.

| Offset | Type | Value |
|---|---|---|
| 0x00 | char[4] | `SpA1` |
| 0x04 | u16 | version **31** |
| 0x06 | u16 | frame width (single-frame sprites: = width; strips: one frame's width, e.g. 130) |
| 0x08 | u32 | total width (strip: frames x stride) |
| 0x0c | u32 | height |
| 0x10 | u32 | 0 |
| 0x14 | u32 | frame count |
| 0x18 | u32 | 0 |
| 0x1c | u32 | 0 |
| 0x20 | u32 | pixel data size (width x height x 4) |
| 0x24 | u32 | 4 |
| 0x28 | | RGBA8 pixels, row by row, top to bottom |

Verified on D2R's own `amskillicon.sprite`: v31, frame width 130, width 7920 (60 frames x 132), height 130, 60
frames, size 4,118,400. Maximum texture width **16,384 px**. Write premultiplied-alpha-aware scaling (bilinear with
alpha weighting) so edges don't go dark.

`.lowend.sprite`: the same header and layout at half the pixel size.

## Item pictures

| Rule | Value |
|---|---|
| Inventory cell | **98 px** HD, **49 px** lowend (classic 28 px; scale x3.5) |
| Sprite size | `invwidth x 98` by `invheight x 98`, picture centred |
| Location | `data/hd/global/ui/items/<weapon|armor|misc>/<folder>/<name>.sprite` (+ `.lowend.sprite`) |
| Asset name | the path under that table folder without extension, e.g. `axe/hand_axe` |

Maps under `data/hd/items/` (JSON arrays of one-key objects):

| File | Key | Value |
|---|---|---|
| `items.json` | base item `code` | `{ "asset": "axe/hand_axe" }` |
| `uniques.json` | uniqueitems `index` lowercased, spaces and hyphens -> `_`, apostrophes dropped (`Buriza-Do Kyanon` -> `buriza_do_kyanon`) | `{ "normal": ..., "uber": ..., "ultra": ... }` (picture per base tier) |
| `sets.json` | setitems `index`, same normalisation | same as uniques |

**A unique's own art needs a non-blank `invfile`** (build 93847): with it blank the game shows the base item's picture and ignores `uniques.json`. All 143 stock uniques with their own art set it; the base item's `invfile` is enough.

**Every item code, unique and set item needs an entry pointing at an existing sprite.** A missing one makes the
client request `data/hd/global/ui/items/<table>/[default_unit]` every frame (blz-log spam) and then crash (vendor
screen, Item Spawner: access violation at D2R+0x29538e). Entries for uniques/sets the mod removed must go too (a
dangling entry for a removed unique crashed the Item Spawner). Stopgap: map new items to a D2R picture of the same type until art
exists.

Three more `items.json` facts (D2R 3.3, build 93847; taken from the classic-import item code's findings, the draw behaviour was not re-measured against a live client here, so treat them as **unverified** until a lane confirms them in game):

- **The key is the first 3 characters of the code, plus a space.** The loader `0x6635a0` writes a space (0x20) at byte 3 of the key (`0x663a14`, patch address `0x6639f9`), while the picture lookup `0x662fb0` compares the whole code dword (+0x80). A 4-character code therefore never finds its entry (no picture), and its entry overwrites the one of its 3-character prefix. Evidence: read from the code in Ghidra, build 93847; an earlier note here said "bit 0x20 in the 4th byte", which the loader does not do. Use 3-character codes.
- **An asset is looked up only in the item's own table folder** (`weapon`, `armor` or `misc` under `global/ui/items/` and `items/`). A picture borrowed from an item of another table (for example a misc item showing a weapon's sprite) must be copied into the borrowing table's folder first, sprites and unit file both.
- **A dropped item is drawn from the asset's unit file `data/hd/items/<folder>/<asset>.json`.** An asset with only a `.sprite` shows in the inventory but the item is invisible on the ground. A new picture needs a unit file too: copy the one of the D2R asset it stands in for.

## Skill icons

| Rule | Value |
|---|---|
| Classic file | `data/global/ui/spells/<xx>skillicon.dc6` (shared: `skillicon.dc6`) |
| HD file | `data/hd/global/ui/spells/<class>/<xx>skillicon.sprite`: `amazon/amskillicon`, `sorceress/soskillicon`, `necromancer/neskillicon`, `paladin/paskillicon`, `barbarian/baskillicon`, `druid/drskillicon`, `assassin/asskillicon`, `warlock/waskillicon`; non-class skills `submenu/skillicon`; mercenary skills `hireables/hrskillicon` (skilldesc `HireableIconCel`) |
| Referenced as | `Spells\<Class>\<Xx>Skillicon` (skillstreepanelhd.json `skillButtonFile`) |
| Frames | two per icon: normal, then pressed. skilldesc `IconCel` = frame index (even) |
| Size | **130 px** icons, **132 px stride**, one horizontal strip; D2R draws icons at the sprite's pixel size (no scaling to the slot) |
| Capacity | 16,384 / 132 / 2 = **62 icons** per strip at full size; more icons need smaller frames (looks small) |
| Shared sheet | Every class-less skill (Attack, Throw, item charges and oskills) reads `submenu/skillicon` by `IconCel`, the same cel in classic and HD. Its 62-icon cap is shared by all of them: choose which item skills keep an icon (most granted first) |
| Converting a classic mod's sheets | Class sheets are pairs (normal, pressed), but a classic **shared** sheet may hold **one frame per icon**. Read each sheet's real layout: rounding every frame down to even showed the previous icon for every odd frame |

Skill tree backgrounds: `Spells\Skill_Trees\<Xx>Skilltree` (`skillBackgroundFile`, one per class).

## Panel backgrounds

| Rule | Value |
|---|---|
| Size | **1162 x 1507** (`$LeftPanelRect` / `$RightPanelRect` in `_profilehd.json`) |
| Reference | layout `"filename": "PANEL\\x\\y"` = `data/hd/global/ui/panel/x/y.sprite` (case-insensitive) |
| From classic 512 x 704 art | scale x 2.2695 across, x 2.1406 down |
| Examples | `PANEL\\Inventory\\Classic_Background`, `PANEL\\Inventory\\Background`, `PANEL\\Horadric_Cube\\HoradricCube_BG`, `PANEL\\Stash\\StashPanel_BG_Personal` / `_Shared` |
| Blank background | `PANEL\\panel_bg`: frame and header only. The Add Sockets and Cube backgrounds have their slots baked in |
| Stock pieces for new panels | `PANEL\\Inventory\\Inventory_Paperdoll_Weapon` (197 x 392, an empty 2x4 slot), `Lobby\\Final\\LobbyArrowLargeR` (94 x 108, 4 frames; an `ImageWidget` takes `"scale"` in its rect) |

Panel art may hold things D2R draws itself elsewhere (a gold box where D2R's stash tabs go): cut and move them in
the sprite build step. See [ui-layouts.md](ui-layouts.md).

## Missiles

- `data/hd/missiles/missiles.json`: one object, `"dependencies": {...}` first, then **missile name (lowercased) ->
  model name** (no vanilla missile name has a capital, so whether D2R lower-cases a mod's `ZharBolts` before the
  case-sensitive lookup is unproven: write both spellings); models are `data/hd/missiles/<model>.json` (+ particles/textures).
- `CelFile` in missiles.txt is used **only by the classic renderer**.
- A missile missing from the map is **invisible in HD** (it still works). Map new missiles to a D2R model with a
  similar look; `"null"` for invisible ones. A good automatic stopgap: the model D2R uses for a vanilla missile with
  the same `CelFile`.

## Overlays (auras, cast effects, state visuals)

- overlay.txt `Character` -> folder: `data/hd/overlays/<Character>/<overlay>.json` (name = overlay key). D2R's
  folders: `common` (141 rows), `paladin` 45, `monster` 35, `sorceress` 29, `druid` 26, `warlock` 25, `assassin` 10,
  `amazon` 6, `necro` 6, `barbarian` 4, `object`, `objects`, `npcs`, `item`, `test`.
- **Empty `Character` = no HD overlay** (classic still draws `Filename`). Symptoms: no aura glow, no cast effect,
  Whirlwind with no spin effect (only the get-hit frames show).
- New overlays: copy a D2R overlay json into your folder, or reuse D2R's overlay row.

## Player animations (HD state machines)

- `data/hd/character/player/<class>/<class>_state_machine.json` (amazon, assassin, barbarian, druid, necromancer,
  paladin, sorceress, warlock; barbarian and sorceress also have a `_shell` variant).
- JSON: `states` (each `AnimationState` has `stateId`, `modeId`, `skillIndex`, `name`, `animationBindings` per weapon
  class `hth`/`1hs`/`2hs`/`stf`/..., `enterEvents`, `exitEvents`) and `transitions` (one `AnimationTransitionGroup`
  per `from` state, with `settings` items `{to, crossfadeSeconds}`).
- **Sequence skills pick their clip by skill ID**: a state with `modeId` **18** (SQ) and `skillIndex` = the skill's
  row ID (Barbarian `PMODE_SEQUENCE_WHIRLWIND`: skillIndex 151).
- A new sequence skill has no HD body animation until it has a state. Fix: copy the D2R state whose skill has the
  **same `seqnum`**, give it a new `stateId` (max + 1) and the new `skillIndex`; add a transition group from it
  (copy of the source's group) and an entry to it in every other group (copy of the entry to the source).
- Skills whose sequence has no D2R clip have no HD body animation (new art needed).

## Monsters

- Two sources: monstats `Code` -> classic animation set `data/global/monsters/<code>/cof/<code><mode><wclass>.cof`
  (+ DCC), **used even in HD for timing**; and `data/hd/character/monsters.json`: **monstats `Id` -> HD model name**
  (`data/hd/character/enemy/<model>/...`, with its own `<model>_state_machine.json`).
- A missing COF crashes ("Could not add cof file"); a monster `Id` missing from monsters.json has no HD model.
- **IMPORTANT: every JSON key is case-sensitive.** monsters.json is looked up by the monstats `Id` exactly as spelled:
  a mod monster `hellbovineMap` keyed as `hellbovinemap` is invisible in HD (proven in game, 2026-11-04).
  Vanilla Ids are all lower case, so D2R's own file never shows this. Never lower-case a key D2R builds from a name.
- Cheapest new monster: reuse a D2R monster's `Code` and monstats2 visual columns, and map its `Id` to that HD model.
  With its own classic files (COF/DCC + `animdata.d2` records) it keeps its own timing and classic art and only
  borrows the HD model.
- `animdata.d2` (classic frame timing) must contain every Code+mode+weapon class used; merge D2R's file with yours.

## New models and textures at new paths

`.model`, `.skeleton`, `.animations` and `.texture` files work at **new paths** as plain files of the mod folder
(e.g. `data/hd/character/<mod>/<unit>/`), so you never have to overwrite a vanilla unit. But D2R finds models and
textures through two index files built at start-up, not through the file system:

| Index | Key | A path that is not listed |
|---|---|---|
| `data/hd/model_lod_desc.bin` (14,310 entries in 93847) | FNV-1a 32 (`0x811c9dc5` / `0x1000193`) of the lower-cased game path, e.g. `data/hd/character/enemy/<unit>/torso.model` | Opened as the plain file, loaded without an error, **never drawn**. The log says `Failed to find LOD for model ...` |
| `data/hd/texture_desc_cache.json` (31,073 entries) | `filename` | Read with the wrong format or size: colour noise, or the GPU device is lost |

A mod's own copy of an index replaces the game's, so build both at build time from the installed game's files with
your paths added. Each new entry copies the entry of a vanilla unit of the same kind.

`model_lod_desc.bin` layout (little endian): a header of three `{u32 count, i32 self-relative offset}` pairs; array
1 is `count1` 44-byte entries **sorted by key**: `u32 key | f32 bbMin[3] | f32 bbMax[3] | u8 lodMask (bit k+1 = LOD
k) + 3 pad | u32 lodCount | u32 streamOffset | u32 streamSize`. `streamOffset` is self-relative and points into
array 2 (12-byte records into array 3, 32-byte per-mesh stream records). Adding an entry moves arrays 2 and 3, so
**rewrite every entry's `streamOffset`**: a stale one asserts `isMeshFlipbook == GetModelInfo()->isMeshFlipbook`
(model_asset.cpp:397, `Invalid data detected!` in d2rloader.log) and the game dies in the first preload.

Other rules for new units:

- A listed model path is opened as `<base>_lodN.model` for each LOD its mask lists.
- Every `Model` in a `.model` file needs at least one mesh binding (`model_asset.cpp:305 MeshBindingCount >= 1`).
- Animations are read from `<clip directory>/combined.animations`, not from single `.animation` files.
- Unit JSON, `monsters.json` and state machine JSON files are not indexed; any path works.
- D2RLoader's ResourceService can serve plugin files at new paths too (limits: 256 MiB per plugin load, 64 MiB per
  file), but models still need the index entry. Plain mod-folder files are simpler.

## Presets for new DS1 levels

D2R draws a level in HD from one HD preset per DS1 (`data/hd/env/preset/**/<ds1 stem>.json`: a terrain entity plus
placed entities, 10 HD units per DS1 tile). A DS1 with no preset plays on flat ground with invisible walls: the
`.ds1` and `.dt1` still give layout and collision (see
[Legacy files](#legacy-classic-g-mode-files-still-needed)), only the HD drawing is missing. A mod that brings many new
DS1 (for example from a classic mod) cannot hand-author a scene for each, and a hand-made scene is redone on every
re-import, so it can generate the preset from the DS1. This is how one mod's generator worked (the method is
reusable; the values are that mod's choices, not engine facts):

- **Per-tile kit.** Read the DS1's wall and floor cells and place clones of the stock entities of a chosen stock tile
  set on them, over a stock flat terrain textured with a stock biome. Commit the rule per tile set (which stock kit and
  biome stand in), not the generated presets. A tile set with no stock twin is an approximation until its own art exists.
- **Room paste.** A stock room whose tiles match most of a spot (that mod used 60% or more) is pasted whole: it brings
  its own sculpted terrain, water and bridges, which tile-by-tile copying never draws.
- **3x3 patch.** A tile whose 3x3 neighbourhood (else its plus-shaped cross) occurs in a stock preset gets what that
  preset placed on the centre tile. Rooms and patches apply to every generated preset.
- **Border painter.** For a DS1 that draws a tree-line `.dt1` tile: drop the trees past the playable area, then paint
  them again from it outward, copying the tile set's stock trees by direction and distance to the blocked ground. Harvest
  the tree kit per tile set from the stock presets that share its DT1 files. The playable area is the ground no DS1
  cell marks unwalkable (collision bit `0x20000`), which also closes the plain-floor gaps of dashed tree lines; blocked
  floor that touches walkable floor, or draws a water DT1, is a stream and gets no trees; other blocked floor lies past
  the map edge and does.
- **Water.** A stock room draws its stream as one room-sized mesh, so outside pasted rooms the blocked floor of each
  water DT1 gets a stock water plane, scaled to cover it in near-square rectangles.

Cost check before shipping a generated level: in the largest one, compare frame rate with a stock area of the same size
and biome. The entity pool and the JSON pool are fixed size (EntityPool and JsonPool in
[d2r-93847-addresses.md](d2r-93847-addresses.md), build 93847: a preset over about 34k entities, or a generated
preset JSON of tens of MB, ran them dry and crashed); if a level is clearly slower, merge entities or bake terrain.

### Override ops (fixing one generated map)

A generated preset is wrong in places no general rule should fix (a prefab floating above the ground, a rock on open
floor). Keep the generator rule-only and fix the one map in data after generation, as a list of ops per preset, so the
fix is a reviewed diff. The ops that mod used:

- **Selectors** (all given must match; every op but `add` and `entity` needs one): `at [x, y]` (a DS1 tile, = position
  // 10 HD units), `area [x0, y0, x1, y1]` (tiles, inclusive), `model` (case-insensitive glob) and `name` (glob),
  `pos [x, z]` (one entity by its generated position, tolerance 0.01), `expect` (how many it must match). Never select
  by entity `id` or array index: a re-serialised preset renumbers them. The terrain entity is never selected.
- **Ops:** `remove`; `ground` (set y to the ground plane under the entity: the floating fix); `move` (`by` in HD units,
  or `to` a tile, y re-grounded); `swap` (change the model or prefab path, merging the new model's dependencies from a
  stock preset); `add` (copy the first entity of a stock preset whose model matches, to a tile, with a fresh id and that
  preset's dependencies); `entity` (an inline entity with a fresh id, what a diff writes for an entity an editor added).
  Merge the `dependencies` of anything added, or its model does not load.
- **Stale ops fail.** An op that matches nothing, or not its `expect`, means the generator moved what it aimed at:
  report it and fail the build, then re-aim or drop the op.
- **Editor round trip:** edit a copy of the generated preset in an editor, compute the ops that turn the generated one
  into the edited one (entities only in the generated file become `remove`, a removed and added pair of one model within
  two tiles becomes a `move`, the rest inline `entity`), commit those ops, and check that replaying them on the
  generated preset gives the edited one. Prefer a selector op over inline `entity` when the fix is a rule of the map.
- **Proof:** an override changes what players see. Check it in game: pin the level's DS1 variant, warp there and look
  at the spot before and after.

## Stand-ins first

Make the rules work before the art. For each new thing, ship the closest vanilla HD look:

| New thing | Stand-in |
|---|---|
| Monster | The vanilla monster closest in shape and role (map its monstats `Id` to that HD model in `monsters.json`; scale or recolour later) |
| Missile | The vanilla missile model with the same element and shape (`missiles.json`) |
| Item | The vanilla picture of the same base type (`items.json`), or a bilinear upscale of the classic DC6 |
| Skill icon | An upscale of the classic icon |
| Panel | An upscale of the classic panel (1162 x 1507) |

Keep a list of every stand-in so the art work is easy to plan.

## Legacy (classic, G mode) files still needed

| File type | Why |
|---|---|
| `.dt1` / `.ds1` (`data/global/tiles`) | Map building, in HD too. Missing tile -> black screen / crash on entering the area |
| `.cof` + `.dcc` monsters, `animdata.d2` | Timing in HD; art in classic mode |
| `.dcc` missiles and overlays | Classic mode crashes on a missing graphics file when the effect spawns |
| `.dc6` item pictures (`data/global/items/<invfile>.dc6`) | Classic inventory art |
| `.dc6` skill icon sheets | Classic skill icons |

D2R ships its own legacy art (about 21,000 .dcc, 3,600 .cof, 1,300 .dc6, 266 .dt1, 2,277 .ds1): reuse it freely.
Ship only new files; leave D2R's names alone so its HD and classic versions stay matched.

## New objects

A new `objects` row needs two HD files or it spawns and works but draws nothing: a line in
`data/hd/objects/objects.json` (`"<snake_case class>": { "asset_path": "<folder>" }`, `ShrineAltar` -> `shrine_altar`)
and `data/hd/objects/<folder>/<name>.json`. A copy of the stock object's json reuses its model (build 93847).
