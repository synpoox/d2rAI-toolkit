# Consolidation plan: one toolkit for every mod project

Status: plan, 2026-11-11. This file lives on the `plan/consolidation` branch only and is never merged. It names the
source projects (CLAUDE.md rule 11 keeps project names off `main`). Everything that moves into the toolkit is rewritten
without project names.

Source projects, read at these `origin/main` commits plus their unmerged branches:

| Project | Repo | Commit | Notes |
|---|---|---|---|
| pd2-resurrected | synpoox/pd2-resurrected | 97489f6 | Most of the reusable work |
| Project Forever | synpoox/project-forever (folder `resurrected-forever`) | dc15829 | Research branches, plus uncommitted agent docs and inventories |
| resurrected-09 | synpoox/resurrected-09 | 2a7a77a | 1.09d data and research, plus uncommitted agent docs |
| toolkit | synpoox/d2rAI-toolkit | 3731315 | Target |

## 1. Decision: local first

The toolkit stays a local checkout beside the projects. Making it consumable from GitHub alone (pip from git, CMake
FetchContent, a remote plugin marketplace, CI tokens) is deferred. The reasons:

- All development, game slots, Ghidra and the self-hosted runner are on one PC.
- The packaging work is large.
- It does not make future projects faster; the content does.

Section 9 lists what triggers revisiting this and keeps the design.

What local first still requires (phase 1):

- **One way to find the toolkit.** `D2R_TOOLKIT`, else walk up the parent folders for `d2rAI-toolkit/`. The toolkit
  ships it in three forms: Python `tools/toolkit_path.py`, PowerShell `tools/ToolkitPath.ps1` and CMake
  `cmake/FindD2rToolkit.cmake`. Projects stop keeping their own copies: pd2-resurrected has 3 copies plus `classic()`
  shims, resurrected-09 has 3.
- **One pin per project.** Each project has a `toolkit.version` file holding a toolkit commit. The toolkit's locator
  warns when the local checkout does not contain that commit. CI checks out the pin instead of `git pull`.
- **Skills and knowledge loaded in every project.** The toolkit becomes a Claude Code plugin served from a local
  directory marketplace:
  - It is registered once in user settings, and each project enables it in `.claude/settings.json`.
  - Skills and knowledge are written once and load in every repo.
- **Links, not local paths.** Docs in projects link to `https://github.com/synpoox/d2rAI-toolkit/blob/<commit>/...`, never
  to `../d2rAI-toolkit` or a user folder. This also keeps the deferred remote step small.

## 2. Rules for every move

1. **Generic moves, constants stay.** A moved module takes the project's data as parameters or config: id lists,
   rules maps, scopes, mod name, slot numbers. The project keeps a thin driver.
2. **Tests move with code.** A module never moves without its unit tests. Fixtures are made synthetic where they
   embed project data.
3. **Copy first, switch later.**
   - The toolkit gains the generic version first.
   - The project switches in a separate PR and deletes its copy.
   - pd2-resurrected switches only after its alpha (target about 2026-11-17).
4. **No project names in moved text** (rule 11).
   - Use "the source mod", "a classic port" or "a 1.13c-based mod".
   - pd2-resurrected's `PD2R_*` env vars become `MODKIT_*`.
   - Do not name other community mods either. Say "another community mod".
5. **Contradictions are settled, not copied.** Where a project finding contradicts toolkit knowledge (section 6), the
   move PR updates the toolkit text and cites the evidence.
6. **Build-specific values are marked** with the build number (rule 10).

## 3. Phase 0: before anything moves

| # | Repo | Task |
|---|---|---|
| 0.1 | Project Forever | Commit the uncommitted `AGENTS.md`, `docs/agents/{domain,issue-tracker,triage-labels}.md` and `docs/research/*` (5 inventories plus `source-document-inventory.json`). **Do not** commit the uncommitted `GLOSSARY.md`: it is an old 6-line stub, and main has the real one. Fix the repo name in `issue-tracker.md`; main's docs mix `project-forever-clean` and `resurrected-forever`. Local `main` is behind origin, so pull first. |
| 0.2 | resurrected-09 | Commit the uncommitted `AGENTS.md` and `docs/agents/*`; the uncommitted `GLOSSARY.md` is the old version. Fix the stale `synpoox/project-09` in `issue-tracker.md`. `domain.md` still points at `docs/adr/`, which was replaced by map issue #12: pick one. Local `main` is 31 commits behind. |
| 0.3 | Project Forever, resurrected-09 | Adopt pd2-resurrected's rule that `research/*` branches are never merged or deleted. Most of these two projects' generic findings live only on unmerged research branches, and they are sources for phase 2. |
| 0.4 | toolkit | Add `pd2-data/` to `.gitignore` or move it out of the repo. Delete or move `mpyq-0.2.5.tar.gz`, `hs_err_pid*.log` and `replay_pid*.log`. Commit or drop the uncommitted `tools/ghidra_scripts/{FuncsInRange,RangeAsm}.java`. |
| 0.5 | toolkit | Hygiene. Clear out the existing rule-11 breaches (section 7). |

## 4. Phase 1: local wiring (toolkit, then each project)

