---
name: d2r-ui
description: Change Diablo II Resurrected HD layouts, inventory/stash/cube/trade grids, panel art, widgets, buttons, tabs, skill tree, fonts or UI text.
---

# HD UI: layouts, panels and grids

1. Read relevant [UI layouts](../../../knowledge/ui-layouts.md) sections. Use [widget and asset discovery](reference.md#find-what-to-change) to find the actual widget IDs, bounds and art. Change controller variants when supported.
2. For grids, read [Grid sizes](reference.md#grid-sizes-inventory-stash-cube-trade). Match both inventory records to the layout and respect the 16 × 16 save limit for personal stash, inventory and cube. Preserve equipment dimensions. For art or tree tabs, read the corresponding [reference heading](reference.md), including stock widget compatibility and untested page ranges.
3. Build and validate. Use `d2r-in-game-testing` and [the screen checklist](reference.md#build-and-test) to verify geometry, interactions, controller and low-texture layouts as applicable.
