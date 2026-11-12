# Orchestrator decisions, 2026-11-12 (night run, owner away)

## Approvals received (owner, 2026-11-12 evening)

| Group | Approved | Not approved |
|---|---|---|
| H-P | HP1–HP18 | HP14's origin-bug ledger (the rest of HP14 is in) |
| H-9 | H9-1–H9-7, H9-10–H9-15 | H9-8, H9-9 |
| H-F | HF1–HF4, HF6–HF8, HF10 | HF5, HF9, HF11, HF12, HF13 |
| H-X | X1–X11, X13, X14, X16, X17 | X12, X15 |
| I | I1–I13, I15–I20 | I14. I9 = deviations ledger only. I11 skill named `d2r-orchestrator` |
| IK | all recommendations | IK1: orchestrator name (as I11). IK4: throw. IK9: rename the coordinator skill per I11 |

Phase 3 (mod switches): **not started**, waiting for explicit permission.

## Decisions I made (best judgment)

1. **HP14 scope.** Lands the deviation status vocabulary and the D2R-only approval ledger text in
   `porting-classic-mods.md` §10. The origin-bug ledger is left out entirely.
2. **I4 (triage labels).** Lands the five labels only. The `origin-bug` label and its ledger are dropped, to match
   the HP14 and I9 exclusions.
3. **I9 (ledgers).** Only `templates/deviations.md`. No `origin-bugs.md`, no `d2r-only-content.md` template.
   (HP14's D2R-only ledger stays as porting-guide text only, no template.)
4. **IK1 file name.** `templates/coordinator-prompt.md` becomes `templates/orchestrator-prompt.md`, rewritten with the
   orchestrator method. IK9: `.claude/skills/d2r-coordinator` becomes `.claude/skills/d2r-orchestrator`, every
   reference updated. The name differs from the owner's private global `orchestrator` skill, so they do not clash.
5. **X10 and X11** ("done in G"). Done as knowledge corrections only (engine-limits.md, tables.md) with evidence.
   G2, G4 and G5 code stays on hold.
6. **X12 not approved.** `porting-classic-mods.md` keeps "write both banks" untouched. H9-7 (Warlock placeholder
   rows in the LoD bank) lands as facts in `tables.md` "Two banks" without changing that advice.
7. **X15 not approved.** The screenshot rule ("never commit them") stays as is; I12's screenshot rules land without
   the orphan `issue-assets` branch part.
8. **I14 not approved.** No merge-slot pool text in `docs/testing.md`; I12/I13 land without it.
9. **HF10** lands inside the I10 research template (pin sources by hash), as the plan says.
10. **Mod switch issues** (the per-mod issues for lanes H and I) are **not** filed in the mod repos tonight. Filing
    them writes to the mod repos (one public), and they are Phase 3 work items. Listed as a next step instead.
11. **Packaging.** Items are grouped into 10 PRs by destination file, not one PR per item, to avoid the table-row
    conflicts the last handoff warned about. Each item still has its own sub-issue; each PR closes its items.
12. **Artifact doc.** I set the Approval cells in the live doc to match the owner's message.
