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

- Start from `origin/main` (`git fetch origin`, then a new branch); read the docs your task names first. Touch only
  the files your task owns; report other problems, do not fix them.
- Never commit game files, dumps, extracted tables, saves or game screenshots. Keep the repo public-clean (no real
  names, e-mails, hosts, tokens) and run the privacy scan before every commit. Commit with a noreply identity.
- Open a PR to `main`; do not merge. The coordinator reviews and merges.
- Game slots (`[testing].game_slots`) are queued, never added: lock one, put its number on every command that can
  touch it, unlock straight away. Never touch the owner's real install. Kill only processes you started.
- Never end your turn while a build, install, download or game run you started is still going.
- Final report: PR link, head SHA, checks and tests with results, what is left, any incident.
