// Build 93847: items, item spells, sockets, the Horadric Cube, drops and treasure classes.
// A byte array is D2R's original bytes at a patch or hook address, for the entry check before a patch or hook.
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Item functions ------------------------------------------------------------------------------------------------
inline constexpr uint64_t ItemRecord = 0x314110;  // (dataFlag, item classId) -> items record (code +0x80, normcode +0x84)
inline constexpr uint64_t ItemIsType = 0x373890;  // (item, itemtypes row) -> non-zero when the item is of that type
inline constexpr uint64_t ItemMissileType = 0x371b60;  // (item) -> weapons.txt missiletype row
inline constexpr uint64_t ItemLevel = 0x36ccf0;  // (item) -> item level (the matcher's out, 0x529d50)
inline constexpr uint64_t ItemQuality = 0x36cf60;     // (item) -> quality (6 rare)
inline constexpr uint64_t ItemPage = 0x36cfe0;            // (item) -> item data +0x55: 0 inventory, 3 cube, 4 stash
inline constexpr uint64_t ItemCode = 0x36ef50;            // (item) -> items.txt code as a dword ('box ' 0x20786f62)
inline constexpr uint64_t ItemStorePage = 0x36ca10;        // (item) -> item data +0x54
inline constexpr uint64_t SetItemStorePage = 0x36d730;     // (item, page): item data +0x54
inline constexpr uint64_t SetItemPage = 0x36de20;          // (item, page): item data +0x55 (ItemPage); 0xff socketed
inline constexpr uint64_t ItemTestFlag = 0x36e2d0;  // (item, flag, line, file) -> non-zero when item data +0x18 has it
inline constexpr uint32_t ItemFlagIdentified = 0x10;
inline constexpr uint64_t IdentifyItem = 0x46e8c0;  // (game, player, item, 1): identifies it and tells the client
inline constexpr uint64_t ItemCalc = 0x3b4880;  // (dataFlag, player, item, calc) -> value
inline constexpr uint64_t ItemRandom = 0x3d5860;  // (item, min, max) -> min..max from the item's seed
inline constexpr uint64_t ItemVersion = 0x3730d0;      // (item) -> 0 classic, 100 or more expansion (1.13c #10718)
// (item) -> &its item seed {lo, hi}, which item rolls draw from (not the unit seed, UnitSeed)
inline constexpr uint64_t ItemSeed = 0x36cc80;
inline constexpr uint64_t ItemOwnerId = 0x371d00;    // (item) -> the owner's unit id (item data +0xc), -1 for none
inline constexpr uint64_t SetItemFlag = 0x36d8f0;   // (item, flag, on): item data +0x18 flags (0x400000 ethereal)
inline constexpr uint64_t ItemSocketable = 0x36b410;  // (item) -> non-zero: can take sockets (1.13c D2Common #10360)
inline constexpr uint64_t SetItemSockets = 0x36e880;  // (item, n): sockets, clamped to the type's max (1.13c #10599)
inline constexpr uint64_t ItemHasSockets = 0x36c750;  // (item) -> non-zero when socketed; cube input flags 4 / 8 test it
inline constexpr uint64_t ItemIsEthereal = 0x3740a0;  // (item) -> non-zero when ethereal; cube input flags 0x10 / 0x20
// (item): sets the ethereal flag, then base stats times 3/2 (1.13c's D2Common #10890). Callers: the drop 0x442d60, the
// ethereal property 0x3ccc60, the cube output 0x5269c0.
// mov [rsp+0x10],rbx / push rdi / sub rsp,0x20 / mov rbx,rcx / test rcx,rcx
inline constexpr uint64_t ItemApplyEthereal = 0x3d3510;
inline constexpr uint8_t ItemApplyEtherealEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x10, 0x57, 0x48, 0x83,
                                                     0xec, 0x20, 0x48, 0x8b, 0xd9, 0x48, 0x85, 0xc9};
inline constexpr int ItemModeSocketed = 6;

// --- Item spells and properties ------------------------------------------------------------------------------------
// Item spell dispatchers, (game, player, item, target): the check -> bool, then the use (whose caller frees an item
// whose spell flag is 0, as slot 16's empty entry is). Both index D2R's 20-entry item spell table (ItemSpellTable) by the
// item's pSpell; slots 16-19 are empty.
// mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi
inline constexpr uint64_t ItemSpellCheck = 0x5817f0;
inline constexpr uint8_t ItemSpellCheckEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c,
                                                  0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18};
