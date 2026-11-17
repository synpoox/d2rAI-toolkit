#include "sig.h"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <cstring>

namespace sigscan {

namespace {

auto Hex(char c) noexcept -> int {
	if (c >= '0' && c <= '9') {
		return c - '0';
	}
	if (c >= 'a' && c <= 'f') {
		return c - 'a' + 10;
	}
	if (c >= 'A' && c <= 'F') {
		return c - 'A' + 10;
	}
	return -1;
}

struct Section {
	uint32_t rva, size;
};

// The executable sections and SizeOfImage of the PE image at base; false when there is no PE header.
auto ReadSections(uint64_t base, Section* out, int cap, int* count, uint32_t* imageSize) noexcept -> bool {
	*count = 0;
	*imageSize = 0;
	if (base == 0) {
		return false;
	}
	const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
	if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
		return false;
	}
	const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(base + static_cast<uint64_t>(dos->e_lfanew));
	if (nt->Signature != IMAGE_NT_SIGNATURE) {
		return false;
	}
	*imageSize = nt->FileHeader.SizeOfOptionalHeader >= offsetof(IMAGE_OPTIONAL_HEADER64, SizeOfImage) + 4
	                 ? nt->OptionalHeader.SizeOfImage
	                 : 0;
	const auto* section = IMAGE_FIRST_SECTION(nt);
	for (int i = 0; i < nt->FileHeader.NumberOfSections && *count < cap; ++i, ++section) {
		if ((section->Characteristics & IMAGE_SCN_MEM_EXECUTE) != 0 && section->Misc.VirtualSize != 0) {
			out[(*count)++] = {section->VirtualAddress, section->Misc.VirtualSize};
		}
	}
	return true;
}

}  // namespace

auto Parse(const char* pattern, uint8_t* bytes, bool* fixed) noexcept -> int {
	if (pattern == nullptr) {
		return -1;
	}
	int n = 0;
	bool anyFixed = false;
	for (const char* p = pattern; *p != '\0';) {
		if (*p == ' ') {
			++p;
			continue;
		}
		if (n == static_cast<int>(MaxPattern) || p[1] == '\0' || (p[2] != ' ' && p[2] != '\0')) {
			return -1;
		}
		if (p[0] == '?' && p[1] == '?') {
			fixed[n] = false;
			bytes[n] = 0;
		} else {
			const int hi = Hex(p[0]), lo = Hex(p[1]);
			if (hi < 0 || lo < 0) {
				return -1;
			}
			fixed[n] = true;
			bytes[n] = static_cast<uint8_t>(hi * 16 + lo);
			anyFixed = true;
		}
		++n;
		p += 2;
	}
	return anyFixed ? n : -1;
}

auto Find(const uint8_t* data, size_t size, const char* pattern, size_t* first, int limit,
          const uint32_t* histogram) noexcept -> int {
	uint8_t bytes[MaxPattern];
	bool fixed[MaxPattern];
	const int len = Parse(pattern, bytes, fixed);
	if (len < 0) {
		return -1;
	}
	const size_t n = static_cast<size_t>(len);
	if (size < n) {
		return 0;
	}
	size_t anchor = n;
	for (size_t i = 0; i < n; ++i) {
		if (fixed[i] && (anchor == n || (histogram != nullptr && histogram[bytes[i]] < histogram[bytes[anchor]]))) {
			anchor = i;
		}
	}
	int found = 0;
	const uint8_t* const last = data + (size - n) + anchor;  // the anchor of the last possible match
	for (const uint8_t* p = data + anchor; p <= last && found < limit; ++p) {
		p = static_cast<const uint8_t*>(std::memchr(p, bytes[anchor], static_cast<size_t>(last - p) + 1));
		if (p == nullptr) {
			break;
		}
		const uint8_t* start = p - anchor;
		size_t i = 0;
		while (i < n && (!fixed[i] || start[i] == bytes[i])) {
			++i;
		}
		if (i == n) {
			if (found++ == 0 && first != nullptr) {
				*first = static_cast<size_t>(start - data);
			}
		}
	}
	return found;
}

auto Target(const Entry& entry, const uint8_t* image, const uint8_t* match) noexcept -> int64_t {
	const int64_t at = (match - image) + entry.at;
	if (entry.kind == Kind::Code) {
		return at;
	}
	int32_t field;
	std::memcpy(&field, match + entry.at, 4);
	return entry.kind == Kind::Rip ? (match - image) + entry.next + field
	                               : static_cast<int64_t>(static_cast<uint32_t>(field)) + entry.next;
}