| # | Where | Task |
|---|---|---|
| 1.1 | toolkit | `tools/toolkit_path.py`, `tools/ToolkitPath.ps1`, `cmake/FindD2rToolkit.cmake`: env var, then a parent walk (this works from worktrees), then a pin check against `toolkit.version`. |
| 1.2 | toolkit | Plugin and marketplace. `.claude-plugin/marketplace.json` plus `plugin.json` exposing the 12 `d2r-*` skills and the new method skills from section 5.9. Skills reference knowledge through `${CLAUDE_PLUGIN_ROOT}`. Document the one-time user-settings registration in `docs/ai-workflow.md`. |
| 1.3 | toolkit | Split `CLAUDE.md`. Maintainer rules stay. Consumer guidance moves to a `d2r-toolkit` skill: what the toolkit offers, how to find it, the pin, and "new generic work starts here". |
| 1.4 | toolkit | `plugin-template` and `plugin-common` take the toolkit's PluginSDK submodule. Both projects pin the same SDK commit (03a5af9) today, so their own submodules can go. |
| 1.5 | resurrected-09 | `toolkit.version` (from the README pin b8b4ae9, bumped). Swap `R09_TOOLKIT_DIR` in `plugin/CMakeLists.txt`, the `D2R_TOOLKIT` lookups in `merge/column_map.py` and `to_113c.py`, and the `game_checks.__file__` lookup in `dr_cap_checks.py` for 1.1. Enable the plugin. |
| 1.6 | Project Forever | `toolkit.version`; fix the placeholder in `tests/game/slot_install_checks.py`; enable the plugin. |
| 1.7 | pd2-resurrected (after alpha) | `toolkit.version`, replacing `README.md:77`. Swap `pd2_table.toolkit()`, `pd2_ids` re-export, the `classic()` shims, `install.ps1` and `plugin/CMakeLists.txt` for 1.1. `gate.yml`, `release.yml` and `cache-verify.yml` check out the pin on the runner instead of `git pull --ff-only`. Enable the plugin. |
| 1.8 | all three | Rewrite doc links that point at local toolkit paths or user folders as GitHub links at the pinned commit. This includes pd2-resurrected's `docs/agents/*`, README and research, and Project Forever's inventories. Data paths like `d2r-data/93847` become "`modkit fetch` cache". |

## 5. Phase 2: everything reusable, by destination

Sizes: S under half a session, M one session, L several. "Source" uses **P** = pd2-resurrected, **F** = Project
Forever, **9** = resurrected-09. A path followed by `@branch` lives only on that unmerged branch. `@history` means a
file deleted from main, readable at `9886e2b^`.

### 5.1 `shared/classic_import`: table and id layer (merge forks first)

pd2-resurrected still runs older forks of code the toolkit has already generalized. Settle this layer first; most
other P tools import it.

| Source | Item | Action | Size |
|---|---|---|---|
| P | `tools/pd2_ids.py` | Merge the generic algorithm (append-only ids, renames, formula and ref rewrites, `merge_table`) into `ids.py`. P keeps REFS, FORMULAS, FUNCS, FIXES, `_NPC`, `PLAIN_STRINGS`, `_TIER`, `MAP_SPELL`, HIT_PARAMS, MISSILE_FUNCS and LEFT_OUT_LEVELS. | L |
| P | `tools/pd2_tables.py` | Delete in favour of `tables.py`; port any missing operation first (rows, repeats, move, cells). | M |
| P | `tools/pd2_diff.py` | Keep a CLI shim with ITEM_TABLES and the P2/P3/P4/M1/alpha scopes; the rest is `diff.py`. | M |
| P | `tools/pd2_table.py` | Use `ids.Table`; keep the CRLF-safe and Expansion-row handling if `ids.Table` lacks it. | S |
| P | `tools/pd2_cache.py` + `pd2_cache_verify.py` | New `cache.py` / `cache_verify.py`: machine-wide extract and rule caches, file locks, code-hash rule keys (`toolkit_sources`), CI policy, merge-slot semaphore. Rename `PD2R_CACHE`, `_CI_SCOPE`, `_MERGE_SLOTS`, `_CACHE_GB` to `MODKIT_*`. | L |
| P | `tools/pd2_merge.py`, `pd2_extract.py` | Move the lock, cache replay, output check and junction into `merge.py` / `extract.py`. P keeps its RULES map. | M |
| P | `tools/pd2_items.py` | `items.py`: item tables by key, cube merge, no-drop types, HD pictures for new items. | M |
| P | `tools/pd2_strings.py` | `strings.py` rule: overrides, renames, `--assign` of new string ids. Add the `.tbl` reader to `modkit/strings.py`. | M |
| P | `tools/pd2_animdata.py` | `modkit/animdata.py` (animdata.d2 read, write, merge) plus a classic_import rule. | S |
| P | `tools/pd2_sounds.py` | `sounds.py`: WAV to FLAC, sounds.txt rows copying D2R-only columns from `like`. | S |
| P | `tools/pd2_{missiles,monsters,objects,overlays}_hd.py` | One `hd_entries.py` with four kinds. | M |
| P | `tools/pd2_standins.py` | `standins.py`: point unbuilt function columns at D2R rows. | S |
| P | `tools/pd2_skilldesc.py` | `skilldesc.py`: rewrites descline function, text and calc. | M |
| P | `tools/pd2_skill_icons.py` | `skill_icons.py`: classic DC6 icons to HD strips, hireling icons. | M |
| P | `tools/pd2_automap.py` | `automap.py`: classic automap cels appended to HD tiles. | S |
| P | `tools/pd2_levels.py` | `maps/levels.py`: lvltypes, objpreset, DS1 id rewrite, monpreset. Needs 5.2's DS1 reader. | M |
| P | `tools/tests/test_{ids,tables,diff,strings,items,animdata,sounds,*_hd,standins,skilldesc,skill_icons,automap,cache*,memo,pipeline,deviation_counts}.py` | Move with the modules. `test_deviation_counts` becomes `tools/check_deviations.py`. | L |
| 9 | `merge/109d-to-113c-column-map.{json,tsv}` + value maps (dropsound/usesound, `anim` to mode codes, `transformcolor`, SkillNSeq) | Dataset in `shared/classic_import/data/`. | L |
| 9 | `merge/column_map.py` (+ the 17 early scripts on `@research/109d-vs-113c-columns`) | Generator `gen_109d_map.py` with hash-checked MPQ stack and `.bin` widening proof. Drop the scratch scripts. | M |
| 9 | `merge/to_113c.py` | `from_109d.py`: recode hooks (×16 SrcDam, row to name, Lookup, carry_copies), forward and back. **Fix first:** it still recodes `BaseId` as a row and copies AIParamN to aipN, which `@research/monster-ai` shows is wrong. | M |
| 9 | `merge/test_to_113c.py`, `test_column_map.py` | `tests/test_classic_import_109d.py`: round trip, BLANK_IS_ZERO, widening. | S |
| 9 | `docs/research/skill-functions.tsv` | `data/109d-skill-functions.tsv`: 2088 skill and missile pairs, each a 1.09d address mapped to a D2R index and RVA, with a verdict. | M |
| 9 | `09-baseline.json`; `@research/109d-stock-files` hash list | `baselines/109d.json` (install path dropped), plus the list of files that are "not part of 1.09d". | S |
| P | `pd2-baseline.json` | `templates/baseline.example.json`. | S |
| 9 | Monster AI pairing (BaseId to D2R AI) | New dataset, generated. Only 9 of 169 pairs are read today. | M |

