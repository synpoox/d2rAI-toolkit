---
name: d2r-mod-setup
description: Set up d2r-modkit or a Diablo II Resurrected mod project. Use for missing CascLib or game data, new projects, builds, installs, launch and shipping.
---

# Set up the toolkit and a mod project

1. For prerequisites or missing CASC data use [Quick start](../../../README.md#quick-start-5-minutes) and [Requirements](../../../README.md#requirements). Keep Blizzard files and outputs outside Git.
2. Start with `python -m modkit new <dir> --name <ModName>`. For project layout, namespaces, plugins or extended saves read [Modkit project layout](../../../docs/README.md#modkit-project-layout). Route creator-approved classic ports through `d2r-port`.
3. Apply the relevant domain skill and run `python -m modkit build <dir>`. Review warnings and clear validator errors. Install with the game closed. Use `d2r-in-game-testing` for agent installs, launches and test characters; for launch mode and first startup retrieve `d2rloader` → `Starting a mod`.
4. Record TESTING.md evidence. Use `d2r-debug` for failures and `d2r-release` for packaging. Ship only mod files, with D2RLoader when using plugins or extended saves.
