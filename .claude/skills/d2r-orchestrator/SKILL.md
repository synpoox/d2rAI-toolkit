---
name: d2r-orchestrator
description: Orchestrate Diablo II Resurrected mod projects with implementer and reviewer lanes. Use to delegate multiple tasks, route models and game checks, review and squash merge, release, or hand off.
---

# Orchestrate a D2R mod project

Route work only; implementers change code/data and another agent reviews. Resume the newest handoff or read [setup](../../../docs/orchestrator-setup.md) for a new project.

1. Close duplicates before assigning. Use one issue, branch, worktree and PR per implementer, child tasks with unique request IDs, and at most five implementers at once. Read [the routing round](../../../docs/ai-workflow.md#how-the-orchestrator-runs-a-round) and [model tiers](../../../docs/ai-workflow.md#4-choosing-models-and-providers) before dispatch. Use issue evidence and short briefs.
2. Follow `d2r-in-game-testing` for game action. Read PR/issue links and one-line statuses only (no code, diffs or logs) in orchestrator context. Read [Handoff](../../../docs/ai-workflow.md#handoff) as context fills or a lane needs a restart.
3. Route each PR to an independent reviewer. At most two fix cycles. With no blockers and final-head gate evidence where required, squash merge per `d2r-project-conventions`. Clean up with junction-safe tools and protect kept branches. Use `d2r-release` after a merged batch.
4. Read [Safety](../../../docs/ai-workflow.md#7-safety-secrets-identity-public-things) before handling downloads or committing. Use [owner reporting](../../../docs/ai-workflow.md#8-talking-to-the-human-owner) for vital updates and obtain approval for public, paid or destructive work.
