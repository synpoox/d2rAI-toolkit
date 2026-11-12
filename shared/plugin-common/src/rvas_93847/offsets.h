// Build 93847: byte offsets into the game, units, DataTables and the txt records (skills, missiles, monstats, levels,
// charstats, items).
// Record offsets differ from 1.10 / 1.13c; the comments give the 1.13c offset where it helps.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Game ----------------------------------------------------------------------------------------------------------
// --- Offsets ------------------------------------------------------------------------------------------------------
inline constexpr int GameDataFlag = 0x106;  // Game: byte passed to every data-table getter
// --- Offsets ------------------------------------------------------------------------------------------------------
inline constexpr int GameFrame = 0x170;  // Game: int32 frame counter (unit events are timed in it)
inline constexpr int GameDifficulty = 0x104;  // uint8: 0 normal, 1 nightmare, 2 hell
// Game from a game id: GameById(GameKey(id)); game +0x08 (u16) holds the id back. The server thread walks the same
// table without a lock (0x406400).
inline constexpr uint64_t GameKey = 0x4061e0;   // (u16 id) -> key, 0 for an empty slot
inline constexpr uint64_t GameById = 0x4062f0;  // (key) -> game or null
inline constexpr int GameIdField = 0x08;
inline constexpr uint64_t PlayerCount = 0x4251e0;   // (game) -> players, at least the /players setting
// Game: per-level monster regions (array indexed by level id); a region's spawned-monster count at +0x2cc (0x509520)
inline constexpr int GameMonRegions = 0x1d0;
// The game's monsters: 128 lists by unit id & 0x7f at game +0x2630 (0x4925b0), the next unit at +0x158 (FindUnit)
inline constexpr int GameMonsters = 0x2630, UnitListNext = 0x158;
// The game's dropped-uniques mask (1.13c +0x1b24): bit `row & 31` of u32 `row >> 5`, by uniqueitems row (at most
// 0x1000). The unique roll 0x443910 refuses a set bit, a forced row included, and sets it on a drop.
inline constexpr int GameUniquesDropped = 0x3638;
inline constexpr int GameActs = 0x190, GameActCount = 0x198;
inline constexpr int UnitGame = 0xd8;  // Game*, what 0x48ff00 returns
inline constexpr uint64_t DataTables = 0x300a90;  // (dataFlag) -> data tables; states.txt row count at +0x298
inline constexpr int TablesStateCount = 0x298;  // uint64 states.txt row count in DataTables
// charstats.txt in DataTables: records (0xd0 bytes) and count; D2R's Charge start reads the byte at +0x3d (1.13c +0x41)
// as the class's charge speed
inline constexpr int TablesCharStats = 0x1240;
inline constexpr int TablesCharStatsCount = 0x1248;
// DataTables: the progressive states (int16 state ids) and their count (int64), read by SrvPrgDispatch
inline constexpr int TablesProgressiveStates = 0x420;
inline constexpr int TablesProgressiveCount = 0x428;
// levels.txt in DataTables: records (0x18c bytes) and count; mon1-25 / nmon1-25 are int16, a negative one ends the list
inline constexpr int TablesLevels = 0x1460;
inline constexpr int TablesLevelCount = 0x1468;
inline constexpr int TablesOverlayCount = 0x1230;  // int64 overlay.txt row count in DataTables
inline constexpr int TablesItemTypesCount = 0x1350;  // int64 itemtypes.txt row count in DataTables (ItemIsType's bound)
inline constexpr int TablesTcNames = 0xd70;         // TreasureClassEx name map, for TcIndexByName
// The stat-layer split item events use for skill/level layers: layer >> shift is the skill, layer & mask the level
inline constexpr int TablesSkillLayerShift = 0x14d0, TablesSkillLayerMask = 0x14d4;

