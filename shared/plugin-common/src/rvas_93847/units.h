// Build 93847: skills, missiles, paths, units, pets and monster spawning.
// Call a function through d2r::Engine<Fn>(rva) or the d2r::api table (d2r.h).
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Skills --------------------------------------------------------------------------------------------------------
// --- Functions, signature in the comment --------------------------------------------------------------------------
inline constexpr uint64_t GetSkillRecord = 0x97790;    // (dataFlag, skillId) -> skills.txt record or null
inline constexpr uint64_t EvalSkillCalc = 0x3b5160;    // (dataFlag, unit, calc, skillId, level) -> value
inline constexpr uint64_t SkillTargetXY = 0x432b70;    // (game, unit, &x, &y) -> non-zero when the skill has a target point
inline constexpr uint64_t SkillTargetUnit = 0x48fe20;  // (game, unit) -> the skill's target unit or null
inline constexpr uint64_t ClientSkillTargetXY = 0x214c80;   // (unit, &x, &y) -> non-zero when the skill has a point
inline constexpr uint64_t ClientSkillTargetUnit = 0x9a570;  // (unit) -> target unit (client)
// (unit, skillId) -> srvmissile a/b/c row by the skill's charges (1, 2, 3+), srvmissilea for a skill with no charges,
// -1 on error (vanilla's charge-missile helper; D2R's srvdo 37 uses it)
inline constexpr uint64_t PickSkillMissile = 0x571700;
inline constexpr uint64_t SetUnitSkillFlag = 0x34e790; // (unit, on): unit flags (+0x124) bit 0x40, set by do functions
// Leap, the way D2R's Leap (srvdo 77 0x568690, cltdo 43 0x22f9a0) and Leap Attack (srvdo 78 0x568920) run it
inline constexpr uint64_t GetUnitSkill = 0x33dd40;  // (unit, skillId, 0) -> the unit's skill (flags +0x14) or null
inline constexpr uint64_t UnitSkillId = 0x33e080;  // (unitSkill, file, line) -> skills.txt id
inline constexpr uint64_t UnitSkillLevel = 0x33d1e0;  // (unit, unitSkill, bonus) -> level; bonus 0 = hard points
// The current unit skill of a unit: (unit) -> the unit skill it is using, or null. D2R's Inferno (srvdo 19 0x554460 ->
// 0x551730, cltdo 24 0x2203f0) and Nest (srvst 49) keep their channel and spawn data on it.
inline constexpr uint64_t CurrentSkill = 0x34ba40;
inline constexpr uint64_t LeapStart = 0x33e380;  // (unit, unitSkill) -> non-zero: leap path to the skill's point, type 9
inline constexpr uint64_t LeapLanded = 0x56b5e0;  // (game, unit, unitSkill) -> non-zero once the unit has landed
inline constexpr uint64_t SkillMeleeHit = 0x56b170;  // (game, unit, skillId, level): Leap Attack's hit on the skill target
inline constexpr uint64_t CltDoLeap = 0x22f9a0;  // D2R cltdo 43 (unit, skillId): Leap's client half
// Power Strike's client do function (cltdo 22, 1.13c D2Client 0x15660) draws the strike only for the local player:
// `je` at this address skips its early return.
inline constexpr uint64_t CltDoStrikeLocalOnly = 0x2aed4a;
// (unit, skill, level, target, 0) -> non-zero cast: a skill cast from unit at target as an event, sent to clients (aura
// event 33 0x42f300 casts this way); refuses while the unit has state 54
inline constexpr uint64_t CastEventSkill = 0x5896e0;

