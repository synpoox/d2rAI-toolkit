---
name: d2r-monsters
description: Change Diablo II Resurrected monsters, bosses, superuniques, minions, skills, AI, difficulty, density, level spawns or waypoints.
---

# Monsters and areas

1. Clone vanilla rows with the desired AI, skills and appearance. Retrieve `tables` → `Monster records and skills` for linked records and string keys, or `Monster spawns and difficulty` for bosses, areas and scaling.
2. Keep quest bosses' roles, match skill modes to real monmode/monseq entries, and use exact-case model keys. For new art retrieve `hd-graphics` → `Monsters`. For new areas retrieve `engine-limits` → `Levels and areas`; reuse vanilla layouts first. Clear maze Position without entry rooms and respect automap bounds. Use `d2r-engine` for wholly new behavior.
3. Build and fix validation errors. In a slot with `d2r-in-game-testing`, enter the target difficulty and area and verify name, HD/classic appearance, life/damage, skill timing, drops and normal death.
