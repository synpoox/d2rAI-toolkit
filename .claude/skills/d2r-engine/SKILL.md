---
name: d2r-engine
description: Extend Diablo II Resurrected with D2RLoader plugins when data cannot express a feature. Use for engine hooks, native functions, calc codes, limits, new game systems, or finding and understanding a D2R function.
---

# Engine work: D2RLoader plugins and reverse engineering

1. Check vanilla functions and retrieve the applicable `engine-limits` and `d2rloader-capabilities` sections before native work. Prefer data, then PluginSDK services. For a new subsystem start with `new-game-systems`; for charged items use `d2r-items`; for classic DLLs use `d2r-port`.
2. Verify the image, ABI, entry bytes/instruction boundaries and existing hooks (including loader trampolines). One owner per site. Retrieve `engine-re` → `Before hooking` or `Resolve addresses by signature`; use `knowledge address --symbol <symbol-or-rva>` for registry evidence. For a new finding, retrieve `engine-re` → `Dump the running image`, `Analyse once` or `Query scripts` according to the step.
3. New hooks resolve by unique signature. Disable only the affected part on absent or ambiguous matches. Guard existing fixed RVAs by their exact image stamp and reverify after game/loader updates. Keep expected-byte validation, ABI resource, template environment/sound/item-type guards, per-part status/log and feature off-switches. Use major.minor in installer requirements.
4. For build/install follow [Build](../../../plugin-template/README.md#build) and [Install and loading](../../../plugin-template/README.md#install-and-loading). For custom skill slots or inline hooks use the corresponding template section; for dispatch writes retrieve `engine-re` → `6. Writing hooks`.
5. Record build, ABI/bytes, uniqueness and ownership evidence. Build and run targeted regressions via `d2r-in-game-testing`. Distinguish static RE from runtime proof and report compatibility gaps.
