// Engine addresses and record offsets for ONE game image: D2R 3.3.0 build 93847 under D2RLoader 1.3.1
// (PE TimeDateStamp 0x6ab3782c; Steam's 94995 is the same image).
//
// One header per D2R build: a new build gets its own rvas_<build>.h and d2r.h includes that one. The values come from
// the Ghidra analysis of the dumped image (tools/dump_image.py, tools/ghidra_analyze.ps1). A different D2R patch or
// D2RLoader release moves them: re-find each one (knowledge/engine-re.md) before writing a new header.
//
// Policy: every RVA in this header and in rvas_93847/ has a row in knowledge/d2r-93847-addresses.md (RVA, signature,
// meaning, evidence); tests/test_rva_knowledge.py fails when one has none. Add the knowledge row with the value.
// The structures these functions take are in d2r.h. The values are split by area:
//   tables.h   the dispatch tables (skill, missile, aura event, item spell, object operate, AI) and their slots
//   damage.h   hits and damage        units.h   skills, missiles, paths, units, pets
//   offsets.h  byte offsets           stats.h   stats, states, auras, curses
//   items.h    items, cube, drops     levels.h  levels, rooms, portals, objects, automap
//   ai.h       monster AI             client.h  the client side
//   pools.h    the engine's memory pools
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

}  // namespace rva

}  // namespace d2r

#include "rvas_93847/tables.h"
#include "rvas_93847/damage.h"
#include "rvas_93847/units.h"
#include "rvas_93847/offsets.h"
#include "rvas_93847/stats.h"
#include "rvas_93847/items.h"
#include "rvas_93847/levels.h"
#include "rvas_93847/ai.h"
#include "rvas_93847/client.h"
#include "rvas_93847/pools.h"
