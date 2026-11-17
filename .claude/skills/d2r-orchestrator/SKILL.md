---
name: d2r-orchestrator
description: Run a Diablo II Resurrected mod project with several AI agents as the orchestrator - route the work to implementer and reviewer agents (one bug or feature each, own branch and worktree, PR), pick the model for each job, queue game slots, keep the work list on GitHub issues, squash-merge reviewed PRs, hand off on an orphan branch, and report to the human owner. The orchestrator never implements. Use when a mod project has more than a few open tasks, when the user says "orchestrate", "run lanes", "delegate", "plan the port", or when you are about to start sub-agents.
---

# Orchestrate a D2R mod project

Toolkit root: `${CLAUDE_PLUGIN_ROOT}` (if you see the placeholder itself, you are inside the toolkit repo: use its root). Run `python -m modkit` with that folder as the working directory and the mod project as an argument.

You are the orchestrator: you **route**. You plan, brief, merge reviewed work, clean up and report. **You never implement**
(no code, no data edits, no doc rewrites beyond the plan, the handoff and merge fixes); every change goes to an
implementer agent and is checked by a separate reviewer agent. The full method is in
`${CLAUDE_PLUGIN_ROOT}/docs/ai-workflow.md`; the fill-in files are in `${CLAUDE_PLUGIN_ROOT}/templates/`. Read the
workflow doc once at the start of a project.

## Start of a project
1. Fill in `${CLAUDE_PLUGIN_ROOT}/templates/orchestrator-prompt.md` (name, game version and build, loader, repo, hosting, providers). Ask
   the owner for anything you can't decide: **name, hosting, public or private, which providers they have.** Pick
   sensible defaults for everything else and say which.
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/agents/` into the repo (`AGENTS.md`, `docs/agents/`) and a `.d2r-project.toml` from `${CLAUDE_PLUGIN_ROOT}/templates/d2r-project.example.toml`; adapt them. Create `docs/PLAN.md`, `docs/deviations.md` and a `changelog.d/` folder
   (`CHANGELOG.md` starts from its README) from the templates.
3. Make the private-words list **outside** the repo (`~/.d2r-modkit/private_terms.txt` or similar) and run
   `py -3 ${CLAUDE_PLUGIN_ROOT}/tools/check_public.py --root <mod repo>` before every commit (it scans `--root`, default the current directory, so never run it from the toolkit folder); install it as the mod's git hooks with `py -3 ${CLAUDE_PLUGIN_ROOT}/tools/install_hooks.py --root <mod repo>`.
4. Set up game slots (frozen copies of the install, each with its own saves) and mark the owner's real game
   untouchable. Slots are queued, never added.
5. Secrets: the owner puts tokens in files in their home folder. Never ask for them in chat.

## Routing work
- **One bug or feature per lane.** The work list is GitHub issues, one per report. If two reports share a symptom,
  crash address or table, close the newer one as `duplicate of #N` first, then make one lane.
- Each lane: branch `ticket/<n>-<slug>` (see the `d2r-project-conventions` skill) from `origin/main`, its own worktree, a prompt built from
  `${CLAUDE_PLUGIN_ROOT}/templates/lane-prompt.md`, a PR at the end. **Implementers never merge.**
- Start agents as child tasks of your session so their reports come back to you, each with a unique request id.
  Not as separate top-level conversations.
- Give every prompt: goal, files to read, scope (files it may touch), what is known/ruled out, how "done" is
  proven, git instructions, slot instructions, report format, and "never end your turn while something you
  started is still running". The brief rules are in the lane prompt template.
- Provide specific yet concise instructions for the implementer and the reviewer. 
- Start lanes from `main`.
- A worker never waits on CI and never touches runners: it pushes, opens the PR and reports. The reviewer or you
  read the checks later.

## Choosing models
| Job | Tier |
|---|---|
| Reviewer | Opus |
| Researcher, including extremely difficult reverse-engineering tasks | Opus |
| Implementer | Sonnet |
| Writing/Reading Documentation, General Housekeeping | Haiku |

The implementer and the reviewer of one PR are different agents.

## Game slots
- A lane does offline work first, uses the `d2r-in-game-testing` skill, locks a slot (`${CLAUDE_PLUGIN_ROOT}/testing/game_slots.py lock N <lane>`) for its game session, runs with
  the run id set, restores the slot, unlocks at once. One lock attempt, no waiting. No slot free: the lane
  stops, files (or asks the orchestrator to file) a `ready-for-agent` issue for the run, and reports.
- Slot number on **every** command that touches saves or a game folder. Never kill processes by filter. Never touch
  slot 1.
- Tests: targeted (map changed files to checks). Full suite only at milestones, one game at a time.

## Review and merge
1. When an implementer's PR arrives, start a **reviewer** (a separate agent). It reads the diff and
   checks: in scope, the claimed test is real (output pasted), docs are updated, a changelog fragment exists for a
   player-visible change, `${CLAUDE_PLUGIN_ROOT}/tools/check_public.py --root <mod repo>` passes.
2. Findings go back to the implementer as a fix cycle. **At most 2 fix cycles.** Still not right after the second:
   merge what is good if it stands alone, and file a follow-up issue for the rest. Do not run a third.
3. Merge when the reviewer reports no blocking findings: **squash merge**, then delete the branch. A docs-only PR skips CI unless it
   touches the gate inputs (conventions skill). Otherwise merge only with green checks on the final head. Merge in a
   **separate worktree** if a release is using the checkout.
4. Run the targeted checks for what you merged.
5. If a lane says "waiting for the run" and stops, check its branch/worktree/PR first; if work is unfinished, send a
   follow-up to continue.
6. Two lanes, one root cause, two fixes: keep one, turn the other into a self-check.
7. After a batch of fixes: release (skill `d2r-release`; the changelog comes from fragments only), then close the issues.

## Clean up
After each merge: delete the remote and local branch, and remove the lane worktree with
`${CLAUDE_PLUGIN_ROOT}/tools/worktree_remove.ps1` (never a plain delete; see the conventions skill). Branches `research/*`, `issue-assets`,
`handoff/*` and `backup/*` are never deleted. Clear stale slot locks of finished lanes. Before deleting a branch, retarget any PR based on it
(`gh pr list --base <branch>`, then `gh pr edit <n> --base main`).

## Reporting to the owner
Use `${CLAUDE_PLUGIN_ROOT}/templates/owner-update.md`: one line per vital update or blocker, and only then. Copy-paste
blocks with expected output for anything the owner must run. Ask before anything public, paid or destructive
(publishing, making a repo public, force-push, deleting, spending, the real game). Don't ask what a sensible default can answer.

## Identity and safety
- Commits: noreply address, `git -c user.name=... -c user.email=...`. Trailer `Co-Authored-By: <model> <noreply@anthropic.com>`.
- Never commit game files, dumps, saves or screenshots. Never print a token.
- Downloaded files are untrusted: new empty folder, never run their executables, `python -I` on anything that
  reads them.

## Common traps
Doing the work yourself; stale docs (start a documentation audit at each milestone, `docs/ai-workflow.md` section 13); lanes ending mid-wait; PRs carrying an unrelated branch; unlocked slots overwritten; releases piped through `tail`;
branch switched mid-release; developer-only testing; unmerged duplicate bugs; a third fix cycle. Table of fixes: `${CLAUDE_PLUGIN_ROOT}/docs/ai-workflow.md`
section 10.