// --- Missiles ------------------------------------------------------------------------------------------------------
inline constexpr uint64_t CreateMissile = 0x5371a0;    // (game, &MissileParams) -> missile unit or null
inline constexpr uint64_t ClientCreateMissile = 0x1b7760;   // (&MissileParams, 0) -> missile unit or null
inline constexpr uint64_t MissileRecord = 0x166040;    // (dataFlag, missileId) -> missiles.txt record or null
inline constexpr uint64_t MissileCount = 0x1b89a0;     // (dataFlag) -> rows in missiles.txt
// Missiles (srvhit 4 is Exploding Arrow's hit, srvdo 7 / cltdo 7 Guided Arrow's homing, srvdo 1 / cltdo 1 the default)
inline constexpr uint64_t SrvHitSubMissiles = 0x45ddb0;  // srvhit 4 (game, missile, hit): HitSubMissile1-4 at the missile
inline constexpr uint64_t MissileSrvDoDefault = 0x463100;  // srvdo 1 (game, missile): move, collide, count down range
inline constexpr uint64_t MissileSrvEnd = 0x4639a0;  // (game, missile, hit, 1): what srvdo 1 does when range runs out
inline constexpr uint64_t MissileCltDoDefault = 0x1b5380;  // cltdo 1 (missile, float part-frame)
inline constexpr uint64_t MissileOwner = 0x490300;  // (game, missile) -> owner unit or null
inline constexpr uint64_t ClientMissileOwner = 0x9a7b0;  // (missile) -> owner unit or null
inline constexpr uint64_t MissileSrvFrames = 0x3bb1e0;  // (missile) -> range frames left (server)
// (missile) -> frames run: the range minus MissileSrvFrames' frames left, 1 on the first step (D2R's cltdo 1 tests 1;
// 1.13c's cdo 69 the same as current == total - 1, D2Common #10737 / #10534)
inline constexpr uint64_t MissileCltFrames = 0x3bb0f0;
// (dataFlag, missile, owner, calc, -1, -1) -> value; dmg 1 0x453490 evaluates DmgCalc1 this way
inline constexpr uint64_t EvalMissileCalc = 0x3b4a90;
// The client's 3D offset and motion of a missile's graphic, as D2R's Meteor (cltdo 9, 0x1b6480) sets them (1.13c's
// D2Client 0xc7e30 and its writes to gfx +0x30 +0x10..0x18): (missile, x, y, z) << 11; (missile, x, y, z, shift),
// shift 0 stores the values as given (1.13c's raw writes), else << 11.
inline constexpr uint64_t SetMissileOffset = 0x193a80;
inline constexpr uint64_t SetMissileMotion = 0x193ad0;
// (game, missile, unit, skill, level, UnitStateKey(unit), 0, 0, 0, 0, 1) -> missile thrown at the skill's target
inline constexpr uint64_t ThrowSkillMissile = 0x4333f0;
inline constexpr uint64_t ClientThrowSkillMissile = 0x213f50;  // (unit, missile, skill, level, UnitStateKey(unit))
inline constexpr uint64_t MissileBounces = 0x3bc0a0;  // (missile) -> chain count left (Chain Lightning's)
inline constexpr uint64_t SetMissileBounces = 0x3bd8a0;  // (missile, count); srvdo 139 sets it to uy - ty
inline constexpr uint64_t SetMissileTargetDx = 0x3bda20;  // (missile, tx - ux), set by srvdo 139 (0x585440)
inline constexpr uint64_t MissileSkill = 0x3bc450;  // (missile) -> skill id
inline constexpr uint64_t MissileLevel = 0x3bb470;  // (missile) -> skill level
inline constexpr uint64_t MissileActivateFrame = 0x3bae80;  // (missile) -> 1.13c's data +0x08 (D2R +0x0a)
inline constexpr uint64_t SetMissileFramesLeft = 0x3bd450;  // (missile, frames): what MissileSrvFrames reads
// (missile, MsAnimSpeed << 8 / range): cltdo 24 calls it on each flame it draws
inline constexpr uint64_t SetMissileAnimRange = 0x34da60;
inline constexpr uint64_t MissileTargetType = 0x3bc190;  // (missile) -> target unit type, 6 for none
inline constexpr uint64_t MissileTargetId = 0x3bc280;  // (missile) -> target unit id
// MissileParams::flags
inline constexpr uint32_t MissileFromOrigin = 0x820;      // start at the origin unit, fly to targetX/targetY
inline constexpr uint32_t MissileChannel = 0x8020;  // D2R's Inferno (srvdo 19, cltdo 24)
inline constexpr uint32_t MissileNotTriggering = 0x20000;  // Multiple Shot's outer missiles, the ones calc3 leaves out
inline constexpr uint32_t MissileAtXY = 0x1;  // start at x/y
inline constexpr uint32_t MissileAimOffset = 0x2;  // targetX/targetY are offsets from the start (Nova's srvhit 5)
// A charge spread sets it; CreateMissile hands it, with params +0x64, to the missile's setup 0x3bf9b0
inline constexpr uint32_t MissileFlag10000 = 0x10000;

