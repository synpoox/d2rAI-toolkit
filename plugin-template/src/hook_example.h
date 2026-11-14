// Example inline hook on a D2R function, found by its signature (build 93847's cache). See hook_example.cpp.
#pragma once

#include "sig.h"

#include <D2RLPlugin/api.h>

#include <cstddef>
#include <cstdint>
#include <span>

// This plugin's own engine address for the hook: resolve it after d2r::Bind() (cache on a known build, else a scan),
// and gate the hook part on it (its `uses`).
void ResolveHookExample(uint64_t exeBase) noexcept;
auto HookExampleUses() noexcept -> std::span<sigscan::Entry* const>;

auto InstallHookExample(const D2RL::PluginContext* context, char* report, size_t reportSize) noexcept -> bool;
auto HookExampleCalls() noexcept -> int64_t;  // how often the hooked function ran since load
