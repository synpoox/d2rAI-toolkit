<!-- Snapshot of the live doc https://claude.ai/artifact/5DCNKj7JZuuSYnWo3i45QT taken 2026-11-11. The live doc is the source of truth; refresh this copy at each handoff. -->

# Consolidation Phase 2: lane items and approvals

Nov 11, 2026 · owner

## Status

Lanes A, E and F are approved in full, and lane D except D8 (on hold). Lane G is approved except G2, G4 and G5. B, C, H and I wait until we get there.

Every item copies a generic version into d2rAI-toolkit with its tests. No mod repo changes during Phase 2; each mod deletes its copy later, in a separate PR (resurrected-09, then Project Forever, then pd2-resurrected after its alpha, about 2026-11-17). Sources: **P** = pd2-resurrected, **F** = Project Forever, **9** = resurrected-09. Sizes: S under half a session, M one session, L several.

| Lane | What | Decision (2026-11-11) | Notes |
| --- | --- | --- | --- |
| A | Classic table and id layer | Approved | Blocks B and C |
| B | Classic DS1 levels to HD presets | Waiting | After A |
| C | Art and asset ports | Waiting | After A |
| D | 1.09d datasets and generators | Approved | D8 on hold: fix issue resurrected-09 #93 raised, not to start |
| E | Testing | Approved | E13 slot table changed: Slot4–8 pd2-resurrected, Slot9–10 resurrected-09 |
| F | Release, tools, CI templates | Approved | F6 (SessionStart hook) included |
| G | C++ plugin-common and template | G1, G3, G6–G12 approved | G2, G4, G5 wait |
| H | Knowledge and contradictions | Waiting |  |
| I | Methods, templates, skills | Waiting | Keep/throw table unanswered |

Decided 2026-11-11:

- **D8:** first "fix now", then put on hold the same day. The fix issue (resurrected-09 #93) exists without its agent label, so nobody starts it.
- **G1, G10–G12:** approved with the two-homes rule. Every address goes in the header and in `knowledge/`, kept in step by a test; G10 and G12 go to `knowledge/` only.
- **Slots:** Slot2 toolkit tests, Slot3 Project Forever, Slot4–8 pd2-resurrected, Slot9–10 resurrected-09.

## Lane A: classic table and id layer

Approved. This lane goes first and blocks B and C. It copies from pd2-resurrected's current `main` into `shared/classic_import/`; nothing is written to pd2-resurrected while it's frozen.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Id rules | Merges the generic algorithm: append-only ids, renames, formula and ref rewrites, `merge_table` | P `tools/pd2_ids.py` → `ids.py` | P runs an older fork of `ids.py` | Two id engines → one. P keeps REFS, FORMULAS, FUNCS, FIXES, `_NPC`, `PLAIN_STRINGS`, `_TIER`, `MAP_SPELL`, HIT\_PARAMS, MISSILE\_FUNCS, LEFT\_OUT\_LEVELS | L | Approved |
| A2 | Table edits | Ports missing operations (rows, repeats, move, cells) | P `pd2_tables.py` → `tables.py` | Duplicate of `tables.py` | Fork → toolkit only | M | Approved |
| A3 | Table diff | Generic diff in the toolkit; P keeps a thin CLI shim | P `pd2_diff.py` → `diff.py` | Duplicate of `diff.py` | Fork → shim. The shim keeps ITEM\_TABLES and the P2/P3/P4/M1/alpha scopes | M | Approved |
| A4 | Table class | Uses `ids.Table`, adding CRLF-safe and Expansion-row handling if missing | P `pd2_table.py` → `ids.Table` | Duplicate class | Fork → one class | S | Approved |
| A5 | Game-file cache | Machine-wide extract and rule caches, file locks, code-hash rule keys, CI policy, merge-slot semaphore | P `pd2_cache.py` + `pd2_cache_verify.py` → `cache.py`, `cache_verify.py` | Every mod's build re-extracts the game files and collides | None → shared. `PD2R_CACHE`, `_CI_SCOPE`, `_MERGE_SLOTS`, `_CACHE_GB` become `MODKIT_*` | L | Approved |
| A6 | Build plumbing | Lock, cache replay, output check and junction handling | P `pd2_merge.py`, `pd2_extract.py` → `merge.py`, `extract.py` | Generic build steps | P-only → toolkit. P keeps its RULES map | M | Approved |
| A7 | Item tables | Item tables by key, cube merge, no-drop types, HD pictures for new items | P `pd2_items.py` → `items.py` | Every port adds items | P-only → toolkit | M | Approved |
| A8 | HD entries | One module covering missiles, monsters, objects and overlays | P `pd2_{missiles,monsters,objects,overlays}_hd.py` → `hd_entries.py` | Four near-copies | 4 files → 1 | M | Approved |
| A9 | Stand-ins | Points function columns that aren't built yet at D2R rows | P `pd2_standins.py` → `standins.py` | Every port needs stand-ins | P-only → toolkit | S | Approved |
| A10 | Skill descriptions | Rewrites descline function, text and calc | P `pd2_skilldesc.py` → `skilldesc.py` | Every skill port needs it | P-only → toolkit | M | Approved |
| A11 | Tests | `test_ids`, `tables`, `diff`, `items`, `*_hd`, `standins`, `skilldesc`, `cache*`, `memo`, `pipeline`; `test_deviation_counts` becomes `tools/check_deviations.py` | P `tools/tests/` → `tests/` | Tests move with code | Fixtures made synthetic | L | Approved |
| A12 | Baseline example | Example baseline file with P's values stripped | P `pd2-baseline.json` → `templates/baseline.example.json` | Shows a mod the shape | — | S | Approved |

**Stays in pd2-resurrected:** the RULES map, the `pd2_ids` constants, ITEM\_TABLES and its scopes. Before pd2-resurrected switches, diff its sources again for changes made after the copy.

## Lane B: classic DS1 levels to HD presets

Waiting; starts after A. These files move from pd2-resurrected as one unit, into `shared/classic_import/maps/` and `modkit/`.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | DS1/DT1 readers | Reads DS1 (v18 or lower), DT1 and lvltypes | P `pd2_ds1.py` + `presets/dt1.py` → `modkit/ds1.py` | The base of every classic map port | P-only → modkit | S | Waiting |
| B2 | Ground height | Ground height from terrain.physics | P `pd2_terrain.py` → `modkit/terrain.py` | Needed for HD presets | P-only → modkit | S | Waiting |
| B3 | Preset pipeline | Classic level → HD preset: tiles, painter, presets core, 8 hooks, 15 passes, `fence_kit.json`, `hd-folder-types.tsv` | P `pd2_tiles`, `pd2_painter`, `pd2_presets`, `tools/presets/**` → `maps/` | Works on any classic level | P-only → toolkit. Each pass reviewed; one-mod passes stay as hooks | L | Waiting |
| B4 | Map overrides | Override ops per map, plus a lint for stale ones | P `pd2_overrides.py` + `pd2_presets_lint.py` → `maps/` | Hand fixes on top of generated maps | P-only → toolkit | M | Waiting |
| B5 | Tile copies | Finds DT1 tiles that are pixel copies of D2R tiles | P `pd2_dt1_copies.py` → `maps/` | Reuses HD art instead of upscaling | P-only → toolkit | S | Waiting |
| B6 | Map scorers | Coverage, fidelity, parity and lighting scores | P `pd2_coverage`, `_fidelity`, `_parity`, `_lighting` → `maps/` | A measurable map gate | P-only → toolkit; area lists passed in | L | Waiting |
| B7 | Level tables | lvltypes, objpreset, DS1 id rewrite, monpreset | P `pd2_levels.py` → `maps/levels.py` | Needs B1 | P-only → toolkit | M | Waiting |
| B8 | Edge tour | In-game tour of map edges using the fidelity classifier | P `pd2_edge_tour.py` → `testing/edge_tour.py` | Visual check of B's output | P-only → toolkit; reuses `check_helpers.pair`, `goto_line` | L | Waiting |
| B9 | Tests | `test_presets_*`, `test_edges_*`, `floor_height`, `ds1cache`, `dt1_copies`, `terrain`, `lighting`, `levels`, `coverage*`, `fidelity`, `parity`, `overrides`, `presets_fixtures.py` | P `tools/tests/` → `tests/` | Tests move with code | Fixtures made synthetic | L | Waiting |
| B10 | Map method | The DS1/DT1 method from four research branches | P `@research/lp3-border-painter`, `lp3-tile-table`, `hd-parity-strategy`, `pd2-only-levels` → `knowledge/` | Explains B3 | Unmerged → knowledge; method only | M | Waiting |

**Stays in pd2-resurrected:** the jungle UNWALKABLE ratios, the TERRAIN preset, the `presets-hd.d` and override paths, the area lists and the scorer baselines.

## Lane C: art and asset ports

Waiting; starts after A. Everything comes from pd2-resurrected.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Upscaler | Real-ESRGAN ×4 with a committed hash cache and an icon style | P `pd2_art.py` → `modkit/upscale.py` | All classic art needs upscaling | P-only → modkit; tool path from config | M | Waiting |
| C2 | Panel widening | Widens panel grid art by N columns (HD, lowend, DC6) | P `pd2_panels.py` → `modkit/panels.py` | Bigger stash or inventory | P-only → modkit | S | Waiting |
| C3 | Skill-tree art | Redraws tree sprites at merged skill positions | P `pd2_skilltrees.py` → `modkit/skilltrees.py` | Changed skill trees | P-only → modkit; measured JSON stays data | M | Waiting |
| C4 | Strings | Overrides, renames, `--assign` of new string ids; reads classic `.tbl` | P `pd2_strings.py` → `strings.py` rule + `modkit/strings.py` | Every port carries strings | P-only → toolkit | M | Waiting |
| C5 | Animdata | Reads, writes and merges animdata.d2 | P `pd2_animdata.py` → `modkit/animdata.py` + a rule | New monsters and skills need it | P-only → modkit | S | Waiting |
| C6 | Sounds | WAV → FLAC; sounds.txt rows copy D2R-only columns from `like` | P `pd2_sounds.py` → `sounds.py` | Classic sounds | P-only → toolkit | S | Waiting |
| C7 | Skill icons | Classic DC6 icons → HD strips, plus hireling icons | P `pd2_skill_icons.py` → `skill_icons.py` | New skills need icons | P-only → toolkit | M | Waiting |
| C8 | Automap | Appends classic automap cels to the HD tiles | P `pd2_automap.py` → `automap.py` | New maps on the automap | P-only → toolkit | S | Waiting |
| C9 | Tests | `test_strings`, `animdata`, `sounds`, `skill_icons`, `automap` | P `tools/tests/` → `tests/` | Tests move with code | Fixtures made synthetic | M | Waiting |

## Lane D: 1.09d datasets and generators

Approved, except D8, which is on hold: its fix issue, resurrected-09 #93, is raised but not to start. Everything comes from resurrected-09 and goes into `shared/classic_import/data/`, `baselines/` and `tests/`.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | 1.09d column map | Dataset turning 1.09d tables into the 1.13c layout, plus value maps (dropsound/usesound, `anim` → mode codes, `transformcolor`, SkillNSeq) | 9 `merge/109d-to-113c-column-map.{json,tsv}` → `data/` | Every 1.09d port needs it | 9-only → toolkit | L | Approved |
| D2 | Map generator | Generates D1 from a hash-checked MPQ stack, with a proof that `.bin` widens `.txt` | 9 `merge/column_map.py` (+ 17 early scripts) → `gen_109d_map.py` | D1 is generated, never hand-edited | Scripts → one generator. **Drops the scratch scripts that contain real user paths** | M | Approved |
| D3 | 1.09d converter | Recode hooks forward and back (×16 SrcDam, row → name, Lookup, carry\_copies) | 9 `merge/to_113c.py` → `from_109d.py` | The converter itself | 9-only → toolkit. **Fixes the monster-AI bug first** (`BaseId` read as a row; AIParamN copied to aipN) | M | Approved |
| D4 | Converter tests | Round trip, BLANK\_IS\_ZERO, widening | 9 `test_to_113c.py`, `test_column_map.py` → `tests/test_classic_import_109d.py` | Tests move with code | — | S | Approved |
| D5 | Skill-function map | 2,088 skill and missile pairs: 1.09d address → D2R index and RVA, with a verdict | 9 `docs/research/skill-functions.tsv` → `data/109d-skill-functions.tsv` | Saves re-reversing each function | 9-only → toolkit | M | Approved |
| D6 | 1.09d baseline | Stock 1.09d file hashes plus a "not part of 1.09d" list | 9 `09-baseline.json` + `@research/109d-stock-files` → `baselines/109d.json` | Pins the reference install | 9-only → toolkit; install path removed | S | Approved |
| D7 | Monster-AI pairing | New generated dataset: BaseId → D2R AI | 9 `@research/monster-ai` → `data/` | Only 9 of 169 pairs are mapped today | 9 of 169 → all 169 | M | Approved |
| D8 | Fix resurrected-09 too | On hold (2026-11-11). Planned in resurrected-09 #93: BaseId fully; AI parameters remapped where a slot map is verified on both builds, the rest listed as deviations | resurrected-09 | 9 ships the bug until it's fixed | The only item that writes to a mod | S | Question |

**Stays in resurrected-09:** the 09 rules inside `to_113c.py` and its patches.

## Lane E: testing

Approved, with your change to E13: pd2-resurrected keeps Slot4–8 and resurrected-09 has Slot9–10. Everything lands in `testing/`.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | Rate check | Binomial rate check at 4σ, seeded counts | 9 `tests/game/stats.py` + `test_stats.py` → `testing/stats.py` | Drop and proc rates for any mod | 9-only → toolkit, unchanged | S | Approved |
| E2 | Save round trip | `plugin_log`, `read_save`, `save_and_exit` (waits for `RD` and the `.d2rl` sidecar), create/save/reload a character | 9 `skeleton_checks.py` → `testing/lod_checks.py` | Every mod needs it | 9-only → toolkit. Plugin, mod and character are parameters; menu fractions in a shared constants module (3.3, 1920×1080) | M | Approved |
| E3 | Image bytes | Checks the PE stamp, reads RVA spans, compares stock and patched | 9 `dr_cap_checks.py` `_image()` → `testing/image_bytes.py` | Proves a patch landed | 9-only → toolkit | S | Approved |
| E4 | D2R-only content | Zone-switch scan, Colossal portal, Terror Zone pixel detector, `heraldspawn` control | 9 `d2r_only*.py` + test → `testing/d2r_only.py` | Checks D2R-only content is on or off | 9-only → toolkit. Calibrated on 93847. **These leave town, so agents only unit-test them** | M | Approved |
| E5 | Save editing | Unlocks difficulties in a save (byte 0x15 = 0x0f, bytes 0x98–0x9a, `finalize`) | 9 `leech_checks.py` @ticket/29-leech → `testing/save_edit.py` | Hell testing without playing through | 9 branch → toolkit | S | Approved |
| E6 | Plugin log helper | One shared plugin-log reader | P `tests/game/*_checks.py` `_log(ctx)` → `check_helpers.plugin_log()` | Copied into every check | Copies → one | S | Approved |
| E7 | Unit probe | Read-only counter of units and missiles | P `missile_probe.py` → `testing/unit_probe.py` | Checks spawns and missiles | P-only → toolkit; RVAs from the registry | S | Approved |
| E8 | Contact sheet | Contact sheet plus luma and black-pixel metrics | P `contact_sheet.py` → `testing/contact_sheet.py` | Screenshot evidence | P-only → toolkit; merged with `check_helpers.side_by_side` | S | Approved |
| E9 | Warp docs | Generates a `cheat goto` doc for added maps | P `pd2_warps.py` → `testing/warps.py` | Agents reach new maps fast | P-only → toolkit | S | Approved |
| E10 | Force DS1 | Pins a DS1 variant in a slot | P `pd2_force_ds1.py` → `testing/force_ds1.py` | Reproducible map tests | P-only → toolkit; mod folder from `mod.json` | S | Approved |
| E11 | Fixture pattern | One fixture mod.json plus a patch per check | P `tests/game/fixtures/*` → `testing/README.md` | Keeps checks isolated | Undocumented → documented; pattern only | S | Approved |
| E12 | Slot-savepath check | Both modinfo savepaths equal the slot folder | F `slot_install_checks.py` → `testing/` | A wrong savepath hides characters | F-only → toolkit | S | Approved |
| E13 | Slot registry | `game_slots lock` enforces a slot-to-owner table from `~/.d2r-modkit/slots.toml` | New | Today `lock any` can take another project's slot | Trust → enforced; machine config, never in a repo | M | Approved |
| E14 | No config, no slot | Tools refuse to touch a slot when no config is found | New | Today they silently use the toolkit's default | Silent default → refusal | S | Approved |

**Slot table (E13, approved 2026-11-11, amended the same day):**

| Slot | Owner |
| --- | --- |
| Slot2 | toolkit tests |
| Slot3 | Project Forever |
| Slot4–8 | pd2-resurrected |
| Slot9–10 | resurrected-09 |

The edge tour moves with lane B.

## Lane F: release, tools and CI templates

Approved, including F6, the SessionStart hook. Everything comes from pd2-resurrected and goes into `release/`, `tools/` and `templates/workflows/`. The CI templates can't run here (Actions has never run on the toolkit repo), so they're reviewed by reading only.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | Release stager | Folds changelog fragments and stages a release; plugins, staging list and filter-table fill come from `release.toml` | P `tools/release.py` → `release/` | Probably closes toolkit #7 (release builder) | P-only → toolkit | M | Approved |
| F2 | Changelog fragments | `changelog.d/` replaces per-version sections; updates `docs/release.md` and the `d2r-release` skill | P `changelog.d/` convention → `templates/changelog.d/README.md` | No changelog merge conflicts | Sections → fragments. F owns these files, not lane I | S | Approved |
| F3 | Companion plugins | Fetches community plugins pinned by SHA-256, overlays config, installs | P `tools/companions.py` + manifest schema → `release/companions.py` | Closes toolkit #6 (companion installer) | P-only → toolkit; FILTER\_TABLES, ITEM\_RANGES and the item toggle become per-entry options | M | Approved |
| F4 | Plugin install | Built plugins, savepath restore, stray-plugin quarantine | P `tools/install.ps1` → `tools/install_plugins.ps1` | Safe installs | P-only → toolkit, on top of `modkit install` / `slot_install` | S | Approved |
| F5 | Safe worktree removal | Removes worktrees that contain junctions without deleting through them | P `worktree_remove.ps1` + test → `tools/` | Prevents data loss | P-only → toolkit | M | Approved |
| F6 | Stale-branch hook | SessionStart warning when HEAD lacks `origin/main` | P `.claude/settings.json` → plugin hook | Stale branches | P-only → every plugin session | S | Approved |
| F7 | Table probe | Probes skill-function tables | P `probe_tables.py` → `tools/probe_tables.py` | RE helper | P-only → toolkit | S | Approved |
| F8 | `tests.yml` | Unit-test workflow template (ubuntu) | P → `templates/workflows/` | Mods get CI | Not runnable here | S | Approved |
| F9 | `gate.yml` + `gate-control.yml` | Self-hosted table-diff gate, cache replay, never-skip trick, docs-only filter, cancel and rerun by label | P → `templates/workflows/` | Merge gate | Runner labels and paths become inputs | M | Approved |
| F10 | `cache-verify.yml` | Nightly fresh vs cached merge | P → `templates/workflows/` | Catches a stale cache | — | S | Approved |
| F11 | `release.yml` | Self-hosted full build plus GitHub release | P → `templates/workflows/` | Release CI | — | S | Approved |

## Lane G: C++ plugin-common and template

G1, G3 and G6–G12 are approved; G2, G4 and G5 wait. All addresses are for build 93847, and the plugin template has to build. Sources go into `shared/plugin-common/` and `plugin-template/`.

**Your question: shouldn't G1 and G10–G12 go into `knowledge/`?** Yes. The toolkit already keeps every address twice, on purpose:

| Home | What it's for | Size today |
| --- | --- | --- |
| `knowledge/d2r-93847-addresses.md` | The registry people and agents read: what each address is, its signature, how it was confirmed | about 290 values |
| `shared/plugin-common/src/rvas_93847.h` | The copy plugins compile against (`knowledge/engine-re.md` says every confirmed address goes in this header) | about 80 values |

Approved 2026-11-11:

- **G1:** both homes. Each promoted RVA goes into the header *and* gets a row in `d2r-93847-addresses.md` with its meaning and evidence. A new unit test fails when an RVA is in the header but missing from knowledge, so the two can't drift.
- **G10 (DR cap), G12 (packets):** knowledge only. No toolkit code calls them; they go into the header when a toolkit mechanism needs them.
- **G11 (leech hook):** both, because a plugin hooks it. The rounding rule goes into knowledge.

| # | Item | What it does | From → to | Why | Today → after | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | Address promotion | Promotes about 233 RVAs; splits `rvas_93847.h` by area (tables, hits/damage, units/paths/pets, data offsets, stats, items/cube, levels/rooms, AI, client, memory pools); structs go to `d2r.h` | P `plugin/common/pd2_engine.h` → header + `knowledge/d2r-93847-addresses.md` | 233 of 327 addresses are missing from the toolkit | Mod-only → shared. PD2 comments trimmed; the headers' policy lines aligned | L | Approved |
| G2 | Pool growth | `tlsf_add_pool` for the Entity, Renderer, JSON, Object, Jobs and Texture pools | P `core-maps/entity_pool.*` → `pool_grow.*` | Big mods run out of pool memory | P-only → shared; pool sizes into knowledge | M | Waiting |
| G3 | AI registry | Registers monster think functions by monai row and class, with D2R fallback | P `core-maps/ai_hooks.*` → `ai_registry.*` | New monster AI | P-only → shared | M | Approved |
| G4 | Automap extension | Automap lookup for level types 36 and up | P `core-ui/automap.*` → `automap_ext.*` | New maps on the automap | P-only → shared | M | Waiting |
| G5 | Item pictures | Patch so items.json keys 4-character codes | P `core-ui/item_pictures.*` → shared | 4-character item codes | P-only → shared | S | Waiting |
| G6 | Palette reload | Reloads the act palette on a level change without a load screen | P `core-ui/level_palette.*` → shared | Cross-act maps | P-only → shared | S | Approved |
| G7 | Skill router | Router-slot dispatcher plus missile function signatures | P `core-rules/skill_functions.*`, `missile_functions.*` → `plugin-template/skill_router.*` | New skill functions without slot collisions | P-only → template; PD2 skills stay | L | Approved |
| G8 | Parts table | One `{word, engine, install}` table plus a status command per plugin | P / 9 `plugin/*/plugin.cpp` → `plugin-common/parts.h` | Same pattern in every plugin | Copies → one; template updated | M | Approved |
| G9 | Template build | Several plugins per project, the toolkit locator, SDK submodule init in a fresh worktree | P `plugin/CMakeLists.txt`, `build.ps1` → template | Builds fail in fresh worktrees | — | S | Approved |
| G10 | DR cap address | DR cap at 0x4524d0 (50 in D2R vs 75 in 1.09d) | 9 `09-rules/dr_cap.cpp` → knowledge | Shared fact | 9 keeps the value 75 | S | Approved |
| G11 | Leech hook | Hook 0x450c90 plus offsets; 1.09d leech rounding | 9 `leech.cpp` @ticket/29-leech → header + knowledge | Shared fact | 9 branch → shared | S | Approved |
| G12 | Level packets | Act darkness packet 0x53, level sound packet 0x2c | P `core-maps/level_fx.*` → knowledge | Shared fact | P-only → shared | S | Approved |

## Lane H: knowledge and contradictions

Waiting. Facts only; each mod's choices stay with it. A fact read from a mod's files moves only once it matches the stock version (plan rule 3). The lane has three sub-lanes, one per source project, plus the contradictions.

**H-P: from pd2-resurrected**

| # | Source | What it adds | Lands in | Size | Approval |
| --- | --- | --- | --- | --- | --- |
| HP1 | `d2rloader-capabilities.md` | Capability matrix, loader 1.3.1 / SDK 0.4.0 | new `d2rloader-capabilities.md` | M | Waiting |
| HP2 | `skill-function-tables.md` | All function tables, bounds, free slots, readers; cltstfunc `0x235f590`, srvdmg `0x2391270` | `d2r-93847-addresses.md`, `engine-limits.md` | M | Waiting |
| HP3 | `core-rules-inventory.md`, `pd2-engine-dll-triage.md` | Method only: sort a classic DLL's rules into buckets, slot-collision checklist, DLL triage from strings | `porting-classic-mods.md` §1, §5 | M | Waiting |
| HP4 | `pd2-data-inventory.md` | Stock 1.13c vs D2R 3.3 tables, columns, events; saves v96 vs v105 | new `classic-113c-tables.md`, `porting` §3 | M | Waiting |
| HP5 | `pd2-asset-inventory.md`, `pd2-strings-inventory.md` | D2R string-id budget, reversed multi-line skill text | `strings.md` | S | Waiting |
| HP6 | `plrmodes.md`, `stack-split.md`, `states-immed.md` | Reading 1.13c patch tables; 1.13c never reads states `immed` | `classic-113c-tables.md`, `porting` §6 | S | Waiting |
| HP7 | `ms2-*`, `ms3-*`, `ms4-*`, `ub2-*` | Map opening, map stats, monster region, portal maker, item spell 16 / `0x236fe30` | `d2r-93847-addresses.md`, `new-game-systems.md` | M | Waiting |
| HP8 | 25 work-item notes | D2R function signatures and slots only | `d2r-93847-addresses.md` | M | Waiting |
| HP9 | ADR 0001–0003 | Bank choice, data from a hash-pinned extract, extended saves with append-only ids, as decisions to make | `porting` §0, §2 | S | Waiting |
| HP10 | ADR 0004 | Plugins split by multiplayer scope; when a system gets its own DLL | `d2rloader.md`, `new-game-systems.md` | S | Waiting |
| HP11 | ADR 0005 + `hd-preset-overrides.md` | HD presets from DS1: room paste, 3×3 patch, border painter, override ops | `hd-graphics.md` | M | Waiting |
| HP12 | `modkit-validation.md` | Validation errors and causes; fixes need an in-game proof | `modkit-ops.md` | M | Waiting |
| HP13 | `core-rules.md` | Format of the hook list (rule, source, bucket, slot, RVA) | `porting` §5 template | S | Waiting |
| HP14 | `deviations.md`, `pd2-origin-bugs.md`, `d2r-only-content.md` | Status vocabulary, origin-bug ledger, D2R-only approval ledger | `porting` §10 | S | Waiting |
| HP15 | `GLOSSARY.md` | Fidelity terms: deviation, exact, approximated, cut, router slot, companion plugin | `porting` §0 | S | Waiting |
| HP16 | `item_quantity.*`, `stack_split.*` | Loader gaps: WidgetService has no screen rect, OverlayService draws nothing, TCP/IP clients have no game thread | `d2rloader.md` | S | Waiting |
| HP17 | `docs/agents/game-slots.md` | RotW-character trap, `cheat expansion 2` crash, LoD badge | `cheat-commands.md` | S | Waiting |
| HP18 | `@research/suite-companions` | Method only: checking another plugin's hooks coexist with yours | `d2rloader.md` | S | Waiting |

**H-9: from resurrected-09**

| # | Source | What it adds | Lands in | Size | Approval |
| --- | --- | --- | --- | --- | --- |
| H9-1 | `skill-functions.md` | 1.09d dispatch charts vs D2R tables; class row ranges; loader-thunked slots | new `classic-109d-engine.md` | L | Waiting |
| H9-2 | `@research/monster-ai` | AI table 1.09d 0xebac8 vs D2R 0x2396e90; BaseId picks the AI; AIParam slots moved in 1.10 | `classic-109d-engine.md` | M | Waiting |
| H9-3 | `@research/109d-to-d2r-code-changes` | About 60 rule differences, with addresses | new `classic-109d-vs-d2r.md` | L | Waiting |
| H9-4 | `@research/109d-vs-113c-columns` + `merge/README.md` | 75 vs 92 tables, number vs name refs, SrcDam ×16, row shifts; 1.13c `.bin` = widened 1.09d `.txt` | new `classic-109d-tables.md`, `porting` | M | Waiting |
| H9-5 | `@research/109d-stock-files` | Per-file hashes, Version Changer 4.6 provenance, NoCD, code-cave diff | new `classic-reference-installs.md` | M | Waiting |
| H9-6 | `@research/runtime-capabilities` | Loader 1.3.1 ships SDK 0.3.0 vs 0.4.0 headers; Battle.net 93847 vs Steam 93787; closed source | `d2rloader.md` / `d2rloader-capabilities.md` | S | Waiting |
| H9-7 | `@research/warlock-leftovers-on-lod` | LoD bank keeps Warlock placeholder rows; `sounds` always reads `excel/`; converted characters read `excel/`; RotW-only flags | `tables.md` "Two banks" | M | Waiting |
| H9-8 | `@research/baseline-evidence` | Evidence hierarchy and observation record | new `docs/fidelity-evidence.md` | S | Waiting |
| H9-9 | `@history` `gameplay-fidelity.md` | Exact / approximated / cut, timing, accepting random distributions | new `docs/fidelity-policy.md` | M | Waiting |
| H9-10 | `@history` `runtime-support.md` | Runtime qualification checklist | new `docs/runtime-qualification.md` | M | Waiting |
| H9-11 | `@history` `technical-approach.md`, ADRs 0001–0003 | Fixed game plus rolling loader, data first plus targeted hooks, extended saves from the start | `ai-workflow.md`, `porting` §0 | S | Waiting |
| H9-12 | `GLOSSARY.md` | Reference install, deviation, table set, column vs rename map, placeholder row | `porting` glossary | S | Waiting |
| H9-13 | `@ticket/29-leech` | Leech model (D2R 1/64 fixed point, player-only divide vs 1.09d) and the DR cap | `classic-109d-vs-d2r.md` | S | Waiting |
| H9-14 | `d2r-conveniences.md` | D2R 3.3 features a port can keep or turn off | new `d2r-conveniences.md` | S | Waiting |
| H9-15 | `patches/24-d2r-only-content.json` | Example patch turning off Terror Zones, Heralds and the Colossal portal | `examples/patches/no-terror-zones.json` | S | Waiting |

**H-F: from Project Forever**

| # | Source | What it adds | Lands in | Size | Approval |
| --- | --- | --- | --- | --- | --- |
| HF1 | `@research/flask-runtime` | pSpell 16–19, not-consumed flag at `0x236fe30`, charge stores, `ItemInteractionService` scope, `editItem` limits, stat 253 | new `charged-items.md` | L | Waiting |
| HF2 | `@research/save-freeze` | Retail id widths, extended limits (1 MiB / 247 pages / Recovery), 5→6 migration, freeze table, savepath hides characters | `saves.md`, `tables.md` | L | Waiting |
| HF3 | `@research/map-hosting` | Cloning `levels` rows onto stock tiles; level id ≤255, Layer <100; `Red Portal,lvl=`; per-game resets; no zone API | `new-game-systems.md`, `tables.md` | L | Waiting |
| HF4 | `@research/d2r-play-modes` | Official vs community support, TCP/IP, ladder claims, offline auth, the 2.5 migration warning, EULA flag | `docs/distribution.md` | M | Waiting |
| HF5 | `@research/archetype-weaknesses` | D2R 3.3 facts only: dead and trap skills, patch history | new `class-balance-3.3.md` | L | Waiting |
| HF6 | `pd2-re-inventory.md` | Rule only: one owner per hook site | `engine-re.md` | S | Waiting |
| HF7 | `in-game-testing-inventory.md` | Testing hazards: acknowledgement ≠ output, background flag, zero-durability reloads, held cursor item, broken `cheat item`/`gold`, `--no-validate` debt | `docs/testing.md` | M | Waiting |
| HF8 | `reusable-foundations.md` | Prepared vs fresh characters; exit 0 doesn't mean nothing was skipped | `docs/testing.md` | S | Waiting |
| HF9 | `pd2-project-inventory.md` | Method only: a decision record doesn't prove the work landed | `ai-workflow.md` | S | Waiting |
| HF10 | `source-document-inventory.json` | Pattern: pin sources by hash | research template (lane I) | S | Waiting |
| HF11 | ADR 0001 | The option and its consequences (stored vs live rules for owned items) | `saves.md` | S | Waiting |
| HF12 | `play-modes-and-leagues.md` | Feasibility checklist only | `docs/distribution.md` | S | Waiting |
| HF13 | `toolkit-inventory.md` | Drift list becomes toolkit issues | toolkit issues | S | Waiting |

**H-X: contradictions the toolkit settles.** Each becomes one toolkit issue, fixed with evidence.

| # | Topic | Toolkit says now | Evidence says | Done in | Approval |
| --- | --- | --- | --- | --- | --- |
| X1 | Who tests | "the user tests in game" | Agents run checks in slots | I | Waiting |
| X2 | Skill tabs | More than 3 is engine work | 8 TabWidgets confirmed | H | Waiting |
| X3 | Numeric string ids | Never append | Safe below 65,536 | H | Waiting |
| X4 | Install namespace | `install.py` writes none | Mods add it by hand | H (code) | Waiting |
| X5 | Loader vs SDK | No capability matrix | P, F, 9 research | H | Waiting |
| X6 | Hook byte coverage | At least 14 bytes | Template uses 8-byte signatures | H | Waiting |
| X7 | Extended-save marker | `0x44520069` | SDK README: `0x44520006` | H | Waiting |
| X8 | srvstfunc / cltstfunc | "not confirmed" / max 61 | 94 slots; cltstfunc 70 at `0x235f590` | H | Waiting |
| X9 | Cube portal | Only the Cow Level | `Red Portal,lvl=<id>` reaches any same-act level | H | Waiting |
| X10 | Memory pools | Renderer pool fixed at 12 MB | Six pools grow at runtime | G | Waiting |
| X11 | Item code length | 4 characters | items.json keys by 3 without a patch | G | Waiting |
| X12 | Which banks to write | Write both | P: RotW only; 9: both, keeping Warlock placeholders | H | Waiting |
| X13 | Reviewer | Coordinator reviews and merges | Separate reviewer, fix-cycle cap, docs-only PRs skip CI | I | Waiting |
| X14 | No free slot | Poll about 30 minutes | Stop and file `ready-for-agent` | I | Waiting |
| X15 | Screenshots | Never commit | Orphan `issue-assets` branch; never on `main` | H | Waiting |
| X16 | Changelog | Coordinator writes version sections | Fragments only | F / I | Waiting |
| X17 | Test character | — | Level 99, XP 3520485254, 490 stat points, 98 skill points (your rule) | H | Waiting |

## Lane I: methods, templates and skills

Waiting. The three repos carry drifting copies of the same agent scaffold; this lane writes it once in the toolkit. Per-repo values (repo name, slots, labels, testing config) go in a small `.d2r-project.toml`.

| # | Item | What it does | Sources | Toolkit home | Size | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| I1 | Agent scaffold | `AGENTS.md` pointer plus `docs/agents/{issue-tracker,triage-labels,domain}.md`; F's issue tracker is the base | P, F, 9 | `templates/agents/` + new `d2r-project-conventions` skill | M | Waiting |
| I2 | Issue and PR rules | `Closes #n` / `Part of #n`; sub-issues by database id; delete merged branches; `research/*`, `issue-assets`, `handoff/*` never merged | P | `d2r-project-conventions` | S | Waiting |
| I3 | Wayfinder labels | A map issue with children typed research / prototype / grilling / task | F | `d2r-project-conventions` (optional) | S | Waiting |
| I4 | Triage labels | Five labels plus `origin-bug` and its ledger | P, F, 9 | `templates/agents/triage-labels.md` | S | Waiting |
| I5 | Gate rule | Docs-only PRs skip CI unless they touch gate inputs; green on the final head plus MERGEABLE; offline runners mean a local run with the report | P | `d2r-project-conventions`, `templates/workflows/` | S | Waiting |
| I6 | `ORDER` rule | A new pass or hook is a new module with `ORDER`, never a shared list | P | `templates/` | S | Waiting |
| I7 | Roadmap | Lettered work items, one session each, status on issues, a Blocked-by column | P | `templates/PLAN.md` | S | Waiting |
| I8 | ADRs | `docs/adr/NNNN-<slug>.md` with Status, Context, Options, Decision, Consequences, Amendments (your decision of 2026-11-11) | P, F, 9 | `templates/ADR.md`, `ai-workflow.md` | S | Waiting |
| I9 | Ledgers | Deviations (feeding `diff.gate`), origin bugs, D2R-only approvals | P, 9 | `templates/deviations.md`, `origin-bugs.md`, `d2r-only-content.md` | S | Waiting |
| I10 | Research docs | One `research/<topic>` branch per ticket; header, evidence labels, hash-pinned sources, short answer, options, unverified list | F, 9 | `templates/research.md` | S | Waiting |
| I11 | Orchestrator method | Never implements; separate implementer and Opus reviewer; at most 5 agents and 2 fix cycles; handoff on an orphan branch | P | `d2r-coordinator`, `coordinator-prompt.md`, new `templates/handoff.md` | M | Waiting |
| I12 | Game-check recipe | Lock → install → pin DS1 → start → cheats → warp → shoot → upload → unlock → report; screenshot rules | P | `docs/testing.md`, new `d2r-in-game-testing` skill | M | Waiting |
| I13 | Testing rules | Hell, RotW characters, console over clicks, 10 minutes without progress → `ready-for-human`, one lock from install to cleanup, never `lock any`, count skips | P, F | `d2r-in-game-testing` | S | Waiting |
| I14 | Merge-slot pool | Machine-wide cap on heavy builds, slots kept for CI | P | `docs/testing.md` | S | Waiting |
| I15 | Worktree hygiene | Junction-safe removal; never `--delete-branch` / `worktree remove --force` with junctions | P | `d2r-project-conventions` | S | Waiting |
| I16 | Naming | Conventional commit prefixes with issue numbers; `ticket/<n>-<slug>`, `research/<topic>`, `refactor/<topic>` | 9 | `d2r-project-conventions` | S | Waiting |
| I17 | Pin bumps | `chore: pin d2rAI-toolkit to <sha>` commits | 9 | `d2r-toolkit` skill | S | Waiting |
| I18 | Generated data | Made by a script, checked by a test; game data outside the repo | 9, P | `d2r-project-conventions` | S | Waiting |
| I19 | Documentation audit | Periodically check claims and links against `main` | P | `ai-workflow.md` | S | Waiting |
| I20 | Player docs | Player README outline, GLOSSARY template | P | `templates/` | S | Waiting |

**Keep or throw the toolkit's existing files** (decides how I1–I20 land)

| # | Existing | Recommendation | Approval |
| --- | --- | --- | --- |
| IK1 | `templates/coordinator-prompt.md` | Keep, rewrite with the orchestrator method | Waiting |
| IK2 | `templates/lane-prompt.md` | Keep, merge in the brief rules | Waiting |
| IK3 | `templates/lane-rules.txt` | Throw (replaced by I1) | Waiting |
| IK4 | `templates/bugs.md` | Throw, or keep as an option without GitHub | Waiting |
| IK5 | `templates/PLAN.md` | Keep the file, replace its content (I7) | Waiting |
| IK6 | `templates/CHANGELOG.md` | Replace with fragments (F2) | Waiting |
| IK7 | `templates/owner-update.md` | Keep, trim to one line per vital update or blocker | Waiting |
| IK8 | `docs/ai-workflow.md` §1–12 | Keep, update for X1, X13, X14, X16; drop §6 if `bugs.md` goes | Waiting |
| IK9 | `d2r-coordinator` skill | Keep, merge in I11 | Waiting |
| IK10 | `d2r-release`, `docs/release.md`, `docs/testing.md` | Keep | Waiting |

## Issues raised

Each approved lane now has a toolkit issue for the work, plus a switch issue in every mod that holds a copy. Each switch issue lists, row by row, what to delete, what replaces it and what the mod keeps. It also has step-by-step agent instructions: check the blockers, follow the toolkit PR's final names, bump the pin, compare old and new output, delete, then grep. All are labelled `ready-for-agent` and blocked natively, so a switch issue can only start once its toolkit lane issue closes. pd2-resurrected's are also blocked by its alpha (#143).

| Lane | Toolkit work | pd2-resurrected (public) | resurrected-09 | Project Forever |
| --- | --- | --- | --- | --- |
| A | [toolkit #46](https://github.com/synpoox/d2rAI-toolkit/issues/46) | [#931](https://github.com/synpoox/pd2-resurrected/issues/931) | — | — |
| D | [toolkit #47](https://github.com/synpoox/d2rAI-toolkit/issues/47) | — | [#90](https://github.com/synpoox/resurrected-09/issues/90) | — |
| E | [toolkit #48](https://github.com/synpoox/d2rAI-toolkit/issues/48) | [#932](https://github.com/synpoox/pd2-resurrected/issues/932) | [#91](https://github.com/synpoox/resurrected-09/issues/91) | [#60](https://github.com/synpoox/resurrected-forever/issues/60) |
| F | [toolkit #49](https://github.com/synpoox/d2rAI-toolkit/issues/49) (now parent of #6, #7) | [#933](https://github.com/synpoox/pd2-resurrected/issues/933) | — | — |
| G | [toolkit #50](https://github.com/synpoox/d2rAI-toolkit/issues/50) | [#934](https://github.com/synpoox/pd2-resurrected/issues/934) | [#92](https://github.com/synpoox/resurrected-09/issues/92) | — |

Parents: pd2-resurrected [#924](https://github.com/synpoox/pd2-resurrected/issues/924); resurrected-09 [#89](https://github.com/synpoox/resurrected-09/issues/89), new. Project Forever has a single switch issue, so it has no parent.

Found while checking the mods:

- The monster-AI fix (D8) is resurrected-09 [#93](https://github.com/synpoox/resurrected-09/issues/93). It is on hold, without the agent label, and still blocks that repo's lane D switch, #90. Release or drop that link when D8 is decided. Toolkit #47 matches its output.
- Slots (amended 2026-11-11): pd2-resurrected owns Slot4–8 (its `AGENTS.md` already says so; #932 swaps that text for a pointer to the registry). resurrected-09 owns Slot9–10 (its README already says so; #91 does the same).
- G1 and G10–G12 are now in toolkit #50, pd2-resurrected #934 and resurrected-09 #92.
