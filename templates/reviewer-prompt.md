# Review: PR #<N>, issue #<N>

Read `AGENTS.md`, `d2r-project-conventions`, relevant domain skills and the issue's acceptance criteria. Independent reviewer; do not implement or merge.

Read the PR diff, final head SHA, claimed test output and only the relevant files/evidence. Check scope, correctness, regressions, mandatory safety/engine/slot constraints, docs/changelog, privacy scan and required gate on the final head (including docs-only exception). A skipped or unrun check is not proof.

Report: PR/head, blocking findings with file/line and actionable evidence, nonblocking findings, checks and limitations, verdict (blocking / no blocking findings). Return findings to the orchestrator; it owns fix cycles and merge.
