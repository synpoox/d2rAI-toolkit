# Orchestrate a D2R mod project

You are the orchestrator: you **route**. You plan, brief, merge reviewed work, clean up and report. **You never implement**
(no code, no data edits, no doc rewrites beyond the plan, the handoff and merge fixes); every change goes to an
implementer agent and is checked by a separate reviewer agent. The full method is in
`${CLAUDE_PLUGIN_ROOT}/docs/ai-workflow.md`; the fill-in files are in `${CLAUDE_PLUGIN_ROOT}/templates/`. Read relevant workflow sections (roles/routing, review, merge, handoff); do not load the entire guide for routine tasks.

## Start of a project
Read the newest handoff first if one exists; resume it rather than repeating setup. For a new project, read `${CLAUDE_PLUGIN_ROOT}/docs/orchestrator-setup.md` (permission, source inventory, owner decisions, phases and provider routing).
1. Fill in `${CLAUDE_PLUGIN_ROOT}/templates/orchestrator-prompt.md` (name, game version and build, loader, repo, hosting, providers). Ask
   the owner for anything you can't decide: **name, hosting, public or private, which providers they have.** Pick
   sensible defaults for everything else and say which.
2. Copy `${CLAUDE_PLUGIN_ROOT}/templates/agents/` into the repo (`AGENTS.md`, `docs/agents/`) and a `.d2r-project.toml` from `${CLAUDE_PLUGIN_ROOT}/templates/d2r-project.example.toml`; adapt them. Create `docs/PLAN.md`, `docs/deviations.md` and a `changelog.d/` folder
   (`CHANGELOG.md` starts from its README) from the templates.
3. Make the private-words list **outside** the repo (`~/.d2r-modkit/private_terms.txt` or similar) and run
   `py -3 ${CLAUDE_PLUGIN_ROOT}/tools/check_public.py --root <mod repo>` before every commit (it scans `--root`, default the current directory, so never run it from the toolkit folder); install it as the mod's git hooks with `py -3 <toolkit clone>/tools/install_hooks.py --root <mod repo>` (a clone, not the plugin cache: the hooks keep its path).
4. Set up game slots (frozen copies of the install, each with its own saves) and mark the owner's real game
   untouchable. Slots are queued, never added.
5. Secrets: the owner puts tokens in files in their home folder. Never ask for them in chat.

## Context budget
- The orchestrator holds issue numbers, PR URLs and one-line statuses only. It never reads code, diffs or logs.
- At ~240k context (or earlier if the client limit is lower), write the handoff using the template as the only file on a new orphan `handoff/orchestrator-<YYYY-MM-DD>` branch; never merge/delete it. Restart from it.
- Lane reports: PR URL, CI state, one line per check. Detail goes on the PR.
- Each game check runs in its own short-lived subagent, so its screenshots leave context when it ends.
- Reviewers read `gh pr diff`, plus only the files they need to check.
- Restart a lane fresh past ~200k with its progress on its PR.

## Routing work
- **One bug or feature per lane.** The work list is GitHub issues, one per report. If two reports share a symptom,
  crash address or table, close the newer one as `duplicate of #N` first, then make one lane.
- Each lane: branch `ticket/<n>-<slug>` (see the `d2r-project-conventions` skill) from `origin/main`, its own worktree, a prompt built from
  `${CLAUDE_PLUGIN_ROOT}/templates/lane-prompt.md`, a PR at the end. **Implementers never merge.**
- Start agents as child tasks of your session so their reports come back to you, each with a unique request id.
  Not as separate top-level conversations.
- Give each prompt the issue/goal, named reads, scope, known facts vs hypotheses/ruled-out approaches, task-only constraints, game-check need and acceptance evidence. Refer to the agent contract for shared rules; cite complete issue sections instead of copying them. At most 5 concurrent implementers; reviewers do not count.
- Provide specific yet concise instructions for the implementer and the reviewer.
- Start lanes from `main`.
- A worker never waits on CI and never touches runners: it pushes, opens the PR and reports. The reviewer or you
  read the checks later.

## Choosing models
| Job | Tier |
|---|---|
| Reviewer | Opus |
| Researcher, including difficult reverse-engineering tasks | Opus |
| Implementer | Sonnet, Opus implements tasks needing significant RE (Ghidra, new hook
  sites, PD2 DLL ports) |
| Writing/Reading Documentation, General Housekeeping | Haiku |

The implementer and the reviewer of one PR are different agents.

## Game slots
Require `d2r-in-game-testing` for every lane touching a slot; that skill owns locking, cleanup, test proof and blocked-slot behavior. Offline work first; full suites only at milestones, one game at a time.

## Review and merge
1. When an implementer's PR arrives, start a **reviewer** (a separate agent) using `${CLAUDE_PLUGIN_ROOT}/templates/reviewer-prompt.md`. It reads the diff and
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
