// Engine addresses by byte signature: find an address in the running game image by a unique byte pattern instead of
// a fixed RVA, so a plugin keeps working on a D2R build whose code it can still find. README.md, "Engine addresses by
// signature", explains the format for mod authors.
//
// An entry is a pattern ("48 8b 05 ?? ?? ?? ?? 48 85 c0", `??` = any byte) that must match exactly once in the image's
// executable sections, and how to get the address from the match:
//   Code  address = match + at                                (a function entry, or a patch site inside one)
//                                                              at < 0: the pattern starts past a function entry that
//                                                              another plugin may hook (knowledge/engine-re.md)
//   Rip   address = match + next + int32 at (match + at)      (a call / jump / rip-relative operand pointing at it:
//                                                              `next` is where that instruction ends)
//   Abs   address = image + uint32 at (match + at) + next     (a disp32 that is the RVA itself, MSVC's
//                                                              image-base-relative table reads)
// `next` also carries a field offset for Rip / Abs: a table only read through `[table + 0x10]` points 0x10 past it.
// Pattern "" is cache only: the entry resolves on known builds and stays off on others (an address no code points
// at, such as D2RLoader's own slots).
// Resolve() fills every entry: from a per-build cache when the image's PE stamp has one (no scan), else by a scan.
#pragma once

#include <cstddef>
#include <cstdint>

namespace sigscan {

enum class Kind : uint8_t { Code, Rip, Abs };
enum class State : uint8_t { Unresolved, Ok, NotFound, Ambiguous, BadPattern, OutOfImage, CacheOnly };

struct Entry {
	const char* name;
	const char* area;  // the group it belongs to (a shared entry: its rvas_93847/<area>.h)
	Kind kind;
	int16_t at;
	int16_t next;
	const char* pattern;
	// Filled by Resolve()
	State state = State::Unresolved;
	bool cached = false;   // taken from the build's cache, not scanned
	uint64_t rva = 0;      // 0 unless Ok
	uint64_t address = 0;  // image base + rva, 0 unless Ok
};

// One build's cache: the RVA of each entry on the image with that PE TimeDateStamp (generated, sig/cache_*.inc).
struct CacheRow {
	Entry* entry;
	uint64_t rva;
};
struct Cache {
	uint32_t stamp;
	const CacheRow* rows;
	size_t count;
};

inline constexpr size_t MaxPattern = 256;

// "48 8b ?? 05" into bytes and a fixed mask; the length, or -1 for a bad pattern (bad token, longer than MaxPattern,
// or no fixed byte).
auto Parse(const char* pattern, uint8_t* bytes, bool* fixed) noexcept -> int;

// Matches of `pattern` in data[0, size), counted up to `limit` (2 is enough to tell one from several); *first gets the
// offset of the first. -1 for a bad pattern. `histogram` (256 byte counts of the data, optional) picks the rarest fixed
// byte as the one searched for.
auto Find(const uint8_t* data, size_t size, const char* pattern, size_t* first, int limit = 2,
          const uint32_t* histogram = nullptr) noexcept -> int;

// The address an entry gives for a match at `match` (Code / Rip / Abs above), as an offset from `image`.
auto Target(const Entry& entry, const uint8_t* image, const uint8_t* match) noexcept -> int64_t;

// Fills every entry for the PE image at exeBase: from the cache whose stamp is the image's (entries it lacks are
// scanned), else by scanning the executable sections. An entry is Ok only for exactly one match whose address lies in
// the image (in an executable section for Code).
void Resolve(Entry* const* entries, size_t count, uint64_t exeBase, const Cache* caches, size_t cacheCount) noexcept;

// One pattern, no Entry: how many times `pattern` matches in the executable sections of the image at exeBase (counted up to
// 64), and when exactly once, its RVA + `offset` (the offset from the match to e.g. a function entry, may be negative) in
// *rva, which must lie in an executable section. 0 = none, 1 = one match (*rva set), n > 1 = several, -1 = bad pattern,
// no PE image, or an offset that leaves the executable code (*rva is untouched unless 1).
auto ScanUnique(uint64_t exeBase, const char* pattern, int offset, uint64_t* rva) noexcept -> int;

// "not found", "several matches", ...
auto StateText(State state) noexcept -> const char*;

}  // namespace sigscan
