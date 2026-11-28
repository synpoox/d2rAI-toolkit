---
name: d2r-mod-setup
description: Set up d2r-modkit or a Diablo II Resurrected mod project. Use for missing CascLib or game data, new projects, builds, installs, launch and shipping.
---

# Set up the toolkit and a mod project

1. For dependencies, missing CASC data or an initial checkout, use [One-time setup](reference.md#one-time-setup-windows). Keep extracted Blizzard files outside Git.
2. Run `python -m modkit new <dir> --name <ModName>` for a new project. Read [A new mod](reference.md#a-new-mod) for mods with plugins, namespaces or extended saves. Port an existing classic mod through `d2r-port`.
3. Use the relevant domain skill, then `python -m modkit build <dir>`. Fix all errors and review warnings. Read [The loop](reference.md#the-loop) for loader selection and restart behavior. Use `d2r-in-game-testing` before installing to a slot or making a test character.
4. Record check evidence in TESTING.md. Use `d2r-debug` on failure and [Shipping](reference.md#shipping) plus `d2r-release` for packaging.
