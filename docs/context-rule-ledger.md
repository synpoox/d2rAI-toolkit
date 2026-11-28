# Context rule migration ledger (P0–P2)

Maintainer audit; **not** mandatory worker context. Baseline: `5d59cb6dbf6fabe34f17c8a14c73d6ddf45ba2bd`. Scope: standing instructions and prompt contract, not rewriting all technical skills. The 15 skill files were inspected for overlapping lock, hook, safety and routing instructions; topic-specific procedures/evidence remain in their original owners. Subsequent domain-skill compression is P3.

## Canonical ownership and mandatory read triggers

| Original sources / rule cluster | Canonical owner after change | When loaded |
|---|---|---|
| AGENTS Start; lane Git; conventions branches | AGENTS (scope) + d2r-project-conventions (fetch/default branch, branch prefix, isolated worktree, LFS, no merge) | Startup; before Git |
| AGENTS Safety; toolkit rules 1/10/12; orchestrator safety; workflow §7 | AGENTS (prohibited artifacts, privacy scan, secrets, consent, owner game/saves) + workflow §7 (untrusted downloads, private terms, public push) + toolkit CLAUDE.md for toolkit itself | Startup; before commit/approval/download |
| AGENTS Git; lane Git/Do; orchestrator standing rules | d2r-project-conventions (noreply, model trailer, PR body, changelog, version); AGENTS (role boundaries) | Before Git |
| Issue tracker, triage labels, domain docs | AGENTS routing + docs/agents/{issue-tracker,triage-labels,domain}.md | Before corresponding operations/exploration |
| AGENTS game slots; lane Game slot; orchestrator standing/slot; workflow §5; toolkit rule 7 | d2r-in-game-testing: named one-attempt lock, MODKIT_RUN, slot on every command, owner check before install/stop, abort on lock failure, savepath, restore/unlock/status, PID ownership, no polling, ready-for-agent fallback, character recipe, no synthetic OS input/focus | Before any slot action |
| AGENTS test/report; lane Done means; workflow §5 | AGENTS cheap/targeted checks, release-like tests, reporting; testing skill runtime evidence, skipped counts; task acceptance exact check/command/expected output | Startup; before testing/delivery |
| AGENTS no CI wait/no runners/no messaging/no unfinished processes | AGENTS; orchestrator routes and checks CI later | Startup |
| Lane Read/Scope/Findings/Do/Don't/Done; briefing notes | Issue + lane-prompt; workflow §9; explicit task-only constraints, verified vs suspected, ruled-out methods, named paths, no scope expansion, expected proof | Per task |
| Lane RE notes; toolkit rule 9; engine skill | d2r-engine: data/SDK first, byte and ABI verification, unique signatures for new hooks, reference image provenance, per-part disable, existing fixed RVA image guard, version major.minor, hook ownership, diagnostics, off-switches, ABI manifest; toolkit item-type rule retained | Before engine work |
| Orchestrator prompt §0–1 and §4–6 | Project config, compact prompt for project decisions, orchestrator-setup for first-time permission/download/inventory/scaffold/phase/lessons; workflow §§1/4/10 and testing skill | New project only or relevant task |
| Orchestrator prompt §2–3; skill routing/context | d2r-orchestrator + workflow §§2–4: strongest reviewer/orchestrator, tiered implementers, child tasks/request IDs, max five implementers, duplicate closure, no self-review, no implementation | Orchestration |
| Orchestrator prompt §7 and standing rules; workflow §3; conventions gate | d2r-orchestrator + conventions; reviewer-prompt for independent evidence and findings, two fix cycles, squash merge, final head green/MERGEABLE, docs exception, offline local fallback, protected branches and worktree cleanup | Review/merge |
| Orchestrator prompt §8; release skill; workflow §6 | d2r-release + workflow §6: fail-fast release, no piping through tail, no checkout switch, fragment-derived changelog, verify pages and close released issues | Release |
| Orchestrator prompt §9–10; handoff and owner-update templates | d2r-orchestrator + handoff/owner-update templates; orphan branch, newest first, never merge/delete, one-line vital updates, commands with expected output, owner approvals | Handoff/report |
| Project config and hardcoded defaults | .d2r-project.toml + toolkit.version; project-specific rules may tighten; no silent safety exceptions | Startup |

## Contradictions resolved

- **Slot waiting:** old workflow said `lock any` and testing skill offered `--wait`; AGENTS and orchestrator prohibited polling/waiting. Named slot, one attempt, `--wait 0`, then ready-for-agent issue. Confirmed CLI supports explicit timeout and ownership check.
- **Hook image guards:** old engine step and orchestrator phase said every hook uses one fixed image; lane and toolkit rules require new hooks by unique signature. Use the latter: existing fixed-RVA parts remain image-guarded; signature-only parts fail closed individually when any required signature is absent/non-unique. No blanket build guard for signature-only parts.
- **UI proof:** old UI skill asked for screenshots; agent-run testing is primary, with human handoff only under testing skill criteria.
- **Prompt completeness:** the old lane brief said both to avoid shared rules and to repeat Git/slot/report policy. Issue + mandatory agent contract/skill reads now supply shared policy. No acceptance evidence may be dropped.
- **Local overrides:** project game-check guidance may specialize configuration and proof, not silently waive safety or no-wait.

## Deferred work and validation

P3–P7 remain out of scope: comprehensive domain skill compression, indexed retrieval, automated enforcement, token budgets and task benchmark. Existing long workflow/reference material remains available; setup and this ledger are not routinely loaded. Source-size measurements are not runtime-token or cache measurements. Existing consumer copies of AGENTS.md must be migrated intentionally at their next pin update; do not silently overwrite project exceptions.
