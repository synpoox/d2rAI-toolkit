// Build 93847: levels, rooms, portals and warps, objects, monster regions, act light and the automap.
// Room and level functions take the game or dataFlag the comment names.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Levels, rooms and the draw tree -------------------------------------------------------------------------------
inline constexpr uint64_t LevelRecord = 0x32c4a0;  // (dataFlag, level id) -> levels.txt record
// The room holding x/y near a room, as D2R's summon helper 0x4350e0 (Bone Wall, Raise Skeleton) spawns and 0x509520
// counts
inline constexpr uint64_t RoomAtXY = 0x38dfb0;  // (room, x, y) -> the room holding x/y near `room`, or null
inline constexpr uint64_t RoomLevelId = 0x2efc10;  // (room) -> levels.txt id
inline constexpr uint64_t InTerrorZone = 0x489b70;  // (game, level id) -> bool: the level is in the active Terror Zone
// D2Common's DUNGEON_FindActSpawnLocationEx (1.13c's ordinal 10816), as WarpToLevel calls it: (dataFlag, act, level,
// spot, int32* x, int32* y, unit size) -> the room holding the free spot near the level's spot, its coordinates in x/y,
// or null. With the levels record's +0x90 set, spot picks a special tile of the level's presets (0x3dac20; 13 the
// level's entry); without it, spot is unused. It builds the level if needed.
inline constexpr uint64_t ActSpawnSpot = 0x2ef8b0;
// The steps ActSpawnSpot's 0x3da650 takes from a level id to a room (D2Common Drlg): (dataFlag, act +ActDrlg, level id)
// -> the act's level (made if missing); (dataFlag, level) builds its rooms when level +0x10 (the first room ex) is
// null; (level, tile x, tile y) -> the room ex holding the tile; (dataFlag, room ex) -> its room, made if needed. A
// level's origin is in tiles at +0x24/+0x28.
inline constexpr int ActDrlg = 0x70;
inline constexpr uint64_t LevelGet = 0x3267c0;
inline constexpr uint64_t LevelBuild = 0x3271c0;
inline constexpr uint64_t LevelRoomExAt = 0x3275b0;
inline constexpr uint64_t RoomExRoom = 0x3289a0;
inline constexpr int LevelFirstRoomEx = 0x10, LevelTileX = 0x24, LevelTileY = 0x28;
// (game, room): spawns a room's monsters as it activates (1.13c D2Game 0x6fc67a20). Its first call (1.13c 0x6fc66cd0)
// counts the room in its level's monster region at +0x04.
// mov r11,rsp / push rbx / push rsi / sub rsp,0xb8
inline constexpr uint64_t RoomPopulate = 0x50acf0;
inline constexpr uint8_t RoomPopulateEntry[] = {0x4c, 0x8b, 0xdc, 0x53, 0x56, 0x48, 0x81, 0xec, 0xb8, 0x00, 0x00, 0x00};
// A room's subtile rect, as 0x2f0680 (does the room hold x/y) reads it: int32 x, y, width, height
inline constexpr int RoomX = 0x80, RoomY = 0x84, RoomWidth = 0x88, RoomHeight = 0x8c;
// (game, room, preset): spawns one room preset unit (1.13c D2Game 0x6fd013b0) through 0x48dc50 (1.13c 0x6fd012d0; type 1
// goes to 0x50a050). The room's preset loop 0x48f190 (1.13c 0x6fd01430) is its only caller. Preset: +4 int32 id (a
// monstats id for a monster), +0x20 int32 unit type.
// push rbx / push rsi / push rdi / sub rsp,0x80
inline constexpr uint64_t PresetSpawn = 0x4926b0;
inline constexpr uint8_t PresetSpawnEntry[] = {0x40, 0x53, 0x56, 0x57, 0x48, 0x81, 0xec, 0x80, 0x00, 0x00, 0x00};
inline constexpr int PresetId = 0x4, PresetType = 0x20;
// A room preset's subtile offsets from the room's RoomX/RoomY, as PresetSpawn reads them
inline constexpr int PresetX = 0x8, PresetY = 0x24;
// The room walk of 0x593630 (finds an object by class near a unit): (room, &rooms, &count) the room and its
// neighbours, (room) its first unit, (unit) the next unit in its room
inline constexpr uint64_t NearRooms = 0x2efde0;
inline constexpr uint64_t RoomFirstUnit = 0x2efd90;
inline constexpr uint64_t NextUnitInRoom = 0x34b4a0;

