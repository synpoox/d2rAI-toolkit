// The legacy palette of the level entered. D2R loads a level's palette (levels.txt Pal) only when a load screen ends,
// so a level whose Pal differs from the one before it, entered without a load screen (a portal, a teleport, a command
// that jumps across acts), draws in the wrong palette: tiles of one act show with another act's colours. This part
// listens for level changes and calls D2R's own act palette load when the Pal changed. No hook, no patch.
//
//   from a part's install, after d2r::Bind() succeeded:
//   level_palette::Install(context, report, sizeof(report));
//
// Knowledge: knowledge/d2r-93847-addresses.md (LoadActPalette, SetActPalette, LevelRecord, LvlPal).
// Rule 6: Install does nothing when Bind() has not accepted the image.
#pragma once

#include <D2RLPlugin/api.h>

#include <cstddef>
#include <cstdint>

namespace level_palette {

// Reload only when the palette changes: the first level of a game had its load screen (previousLevel <= 0).
constexpr auto NeedsLoad(int32_t previousLevel, uint8_t previousPal, uint8_t pal) noexcept -> bool {
	return previousLevel > 0 && previousPal != pal;
}

// Listens for level changes on the UI thread. Writes the line for the log into `report`.
void Install(const D2RL::PluginContext* context, char* report, size_t size) noexcept;

// "palette: level changes N, palettes loaded N", for a status command.
void Counters(char* out, size_t size) noexcept;

}  // namespace level_palette
