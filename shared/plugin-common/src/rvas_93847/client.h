// Build 93847: the client side: units and messages, the palette, NPC menus and the server's NPC table.
// Client functions take no game; dataFlag comes from UnitDataFlag (units.h).
// Part of rvas_93847.h; every RVA here has a row in knowledge/d2r-93847-addresses.md.
#pragma once

#include <cstdint>

namespace d2r::rva {

// --- Client units and messages -------------------------------------------------------------------------------------
inline constexpr uint64_t LocalPlayerSlot = 0x8b2d0;  // () -> slot of the local player
inline constexpr uint64_t ClientPlayer = 0x9a480;  // (slot) -> the client's player unit in that slot
inline constexpr uint64_t ClientFindUnit = 0x9a5d0;  // (id, type) -> the client's unit or null
inline constexpr uint64_t ClientMessage = 0x491960;  // (player, message, player); 0x15 is "can't do that"
// (*(game + GameClients), packet): sends a chat packet 0x26 (type at +1, unit type +3, unit id +4, colour +8, name at
// +10 up to 60 bytes, text at +0x47 up to 255) to the game's clients; it breaks on longer text. D2R's own GameChat
// (0x4016c0, the debug commands' "Warping to level") sends type 1 with unit type 2, which the client drops; type 4 or
// unit type 0 shows.
inline constexpr uint64_t SendChat = 0x477a30;
// The game's clients: a list at game +0x138, the next client at +0x628 (0x484d90 walks it); (client, 0) -> its player
inline constexpr int GameClients = 0x138, ClientNext = 0x628;
inline constexpr uint64_t ClientUnit = 0x484c90;
// (client, packet): sends a 10-byte packet, a2q3's 0x53 {0x53, int period, int time, byte eclipse} (0x5a4290). The
// game's light tick 0x406550 sends the same packet to an act's clients when its light changes. Client +4: 4 in game.
inline constexpr uint64_t SendPacket10 = 0x477420;
inline constexpr int ClientState = 4, ClientInGame = 4;
// How the chest operate plays its unlock sound: rva::ClientMessage(player, 0xb, player), then (player) -> its client
// (player data +0xf0, null for a non-player) and (player, client) sends the sound packet 0x2c
inline constexpr uint64_t PlayerClient = 0x48fde0;
inline constexpr uint64_t SoundPacket = 0x5397f0;
inline constexpr int SoundChestOpen = 0xb;

// --- Palette -------------------------------------------------------------------------------------------------------
// (act byte) -> void: loads data/global/palette/act<N+1>/pal.pl2 (legacy floor, light and colormap tables) and updates
// the palette texture. Only the load screen's end calls it with a level's palette (0xc5f80 passes the act palette), so
// a level entered without one keeps the last act's. SetActPalette sets that palette.
inline constexpr uint64_t LoadActPalette = 0x9041a0;
// (act byte) -> void: sets ActPalette. The client's unit placement 0x9bf00 sets it from the level record's Pal,
// the act load 0x86bc0 from the act. The global it writes: 0x2a2adc0.
inline constexpr uint64_t SetActPalette = 0xcd6d0;

// --- NPC menus (client) and the NPC table (server) -----------------------------------------------------------------
// NPC menus (D2Client\src\UI\npcmenu.cpp): a vector of 0x48-byte records, one per NPC with a menu. +0 uint16 NPC
// class, +4 int32 entry count (the last entry is Cancel), +8 uint16 string id[5], +0x18 handler[5]. The client fills
// them from npc.txt and per-NPC setters (a few NPCs get Hire or a travel entry), then opens one
// with NpcMenuOpen.
inline constexpr uint64_t NpcMenus = 0x2a48830, NpcMenuCount = 0x2a48838;
inline constexpr int NpcMenuSize = 0x48, NpcMenuEntries = 0x04, NpcMenuStrings = 0x08, NpcMenuHandlers = 0x18;
inline constexpr int NpcMenuMaxEntries = 5;
inline constexpr uint16_t StrNpcMenuHire = 0xd45;
inline constexpr uint64_t NpcMenuHire = 0x112620;  // Hire's handler: opens HireMenuPanel, for any NPC
// (record, resurrect) -> 1: inserts or removes Resurrect before Hire, then the menu opens.
// push rbp / push rbx / push rdi / lea rbp,[rsp-0x47] / sub rsp,0x90
inline constexpr uint64_t NpcMenuOpen = 0x116480;
inline constexpr uint8_t NpcMenuOpenEntry[] = {0x40, 0x55, 0x53, 0x57, 0x48, 0x8d, 0x6c, 0x24,
                                               0xb9, 0x48, 0x81, 0xec, 0x90, 0x00, 0x00, 0x00};
// The server's NPC table (D2Game\src\Unit\SUnitNpc.cpp, read by 0x3971a0): 43 entries of 0x1c bytes, +0 uint16 NPC
// class, +7 byte "hires mercenaries" (the hire handler 0x53d350 refuses an NPC without it). Kashya, Greiz, Asheara
// and Qual-Kehk have 1; every other NPC has 0.
inline constexpr uint64_t NpcTable = 0x237ea60;
inline constexpr int NpcTableSize = 0x1c, NpcTableHires = 7;

}  // namespace d2r::rva
