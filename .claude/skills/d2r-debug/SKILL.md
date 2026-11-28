---
name: d2r-debug
description: Diagnose Diablo II Resurrected mod crashes, asserts, hangs, missing characters, load failures and wrong skill, item or UI behavior. Use logs and controlled bisection.
---

# Debug a D2R mod

1. Read [Where to look](reference.md#where-to-look-newest-first) and start with the newest logs and asserts. Route crash RVAs or last-resort reports to `d2r-crash`. Use [loader notes](../../../knowledge/d2rloader.md) for installation or plugin load surprises.
2. Match evidence to [Symptom → usual cause](reference.md#symptom---usual-cause) or [debugging knowledge](../../../knowledge/debugging.md). Back up saves and use supported save tooling only. For a hang, compare repeated busy-thread samples.
3. Bisect plugin features or patch ops per [Bisect](reference.md#bisect). Rebuild to zero errors and use `d2r-in-game-testing` to isolate and reproduce in an owned slot.
4. Fix the cause and record evidence and a regression check in TESTING.md. Report unresolved hypotheses separately.
