---
name: d2r-toolkit
description: Route Diablo II Resurrected mod work to the pinned toolkit, craft skills and rules. Use before starting mod work, resolving tools or pins, or contributing reusable tools, templates and engine facts.
---

# Using the D2R toolkit from a mod

1. Resolve the checkout with [toolkit finder](../../../docs/toolkit-finder.md). Use the pinned checkout as the working directory for `python -m modkit`. Report a mismatch. Change the pin only deliberately after rebuilding and testing, in a pin-only commit.
2. Read the applicable domain skill before acting. Work from the nearest vanilla row and prefer data to plugins. Read relevant [engine limits](../../../knowledge/engine-limits.md), especially save widths, indexed rows, formulas and HD assets. Use [knowledge lookup](../../../docs/context-tooling.md#retrieve-knowledge) for specific sections.
3. Put reusable tools and verified engine facts in the toolkit, with build provenance. Keep mod-specific work in the mod.
4. Build to zero errors and review warnings. Use `d2r-in-game-testing` before any slot operation and record results in TESTING.md. Install only with the game closed. Back up saves and edit only with `modkit save-set`; use the debug spawner for items.
5. Keep extracted game files, saves, dumps, screenshots and private data out of Git. Run the privacy scan before commits. Get authorization before public, paid or destructive actions and leave the owner's game and saves untouched.

Read [the toolkit reference](reference.md#where-things-are) for the directory and skill map. Read [Rules for a mod](reference.md#rules-for-a-mod) for the full craft requirements, especially item type ID checks after itemtypes changes. Use `d2r-engine` for plugin constraints and `d2r-port` for a permitted classic port.
