---
name: d2r-cube
description: Create or change Diablo II Resurrected Horadric Cube recipes for crafting, upgrades, rerolls, sockets, portals, gold or conditional transmutation.
---

# Cube recipes (cubemain.txt)

1. Clone the nearest vanilla row with `modkit show cubemain "<description>"` or find a precedent using `modkit find cubemain op=...`. Retrieve `tables` → `Cube recipe fields` when editing counts, qualifiers, outputs or levels.
2. For gating retrieve `engine-limits` → `Cube conditions and portal outputs`. Only player ops 1–14 are checked by the player switch; unsupported conditions may silently pass. Prefer an input token or supported item-stat gate. Use `d2r-engine` when data cannot express the gate.
3. Build to zero errors. In an owned slot with `d2r-in-game-testing`, test exact inputs, a missing or extra input, pass/fail values for conditions, and resulting output stats.
