# Orchestrator handoff, 2026-11-12 (night run)

The owner's decisions log is next to this file: `decisions-2026-11-12-pm.md`.

## State

- **Main:** `c775e4e`. The full suite ran 968 tests OK on main + #251. Main's only change since then is #251's
  docs-only fix commit. The showcase builds with 0 errors at `91d54d4`, and no `modkit/` change came after it.
- **Phase 2 lanes H and I:** done. All approved rows are merged, and the lane parents #148, #167, #181, #190 and #206
  are closed. Rows the owner did not approve were not done.
- **Phase 3 (the mods' switch issues): not started.** It waits for the owner's explicit permission. Nothing was
  written to the mod repos; they were read with `git show` only.
- **Open PRs:** none.

## Merged tonight

| PR | Lane | Rows | Merge |
|---|---|---|---|
| #236 | h-classic-109d | H9-1..5, H9-11..13 | 701a273 (2 cycles) |
| #237 | i-conventions | I1-5, I15, I16, I18, IK3 | 003efc9 (2 cycles; leftovers #249) |
| #238 | h-loader | HP1, H9-6, HP10, HP16, HP18, X5, HF1 | 781c60d |
| #240 | h-porting-p | HP3-6, HP9, HP13, HP14 (no origin-bug ledger), HP15, X3 | c9b51db (2 cycles) |
| #241 | h-addresses | HP2, HP7, HP8, HF6, X6, X8-X11 | a1d3a94 (2 cycles) |
| #244 | h-graphics-ops | HP11, HP12, X2, X4 | 5dcc10e |
| #245 | i-testing | I12, I13, HF7, HF8, HP17, X17, X1 | 42fa487 (2 cycles) |
| #247 | h-saves-maps | HF2-4, X7, H9-7, H9-10, H9-14, H9-15 | 0a7e55b (2 cycles) |
| #248 | main fix | skill link prefix (main broke after #236) | one line, no reviewer |
| #250 | i-templates | I6-10, HF10, I20, IK5, IK6 | 91d54d4 (2 cycles) |
| #251 | i-orchestrator | I11, IK1, IK2, IK4, IK7-10, I17, I19, X13, X14, X16 | c775e4e (2 cycles) |

## Open follow-ups (priority order)

1. **#249:** the `backup/` kept-branch prefix has no source. **The owner decides** whether to keep it, rename it or
   drop it. The issue also lists four small gaps in `templates/agents/AGENTS.md`.
2. **#252:** two files still hint at waiting for a game slot (X14).
3. **#243:** `shared/classic_import/items.py` still checks the old item-code 4th-byte idea (X11). This is code.
4. **#246:** `classic-109d-engine.md` sentence fix and nits.
5. **#242:** refresh `109d-skill-functions.tsv`.
6. **#239:** the collected review nits, one comment per PR. They are small, docs-only and can be batched.

## Next steps for the owner

- **Phase 3:** give permission before anyone files the mods' switch issues. The final file and heading names are in each
  merged PR's body.
- **#249:** the `backup/` name.
- **X4 (#244):** `mod.json` has a new optional `"namespace"` key, copied into `d2rloader/metadata.json`.
- **CLAUDE.md:** gained rule 7, "in-game checks are run by agents" (#245). The old rule 7 (ask before public, paid
  or destructive steps) is now rule 8.
- **Renames:** the `d2r-coordinator` skill is now `d2r-orchestrator`, and `templates/coordinator-prompt.md` is now
  `orchestrator-prompt.md`. `templates/bugs.md` and `templates/CHANGELOG.md` are deleted. Mods that link them need
  updating in Phase 3.

## Hazards

- **Shared index files.** Lanes that edit the same index files (`knowledge/README.md`, `docs/README.md`, the
  d2r-toolkit skill) made reviewed PRs go stale twice. Merge each PR as soon as its review clears, or have the index
  rows done in one final PR.
- **Skill links.** They must use `${CLAUDE_PLUGIN_ROOT}/`. Every reviewer brief should include
  `tests.test_plugin_manifest`; a bare path broke main once.
- **Full suite.** It takes about 4 minutes when idle and up to about 25 minutes with several agents running. Have
  agents redirect it to a log and read the `Ran N tests` line.
- **`tools/worktree_remove.ps1 -DeleteBranch`.** It did not recognise squash-merged branches, so delete those with
  `git branch -D`. The script also refuses worktrees that are still locked.
- **Busy branches.** A lane branch checked out in another worktree can't be checked out again. Fix workers used a
  local branch name and `git push origin HEAD:<branch>`.

## Leftover worktrees (`.claude/worktrees/`)

The process of this session still locks these worktrees. All their PRs are merged, so none holds unpushed work. Remove
them with `tools/worktree_remove.ps1` once that process has exited.

- `agent-a085bc2def39f8efe`
- `agent-a2172f3f4e28649d0`
- `agent-a34f00efc61b4689b`
- `agent-a3967aae7f20dac47`
- `agent-a39ffcc70a10a9bbd`
- `agent-a5dbe38b986dbe37d`
- `agent-a7b4df255c269c685`
- `agent-a8e1f6bb00611906c`
- `agent-ad7810eec7f0bec05`
- `agent-ae5d6ecc6f3c32b36`
- `agent-ae6c6fd3fb621126b`

`agent-a824b4a85fe094b67` (`lane/h-classic-109d`, merged) shows `knowledge/porting-classic-mods.md` as modified, but
the diff is empty (line endings only), so it is safe to remove.

Older `lane/a-*` and similar branches from earlier sessions were left untouched.
