// The router's dispatch: a routed skill id reaches its function, every other id returns 0. No game needed.
#include "skill_router.h"

#include <cstdio>

namespace {

int g_failures = 0;
int g_calls[2] {};

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

auto SkillA(d2r::Game*, d2r::Unit*, int32_t, int32_t level) noexcept -> int64_t {
	++g_calls[0];
	return level;
}
auto SkillB(d2r::Game*, d2r::Unit*, int32_t, int32_t) noexcept -> int64_t {
	++g_calls[1];
	return 1;
}

}  // namespace

int main() {
	using namespace skill_router;
	ResetForTest();
	char byte = 0;
	auto* game = reinterpret_cast<d2r::Game*>(&byte);
	auto* unit = reinterpret_cast<d2r::Unit*>(&byte);

	Check(!Add(5, nullptr), "a null function is refused");
	Check(!Add(-1, &SkillA), "a negative skill id is refused");
	Check(Add(5, &SkillA) && Add(9, &SkillB), "two skills route");
	Check(!Add(5, &SkillB), "a skill id routes once");
	Check(Count() == 2, "two routes");
	Check(Dispatch(game, unit, 5, 7) == 7 && g_calls[0] == 1, "a routed id reaches its function with its level");
	Check(Dispatch(game, unit, 9, 1) == 1 && g_calls[1] == 1, "the other routed id reaches its own");
	Check(Dispatch(game, unit, 6, 1) == 0 && g_calls[0] == 1 && g_calls[1] == 1, "an unrouted id returns 0");
	Check(Dispatch(nullptr, unit, 5, 1) == 0 && Dispatch(game, nullptr, 5, 1) == 0, "a null game or unit returns 0");
	ResetForTest();
	bool full = true;
	for (int i = 0; i < MaxRoutes; ++i) {
		full = Add(i, &SkillA) && full;
	}
	Check(full && !Add(MaxRoutes, &SkillA), "MaxRoutes routes, no more");
	ResetForTest();

	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