### 5.2 `shared/classic_import/maps`: DS1 to HD presets and scoring (P, one unit)

These files depend on each other and move together. The PD2 constants are few: jungle UNWALKABLE ratios, the TERRAIN
preset, `merge/presets-hd.d` and overrides paths, and the scorer baselines.

| Item | Size |
|---|---|
| `pd2_ds1.py` + `presets/dt1.py` go to `modkit/ds1.py` (DS1 v18 or lower, DT1, lvltypes readers) | S |
| `pd2_terrain.py` goes to `modkit/terrain.py` (terrain.physics ground height) | S |
| `pd2_tiles.py`, `pd2_painter.py`, `pd2_presets.py` + `tools/presets/**` (core, 8 hooks, 15 passes, `fence_kit.json`), `hd-folder-types.tsv` | L |
| `pd2_overrides.py` + `pd2_presets_lint.py` (per-map override ops and stale-op lint) | M |
| `pd2_dt1_copies.py` (DT1 tiles that are pixel copies of D2R tiles) | S |
| Scorers `pd2_coverage.py`, `pd2_fidelity.py`, `pd2_parity.py`, `pd2_lighting.py`; they take the area lists as input | L |
| Tests: `test_presets_*`, `test_edges_*`, `test_floor_height`, `test_ds1cache`, `test_dt1_copies`, `test_terrain`, `test_lighting`, `test_levels`, `test_coverage*`, `test_fidelity`, `test_parity`, `test_overrides`, `presets_fixtures.py` | L |
| Branch work for the knowledge side: `@research/lp3-border-painter`, `@research/lp3-tile-table`, `@research/hd-parity-strategy`, `@research/pd2-only-levels` (the DS1/DT1 method) | M |

### 5.3 `modkit`: art

| Source | Item | Action | Size |
|---|---|---|---|
| P | `tools/pd2_art.py` | `modkit/upscale.py`: Real-ESRGAN ×4 with a committed hash cache and icon style; tool path from config. | M |
| P | `tools/pd2_panels.py` | `modkit/panels.py`: widen panel grid art by N columns (HD, lowend, DC6). | S |
| P | `tools/pd2_skilltrees.py` | `modkit/skilltrees.py`: redraw tree sprites at merged skill positions; measured JSON stays data. | M |

### 5.4 `testing/`

