// Build 93847: the engine's function tables (the txt "func" columns index them), their sizes and free slots, the
// D2R slots a plugin calls or wraps, and the dispatchers that read them. Part of rvas_93847.h; every RVA here has a
// row in knowledge/d2r-93847-addresses.md.
//
// Write a slot with PatchWriteU64(table + 8 * slot, expected, 8, function): expected 0 for an empty slot, the current
// pointer when wrapping a D2R function.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Skill tables (skills.txt srvdofunc / cltdofunc / srvstfunc / cltstfunc) --------------------------------------
// Server skill "do" functions, indexed by skills.txt srvdofunc: 191 slots of 8-byte pointers. D2R 3.3 fills slots up
// to 171; 172-190 are empty (zero) and free for a mod's own functions. Dispatcher SrvSkillDispatch calls
// int32_t fn(Game*, Unit* caster, int32_t skillId, int32_t level); non-zero is success.
inline constexpr uint64_t SrvDoTable = 0x238ea00;
inline constexpr int SrvDoSlots = 191;
inline constexpr int SrvDoFirstFree = 172;
// Client skill "do" functions, indexed by cltdofunc: 130 slots (bound dword 0x235f7c4); 110-129 are free. Dispatcher
// 0x216d20 calls int32_t fn(Unit* caster, int32_t skillId, int32_t level); non-zero plays the do sound.
inline constexpr uint64_t CltDoTable = 0x235f7d0;
inline constexpr int CltDoSlots = 130;
inline constexpr int CltDoFirstFree = 110;
// Server skill "start" functions (srvstfunc): 91 slots, 71-90 free. Caller 0x43b3e0; 0 from the function aborts the
// cast.
inline constexpr uint64_t SrvStTable = 0x238e710;
inline constexpr int SrvStSlots = 91;
inline constexpr int SrvStFirstFree = 71;
// Client skill "start" functions (cltstfunc): 70 slots (bound dword 0x235f7c0), 62-69 free. Dispatcher 0x218030 calls
// int32_t fn(Unit* caster, int32_t skillId, int32_t level); 0 refuses the cast.
inline constexpr uint64_t CltStTable = 0x235f590;
inline constexpr int CltStSlots = 70;
inline constexpr int CltStFirstFree = 62;
// Server skill dispatcher (D2Game Skills.cpp): (game, unit, skillId, level, a5, a6, a7) -> non-zero ran; reads
// srvdofunc (skills +0x4e), rejects > 0xbe, calls the slot if non-null. Call it; other plugins hook it.
inline constexpr uint64_t SrvSkillDispatch = 0x43acb0;

// D2R's own slots worth calling or wrapping
inline constexpr int SrvStFindPotion = 33, SrvStFindItem = 34;  // Find Potion / Find Item start (server)
inline constexpr int CltStFindPotion = 26, CltStFindItem = 28;  // the same (client)
inline constexpr int SrvDoMelee = 2;         // 0x430240: Bash's do function, applies the queued hit
inline constexpr int SrvDoPoisonDagger = 32; // 0x55cc50: Poison Dagger's do function, applies the queued hit
inline constexpr int SrvDoTeleport = 27;     // 0x554c40: 0 when there is no room, the level forbids it or it collides
inline constexpr int SrvDoInferno = 19;      // 0x554460: Inferno (channelled flame)
inline constexpr int SrvDoNova = 22, CltDoNova = 25;
inline constexpr int SrvDoMaggotEgg = 84, CltDoMaggotEgg = 46;
// Charge: srvst 31 (0x564dc0) aims the charge path, srvdo 67 (0x5622c0) runs it and hits at the end
inline constexpr int SrvStCharge = 31, SrvDoCharge = 67;
// Assassin charge-ups: srvdo 34 (0x570a70) targets, rolls, queues the hit, AddCharge on a hit, applies; 38 / 39
// (0x56ef30, 0x571860) are the later Fists of Fire charges
inline constexpr int SrvDoChargeUp = 34, SrvDoFireCharge1 = 38, SrvDoFireCharge2 = 39;
// srvdofunc 58, Revive: brings the target corpse back in place as the caster's pet. Nothing on that path registers
// the skill's auraevent1-4 on the pet.
inline constexpr int SrvDoRevive = 58;
inline constexpr uint64_t SrvDoReviveD2R = 0x55e7e0;
// srvdofunc 150, Smite (also the monster Smites): builds the hit on its stack, QueueHit, then ApplyMeleeHit
inline constexpr int SrvDoSmite = 150;
inline constexpr uint64_t SrvDoSmiteD2R = 0x564930;
// srvstfunc 66: (game, unit, skill, level) -> 1, registers the skill's auraevent1-4 / auraeventfunc1-4 on the unit for
// good (no stat list, no source), through 0x588670 and 0x438230 per event
inline constexpr uint64_t RegisterSkillEvents = 0x42fa90;

