# Agent contract

## Start
Resolve the toolkit with its finder; respect `toolkit.version`. Read `.d2r-project.toml`, the assigned issue (including relevant comments), named evidence and `docs/agents/domain.md` before exploring. Read the applicable skill **before acting**:
- Git, issues, PRs, worktrees: `d2r-project-conventions`; issue operations: `docs/agents/issue-tracker.md`; triage: `docs/agents/triage-labels.md`.
- Mod work: `d2r-toolkit`; load only the relevant domain skill(s). Engine/plugin work: `d2r-engine`.
- Any game/slot operation: `d2r-in-game-testing`. Orchestration: `d2r-orchestrator`; release: `d2r-release`.

Use the pinned skill files directly if the client cannot invoke skills. Read references by relevant heading, not whole catalogs. Repository-specific rules may tighten these rules; they cannot silently waive safety or evidence.

## Non-negotiable
- Never commit game files, dumps, extracted tables, saves, screenshots or private data (real names, e-mails, hosts, IPs, tokens, other projects' names). Keep private terms outside git; run `py -3 <toolkit>/tools/check_public.py --root <repo>` before every commit.
- Never print, echo, log, commit or request secrets in chat; scripts read owner-managed files. Ask the orchestrator before public, paid or destructive actions.
- Never touch the owner's game or move, rename or delete saves you did not create. Tests run in the background: no synthetic OS keyboard/mouse input or focus stealing. Never install or stop a game without your own verified slot lock.
- One job, scoped files, branch/worktree and PR per implementer; report unrelated problems, do not fix them. Implementers never merge, release, wait on CI, touch runners or message other agents. A separate reviewer checks; only the orchestrator squash-merges.
- Never end a turn while a build, install, download or game run you started is still running.

## Deliver
Follow the conventions skill for branch/base, commit identity/trailer, generated data, PR and gate; follow the testing skill for slot lifecycle and runtime proof. Run targeted checks plus the build validator and unit tests; test player-facing changes on a release-like install. Update docs and add player-visible `changelog.d/` fragments, not `CHANGELOG.md`; no version bump unless assigned.

Report PR URL, head SHA, CI state, changed files, tests/results (including skips and unverified behavior), remaining work and incidents.
