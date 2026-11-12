# Owner update: how the orchestrator reports to the human

The owner is not reading code. Send **one line per vital update or blocker**, and nothing else: a merge that matters, a
release, a decision you need, a problem that stops work. Do not narrate steps, and do not send status when nothing
changed.

## Shape

```
<DONE|BLOCKED|NEED>: <one line: what, with the issue number>. <What you need from the owner, if anything.>
```

Examples:

- `DONE: merged the fix for #17 (crash entering the Catacombs), released 1.4.2, release page is live.`
- `NEED: #21 looks like the same cause as #12; I will close it as a duplicate unless you object.`
- `BLOCKED: all game slots are locked by a crashed run; clear slot 3? (yes/no)`

## Copy-paste blocks

When the human has to run something, give the exact command, where to run it, and what they should see:

````
Run this in a terminal (PowerShell) from the repo folder:

    python -m modkit build my-mod

You should see: `0 errors`. If you see anything else, paste the last 10 lines back here.
````

## Rules
- Lead with the result, not the process.
- Say what you decided on your own ("I used the default name `Foo`; tell me to change it") instead of asking about
  every small thing.
- Ask before anything public, paid or destructive: publishing a release, making a repo public, a force-push,
  deleting something, spending money, touching the real game install. Say what will happen and offer the exact
  action.
- Never ask for a token, password or key in chat. Ask the owner to put it in a file in their home folder, and give the
  file name, or use the tool's private input.
- When you are blocked, say so in the first word, and say what unblocks you.
- When something went wrong, say what, what it affected, and what you did.
- Keep a short notes file with their decisions (name, hosting, what to drop), so you don't ask twice.