// mov [rsp+0x18],rbx / mov [rsp+0x20],rbp / push rsi / push rdi / push r15
inline constexpr uint64_t ItemSpellUse = 0x581680;
inline constexpr uint8_t ItemSpellUseEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x18, 0x48, 0x89, 0x6c,
                                                0x24, 0x20, 0x56, 0x57, 0x41, 0x57};
// (dataFlag, a1, a2, item, Property*, set, stat, layer, value, a8, a9, a10): put one stat on the item's list, as
// every D2R property function does (value shifted by the stat's ValShift)
inline constexpr uint64_t PropertySetStat = 0x3d5940;
// (item, &property {prop, param, min, max}): a cube output mod on the item's magic list (mod type 7, 1.13c #10914)
inline constexpr uint64_t ApplyCubeMod = 0x3d3420;
// (item, affix record) -> non-zero when the magicprefix/suffix record may roll on the item (item types, level 100+
// rules); both affix pickers (0x58c940, 0x58ce80) call it for each candidate, after the picker's own `rare` test
// (record +0x64, a flag in D2R: 0 bars quality 6, 8 and 9).
// mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi / mov [rsp+0x20],rdi
inline constexpr uint64_t AffixAllowed = 0x3d4220;
inline constexpr uint8_t AffixAllowedEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10,
                                                0x48, 0x89, 0x74, 0x24, 0x18, 0x48, 0x89, 0x7c, 0x24, 0x20};
// The staffmods roll on a new item (0x58a050, D2Game\src\Items\ItemsMagic.cpp; 1.13c D2Game +0x13de0): (item, drop
// params). It reads the itemtypes StaffMods class and that class's skill count, then rolls 1.13c's tiers in 0x58af50
// (DropFlags 0x20 adds the item level as bonus) or, on a version-0 item, 0x58b7c0.
// Entry: mov [rsp+0x10],rbx / push rbp / push rdi / push r14 / sub rsp,0x30 / mov rdi,rdx
inline constexpr uint64_t ItemStaffMods = 0x58a050;
inline constexpr uint8_t ItemStaffModsEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x10, 0x55, 0x57, 0x41,
                                                 0x56, 0x48, 0x83, 0xec, 0x30, 0x48, 0x8b, 0xfa};
inline constexpr uint32_t DropFlagStaffModsBonus = 0x20;
inline constexpr uint64_t StaffModsClass = 0x372b80;   // (item) -> itemtypes StaffMods class (0-6, 7 Warlock), or >7
// The item decoder (0x378860, D2Common Items.cpp; client packets and save loads) resets a weapon's base damage from
// weapons.txt and, when ethereal, times 3/2 inline: per stat 21, 22, 23, 24, 159, 160 the 16 bytes
// lea eax,[rax+rax*2] / cdq / sub eax,edx / mov edx,<stat> / sar eax,1 / mov r8d,eax, before SetUnitStat.
inline constexpr uint64_t DecodeEtherealDamage[] = {0x37a451, 0x37a47c, 0x37a4a7, 0x37a4d2, 0x37a4fe, 0x37a52a};
// The weapon durability loss per hit (0x441b10, D2Game\src\Items\Items.cpp; 1.13c's D2Game +0x12ee0): a weapon loses
// one durability when rand(100) < its chance, `mov ebx,4` (0x441b83) and `mov ebx,0xa` (0x441ba6) for the item types
// that take 10. The two immediates D2R ships are WeaponDurabilityVanilla.
inline constexpr uint64_t WeaponDurabilityChance[] = {0x441b83, 0x441ba6};
inline constexpr uint8_t WeaponDurabilityVanilla[] = {4, 10};

// --- Inventories and sockets ---------------------------------------------------------------------------------------
inline constexpr uint64_t UnitInventory = 0x34a360;    // (unit, file, line) -> the unit's inventory, or null
inline constexpr uint64_t InventoryFirstItem = 0x388c10;  // (inventory) -> first item, or null
inline constexpr uint64_t InventoryNextItem = 0x38aba0;   // (item) -> next item in its inventory, or null
inline constexpr uint64_t InventoryBodyItem = 0x3886d0;  // (inventory, bodyloc 0-12) -> the item worn there
// Socketed items, from the socket-insert path 0x46eb00 (D2Game\src\Items\ItemMode.cpp). A socketed item lives in its
// parent's inventory, its stat list linked under the parent's. 0x46eb00 also applies the gems.txt mods (0x475140),
// which a moved gem already carries, so a reroll does the placement and link alone.
inline constexpr uint64_t CreateInventory = 0x3861c0;      // (item): gives the item an empty inventory
inline constexpr uint64_t InventoryRemove = 0x38ba30;      // (item) -> non-zero: out of whatever inventory holds it
inline constexpr uint64_t PlaceInSocket = 0x3856e0;        // (parent's inventory, item, 1) -> non-zero: in a socket
// (game, player, item, item flags, command flags, mode, +0x55, +0x54, xy) sends the item to the clients with those
// values set for the send, then restores them (InvMode.cpp 0x536410 picks the packet by the flags). The cursor socket
// handler 0x4f9f40 refreshes the parent with item flag 1.
inline constexpr uint64_t SendItem = 0x535f60;