void Resolve(Entry* const* entries, size_t count, uint64_t exeBase, const Cache* caches, size_t cacheCount) noexcept {
	for (size_t i = 0; i < count; ++i) {
		Entry& e = *entries[i];
		e.state = State::Unresolved;
		e.cached = false;
		e.rva = e.address = 0;
	}
	Section exec[16];
	int execCount = 0;
	uint32_t imageSize = 0;
	if (!ReadSections(exeBase, exec, 16, &execCount, &imageSize)) {
		for (size_t i = 0; i < count; ++i) {
			entries[i]->state = State::NotFound;
		}
		return;
	}
	const auto* image = reinterpret_cast<const uint8_t*>(exeBase);
	const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(
		exeBase + static_cast<uint64_t>(reinterpret_cast<const IMAGE_DOS_HEADER*>(exeBase)->e_lfanew));
	const uint32_t stamp = nt->FileHeader.TimeDateStamp;
	for (size_t c = 0; c < cacheCount; ++c) {
		if (caches[c].stamp != stamp) {
			continue;
		}
		for (size_t r = 0; r < caches[c].count; ++r) {
			Entry& e = *caches[c].rows[r].entry;
			e.state = State::Ok;
			e.cached = true;
			e.rva = caches[c].rows[r].rva;
			e.address = exeBase + e.rva;
		}
	}
	uint32_t histogram[256] = {};
	bool counted = false;
	for (size_t i = 0; i < count; ++i) {
		Entry& e = *entries[i];
		if (e.state == State::Ok) {
			continue;
		}
		if (e.pattern != nullptr && e.pattern[0] == '\0') {
			e.state = State::CacheOnly;
			continue;
		}
		uint8_t bytes[MaxPattern];
		bool fixed[MaxPattern];
		const int len = Parse(e.pattern, bytes, fixed);
		if (len < 0 || e.at < 0 || (e.kind == Kind::Code ? e.at >= len : e.at + 4 > len)) {
			e.state = State::BadPattern;
			continue;
		}
		if (!counted) {  // once, and only when something is scanned
			for (int s = 0; s < execCount; ++s) {
				for (uint32_t b = 0; b < exec[s].size; ++b) {
					++histogram[image[exec[s].rva + b]];
				}
			}
			counted = true;
		}
		int found = 0;
		const uint8_t* match = nullptr;
		for (int s = 0; s < execCount && found < 2; ++s) {
			size_t first = 0;
			const int n = Find(image + exec[s].rva, exec[s].size, e.pattern, &first, 2 - found, histogram);
			if (n > 0 && found == 0) {
				match = image + exec[s].rva + first;
			}
			found += n;
		}
		if (found != 1) {
			e.state = found == 0 ? State::NotFound : State::Ambiguous;
			continue;
		}
		const int64_t target = Target(e, image, match);
		bool inside = target > 0 && target < static_cast<int64_t>(imageSize);
		if (inside && e.kind == Kind::Code) {
			inside = false;
			for (int s = 0; s < execCount; ++s) {
				inside = inside || (target >= exec[s].rva && target < static_cast<int64_t>(exec[s].rva) + exec[s].size);
			}
		}
		if (!inside) {
			e.state = State::OutOfImage;
			continue;
		}
		e.state = State::Ok;
		e.rva = static_cast<uint64_t>(target);
		e.address = exeBase + e.rva;
	}
}

auto ScanUnique(uint64_t exeBase, const char* pattern, int offset, uint64_t* rva) noexcept -> int {
	Section exec[16];
	int execCount = 0;
	uint32_t imageSize = 0;
	if (!ReadSections(exeBase, exec, 16, &execCount, &imageSize)) {
		return -1;
	}
	const auto* image = reinterpret_cast<const uint8_t*>(exeBase);
	int found = 0;
	int64_t target = 0;
	for (int s = 0; s < execCount && found < 64; ++s) {
		size_t first = 0;
		const int n = Find(image + exec[s].rva, exec[s].size, pattern, &first, 64 - found);
		if (n < 0) {
			return -1;
		}
		if (n > 0 && found == 0) {
			target = static_cast<int64_t>(exec[s].rva + first) + offset;
		}
		found += n;
	}
	if (found != 1) {
		return found;
	}
	for (int s = 0; s < execCount; ++s) {
		if (target >= exec[s].rva && target < static_cast<int64_t>(exec[s].rva) + exec[s].size) {
			*rva = static_cast<uint64_t>(target);
			return 1;
		}
	}
	return -1;
}

auto StateText(State state) noexcept -> const char* {
	switch (state) {
	case State::Ok: return "found";
	case State::NotFound: return "not found";
	case State::Ambiguous: return "found more than once";
	case State::BadPattern: return "has a bad pattern";
	case State::OutOfImage: return "points outside the image";
	case State::CacheOnly: return "has no signature (known builds only)";
	case State::Unresolved: break;
	}
	return "not resolved (Bind not run)";
}

}  // namespace sigscan
