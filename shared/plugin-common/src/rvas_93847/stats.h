// Build 93847: stats, stat lists, states, auras, charges and curses.
// Stat ids are itemstatcost rows.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// The load of the damage reduction cap (stat 36) in the resist getter: where D2R puts 50 (1.09d: 75). 13 bytes, the cap
// at DrCapValueOffset. A plugin that patches it passes these as the expected bytes (see knowledge, "Damage reduction cap").
inline constexpr uint64_t DrCapLoad = 0x4524d0;
inline constexpr uint8_t DrCapLoadExpected[] = {0x41, 0x83, 0x7e, 0x08, 0x24, 0xb8, 0x32, 0x00, 0x00, 0x00, 0x0f, 0x44, 0xc8};
inline constexpr int DrCapValueOffset = 6;

// --- Stats ---------------------------------------------------------------------------------------------------------
inline constexpr uint64_t UnitStat = 0x2f5020;         // (unit, stat, param) -> value (stat with a parameter/layer)
inline constexpr uint64_t UnitStatNoParam = 0x2f5c60;  // (unit, stat) -> value
inline constexpr uint64_t SetUnitStat = 0x2f7d10;  // (unit, stat, value, layer)
inline constexpr uint64_t UnitBaseStat = 0x2f48c0;  // (unit, stat, layer) -> the value on the unit's base list
inline constexpr uint64_t UnitMaxLife = 0x2f4d20;  // (unit) -> max life, 1/256
// (client, unit, 1, stat, value, layer): sends the unit's stat to the client, as the charge use does
inline constexpr uint64_t SendUnitStat = 0x47a190;
// How a charge use (0x4368a0) and the repair (0x46f3be) move an item_charged_skill (204) value, charges | max << 8 at
// layer skill << TablesSkillLayerShift | level:
// (unit, stat, out, max) -> count: the unit's full-stat entries of the stat, 8 bytes each {u16 layer, u16 stat, i32}
inline constexpr uint64_t UnitStatEntries = 0x2f84b0;
// (item, skill, level, &charges, &list) -> non-zero: the item's list that holds the charged skill (a D2RCore jump)
inline constexpr uint64_t ChargedSkillList = 0x3d4950;
inline constexpr uint64_t SetListStatOf = 0x2f7c20;  // (dataFlag, list, stat, value, layer, unit) (a D2RCore jump)
// The server's stat callback, (game, unit, item, stat << 32 | layer (a 64-bit r9), old, new), for stats with
// fCallback: a switch on stats 7-209 only (`lea eax,[r12-7]; cmp eax,0xca` at 0x46ff4a), item_aura (151) at
// 0x470470. Its entry is `jmp [rip+x]`: D2RCore hooks it, so wrap the pointer handed to StatCallbackInit instead.
inline constexpr uint64_t StatCallback = 0x46fdd0;
// (unit, flags, callback, arg): sets up the unit's stat list with its callback (unit creation 0x4252c0, 0x543120).
// mov [rsp+0x10],rbx / mov [rsp+0x18],rsi / mov [rsp+0x20],rdi / push rbp
inline constexpr uint64_t StatCallbackInit = 0x2f65d0;
inline constexpr uint8_t StatCallbackInitEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x10, 0x48, 0x89, 0x74,
                                                    0x24, 0x18, 0x48, 0x89, 0x7c, 0x24, 0x20, 0x55};
inline constexpr int StatMana = 8, StatMaxMana = 9;  // in 1/256
inline constexpr int StatDamagePercent = 25;  // itemstatcost damagepercent
inline constexpr int StatPoisonMin = 57;  // poisonmindam, poisonmaxdam 58, poisonlength 59
inline constexpr int StatPoisonMax = 58;
inline constexpr int StatPoisonLength = 59;
inline constexpr int StatLife = 6;  // itemstatcost hitpoints (current life, in 1/256)
inline constexpr int StatMaxLife = 7;  // maxhp, in 1/256
inline constexpr int StatLightResist = 41;  // lightresist
inline constexpr int StatVelocityPercent = 67;  // itemstatcost velocitypercent
inline constexpr int StatQuantity = 70;
inline constexpr int StatMinDamage = 21, StatMaxDamage = 22;
inline constexpr int StatLightRadius = 89;  // item_lightradius
// Stats Frozen Armor's srvdo 18 sets on its state list (itemstatcost ids)
inline constexpr int StatListSkill = 0x15e;  // 350: the skill that made the list
inline constexpr int StatListLevel = 0x15f;  // 351: its level
inline constexpr int StatListKey = 0xca;     // 202: rva::StateListKey's value