// --- Paths and movement --------------------------------------------------------------------------------------------
inline constexpr uint64_t PathSetTargetUnit = 0x342920;  // (path, unit): path +0x70 target unit
inline constexpr uint64_t PathSetTargetXY = 0x342a50;  // (path, x, y): path +0x10/+0x12 target point; clears +0x70
// (path, mask): path +0x64, what the path collides with (1.13c D2Common #11164, +0x50); missile create 0x5371a0 sets it
// from CollideType's row of the mask table 0x2391378 (CollideType 3: 0x184)
inline constexpr uint64_t PathSetCollisionMask = 0x342740;
inline constexpr uint64_t PathSteer = 0x340e70;  // (path, unit, 0, 1): re-aim the path at its target unit
inline constexpr uint64_t PathSetVelocity = 0x342ae0;  // (path, velocity): ignored while the skill has flag 0x1000
inline constexpr uint64_t UnitDistance = 0x324fc0;  // (a, b) -> distance in subtiles
inline constexpr uint64_t UnitSize = 0x34b580;  // (unit) -> collision size: a missile's row Size, 2 for a player
// (room, x, y, mask) -> the mask's bits set at subtile x/y (0x27 with no room there), 1.13c's single-point test
inline constexpr uint64_t CollisionAt = 0x366250;
// int32[64] x and y offsets of D2's 64 directions (radius 30), the ones Nova's srvhit 5 (0x45fd20) aims at
inline constexpr uint64_t DirectionX = 0x1d1b650;
inline constexpr uint64_t DirectionY = 0x1d1b750;
// (game, owner, x, y, range, flags, skip unit id, 0) -> nearest target to x/y other than the skipped unit, or null
inline constexpr uint64_t NearestTarget = 0x4331d0;
inline constexpr uint32_t NearestTargetFlags = 0x8a783;  // Chain Lightning's search: 0x88583 | the 0xa783 the search adds

