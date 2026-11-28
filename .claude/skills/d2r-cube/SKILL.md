---
name: d2r-cube
description: Create or change Diablo II Resurrected Horadric Cube recipes for crafting, upgrades, rerolls, sockets, portals, gold or conditional transmutation.
---

# Cube recipes (cubemain.txt)

1. Find and clone a similar vanilla `cubemain` row with `modkit show`. Read [A recipe row](reference.md#a-recipe-row) for input counts, qualifiers, output fields, item levels and portals.
2. For gating, read [Conditions](reference.md#conditions-opparamvalue-d2r-hard-limits). Player ops outside the supported range may pass silently. Prefer item-token or item-stat gating. Unsupported conditions require `d2r-engine`.
3. Build and resolve validator errors. With `d2r-in-game-testing`, verify the exact inputs, missing and extra inputs, and resulting output stats.
