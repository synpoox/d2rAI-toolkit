---
name: d2r-crash
description: Triage a player’s Diablo II Resurrected crash, access violation, D2R.exe RVA or D2RLoader last-resort report. Use crash evidence to identify the failing module, instruction and cause.
---

# Triage a crash

1. Collect available reports, loader and plugin logs, game version/store, other plugins and observed symptoms. Read [the collection list](reference.md#1-get-the-files-ask-once-same-session) for paths. Keep artifacts private.
2. Use [crash triage](../../../knowledge/crash-triage.md) and [Read before guessing](reference.md#2-read-before-guessing). Identify the actual module, subtract its image base and use a matching runtime image. Verify the faulting instruction, access type, register values and plausible caller chain.
3. Read [environment checks](reference.md#3-rule-out-the-environment) before attributing the crash to the mod. Verify the installed plugin version, path, other plugins and first-start cache. Bisect with off-switches.
4. Fix the failing data or guard the engine case using `d2r-engine`. Record report lines, instruction, register, build and regression evidence. Say when the crash could not be reproduced and what diagnostics a recurrence will produce.
