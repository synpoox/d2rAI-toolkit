---
name: d2r-items
description: Change Diablo II Resurrected loot, base items, item types, uniques, sets, runewords, gems, affixes, stats, drops, vendors or HD item art.
---

# Items, affixes and loot

Read the item sections of [tables](../../../knowledge/tables.md) and [engine limits](../../../knowledge/engine-limits.md). Start from the nearest vanilla row. For reusable or charged items read [charged items](../../../knowledge/charged-items.md).

- For base items or pictures, read [Base items](reference.md#base-items-weaponstxt-armortxt-misctxt). Keep a unique three-character code and classic and HD art entries.
- For stats, sets, runewords, affixes, drops or vendors, read the corresponding heading in [item reference](reference.md). Append indexed stats and respect save bit widths, set size and runeword slot limits.
- Read [Engine traps](reference.md#engine-traps) for itemtypes, layered stats or potions. Preserve D2R item type IDs and run the item type checker after changes.

Build to zero errors. Use `d2r-in-game-testing` for applicable tooltip, HD/classic picture, socket, runeword, vendor and actual drop checks.
