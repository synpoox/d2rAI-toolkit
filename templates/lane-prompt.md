# Lane prompt: <short title, e.g. "Bug 17: crash when entering Andariel's lair">

> One job per lane prompt. Fill in the placeholders, delete the notes, and send it as the lane's task. The shared
> rules live in `AGENTS.md`, so this prompt only carries what is specific to this job.
> Guide: [docs/ai-workflow.md](../docs/ai-workflow.md#9-writing-a-good-lane-prompt).
>
> Brief rules (a lane starts with no memory; this prompt is everything it knows):
> 1. One job per prompt. If it needs "and also", write two prompts.
> 2. Goal in one sentence, and why it matters. Name docs and files by path, not by description.
> 3. Scope: the files it may change; everything else is out of bounds.
> 4. Known facts and suspicions, kept apart: say "suspicion" when you have not checked. List what was ruled out.
> 5. Done means evidence: a check name, a command and the expected line. "Fixed" is not evidence.
> 6. Say what *not* to do when the obvious approach is wrong.
> 7. Reverse-engineering lanes get the build number and the address list, and must re-verify every address by bytes.
> 8. Git, slot and report sections stay; the lane never waits on CI and never merges.

Read `AGENTS.md` and follow it exactly. You are the lane `<lane-name>` of `<MOD NAME>`.

## Goal
<One sentence: what must be true when you are done, and who it matters to.>
Example: "The game no longer crashes when a player enters the Catacombs with a Whirlwind-type skill equipped (bug
#17)."

## Read first
- The issue #<N> (the whole thread, including comments)
- `<doc 1>` (why)
- `<doc 2>` (why)
- `knowledge/<topic>.md`

## Scope
You may change:
- `<path or glob>`
- `<path or glob>`

Do not change anything else. If you find another problem, list it in your report.

## What is already known
- <Cause found, symptom, log excerpt, address, build number.>
- <What was already tried or ruled out.>
- <Suspicions, marked as suspicions.>

## Do
1. <Step or constraint. Be concrete: commands, file names, expected output.>
2. <...>
3. <Add a check or unit test for what you built.>
4. <Update the docs. Add a `changelog.d/` fragment if players will notice.>

## Don't
- <The obvious wrong approach and why.>

## Done means
- <Check name(s)> pass: `<command>` prints `<expected line>`.
- `python -m modkit build <project>` shows 0 errors.
- `python -m unittest` passes.
- `python tools/check_public.py` prints nothing.
- <Release-package test if player-facing.>

## Git
- Branch `ticket/<n>-<slug>` (or `research/<topic>`, `refactor/<topic>`; see the d2r-project-conventions skill) from `origin/main`. Open a PR to `main`. Do not merge, and do not wait for CI: push, open the PR, report. A separate reviewer checks it.
- Do not bump the release version. <Or: "Bump to the next free version after main's.">

## Game slot
<"No game needed." or "Needs a game: lock a slot as the rules say (one attempt, no waiting); if none is free, stop and file a `ready-for-agent` issue.">
Checks to run: `<list>`.

## Report
PR URL, head SHA, files changed, tests run with results, what is left, any incident. Do not end your turn while
anything you started is still running.
