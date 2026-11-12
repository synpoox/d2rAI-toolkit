// Build 93847: hits and damage: the queued melee hit, the damage pipeline, area hits, elemental damage and the
// damage block layout.
// Offsets of the damage block are bytes into the block QueuedHit returns.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Hit queue and melee hit ---------------------------------------------------------------------------------------
// (game, attacker, target, &damage, flag): queues a hit in the attacker's list (+0x108, QueuedHit reads it); a hit
// that landed is result & 1 with none of 0x8380
inline constexpr uint64_t QueueHit = 0x44b600;
// mov [rsp+0x20],rbx / push rbp / push rsi / push r14 / sub rsp,0x30 / mov rbx,r9
inline constexpr uint8_t QueueHitEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x20, 0x55, 0x56, 0x41,
                                            0x56, 0x48, 0x83, 0xec, 0x30, 0x49, 0x8b, 0xd9};
inline constexpr uint64_t ApplyMeleeHit = 0x44b2b0;    // (game, attacker, target, 0, 1): the queued melee hit
// (attacker, defender) -> the damage block of the attacker's queued hit on defender (unit +0x108 list), or null
inline constexpr uint64_t QueuedHit = 0x44d660;
// (game, attacker, defender, &damage, 0, srcdam): weapon damage scaled by srcdam / 128 (0 = 128), as a melee hit with a
// skill's SrcDam builds it
inline constexpr uint64_t WeaponDamage = 0x44c030;
// (game, &block, unit, target, skill, level): the hit's damage for a kick, into a damage block with DmgPercent set;
// D2R's srvdo 52 (0x56fc80) fills its kick with this after the roll (MeleeRoll)
inline constexpr uint64_t MeleeFill = 0x573af0;
// (game, unit, target, toHit, flag, 0) -> result flags (bit 0 hit); flag = skill byte SkRollFlags & the byte at
// MeleeRollFlagMask
inline constexpr uint64_t MeleeRoll = 0x44b720;
inline constexpr uint64_t MeleeRollFlagMask = 0x1d996d0;
inline constexpr uint64_t SkillToHit = 0x339040;  // (unit, skillId, level) -> attack rating for the roll
inline constexpr uint64_t UnitHitClass = 0x3495d0;  // (unit) -> the value Leap Attack puts at DmgHitClass
// (dataFlag, unit, skillId, level, 0) -> the skill's own physical min / max in 1/256 (MinDam/MaxDam with MinLevDam...;
// a kick's from strength and dexterity), the pair MeleeFill reads; 1.13c's D2Game 0x9f1a0 adds min + rand(max - min)
// to the hit's physical damage
inline constexpr uint64_t SkillPhysMin = 0x3385b0;
inline constexpr uint64_t SkillPhysMax = 0x338160;

// --- Damage pipeline -----------------------------------------------------------------------------------------------
// D2R's area apply 0x436e90 (game, attacker, victim, &damage), which AreaKnockback's callback 0x43a740 calls, in steps:
inline constexpr uint64_t AvoidRoll = 0x44b930;  // (game, attacker, victim, 1, 0) -> 1 avoided, 2/4/0x10 block kinds
inline constexpr uint64_t DamageStep = 0x5889e0;  // (attacker, victim, &damage)
inline constexpr uint64_t DamageEffects = 0x44df10;  // (game, attacker, victim, &damage): 0x44ce80 runs it for area hits
// (game, attacker, victim, area, &damage): with area 0, events 5 domeleedamage (attacker) and 1 (victim), as a melee
// hit's 0x44b2b0 calls it; with area 1, events 6 domissiledamage and 2
inline constexpr uint64_t HitEvents = 0x44ce80;
inline constexpr uint64_t DealDamage = 0x44a9b0;  // (game, attacker, victim, &damage)
// The unit event dispatcher 0x5881e0, (game, event, unit, target, damage, list), is jmp [here]: D2RCore's. The hit
// (0x44ce80) raises domeleedamage (5) / domissiledamage (6) on the attacker through 0x44d570 before the damage lands.
inline constexpr uint64_t EventDispatchSlot = 0x3e2a420;
// DamageEffects (0x44df10) runs its 12 damage types (1.13c's table, 0x40 bytes each here) through (&ctx, &type, flag),
// called as jmp [this slot]: D2RCore's resist step (1.13c's 0x6fcfbd00).
inline constexpr uint64_t DamageTypeStepSlot = 0x3e2aab0;
inline constexpr int StepGame = 0x00, StepVictim = 0x18;  // ctx: Game*, the difficulty record, attacker, victim
// type: +0 the int32* damage field; +0x28 int32 non-zero on the 9 types 1.13c flags (physical, fire, lightning, cold,
// magic, poison and the three leeches; not the cold, freeze and poison lengths)
inline constexpr int TypeField = 0x00, TypeMirrored = 0x28;
// (attacker, victim, rate, length, a5, a6, a7): poison, stat 74 (hpregen) at -rate for length frames. Its entry tests
// the length (test r9d,r9d / jle, relative); a hook sits past it, at PoisonApplyHook, with the arguments still in
// place: mov rax,rsp / push rbp / push rsi / push r14 / push r15 / sub rsp,0x68 / mov r14d,r9d
inline constexpr uint64_t PoisonApply = 0x4518c0, PoisonApplyHook = 0x4518c9;
inline constexpr uint8_t PoisonApplyHookEntry[] = {0x48, 0x8b, 0xc4, 0x55, 0x56, 0x41, 0x56, 0x41,
                                                   0x57, 0x48, 0x83, 0xec, 0x68, 0x45, 0x8b, 0xf1};