// --- Unit ----------------------------------------------------------------------------------------------------------
inline constexpr int UnitType = 0x00;    // int32: 0 player, 1 monster, 2 object, 3 missile, 4 item, 5 tile
inline constexpr int UnitPath = 0x38;    // dynamic path (x +0x2, y +0x6, uint16) or static path (x +0x10, y +0x14)
inline constexpr int UnitArg12c = 0x12c; // int32 passed by D2R's summon skills to PetSkillStats
inline constexpr int UnitArg130 = 0x130; // int32 passed to AddPetToParty
inline constexpr int UnitMonster = 1;
inline constexpr int UnitMode = 0x0c;  // int32 current mode (monmode for a monster)
inline constexpr int MonModeDeath = 0, MonModeDead = 12;
inline constexpr int UnitData = 0x10;  // the unit's type data; a missile's holds its range and last unit hit
inline constexpr int UnitClassId = 0x04;  // int32 row in the unit's table: monstats for a monster, missiles.txt for a missile
inline constexpr int UnitIdField = 0x08;  // uint32, the id NearestTarget skips
inline constexpr int UnitSeqAnim = 0x40;  // pointer cltdo 24 tests to pick how it rewinds an Inferno caster
inline constexpr int UnitOwnerType = 0xe8;  // int32 owner unit type (MissileOwner 0x490300 reads both)
inline constexpr int UnitOwnerId = 0xec;    // uint32 owner unit id
inline constexpr int UnitMainFlags = 0x124;  // uint32, 1.13c's +0xc4 flags with the same bits
inline constexpr uint32_t UnitNoTreasure = 0x20000, UnitNoExperience = 0x4000000;  // Nest sets both on each spawn
inline constexpr uint32_t UnitNoDrop = 0x20000;
inline constexpr int PathTargetUnit = 0x70;  // Unit* on a dynamic path: what PathSteer aims at (set by PathSetTargetUnit)
inline constexpr int PathCollisionMask = 0x64;  // uint32 (set by PathSetCollisionMask)
// int32 type and uint32 id (-1 none) of the last unit a LastCollide missile hit, set by D2Common 0x3bd580 in the
// collision 0x4639a0
inline constexpr int MdLastHitType = 0x20, MdLastHitId = 0x24;

// --- Unit skill (GetUnitSkill) -------------------------------------------------------------------------------------
// Unit skill (rva::GetUnitSkill): flags and the target the hit looks up (0x56ad90)
inline constexpr int USkillFlags = 0x14;  // 0x80 leap starts, 0x100 in the air, 0x1000 path velocity locked
inline constexpr int USkillTargetType = 0x2c;  // 6 = none
inline constexpr int USkillTargetId = 0x30;
inline constexpr int USkillParam = 0x24;  // int32 Charge's counter
// The current unit skill (rva::CurrentSkill) of a nest: where and what its start (srvst 49) set it to spawn
inline constexpr int USkillSpawnX = 0x24, USkillSpawnY = 0x28, USkillSpawnMon = 0x2c, USkillSpawnMode = 0x30;

