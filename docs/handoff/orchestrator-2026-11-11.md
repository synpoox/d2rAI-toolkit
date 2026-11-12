# Handoff: toolkit consolidation orchestrator, 2026-11-11

Branch `handoff/orchestrator-2026-11-11` of d2rAI-toolkit. Orphan, never merged. It names mod projects, which toolkit
rule 4 (public-clean) keeps off `main`.

Read first:
- How to run the consolidation: `docs/orchestrator-handoff.md` on branch `plan/consolidation`.
- The plan itself: `docs/consolidation-plan.md` on the same branch.
- Both are in the worktree `repos\d2rAI-toolkit-consolidation-plan`.

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
| pd2-resurrected#924 | Parent: every consolidation leftover for pd2-resurrected, blocked by #143 (alpha) | add one sub-issue per Phase 2 lane as each lands |
| pd2-resurrected#925 | Phase 1 wiring: finder, pin, drop the SDK submodule, CI checks out the pin, plugin | after alpha |
| pd2-resurrected#926 | Phase 1 doc links, including `core-rules-inventory.md`'s old `d2rAI-toolkit/pd2-data` path | after alpha |

Older open toolkit issues: #6 (companion installer) and #7 (release builder) belong to lane F. #9, #30 and #32
(game_slots and game_ctl) are unrelated.

## Next: Phase 2

The owner asked for confirmations of lanes **A and D to I** (the ones that can run in parallel). They were shown in
full on 2026-11-11, but **no lane is approved yet**. Re-show them (plan §5) and get a yes for each.

- My suggested first batch is A, D, E, F, G (5 workers); H and I follow.
- Lanes B and C come after A.

Pending owner decisions inside the lane confirmations:

- **Lane D:** the 1.09d converter has a monster-AI bug (`BaseId` treated as a row; AIParamN copied to aipN; see
  resurrected-09 `research/monster-ai`). The toolkit copy gets the fix. Ask whether resurrected-09 should also get the
  fix now, in its own PR, or only when it switches.
- **Lane E:** the slot-owner table for `~/.d2r-modkit/slots.toml`: Slot2 toolkit tests, Slot3 Project Forever,
  Slot4–7 pd2-resurrected. The Terror Zone and Herald checks leave town, so agents only unit-test them.
- **Lane F:** the stale-branch SessionStart hook would run in every session that loads the plugin; ask whether the
  owner wants it. CI templates can't be run, because Actions never runs on the toolkit repo.
- **Lane I:** the toolkit already has methods and templates from upstream. The owner wants a keep/throw decision first.
  My recommendation, shown to the owner and not yet answered:

  | Existing | Recommendation |
  |---|---|
  | `templates/coordinator-prompt.md` | keep, rewrite with the orchestrator method |
  | `templates/lane-prompt.md` | keep, merge in the brief rules |
  | `templates/lane-rules.txt` | throw (replaced by `templates/agents/`) |
  | `templates/bugs.md` | throw, or keep as an option without GitHub |
  | `templates/PLAN.md` | keep the file, replace its content with the roadmap shape |
  | `templates/CHANGELOG.md` | replace (lane F, fragments) |
  | `templates/owner-update.md` | keep, trim to "one line per vital update or blocker" |
  | `docs/ai-workflow.md` §1–12 | keep, update for contradictions 1, 13, 14, 16; drop §6 if `bugs.md` goes |
  | `d2r-coordinator` skill | keep, merge in the orchestrator method |
  | `d2r-release`, `docs/release.md`, `docs/testing.md` | keep |

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
- Worktrees owned by other sessions, left alone:
  - toolkit: `.claude/worktrees/schema3-packager-27cf10`, `d2rAI-toolkit-4b`, `-5`, `-plugin-common`,
    `-slot-install`, two under `~/.ao/data/worktrees/`, and two under `%TEMP%`.
  - resurrected-09: several `agent-*` and `ao` worktrees.
- `synpoox/goto-coords` (toolkit) has 2 pushed commits not on `main` (`cheat goto` coordinate docs). Untouched; ask
  the owner.
