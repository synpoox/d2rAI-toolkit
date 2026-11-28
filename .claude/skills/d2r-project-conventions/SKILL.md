---
name: d2r-project-conventions
description: Apply Diablo II Resurrected project conventions before issue, PR, branch, commit, merge, worktree or repository setup operations. Includes gate, generated data and optional Wayfinder rules.
---

# Project conventions

Use `.d2r-project.toml` for per-repo choices. Before acting read the applicable [lane workflow](../../../docs/ai-workflow.md#3-lanes-one-job-one-branch-one-pr) section; use [preflight and verify-lane](../../../docs/context-tooling.md#validate-a-lane) for manifest checks.

- **Issues/PRs:** verify repo identity first. Use body files, real issue/sub-issue and blocker links, and `Closes #N` or `Part of #N` as the opening line. Create an issue first when missing. Comment before closing. Use project issue tracker/triage docs and avoid PR triage unless enabled.
- **Branch/commit:** fetch the configured default base, use an isolated lane and configured prefixes (default `ticket/<n>-<slug>`). Keep protected branches. Pull LFS for pointer files. Use noreply, an issue-tagged conventional subject and model attribution trailer. Player-visible PRs add fragments; bump versions only when assigned.
- **Merge:** implementers never merge. A docs-only PR skips the gate except configured inputs. Otherwise require MERGEABLE and green checks for the final head; refresh after merging the base. If runners are offline, run the configured gate on a clean final head and paste its report. Only the owner may approve a parity drop.
- **Cleanup:** remove junctions with the toolkit's worktree remover, never plain recursive deletion. Keep configured branches; delete ordinary merged branches locally and remotely. Regenerate `[testing].generated` from its source. Consult [worktree cleanup and project options](../../../docs/ai-workflow.md#worktree-cleanup-and-project-options) for exact commands and optional Wayfinder.
