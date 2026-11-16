// The AI registry's dispatch: a registered class goes to its think, every other monster and unit type to D2R's. A fake
// slot writer stands in for PatchWriteU64, so the test needs no game.
#include "ai_registry.h"

#include <cstdio>
#include <cstring>

namespace {

int g_failures = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

int g_calls[3] {};  // 0 D2R's think, 1 port A, 2 port B

void D2rThink(d2r::Game*, d2r::Unit*, uint8_t*) noexcept { ++g_calls[0]; }
void PortA(d2r::Game*, d2r::Unit*, uint8_t*) noexcept { ++g_calls[1]; }
void PortB(d2r::Game*, d2r::Unit*, uint8_t*) noexcept { ++g_calls[2]; }

struct Writes {
	int count = 0;
	uint64_t slot = 0;
	uint64_t expected = 0;
	bool accept = true;
};

auto Write(uint64_t slotRva, uint64_t expectedRva, ai_registry::ThinkFn, void* user) noexcept -> bool {
	auto* w = static_cast<Writes*>(user);
	++w->count;
	w->slot = slotRva;
	w->expected = expectedRva;
	return w->accept;
}

// A unit's first 8 bytes: type at +0, class id at +4.
struct FakeUnit {
	alignas(8) uint8_t bytes[0x40] = {};
	FakeUnit(int32_t type, int32_t classId) {
		std::memcpy(bytes + d2r::rva::UnitType, &type, 4);
		std::memcpy(bytes + d2r::rva::UnitClassId, &classId, 4);
	}
	auto unit() -> d2r::Unit* { return reinterpret_cast<d2r::Unit*>(bytes); }
};

void Run(int k, d2r::Unit* unit) { ai_registry::Dispatch(k, nullptr, unit, nullptr); }

}  // namespace

int main() {
	using namespace ai_registry;
	Writes w;
	ResetForTest();

	Check(!RegisterWith(&Write, &w, -1, 0x5b1ca0, &D2rThink, 5, &PortA), "a negative row is refused");
	Check(!RegisterWith(&Write, &w, d2r::rva::AiRows, 0x5b1ca0, &D2rThink, 5, &PortA), "a row past monai.txt is refused");
	Check(!RegisterWith(&Write, &w, 3, 0x5b1ca0, &D2rThink, 5, nullptr), "a null think is refused");
	Check(w.count == 0, "refused registrations write no slot");

	Check(RegisterWith(&Write, &w, 3, 0x5b1ca0, &D2rThink, 5, &PortA), "first registration on a row succeeds");
	Check(w.count == 1 && w.slot == d2r::rva::AiTable + 3u * d2r::rva::AiRowSize && w.expected == 0x5b1ca0,
	      "it writes the row's slot, expecting D2R's think");
	Check(RegisterWith(&Write, &w, 3, 0x5b1ca0, &D2rThink, 6, &PortB), "a second class on the row succeeds");
	Check(w.count == 1, "the slot is written once per row");
	Check(Vanilla(3) == &D2rThink && Vanilla(4) == nullptr, "Vanilla() gives D2R's think of a registered row");

	FakeUnit a(1, 5), b(1, 6), other(1, 7), object(2, 5);
	Run(0, a.unit());
	Run(0, b.unit());
	Run(0, other.unit());
	Run(0, object.unit());
	Run(0, nullptr);
	Check(g_calls[1] == 1 && g_calls[2] == 1, "registered classes reach their own think");
	Check(g_calls[0] == 3, "another class, a non-monster and a null unit reach D2R's think");

	w.accept = false;
	Check(!RegisterWith(&Write, &w, 9, 0x5c8d40, &D2rThink, 5, &PortA), "a slot that is not D2R's think refuses the write");
	Check(Vanilla(9) == nullptr, "a refused row is not registered");
	w.accept = true;

	ResetForTest();
	bool full = true;
	for (int row = 0; row < MaxRows; ++row) {
		full = RegisterWith(&Write, &w, row, 0x5b1ca0, &D2rThink, 5, &PortA) && full;
	}
	Check(full, "MaxRows rows register");
	Check(!RegisterWith(&Write, &w, MaxRows, 0x5b1ca0, &D2rThink, 5, &PortA), "one row too many is refused");
	ResetForTest();
	bool classes = true;
	for (int c = 0; c < MaxClasses; ++c) {
		classes = RegisterWith(&Write, &w, 1, 0x5b1ca0, &D2rThink, c, &PortA) && classes;
	}
	Check(classes && !RegisterWith(&Write, &w, 1, 0x5b1ca0, &D2rThink, 99, &PortA), "MaxClasses classes per row, no more");

	// The table passed in, 16 rows, and the before-think callback
	ResetForTest();
	Check(RegisterWithTable(&Write, &w, 0x2000, 4, 0x5b1ca0, &D2rThink, 5, &PortA) &&
	          w.slot == 0x2000 + 4u * d2r::rva::AiRowSize,
	      "RegisterWithTable writes the slot in the given table");
	Check(MaxRows == 16, "sixteen rows");
	ResetForTest();
	for (int row = 0; row < MaxRows; ++row) {
		RegisterWith(&Write, &w, row, 0x5b1ca0, &D2rThink, 5, &PortA);
	}
	Check(Vanilla(MaxRows - 1) == &D2rThink, "the last of 16 rows registers");
	g_calls[1] = 0;
	SetBeforeThink([](d2r::Unit*, int32_t classId) noexcept { g_calls[1] += 100 + classId; });
	FakeUnit c(1, 5), d(1, 9);
	Run(0, c.unit());
	Run(0, d.unit());
	Check(g_calls[1] == 100 + 5 + 1, "the callback runs before a registered think, not before D2R's");
	SetBeforeThink(nullptr);
	Check(!RegisterAt(nullptr, 3, 0x1000, 5, &PortA), "RegisterAt refuses when the image is not bound");

	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
