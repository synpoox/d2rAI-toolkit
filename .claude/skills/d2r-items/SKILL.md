---
name: d2r-items
description: Change Diablo II Resurrected loot, base items, item types, uniques, sets, runewords, gems, affixes, stats, drops, vendors or HD item art.
---

# Items, affixes and loot

1. Clone the nearest vanilla row and retrieve only the relevant `tables` heading: `Base item and vendor fields`, `Treasure classes and affixes`, or `Item and affix tables` for uniques, sets, runewords, stat display and affix fields. Read `charged-items` by section for reusable or charged items.
2. Use unique three-character codes across weapons/armor/misc. Supply classic and HD pictures; retrieve `hd-graphics` → `Item pictures` for assets. Preserve D2R itemtype IDs, then run [the ID checker](../../../plugin-template/README.md#item-type-ids).
3. Append indexed stats, respect saved widths, validate function-28 layers against Save Param Bits, and stay within six items per set and seven property slots per runeword. For layered stats, timed potions or save changes retrieve `engine-limits` → `Items, inventory, sets, runes, cube` or the affected `saves` section.
4. Build to zero errors. In a slot via `d2r-in-game-testing`, spawn the item and verify tooltip, HD/classic picture, sockets/runeword and vendors as applicable. Verify drops from the intended monster using repeated kills or a treasure-class check.
