---
name: d2r-in-game-testing
description: Run and report Diablo II Resurrected checks in a game slot. Use before any slot operation, when a change needs in-game proof, or before handing a check to the owner.
---

# Check a change in the real game

1. Run the build validator, unit tests and targeted offline checks first. Full game suites are for milestones, one game at a time. Retrieve `docs/testing` → `Slot commands for a lane` before acting. Project game-check instructions may specialize steps without waiving safety.
2. Work only in a permitted named slot, never slot 1. Set the lane environment, make one lock attempt with `--wait 0` and keep it until cleanup. If unavailable, file or route `ready-for-agent` with run steps. Use the background harness, never OS input or focus stealing. Leave owner's game and saves untouched.
3. Verify ownership before install or stop; install only with the game closed. Verify the slot savepath after every install. For player-facing changes follow [release-like install and restore](../../../docs/testing.md#test-what-players-get). If needed pin the DS1 variant using [its procedure](../../../docs/testing.md#pin-a-ds1-variant).
4. Test on Hell with the slot's level 99 Reign of the Warlock character of your class (all skills unlocked); retrieve `docs/testing` → `The test character` if absent. Scan startup logs with the full plugin set. God mode one-shots targets; use test commands for boss-life checks. Use console before clicks; check the cursor before inventory clicks. For cheats or misleading console acknowledgements read [Practical hazards](../../../docs/testing.md#practical-hazards) and retrieve the matching `cheat-commands` section.
5. Keep screenshots, logs and saves outside Git. On success or failure stop only your processes (by PID), restore DS1/installation, unlock and verify status. Report observed output and passed/failed/skipped counts. For harness-inaccessible input, real-player judgement, owner-game checks or five minutes with no progress, follow [handoff](../../../docs/testing.md#who-runs-the-check).