// --- Units ---------------------------------------------------------------------------------------------------------
inline constexpr uint64_t UnitSeed = 0x34a1e0;         // (unit) -> &seed {lo, hi} (D2 RNG, see Roll())
inline constexpr uint64_t UnitDataFlag = 0x34a0e0;          // (unit) -> data flag byte; the client's DataFlag
inline constexpr uint64_t UnitPackedXY = 0x34a110;               // (unit) -> uint32: x low 16 bits, y high 16
// What OpenRedPortal does first, to find the portal's spot: the unit's (x, y), then a search around it, (game,
// room, int xy[2] in/out, 3, 0x400, room** found, 5, 100); *found stays null when there is no free spot. Reads only.
inline constexpr uint64_t UnitCoords = 0x34a040;  // (unit, int32 xy[2])
inline constexpr uint64_t UnitId = 0x34a330;  // (unit, file, line) -> unit id
inline constexpr uint64_t UnitClassOf = 0x349860;  // (unit, file, line) -> class id (the dispatchers' item row)
inline constexpr uint64_t UnitModeOf = 0x34ab60;  // (unit) -> u32; the leech passes it as the third value of Disguise
// (unit, uint32* type, int32* class, uint32* mode): the unit's disguise form. It reads the unit's states against a table of
// 0x44-byte records (+0x2d: 1 monster, 2 player; +0x2e: the class) and rewrites type, class and mode when one matches.
inline constexpr uint64_t Disguise = 0x33a1f0;
inline constexpr uint64_t UnitRoom = 0x34b440;  // (unit) -> its room
// Double Throw (D2R's own srvdo 74 0x567a20, cltdo 42 0x22f3f0, Chain Lightning's srvhit 12 0x45d5e0)
inline constexpr uint64_t UnitWeapon = 0x4242b0;  // (unit) -> weapon item the server attacks with, or null
inline constexpr uint64_t ClientUnitWeapon = 0x34b000;  // (unit) -> the client's weapon item, or null
// What D2R's Charge hit (srvdo 67) asks before it strikes
inline constexpr uint64_t FindUnit = 0x48fe80;     // (game, unit type, id) -> unit or null
inline constexpr uint64_t UnitInReach = 0x348650;  // (unit, target, reach, 0) -> non-zero when in reach
inline constexpr uint64_t UnitReach = 0x34aa90;    // (unit) -> 1 for a player, 3 for a monster
inline constexpr uint64_t UnitDead = 0x34c2c0;     // (unit) -> non-zero when dying or dead
// (unit) -> alignment: stat 172 for players and monsters (0 hostile, 1 neutral, 2 ally; pets 2), 2 for other types.
// 1.13c's D2Common #10830. D2RLoader hooks its entry: call it, never hook it.
inline constexpr uint64_t UnitAlignment = 0x2f4190;
// (unit, overlay, layer): overlay.txt row as stat 0xb2 on the given layer; 1.13c's D2Common #10689 has no layer (0).
// Asserts on a row past the table, so check DataTables + TablesOverlayCount first, as Leap Attack (0x56b170) does.
inline constexpr uint64_t SetOverlay = 0x349020;
inline constexpr uint64_t SetUnitFlag = 0x34e140;  // (unit, flag, on)
// (unit, flags, on): unit flags +0x124 (bit 0x10000 is dead, see UnitDead); 0x20000 is 1.13c's no-treasure-class bit
inline constexpr uint64_t SetUnitFlags = 0x34e190;
// (game, unit, room, x, y, 0, 0): moves the unit to a free spot by x/y in room, as WarpToLevel does in its own act
inline constexpr uint64_t TeleportUnit = 0x491ca0;
// (unit): flags it (+0x124 bit 0x2000) for its room's update list; D2R's srvst 63 calls it on the corpse it takes
inline constexpr uint64_t QueueUnitUpdate = 0x38ebf0;
inline constexpr uint64_t UnitFrame = 0x349560;  // (unit) -> animation frame (+0x5c >> 8)
inline constexpr uint64_t SetUnitFrame = 0x34da20;  // (unit, frame): +0x5c and +0x60 = frame << 8
inline constexpr uint64_t SetUnitFrames = 0x34d990;  // (unit, n): +0x4c = n << 8, keeping its low byte
inline constexpr uint64_t SetUnitAnimSpeed = 0x34d8c0;  // (unit, n): +0x64 = n << 8
// (game, unit, event type, 0) -> earliest frame of the unit's timer events of that type (1 = mode end), 0 for none
inline constexpr uint64_t UnitEventFrame = 0x48b230;
inline constexpr uint64_t RemoveUnitEvent = 0x48b890;  // (game, unit, event, key): 0 for most; an item aura passes its key
inline constexpr uint64_t AddUnitEvent = 0x48b720;  // (game, unit, event, frame, key, skill, stateKey): zeros for most; item aura ticks (0x437419) pass them

// --- Mode-change gates ---------------------------------------------------------------------------------------------
// Mode-change gate for a busy player (modes 7-0x12), called by 0x42bfb0 (game, unit, mode, unitSkill, flag):
// (game, unit, requested mode, the request's unit skill or null, flag) -> 0 allow, 1 refuse, 4 buffer
inline constexpr uint64_t BusyModeGate = 0x42d840;
// mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi
inline constexpr uint8_t BusyModeGateEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c,
                                                0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18};
// Mode-change gate for a player in get-hit, block or knockback (modes 4, 9, 0x13), called by 0x42bfb0 (game, unit,
// requested mode, flag byte) -> 0 allow, 1 refuse, 4 buffer
inline constexpr uint64_t HitRecoveryGate = 0x42d700;
// mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x20],rsi
inline constexpr uint8_t HitRecoveryGateEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c,
                                                   0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x20};
// The immediates of its two "mode end - game frame > 1" tests (cmp eax,1): walk / run -> buffer, the rest -> refuse
inline constexpr uint64_t HitRecoveryWindowBuffer = 0x42d7d2;
inline constexpr uint64_t HitRecoveryWindowRefuse = 0x42d808;

