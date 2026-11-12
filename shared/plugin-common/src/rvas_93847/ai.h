// Build 93847: monster AI: think functions, the tick block, helpers and mode commands.
// The AI table itself is in tables.h (AiTable).
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- AI rows and thinks --------------------------------------------------------------------------------------------
inline constexpr uint64_t AiMephisto = 0x5b1ca0, AiDiablo = 0x5c8d40, AiBaalCrab = 0x5a8b80;
inline constexpr uint64_t AiOverseer = 0x5c2290;  // row 120's think
inline constexpr uint64_t AiTrapMelee = 0x5b5ca0;  // row 87's think: melee by aip1, else idle aip2
inline constexpr uint64_t AiTrappedSoul = 0x5cfb20;  // row 99's think, read from the table
// Row 71's think, read from the table; its state opens with the same "state 5: idle 0x10" as 1.13c's 0x6fca3fe0
inline constexpr uint64_t AiRegurgitator = 0x5b3040;
// D2R's own hide and unhide, 1.13c D2Game 0x7be10 / 0x89730, as the FrogDemon (monai 52, 0x5afb80) and Vulture (23)
// thinks call them. Hide (game, unit): unit flags 0xe off, the room's collision 0x1000 and 0x100 at the unit cleared,
// path mask 0, think in 12. Unhide (game, unit) -> 0 when the unit has no room to stand: flags 0xe on, the unit placed
// (TeleportUnit), collision 0x100 marked, path mask 0x3c01, think in 12.
inline constexpr uint64_t AiHide = 0x5bae30, AiUnhide = 0x5bafb0;

// --- The think tick and monster AI helpers -------------------------------------------------------------------------
// More of the think's tick (AiTickTarget): +0x24 non-zero in melee range, +0x28 the monstats record, +0x38 uint8
// difficulty (as D2R's Overseer think 0x5c2290 reads them)
inline constexpr int AiTickInMelee = 0x24, AiTickMonStats = 0x28, AiTickDifficulty = 0x38;
// The tick's AI control (tick +0): its three int params at +0x44 (1.13c +0x14, +0x18, +0x1c), as the Regurgitator
// think reads its state at +0x44 and corpse at +0x48
inline constexpr int AiTickControl = 0x0, AiControlParams = 0x44;
// The think's tick block: the target at +0x10 (1.13c +0x08), its distance at +0x20 (1.13c +0x14), as the Mephisto
// think reads them
inline constexpr int AiTickTarget = 0x10, AiTickDistance = 0x20;
// (game, unit, mode, skill, target, x, y, 0) -> non-zero once cast; on failure it idles 10 (0x4a7bc0)
inline constexpr uint64_t AiUseSkill = 0x4a7bc0;
inline constexpr uint64_t AiIdle = 0x4a6d10;      // (game, unit, frames): mode neutral, think again after frames
inline constexpr uint64_t AiSetDelay = 0x4a6e50;  // (game, unit, frames): think again after frames, mode kept
inline constexpr uint64_t AiAttack = 0x4a78e0;    // (game, unit, mode, target): melee in mode 4 (A1) or 5 (A2)
inline constexpr uint64_t AiApproach = 0x4a8740;  // (game, unit, target, 0): walk at the target

// --- Mode commands -------------------------------------------------------------------------------------------------
// The mode command AiIdle sends: (unit, mode, &cmd), cmd +0x10 the unit, then (game, &cmd, 1)
inline constexpr uint64_t ModeCmdInit = 0x4471e0, ModeCmdRun = 0x4475c0;
// mov [rsp+0x20],rbx / push rbp / push rsi / push rdi / sub rsp,0x20 / mov rdi,r8
inline constexpr uint8_t ModeCmdInitEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x20, 0x55, 0x56, 0x57,
                                               0x48, 0x83, 0xec, 0x20, 0x49, 0x8b, 0xf8};
inline constexpr int ModeCmdUnit = 0x10;
inline constexpr int32_t ModeDeath = 0;

}  // namespace d2r::rva
