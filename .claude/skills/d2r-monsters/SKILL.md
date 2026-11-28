---
name: d2r-monsters
description: Change Diablo II Resurrected monsters, bosses, superuniques, minions, skills, AI, difficulty, density, level spawns or waypoints.
---

# Monsters and areas

1. Read the monster and level sections of [tables](../../../knowledge/tables.md) and relevant [engine limits](../../../knowledge/engine-limits.md). Clone vanilla records for each changed table.
2. For a new unit, read [A new monster](reference.md#a-new-monster--rows-in-three-tables) for the three tables, linked IDs, assets and AI. For bosses, skills, spawns or difficulty, read the corresponding [reference heading](reference.md). Keep vanilla AI parameters and referenced IDs coherent.
3. Build and fix validation errors. Use the [test checklist](reference.md#build-and-test) with `d2r-in-game-testing`. Confirm the intended difficulty and area, spawn, AI/skills, drops and graphics as applicable.
