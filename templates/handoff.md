# Orchestrator handoff: <MOD NAME>, <YYYY-MM-DD>

> How to use: when your context is nearly full, or the owner ends the session, fill this in and push it as the only
> file (`HANDOFF.md`) on a new orphan branch `handoff/orchestrator-<YYYY-MM-DD>`:
> `git switch --orphan handoff/orchestrator-<date>`, add the file, commit with the noreply identity, push. The branch is
> never merged and never deleted. The next orchestrator reads the newest `handoff/orchestrator-*` branch first, then the
> issues. Keep it under one page: pointers, not copies. Delete these notes. No tokens, no real names, no e-mails.

## State
- Repo `<REPO>`, `main` at `<SHA>`, released version `<VERSION>`, toolkit pin `<SHA>`.
- Phase: `<PHASE FROM docs/PLAN.md>`. Last owner message: `<DATE, what they asked for>`.

## Running now
| Agent | Role | Issue / PR | Branch | State |
|---|---|---|---|---|
| `<name>` | implementer / reviewer | #<n> / #<pr> | `ticket/<n>-<slug>` | `<what it is doing, fix cycle 0/1/2>` |

## Waiting
- Needs the owner: `<decision or action, since when>`.
- Blocked on: `<issue, slot, external thing>`.
- Follow-up issues filed after fix cycle 2: `#<n>`.

## Next
1. `<the next three jobs, in order, with issue numbers>`

## Things the next orchestrator must know
- Decisions made that are not yet in an issue or ADR: `<decision, why>`.
- Traps hit this session: `<cause, not just symptom>`.
- Slot locks, worktrees or branches to clean up: `<list>`.