// --- Room release --------------------------------------------------------------------------------------------------
// (room, 0) sets bit 0x400000 of the room's level-gen room (+0x18, flags +0x50; 0x328860), (room, 1) clears it. The
// portal maker sets it on each portal's room, operate 15 clears it on removal: an unmarked room is freed with its units
// once no player is near.
inline constexpr uint64_t RoomPortalMark = 0x2f0530;
// The room-release pass 0x4088c0 asks (act, room) -> nonzero for each room 10+ ticks without a player; a yes frees the
// room and its units (0x504260 each, then 0x2f0110). Its only caller. 0 when the room is marked (RoomPortalMark).
// push rbx / sub rsp,0x20 / cmp dword [rcx+0x80],0 / mov rbx,rdx
inline constexpr uint64_t RoomReleasable = 0x2f0630;
inline constexpr uint8_t RoomReleasableEntry[] = {0x40, 0x53, 0x48, 0x83, 0xec, 0x20, 0x83, 0xb9,
                                                  0x80, 0x00, 0x00, 0x00, 0x00, 0x48, 0x8b, 0xda};

// --- Portals, objects and warps ------------------------------------------------------------------------------------
// (game, player, key, level, max) -> 1 opened: the cube's "Red Portal" output (0x52aa00 passes its key, level, max).
// The player must stand in town; it finds a free spot, makes red portal 60 to the level (same act only), and counts
// the opening in the game's counter for key; with max > 0 it refuses once the counter reaches max. A refusal sends
// client message 0x15.
inline constexpr uint64_t OpenRedPortal = 0x5da800;
// (game, unit, room, x, y, destLevel, &object, objectId, 0, 1) -> non-zero: the portal pair OpenRedPortal makes
// (D2Game\src\Items\ItemMode.cpp): it finds a free spot near (x, y) in room, the portal opens on event 1, and 0x435dd0
// makes its linked return portal in the level. With the last 1 the unit is not read (only the town refusal message uses
// it); the destination must be in the room's act. Arg 9 0 / 10 1 skip the town check. The caller sets the destination
// after (SetPortalLevel), as OpenRedPortal does.
inline constexpr uint64_t PortalMaker = 0x432ce0;
inline constexpr uint64_t FindFreeSpot = 0x517f90;
inline constexpr uint64_t GameCounter = 0x5d88b0;  // (game + GameCounters, &key) -> int32* counter (made if missing)
inline constexpr int GameCounters = 0x1aac8;
// (questRecord, quest, bit) -> non-zero when set (D2Common QuestRecord.cpp); a player's record for a difficulty is
// at player data + 0x40 + difficulty * 8 (the item-use quest checks in 0x4734f0). Bit 0: the quest is done.
inline constexpr uint64_t QuestFlag = 0x325c50;
inline constexpr int PlayerQuests = 0x40;
// (game, player, level, 0): moves the player into the level (D2Game\src\Game\Clients.cpp). In the same act it finds the
// level's arrival spot (ActSpawnSpot) and teleports there (TeleportUnit); else it changes act. The debug "Warping to
// level" handler 0x402820 calls it.
inline constexpr uint64_t WarpToLevel = 0x488180;
inline constexpr uint64_t ObjectRecord = 0x38fd00;  // (dataFlag, objects row) -> objects record (0x168 bytes) or null
// How the portal maker 0x432ce0 makes a portal, without its return portal (0x435dd0):
// (unit type, row, x, y, game, room, 1, 1, 0, 0) -> unit; for an object its InitFn runs (12: mode 1, the red portals')
inline constexpr uint64_t SpawnUnit = 0x490410;
inline constexpr uint64_t SetObjectMode = 0x34e5f0;   // (object, mode)
inline constexpr int UnitEventOpen = 1;               // the event that opens a portal (mode 1 -> 2)
inline constexpr uint64_t SetPortalLevel = 0x34e9d0;  // (object, level byte): the portal's destination
inline constexpr uint64_t PortalLevel = 0x34ad40;     // (object) -> uint16 destination
// How operate 15 removes a used town portal: (room, unit type, unit id) tells the room's clients, (game, unit) frees
// the unit
inline constexpr uint64_t RoomUnitRemoved = 0x2ef4d0;
inline constexpr uint64_t RemoveUnit = 0x48faa0;
// D2R's chest operate (OperateFn 4, D2Game\src\Objects\ObjMode.cpp): mode 0 only; it sets mode 1 with event 1 at the
// open frames (or mode 2), plays sound 0xb for a locked chest, then drops the act's chest TC.
inline constexpr uint64_t OperateChestFn = 0x58e2f0;
// The Chaos Sanctuary sweep (0x5e5990, D2Game\src\Quests\a4q2.cpp; 1.13c's D2Game +0xbb3b0): once the fifth seal opens,
// it kills every monster but Diablo (243) in level 108's rooms, each through ModeCmdInit (unit, 0, &cmd) at 0x5e5a8c,
// then ModeCmdRun. This is the return address of that kill call.
inline constexpr uint64_t SealSweepKillReturn = 0x5e5a91;

