// The game functions a plugin calls, bound from the per-build header (rvas_93847.h), and helpers to read the game's
// structures. Calling convention: plain Windows x64 (rcx, rdx, r8, r9, then stack). Unit/Game are opaque; read fields
// with At<T>.
//
// Two ways to an address (README.md, "Engine addresses by signature"):
//   d2r::sig::<Name>  the signature entry (signatures.h): resolved by Bind() on any image where its code is found, from
//                     the build's cache or by a scan. A part that reads only these lists them in `uses` (parts.h) and
//                     installs on any image where they all resolved.
//   d2r::rva::<Name>  the fixed RVA of build 93847 (rvas_93847.h), for code not moved to entries yet: Bind() returns
//                     true only on that image, and a part without `uses` installs only then.
// api is bound from the entries (a function not found stays null). The entry bytes every InstallInlineHook checks are
// the second line of defence.
#pragma once

#include "rvas_93847.h"
#include "signatures.h"

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace d2r {

struct Damage;  // opaque: the hit's damage block passed to srvdmg functions; its layout is not mapped yet

// --- Structures ---------------------------------------------------------------------------------------------------
// Missile creation parameters for rva::CreateMissile. 1.10's 0x5c-byte block, shifted by 0x10 after the three pointers.
struct MissileParams {
	uint32_t flags;           // 0x00 (seen: 0x820/0x420 caster -> point, 0x21 start at x/y, 1 placed at x/y)
	uint32_t pad04;
	Unit* owner;              // 0x08
	Unit* origin;             // 0x10 (start at this unit's position when x/y are 0)
	Unit* target;             // 0x18
	int32_t missile;          // 0x20 missiles.txt row
	int32_t x, y;             // 0x24 start (0: the origin's position)
	int32_t targetX, targetY; // 0x2c aim point
	int32_t gfxArg;           // 0x34
	int32_t velocity;         // 0x38
	int32_t skill;            // 0x3c
	int32_t skillLevel;       // 0x40
	int32_t loops;            // 0x44
	int32_t unk48;            // 0x48
	int32_t frame;            // 0x4c
	int32_t activateFrame;    // 0x50
	int32_t activation;       // 0x54 frames before the missile starts (skills.txt calc2 in Multiple Shot)
	int32_t pad58;
	int32_t range;            // 0x5c frames the missile lives (Inferno's calc1)
	uint8_t pad60[0x68 - 0x60];
	int32_t sourceKey;        // 0x68 unit state key of the missile a chain starts from (Chain Lightning's srvhit 12)
	int32_t pad6c;
	int32_t callback;         // 0x70 create callback run on the new missile with callbackArg (0: none)
	int32_t callbackArg;      // 0x74 (Firestorm's 1 and DiabWall's 7 take the maker's index and seed it from that)
	uint8_t rest[0xa0 - 0x78];
};
static_assert(sizeof(MissileParams) == 0xa0);
static_assert(offsetof(MissileParams, missile) == 0x20);
static_assert(offsetof(MissileParams, targetX) == 0x2c);
static_assert(offsetof(MissileParams, skill) == 0x3c);
static_assert(offsetof(MissileParams, activation) == 0x54);
static_assert(offsetof(MissileParams, range) == 0x5c);
static_assert(offsetof(MissileParams, sourceKey) == 0x68);
static_assert(offsetof(MissileParams, callback) == 0x70);

// Pet summon parameters for rva::SummonPet (1.10's block with an 8-byte owner pointer).
struct SummonParams {
	uint32_t flags;    // 0x00: 1 = at x/y (else at the owner)
	uint32_t pad04;
	Unit* owner;       // 0x08
	uint16_t monster;  // 0x10 monstats row
	uint16_t pad12;
	int32_t aiState;   // 0x14
	int32_t mode;      // 0x18 monmode
	int32_t x, y;      // 0x1c
	int32_t petType;   // 0x24
	int32_t petMax;    // 0x28
	int32_t pad2c;
};
static_assert(sizeof(SummonParams) == 0x30);
static_assert(offsetof(SummonParams, x) == 0x1c);
static_assert(offsetof(SummonParams, petMax) == 0x28);


// Argument of rva::NewStateList, laid out as Frozen Armor fills it on its stack.
struct StateListRequest {
	Unit* owner;               // 0x00
	Unit* unit;                // 0x08
	int32_t skill;             // 0x10
	int32_t level;             // 0x14
	int32_t frames;            // 0x18 how long the list lasts
	int32_t stat;              // 0x1c a stat the new list gets, -1 none (D2R's open wounds: hpregen)
	int32_t value;             // 0x20 its value, set only on a new list
	int32_t state;             // 0x24
	void (*expired)();         // 0x28 called when the list runs out (rva::SkillStateExpired)
};
static_assert(sizeof(StateListRequest) == 0x30);
static_assert(offsetof(StateListRequest, state) == 0x24);

// rva::AreaUnits: the centre (x, y 0 = the unit's position) and what its callback receives.
struct AreaCenter {
	void* room;  // rva::UnitRoom of the unit
	int32_t x, y;
};
struct AreaContext {
	void* game;
	Unit* unit;
	int64_t count;  // units the callback returned non-zero for
	void* arg;      // AreaUnits' arg
};
static_assert(sizeof(AreaContext) == 0x20);
// The client's (rva::ClientAreaUnits)
struct ClientAreaContext {
	Unit* center;
	int32_t count;  // units the callback returned non-zero for
	void* arg;
};
static_assert(offsetof(ClientAreaContext, arg) == 0x10);

// Argument of rva::CrushingBlowApply, as D2R's event 16 fills it on its stack (0x583223)
struct CrushingBlowArgs {
	void* damage;           // 0x00 the event's damage block
	int32_t divisors[3];    // 0x08 4, 10, 10
	uint8_t missile;        // 0x14 the event is 6 (domissiledamage)
};
static_assert(offsetof(CrushingBlowArgs, divisors) == 0x08);
static_assert(offsetof(CrushingBlowArgs, missile) == 0x14);

// The damage block D2R's Leap (srvdo 77) hands rva::AreaKnockback, filled as it fills it on its stack: hit flags 0,
// result flags 9, an empty inline list at +0x40 (data pointer, size, capacity 16 with the inline bit) and an empty
// tagged pointer at +0x158. The callback copies the block, so it stays as built and needs no cleanup.
struct LeapKnockback {
	uint32_t hitFlags = 0;     // 0x00
	uint32_t resultFlags = 9;  // 0x04
	uint8_t pad08[0x40 - 0x08] {};
	void* listData = inlineList;                          // 0x40
	uint64_t listSize = 0;                                 // 0x48
	uint64_t listCapacity = 0x8000000000000010ull;        // 0x50
	uint8_t inlineList[0xc0] {};                           // 0x58
	uint8_t pad118[0x158 - 0x118] {};
	uint64_t tagged[5] = {1, 0, 0, 0, 0};                  // 0x158
	LeapKnockback() = default;
	LeapKnockback(const LeapKnockback&) = delete;  // listData points into this object
};
static_assert(sizeof(LeapKnockback) == 0x180);
static_assert(offsetof(LeapKnockback, listData) == 0x40);
static_assert(offsetof(LeapKnockback, tagged) == 0x158);
// The same block as a plain hit's damage, for callers that build one
using DamageBlock = LeapKnockback;
// Argument of rva::ApplyCurse, as the curse srvdo (0x5598f0) fills it: aurastat1 travels in the NewStateList
// request, aurastat2-6 are set on the list after it.
struct CurseParams {
	Game* game;           // 0x00
	Unit* caster;         // 0x08
	int32_t pad10[2];     // 0x10 not read here
	int32_t skill;        // 0x18
	int32_t level;        // 0x1c
	int32_t key;          // 0x20
	int32_t frames;       // 0x24
	int32_t stats[6];     // 0x28 aurastat1-6, -1 for none
	int32_t values[6];    // 0x40 their calcs, already worked out
	int32_t state;        // 0x58 aurastate
};
static_assert(offsetof(CurseParams, stats) == 0x28);
static_assert(offsetof(CurseParams, values) == 0x40);
static_assert(offsetof(CurseParams, state) == 0x58);

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

// Bound by Bind() from the entries d2r::sig::<same name>; null until then, and a function whose entry did not resolve.
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
// Image base when it is the image rvas_93847.h describes (0 before Bind() and on any other image). Engine<Fn>(rva) is
// for functions only one part calls.
extern uint64_t imageBase;
template <typename Fn>
inline auto Engine(uint64_t offset) noexcept -> Fn {
	return reinterpret_cast<Fn>(imageBase + offset);
}
// The function a resolved entry found (null when it did not resolve): Engine<Fn>(d2r::sig::GetSkillRecord).
template <typename Fn>
inline auto Engine(const sigscan::Entry& entry) noexcept -> Fn {
	return reinterpret_cast<Fn>(entry.address);
}
// Resolves every d2r::sig entry and binds api from them (on any PE image); true only when the image is the one
// rvas_93847.h describes, the image the fixed rva:: values (and parts without `uses`) need.
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


// Leap Attack's (0x56b170) cleanup of its damage block: the tagged object at +0x158 (bit 0 set: a heap pointer or
// none; clear: an object in place), then the list if it outgrew its inline space (capacity without the inline bit).
inline void ReleaseDamage(LeapKnockback& damage) noexcept {
	const auto release = [](void* p) {
		void* allocator = Engine<void* (*)() noexcept>(rva::EngineAllocator)();
		(*reinterpret_cast<void (***)(void*, void*) noexcept>(allocator))[4](allocator, p);
	};
	const uint64_t tagged = damage.tagged[0];
	void* object = (tagged & 1) != 0 ? reinterpret_cast<void*>(tagged & ~1ull) : &damage.tagged[0];
	if (object != nullptr) {
		(**reinterpret_cast<void (***)(void*, int32_t) noexcept>(object))(object, 0);
		if ((damage.tagged[0] & 1) != 0) {  // read again: the destructor may leave a heap pointer
			release(reinterpret_cast<void*>(damage.tagged[0] & ~1ull));
		}
		damage.tagged[0] = 1;
	}
	if (static_cast<int64_t>(damage.listCapacity) >= 0) {
		release(damage.listData);
	}
}

// Copies a rolled block's plain fields (all but the list at 0x40 and the tagged object at 0x158) into a fresh one:
// ElementalDamage (0x437d00) writes only 0x0c-0x3c and 0x118-0x144, and never the flags.
inline void CopyRolled(const LeapKnockback& from, LeapKnockback& to) noexcept {
	const auto* src = reinterpret_cast<const uint8_t*>(&from);
	auto* dst = reinterpret_cast<uint8_t*>(&to);
	std::memcpy(dst, src, offsetof(LeapKnockback, listData));
	std::memcpy(dst + offsetof(LeapKnockback, pad118), src + offsetof(LeapKnockback, pad118), sizeof(from.pad118));
}

}  // namespace d2r
