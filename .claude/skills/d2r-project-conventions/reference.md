# Project conventions

Per-repo values (repo, labels, kept branches, gate, game slots, junctions) are in `.d2r-project.toml` at the mod's root; the template is `${CLAUDE_PLUGIN_ROOT}/templates/d2r-project.example.toml`. Set a repo up from `${CLAUDE_PLUGIN_ROOT}/templates/agents/` (`AGENTS.md` pointer plus `docs/agents/{issue-tracker,triage-labels,domain}.md`). Command forms are in `docs/agents/issue-tracker.md`.

## Issues and PRs
- Verify the repo (`gh repo view --json nameWithOwner`) before creating anything. Use `--body-file`. To close: comment, then close.
- A PR body opens with `Closes #<n>` (finishes it) or `Part of #<n>`. No issue yet: open one first.
- Link sub-issues and blockers for real (gh flags, or the REST API with the **database id**, not `#n`); a text line alone is no link.
- PRs are not a triage surface unless `[issues].prs_are_triage_surface` is true. Triage uses the five labels in `docs/agents/triage-labels.md`.
- After a PR merges, delete its branch on the remote and locally.

## Branches and commits
- Start from fresh `origin/main` (or configured default branch): `git fetch origin`, own branch/worktree, `git lfs pull` if assets are pointer text. One topic; open PR to the default branch, never merge as implementer.
- Use noreply commit identity; commit trailer `Co-Authored-By: <model> <noreply@anthropic.com>`. PR body: what changed, tests/evidence, what remains. Implementers do not bump versions unless assigned; player-visible changes add a `changelog.d/` fragment, never edit `CHANGELOG.md`.
- Prefixes come from `[branches]` (defaults): `ticket/<n>-<slug>` for an issue, `research/<topic>` for findings, `refactor/<topic>`, `backup/<topic>` to preserve unfinished work.
- Branches in `[branches].keep` (default `research/*`, `issue-assets`, `handoff/*`, `backup/*`) are never merged and never deleted: docs and issues link to them. `issue-assets` keeps old links only: never add a game screenshot to it or to any other branch.
- Commit subject: conventional prefix plus issue number, e.g. `fix(items): stop affix overflow (#123)`; prefixes `feat fix docs refactor test chore`.

## Merge gate
- A docs-only PR skips the gate unless it touches `[gate].inputs`. Otherwise merge only with green checks on the **final head** and the PR `MERGEABLE`.
- The CI report names GitHub's merge commit, not the PR head; a local report must come from a clean tree (untracked files count).
- Merged `main` into the branch? Rerun the gate; a report for an older head does not count.
- Runners offline: run `[gate].command` locally on the final head and paste the report (its first line names the commit) in the PR.
- A parity drop merges only with the owner's `[gate].drop_ok_label`. Agents never add it.
- Workflow templates: `${CLAUDE_PLUGIN_ROOT}/templates/workflows/`.

## Worktrees
- Worktrees share the cache through junctions (`[testing].junctions`). Remove a worktree only with `powershell -ExecutionPolicy Bypass -File ${CLAUDE_PLUGIN_ROOT}/tools/worktree_remove.ps1 -Path <worktree> [-DeleteBranch] -Cache <[testing].shared_cache>`: it unlinks every junction, checks the cache is unchanged and refuses a locked or dirty worktree. Only if the script cannot run: `cmd /c rmdir <worktree>\<name>` on each junction, then `git worktree remove`.
- Never plain `git worktree remove`, `--force`, `rm -rf`, or `gh pr merge --delete-branch` while junctions exist: they follow the junction and empty the shared cache.

## Generated data
Files under `[testing].generated` are made by a script and checked by a test; never hand-edit them: change the script or its input and regenerate. Game data stays outside the repo (read from the install or the cache).

## Wayfinder (optional, `[issues].wayfinder`)
One map issue labelled `wayfinder:map` (notes, decisions so far, open questions). Children are sub-issues labelled `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` or `wayfinder:task`, with blockers as dependencies. Claim the first unassigned, unblocked child in map order (`gh issue edit <n> --add-assignee @me`). Resolve: comment the answer, close, add a pointer to the map's decisions. Research branches stay (see above).