// --- Monster regions -----------------------------------------------------------------------------------------------
// GameMonRegions: 0x5098b0 builds every level's region once per game (0x508750), from its levels row. Fields at 1.13c's
// offsets.
inline constexpr int RegionCount = 0x10, RegionRarity = 0x11, RegionSpawnCount = 0x12;  // uint8: groups, sum, picks
inline constexpr int MonRegionCount = 0x2cc;
inline constexpr int RegionGroups = 0x14, RegionGroupSize = 0x34, RegionMaxGroups = 13;  // int16 monstats id, uint8 rarity
inline constexpr int RegionMonDen = 0x2b8;                         // uint32 levels MonDen of the difficulty
inline constexpr int RegionBossMin = 0x2bc, RegionBossMax = 0x2bd;  // uint8 MonUMin / MonUMax
// (game, level id) -> the level's monster level: levels MonLvl / MonLvlEx of the difficulty (0x32c700), plus a terror
// zone's bump (MonsterRegionAdjustMonsterLevel). Monster spawns, uniques and item levels call it; D2R never reads the
// region's own monster level fields (+0x2dc, +0x2e0).
// mov [rsp+0x10],rbx / mov [rsp+0x18],rsi / push rdi / sub rsp,0x30
inline constexpr uint64_t AreaMonsterLevelFn = 0x508f80;
inline constexpr uint8_t AreaMonsterLevelEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x10, 0x48, 0x89, 0x74,
                                                    0x24, 0x18, 0x57, 0x48, 0x83, 0xec, 0x30};

// --- Act light -----------------------------------------------------------------------------------------------------
// An act's eclipse, the way the Tainted Sun quest (a2q3.cpp 0x5a7370) darkens act II. ActEclipseOn: (dataFlag, act)
// eclipse on (1.13c D2Common #10337). ActLightSet: (dataFlag, act, room or null, period, time, eclipse) sets the act's
// light, as the client's packet 0x53 handler (0x12cb50) does; period 2, time 0, eclipse 0 is 1.13c #10895's eclipse off,
// which also puts back the speed (EnvSpeedNormal) and clears the pause. The act's light at act +8: period +0, speed
// +0x2c, pause +0x30, eclipse +0x34 (0x351df0 reads it). A unit's act at unit +0x20 (0x34a1a0).
inline constexpr uint64_t ActEclipseOn = 0x3526f0, ActLightSet = 0x3525c0;
inline constexpr uint64_t EnvSpeedNormal = 0x2376848;  // int 128 (1.13c 0x6fdeb238); the eclipse's is 4 (0x237684c)
inline constexpr int UnitAct = 0x20, ActEnv = 8, EnvSpeed = 0x2c, EnvPause = 0x30, EnvEclipse = 0x34;

}  // namespace d2r::rva
