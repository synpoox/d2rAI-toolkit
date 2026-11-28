---
name: d2r-debug
description: Diagnose Diablo II Resurrected mod crashes, asserts, hangs, missing characters, load failures and wrong skill, item or UI behavior. Use logs and controlled bisection.
---

# Debug a D2R mod

1. Retrieve `debugging` → `Where to look first`. Start with the newest logs and post-startup asserts; route a crash RVA or last-resort report to `d2r-crash`. For plugin load or install surprises, search `d2rloader` by symptom.
2. Search knowledge with the exact assert, symptom or log text. Inspect the matching row in `debugging` → `Symptom table` if the excerpt needs context. For hangs retrieve `Hangs` and map repeated samples of the busy thread. Back up saves before changes and use supported save tools.
3. Halve enabled plugin features with `<plugin>-off.txt` or halve patch ops, rebuilding/reinstalling between trials. Respect feature dependencies. Compare the isolated row to vanilla and use an owned slot via `d2r-in-game-testing`.
4. Fix the cause, rebuild to zero errors and record evidence and the regression check in TESTING.md. Separate confirmed causes from hypotheses.
