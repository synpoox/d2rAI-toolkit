---
name: d2r-in-game-testing
description: Run and report Diablo II Resurrected checks in a game slot. Use before any slot operation, when a change needs in-game proof, or before handing a check to the owner.
---

# Check a change in the real game

1. Run offline checks first. Read [The recipe](reference.md#the-recipe) before touching a slot. Follow project game-check details where they preserve these safeguards. Use the background harness only. Leave the owner's game and saves untouched.
2. Set required environment per the recipe. Select a permitted named slot. Make one lock attempt with `--wait 0`; if unavailable, stop and report a `ready-for-agent` check. Hold one lock through cleanup and verify ownership before install or stop.
3. Install with the game closed and verify the slot's savepath. Use a release-like install for player-facing changes. [Reuse or prepare](reference.md#the-test-character) a level 99 Reign of the Warlock character with Hell open. Scan plugin startup logs with the full plugin set, then run the named checks. Read [Rules](reference.md#rules) for console output, cursor and stall handling.
4. Keep evidence out of Git. On success or failure, stop your processes, restore DS1 and slot state, unlock and verify status. Report observed output, passed/failed/skipped counts, and anything unverified. Read [When to hand it over](reference.md#when-to-hand-it-over) only for a human-only check or stalled run.
