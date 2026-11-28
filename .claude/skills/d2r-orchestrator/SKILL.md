---
name: d2r-orchestrator
description: Orchestrate Diablo II Resurrected mod projects with implementer and reviewer lanes. Use to delegate multiple tasks, route models and game checks, review and squash merge, release, or hand off.
---

# Orchestrate a D2R mod project

You route work. Implementers change the mod and separate reviewers verify it. Read the latest handoff first; for a new project use [setup](../../../docs/orchestrator-setup.md). Use relevant [workflow sections](../../../docs/ai-workflow.md).

1. Close duplicate issues before routing. Read [Routing work](reference.md#routing-work) and [Choosing models](reference.md#choosing-models) before dispatch. One issue, branch, worktree and PR per implementer. Use child tasks with unique request IDs and at most five concurrent implementers. Keep brief content task-specific.
2. Use `d2r-in-game-testing` for all slot work. Keep summaries and links in orchestrator context. Read [Context budget](reference.md#context-budget) for fresh lanes and orphan handoffs.
3. Apply [Review and merge](reference.md#review-and-merge) and `d2r-project-conventions`. Require an independent reviewer, at most two fix cycles, final-head gate evidence where applicable and squash merges. Clean up via [Clean up](reference.md#clean-up); protect junctions and kept branches.
4. Read [Identity and safety](reference.md#identity-and-safety) before handling downloaded files or committing. Use `d2r-release` after a merged batch and [owner reporting](reference.md#reporting-to-the-owner) for vital updates and consent.
