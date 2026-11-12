// NeedsLoad decides when a palette is reloaded; the rest of the part needs the game.
#include "level_palette.h"

#include <cstdio>

namespace {

int g_failures = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

}  // namespace

int main() {
	using level_palette::NeedsLoad;
	Check(!NeedsLoad(-1, 0, 4), "the first level of a game had its load screen");
	Check(!NeedsLoad(0, 0, 4), "level 0 is no level");
	Check(!NeedsLoad(109, 4, 4), "the same palette is not reloaded");
	Check(NeedsLoad(109, 4, 3), "a different palette is reloaded");
	Check(NeedsLoad(1, 0, 255), "any change counts");
	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
