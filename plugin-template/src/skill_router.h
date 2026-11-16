// A router for server skill "do" functions, and the function signatures of D2R's missile tables (build 93847).
//
// D2R has 191 srvdofunc slots and 172-190 are free (d2r::rva::SrvDoFirstFree). A mod with more new do functions than
// free slots puts ONE function in the last free slot: the router. It looks the skill id up in a table of routes and
// calls the function registered for it, so any number of skills share the slot. In skills.txt a routed skill sets
// srvdofunc to the router's slot (SrvDoSlots - 1 = 190) and the route is registered here by skill id.
//
//   skill_router::Add(MySkillId, SrvDoMySkill);              // before InstallRouter, from the skills part
//   skill_router::InstallRouter(context, report, size);      // writes the router into the last slot
//
// The slot is written with PatchWriteU64 and an expected value of eight zero bytes, so a slot D2R or another plugin
// already uses is refused and reported, never overwritten (rule 6: Bind() first, major.minor version checks only).
// A skill id with no route returns 0 (the cast does not run) and logs a sampled warning.
//
// The missile function types below are D2R's signatures for missiles.txt pSrvDoFunc / pSrvHitFunc / pCltDoFunc /
// pSrvDmgFunc / pCltHitFunc; their tables and free slots are d2r::rva::Missile*Table / *Slots / *FirstFree.
#pragma once

#include "d2r.h"

#include <D2RLPlugin/api.h>

#include <cstddef>
#include <cstdint>

// srvdofunc: non-zero = the skill ran (zero refuses the cast).
using SrvDoFn = int64_t (*)(d2r::Game* game, d2r::Unit* unit, int32_t skillId, int32_t level) noexcept;

// Missile functions (signatures as documented in knowledge/ for build 93847):
using MissileSrvDoFn = int64_t (*)(d2r::Game* game, d2r::Unit* missile) noexcept;
// srvhit: `hit` is null when the missile hit nothing. The return value is the hit result: D2R's collision (0x4639a0)
// deals the missile's damage only when it has bit 2 (srvhit 4 returns 3, or 1 without a missile row; srvhit 12 returns
// 1 or 3), so a function that wants the normal damage returns 3.
using MissileSrvHitFn = int32_t (*)(d2r::Game* game, d2r::Unit* missile, d2r::Unit* hit) noexcept;
// cltdo: the second argument is a float (xmm1 on x64), not an int.
using MissileCltDoFn = void (*)(d2r::Unit* missile, float partFrame) noexcept;
// d2r::Damage is opaque: its layout is not mapped yet.
using MissileSrvDmgFn = void (*)(d2r::Game* game, d2r::Unit* missile, d2r::Unit* target, d2r::Damage* damage) noexcept;
// Zero skips the rest of the client's hit (for example the explosion missile).
using MissileCltHitFn = int32_t (*)(d2r::Unit* missile, d2r::Unit* hit) noexcept;

namespace skill_router {

inline constexpr int MaxRoutes = 64;

// The router's slot: the last srvdofunc slot (190).
inline constexpr int Slot = d2r::rva::SrvDoSlots - 1;

// Routes `skillId` to `function`. False when the table is full, the id is already routed, an argument is invalid, or
// the router is already installed. Call it before InstallRouter, never from a skill function.
auto Add(int32_t skillId, SrvDoFn function) noexcept -> bool;

// The srvdofunc the router's slot holds: picks the route of `skillId`. Exposed for tests.
auto Dispatch(d2r::Game* game, d2r::Unit* unit, int32_t skillId, int32_t level) noexcept -> int64_t;

// Number of routes added.
auto Count() noexcept -> int;

// Writes the router into Slot when at least one route exists. Returns whether it is installed; `report` gets one line.
auto InstallRouter(const D2RL::PluginContext* context, char* report, size_t size) noexcept -> bool;

// Forgets every route. Tests only.
void ResetForTest() noexcept;

}  // namespace skill_router