// --- Pets and summons ----------------------------------------------------------------------------------------------
inline constexpr uint64_t SummonPet = 0x4350e0;        // (game, &SummonParams) -> pet; registers it, enforces petmax
inline constexpr uint64_t SetPetLevel = 0x55fb50;      // (game, owner, pet, 0, skillLevel): pet level from the owner's
inline constexpr uint64_t PetSkillStats = 0x55ef80;    // (game, owner, pet, skill, level, owner+0x12c, 0): the skill's
inline constexpr uint64_t AddPetToParty = 0x58d950;    // (game, pet, 0, owner+0x130)
// Player pets (D2R's PlayerPets.cpp), walked the way its pet add (0x501550, from the summon 0x4350e0) walks them
inline constexpr uint64_t UnitPlayerData = 0x34b240;  // (player) -> player data; its pet table at +0x98
inline constexpr int PlayerPets = 0x98;
inline constexpr uint64_t PetEntry = 0x5013f0;  // (dataFlag, pet table, pet type) -> the type's entry (stride 0x20)
// entry: first pet node (id +0x4, next +0x18), count, max (0x501830 stores the summon's petmax; 0x501ac0 asserts
// count <= max)
inline constexpr int PetHead = 0x0, PetCount = 0x8, PetMax = 0xc;
inline constexpr uint64_t FirstPet = 0x4ff1a0;  // (game, owner, pet type, 1) -> the type's first pet, or null
// (game, owner, pet id, 1): takes the pet off the list and kills it, as the pet add's loop over a group does
inline constexpr uint64_t RemovePet = 0x4ffd30;

// --- Monster spawning ----------------------------------------------------------------------------------------------
inline constexpr uint64_t MonStatsRecord = 0x976e0;  // (dataFlag, classId) -> monstats record or null
// (game, room, x, y, monstats id, mode, -1, 0x42) -> monster or null; counts it in its level's monster region. D2R's
// Nest (0x57c590) passes its 1-based spawn index and 0 for the last two
inline constexpr uint64_t SpawnMonster = 0x492cf0;
// Monster kits, the way D2R's Nest (srvdo 91, 0x57c590) and srvhit 6 (0x45ce90) spawn
inline constexpr uint64_t ClearSpawnSpot = 0x3636d0;  // (room, x, y, 1, 0x100): Nest calls it before spawning
inline constexpr uint64_t NestHold = 0x48e820;  // (unit, 0): Nest calls it before spawning; sets state 54 to the value
// (game, room, monstats id, x, y, mode, 0) -> monster or null: srvhit 6's spawn at the missile
inline constexpr uint64_t SpawnMonsterAt = 0x50a050;
// (spawn params, monster): D2R's per-class setup of a monster that its spawn core 0x493cc0
// (D2Game\src\Monster\MonsterSpawn.cpp) just made; 0x493cc0 is its only caller, and 0x492cf0 and the other spawners
// all go through 0x493cc0. The monster's stats and its monstats Align alignment (0x48e600) are set by then.
// mov [rsp+0x18],rbx / mov [rsp+0x20],rbp / push rsi / push rdi / push r15
inline constexpr uint64_t MonsterSpawned = 0x494a60;
inline constexpr uint8_t MonsterSpawnedEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x18, 0x48, 0x89, 0x6c,
                                                  0x24, 0x20, 0x56, 0x57, 0x41, 0x57};
// (game, player, a, b): the player's life regen event (unit event 3, D2Game\src\Player\PlrModes.cpp). It adds itself
// again for the next frame first, so it runs every frame for every player, dead or alive.
// mov [rsp+0x20],rbx / push rbp / sub rsp,0x40 / mov eax,r9d / mov dword [rsp+0x30],0
inline constexpr uint64_t PlayerRegenEvent = 0x42e600;
inline constexpr uint8_t PlayerRegenEventEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x20, 0x55, 0x48, 0x83, 0xec, 0x40, 0x41,
                                                    0x8b, 0xc1, 0xc7, 0x44, 0x24, 0x30, 0x00, 0x00, 0x00, 0x00};
inline constexpr uint64_t IsPet = 0x3af240;  // (unit) -> non-zero for a pet monster (D2R's leech tests it at 0x450e31)

}  // namespace d2r::rva
