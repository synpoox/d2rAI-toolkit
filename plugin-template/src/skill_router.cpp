#include "skill_router.h"

#include "log.h"

#include <atomic>
#include <cstdio>

namespace skill_router {

namespace {

struct Route {
	int32_t skillId;
	SrvDoFn function;
};

// Filled before the router is installed; read-only after
Route g_routes[MaxRoutes];
int g_count = 0;
bool g_installed = false;  // set by a successful InstallRouter: Add refuses after that (the game thread reads g_routes)
std::atomic<uint32_t> g_misses {0};

}  // namespace

auto Add(int32_t skillId, SrvDoFn function) noexcept -> bool {
	if (g_installed || function == nullptr || skillId < 0 || g_count == MaxRoutes) {
		return false;
	}
	for (int i = 0; i < g_count; ++i) {
		if (g_routes[i].skillId == skillId) {
			return false;
		}
	}
	g_routes[g_count++] = {skillId, function};
	return true;
}

auto Dispatch(d2r::Game* game, d2r::Unit* unit, int32_t skillId, int32_t level) noexcept -> int64_t {
	if (game == nullptr || unit == nullptr) {
		return 0;
	}
	for (int i = 0; i < g_count; ++i) {
		if (g_routes[i].skillId == skillId) {
			return g_routes[i].function(game, unit, skillId, level);
		}
	}
	if (plog::Sample(g_misses)) {
		plog::Warn("srvdo router: no function for skill %d (%u so far)", skillId, g_misses.load());
	}
	return 0;
}

auto Count() noexcept -> int {
	return g_count;
}

auto InstallRouter(const D2RL::PluginContext* context, char* report, size_t size) noexcept -> bool {
	static constexpr uint8_t Empty[8] = {};  // the slot must still be a null pointer
	if (g_count == 0) {
		std::snprintf(report, size, "no routes");
		return false;
	}
	if (context == nullptr || d2r::sig::SrvDoTable.state != sigscan::State::Ok) {
		std::snprintf(report, size, "FAILED (image not bound)");
		return false;
	}
	const uint64_t rva = d2r::sig::SrvDoTable.rva + static_cast<uint64_t>(Slot) * 8;
	const bool ok = context->PatchWriteU64(rva, Empty, sizeof(Empty), reinterpret_cast<uint64_t>(&Dispatch));
	std::snprintf(report, size, "srvdofunc %d router, %d route(s)%s", Slot, g_count, ok ? "" : " FAILED (slot not empty)");
	g_installed = ok;
	return ok;
}

void ResetForTest() noexcept {
	g_count = 0;
	g_installed = false;
}

}  // namespace skill_router
