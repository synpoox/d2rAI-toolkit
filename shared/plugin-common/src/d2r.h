// The game functions a plugin calls, bound from the per-build header (rvas_93847.h), and helpers to read the game's
// structures. Calling convention: plain Windows x64 (rcx, rdx, r8, r9, then stack). Unit/Game are opaque; read fields
// with At<T>.
//
// Build check: Bind() refuses an image whose PE stamp is not rva::ImageStamp and leaves api null; the plugin then
// leaves every engine part off. The entry bytes every InstallInlineHook checks are the second line of defence.
#pragma once

#include "rvas_93847.h"

#include <cstdint>

namespace d2r {

using GetSkillRecordFn = uint8_t* (*)(uint32_t dataFlag, int32_t skillId) noexcept;
using EvalSkillCalcFn = int32_t (*)(uint32_t dataFlag, Unit* unit, int32_t calc, int32_t skillId, int32_t level) noexcept;
using SkillTargetXYFn = int32_t (*)(Game* game, Unit* unit, int32_t* x, int32_t* y) noexcept;
using SkillTargetUnitFn = Unit* (*)(Game* game, Unit* unit) noexcept;
using CreateMissileFn = Unit* (*)(Game* game, MissileParams* params) noexcept;
using MissileRecordFn = const uint8_t* (*)(uint32_t dataFlag, int32_t missileId) noexcept;
using MissileCountFn = int32_t (*)(uint32_t dataFlag) noexcept;
using UnitSeedFn = uint32_t* (*)(Unit* unit) noexcept;
using SetUnitSkillFlagFn = void (*)(Unit* unit, int32_t on) noexcept;
using ApplyMeleeHitFn = void (*)(Game* game, Unit* attacker, Unit* target, int32_t bonus, int8_t extra) noexcept;
using UnitStatFn = int32_t (*)(Unit* unit, int32_t stat, int32_t param) noexcept;
using UnitStatNoParamFn = int32_t (*)(Unit* unit, int32_t stat) noexcept;
using SummonPetFn = Unit* (*)(Game* game, SummonParams* params) noexcept;
using SetPetLevelFn = int64_t (*)(Game* game, Unit* owner, Unit* pet, int32_t levelOverride, int32_t skillLevel) noexcept;
using PetSkillStatsFn = int64_t (*)(Game* game, Unit* owner, Unit* pet, int32_t skillId, int32_t level, int32_t arg6,
                                    int64_t arg7) noexcept;
using AddPetToPartyFn = void (*)(Game* game, Unit* pet, int32_t zero, int32_t ownerArg) noexcept;
using PickSkillMissileFn = int32_t (*)(Unit* unit, int32_t skillId) noexcept;
using UnitDataFlagFn = uint8_t (*)(Unit* unit) noexcept;
using ClientSkillTargetXYFn = int32_t (*)(Unit* unit, int32_t* x, int32_t* y) noexcept;
using ClientCreateMissileFn = Unit* (*)(MissileParams* params, int32_t zero) noexcept;

// Bound by Bind() from the image base; all null until then and on any other image.
struct Api {
	GetSkillRecordFn getSkillRecord;
	EvalSkillCalcFn evalSkillCalc;
	SkillTargetXYFn skillTargetXY;
	SkillTargetUnitFn skillTargetUnit;
	CreateMissileFn createMissile;
	MissileRecordFn missileRecord;
	MissileCountFn missileCount;
	UnitSeedFn unitSeed;
	SetUnitSkillFlagFn setUnitSkillFlag;
	ApplyMeleeHitFn applyMeleeHit;
	UnitStatFn unitStat;
	UnitStatNoParamFn unitStatNoParam;
	SummonPetFn summonPet;
	SetPetLevelFn setPetLevel;
	PetSkillStatsFn petSkillStats;
	AddPetToPartyFn addPetToParty;
	PickSkillMissileFn pickSkillMissile;
	UnitDataFlagFn unitDataFlag;
	ClientSkillTargetXYFn clientSkillTargetXY;
	ClientCreateMissileFn clientCreateMissile;
};
extern Api api;
// Image base Bind() accepted (0 before that). Engine<Fn>(rva) is for functions only one part calls.
extern uint64_t imageBase;
template <typename Fn>
inline auto Engine(uint64_t offset) noexcept -> Fn {
	return reinterpret_cast<Fn>(imageBase + offset);
}
// Binds api when the image is the one rvas_93847.h describes; false (api left null) on any other image.
auto Bind(uint64_t exeBase) noexcept -> bool;

// --- Helpers ------------------------------------------------------------------------------------------------------
// Read a field of an opaque game structure: At<int32_t>(unit, rva::UnitType).
template <typename T>
inline auto At(const void* p, int offset) noexcept -> T {
	return *reinterpret_cast<const T*>(static_cast<const uint8_t*>(p) + offset);
}

inline auto DataFlag(Game* game) noexcept -> uint32_t {
	return At<uint8_t>(game, rva::GameDataFlag);
}

// A unit's position in subtiles, read the way rva::SkillTargetXY reads it.
inline auto UnitXY(Unit* unit, int32_t* x, int32_t* y) noexcept -> bool {
	const int32_t type = At<int32_t>(unit, rva::UnitType);
	const uint8_t* path = At<const uint8_t*>(unit, rva::UnitPath);
	if (path == nullptr) {
		return false;
	}
	if (type == 2 || type == 4 || type == 5) {
		*x = At<int32_t>(path, 0x10);
		*y = At<int32_t>(path, 0x14);
	} else {
		*x = At<uint16_t>(path, 0x2);
		*y = At<uint16_t>(path, 0x6);
	}
	return true;
}

// Evaluate one of the skill record's calc columns (field = rva::SkCalc1, rva::SkPrgCalc1, ...) for this unit and level.
inline auto EvalCalc(Game* game, Unit* unit, const uint8_t* skill, int field, int32_t skillId, int32_t level) noexcept
	-> int32_t {
	return api.evalSkillCalc(DataFlag(game), unit, At<int32_t>(skill, field), skillId, level);
}

// dataFlag: DataFlag(game) on the server, api.unitDataFlag(unit) on the client.
inline auto ValidMissile(uint32_t dataFlag, int32_t missile) noexcept -> bool {
	return missile >= 0 && missile < api.missileCount(dataFlag);
}

// D2's seed step (the game inlines it): lo' = lo * 0x6ac690c5 + hi, hi' = the carry. Use with api.unitSeed(unit).
inline auto Roll(uint32_t* seed) noexcept -> uint32_t {
	const uint64_t s = static_cast<uint64_t>(seed[0]) * 0x6ac690c5ULL + seed[1];
	seed[0] = static_cast<uint32_t>(s);
	seed[1] = static_cast<uint32_t>(s >> 32);
	return seed[0];
}

// Random number in [0, n) from a D2 seed (0 when n is 0). n takes the whole uint32 range (odds up to 0xffffffff).
inline auto RandomBelow(uint32_t* seed, uint32_t n) noexcept -> uint32_t {
	if (n == 0) {
		return 0;
	}
	const uint32_t v = Roll(seed);
	return (n & (n - 1)) == 0 ? v & (n - 1) : v % n;
}

}  // namespace d2r