// --- Missile tables (missiles.txt pSrvDoFunc / pSrvHitFunc / pCltDoFunc / pCltHitFunc / pSrvDmgFunc) --------------
// int64_t fn(Game*, Unit* missile): 54 slots, 46-53 free (dispatcher 0x466ce0, record +0x2c)
inline constexpr uint64_t MissileSrvDoTable = 0x2390e80;
inline constexpr int MissileSrvDoSlots = 54;
inline constexpr int MissileSrvDoFirstFree = 46;
// void fn(Game*, Unit* missile, Unit* hit or null): 71 slots (bound 0x2391404), 61-70 free (dispatcher 0x464ac0,
// record +0x2e)
inline constexpr uint64_t MissileSrvHitTable = 0x2391030;
inline constexpr int MissileSrvHitSlots = 71;
inline constexpr int MissileSrvHitFirstFree = 61;
// void fn(Unit* missile, int32_t a2): 92 slots, 78-91 free (called from 0x1ba040, record +0x28)
inline constexpr uint64_t MissileCltDoTable = 0x2358430;
inline constexpr int MissileCltDoSlots = 92;
inline constexpr int MissileCltDoFirstFree = 78;
// int32_t fn(Unit* missile, Unit* hit): 81 slots (dispatcher 0x1b8e60, bound dword 0x2358a64), 66-80 free (and 6, 7 empty
// in the image; a mod's reading also lists 8, 11, 15, 17, 20-23, 27, 35, 45, 49, 58, 59 as empty, not checked here). Zero skips the hit's explosion. Record +0x2a.
inline constexpr uint64_t MissileCltHitTable = 0x2358710;
inline constexpr int MissileCltHitSlots = 81;
inline constexpr int MissileCltHitFirstFree = 66;
// void fn(Game*, Unit* missile, Unit* hit, Damage*): 31 slots, 18-30 free. Called by srvhit 1 (0x45bc40) while it
// builds the hit's damage.
inline constexpr uint64_t MissileSrvDmgTable = 0x2391270;
inline constexpr int MissileSrvDmgSlots = 31;
inline constexpr int MissileSrvDmgFirstFree = 18;
// MissileParams::callback: run by the create (0x3bac90) from this table as fn(missile, callbackArg). 1 is Firestorm's
// (0x3b75c0; srvdo 117 / cltdo 67): frames capped at 77, seed from the arg, a type 10 path.
inline constexpr uint64_t MissileCallbackTable = 0x2381f30;
inline constexpr int MissileCallbackFirestorm = 1;

// --- Events (skills.txt auraeventfunc1-4, itemstatcost event functions) -------------------------------------------
// int32_t fn(Game*, int32_t event, Unit* unit, Unit* target, void* damage, int32_t skill, int32_t level): 41 slots
// (dispatcher 0x43823a, bound 40), all of 1-40 filled. Slot 32 (a skill damage event) is reached by no D2R row.
inline constexpr uint64_t AuraEventTable = 0x238e5c0;
inline constexpr int AuraEventSlots = 41;
inline constexpr int AuraEventUnused = 32;
inline constexpr uint64_t AuraEvent32D2R = 0x42eea0;
// Slot 16 is D2R's crushing blow (item_crushingblow): chance = the stat at (skill >> 16, layer skill & 0xffff), roll %
// 100 on the unit's seed, then CrushingBlowApply (damage.h).
inline constexpr int AuraEventCrushingBlow = 16;
inline constexpr uint64_t AuraEvent16D2R = 0x583150;
inline constexpr int EventDoMeleeDamage = 5;     // events.txt domeleedamage
inline constexpr int EventDoMissileDamage = 6;   // events.txt domissiledamage

// --- Item tables ---------------------------------------------------------------------------------------------------
// properties.txt func1-7: int32_t fn(dataFlag, a1, a2, item, Property*, set, stat, val, first func's result, a8, a9,
// a10), from the property apply 0x3d4620; 37 slots (bound dword 0x2386bd8 = 37), 26-35 null
inline constexpr uint64_t PropertyFuncTable = 0x2386ab0;
inline constexpr int PropertyFuncSlots = 37;
// Item spell table (misc pSpell, read by 0x300ae0): 20 entries of 12 bytes {u32 check, u32 use, u32 keep}. keep 1
// leaves the item after its use (the Cube's entry 7); 0 lets the use-item handler 0x4f40c0 free a non-book. D2R fills
// 0-15; 16-19 are empty; 20+ are ignored. Mark a slot kept with PatchWriteU32(table + 12 * slot + 8, 0 -> 1).
inline constexpr uint64_t ItemSpellTable = 0x236fe30;
inline constexpr int ItemSpellEntrySize = 12;
inline constexpr int ItemSpellSlots = 20, ItemSpellFirstFree = 16;

// --- Object tables -------------------------------------------------------------------------------------------------
// Object operate functions: 75 slots of int32_t fn(ObjectOperate* {game, object, player, seed, id}), indexed by
// objects.txt OperateFn (record +0x15e). The dispatcher 0x592c40 skips a null slot. Slot 60 is null and unused; slot
// 35 is the null slot of the 1.09 Steeg Stone (337), an object no level places. Both are free for a plugin.
inline constexpr uint64_t ObjectOperateTable = 0x23a51c0;
inline constexpr int ObjectOperateSlots = 75;
inline constexpr int ObjectOperateFree60 = 60, ObjectOperateFree35 = 35;
inline constexpr int OperateChest = 4;     // 0x58e2f0, the chests' OperateFn
inline constexpr int OperateWaypoint = 23; // 0x58fe00, the waypoints' OperateFn
// Object init functions: 81 slots, indexed by InitFn (record +0x15c)
inline constexpr uint64_t ObjectInitTable = 0x239b980;

// --- AI table ------------------------------------------------------------------------------------------------------
// D2Game's AI table: one 0x20-byte row per monai row, the think function void fn(Game*, Unit* monster, AiTick*) at +0,
// an int at +0x10, a second function at +0x18. 155 rows. ai.h holds the thinks and the tick layout.
inline constexpr uint64_t AiTable = 0x2396ea0;
inline constexpr int AiRowSize = 0x20;
inline constexpr int AiRows = 155;

}  // namespace d2r::rva