// --- skills.txt record (748 bytes in D2R; offsets differ from 1.10/1.13c) ------------------------------------------
// skills.txt record (748 bytes in D2R; offsets differ from 1.10/1.13c)
inline constexpr int SkPrgCalc1 = 0x58;       // int32 calc index (pass to EvalCalc)
// skills.txt record (748 bytes in D2R)
inline constexpr int SkSrvDoFunc = 0x4e;  // uint16 srvdofunc, read by the dispatcher 0x43acb0
inline constexpr int SkSrvPrgFunc1 = 0x50;  // int16 srvprgfunc1-3, read by SrvPrgDispatch
inline constexpr int SkSrvMissile = 0x66;     // int16 srvmissile
inline constexpr int SkSrvMissileA = 0x68;    // int16 srvmissilea; srvmissileb +0x6a, srvmissilec +0x6c
inline constexpr int SkSrvOverlay = 0x6e;  // int16 srvoverlay (skills field table 0x302380)
inline constexpr int SkAuraFilter = 0x70;  // int32 aurafilter, the area unit mask (clthit 26 reads it)
inline constexpr int SkAuraStat1 = 0x74;      // int16 aurastat1-6, read by AddAuraStats (0x574480)
inline constexpr int SkAuraLenCalc = 0x80;    // int32 auralencalc: 1.13c's 0x60, before aurarangecalc as there
inline constexpr int SkAuraRangeCalc = 0x84;  // int32 calc index
inline constexpr int SkAuraStatCalc1 = 0x88;  // int32 aurastatcalc1-6 (calc index, pass to EvalCalc), same reader
inline constexpr int SkAuraState = 0xa0;      // int16 aurastate
inline constexpr int SkAuraTargetState = 0xa2;  // int16 auratargetstate (skills field table 0x302380)
// Two record fields Frozen Armor passes to SendSkillState by address; what they hold is not read yet.
inline constexpr int SkSendStateA = 0xa4;
inline constexpr int SkSendStateB = 0xac;
inline constexpr int SkSummon = 0x110;        // int16 monstats row
inline constexpr int SkPetType = 0x112;       // uint8 pettype row
inline constexpr int SkSumMode = 0x113;       // uint8 monmode, 255 = none
inline constexpr int SkPetMaxCalc = 0x114;    // int32 calc index
inline constexpr int SkSumOverlay = 0x13c;  // int16 sumoverlay (1.13c +0xe6): Nest puts it on each spawn
inline constexpr int SkCltMissileA = 0x140; // int16 cltmissilea; cltmissileb +0x142, cltmissilec +0x144
inline constexpr int SkCltCalc1 = 0x16c;  // int32 cltcalc1-3 (calc index; 1.13c's 0x114)
inline constexpr int SkCltCalc2 = 0x170;
inline constexpr int SkCltCalc3 = 0x174;
inline constexpr int SkCalc1 = 0x190;         // int32 calc index
inline constexpr int SkCalc2 = 0x194;
inline constexpr int SkCalc3 = 0x198;
inline constexpr int SkCalc4 = 0x19c;  // skills field table at 0x306193
inline constexpr int SkParam1 = 0x1b8;  // int32 Param1-8, field table at 0x305e68
inline constexpr int SkParam2 = 0x1bc;
inline constexpr int SkParam3 = 0x1c0;
inline constexpr int SkParam4 = 0x1c4;
inline constexpr int SkParam5 = 0x1c8;
inline constexpr int SkParam6 = 0x1cc;
inline constexpr int SkReqLevel = 0x214;    // uint16 reqlevel
inline constexpr int SkLocalDelay = 0x238;  // int32 compiled localdelay formula, -1 for none
inline constexpr int SkFlags24 = 0x24;
inline constexpr int SkPerDelayCalc = 0x180;  // int32 perdelay calc index
inline constexpr int SkRollFlags = 0x29;  // uint8 Leap Attack's hit masks with MeleeRollFlagMask for MeleeRoll's flag
inline constexpr int SkEType = 0x284;  // uint8 EType (1.13c's 0x1dc)
// uint16 ResultFlags, uint32 HitFlags, int32 HitClass (1.13c's 0x12e / 0x130 / 0x134), as D2R's Hunger (0x576630)
// reads them into its damage block
inline constexpr int SkResultFlags = 0x186;
inline constexpr int SkHitFlags = 0x188;
inline constexpr int SkHitClass = 0x18c;
inline constexpr int SkSrcDam = 0x24d;  // uint8 SrcDam (0 = 128), read by Leap Attack's 0x56b170

// --- missiles.txt record (1.13c offsets shifted by 0x24) -----------------------------------------------------------
inline constexpr int MsCltSubMissile1 = 0x40;  // int16 CltSubMissile1 (1.13c's 0x1e; D2R's cltdo 9 reads it)
// int16 HitSubMissile1 and CltHitSubMissile1 (1.13c's 0x24 / 0x2c), as D2R's clthit 26 (0x1adcb0) reads them
inline constexpr int MsHitSubMissile1 = 0x46;
inline constexpr int MsCltHitSubMissile1 = 0x4e;
// missiles.txt record (1.13c's shifted by 0x24)
inline constexpr int MsParam1 = 0x5c;     // int32 Param1 (1.13c's 0x38)
inline constexpr int MsHitPar1 = 0x70;  // int32 missiles.txt sHitPar1 (Chain Lightning's chain range, 0 = the skill's)
inline constexpr int MsHitPar2 = 0x74;  // int32 sHitPar2, sHitPar3 +0x78 (1.13c's 0x50 / 0x54 + 0x24)
inline constexpr int MsHitPar3 = 0x78;
inline constexpr int MsCltHitPar1 = 0x90;  // int32 cHitPar1-3 (1.13c's 0x6c-0x74 + 0x24)
inline constexpr int MsCltHitPar2 = 0x94;
inline constexpr int MsCltHitPar3 = 0x98;
inline constexpr int MsDParam1 = 0x9c;    // int32 dParam1
inline constexpr int MsDParam2 = 0xa0;    // int32 dParam2 (1.13c's 0x7c)
inline constexpr int MsHitCalc1 = 0xac;  // int32 SHitCalc1 (calc index; 1.13c's 0x88 + 0x24), as srvhit 9 (0x45d020) reads it
inline constexpr int MsCltHitCalc1 = 0xb0;  // int32 CHitCalc1 (calc index; 1.13c's 0x8c + 0x24, before DmgCalc1)
inline constexpr int MsDmgCalc1 = 0xb4;   // int32 DmgCalc1 (calc index), read by dmg 1 0x453490
// uint32 HitFlags, uint16 ResultFlags (1.13c's 0xa8 / 0xac + 0x28; the field table at 0x3c2c70)
inline constexpr int MsHitFlags = 0xd0;
inline constexpr int MsResultFlags = 0xd4;
inline constexpr int MsAnimSpeed = 0x1a0;  // uint8, the client create (0x1b7760) passes it to SetUnitAnimSpeed
inline constexpr int MsCollideKill = 0x1ae;  // uint8 CollideKill (1.13c's 0x186 + 0x28; the field table at 0x3c4233)
inline constexpr int MsSkill = 0x1b6;     // int16 Skill (skills.txt row), read off a live explodingarrow row

