---
name: d2r-ui
description: Change Diablo II Resurrected HD layouts, inventory/stash/cube/trade grids, panel art, widgets, buttons, tabs, skill tree, fonts or UI text.
---

# HD UI: layouts, panels and grids

1. Find widgets with `modkit widgets <layout>`. Retrieve `ui-layouts` → `Main layout files` if the file is unknown, or `Measuring positions` for art discovery. Change applicable controller variants too.
2. For grids retrieve `ui-layouts` → `Grids`. Match both inventory records and the layout. Respect the 16 × 16 save limit for personal stash, inventory and cube. Preserve equipment dimensions and match rect scales. For art and skill trees retrieve `Panel backgrounds`, `Tab bars` or `Skill tree tabs` as appropriate.
3. Build to zero errors. In a slot with `d2r-in-game-testing`, verify grid alignment, far corners, tabs, gold, low textures and supported controller layouts. Treat unproven skill-page ranges as unverified.