// --- Replenish -----------------------------------------------------------------------------------------------------
// Replenish (D2Game\src\Items\ItemMode.cpp). Item event 3 replenishes: (game, item) schedules it 2500 / stat + 1 frames
// on for item_replenish_durability (252), unless one is pending; the equip 0x46eb00 and the durability loss 0x441b10
// call it, each beside its replenish_quantity (253) twin 0x43eaa0. The handler (game, item, ...) adds one durability or
// quantity (0x46f4f0) and schedules the next, at least 125 frames on.
// mov [rsp+8],rbx / mov [rsp+0x10],rsi / push rdi / sub rsp,0x40
inline constexpr uint64_t ScheduleReplenish = 0x43ea10;
inline constexpr uint8_t ScheduleReplenishEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x74,
                                                     0x24, 0x10, 0x57, 0x48, 0x83, 0xec, 0x40};
// mov [rsp+8],rbx / mov [rsp+0x10],rbp / mov [rsp+0x18],rsi
inline constexpr uint64_t ReplenishEvent = 0x476060;
inline constexpr uint8_t ReplenishEventEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c,
                                                  0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18};

// --- Horadric Cube -------------------------------------------------------------------------------------------------
// D2Game\src\Player\PlrTrade.cpp. Recipe search: (result*, game, player, out*) walks cubemain in order and stores the
// first row that passes its filters (enabled, version, ladder, difficulty, class, numinputs == items in the cube,
// player ops 1-14) and whose 7 inputs all match: result {int32 row, uint8 found}. out is 3 x {item*, int32, int32},
// zeroed before each row's inputs.
// push rbp / push rbx / push rsi / push rdi / push r12 / push r13 / push r14 / push r15 / lea rbp,[rsp-0x78] /
// sub rsp,0x178
inline constexpr uint64_t CubeRecipeSearch = 0x529090;
inline constexpr uint8_t CubeRecipeSearchEntry[] = {0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55,
                                                    0x41, 0x56, 0x41, 0x57, 0x48, 0x8d, 0x6c, 0x24, 0x88,
                                                    0x48, 0x81, 0xec, 0x78, 0x01, 0x00, 0x00};
// (game, inventory, row, input 0-6, out*, used*) -> non-zero when that input matches (an empty input does); used is
// 0x30 int32 flags for the cube items already taken by earlier inputs, zeroed before each row
inline constexpr uint64_t CubeInputMatch = 0x529d50;
inline constexpr int CubeMatchUsedSlots = 0x30;
// It counts each matching cube item as one (qty at input +7, 0 means 1) and flags every match in used[k], k the item's
// place among the cube items in inventory order. mov [rsp+0x20],r9d / push rbp / push rbx / push rsi / push r13 /
// mov rbp,rsp / sub rsp,0x68
inline constexpr uint8_t CubeInputMatchEntry[] = {0x44, 0x89, 0x4c, 0x24, 0x20, 0x55, 0x53, 0x56, 0x41,
                                                  0x55, 0x48, 0x8b, 0xec, 0x48, 0x83, 0xec, 0x68};
