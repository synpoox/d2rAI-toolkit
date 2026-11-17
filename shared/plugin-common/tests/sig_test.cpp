// The signature matcher and resolver (sig.h) on made-up bytes and a made-up PE image, and the per-part gate. No game.
#include "parts.h"
#include "sig.h"
#include "sig_hook.h"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <cstdio>
#include <cstring>

namespace {

int g_failures = 0;
int g_installs = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

void Install(const D2RL::PluginContext*, char* report, size_t size) noexcept {
	++g_installs;
	std::snprintf(report, size, "on");
}

// Headers + one executable section at 0x1000 (0x100 bytes); SizeOfImage 0x3000.
struct FakeImage {
	alignas(16) uint8_t bytes[0x3000] = {};
	explicit FakeImage(uint32_t stamp) {
		auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(bytes);
		dos->e_magic = IMAGE_DOS_SIGNATURE;
		dos->e_lfanew = 0x80;
		auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(bytes + 0x80);
		nt->Signature = IMAGE_NT_SIGNATURE;
		nt->FileHeader.TimeDateStamp = stamp;
		nt->FileHeader.NumberOfSections = 1;
		nt->FileHeader.SizeOfOptionalHeader = sizeof(IMAGE_OPTIONAL_HEADER64);
		nt->OptionalHeader.SizeOfImage = sizeof(bytes);
		auto* text = IMAGE_FIRST_SECTION(nt);
		std::memcpy(text->Name, ".text", 5);
		text->VirtualAddress = 0x1000;
		text->Misc.VirtualSize = 0x100;
		text->Characteristics = IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_CNT_CODE;
		uint8_t* code = bytes + 0x1000;
		const uint8_t fn[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x57, 0x48, 0x83, 0xec, 0x20};  // at 0x1010
		std::memcpy(code + 0x10, fn, sizeof(fn));
		// lea rcx, [rip + x] at 0x1040 -> 0x2000: x = 0x2000 - 0x1047
		const uint8_t lea[] = {0x48, 0x8d, 0x0d, 0, 0, 0, 0, 0xc3, 0xaa};
		std::memcpy(code + 0x40, lea, sizeof(lea));
		const int32_t x = 0x2000 - 0x1047;
		std::memcpy(code + 0x43, &x, 4);
		// mov rax, [r8 + rcx*8 + 0x2100] at 0x1060 (an image-relative table read)
		const uint8_t abs[] = {0x49, 0x8b, 0x84, 0xc8, 0x00, 0x21, 0x00, 0x00, 0xbb};
		std::memcpy(code + 0x60, abs, sizeof(abs));
		// the same 3 bytes twice (ambiguous), and a jump far outside the image
		const uint8_t twice[] = {0xde, 0xad, 0xbe};
		std::memcpy(code + 0x80, twice, 3);
		std::memcpy(code + 0x90, twice, 3);
		const uint8_t jmpFar[] = {0xe9, 0x00, 0x00, 0x00, 0x40, 0xcd};  // jmp +0x40000000
		std::memcpy(code + 0xa0, jmpFar, sizeof(jmpFar));
	}
	auto base() const -> uint64_t { return reinterpret_cast<uint64_t>(bytes); }
};

[[maybe_unused]] auto* const g_hookCompiles = &sigscan::HookBySignature<void (*)() noexcept>;  // the header builds

}  // namespace

