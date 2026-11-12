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
13. **Branch names.** I16's `ticket/<n>-<slug>` is the approved convention. #237's fix cycle aligns the toolkit's
    lane prompt and `docs/ai-workflow.md` (which said `lane/<name>`) with it.
14. **Fix cycles wait for a free slot.** Fix workers count toward the 5-agent cap (reviewers do not), so a fix starts
    only when an implementer finishes.
15. **X4 key name.** `mod.json` gets a new optional `"namespace"` key; install and the release stager copy it to the
    top level of `d2rloader/metadata.json` (PR #244). Mods with namespaced strings set it there instead of by hand.
16. **X1 in CLAUDE.md.** CLAUDE.md gained a rule "in-game checks are run by agents in slots" (PR #245); the old rule 7
    (ask the human before public, paid or destructive steps) is now rule 8, unchanged in content.
17. **X7 (extended-save marker).** Both 0x44520005 and 0x44520006 are right, for different SDK versions; 0x44520069
    was never observed (PR #247). The lane worker read only the 8-byte headers of local `.d2s` files to check this;
    nothing was copied or changed.
18. **Main broke once.** Merging #236 left a bare `knowledge/` path in the d2r-toolkit skill, so
    `test_plugin_manifest` failed on main. The reviewer ran targeted tests that did not include it. Fixed in a small
    dedicated PR; from then on every reviewer brief requires `tests.test_plugin_manifest`.
19. **#248 merged without a reviewer.** It was a one-line path prefix that unbroke main. I read the diff and the
    test result myself. Every other PR got an independent Opus reviewer.
20. **#237 merged with one blocking item left.** After 2 cycles, the reviewer still objected to the `backup/`
    kept-branch prefix: it has no source in the three projects, only two one-off local branches. Per the 2-cycle cap,
    it and 5 small gaps went to follow-up #249, and #237 merged. Owner: please confirm or reject the `backup/` name
    (#249).
21. **Conflict merges after review.** When a reviewed PR conflicts with main because of later merges, a worker
    merges main in (keeping both sides) and also applies the cycle-2 wording nits in the same files. I then merge
    without a third review, unless the conflicts touched substance.
22. **Recurring bottleneck: reviewed PRs go stale.** #241 and #247 both conflicted with main after passing review,
    because lanes edit the same index files (knowledge/README.md, docs/README.md, the d2r-toolkit skill). The fix
    I use: one conflict worker per stale PR merges main in and applies the cycle-2 nits in the same pass, and I merge
    PRs as soon as review clears. Suggestion for the owner: have future lanes leave index rows to a final
    orchestrator-run index PR, so that only one PR touches each index.
23. **First loader with D2R 3.3 = 1.2.0-beta.** The #247 reviewer settled this by fetching the public D2RLoader
    changelog (read-only).
24. **#251 (orchestrator rename) is reviewed after #250 merges.** Both PRs rewrite templates/PLAN.md, docs/ai-workflow.md
    and the coordinator skill. Reviewing #251 before its conflict merge would review text that is about to change, so
    the order is: merge #250, merge main into #251 (a worker), then the independent review.
25. **Showcase verified.** At 91d54d4 the showcase builds with 0 errors (65 warnings).
26. **X14: no slot wait at all.** The #237 review found that a source project's game-check doc says "wait up to about
    30 minutes". The owner approved X14 ("stop and file ready-for-agent"), and the approval wins: one lock attempt that
    does not wait, then stop and file. #251's fix cycle removes every 30-minute wait.
27. **Agent cap.** The toolkit text now matches the owner's own method: at most 5 implementers at once, and reviewers
    do not count.
28. **#251 merged with 2 non-blocking leftovers.** Two files outside the PR still hint at waiting for a slot
    (`d2r-in-game-testing` skill, `testing/README.md`). Filed as #252.
29. **Lane parents closed.** #148, #167, #181, #190 and #206 are closed. Every approved sub-issue is merged, and each
    parent's closing comment says Phase 3 waits for the owner. Unapproved rows were not done, and their sub-issues were never filed.
30. **Main verified at the end.** The full suite on main + #251 (3ccf2a0) ran 968 tests OK. #251's last commit
    changed docs only. The showcase builds with 0 errors at 91d54d4; no `modkit/` change came after it.
