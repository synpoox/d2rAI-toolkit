// Engine addresses, record offsets and structures for ONE game image: D2R 3.3.0 build 93847 under D2RLoader 1.3.1
// (PE TimeDateStamp 0x6ab3782c; Steam's 94995 is the same image).
//
// One header per D2R build: a new build gets its own rvas_<build>.h and d2r.h includes that one. The values come from
// the Ghidra analysis of the dumped image (tools/dump_image.py, tools/ghidra_analyze.ps1). A different D2R patch or
// D2RLoader release moves them: re-find each one (knowledge/engine-re.md) before writing a new header.
//
// Keep this header to engine facts any mod can use. A value only one project needs stays in that project.
#pragma once

#include <cstddef>
#include <cstdint>

namespace d2r {

struct Game;
struct Unit;

namespace rva {

// PE TimeDateStamp of the image these values belong to. On any other image Bind() binds nothing (build_guard.h).
inline constexpr uint32_t ImageStamp = 0x6ab3782c;

// --- Tables -------------------------------------------------------------------------------------------------------
// Server skill "do" functions, indexed by skills.txt srvdofunc: 191 slots of 8-byte pointers. D2R 3.3 fills slots up
// to 171; 172-190 are empty (zero) and free for a mod's own functions.
inline constexpr uint64_t SrvDoTable = 0x238ea00;
inline constexpr int SrvDoSlots = 191;
inline constexpr int SrvDoFirstFree = 172;

// --- Functions, signature in the comment --------------------------------------------------------------------------
inline constexpr uint64_t GetSkillRecord = 0x97790;    // (dataFlag, skillId) -> skills.txt record or null
inline constexpr uint64_t EvalSkillCalc = 0x3b5160;    // (dataFlag, unit, calc, skillId, level) -> value
inline constexpr uint64_t SkillTargetXY = 0x432b70;    // (game, unit, &x, &y) -> non-zero when the skill has a target point
inline constexpr uint64_t SkillTargetUnit = 0x48fe20;  // (game, unit) -> the skill's target unit or null
inline constexpr uint64_t CreateMissile = 0x5371a0;    // (game, &MissileParams) -> missile unit or null
inline constexpr uint64_t MissileRecord = 0x166040;    // (dataFlag, missileId) -> missiles.txt record or null
inline constexpr uint64_t MissileCount = 0x1b89a0;     // (dataFlag) -> rows in missiles.txt
inline constexpr uint64_t UnitSeed = 0x34a1e0;         // (unit) -> &seed {lo, hi} (D2 RNG, see Roll())
inline constexpr uint64_t SetUnitSkillFlag = 0x34e790; // (unit, on): unit flags (+0x124) bit 0x40, set by do functions
inline constexpr uint64_t ApplyMeleeHit = 0x44b2b0;    // (game, attacker, target, 0, 1): the queued melee hit
inline constexpr uint64_t UnitStat = 0x2f5020;         // (unit, stat, param) -> value (stat with a parameter/layer)
inline constexpr uint64_t UnitStatNoParam = 0x2f5c60;  // (unit, stat) -> value
inline constexpr uint64_t SummonPet = 0x4350e0;        // (game, &SummonParams) -> pet; registers it, enforces petmax
inline constexpr uint64_t SetPetLevel = 0x55fb50;      // (game, owner, pet, 0, skillLevel): pet level from the owner's
inline constexpr uint64_t PetSkillStats = 0x55ef80;    // (game, owner, pet, skill, level, owner+0x12c, 0): the skill's
                                                       // passivestat/aurastat/aurastate on the pet
inline constexpr uint64_t AddPetToParty = 0x58d950;    // (game, pet, 0, owner+0x130)
// (unit, skillId) -> srvmissile a/b/c row by the skill's charges (1, 2, 3+), srvmissilea for a skill with no charges,
// -1 on error (vanilla's charge-missile helper; D2R's srvdo 37 uses it)
inline constexpr uint64_t PickSkillMissile = 0x571700;
inline constexpr uint64_t UnitDataFlag = 0x34a0e0;          // (unit) -> data flag byte; the client's DataFlag
inline constexpr uint64_t ClientSkillTargetXY = 0x214c80;   // (unit, &x, &y) -> non-zero when the skill has a point
inline constexpr uint64_t ClientCreateMissile = 0x1b7760;   // (&MissileParams, 0) -> missile unit or null

// --- Offsets ------------------------------------------------------------------------------------------------------
inline constexpr int GameDataFlag = 0x106;  // Game: byte passed to every data-table getter

inline constexpr int UnitType = 0x00;    // int32: 0 player, 1 monster, 2 object, 3 missile, 4 item, 5 tile
inline constexpr int UnitPath = 0x38;    // dynamic path (x +0x2, y +0x6, uint16) or static path (x +0x10, y +0x14)
inline constexpr int UnitArg12c = 0x12c; // int32 passed by D2R's summon skills to PetSkillStats
inline constexpr int UnitArg130 = 0x130; // int32 passed to AddPetToParty

// skills.txt record (748 bytes in D2R; offsets differ from 1.10/1.13c)
inline constexpr int SkPrgCalc1 = 0x58;       // int32 calc index (pass to EvalCalc)
inline constexpr int SkSrvMissile = 0x66;     // int16 srvmissile
inline constexpr int SkSrvMissileA = 0x68;    // int16 srvmissilea; srvmissileb +0x6a, srvmissilec +0x6c
inline constexpr int SkAuraRangeCalc = 0x84;  // int32 calc index
inline constexpr int SkSummon = 0x110;        // int16 monstats row
inline constexpr int SkPetType = 0x112;       // uint8 pettype row
inline constexpr int SkSumMode = 0x113;       // uint8 monmode, 255 = none
inline constexpr int SkPetMaxCalc = 0x114;    // int32 calc index
inline constexpr int SkCalc1 = 0x190;         // int32 calc index
inline constexpr int SkCalc2 = 0x194;
inline constexpr int SkCalc3 = 0x198;

// --- Client unit tables (data, read by testing/unit_probe.py) -------------------------------------------------------
// 128 buckets of Unit* by unit id & 0x7f, the next unit in a bucket at unit +0x158. Players, monsters, objects and
// items are 0x400 bytes apart from ClientUnits (index by unit type); missiles have their own table. Dead monsters
// stay in the table (mode 0 or 12).
inline constexpr uint64_t ClientUnits = 0x2a23910;
inline constexpr uint64_t ClientMissiles = 0x2a25d10;

}  // namespace rva

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

}  // namespace d2r
