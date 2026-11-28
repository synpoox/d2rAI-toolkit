---
name: d2r-skill
description: Create, balance or rework a Diablo II Resurrected skill, including tree slot, tooltip, icon, missiles, states and HD animation.
---

# Make a D2R skill

1. Identify class or item/monster use, the class skill to replace and unusual behavior. Read relevant [engine limits](../../../knowledge/engine-limits.md) and [vanilla function selection](reference.md#2-find-the-vanilla-skill-whose-behaviour-is-closest). Use `d2r-engine` only for behavior data cannot express.
2. Preserve the class save slot by replacing an existing row unless extended saves are explicitly supported. Read [Class skills](reference.md#3-class-skills-replace-dont-add) and [Write the op](reference.md#4-write-the-op) for fields, formulas, damage, visuals and the example. Sequence skills need SQ and a compatible HD state; missiles need an HD model. Preserve Whirlwind stop functions when cloning its behavior.
3. For a port, read [Traps from ports](reference.md#traps-from-ports). Build, fix errors and check renamed references. Run [the runtime checklist](reference.md#6-hand-over) with `d2r-in-game-testing` and record results in TESTING.md.