// (unit, amount) -> life added: life + amount up to the max, unless the unit is dead or has state 92. Callers: the life
// leech 0x450c90 (attacker) and the hit's absorb heal in 0x44ce80 (victim).
// mov [rsp+0x18],rbx / push rsi / sub rsp,0x20 / mov esi,edx / mov rbx,rcx
inline constexpr uint64_t AddLife = 0x451820;
inline constexpr uint8_t AddLifeEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x18, 0x56, 0x48, 0x83,
                                           0xec, 0x20, 0x8b, 0xf2, 0x48, 0x8b, 0xd9};
// (game, attacker, target, &damage): the life and mana leech of a hit. It shifts the life and mana steal percents
// (DamageLifeLeech, DamageManaLeech) << 6 (1/64 fixed point) and, for a player attacker, divides them by the difficulty's
// LifeStealDivisor / ManaStealDivisor (DiffLifeDivisor / DiffManaDivisor); 1.09d divides on a monster target instead.
// A pet's leech is asked with IsPet (units.h). Drain (MonDrain) 0 on a monster target ends it early. Its caller 0x44ce80
// drains the target's mana by damage +0x124 and stamina by +0x128 afterwards.
// push rbp / push rsi / push rdi / push r14 / sub rsp,0x58 / cmp dword [r9+0x120],0
inline constexpr uint64_t Leech = 0x450c90;
inline constexpr uint8_t LeechEntry[] = {0x40, 0x55, 0x56, 0x57, 0x41, 0x56, 0x48, 0x83, 0xec,
                                         0x58, 0x41, 0x83, 0xb9, 0x20, 0x01, 0x00, 0x00, 0x00};
inline constexpr int DmgFlags = 0x00;                 // uint32 hit flags
inline constexpr uint32_t DmgFlagElementsLeech = 0x40;  // the elements count in the leeched damage, as the physical does

// --- Area hits -----------------------------------------------------------------------------------------------------
// (game, unit, &AreaCenter, radius, unit mask, callback, arg, 0): callback(&AreaContext, victim) for each unit in range
inline constexpr uint64_t AreaUnits = 0x4398b0;
inline constexpr uint32_t AreaUnitMask = 0x8583;  // the default unit mask of an area hit and of AreaKnockback
// (game, unit, 0, 0, radius, &LeapKnockback, 0, &scratch): Leap's landing knockback (srvdo 77), callback 0x43a740
inline constexpr uint64_t AreaKnockback = 0x437820;
// The whole area apply: the steps AvoidRoll, DamageStep, DamageEffects and DealDamage in order, with events 6
// domissiledamage and 2 (1.13c's 0x10305760 is the same function). AreaKnockback's callback 0x43a740 calls it.
inline constexpr uint64_t AreaApply = 0x436e90;  // (game, attacker, victim, &damage)
// Client: (center unit, x, y, radius, unit mask, callback, arg, 0): callback(&ClientAreaContext, unit) for each unit
// in range; x/y 0 = the center unit's position, radius 0 does nothing (Fist of the Heavens' clthit 26 0x1adcb0)
inline constexpr uint64_t ClientAreaUnits = 0x2142d0;
// srvhit 9's (Immolation Arrow, 0x45d020) helpers: (game, missile, radius, missile row, frames) creates the row at every
// open spot within radius of the missile (frames 0 = the row's own range), and (game, missile, hit, &block) fills the
// missile's damage into a d2r::LeapKnockback block
inline constexpr uint64_t MissileFireDisc = 0x462b20;
inline constexpr uint64_t MissileDamageFill = 0x465d60;

// --- Elemental damage and skill conversion -------------------------------------------------------------------------
// (unit, &damage, skillId, level): adds the skill's elemental damage to a zeroed damage block (poison +0x38 = min +
// rand(max - min), length +0x3c). D2R's melee start (srvst 32, 0x567070) fills the queued hit with it.
inline constexpr uint64_t ElementalDamage = 0x437d00;
// (dataFlag, unit, skillId, level, 1) -> ELen with ELevLen, the length ElementalDamage gives cold and poison
inline constexpr uint64_t ElementalLength = 0x337da0;
// (unit, &damage, etype, amount, length, &resist stat or null, &etype or null): adds amount to the etype's field
// (2 lightning: +0x2c, hit class +0x144 = 0x40; resist stat 41)
inline constexpr uint64_t AddElementDamage = 0x437980;
inline constexpr int DamageFlag148 = 0x148;   // uint8 D2R's Static Field sets to 1
// Conversion D2R's melee start (srvst 32, 0x567070) sets from a skill with an EType: type and percent (calc4), 1.13c's
// 0x65 / 0x68
inline constexpr int DmgConvType = 0x149;
inline constexpr int DmgConvPct = 0x14c;
// (dataFlag, difficulty) -> difficultylevels.txt record (0x84 bytes); StaticFieldMin at +0x68. Static Field (srvdo 20
// 0x5546b0, per unit 0x5556a0) builds its hit from it.
inline constexpr uint64_t DifficultyRecord = 0x300830;
inline constexpr int DiffStaticFieldMin = 0x68;
inline constexpr int DiffLifeDivisor = 0x1c, DiffManaDivisor = 0x20;  // int32 LifeStealDivisor, ManaStealDivisor