int main() {
	// --- Parse ---
	uint8_t b[sigscan::MaxPattern];
	bool f[sigscan::MaxPattern];
	Check(sigscan::Parse("48 8B ?? 05", b, f) == 4 && b[1] == 0x8b && !f[2] && f[3], "Parse: hex, either case, ??");
	Check(sigscan::Parse("  48   8b  ", b, f) == 2, "Parse: extra spaces");
	Check(sigscan::Parse("?? ??", b, f) == -1, "Parse: refuses a pattern with no fixed byte");
	Check(sigscan::Parse("4", b, f) == -1 && sigscan::Parse("488b", b, f) == -1 && sigscan::Parse("4g", b, f) == -1,
	      "Parse: refuses a bad token");
	Check(sigscan::Parse("", b, f) == -1 && sigscan::Parse(nullptr, b, f) == -1, "Parse: refuses an empty pattern");

	// --- Find ---
	const uint8_t data[] = {0x10, 0x48, 0x8b, 0x05, 0x11, 0x22, 0x48, 0x8b, 0x07, 0x33, 0x48, 0x8b};
	size_t first = 99;
	Check(sigscan::Find(data, sizeof(data), "48 8b 05", &first) == 1 && first == 1, "Find: one match, its offset");
	Check(sigscan::Find(data, sizeof(data), "48 8b ??", &first, 10) == 2 && first == 1,
	      "Find: a wildcard matches any byte (and the last 2 bytes are too short for a match)");
	Check(sigscan::Find(data, sizeof(data), "?? 8b", &first, 10) == 3, "Find: a pattern may start with ??");
	Check(sigscan::Find(data, sizeof(data), "48 8b", &first, 2) == 2, "Find: stops counting at the limit");
	Check(sigscan::Find(data, sizeof(data), "48 8c", &first) == 0, "Find: no match");
	Check(sigscan::Find(data, sizeof(data), "8b 33", &first) == 0, "Find: no match across the end");
	Check(sigscan::Find(data, sizeof(data), "33 48 8b", &first) == 1 && first == 9, "Find: a match ending at the end");
	Check(sigscan::Find(data, 2, "48 8b 05", &first) == 0, "Find: data shorter than the pattern");
	uint32_t histogram[256] = {};
	for (const uint8_t x : data) {
		++histogram[x];
	}
	Check(sigscan::Find(data, sizeof(data), "48 8b 07", &first, 2, histogram) == 1 && first == 6,
	      "Find: the same result searching for the rarest byte");
	Check(sigscan::Find(data, sizeof(data), "zz", &first) == -1, "Find: -1 for a bad pattern");

	// --- Resolve ---
	FakeImage image(0x11112222);
	sigscan::Entry code {"Code", "t", sigscan::Kind::Code, 5, 0, "48 89 5c 24 08 57"};
	sigscan::Entry rip {"Rip", "t", sigscan::Kind::Rip, 3, 7, "48 8d 0d ?? ?? ?? ?? c3"};
	sigscan::Entry abs {"Abs", "t", sigscan::Kind::Abs, 4, 0, "49 8b 84 c8 ?? ?? ?? ?? bb"};
	sigscan::Entry none {"None", "t", sigscan::Kind::Code, 0, 0, "11 22 33 44"};
	sigscan::Entry twice {"Twice", "t", sigscan::Kind::Code, 0, 0, "de ad be"};
	sigscan::Entry outside {"Outside", "t", sigscan::Kind::Rip, 1, 5, "e9 ?? ?? ?? ?? cd"};
	sigscan::Entry bad {"Bad", "t", sigscan::Kind::Rip, 2, 6, "e9 ?? ??"};  // the field runs past the pattern
	sigscan::Entry* all[] = {&code, &rip, &abs, &none, &twice, &outside, &bad};
	sigscan::Resolve(all, 7, image.base(), nullptr, 0);
	Check(code.state == sigscan::State::Ok && code.rva == 0x1015 && code.address == image.base() + 0x1015 && !code.cached,
	      "Resolve Code: match + at");
	Check(rip.state == sigscan::State::Ok && rip.rva == 0x2000, "Resolve Rip: follows the rip-relative operand");
	Check(abs.state == sigscan::State::Ok && abs.rva == 0x2100, "Resolve Abs: the disp32 is the RVA");
	Check(none.state == sigscan::State::NotFound && none.address == 0, "Resolve: no match -> NotFound, address 0");
	Check(twice.state == sigscan::State::Ambiguous && twice.address == 0, "Resolve: two matches -> Ambiguous");
	Check(outside.state == sigscan::State::OutOfImage, "Resolve: an address outside the image is refused");
	Check(bad.state == sigscan::State::BadPattern, "Resolve: an operand past the pattern's end is refused");

	const sigscan::CacheRow rows[] = {{&none, 0x1234}};
	const sigscan::Cache caches[] = {{0x99999999, rows, 1}, {0x11112222, rows, 1}};
	sigscan::Resolve(all, 7, image.base(), caches, 2);
	Check(none.state == sigscan::State::Ok && none.cached && none.rva == 0x1234, "Resolve: a known stamp takes the cache");
	Check(code.state == sigscan::State::Ok && !code.cached, "Resolve: entries the cache lacks are still scanned");
	const sigscan::Cache other[] = {{0x99999999, rows, 1}};
	sigscan::Resolve(all, 7, image.base(), other, 1);
	Check(none.state == sigscan::State::NotFound && !none.cached, "Resolve: another build's cache is not used");
	sigscan::Resolve(all, 7, 0, caches, 2);
	Check(code.state == sigscan::State::NotFound && code.address == 0, "Resolve: no image resolves nothing");

	// A fixed RVA valid only on one stamp: pattern "" and a row in that build's cache
	sigscan::Entry fixed {"Fixed", "t", sigscan::Kind::Code, 0, 0, ""};
	sigscan::Entry* fixedOnly[] = {&fixed};
	const sigscan::CacheRow fixedRows[] = {{&fixed, 0x1500}};
	const sigscan::Cache fixedCache[] = {{0x11112222, fixedRows, 1}};
	sigscan::Resolve(fixedOnly, 1, image.base(), fixedCache, 1);
	Check(fixed.state == sigscan::State::Ok && fixed.rva == 0x1500, "a fixed entry resolves on its stamp");
	FakeImage otherBuild(0x33334444);
	sigscan::Resolve(fixedOnly, 1, otherBuild.base(), fixedCache, 1);
	Check(fixed.state == sigscan::State::CacheOnly && fixed.address == 0, "a fixed entry stays off on any other stamp");

	// --- ScanUnique ---
	uint64_t r = 7;
	Check(sigscan::ScanUnique(image.base(), "48 89 5c 24 08 57", 0, &r) == 1 && r == 0x1010, "ScanUnique: one match, its RVA");
	Check(sigscan::ScanUnique(image.base(), "48 89 5c 24 08 57", 5, &r) == 1 && r == 0x1015, "ScanUnique: offset from the match");
	Check(sigscan::ScanUnique(image.base(), "48 8d 0d ?? ?? ?? ?? c3", 0, &r) == 1 && r == 0x1040, "ScanUnique: ?? wildcards");
	r = 7;
	Check(sigscan::ScanUnique(image.base(), "11 22 33 44", 0, &r) == 0 && r == 7, "ScanUnique: no match -> 0");
	Check(sigscan::ScanUnique(image.base(), "de ad be", 0, &r) == 2 && r == 7, "ScanUnique: two matches -> 2, no RVA");
	Check(sigscan::ScanUnique(image.base(), "48 89 5c 24 08 57", 0x2000, &r) == -1, "ScanUnique: offset out of the code -> -1");
	Check(sigscan::ScanUnique(image.base(), "zz", 0, &r) == -1 && sigscan::ScanUnique(0, "48 89", 0, &r) == -1,
	      "ScanUnique: bad pattern or no image -> -1");

	// --- Parts gated by their entries ---
	sigscan::Resolve(all, 7, image.base(), nullptr, 0);
	sigscan::Entry* const goodUses[] = {&code, &rip};
	sigscan::Entry* const badUses[] = {&code, &twice};
	parts::Part table[] = {
		{"found", true, Install, nullptr, goodUses},
		{"missing", true, Install, nullptr, badUses},
		{"legacy", true, Install},
	};
	parts::InstallAll(table, 3, nullptr, "test-plugin", false);
	Check(std::strcmp(table[0].report, "on") == 0, "a part whose entries all resolved installs on any image");
	Check(std::strcmp(table[1].report, "off: engine address Twice found more than once on this game image") == 0,
	      "a part with an unresolved entry stays off and names it");
	Check(std::strncmp(table[2].report, "off: game image differs", 23) == 0, "a part without uses keeps the image gate");
	Check(g_installs == 1, "only the gated-in part installed");

	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