inline constexpr int CubeInputQty = 7;
inline constexpr int CubeRecordSize = 0x16c, CubeNumInputs = 0xc;  // uint8 numinputs
// The search's numinputs filter: movzx eax,[row+0xc] / cmp eax,r13d (the cube's item count) / jne next row. The jne is
// 6 bytes (CubeNumInputsJumpOrig); a 6-byte nop over it lifts the filter.
inline constexpr uint64_t CubeNumInputsJump = 0x52922a;
inline constexpr uint8_t CubeNumInputsJumpOrig[] = {0x0f, 0x85, 0xbd, 0x06, 0x00, 0x00};
inline constexpr uint64_t CubeRecipeCount = 0x3e3f20;  // (dataFlag) -> cubemain row count
inline constexpr uint64_t CubeRecipe = 0x3e3f60;       // (dataFlag, row) -> 0x16c-byte record, or null
inline constexpr int CubeEnabled = 0x0, CubeOp = 0x3;  // uint8 enabled, uint8 op
// The executor: (game, player, record, out*) runs the row the search found (out as the search filled it). The cube
// packet handler 0x4f2490 calls the search and then this; the cheat transmute 0x4127c0 calls it too.
// push rbp / push rbx / push rsi / push rdi / push r12 / push r13 / push r14 / push r15 / lea rbp,[rsp-0x15f8]
inline constexpr uint64_t CubeExecutor = 0x5269c0;
inline constexpr uint8_t CubeExecutorEntry[] = {0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56,
                                                0x41, 0x57, 0x48, 0x8d, 0xac, 0x24, 0x08, 0xea, 0xff, 0xff};
inline constexpr uint8_t CubePageCube = 3;
// cubemain record (CubeRecipe), packed: param +4, value +8; input n at +0x14 + n * 10 (uint16 flags, int32 id,
// uint8 quality at +6; 0x529d50 reads it); output A at +0x5e (uint16 flags, int32 id at +2, uint8 quality at +6, type at
// +9: 0xff usetype, 0xfe useitem), its five mods from +0x77, 12 bytes each {int32 prop, int16 param, min, max, chance}
// (0x5269c0). The field table 0x3e3ff0 holds these less 0xe.
inline constexpr int CubeParam = 0x4, CubeValue = 0x8, CubeInputs = 0x14, CubeInputSize = 10;
inline constexpr int CubeOutQuality = 0x64, CubeOutType = 0x67, CubeOutMods = 0x77, CubeModSize = 12;

// --- Drops and treasure classes ------------------------------------------------------------------------------------
// (game, dropper, killer, TC record, quality, item level, 0, items* or 0, count* or 0, max): rolls the TC and drops
// its picks by the dropper; with no items array it drops all picks (max under 1 means 6). The item level feeds the
// quality roll 0x4421b0. 1.13c's same function takes (..., tc, 0, ilvl, 0, 0, 0, 1).
inline constexpr uint64_t TcDrop = 0x4404f0;
inline constexpr uint64_t TcDropReturn = 0x44486b;  // the TC drop's return address from ItemSpawn
// (game, monster, flag, death*) -> the monster's own TC drop: its monstats TC for the difficulty and kind (champion,
// unique, quest), dropped by 0x441300. death +0x08 is the monster, +0x10 the killer (the quest-drop test and the
// quality roll's player). 1.13c's 0x6fc95680; D2R's death path 0x4479a0 passes flag 0.
inline constexpr uint64_t MonsterTcDrop = 0x447b80;
// (game, drop, 0) -> item or null: makes an item from a drop request (1.13c's same function). The TC drop 0x444680
// (game, unit, item row, quality, index, flags) fills the request and calls it at 0x444866.
// push rbp / push rbx / push rsi / push r12 / push r15 / lea rbp,[rsp-0x37] / sub rsp,0x90
inline constexpr uint64_t ItemSpawn = 0x43cd50;
inline constexpr uint8_t ItemSpawnEntry[] = {0x40, 0x55, 0x53, 0x56, 0x41, 0x54, 0x41, 0x57, 0x48, 0x8d,
                                             0x6c, 0x24, 0xc9, 0x48, 0x81, 0xec, 0x90, 0x00, 0x00, 0x00};
