// Monster AI replacement: a registry of think functions by monai row and monstats class, with D2R's own think as the
// fallback. A native table write: no PluginSDK service runs or replaces a monster's AI (data_tables only reads
// monai.txt). D2R calls a monster's think from its monai row in rva::AiTable (build 93847, 155 rows of
// rva::AiRowSize bytes, the think pointer first). A registered row's slot gets one of the trampolines below, which hands
// registered classes to their think and every other monster to the row's D2R think.
//
//   void MyThink(d2r::Game* game, d2r::Unit* unit, uint8_t* tick) noexcept { ... }
//   // from a part's install, after d2r::Bind() succeeded:
//   ai_registry::Register(context, monaiRow, d2r::rva::AiMephisto, monstatsClass, &MyThink);
//   // inside MyThink, for what the think leaves to D2R:
//   ai_registry::Vanilla(monaiRow)(game, unit, tick);
//
// Knowledge: knowledge/d2r-93847-addresses.md (AI table, tick block). Rule 6: Bind() first; the slot write takes D2R's
// think as its expected value, so a slot another plugin changed refuses the write.
#pragma once

#include "d2r.h"

#include <D2RLPlugin/api.h>

#include <cstdint>

namespace ai_registry {

// A think function, D2R's signature: (game, unit, tick). The tick's fields are d2r::rva::AiTick*.
using ThinkFn = void (*)(d2r::Game* game, d2r::Unit* unit, uint8_t* tick) noexcept;

inline constexpr int MaxRows = 10;     // monai rows one plugin can take over
inline constexpr int MaxClasses = 8;   // classes per row

// Runs `think` instead of D2R's think of monai row `monaiRow` for monsters of monstats class `classId`; other classes on
// the row keep D2R's think. `d2rThink` is the rva of D2R's think in that row (rva::AiMephisto, ...): the first
// registration on a row writes the row's slot with PatchWriteU64, using it as the expected value. Call it from a part's
// install, never from a think. False when the row is out of range, `think` is null, the slot is not `d2rThink`, or the
// registry is full.
auto Register(const D2RL::PluginContext* context, int32_t monaiRow, uint64_t d2rThink, int32_t classId,
              ThinkFn think) noexcept -> bool;

// D2R's own think of a registered row (null for any other row): a registered think calls it for what it leaves to D2R.
auto Vanilla(int32_t monaiRow) noexcept -> ThinkFn;

// The same as Register with the slot write and D2R's think passed in, so a test needs no game:
// `write(slotRva, expectedThinkRva, trampoline, user)` returns whether the slot took it; `vanilla` is D2R's think.
using SlotWriter = bool (*)(uint64_t slotRva, uint64_t expectedRva, ThinkFn trampoline, void* user) noexcept;
auto RegisterWith(SlotWriter write, void* user, int32_t monaiRow, uint64_t d2rThink, ThinkFn vanilla, int32_t classId,
                  ThinkFn think) noexcept -> bool;

// What a registered row's trampoline does (row index k in registration order): the registered think of the unit's class,
// else D2R's. Exposed for tests.
void Dispatch(int k, d2r::Game* game, d2r::Unit* unit, uint8_t* tick) noexcept;

// Forgets every registration. Tests only: the slots are not put back.
void ResetForTest() noexcept;

}  // namespace ai_registry