// --- Stat lists ----------------------------------------------------------------------------------------------------
inline constexpr uint64_t NewStatList = 0x2f7300;  // (flags, expire frame, unit type, unit id) -> list or null
// (unit, list, 1). It does not set the list's state bit: UnitHasState read 0 after it in game, and D2R's 0x339d70 calls
// SetStateBit after it. Its body is D2RCore's (jmp [0x3e2a270], filled at runtime).
inline constexpr uint64_t AttachStatList = 0x2f2cb0;
inline constexpr uint64_t DetachStatList = 0x2f7920;
inline constexpr uint64_t FreeStatList = 0x2f4180;
inline constexpr uint64_t UnitStateList = 0x2f5940;  // (unit, state) -> the unit's list of that state, or null
inline constexpr uint64_t UnitListByFlags = 0x2f5a00;  // (unit, state, flags) -> its stat list with those flags, or null
// (unit, state, flags) -> the unit's stat list of that state and flags, or null; (item, 0, 0x40) is the item's magic
// list. List +0x30 entries {int32 layer, stat, value, extra}, +0x38 uint64 count (d2rAI-toolkit runeword-stat-list.md)
inline constexpr uint64_t UnitFlagList = 0x2f5b80;
inline constexpr uint64_t ListStatValue = 0x2f5df0;  // (dataFlag, list, stat, layer) -> value
inline constexpr uint64_t SetListStat = 0x2f7c00;  // (dataFlag, list, stat, value, layer)
inline constexpr uint64_t SetListState = 0x2f72f0;  // (list, state): list +0x20 = state (0x49bef0, 0x339d70 use it)
inline constexpr uint64_t ListSkill = 0x2f56a0;  // (list) -> its skill id
inline constexpr uint64_t ListLevel = 0x2f56e0;  // (list) -> its skill level
inline constexpr uint64_t StatListUnlink = 0x2f8290;       // (unused, unit): its stat list off its parent's
inline constexpr uint64_t StatListLink = 0x2f81a0;         // (parent, unit, 1): its stat list under the parent's
// unit +0x88: its stat list owner (+0x1c < 0 marks one); +0x90 its first chain of lists, the one NewStateList searches
inline constexpr int UnitListOwner = 0x88, ListOwnerMark = 0x1c, ListOwnerFirst = 0x90;
inline constexpr int ListFlags = 0x1c, ListNext = 0x68;  // uint32 flags, next list in the chain
// owner +0xaf0: the unit's state bits (uint32 words, bit state & 31), what UnitHasState (0x2f6220) reads. SetStateGfxFlag
// writes a second array after it, not this one.
inline constexpr int ListOwnerStates = 0xaf0;
inline constexpr uint32_t ListFlagTimed = 0x2, ListFlagCurse = 0x20;
inline constexpr uint32_t ListFlagMagic = 0x40;        // an item's magic stat list (NewStatList flags)
inline constexpr int ListEntries = 0x30, ListCount = 0x38;

// --- States --------------------------------------------------------------------------------------------------------
inline constexpr uint64_t UnitHasState = 0x3351b0;  // (unit, state) -> non-zero while the unit has it
// (unit, state, on): sets or clears the state bit UnitHasState reads (owner +0xaf0, via 0x2f7ea0, which also raises
// the state's SetStateGfxFlag bit when the bit flips), then QueueUnitUpdate. What RemoveSkillState does for each state
// it removes: this with on 0, then the list detached (unit, list) and freed (dataFlag, list). A bare state (no list
// carrying it) is set as D2R's 0x56bfe0 does, this then SetStateGfxFlag, both on 1; D2R's srvst 63 (0x587b50) takes
// its corpse with this alone.
inline constexpr uint64_t SetStateBit = 0x3354c0;
// (unit, state, on): only the state's gfx/update bit, in the second array after owner +0xaf0 (0x2f62d0), then
// QueueUnitUpdate. Not the state: UnitHasState never reads it. Alone it is right only after NewStateList, as D2R's
// 0x553650; a bare state, or a list attached with SetListState + AttachStatList, takes SetStateBit first.
inline constexpr uint64_t SetStateGfxFlag = 0x3355a0;
// Self buff, the way Frozen Armor's srvdo 18 (0x553e60) builds its aurastate list
// (unit, state, self) -> 1 if it removed any: removes every state of the unit in the same states.txt group as
// `state` (the state itself too with self 1). A state with no group (0) removes nothing.
inline constexpr uint64_t RemoveSkillState = 0x4370b0;
// (&StateListRequest) -> stat list or null. An older list of the state with the same skill and level only gets
// its timer moved and is returned as it is; a lower level returns null; any other older list is replaced.
inline constexpr uint64_t NewStateList = 0x433d20;
inline constexpr uint64_t SendSkillState = 0x438470;  // (game, unit, skill, level, key, 1, state, &aurastat, &calc, 4)
inline constexpr uint64_t UnitStateKey = 0x34b6c0;  // (unit) -> value Frozen Armor passes to 0x435920
inline constexpr uint64_t StateListKey = 0x435920;  // (dataFlag, list, key) -> stat 202 value
inline constexpr uint64_t SetUnitStateKey = 0x3e2b652;  // (unit, key): UnitStateKey's setter (a jmp stub)
inline constexpr uint64_t SkillStateExpired = 0x5551f0;  // Frozen Armor's expiry callback: removes the state
inline constexpr int StateCorpseTaken = 118;  // the state srvst 63 puts on the corpse it uses
inline constexpr int StatePlayerBody = 7;  // the durability step sends nothing to a player who has it