inline constexpr int DropUnit = 0x00;   // Unit* the dropper
inline constexpr int DropFlags = 0xc0;  // uint32; 0x4 makes an ethereal-capable item ethereal (0x442d60), 1.13c +0x80
inline constexpr uint32_t DropFlagEthereal = 0x4;
// int32 item level (1.13c +0x0c), set by the TC drop from the dropper; int32 prefix[3] / suffix[3] (1.13c +0x68 / +0x74):
// a one-based magicprefix / magicsuffix id forces the affix of a magic item, 0 rolls it (0x442c60, quality 4; an id it
// can't apply rolls too).
inline constexpr int DropItemLevel = 0x18, DropPrefix = 0xa8, DropSuffix = 0xb4;
inline constexpr uint64_t TcIndexByName = 0xa121f0;  // (name map, name, 0) -> compiled index, > 0 when found
inline constexpr uint64_t TcRecord = 0x397290;       // (dataFlag, u16 index, 0) -> compiled TreasureClassEx or null
inline constexpr int TcSet = 0x2a, TcUnique = 0x2c;  // u16 Set / Unique columns
inline constexpr uint64_t ItemRowByCode = 0x313ef0;  // (dataFlag, u32 code, 'wss ' = 0x20737377) -> items row, < 0 if none
// (game, unit, items row, quality, set/unique row + 1, flags): drops the item by the unit at its item level, as the TC
// roller 0x4404f0 does
inline constexpr uint64_t DropItemAt = 0x444680;
inline constexpr int32_t QualityNormal = 2;
// D2R's own drop on the three prime evils' deaths (1.13c 0x6fd0aa30, D2Game\src\Quests\QuestsFX.cpp): it flags
// 704/705/709 dead in the game and, once all three are, drops the Hellfire Torch and a Standard of Heroes per player.
// The unique-monster death switch 0x4a1480 tail-calls it (0x4a1645). A ret (0xc3) written over the first byte makes it
// return at once.
inline constexpr uint64_t PrimesDrop = 0x5a8450;
inline constexpr uint8_t PrimesDropOrig[] = {0x48, 0x89, 0x5c, 0x24, 0x20};  // mov [rsp+20],rbx

// --- items.json keys and the spawn cheat (4-character codes) -------------------------------------------------------
// HD pictures of 4-character item codes. The items.json loader 0x6635a0 keys each entry by its code's first 3
// characters plus a space (0x663a14 writes 0x20 to byte 3), while the picture lookup 0x662fb0 (case 4) searches by the
// item record's whole code dword (+0x80). So a 4-character code never finds its entry and overwrites the entry of the
// 3-character code it starts with. D2R's bytes at ItemsJsonKey are ItemsJsonKeyD2R; a fix keeps byte 3 (the code's
// 4th character | 0x20) and sends the 2-character path to D2R's own double-space store at 0x663a07.
inline constexpr uint64_t ItemsJsonKey = 0x6639f9;
// jmp 0x663a14 / mov [rsp+25],al / movzx eax,byte [rsi+2] / test al,al / jne 0x663a10 / mov word [rsp+26],0x2020 /
// jmp 0x663a19 / mov [rsp+26],al / mov byte [rsp+27],0x20
inline constexpr uint8_t ItemsJsonKeyD2R[] = {0xeb, 0x19, 0x88, 0x44, 0x24, 0x25, 0x0f, 0xb6, 0x46, 0x02, 0x84,
                                              0xc0, 0x75, 0x09, 0x66, 0xc7, 0x44, 0x24, 0x26, 0x20, 0x20, 0xeb,
                                              0x09, 0x88, 0x44, 0x24, 0x26, 0xc6, 0x44, 0x24, 0x27, 0x20};
// The `cheat spawn` handler 0x40f670 builds its item-code key the same way (0x40fc39-0x40fc6e: the first 3 characters,
// spaces after a short code, a space in byte 3), then compares it with each item record's code (+0x80), so a
// 4-character code spawns nothing. On entry r8 holds the lowered code and cl its first character; 0x40fc6e is the
// compare loop. D2R's bytes are SpawnCheatKeyD2R.
inline constexpr uint64_t SpawnCheatKey = 0x40fc39;
// mov [rsp+50],cl / movzx eax,byte [r8+1] / test al,al / jne +9 / mov word [rsp+51],0x2020 / jmp 0x40fc69 /
// mov [rsp+51],al / movzx eax,byte [r8+2] / test al,al / jne +9 / mov word [rsp+52],0x2020 / jmp 0x40fc6e /
// mov [rsp+52],al / mov byte [rsp+53],0x20
inline constexpr uint8_t SpawnCheatKeyD2R[] = {0x41, 0x0f, 0xb6, 0x40, 0x01, 0x88, 0x4c, 0x24, 0x50, 0x84, 0xc0, 0x75,
                                              0x09, 0x66, 0xc7, 0x44, 0x24, 0x51, 0x20, 0x20, 0xeb, 0x1a, 0x88, 0x44,
                                              0x24, 0x51, 0x41, 0x0f, 0xb6, 0x40, 0x02, 0x84, 0xc0, 0x75, 0x09, 0x66,
                                              0xc7, 0x44, 0x24, 0x52, 0x20, 0x20, 0xeb, 0x09, 0x88, 0x44, 0x24, 0x52,
                                              0xc6, 0x44, 0x24, 0x53, 0x20};

}  // namespace d2r::rva