| Source | Item | Action | Size |
|---|---|---|---|
| 9 | `tests/game/stats.py` + `test_stats.py` | `testing/stats.py`: binomial rate assert at 4σ, seeded counts. Unchanged. | S |
| 9 | `tests/game/skeleton_checks.py` | `testing/lod_checks.py`: `plugin_log`, `read_save`, `save_and_exit` (waits for the `RD` marker and the `.d2rl` sidecar), and the create/save/reload character flow. The plugin, mod and character come in as parameters. Menu fractions go to a shared constants module (3.3, 1920x1080). | M |
| 9 | `tests/game/dr_cap_checks.py` `_image()` | `testing/image_bytes.py` beside `tools/dump_image.py`: assert the PE stamp, read RVA spans, compare stock and patched. | S |
| 9 | `tests/game/d2r_only*.py` + `test_d2r_only.py` | `testing/d2r_only.py`: zone-switch scan, Colossal portal, Terror Zone purple-pixel detector (calibrated on 93847), `heraldspawn` positive control. | M |
| 9 | `tests/game/leech_checks.py` @ticket/29-leech | `testing/save_edit.py`: unlock difficulties (byte 0x15 = 0x0f, bytes 0x98–0x9a, then `finalize`). | S |
| P | `tests/game/*_checks.py` `_log(ctx)` | `check_helpers.plugin_log()`. | S |
| P | `tests/game/missile_probe.py` | `testing/unit_probe.py`: read-only unit and missile counter; RVAs come from the address registry. | S |
| P | `tools/pd2_edge_tour.py` | `testing/edge_tour.py`: plan warps along map edges, capture HD and legacy pairs. Reuse `check_helpers.pair` and `goto_line`; drop the duplicate subtile maths. | L |
| P | `tools/contact_sheet.py` | `testing/contact_sheet.py`: contact sheet plus luma and black-pixel metrics. Merge with `check_helpers.side_by_side`. | S |
| P | `tools/pd2_warps.py` | `testing/warps.py`: generate a `cheat goto` doc for added maps. | S |
| P | `tools/pd2_force_ds1.py` | `testing/force_ds1.py`: pin a DS1 variant in a slot; mod folder read from `mod.json`. | S |
| P | `tests/game/fixtures/*` | Pattern only: a fixture mod.json plus patch per check, documented in `testing/README.md`. | S |
| F | `tests/game/slot_install_checks.py` | Stock `slot-savepath` check: both modinfo savepaths equal the slot folder. | S |
| new | Slot registry | One machine-wide slot-to-owner table that `game_slots lock` enforces. Today ownership is restated in P's `game-slots.md`, F's inventory and the owner's notes, and `lock any` can take another project's slot. Today's owners: Slot2 tools test, Slot3 Project Forever, Slot4–8 pd2-resurrected, Slot9–10 resurrected-09. | M |
| new | Testing config default | With no config, the tools refuse to touch a slot instead of silently using the toolkit's default config (a trap P documents). | S |

### 5.5 `release/` and `tools/`

| Source | Item | Action | Size |
|---|---|---|---|
| P | `tools/release.py` | Fold changelog fragments and stage a release, both inside `release/`. Plugins, the staging list and the filter-table fill come from `release.toml`. | M |
| P | `changelog.d/` convention + `CHANGELOG.md` shape | `templates/changelog.d/README.md`; replace the per-version-sections `templates/CHANGELOG.md`; update `docs/release.md` and the `d2r-release` skill. | S |
| P | `tools/companions.py` + `companions/manifest.json` schema | `release/companions.py`: fetch community plugins pinned by SHA-256, overlay config, install. FILTER_TABLES, ITEM_RANGES and the item toggle become per-entry manifest options. | M |
| P | `tools/install.ps1` | `tools/install_plugins.ps1`: built plugins plus savepath restore plus stray-plugin quarantine, on top of `modkit install` / `slot_install`. | S |
| P | `tools/worktree_remove.ps1` + `tests/tools/worktree_remove_test.ps1` | `tools/`: worktree removal that is safe with junctions. | M |
| P | `.claude/settings.json` SessionStart hook (warns when HEAD lacks `origin/main`) | Ship it in the plugin (1.2) as a hook. | S |
| P | `docs/research/skill-function-tables/probe_tables.py` | `tools/probe_tables.py`. | S |

### 5.6 CI templates (`templates/workflows/`)

All from P. Runner labels, cache path, labels and titles become inputs.

| Item | Size |
|---|---|
| `tests.yml` (unit tests on ubuntu) | S |
| `gate.yml` + `gate-control.yml`, as a pair: the self-hosted table-diff gate, cache replay, never-skip trick, docs-only path filter, cancel and rerun by label | M |
| `cache-verify.yml` (nightly fresh vs cached merge) | S |
| `release.yml` (self-hosted full build plus GitHub release) | S |

### 5.7 `shared/plugin-common` and `plugin-template` (C++)

