---
name: d2r-crash
description: Triage a player’s Diablo II Resurrected crash, access violation, D2R.exe RVA or D2RLoader last-resort report. Use crash evidence to identify the failing module, instruction and cause.
---

# Triage a crash

1. Collect available reports, loader and plugin logs, store/version, other plugins and the last action. Ask for missing files once, together. For paths, retrieve `crash-triage` → `1. Ask for the right files`. Keep artifacts private.
2. Identify the module and subtract its actual image base from RIP. Use a dump of that same image. Verify access type, bad address/register and a plausible caller chain. Retrieve `crash-triage` → `2. Read the report` for report fields/stack mapping, or `3. Find the function and its job` for Ghidra. For a known pattern retrieve its worked example or evidence section.
3. Check plugin version/path, first-start cache, other plugins and off-switch bisection before assigning cause. Retrieve `crash-triage` → `4. Was it the mod, the data, or the machine?` for ambiguous or shutdown reports.
4. Fix data errors in data; use `d2r-engine` for guarded, counted and logged engine fixes. Record build, report lines, instruction, register, regression check and runtime evidence. If unreproduced, state that and name the diagnostics a recurrence would produce.
