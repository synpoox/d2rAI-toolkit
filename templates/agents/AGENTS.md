## Agent skills

Per-repo values (repo name, labels, game slots, gate) are in `.d2r-project.toml`. The rules for issues, PRs,
branches, the gate and worktrees are in the `d2r-project-conventions` skill; read it before your first issue, branch or PR.

### Issue tracker

Work is tracked in GitHub Issues (`gh`). Before reading or publishing tickets, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage labels. Before triaging or changing labels, read `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. Before exploring the codebase, read `docs/agents/domain.md`.

## Working rules

Start
- Start from `origin/main` (`git fetch origin`, then a new branch named as in the `d2r-project-conventions` skill);
  `git lfs pull` if asset files are pointer text. Read the docs your task names first. Touch only the files your task
  owns; report other problems, do not fix them.

Safety
- Never commit game files, dumps, extracted tables, saves or game screenshots. Keep the repo public-clean (no real
  names, e-mails, hosts, tokens) and run the privacy scan before every commit.
- Never print, echo, log or commit a token or key. Scripts read them from files in the home folder.
- Never touch the owner's real game install. Never move, rename or delete saves of characters you did not create; use
  throwaway characters.
- Ask the orchestrator before anything public, paid or destructive.

Git
- Commit with a noreply identity. Commit messages end with `Co-Authored-By: <your model name> <noreply@anthropic.com>`.
- Open a PR to `main`; do not merge. A separate reviewer checks it and the orchestrator squash-merges. PR body: what changed, how it was tested,
  what is left. Do not message other agents or sessions.
- A change players notice adds a `changelog.d/` fragment (never edit `CHANGELOG.md`). Keep docs in step with your change. Do not bump the release version unless your task says so.

Game slots and tests
- A lane that needs the game runs the `d2r-in-game-testing` skill.
- Tests run in the background only: no synthetic keyboard or mouse input (SendInput, SetCursorPos,
  SetForegroundWindow), no focus stealing.
- Game slots (`[testing].game_slots`) are queued, never added. Lock one for your whole game session, put its number on
  every command that can touch it, run with `MODKIT_RUN=<lane>` so runs do not release your lock, and unlock straight
  away. Check slot status before and after.
- Make one lock attempt that does not wait. If no slot is free, stop, file (or ask the orchestrator to file) a
  `ready-for-agent` issue for the run, and report. Do not poll. Never wait on CI and never touch runners: push, open the PR, report.
- Install only through a script that stops when the lock fails, and check the lock is still yours right before
  installing. Kill only processes you started, by PID.
- Run only the checks your changed files map to, plus the build validator and unit tests. For player-facing changes,
  also test once on a release-like install.
- Never end your turn while a build, install, download or game run you started is still going.

Report
- Final report: PR link, head SHA, CI state, files changed, checks and tests with results, what is left, any incident.