| Source | Item | Action | Size |
|---|---|---|---|
| P | `plugin/common/pd2_engine.h` | Promote nearly whole: about 233 of its 327 RVAs are missing from the toolkit. Split `rvas_93847.h` by area: tables, hits and damage, units and paths and pets, data-table offsets, stats, items and cube, levels and rooms, AI, client, memory pools. Structs (`StateListRequest`, `AreaContext`, `CrushingBlowArgs`, `LeapKnockback`, `CurseParams`) go to `d2r.h`. Trim the PD2 comments. Also align the headers' two policy lines ("shared values move to the toolkit" vs "values one project needs stay there"). | L |
| P | `plugin/core-maps/entity_pool.*` | `pool_grow.*`: `tlsf_add_pool` for the Entity, Renderer, JSON, Object, Jobs and Texture pools; pool sizes go into knowledge. | M |
| P | `plugin/core-maps/ai_hooks.*` | `ai_registry.*`: monster think functions registered by monai row and class, with D2R fallback. | M |
| P | `plugin/core-ui/automap.*` | `automap_ext.*`: automap lookup for level types 36 and up. | M |
| P | `plugin/core-ui/item_pictures.*` | Shared patch so items.json keys 4-character codes. | S |
| P | `plugin/core-ui/level_palette.*` | Shared: reload the act palette on a level change without a load screen. | S |
| P | `plugin/core-rules/skill_functions.*`, `missile_functions.*` | `plugin-template/skill_router.*`: router-slot dispatcher plus missile function signatures. The PD2 skills stay. | L |
| P / 9 | `plugin/*/plugin.cpp` part table and status command (9's `{word, engine, install}` table is the cleanest) | `plugin-common/parts.h`; update the template. | M |
| P | `plugin/CMakeLists.txt`, `plugin/build.ps1` | Template supports several plugins in one project, uses 1.1's locator, and initialises the SDK submodule in a fresh worktree. | S |
| 9 | `plugin/09-rules/dr_cap.cpp` | Address fact only: DR cap at 0x4524d0, 50 in D2R vs 75 in 1.09d. | S |
| 9 | `plugin/09-rules/leech.cpp` @ticket/29-leech | Hook 0x450c90 plus offsets into `rvas_93847.h`; 1.09d leech rounding goes into knowledge. | S |
| P | `plugin/core-maps/level_fx.*` | Address facts: act darkness packet 0x53, level sound packet 0x2c. | S |

### 5.8 `knowledge/`: engine and game facts

Generic parts only. Each row names the file it lands in.

**From pd2-resurrected**

| Source doc | Lands in | Size |
|---|---|---|
| `docs/research/d2rloader-capabilities.md` (capability matrix, loader 1.3.1 / SDK 0.4.0) | new `knowledge/d2rloader-capabilities.md` | M |
| `docs/research/skill-function-tables.md` (all function tables, bounds, free slots, readers, router idea; cltstfunc `0x235f590`, srvdmg `0x2391270`) | `d2r-93847-addresses.md`, `engine-limits.md` | M |
| `core-rules-inventory.md`, `pd2-engine-dll-triage.md` (bucket a source DLL's rules, slot-collision checklist, DLL triage from strings) | `porting-classic-mods.md` §1, §5 | M |
| `pd2-data-inventory.md` (1.13c vs D2R 3.3 tables, columns, events, saves v96 vs v105) | `porting-classic-mods.md` §3 | M |
| `pd2-asset-inventory.md`, `pd2-strings-inventory.md` (D2R string-id budget, reversed multi-line skill text) | `strings.md` | S |
| `plrmodes.md`, `stack-split.md`, `states-immed.md` (reading 1.13c patch tables; 1.13c never reads states `immed`) | `porting-classic-mods.md` §3, §6 | S |
| `ms2-*`, `ms3-*`, `ms4-*`, `ub2-*` (map opening, map stats, monster region, portal maker, item spell 16 / `0x236fe30`) | `d2r-93847-addresses.md`, `new-game-systems.md` | M |
| 25 work-item notes in `docs/research/` (class skills vs D2R do/hit functions) | The D2R function signatures and slots go to `d2r-93847-addresses.md`; the rest stays | M |
| `docs/adr/0001` (RotW bank only), `0002` (source data generated from a hash-pinned extract), `0003` (extended saves, append-only ids) | `porting-classic-mods.md` §0 "decisions to make first" and §2 | S |
| `docs/adr/0004` (plugins split by multiplayer scope; when a system gets its own DLL) | `d2rloader.md` "Plugin flags", `new-game-systems.md` | S |
| `docs/adr/0005` + `docs/hd-preset-overrides.md` (HD presets from DS1: room paste, 3x3 patch, border painter, override ops) | `hd-graphics.md` "Presets for new DS1 levels" | M |
| `docs/modkit-validation.md` (validation errors and causes; fixes need an in-game proof) | `modkit-ops.md` | M |
| `docs/core-rules.md` (format of the hook list: rule, source, bucket, slot, RVA) | `porting-classic-mods.md` §5 template | S |
| `docs/deviations.md`, `pd2-origin-bugs.md`, `d2r-only-content.md` (status vocabulary, origin-bug ledger, D2R-only approval ledger) | `porting-classic-mods.md` §10, plus templates in 5.9 | S |
| `GLOSSARY.md` fidelity terms (deviation, exact, approximated, cut, router slot, companion plugin) | `porting-classic-mods.md` §0 | S |
| `plugin/core-ui/item_quantity.*`, `stack_split.*` (loader gaps: WidgetService has no screen rect, OverlayService draws nothing, TCP/IP clients have no game thread) | `d2rloader.md` | S |
| `docs/agents/game-slots.md` (RotW-character trap, `cheat expansion 2` crash, LoD badge) | `cheat-commands.md` | S |
| `@research/reimagined-map-system` (how another community mod built maps, the limits it hit, licence) | `new-game-systems.md`, without naming the mod | M |
| `@research/suite-companions` (which community plugins coexist with your hooks) | `d2rloader.md` "Other plugins" | S |

**From resurrected-09**

| Source doc | Lands in | Size |
|---|---|---|
| `docs/research/skill-functions.md` (1.09d dispatch charts vs D2R tables; class row ranges; loader-thunked slots) | new `knowledge/classic-109d-engine.md` | L |
| `@research/monster-ai` (AI table 1.09d 0xebac8 vs D2R 0x2396e90; BaseId picks AI; AIParam slots moved in 1.10) | `classic-109d-engine.md` | M |
| `@research/109d-to-d2r-code-changes` (about 60 rule differences, with addresses) | new `knowledge/classic-109d-vs-d2r.md` | L |
| `@research/109d-vs-113c-columns` (75 vs 92 tables, number vs name refs, SrcDam ×16, row shifts) + `merge/README.md` (1.13c `.bin` = 1.09d `.txt` widened) | new `knowledge/classic-109d-tables.md`, `porting-classic-mods.md` | M |
| `@research/109d-stock-files` (per-file hashes, Version Changer 4.6 provenance, NoCD, code-cave diff) | new `knowledge/classic-reference-installs.md` | M |
| `@research/runtime-capabilities` `d2r33-loader-capabilities.md` (loader 1.3.1 ships SDK 0.3.0 vs 0.4.0 headers; Battle.net 93847 vs Steam 93787; closed source, no redistribution) | merge into `d2rloader.md` / `d2rloader-capabilities.md` | S |
| `@research/warlock-leftovers-on-lod` (LoD bank keeps Warlock placeholder rows; `sounds` always reads `excel/`; converted characters read `excel/`; RotW-only flags) | `tables.md` "Two banks" | M |
| `@research/baseline-evidence` `lod109d-evidence.md` (evidence hierarchy, observation record) | new `docs/fidelity-evidence.md` | S |
| `@history` `docs/design/gameplay-fidelity.md` (exact / approximated / cut, timing, acceptance of random distributions) + old GLOSSARY disposition terms | new `docs/fidelity-policy.md` | M |
| `@history` `docs/design/runtime-support.md` (runtime qualification checklist; first 3.3 loader was 1.2.0-beta) | new `docs/runtime-qualification.md` | M |
| `@history` `docs/design/technical-approach.md`, ADRs 0001–0003 (fixed game plus rolling loader, data first plus targeted hooks, extended saves from the start) | `docs/ai-workflow.md` "decisions for a port", `porting-classic-mods.md` §0 | S |
| `GLOSSARY.md` (reference install, deviation, table set, column vs rename map, placeholder row) | `porting-classic-mods.md` glossary | S |
| `@ticket/29-leech` leech model (D2R 1/64 fixed point, player-only divide vs 1.09d) and the DR cap | `classic-109d-vs-d2r.md` | S |
| `docs/design/d2r-conveniences.md` (candidate list only) | new `knowledge/d2r-conveniences.md` | S |
| `patches/24-d2r-only-content.json` (Terror Zones, Heralds, Colossal portal off) | `examples/patches/no-terror-zones.json` | S |

**From Project Forever**

| Source doc | Lands in | Size |
|---|---|---|
| `@research/flask-runtime` (pSpell 16–19, the not-consumed flag in the spell table `0x236fe30`, charge stores: quantity, stat 204, new stat; `ItemInteractionService` scope; `editItem` limits; stat 253) | new `knowledge/charged-items.md` | L |
| `@research/save-freeze` (retail id widths, extended limits 1 MiB / 247 pages / Recovery, 5 to 6 migration, freeze table, retroactive-but-unstored changes, savepath hides characters) | `saves.md`, plus a "freeze before release" section in `tables.md` | L |
| `@research/map-hosting` (clone `levels` rows onto stock tiles; level id ≤255 and Layer <100; `Red Portal,lvl=`; per-game resets; Terror Zone data in `desecratedzones.json`; no zone API) | `new-game-systems.md` "map hosting", `tables.md` Terror Zone section | L |
| `@research/d2r-play-modes` (official vs community support, TCP/IP, ladder claims, offline auth, the 2.5 migration warning, EULA flag) | `docs/distribution.md` "play modes and policy" | M |
| `@research/archetype-weaknesses` (3.3 dead and trap skills, patch-history facts) | optional new `knowledge/class-balance-notes.md` | L |
| `docs/research/pd2-re-inventory.md` (hook-ownership collision at `0x43acb0`: one owner per hook site) | `engine-re.md` | S |
| `docs/research/in-game-testing-inventory.md` (hazards: an acknowledgement is not command output, the background flag, zero-durability reloads, a held cursor item, broken `cheat item`/`gold` substitutes, `--no-validate` debt) | `docs/testing.md` "practical hazards" | M |
| `docs/research/reusable-foundations.md` (prepared vs fresh characters; exit 0 ≠ no skips) | `docs/testing.md` "evidence levels" | S |
| `docs/research/pd2-project-inventory.md` ("a decision record does not prove the work landed"; read research in date order) | `docs/ai-workflow.md` "status drift" | S |
| `docs/research/source-document-inventory.json` (pin sources by hash) | The pattern goes into the research template (5.9) | S |
| `docs/adr/0001` (stored vs live rules for owned items) | `saves.md` "retention policy" note | S |
| `docs/play-modes-and-leagues.md` (feasibility checklist) | `docs/distribution.md` | S |
| `docs/research/toolkit-inventory.md` drift list | Toolkit issues (section 6) | S |

### 5.9 Methods, templates and skills

The three repos carry drifting copies of the same agent scaffold. Write it once in the toolkit, with per-repo values
(repo name, slots, extra labels, testing config) in a small `.d2r-project.toml`.

| Item | Sources | Toolkit home | Size |
|---|---|---|---|
| `AGENTS.md` pointer pattern + `docs/agents/{issue-tracker,triage-labels,domain}.md` | P, F, 9 (F's issue tracker is the most careful: verify the repo first, `--body-file`, comment then close) | `templates/agents/` plus a `d2r-project-conventions` skill | M |
| Issue and PR rules: `Closes #n` / `Part of #n`; sub-issues and blockers through the API by database id; PRs are not a triage surface; delete merged branches; `research/*`, `issue-assets` and `handoff/*` never merged or deleted | P | `d2r-project-conventions` | S |
| Wayfinder labels: a map issue, children typed research / prototype / grilling / task, claim the first free child | F | `d2r-project-conventions` (optional) | S |
| Triage: the five labels plus an `origin-bug` label and ledger | P, F, 9 | `templates/agents/triage-labels.md` | S |
| Gate rule: docs-only PRs skip CI unless they touch gate inputs; otherwise green checks on the final head plus MERGEABLE; runners offline means a local run with the report pasted; a parity drop needs the owner's label | P | `d2r-project-conventions`, `templates/workflows/` | S |
| Changelog fragments and "new pass or hook = new module with `ORDER`, never a shared list" | P | `d2r-release` skill, `templates/` | S |
| Roadmap: lettered work-item prefixes, one session per item, status kept on issues, a Blocked-by column | P | `templates/PLAN.md` | S |
| Decision records: an ADR template with Considered Options, Consequences and dated Amendments, **or** a single map issue with "owner's call #N" in the deviation rows. Document both; each project picks one. | P (ADRs), 9 (map issue), F (ADR) | `templates/ADR.md`, `docs/ai-workflow.md` | S |
| Ledgers: deviations (kept / cut / not yet / approximated, each with why, feeding `diff.gate`), origin bugs, D2R-only approvals | P, 9 | `templates/deviations.md`, `templates/origin-bugs.md`, `templates/d2r-only-content.md` | S |
| Research docs: one `research/<topic>` branch per ticket; header with question, ticket and date read; evidence labels; sources pinned by SHA or hash; short answer; options with cost and risk and "no choice made"; an unverified list with runtime checks | F, 9 | `templates/research.md` | S |
| Orchestrator: never implements, separate implementer and Opus reviewer, at most 5 agents, at most 2 fix cycles, workers never wait on CI, never touch runners, handoff on an orphan `handoff/*` branch | P (`.claude/skills/orchestrator`, `handoff/orchestrator-*`) | Merge into `d2r-coordinator`, `templates/coordinator-prompt.md`, new `templates/handoff.md` | M |
| Game-check recipe (lock, install, pin DS1, start, cheats, warp, shoot, upload, unlock, report) and screenshot rules (one shot settles it, a quiet spot, light radius, median luma over frames, before/after pairs, orphan `issue-assets` branch) | P | `docs/testing.md`, a `d2r-in-game-testing` skill | M |
| Testing rules: Hell, RotW characters, read `cheat-commands.md` first, console over clicks, 10 minutes without progress means unlock and file `ready-for-human`, JSON keys are case-sensitive, SDK service before a native hook, one lock held from install to cleanup, never `lock any`, savepath check after install, count skips | P, F | `d2r-in-game-testing` | S |
| Merge-slot pool: a machine-wide cap on heavy builds, slots reserved for CI, compare CPU time not wall time | P | `docs/testing.md` | S |
| Worktree hygiene: junction-safe removal, never `--delete-branch` / `worktree remove --force` with junctions, the SessionStart freshness hook | P | `d2r-project-conventions` | S |
| Commit and branch naming: conventional prefixes with issue numbers; `ticket/<n>-<slug>`, `research/<topic>`, `refactor/<topic>`; snapshot branches for preserved work | 9 | `d2r-project-conventions` | S |
| Toolkit pin bumped on purpose in a `chore: pin d2rAI-toolkit to <sha>` commit | 9 | `d2r-toolkit` skill (1.3) | S |
| Generated data is never hand-edited: generated by a script, checked by a test; game data outside the repo | 9, P (ADR 0002) | `d2r-project-conventions` | S |
| Periodic documentation audit: check claims and links against main | P `@research/documentation-audit` | `docs/ai-workflow.md` | S |
| Player README outline, GLOSSARY template | P | `templates/` | S |

## 6. Contradictions and drift to settle in the toolkit

Each becomes one toolkit issue, fixed with evidence while doing the matching move.

| # | Topic | Toolkit says | Project evidence |
|---|---|---|---|
| 1 | Who tests | CLAUDE.md rule 7, `d2r-debug`, `d2r-skill`: "the user tests in game" | `docs/testing.md` and all three projects: agents run checks in slots (F drift 1) |
| 2 | Skill tabs | `d2r-ui` skill: more than 3 tabs is engine work | `ui-layouts.md`: 8 TabWidgets confirmed; cite it and state where the limit is (F) |
| 3 | Numeric string ids | `porting-classic-mods.md`: never append numeric ids | `strings.md`: safe below 65,536 (F) |
| 4 | Install namespace | `install.py` writes no `namespace` key | Mods with namespaced strings add it by hand (F) |
| 5 | Loader vs SDK docs | no capability matrix; no ItemInteractionService notes | P `d2rloader-capabilities`, F `flask-runtime`, 9 `runtime-capabilities` |
| 6 | Hook byte coverage | `engine-re.md`: at least 14 bytes | the template's `sound_guard` uses 8-byte signatures; restate as whole instructions (F) |
| 7 | Extended-save marker | `saves.md`: `0x44520069` observed | SDK README: `0x44520006` (F `save-freeze`) |
| 8 | srvstfunc / cltstfunc size | "not confirmed" / "max 61" | 94 slots; cltstfunc 70 slots at `0x235f590` (P, 9) |
| 9 | Cube portal outputs | `engine-limits.md`: portal output only opens the Cow Level | `Red Portal,lvl=<id>` reaches any same-act level (P, F) |
| 10 | Memory pools | `engine-limits.md`: Renderer Pool is a fixed 12 MB | `entity_pool.cpp` grows six pools at runtime (P) |
| 11 | Item code length | `tables.md`: 4-character codes | items.json keys by 3 without a patch (P) |
| 12 | Which banks to write | `porting-classic-mods.md`: write both | P ADR 0001: RotW only, on purpose; 9: both, preserving Warlock placeholders. Present it as a decision with its consequences |
| 13 | Reviewer | the coordinator reviews and merges | P: a separate reviewer, a fix-cycle cap, docs-only PRs skip CI |
| 14 | No free slot | lane rules: poll up to about 30 minutes | P: stop and file `ready-for-agent`; workers never wait on CI |
| 15 | Screenshots | never commit them | P: an orphan `issue-assets` branch. Reconcile: never on `main` |
| 16 | Changelog | the coordinator writes version sections | P: fragments only |
| 17 | Test character level | — | P AGENTS.md says 90+; the owner's rule is 95 for every test character. Use 95. |
| 18 | 9's own map | — | `merge/column_map.py` recodes `BaseId` and AIParam the way `@research/monster-ai` shows is wrong (fix in 5.1) |

## 7. Toolkit hygiene (rule 11)

- `tools/ghidra_query.ps1` hard-codes `-Project PD2` / `pd2-project\PD2.gpr`: make the project list config-driven.
- Remove project names from `knowledge/cheat-commands.md` (Kurast map example), `knowledge/hd-graphics.md` ("PD2
  port"), `shared/classic_import/README.md` and `mpq.py`, and the release `product_id` example `"pd2r"`.
- Add the three project names to the private-terms list so `check_public` catches new mentions. No terms file exists on
  this PC yet, so only the generic checks run today.

## 8. Order of work

1. **Phase 0** (all S): 0.1 and 0.2 first, because they protect uncommitted work.
2. **Phase 1**: 1.1–1.4 in the toolkit, then 1.5 and 1.6. 1.7 waits for the pd2-resurrected alpha.
3. **Phase 2** lanes. Each lane has its own toolkit folder, so they can run in parallel:
   - A. `classic_import` layer (5.1 P rows), first and blocking for B and C.
   - B. maps and scoring (5.2), after A.
   - C. art and asset ports (5.3, plus the 5.1 rows for strings, sounds, animdata, skill icons and automap), after A.
   - D. 1.09d datasets and generators (5.1 rows from 9), independent.
   - E. testing (5.4), independent.
   - F. release, tools and CI templates (5.5, 5.6), independent.
   - G. C++ (5.7), independent; the `pd2_engine.h` promotion first.
   - H. knowledge (5.8) plus contradictions (6), split by source project.
   - I. methods, templates and skills (5.9), after 1.2.
4. **Consumer switches**: after each lane, one PR per project deletes its copies and uses the toolkit version.
   - resurrected-09 first.
   - Project Forever next; it mostly gains the new skills.
   - pd2-resurrected last, after alpha.

## 9. Deferred: using the toolkit without a local copy

Revisit when cloud sessions, GitHub-hosted CI, a second machine or a second contributor need the toolkit. The design
when that happens, kept small by phase 1:

- Make Python pip-installable from a git tag. `testing/` and `release/` become packages, console scripts are added,
  and the `install.py` to `testing` path coupling is removed.
- Data caches move to a user folder.
- `plugin-common` is consumed through CMake FetchContent.
- The Claude plugin comes from a GitHub marketplace source pinned to a tag.
- Reusable workflows are used through `workflow_call`.
- CascLib ships as a release asset.
- A read-only token covers CI.
- One `modkit toolkit bump` command updates every pin.

## 10. Owner decisions

1. Phase 0: commit the uncommitted agent docs in Project Forever and resurrected-09 as they are, or review them first?
2. Decision records: should each project keep its own style (ADRs in pd2-resurrected and Project Forever, the map
   issue in resurrected-09), or should the toolkit pick one?
3. Is `archetype-weaknesses` (Project Forever) worth a toolkit page, or does it stay with the mod?
4. Should the HD preset generator (5.2) move now, or wait for a second mod that adds maps? It is large, and only
   pd2-resurrected uses it today.
5. Confirm level 95 for the shared testing rules (contradiction 17).
