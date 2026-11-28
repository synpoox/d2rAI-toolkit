---
name: d2r-toolkit
description: Route Diablo II Resurrected mod work to the pinned toolkit, craft skills and rules. Use before starting mod work, resolving tools or pins, or contributing reusable tools, templates and engine facts.
---

# Using the D2R toolkit from a mod

1. Resolve the pinned checkout with the [toolkit finder](../../../docs/toolkit-finder.md#the-rules). Run Modkit from that checkout. Report mismatches; update the pin only with owner approval, after rebuilding and re-testing, in a pin-only commit (`chore: pin d2rAI-toolkit to <sha>`).
2. Load the relevant domain skill. Start from vanilla rows and prefer data to code. For unfamiliar limits, use `python -m modkit knowledge search "<topic>" --limit 2` and retrieve the relevant section with `knowledge get <document> --section <heading> --format text`. See [tool commands](../../../docs/context-tooling.md#retrieve-knowledge) when needed.
3. Put reusable tools and engine findings in the toolkit with build provenance. Keep mod-specific work in the mod. Use the [documentation map](../../../docs/README.md) when locating a tool or guide.
4. Build to zero errors and read warnings. Use `d2r-in-game-testing` before slot work; record each installed change in TESTING.md. Back up saves and use `modkit save-set` for stat edits. Spawn items in game. Route failures to `d2r-debug` and player reports to `d2r-crash`.
5. After itemtypes changes, preserve D2R row IDs and run [the ID checker](../../../plugin-template/README.md#item-type-ids). Engine changes use `d2r-engine`; creator-approved classic ports use `d2r-port`.
6. Treat indexed rows as append-only, leave numeric strings below 65,536, and follow the formula and HD limits for your change.
7. Keep game data and build outputs, saves, dumps, screenshots, logs and private data out of Git. Run the privacy scan before every commit and use a noreply identity. Get approval for public, paid or destructive actions. Leave the owner's game and saves untouched and keep secrets out of chat.
