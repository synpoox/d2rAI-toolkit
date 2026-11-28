---
name: d2r-port
description: Port an authorized classic Diablo II mod or its tables and engine DLL behavior to Diablo II Resurrected with D2RLoader. Use for conversion, ID and function collisions, assets and parity.
---

# Port a classic mod to D2R

1. Confirm creator permission before work. Read [Policy](reference.md#policy-tell-the-user-then-follow-it), [classic porting](../../../knowledge/porting-classic-mods.md), and the source-version knowledge files as applicable. Inventory data, DLL rules, assets and expected behavior.
2. Follow [Steps](reference.md#steps) by table and subsystem. Keep D2R-only hard-coded IDs at D2R's numbers, remap references and move occupied function numbers. Preserve both banks, sound and string semantics and format placeholders. Use `d2r-engine` for behavior data or SDK services cannot express.
3. Apply the [table completion checks](reference.md#before-you-say-done-with-a-table) and item type ID checker. Fix build errors and loader asserts before runtime parity checks. Rebuild HD before final art polish. Use `d2r-in-game-testing`, record drift and evidence, and keep TESTING.md current.
