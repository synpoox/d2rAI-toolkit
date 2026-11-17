// Hook a function found by a unique byte signature at load, never by a fixed RVA (knowledge/engine-re.md,
// "Resolve addresses by signature"): moving to a new D2R build means the pattern still finds it, or the hook stays off.
#pragma once

#include "log.h"
#include "sig.h"

#include <D2RLPlugin/api.h>

#include <cstdint>

namespace sigscan {

// Resolves `pattern` (+ `offset` from the match to the function entry) and installs the inline hook there. `entry` /
// `entrySize` are the expected entry bytes the SDK checks. Logs "found <name> at <rva>" or "skipped <name>: <n> matches"
// and returns false when it is not exactly one match or the SDK refuses the hook; *original is the trampoline.
template <typename Function>
auto HookBySignature(const D2RL::PluginContext* context, const char* name, const char* pattern, int offset,
                     const void* entry, uint32_t entrySize, Function hook, Function* original) noexcept -> bool {
	uint64_t rva = 0;
	const int n = ScanUnique(context->exeBase, pattern, offset, &rva);
	if (n != 1) {
		plog::Warn("skipped %s: %d matches", name, n < 0 ? 0 : n);
		return false;
	}
	plog::Info("found %s at 0x%llx", name, static_cast<unsigned long long>(rva));
	return context->InstallInlineHook(rva, entry, entrySize, hook, original);
}

}  // namespace sigscan
