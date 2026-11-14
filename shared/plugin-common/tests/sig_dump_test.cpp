// Build 93847's dump: a scan (no cache) resolves every shared signature entry, and to the RVA its build cache holds
// (signatures.h checks at compile time that the cache equals the fixed rva:: values). Needs the memory-layout dump
// (tools/dump_image.py): D2R_DUMP_93847, else <MODKIT_GHIDRA_WORK or C:/ghidra-work>/D2RLoader_6ab3782c_dump.exe.
// Skipped (exit 77) without one: game files never go in the repo.
#define _CRT_SECURE_NO_WARNINGS
#include "signatures.h"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <iterator>
#include <string>

int main() {
	std::string path;
	if (const char* p = std::getenv("D2R_DUMP_93847"); p != nullptr && *p != '\0') {
		path = p;
	} else {
		const char* work = std::getenv("MODKIT_GHIDRA_WORK");
		path = std::string(work != nullptr && *work != '\0' ? work : "C:/ghidra-work") + "/D2RLoader_6ab3782c_dump.exe";
	}
	FILE* file = std::fopen(path.c_str(), "rb");
	if (file == nullptr) {
		std::printf("skip: no build 93847 dump at %s\n", path.c_str());
		return 77;
	}
	std::fseek(file, 0, SEEK_END);
	const long size = std::ftell(file);
	std::fseek(file, 0, SEEK_SET);
	// Page-aligned, as an image; the dump's file offsets are its RVAs
	auto* image = static_cast<uint8_t*>(VirtualAlloc(nullptr, static_cast<size_t>(size), MEM_COMMIT | MEM_RESERVE,
	                                                  PAGE_READWRITE));
	const bool read = image != nullptr && std::fread(image, 1, static_cast<size_t>(size), file) == static_cast<size_t>(size);
	std::fclose(file);
	if (!read) {
		std::printf("FAIL: cannot read %s\n", path.c_str());
		return 1;
	}

	const auto start = std::chrono::steady_clock::now();
	sigscan::Resolve(d2r::sig::Shared, std::size(d2r::sig::Shared), reinterpret_cast<uint64_t>(image), nullptr, 0);
	const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();

	int failures = 0;
	for (const sigscan::CacheRow& row : d2r::sig::Cache6ab3782c) {
		const sigscan::Entry& e = *row.entry;
		if (e.state == sigscan::State::CacheOnly) {
			std::printf("note: %s is cache only (pattern \"\")\n", e.name);
			continue;
		}
		if (e.state != sigscan::State::Ok || e.rva != row.rva) {
			std::printf("FAIL: %s %s, rva 0x%llx, the cache says 0x%llx\n", e.name, sigscan::StateText(e.state),
			            static_cast<unsigned long long>(e.rva), static_cast<unsigned long long>(row.rva));
			++failures;
		}
	}
	const bool complete = std::size(d2r::sig::Cache6ab3782c) == std::size(d2r::sig::Shared);
	std::printf("%s: the cache holds every shared entry (%zu of %zu)\n", complete ? "ok  " : "FAIL",
	            std::size(d2r::sig::Cache6ab3782c), std::size(d2r::sig::Shared));
	failures += complete ? 0 : 1;
	std::printf("%zu entries scanned in %lld ms, %d failure(s)\n", std::size(d2r::sig::Shared), static_cast<long long>(ms),
	            failures);

	// With the cache: no scan, every entry from it
	sigscan::Resolve(d2r::sig::Shared, std::size(d2r::sig::Shared), reinterpret_cast<uint64_t>(image), d2r::sig::Caches,
	                 std::size(d2r::sig::Caches));
	int cached = 0;
	for (const sigscan::Entry* e : d2r::sig::Shared) {
		cached += e->cached && e->state == sigscan::State::Ok ? 1 : 0;
	}
	std::printf("%s: the stamp takes the cache for all %d\n", cached == static_cast<int>(std::size(d2r::sig::Shared)) ? "ok  " : "FAIL",
	            cached);
	failures += cached == static_cast<int>(std::size(d2r::sig::Shared)) ? 0 : 1;
	return failures == 0 ? 0 : 1;
}
