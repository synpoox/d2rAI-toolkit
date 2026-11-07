// The image guard fails closed: Bind() binds nothing on an image whose PE stamp is not the one rvas_93847.h describes.
// A fake PE header stands in for the game image (Bind reads only the headers before it accepts an image).
#include "build_guard.h"
#include "d2r.h"

#include <cstdio>
#include <cstring>

namespace {

int g_failures = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

// DOS header + 64-bit NT headers with the given TimeDateStamp.
struct FakeImage {
	alignas(16) unsigned char bytes[0x200] = {};
	explicit FakeImage(uint32_t stamp) {
		auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(bytes);
		dos->e_magic = IMAGE_DOS_SIGNATURE;
		dos->e_lfanew = 0x80;
		auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(bytes + 0x80);
		nt->Signature = IMAGE_NT_SIGNATURE;
		nt->FileHeader.TimeDateStamp = stamp;
	}
	auto base() const -> uint64_t { return reinterpret_cast<uint64_t>(bytes); }
};

}  // namespace

int main() {
	Check(!build_guard::Matches(0x12345678), "Matches refuses an unknown stamp");
	Check(!build_guard::Matches(0), "Matches refuses stamp 0 (no image)");
	Check(build_guard::Matches(0x6ab3782c), "Matches accepts the 93847 stamp");

	const FakeImage unknown(0x12345678);
	Check(build_guard::ImageStamp(unknown.base()) == 0x12345678, "ImageStamp reads the PE TimeDateStamp");
	Check(!d2r::Bind(unknown.base()), "Bind refuses an image with an unknown stamp");
	Check(d2r::api.getSkillRecord == nullptr && d2r::api.createMissile == nullptr, "nothing is bound after the refusal");
	Check(d2r::imageBase == 0, "imageBase stays 0 after the refusal");

	unsigned char garbage[0x200];
	std::memset(garbage, 0xcc, sizeof(garbage));
	Check(!d2r::Bind(reinterpret_cast<uint64_t>(garbage)), "Bind refuses memory with no PE header");
	Check(!d2r::Bind(0), "Bind refuses a null image base");

	const FakeImage expected(0x6ab3782c);
	Check(d2r::Bind(expected.base()), "Bind accepts the 93847 stamp");
	Check(d2r::api.getSkillRecord != nullptr && d2r::imageBase == expected.base(), "Bind binds the table on that image");

	uint32_t seed[2] = {1, 2};
	Check(d2r::RandomBelow(seed, 0) == 0, "RandomBelow(0) is 0, no division");
	Check(d2r::RandomBelow(seed, 0xffffffffu) < 0xffffffffu && d2r::RandomBelow(seed, 0x80000000u) < 0x80000000u,
	      "RandomBelow keeps n above INT32_MAX");

	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
