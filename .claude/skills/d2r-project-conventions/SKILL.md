---
name: d2r-project-conventions
description: Conventions for a D2R mod repo worked on by agents - issues and PRs (Closes/Part of, sub-issues, blockers), branch and commit names, merge gate rule, worktree and junction hygiene, generated data, optional wayfinder map. Read before opening an issue, branch or PR, merging, or removing a worktree in a mod repo.
---

# Project conventions

Per-repo values (repo, labels, protected branches, gate, game slots, junctions) are in `.d2r-project.toml` at the mod's root; the template is `${CLAUDE_PLUGIN_ROOT}/templates/d2r-project.example.toml`. Set a repo up from `${CLAUDE_PLUGIN_ROOT}/templates/agents/` (`AGENTS.md` pointer plus `docs/agents/{issue-tracker,triage-labels,domain}.md`). Command forms are in `docs/agents/issue-tracker.md`.

## Issues and PRs
- Verify the repo (`gh repo view --json nameWithOwner`) before creating anything. Use `--body-file`. To close: comment, then close.
- A PR body opens with `Closes #<n>` (finishes it) or `Part of #<n>`. No issue yet: open one first.
- Sub-issues and blockers go through the API by **database id** (not `#n`); a text line alone is no link.
- PRs are not a triage surface unless `[issues].prs_are_triage_surface` is true. Triage uses the five labels in `docs/agents/triage-labels.md`.
- After a PR merges, delete its branch on the remote and locally.

## Branches and commits
- `ticket/<n>-<slug>` for an issue, `research/<topic>` for findings, `refactor/<topic>`, `snapshot/<topic>` to preserve unfinished work.
- `research/*`, `issue-assets` and `handoff/*` (and snapshots) are never merged and never deleted: docs and issues link to them.
- Commit subject: conventional prefix plus issue number, e.g. `fix(items): stop affix overflow (#123)`; prefixes `feat fix docs refactor test chore`.

## Merge gate
- A docs-only PR skips the gate unless it touches `[gate].inputs`. Otherwise merge only with green checks on the **final head** and the PR `MERGEABLE`.
- Merged `main` into the branch? Rerun the gate; a report for an older head does not count.
- Runners offline: run `[gate].command` locally on the final head and paste the report (its first line names the commit) in the PR.
- A parity drop merges only with the owner's `[gate].drop_ok_label`. Agents never add it.
- Workflow templates: `${CLAUDE_PLUGIN_ROOT}/templates/workflows/`.

## Worktrees
- Worktrees share the cache through junctions (`[testing].junctions`). Before removing one, unlink each junction itself: `cmd /c rmdir <worktree>\<name>`. Then `git worktree remove`.
- Never `git worktree remove --force`, `rm -rf`, or `gh pr merge --delete-branch` while junctions exist: they follow the junction and empty the shared cache.

## Generated data
Files under `[testing].generated` are made by a script and checked by a test; never hand-edit them: change the script or its input and regenerate. Game data stays outside the repo (read from the install or the cache).

## Wayfinder (optional, `[issues].wayfinder`)
One map issue labelled `wayfinder:map` (notes, decisions so far, open questions). Children are sub-issues labelled `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` or `wayfinder:task`, with blockers as dependencies. Claim the first unassigned, unblocked child in map order (`gh issue edit <n> --add-assignee @me`). Resolve: comment the answer, close, add a pointer to the map's decisions. Research branches stay (see above).
