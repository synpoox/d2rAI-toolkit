---
name: d2r-port
description: Port an authorized classic Diablo II mod or its tables and engine DLL behavior to Diablo II Resurrected with D2RLoader. Use for conversion, ID and function collisions, assets and parity.
---

# Port a classic mod to D2R

1. Get creator permission and terms before starting. Follow source behavior and record deviations. Keep game files and source archives out of Git. At project start retrieve `porting-classic-mods` → `0. Policy` and `1. Inventory the mod` for fidelity, gaps and DLL triage; use the source-version sections when starting from 1.09d.
2. Extract both games to ignored folders (D2R: `modkit fetch`), decode to text and merge table by table. Retrieve `porting-classic-mods` → `How rows merge`, `Column differences`, `4. IDs` or `5. Function numbers` for the operation at hand. Keep hard-coded D2R IDs, remap every moved reference including hit-6 missiles, maintain both banks where used, and fail the build on occupied function slots. Use `d2r-engine` for DLL rules data/SDK services cannot express.
3. Keep rows below 32,768 and keys within dataguide lengths. Validate every referenced row/function and add a build-time ID self-check and run the item type ID check after itemtypes changes. Preserve printf placeholders, legal string IDs, resolved sounds and real icon frame layouts. Retrieve `8. Strings, sounds, icons` or `9. Graphics` while working on those assets. Build HD first with vanilla stand-ins before final art; ship referenced classic assets.
4. Clear validator errors, restart after the first loader cache-building start and clear loader asserts. Use `d2r-in-game-testing`; first reach Act 1, then verify parity by feature. Maintain deviations, issues and TESTING.md with observed drift.