// --- Auras, charges and item events --------------------------------------------------------------------------------
inline constexpr uint64_t AddAuraStats = 0x574480;  // (unit, list, skillRecord, skillId, level): aurastat1-6 (attackrate also sets stat 69)
inline constexpr uint64_t AddAuraStatsB = 0x574600;  // same arguments, Frozen Armor calls both
// (game, unit, skill, level, aurastate, aurastat1) -> 1: one charge on the aurastate list (made with stats 350/351
// if none), capped at 3, timer reset to auralencalc; aurastat2 grows by aurastatcalc2. srvdo 34 calls it on a hit.
inline constexpr uint64_t AddCharge = 0x56dae0;
// Release dispatcher (srvdo 1, 42, 46, 50, 52 call it with the queued hit): for each progressive state, n =
// min(max(charges, 1), 3) at max(list level, skill level); with prgstack it calls srvprgfunc1..n-1 first, setting the
// charge stat to i, then srvprgfunc n, all as (game, unit, skill, level), and sends SendChargePacket.
inline constexpr uint64_t SrvPrgDispatch = 0x56c3e0;
// (unit, target, skill, level, seed, 0, charges): the release packet an assassin charge-up skill sends after each hit
inline constexpr uint64_t SendChargePacket = 0x5396d0;
// Unit event 9's handler, (game, unit, key, skill, stateKey): an item aura's tick. Casts the skill at item_aura's
// level for it (stat 151, layer skill) through SrvSkillDispatch (unit flag 0x20000000 and UnitStateKey = stateKey
// around the cast), then re-adds the event perdelay (calc +0x180, at least 5) frames on, on the frame grid; with no
// item_aura level (or a dead unit, or no aurastate) it removes the event. The item_aura case (0x581970) starts it.
// mov [rsp+0x20],rbx / push rbp / push rsi / push rdi / push r12 / push r14 / sub rsp,0x40
inline constexpr uint64_t ItemAuraTick = 0x437230;
inline constexpr uint8_t ItemAuraTickEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x20, 0x55, 0x56, 0x57,
                                                0x41, 0x54, 0x41, 0x56, 0x48, 0x83, 0xec, 0x40};
inline constexpr int UnitEventItemAura = 9;
// int32 masks ItemAuraTick tests the skill record's byte +0x24 with: either set, the aura ticks again
inline constexpr uint64_t SkillTickMaskA = 0x1d996e4, SkillTickMaskB = 0x1d996e8;
inline constexpr uint32_t UnitFlagItemAuraCast = 0x20000000;
// A unit's item event nodes: the head at unit +0xe0; node +0 event, +0xc stat, +0x38 next. The node's function (+0x28) is
// a D2RCore trampoline into D2RCore's own event table.
inline constexpr int UnitEventNodes = 0xe0, EventNodeEvent = 0x0, EventNodeStat = 0xc, EventNodeNext = 0x38;
inline constexpr int UnitEventReplenish = 3;

// --- Curses --------------------------------------------------------------------------------------------------------
// D2Game\src\Skills\SkillNec.cpp: puts one curse on one unit, (target, &CurseParams) -> 1 applied. Every curse
// skill's srvdo reaches it once per target. It calls NewStateList (whose own entry D2RCore hooks), which removes the
// unit's first list flagged ListFlagCurse unless it is this state's, then sets aurastat2-6 on the list.
// mov [rsp+8],rbx / mov [rsp+0x18],rbp / mov [rsp+0x20],rsi / push rdi
inline constexpr uint64_t ApplyCurse = 0x55a7e0;
inline constexpr uint8_t ApplyCurseEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c,
                                              0x24, 0x18, 0x48, 0x89, 0x74, 0x24, 0x20, 0x57};
// (game, target, stat, value) -> value: what ApplyCurse sets for each aurastat (a fifth of a resist cut on an immune)
inline constexpr uint64_t CurseStatValue = 0x55bfb0;
inline constexpr uint64_t StateIsCurse = 0x335a40;  // (dataFlag, state) -> non-zero for a states.txt curse

}  // namespace d2r::rva