// --- Critical and deadly strike, crushing blow ---------------------------------------------------------------------
// WeaponDamage's (0x44c030) roll: from 0x44c2b4, right after the physical roll is stored at damage +0x18, to 0x44c3d9
// it rolls the weapon mastery's crit (when a5 is 0), passive_critical_strike, then deadly strike, and doubles the
// physical part with result flag 0x2000. Attacker in RSI, damage block in RDI, a5 in R14D; 0x44c3d9 needs R15D 0.
// The 28 bytes of the block: test r14d,r14d / jnz / mov rcx,rsi / call UnitWeapon / test / jz / lea r9d,[r14+2] /
// xor r8d,r8d / mov rdx,rax (nothing outside jumps into them).
inline constexpr uint64_t WeaponCritBlock = 0x44c2b4;
inline constexpr uint64_t WeaponCritBlockEnd = 0x44c3d9;
inline constexpr uint8_t WeaponCritBlockBytes[] = {0x45, 0x85, 0xf6, 0x75, 0x67, 0x48, 0x8b, 0xce, 0xe8, 0xef,
                                                   0x7f, 0xfd, 0xff, 0x48, 0x85, 0xc0, 0x74, 0x5a, 0x45, 0x8d,
                                                   0x4e, 0x02, 0x45, 0x33, 0xc0, 0x48, 0x8b, 0xd0};
// (unit, weapon) -> bool: a missile's crit or deadly strike, rolled by the missile fill 0x3bf9b0 (D2Common Missile.cpp)
// and the server's 0x432f90 / 0x4333f0; a hit doubles the physical part of a missile that carries it.
// mov [rsp+8],rbx / mov [rsp+0x10],rsi / push rdi / sub rsp,0x20
inline constexpr uint64_t MissileCritRoll = 0x3ba820;
inline constexpr uint8_t MissileCritRollEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x74,
                                                   0x24, 0x10, 0x57, 0x48, 0x83, 0xec, 0x20};
// (unit, weapon, 0, kind) -> the weapon mastery's bonus; kind 2 is the crit chance (D2RCore jumps it at its entry)
inline constexpr uint64_t MasteryBonus = 0x33d4f0;
// (game, unit, target, &CrushingBlowArgs) -> the event's result; called by D2R's event 16 after its roll
inline constexpr uint64_t CrushingBlowApply = 0x581bd0;
// CrushingBlowApply's entry is jmp [rip+0x38a8872]: the qword it jumps through, which a plugin can swap
inline constexpr uint64_t CrushingBlowApplySlot = 0x3e2a448;

// --- Damage block layout (what QueuedHit returns and a pSrvDmgFunc edits) ------------------------------------------
// Damage block QueuedHit returns: +0 hit flags (uint32), +4 result flags (uint16)
inline constexpr int DamageResult = 0x4;
inline constexpr uint16_t ResultHit = 0x1;
inline constexpr uint16_t ResultKnockback = 0x8;
inline constexpr uint16_t ResultAvoided = 0x8380;  // QueueHit's "did not land" bits
// Damage block a pSrvDmgFunc edits: 1.13c's 0x08-0x2c fields sit 0x10 later (phys 0x08 -> 0x18 in srvdmg 1 and 13,
// poison length 0x2c -> 0x3c in srvdmg 11).
inline constexpr int DmgPhys = 0x18, DmgFire = 0x20, DmgLight = 0x2c, DmgMagic = 0x30, DmgCold = 0x34, DmgPoison = 0x38;
inline constexpr int DmgPoisonLength = 0x3c;
inline constexpr int DmgPercent = 0x1c;  // damage% (1.13c 0x0c), set before the melee fill (D2R's srvdo 52)
inline constexpr int DmgColdLength = 0x118;  // ElementalDamage's cold length (1.13c's 0x30)
// int32 the hit's total, 1.13c's 0x4c: DamageEffects (0x44df10) sets it to the sum of the fields after resists, and
// DealDamage (0x44a9b0) reads it
inline constexpr int DmgTotal = 0x134;
inline constexpr int DmgHitClass = 0x144;    // int32 Leap Attack's hit sets from UnitHitClass
// Leeches in the same damage block (built by 0x465d60)
inline constexpr int DamageLifeLeech = 0x120;  // mana leech +0x124, stamina leech +0x128
inline constexpr int DamageManaLeech = 0x124;
inline constexpr int DamageStaminaLeech = 0x128;

}  // namespace d2r::rva
