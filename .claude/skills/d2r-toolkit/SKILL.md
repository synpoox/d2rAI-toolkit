---
name: d2r-toolkit
description: What the d2rAI-toolkit offers a Diablo II Resurrected mod project and where to find it - modkit, knowledge files, testing, release, templates, plugin-template, the craft skills - plus the craft rules a mod follows and how a mod finds and pins the toolkit. Use when a session in a mod project needs toolkit tools, engine knowledge or the toolkit version pin, or before starting any mod work. New generic work (tools, engine facts, templates that hold for any mod) starts in the toolkit, not in the mod.
---

# Using the D2R toolkit from a mod

The toolkit builds Diablo II: Resurrected mods, up to full overhauls, from D2R's own files and engine. You make the
mod with it: the user says what they want, you do it. Target: D2R 3.3 (engine addresses for build 93847 only),
D2RLoader 1.3.1 (PluginSDK 0.4.0). Windows.

Toolkit root: `${CLAUDE_PLUGIN_ROOT}` (if you see the placeholder itself, you are inside the toolkit repo: use its root). Run `python -m modkit` with that folder as the working directory and the mod project as an argument.

## Finding the toolkit and the pin
- Use the toolkit finder; do not hard-code a path:
  - Python: `${CLAUDE_PLUGIN_ROOT}/tools/toolkit_path.py`
  - PowerShell: `${CLAUDE_PLUGIN_ROOT}/tools/ToolkitPath.ps1`
  - CMake: `${CLAUDE_PLUGIN_ROOT}/cmake/FindD2rToolkit.cmake`
- It uses the env var `D2R_TOOLKIT`, else walks up from the mod to a `d2rAI-toolkit` sibling folder.
- The mod's `toolkit.version` file holds the toolkit commit the mod expects (the pin). On a mismatch the finder
  warns: tell the user, and do not move the pin without them. Updating the pin means rebuilding and re-testing.
- **Bump the pin on purpose**, never as a side effect: one commit, `chore: pin d2rAI-toolkit to <sha>`, that changes
  only `toolkit.version`, after the build and the targeted checks pass against that toolkit commit. Say in the PR what
  the new toolkit commits change for the mod.

## Where things are
- `${CLAUDE_PLUGIN_ROOT}/modkit/`: the Python toolkit (`python -m modkit -h`). A mod is a project folder of JSON
  patches applied to the pristine game files; `${CLAUDE_PLUGIN_ROOT}/knowledge/modkit-ops.md` lists every op.
- `${CLAUDE_PLUGIN_ROOT}/knowledge/`: what D2R hard-codes and how its files work (limits, tables, strings, layouts,
  saves, HD graphics, reverse engineering, debugging). Read `${CLAUDE_PLUGIN_ROOT}/knowledge/engine-limits.md` before designing anything
  big, and the topic file before working in an area. A whole new game system (for example a mapping system) starts
  with `${CLAUDE_PLUGIN_ROOT}/knowledge/new-game-systems.md`: the data vs plugin split, the hooks, where state lives, the lanes.
  What D2RLoader 1.3.1 and PluginSDK 0.4.0 can and cannot do is in `${CLAUDE_PLUGIN_ROOT}/knowledge/d2rloader-capabilities.md`
  (the capability matrix; check it before planning a plugin feature); charged or not-used-up items are in
  `${CLAUDE_PLUGIN_ROOT}/knowledge/charged-items.md`.
- `${CLAUDE_PLUGIN_ROOT}/docs/`: how to run a project. `${CLAUDE_PLUGIN_ROOT}/docs/ai-workflow.md` is the method for a mod built with AI
  agents: an orchestrator plus parallel lanes and reviewers, model choice, game slots, releases, safety, handoff.
- `${CLAUDE_PLUGIN_ROOT}/templates/`: fill-in files for a new project: orchestrator prompt, handoff, lane rules, lane prompt,
  `PLAN.md`, `CHANGELOG.md`, owner update.
- `${CLAUDE_PLUGIN_ROOT}/testing/`: how to test a mod in the real game without a human: game slots (frozen copies of
  the install, queued with locks), named game checks driven through a plugin test harness, release-like installs.
- `${CLAUDE_PLUGIN_ROOT}/release/`: packaging and publishing: the release package, a manifest, a fail-fast release
  script, release pages. `${CLAUDE_PLUGIN_ROOT}/docs/distribution.md` compares your own host, GitHub Releases and Nexus Mods
  (`package_release.py --nexus` writes a Nexus-ready archive).
