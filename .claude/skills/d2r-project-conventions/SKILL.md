---
name: d2r-project-conventions
description: Apply Diablo II Resurrected project conventions before issue, PR, branch, commit, merge, worktree or repository setup operations. Includes gate, generated data and optional Wayfinder rules.
---

# Project conventions

Use `.d2r-project.toml` for project values, and [preflight and verify-lane](../../../docs/context-tooling.md#validate-a-lane) for deterministic checks.

- Before issue or PR operations, read [Issues and PRs](reference.md#issues-and-prs). Verify the repo, create real issue relationships and start the PR body with its issue linkage.
- Before branching or committing, read [Branches and commits](reference.md#branches-and-commits). Use current configured base, one isolated lane, noreply identity and issue-tagged conventional commits. Follow the protected branch rules. Player-visible changes use fragments.
- Before merging, read [Merge gate](reference.md#merge-gate). Implementers never merge. Check final-head status and parity requirements per config.
- Before removing a worktree, read [Worktrees](reference.md#worktrees). Use the junction-safe remover. Regenerate files in `[testing].generated` from their source.
- For repository setup or Wayfinder, use [the project scaffold](../../../templates/agents/) or [Wayfinder](reference.md#wayfinder-optional-issueswayfinder).