// --- monstats.txt record -------------------------------------------------------------------------------------------
inline constexpr int MonFlags = 0x3c;  // uint32 flags; lUndead bit 11, hUndead bit 12 (monstats field table 0x39db30)
inline constexpr uint32_t MonUndead = 0x1800;  // 1.13c's D2Common #10239 tests the same two bits
inline constexpr uint32_t MonDemon = 0x2000;  // MonFlags bit 13 (monstats field table 0x39db30)
inline constexpr uint32_t MonPrimeEvil = 0x80;  // MonFlags bit 7 (1.13c's D2Common #10278 tests the same bit)
// monstats record (rva::MonStatsRecord)
inline constexpr int MonSpawn = 0x54;     // int16 spawn, -1 for none
inline constexpr int MonPartyMin = 0x62;  // uint8
inline constexpr int MonPartyMax = 0x63;  // uint8
inline constexpr int MonMinGrp = 0x65, MonMaxGrp = 0x66;  // uint8 MinGrp, MaxGrp (field table 0x39db30; 1.13c +0x2f, +0x30)
inline constexpr int MonRun = 0x6a;  // int16 monstats Run: D2R's field table (0x39db30) has Velocity at 0x68, Run at 0x6a.
inline constexpr int MonAlign = 0x87;  // uint8 monstats Align (rva::MonStatsRecord); 0x493cc0 reads it for 0x48e600
// monstats record: aidel uint8[3] (the txt field table 0x39db30), aip1-8 int16[8][3], Skill1-8 int16, Sk1-8mode uint8
inline constexpr int MonAiDel = 0x8a, MonAiParams = 0x90, MonSkills = 0x1c4, MonSkillModes = 0x1d4;
inline constexpr int MonAiDist = 0x8d;  // uint8 aidist, then (N) and (H) (monstats field table 0x39db30)
inline constexpr int MonDataTypeFlags = 0x1a;     // u8 in the monster's UnitData: 0x10 minion (1.13c +0x16)
inline constexpr uint8_t MonTypeMinion = 0x10;

// --- Other records -------------------------------------------------------------------------------------------------
inline constexpr int LvlPal = 0x0c;  // uint8 Pal (0x9bf00 reads it for SetActPalette; Teleport is +0x0e)
inline constexpr int LevelRecordSize = 0x18c;
inline constexpr int CharStatsSize = 0xd0;
inline constexpr int CsChargeVelocity = 0x3d;
inline constexpr int ItCode = 0x80;      // uint32 code
inline constexpr int ItNormCode = 0x84;  // uint32 normcode (items field table in 0x315fd0)
inline constexpr int ItType = 0x12e;     // int16 items type (the type the socketable test reads)
inline constexpr int It2Handed = 0x12b;  // uint8 items 2handed (items field table 0x315fd0)
inline constexpr int ItemPSpell = 0x94;   // int32 misc pSpell in the items record (ItemRecord)
inline constexpr int ItemLenCalc = 0xb0;  // uint32 misc len calc; the timed potion handler 0x57ecb0 evaluates it
inline constexpr int AffixRare = 0x64;  // uint8 magicprefix/suffix `rare`
inline constexpr int ObjOperateFn = 0x15e;   // uint8 OperateFn
inline constexpr int ObjOpenFrames = 0x9c;   // uint32; >> 8 is the frames the portal maker waits before event 1
inline constexpr int LvlMon1 = 0x3e;
inline constexpr int LvlNMon1 = 0x70;

}  // namespace d2r::rva