- `${CLAUDE_PLUGIN_ROOT}/downloader/`: the player-facing installer/updater source (installs the mod into the
  player's D2R `mods` folder, checks the game and loader versions, updates itself).
- `${CLAUDE_PLUGIN_ROOT}/plugin-template/`: a D2RLoader plugin skeleton, for behaviour that data can't express.
- `${CLAUDE_PLUGIN_ROOT}/tools/`: CascLib build, image dump, the Ghidra scripts for reverse engineering, and
  `${CLAUDE_PLUGIN_ROOT}/tools/check_public.py`, the privacy scan (`--root` is the repo to scan).
- `${CLAUDE_PLUGIN_ROOT}/examples/showcase/`: a small working mod project (a reworked class skill with a new icon and
  HD animation, an item skill with a new missile, a bigger stash).
- `${CLAUDE_PLUGIN_ROOT}/.claude/skills/`: how to do each kind of job. Use them. Craft skills:
  - `d2r-mod-setup`: setup, build, install, run.
  - `d2r-skill`: skills.
  - `d2r-items`: items, affixes and drops.
  - `d2r-monsters`: monsters and areas.
  - `d2r-ui`: layouts, panels and grids.
  - `d2r-cube`: recipes.
  - `d2r-engine`: plugins, reverse engineering and new game systems (with ${CLAUDE_PLUGIN_ROOT}/knowledge/new-game-systems.md).
  - `d2r-in-game-testing`: run a check in the real game yourself, in a slot (recipe, screenshots, test rules).
  - `d2r-debug`: crashes and wrong behaviour.
  - `d2r-crash`: a player's crash report (with ${CLAUDE_PLUGIN_ROOT}/knowledge/crash-triage.md).
  - `d2r-port`: porting a classic mod (with ${CLAUDE_PLUGIN_ROOT}/knowledge/porting-classic-mods.md; from 1.09d also the ${CLAUDE_PLUGIN_ROOT}/knowledge/classic-109d-*.md and ${CLAUDE_PLUGIN_ROOT}/knowledge/classic-reference-installs.md files).

  Project skills:
  - `d2r-orchestrator`: route a project over several agents (lanes, models, slots, separate review, squash merges, handoff).
  - `d2r-project-conventions`: issues, PRs, branches, merge gate, worktrees (with `${CLAUDE_PLUGIN_ROOT}/templates/agents/` and `.d2r-project.toml`).
  - `d2r-release`: ship a version (bump, changelog, fail-fast publish, release pages, mirrors such as Nexus Mods).

## New generic work starts in the toolkit
If the work is not specific to this mod (a new tool, an engine fact, a template, a plugin helper that any mod could
use), do it in the toolkit, not in the mod: make a branch there, follow its `CLAUDE.md`, and have the mod pick it up
through the pin. Keep mod-specific content in the mod. When you learn something new about the engine (a limit, an
address, a fix), add it to `${CLAUDE_PLUGIN_ROOT}/knowledge/` in the toolkit and mark build-specific values with the build number.

## Rules for a mod
1. **Never commit game files.** `d2r-data/` (the cache of extracted game files), mod projects' `out/` folders and
   anything copied from the game stay out of git. Blizzard's files are only read from the user's install.
2. **Data before code.** Most of a mod is table rows, strings, layouts and sprites. Reach for a plugin only when no
   vanilla function or column can do it, and say so when it's needed.
3. **Start from vanilla.** New content clones the closest vanilla row (`modkit show`, `modkit functions`) and
   changes it. Don't invent column values or function numbers.
4. **Build and validate every change** (`python -m modkit build <project>`). Fix all errors; read the warnings.
   0 errors on a pristine build is the baseline.
5. **Respect the limits** in ${CLAUDE_PLUGIN_ROOT}/knowledge/engine-limits.md. The ones people hit:
   - 30 skills per class (saves);
   - string IDs below 65536 (modkit allocates them);
   - indexed tables are append-only;
   - formula syntax;
   - sequence skills need SQ plus an HD state;
   - new missiles need an HD model, new items need an HD picture entry.
6. **Install only with the game closed**; restart the game after every install (in a slot, `python ${CLAUDE_PLUGIN_ROOT}/testing/game_ctl.py --slot <N> start`).
7. **You run the in-game checks, in a game slot; you diagnose from files.** The `d2r-in-game-testing` skill has the
   recipe and the rules. Ask the human only when a check needs one. Keep a TESTING.md in the mod project with a row per
   installed change (what, how, expected) and keep working. Every test character is level 99 (experience 3520485254,
   490 stat points, 98 skill points), made with the Reign of the Warlock game version; don't stop to ask for each test. On "it crashed", read
   the logs (d2r-debug skill) before asking anything. A player's crash report goes through the d2r-crash skill and
   ${CLAUDE_PLUGIN_ROOT}/knowledge/crash-triage.md. Porting a classic mod goes through the d2r-port skill and
   ${CLAUDE_PLUGIN_ROOT}/knowledge/porting-classic-mods.md, and only with the mod creators' permission: confirm it with the user first.
8. **Saves**: back up first; edit only with `modkit save-set`; never hand-write items.
9. **Plugins are tied to one game image.** Engine addresses belong to build 93847 only (image timestamp
   `0x6ab3782c`); the plugin checks the timestamp and installs nothing on a mismatch. Re-find addresses after any
   game or D2RLoader update. Look for an existing D2RLoader hook on a function before you patch it. Version checks
   in installers and requirements use the game's major.minor (`3.3`), never a build number: Steam and Battle.net
   ship the same program under different builds.
   **Item types:** keep D2R-only itemtypes rows at D2R's numbers, and run
   `py -3 ${CLAUDE_PLUGIN_ROOT}/plugin-template/tools/item_type_ids.py <project>/out/data/global/excel/itemtypes.txt`
   after every itemtypes change (${CLAUDE_PLUGIN_ROOT}/knowledge/porting-classic-mods.md).
10. **Keep the repo public-clean.** No real names, e-mails, hosts, IPs or tokens; no other projects' names. Keep
    a private-words list outside the repo (`~/.d2r-modkit/private_terms.txt`, one word per line) and run
    `py -3 ${CLAUDE_PLUGIN_ROOT}/tools/check_public.py --root <mod repo>` before every commit. Commit with a
    noreply identity.
11. **Working with agents:** one bug or feature per lane (own branch, own worktree, PR); lanes never merge; a
    separate reviewer checks each PR (at most 2 fix cycles), the orchestrator squash-merges and releases and never
    implements; duplicate issues are closed before fixing. Details:
    `${CLAUDE_PLUGIN_ROOT}/docs/ai-workflow.md`.
12. **Ask the human before** anything public, paid or destructive (publishing, making a repo public, force-push,
    deleting saves or branches, spending money, touching their real game install). Never ask for secrets in chat.
