---
name: d2r-engine
description: Extend Diablo II Resurrected with D2RLoader plugins when data cannot express a feature. Use for engine hooks, native functions, calc codes, limits, new game systems, or finding and understanding a D2R function.
---

# Engine work: D2RLoader plugins and reverse engineering

1. Check relevant [engine limits](../../../knowledge/engine-limits.md), vanilla functions and [loader capabilities](../../../knowledge/d2rloader-capabilities.md). Prefer data, then SDK services. For a new subsystem, read [new game systems](../../../knowledge/new-game-systems.md). For native support for item charges, follow the [item skill](../d2r-items/SKILL.md). Route classic DLL ports through `d2r-port`.
2. Before native changes, verify the target image, ABI, instruction boundaries, existing hooks and ownership using [engine RE](../../../knowledge/engine-re.md) and the relevant build's address registry. One owner per hook site. New hooks resolve by unique signature. A signature-only part stays off individually on absent or ambiguous matches. Guard existing fixed RVAs by their exact image stamp; reverify on game or loader updates.
3. Read [The plugin](reference.md#the-plugin) before building or installing a DLL. Preserve the ABI resource, template guards, per-part status/log and feature off-switches. Installer checks use major.minor. Read [Common jobs](reference.md#common-jobs) for native slots, function hooks and checked table writes, or [Finding code](reference.md#finding-code-ghidra) for Ghidra commands.
4. Record the build, entry bytes, signature uniqueness and ABI evidence in knowledge. Build and use `d2r-in-game-testing` for targeted runtime checks. Report static findings, runtime proof, and unknowns separately.
