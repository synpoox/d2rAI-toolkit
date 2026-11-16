#include "ai_registry.h"

#include "log.h"

#include <array>
#include <atomic>
#include <cstring>
#include <utility>

namespace ai_registry {

namespace {

using d2r::At;

struct Row {
	int32_t row = -1;
	ThinkFn vanilla = nullptr;
	int32_t classes[MaxClasses] {};
	ThinkFn thinks[MaxClasses] {};
	int count = 0;
};
// Filled at install, before the game runs a think; read-only after
Row g_rows[MaxRows];
std::atomic<BeforeThinkFn> g_before {nullptr};

template <int K>
void Trampoline(d2r::Game* game, d2r::Unit* unit, uint8_t* tick) noexcept {
	Dispatch(K, game, unit, tick);
}

template <int... K>
constexpr auto MakeTrampolines(std::integer_sequence<int, K...>) noexcept {
	return std::array<ThinkFn, sizeof...(K)> {&Trampoline<K>...};
}
constexpr auto Trampolines = MakeTrampolines(std::make_integer_sequence<int, MaxRows> {});

auto Slot(uint64_t tableRva, int32_t row) noexcept -> uint64_t {
	return tableRva + static_cast<uint64_t>(row) * d2r::rva::AiRowSize;
}

// What WriteSlot needs: the context to patch through and the image base the expected think rva is added to.
struct Target {
	const D2RL::PluginContext* context;
	uint64_t base;
};

auto WriteSlot(uint64_t slotRva, uint64_t expectedRva, ThinkFn trampoline, void* user) noexcept -> bool {
	const auto* target = static_cast<const Target*>(user);
	const uint64_t vanilla = target->base + expectedRva;
	uint8_t expected[8];
	std::memcpy(expected, &vanilla, sizeof(expected));
	return target->context != nullptr &&
	       target->context->PatchWriteU64(slotRva, expected, sizeof(expected), reinterpret_cast<uint64_t>(trampoline));
}

}  // namespace

void Dispatch(int k, d2r::Game* game, d2r::Unit* unit, uint8_t* tick) noexcept {
	const Row& r = g_rows[k];
	if (unit != nullptr && At<int32_t>(unit, d2r::rva::UnitType) == d2r::rva::UnitMonster) {
		const int32_t classId = At<int32_t>(unit, d2r::rva::UnitClassId);
		for (int i = 0; i < r.count; ++i) {
			if (r.classes[i] == classId) {
				if (const BeforeThinkFn before = g_before.load(); before != nullptr) {
					before(unit, classId);
				}
				r.thinks[i](game, unit, tick);
				return;
			}
		}
	}
	r.vanilla(game, unit, tick);
}

auto RegisterWithTable(SlotWriter write, void* user, uint64_t tableRva, int32_t monaiRow, uint64_t d2rThink,
                       ThinkFn vanilla, int32_t classId, ThinkFn think) noexcept -> bool {
	if (write == nullptr || vanilla == nullptr || monaiRow < 0 || monaiRow >= d2r::rva::AiRows || think == nullptr) {
		return false;
	}
	int k = 0;
	while (k < MaxRows && g_rows[k].row != monaiRow && g_rows[k].row >= 0) {
		++k;
	}
	if (k == MaxRows) {
		plog::Warn("ai registry: no free row for monai %d", monaiRow);
		return false;
	}
	Row& r = g_rows[k];
	if (r.row < 0) {
		// D2R's think is the expected value: a slot another plugin changed refuses the write
		if (!write(Slot(tableRva, monaiRow), d2rThink, Trampolines[k], user)) {
			plog::Warn("ai registry: monai %d think not swapped (the slot is not D2R's think)", monaiRow);
			return false;
		}
		r.row = monaiRow;
		r.vanilla = vanilla;
	}
	if (r.count == MaxClasses) {
		return false;
	}
	r.classes[r.count] = classId;
	r.thinks[r.count] = think;
	++r.count;
	plog::Info("ai registry: monai %d class %d -> registered think", monaiRow, classId);
	return true;
}

auto RegisterWith(SlotWriter write, void* user, int32_t monaiRow, uint64_t d2rThink, ThinkFn vanilla, int32_t classId,
                  ThinkFn think) noexcept -> bool {
	return RegisterWithTable(write, user, d2r::rva::AiTable, monaiRow, d2rThink, vanilla, classId, think);
}

void SetBeforeThink(BeforeThinkFn before) noexcept {
	g_before.store(before);
}

auto RegisterAtWith(SlotWriter write, void* user, const sigscan::Entry& table, int32_t monaiRow,
                    uint64_t d2rThinkAddress, int32_t classId, ThinkFn think) noexcept -> bool {
	// The image base comes from the entry (address - rva), not from d2r::imageBase, which is 0 off build 93847
	if (table.state != sigscan::State::Ok || table.address < table.rva) {
		return false;  // an unresolved entry: touch nothing
	}
	const uint64_t base = table.address - table.rva;
	if (d2rThinkAddress < base) {
		return false;
	}
	return RegisterWithTable(write, user, table.rva, monaiRow, d2rThinkAddress - base,
	                         reinterpret_cast<ThinkFn>(d2rThinkAddress), classId, think);
}

auto RegisterAt(const D2RL::PluginContext* context, int32_t monaiRow, uint64_t d2rThinkAddress, int32_t classId,
                ThinkFn think) noexcept -> bool {
	const sigscan::Entry& table = d2r::sig::AiTable;
	if (table.state != sigscan::State::Ok || table.address < table.rva) {
		return false;
	}
	Target target {context, table.address - table.rva};
	return RegisterAtWith(&WriteSlot, &target, table, monaiRow, d2rThinkAddress, classId, think);
}

auto Register(const D2RL::PluginContext* context, int32_t monaiRow, uint64_t d2rThink, int32_t classId,
              ThinkFn think) noexcept -> bool {
	if (d2r::imageBase == 0) {
		return false;  // Bind() refused the image or has not run: touch nothing
	}
	Target target {context, d2r::imageBase};
	return RegisterWith(&WriteSlot, &target, monaiRow, d2rThink, reinterpret_cast<ThinkFn>(d2r::imageBase + d2rThink),
	                    classId, think);
}

auto Vanilla(int32_t monaiRow) noexcept -> ThinkFn {
	for (const Row& r : g_rows) {
		if (r.row == monaiRow) {
			return r.vanilla;
		}
	}
	return nullptr;
}

void ResetForTest() noexcept {
	g_before.store(nullptr);
	for (Row& r : g_rows) {
		r = Row {};
	}
}

}  // namespace ai_registry
