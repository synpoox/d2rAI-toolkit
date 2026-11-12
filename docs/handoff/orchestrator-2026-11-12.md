# Handoff: toolkit consolidation orchestrator, 2026-11-12

Branch `handoff/orchestrator-2026-11-12` of d2rAI-toolkit. Orphan line, never merged. It builds on
`handoff/orchestrator-2026-11-11`, whose two docs are still here and still apply: `orchestrator-2026-11-11.md` (phases
0 and 1, how to run the consolidation) and `phase2-approvals.md` (the item-by-item Phase 2 approvals).

The hard rule still holds: **confirm each phase or lane with the owner in the plain what/from/to/why table, and wait
for a clear yes.**

## Where things are

| Repo | `main` |
|---|---|
| d2rAI-toolkit | `e62e5a8` (was `8419adc`) |
| the three mod repos | unchanged this session: read-only during Phase 2 |

## Done this session: Phase 2 copy lanes

The approved lanes are merged into toolkit `main`: 40 PRs, #51–#87, #114, #145 and #146. Each lane item has its own
sub-issue under its lane parent; every PR body has `Closes #N`.

| Lane | Parent | Sub-issues | State |
|---|---|---|---|
| A: classic table and id layer (`shared/classic_import`) | #46 | A1–A12, #88–#99 | all done, parent closed |
| D: 1.09d datasets, generator, converter | #47 | D1–D7, #100–#106 | all done, parent closed. D8 stays on hold and has no row |
| E: shared testing helpers, slot registry | #48 | E1–E14, #107–#121 | all done, parent closed |
| F: release stager, companions, install and worktree tools, CI templates | #49 | F1–F11, #122–#132, plus #6, #7 | all done, parent closed |
| G: addresses, AI registry, palette, skill router, parts | #50 | G1–G12, #133–#144 | G1, G3, G6–G12 done. **G2 (#134), G4 (#136), G5 (#137) on hold, not approved.** #50 stays open for them |

Owner decisions made in this session:
- A5: the shared cache is the env var `MODKIT_SHARED_CACHE`. It is opt-in, with no default folder.
- Mod repos stay read-only until each mod's own switch issue. No tool is deleted from a mod repo in Phase 2.

Check of `main` at `e62e5a8`, after all merges:
- Full suite: 958 tests OK (8 skipped).
- `modkit build examples/showcase`: 0 errors.
- plugin-common: ctest 4/4.
- plugin-template: `build.ps1 -Tests` passes.
- `claude plugin validate .`: passes, with warnings: no `version` in plugin.json or marketplace.json, no icon.
- `check_public`: OK.

## Open after this session

| Item | What | Next step |
|---|---|---|
| #147 | 43 non-blocking review nits still true on `main`, grouped by area | ready-for-agent; small PRs per area |
| #50 G2, G4, G5 | pool growth, automap extension, item pictures | owner approval needed |
| D8 | on hold (see `phase2-approvals.md`) | owner approval needed |
| Plugin validate warnings | add `version` to plugin.json and marketplace.json; add an icon | small; could join #147 |
| Phase 3 | each mod switches to the toolkit copies and deletes its own copies, in its own switch issue | confirm per mod with the owner. The frozen mod waits for its alpha (see `orchestrator-2026-11-11.md`) |
| #9, #30, #32, #37, #44, #45 | older toolkit issues, unrelated to Phase 2 | as before |

## Lessons for the next orchestrator

- **Never serialize reviewers on a shared full-suite lock.** One lock folder made about a dozen reviewers wait 30+
  minutes. Reviewers and fixers run targeted tests only. Run the full suite once on `main` after a merge batch.
- **Merge directly when GitHub says `clean`.** Check `gh api .../pulls/N --jq .mergeable_state`, which reads
  `unknown` for a few seconds after each merge, so poll. Only `dirty` PRs need a syncer. A serial merge train that runs
  the full suite per PR costs about 5–8 minutes per PR.
- **Table-row conflicts are the main recurring conflict.** Every lane adds a row to the same README or knowledge
  table. A syncer must fetch and merge `main` again right before each push. Where PRs share a file, expect the second
  one to need one more sync.
- **Stacked PRs:**
  - Retarget each child to `main` (`gh api -X PATCH .../pulls/N -f base=main`) before merging the parent.
  - Merge the parent without `--delete-branch`.
  - After the parent's squash, every child conflicts on the parent's files. Sync them one at a time, taking `main`'s
    version of the parent's content.
- **`gh pr comment` and `gh pr edit` often fail** with "Could not resolve to a PullRequest". Use `gh api
  repos/<repo>/issues/N/comments -F body=@file` and `gh api -X PATCH .../pulls/N -F body=@file`.
- **Dispatch a reviewer the moment a PR appears.** Keep a list of PR numbers and their state. One PR (#75) was missed
  until the owner asked.
- **CI runs on Linux.** Tests must be platform-neutral: use `casefold`, never `os.path.normcase`, for case-insensitive
  compares. CI does not run on PR branches here, so the reviewer's tests and the final check of `main` are the gate.
- **Two homes for every RVA:**
  - Every RVA goes in `shared/plugin-common/src/rvas_93847/<area>.h`, and the umbrella `rvas_93847.h` declares none.
  - Every RVA also gets a first-cell row in `knowledge/d2r-93847-addresses.md`, marked build 93847.
