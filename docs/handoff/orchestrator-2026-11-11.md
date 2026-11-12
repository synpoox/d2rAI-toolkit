# Handoff: toolkit consolidation orchestrator, 2026-11-11

Branch `handoff/orchestrator-2026-11-11` of d2rAI-toolkit. Orphan, never merged. It names mod projects, which toolkit
rule 4 (public-clean) keeps off `main`.

Read first:
- How to run the consolidation: `docs/orchestrator-handoff.md` on branch `plan/consolidation`.
- The plan itself: `docs/consolidation-plan.md` on the same branch.
- Both are in the worktree `repos\d2rAI-toolkit-consolidation-plan`.
- **Phase 2 approvals, item by item:** the live doc <https://claude.ai/artifact/5DCNKj7JZuuSYnWo3i45QT> (snapshot: `docs/handoff/phase2-approvals.md` on this branch). See "Phase 2" below.

The hard rule still holds: **confirm each phase (each Phase 2 lane) with the owner in the plain what/from/to/why
table, and wait for a clear yes.**

## Where things are

| Repo | `main` |
|---|---|
| d2rAI-toolkit | `8419adc` |
| resurrected-09 | `01573ff` |
| resurrected-forever (Project Forever) | `3892330` |
| pd2-resurrected | `97489f6` (frozen for consolidation until its alpha, ~2026-11-17) |

## Done this session

**Phase 0: toolkit cleanup. Done.**
- d2rAI-toolkit#35: added the Ghidra scripts `FuncsInRange` and `RangeAsm`.
- d2rAI-toolkit#36: mod names out of toolkit text; `ghidra_query.ps1` reads its projects from
  `~/.d2r-modkit/ghidra_projects.json`, which is local and holds the PD2 and 109d projects.
