# Handoff: orchestrator for the toolkit consolidation

Branch `plan/consolidation` of d2rAI-toolkit, worktree `repos\d2rAI-toolkit-consolidation-plan`. Never merged.
The full plan is `docs/consolidation-plan.md` in the same folder. This file tells you how to run it.

## The goal in one paragraph

Three mods (pd2-resurrected, Project Forever, resurrected-09) each built tools, engine facts and working methods.
Move the **generic** ones into the toolkit, so every mod uses one copy. "Generic" means it works for, or is true for,
any mod. Something tied to one game version is fine (classic 1.09d, classic 1.13c, D2R build 93847) when the version is
in its name. Anything about one mod (its content, rules, choices, plans, or research about that mod) stays in the mod.
The toolkit stays a local folder beside the mods; using it straight from GitHub is out of scope.

## Your one hard rule: confirm before each phase

Before you start any phase, show the owner a short confirmation and wait for a clear yes. Each Phase 2 lane (A to I)
counts as its own phase. A yes covers that phase only.

Write the confirmation in plain words, no plan jargon, in this shape:

> **Phase 2, lane A: the 1.13c table layer.** 6 moves, about 3 sessions, 1 PR per move.
>
> | Item | What it does | From | To (its toolkit name) | Why |
> |---|---|---|---|---|
> | Game-file cache | Extracts the game files once per game build and reuses them, so builds don't unpack the game every time | pd2-resurrected `tools/pd2_cache.py` | `shared/classic_import/cache.py` (`classic_import.cache`) | Every port extracts the same game files; one shared cache instead of one per mod |
> | Id rules | Gives new table rows ids that never shift existing ones, and rewrites references to renamed rows | pd2-resurrected `tools/pd2_ids.py` (the algorithm only) | merged into `shared/classic_import/ids.py` | The toolkit already has an older copy; the PD2 id lists stay in pd2-resurrected |
>
> **Stays behind:** the PD2 rules map and id lists (they are PD2 content).
> **What changes for the mods:** nothing yet; each mod switches later in its own PR.
> **Owner checks:** none / one game test in Slot N.
>
> Go ahead?

Rules for the table:

- One row per thing that moves. Group small files only when they move as one unit.
- "What it does" says in one plain sentence what the tool does, or what the page, header or template provides,
  without code names.
- "To" gives the path and the name people will use for it (Python module, CLI command, skill, header, or knowledge
  page title). Names never contain a mod name. Versioned items carry the version (`classic-113c-tables.md`).
- "Why" is one short sentence a non-programmer can follow.
- Always list what stays behind, and say if the owner has to do anything.
- If, while working, a move turns out to be partly mod-specific, stop, and show a new row before going on.

## Phases, in order

Section numbers point into `docs/consolidation-plan.md`.

| Phase | What | Plan |
|---|---|---|
| 0 | Toolkit cleanup: stray files out of the repo, mod names out of existing toolkit text | §3 rows 0.4–0.5, §7 |
| 1 | Wiring: one way to find the toolkit, a pinned toolkit version per mod, toolkit as a Claude plugin, shared SDK submodule | §4 |
| 2A | 1.13c table and id layer (blocks B and C) | §5.1 |
| 2B | Classic DS1 maps to HD presets, plus the edge tour | §5.2, §5.4 |
| 2C | Art, string, sound and icon ports | §5.3, part of §5.1 |
| 2D | 1.09d datasets and generators | §5.1 rows from resurrected-09 |
| 2E | In-game testing tools | §5.4 |
| 2F | Release tools and CI templates | §5.5, §5.6 |
| 2G | C++ engine addresses and mechanisms | §5.7 |
| 2H | Knowledge pages, and settling the contradictions | §5.8, §6 |
| 2I | Methods, templates and skills | §5.9 |
| 3 | Each mod switches to the toolkit copy and deletes its own | §8 step 4 |

Phase 3 order: resurrected-09, then Project Forever, then pd2-resurrected. **pd2-resurrected changes nothing until
its alpha ships (target about 2026-11-17)**, including phase 1 row 1.7. Lanes D to I may run in parallel; A comes
before B and C.

## Already done or decided (2026-11-11)

- Project Forever: research inventories pushed on branch `docs/research-inventories` (not on `main`); `AGENTS.md`
  and `docs/agents/` pushed to `main`; local `main` reset to `origin/main`. Its remote URL still uses the old name
  `synpoox/project-forever` (GitHub redirects).
- Decision records: the toolkit's baseline is ADRs (`docs/adr/NNNN-<slug>.md`).
- Test characters: level 99, experience 3520485254, 490 stat points, 98 skill points.
- Dropped: research about another community mod's map system.

## How to work

- **Toolkit rule 11.** No mod names, real names, e-mails or user paths in anything that lands on toolkit `main`. Run
  `py -3 tools/check_public.py` before every commit. Commit as the noreply identity `synpoox`.
- **Lanes.** One move per lane, own branch and worktree, one PR. Squash-merge; you review and merge. Init submodules
  in each new worktree; no shared `build/`; one DLL install at a time.
- **Tests move with code.** Replace fixtures that embed mod data with synthetic ones.
- **Copy first, switch later.** The toolkit gains the generic copy; the mod deletes its copy in a separate PR.
- **Contradictions** (§6) are fixed in the toolkit text with evidence, during the matching move.
- **Python** is `py -3`. Expect CRLF: check `.gitattributes` before using exact-match edits.
- **Game slots.** Name the slot every time. Slot2 tools test, Slot3 Project Forever, Slot4–7 pd2-resurrected.
  Windowed 1920x1080. Tests stay in the starting town, except pd2-resurrected slots.
- **Remotes.** The toolkit's `origin` is `synpoox/d2rAI-toolkit`. `upstream` (another account) is fetch-only: never
  open or act on its PRs.
- **Ask first** before anything public or destructive: force-push, deleting branches or saves, or changing a mod's
  `main` outside its phase.
- **Reporting.** After each phase: what moved (the same table, marked done), the PRs, and anything that stayed behind
  that was not in the confirmation.