- The extracted PD2 data moved out of the toolkit to `repos\pd2-data\`. Stray tar files and logs deleted.
- The private terms list is `~/.d2r-modkit/private_terms.txt`: the three mod names.

**Phase 1: wiring. Done, except pd2-resurrected.**
- d2rAI-toolkit#41: `CLAUDE.md` split into maintainer rules plus the `d2r-toolkit` skill.
- d2rAI-toolkit#42: the toolkit is a local Claude plugin `d2r-toolkit@d2r-local`. Setup is in
  `docs/ai-workflow.md` §13.
- d2rAI-toolkit#43: the toolkit finder (`tools/toolkit_path.py`, `tools/ToolkitPath.ps1`,
  `cmake/FindD2rToolkit.cmake`) plus the `toolkit.version` pin.
- Row 1.4 (shared SDK) was already true on the toolkit side. Only pd2-resurrected has its own SDK submodule.
- resurrected-09#88: pin plus finder, including its own `toolkit_boot.py` (see d2rAI-toolkit#44).
- resurrected-forever#58: pin plus finder in the slot-install check usage, and `.gitattributes`.
- Row 1.8 doc links: neither mod's `main` had local links. They were rewritten as pinned GitHub links on the unmerged
  branches Project Forever `docs/research-inventories` (`91916b9`) and resurrected-09
  `research/109d-vs-113c-columns` (`8b83672`). Both stay unmerged.

## Open issues from this session

| Issue | What | Next step |
|---|---|---|
| d2rAI-toolkit#37 | `ghidra_query.ps1` fails when a script gets no args | ready-for-agent |
| d2rAI-toolkit#44 | Ship a standard Python bootstrap for mods (replaces resurrected-09's `toolkit_boot.py`) | ready-for-agent; do before resurrected-09's Phase 3 switches |
| resurrected-forever#59 | `docs/agents/issue-tracker.md` names the old slug `project-forever` | ready-for-agent |
| pd2-resurrected#924 | Parent: every consolidation leftover for pd2-resurrected, blocked by #143 (alpha) | sub-issues for lanes A, E, F, G added (#931–934); add more as later lanes are approved |
| pd2-resurrected#925 | Phase 1 wiring: finder, pin, drop the SDK submodule, CI checks out the pin, plugin | after alpha |
| pd2-resurrected#926 | Phase 1 doc links, including `core-rules-inventory.md`'s old `d2rAI-toolkit/pd2-data` path | after alpha |

Older open toolkit issues: #6 (companion installer) and #7 (release builder) belong to lane F. #9, #30 and #32
(game_slots and game_ctl) are unrelated.

## Phase 2: approvals and issues (done 2026-11-11, later the same day)

**The approvals doc.** Live: <https://claude.ai/artifact/5DCNKj7JZuuSYnWo3i45QT>, titled "Consolidation Phase 2: lane items and approvals". It is a Claude Doc in the owner's claude.ai account, so it lasts beyond any session. It has one table per lane (A to I), every item, and an Approval dropdown per item (Approved / Waiting / Question / Rejected). A snapshot is on this branch: `docs/handoff/phase2-approvals.md`. **The live doc wins.** Refresh the snapshot at each handoff: export the tab as markdown and replace the byline name with "owner".

**Nothing has started.** The owner said not to start yet. Next step: ask for a go, then start workers on lanes A, D, E, F and G (5 workers at most), each from its toolkit issue below.

| Lane | Decision (2026-11-11) |
|---|---|
| A | Approved |
| B, C | Waiting; they come after A |
| D | Approved except **D8, on hold** (see below) |
| E | Approved. E13 slot table: Slot2 toolkit tests, Slot3 Project Forever, **Slot4–8 pd2-resurrected, Slot9–10 resurrected-09** |
| F | Approved, including F6 (the SessionStart stale-branch hook) |
| G | Approved except G2, G4 and G5. G1 and G10–G12 follow the **two-homes rule**: every address goes into `rvas_93847.h` *and* `knowledge/d2r-93847-addresses.md`, and a unit test fails when a header RVA has no knowledge row. G10 and G12 go to `knowledge/` only (no toolkit code uses them yet); G11 goes to both. |
| H, I | Waiting. Lane I's keep/throw table is still unanswered |

**D8 history.** The owner first said "fix now". resurrected-09 #93 was raised: `BaseId` is not a row, and the AI parameters need a per-AI slot map, of which only 5 are verified. Then the owner said "stop the D8 fix". #93 is open with no `ready-for-agent` label and a hold comment. It still blocks resurrected-09 #90, the lane D switch. When D8 is decided, either relabel #93 or close it and remove that blocker. Toolkit #47's D3 row matches #93's policy: a slot map where one is verified on both builds; otherwise the plain copy, listed as unverified.

**Issues raised.** Every one is labelled `ready-for-agent` (except #93) and blocked natively. A mod switch issue starts only once its toolkit lane issue closes; pd2-resurrected's issues also wait for the alpha (#143), and F and G there also wait for #925. Each switch issue carries a row-by-row delete / use-instead / keep table and the same agent steps: check blockers, follow the toolkit PR's final names, bump the pin, compare old and new output, delete, grep.

| Lane | Toolkit work | pd2-resurrected (public; parent #924) | resurrected-09 (parent #89) | Project Forever |
|---|---|---|---|---|
| A | d2rAI-toolkit#46 | #931 | — | — |
| D | d2rAI-toolkit#47 | — | #90 (blocked by #93 too) | — |
| E | d2rAI-toolkit#48 | #932 | #91 | #60 |
| F | d2rAI-toolkit#49 (parent of #6, #7) | #933 | — | — |
| G | d2rAI-toolkit#50 | #934 | #92 | — |
| D8 fix | — | — | #93 (on hold) | — |

Found while checking the mods: pd2-resurrected's `AGENTS.md` says "Slot4-8 here" and resurrected-09's README says "Slot9 and Slot10". Both match the amended table; #932 and #91 only swap that text for a pointer to the slot registry. Per that README, its machine config already gives it Slot9 and Slot10 (not checked).

**Still open for the owner:** D8; lanes B, C, H and I (and I's keep/throw table); G2, G4 and G5.

## Owner to-dos

- **Plugin settings.** Add the toolkit plugin to `~/.claude/settings.json`; the owner said they'll do it. Until then,
  the mods' `.claude/settings.json` entries have no effect. Either form works:
  - `claude plugin marketplace add C:/Users/<you>/source/repos/d2rAI-toolkit`, then
    `claude plugin install d2r-toolkit@d2r-local`.
  - Or the JSON in `docs/ai-workflow.md` §13.
- **Plan branch.** `plan/consolidation` has 2 local commits that aren't pushed (`ff5290c`, `48cd8a4`: handoff-doc
  tweaks). Ask before pushing.

## Hazards

- **No CI on the toolkit.** GitHub Actions has never run on the toolkit repo (`gh run list` is empty). Rely on local
  checks: `py -3 -m unittest discover tests` and `py -3 tools/check_public.py --no-history`.
- **Old commit messages.** 13 old commit messages on toolkit `main` name a mod. A full `check_public` run (with
  history) fails on them. Rewriting needs a force-push: owner's call. Use `--no-history`.
- **Force-pushes.** Tell workers to merge `main` in, never force-push. One worker force-pushed (with lease) its own PR
  branch in Phase 0 without asking.
- **Another session on resurrected-09.** It is pushing to resurrected-09 research branches: `1a2a5ce` on
  `research/109d-vs-113c-columns` added 16 scratch scripts with real user paths. Lane D drops those scripts; don't
  copy them.
- **`CLAUDE_PLUGIN_ROOT`.** It is substituted only when a skill loads from the plugin. Inside the toolkit repo the
  placeholder stays literal; each skill's "Toolkit root" line says so. `check_public` must get
  `--root <mod repo>` when run from a mod.
- **Mod line endings.** The mods have no `.gitattributes` (Project Forever now has one for `toolkit.version`) and
  autocrlf is on. Expect CRLF.
- **Agent worktrees.** The `isolation: worktree` option only works when the session's cwd is the toolkit repo. For mod
  repos, workers create their own worktree under `<mod>\.claude\worktrees\` and remove it themselves.
- **pd2-resurrected sources keep moving.** Lane A copies from pd2-resurrected's current `main`. Before its Phase 3
  switch, diff the source again for changes made after the copy.

## Leftover worktrees

- None of this session's worktrees are left; all were removed.
- The Phase 2 approvals part ran from the toolkit worktree `.claude/worktrees/schema3-packager-27cf10` (branch
  `claude/orchestrator-handoff-docs-a89b72`, no commits). It made only issues, the doc and this branch's commit.
- Worktrees owned by other sessions, left alone:
  - toolkit: `.claude/worktrees/schema3-packager-27cf10`, `d2rAI-toolkit-4b`, `-5`, `-plugin-common`,
    `-slot-install`, two under `~/.ao/data/worktrees/`, and two under `%TEMP%`.
  - resurrected-09: several `agent-*` and `ao` worktrees.
- `synpoox/goto-coords` (toolkit) has 2 pushed commits not on `main` (`cheat goto` coordinate docs). Untouched; ask
  the owner.
