// Inline hook example: D2R's Whirlwind hit delay, found by its signature, passed through unchanged and counted.
//
// 0x56ac00 (unit, weapon) -> frames until Whirlwind's next hit. Only Whirlwind's do function calls it (its body is at 0x568f40; slot 76 of the do table holds a jmp thunk at
// 0x568f30), so the hook runs whenever a Whirlwind is in progress (the status command shows the count). To change behaviour (for
// example a classic mod's own hit delays), return your own value.
//
// The pattern, for any function:
//  1. Find the function in Ghidra (tools/ghidra_query.ps1 Decompile.java / Disasm.java 0x<rva>) and work out its
//     arguments and return type.
//  2. Copy its first bytes from the disassembly: WHOLE instructions, REX prefixes included (40 53 = push rbx), ending
//     on an instruction boundary. No fixed minimum: sound_guard.cpp hooks with 8-byte signatures and runs in game.
//     The bytes are both a safety check (wrong image, or someone else patched it -> the hook is refused, nothing
//     changes) and what D2RLoader relocates into the trampoline that becomes `original`.
//  3. Check first whether D2RLoader already hooks the function: an entry of FF 25 (jmp [rip+x]) means D2RLoader (or
//     another plugin) replaced it. Do not stack a second hook on it; use the D2RLoader service/export instead, or
//     hook a caller/callee. This file shows the check.
//  4. Declare its address as a signature entry (README.md, "Engine addresses by signature"; plugin-common's
//     README explains the format): a pattern that matches only there, with `??` over rip-relative displacements and
//     call targets, plus the RVA on each build you know in a cache. tools/make_signatures.py in the toolkit shows how
//     patterns are made from a dump. On a known build the cache gives the address; on another one the scan does, and
//     when it finds the pattern 0 or 2+ times, the part stays off and names the entry.
//  5. Declare the function type noexcept (the SDK's InstallInlineHook template requires a function pointer; the
//     game cannot unwind C++ exceptions) and keep the original pointer to call through.
#include "hook_example.h"

#include <cstdio>
#include <intrin.h>
#include <iterator>

namespace {

// (unit, weapon) -> frames until the next Whirlwind hit: its entry, then up to a rip-relative load (the security cookie)
sigscan::Entry g_hitDelay {"WhirlwindHitDelay", "hook", sigscan::Kind::Code, 0, 0,
                           "48 89 5c 24 18 55 56 57 41 56 41 57 48 81 ec 80 00 00 00 48 8b 05 ?? ?? ?? ?? 48 33 c4 "
                           "48 89 44 24 78 45 33 ff"};
sigscan::Entry* const g_entries[] = {&g_hitDelay};
// Its RVA on each known build (stamp): no scan there
constexpr sigscan::CacheRow Cache93847[] = {{&g_hitDelay, 0x56ac00}};
constexpr sigscan::Cache Caches[] = {{0x6ab3782c, Cache93847, 1}};

// MOV [RSP+0x18],RBX (48 89 5c 24 18) / PUSH RBP (55) / PUSH RSI (56) / PUSH RDI (57) / PUSH R14 (41 56) /
// PUSH R15 (41 57) / SUB RSP,0x80 (48 81 ec 80 00 00 00): 19 bytes, 7 whole instructions.
constexpr uint8_t HitDelayEntry[] = {0x48, 0x89, 0x5c, 0x24, 0x18, 0x55, 0x56, 0x57, 0x41, 0x56,
                                     0x41, 0x57, 0x48, 0x81, 0xec, 0x80, 0x00, 0x00, 0x00};
static_assert(sizeof(HitDelayEntry) >= 1, "whole instructions; see engine-re.md section 6");

using HitDelayFn = int32_t (*)(void* unit, void* weapon) noexcept;

HitDelayFn g_original = nullptr;  // trampoline: D2R's original function, set by InstallInlineHook
volatile long long g_calls = 0;

// The replacement. Same signature as the original; calls it and returns its value unchanged.
auto HitDelay(void* unit, void* weapon) noexcept -> int32_t {
	_InterlockedIncrement64(&g_calls);
	return g_original(unit, weapon);
}

// True when the function entry already starts with jmp [rip+x] (FF 25), i.e. D2RLoader or a plugin hooked it.
auto AlreadyHooked(uint64_t exeBase, uint64_t rva) noexcept -> bool {
	const auto* entry = reinterpret_cast<const uint8_t*>(exeBase + rva);
	return entry[0] == 0xff && entry[1] == 0x25;
}

}  // namespace

void ResolveHookExample(uint64_t exeBase) noexcept {
	sigscan::Resolve(g_entries, std::size(g_entries), exeBase, Caches, std::size(Caches));
}

auto HookExampleUses() noexcept -> std::span<sigscan::Entry* const> {
	return g_entries;
}

auto InstallHookExample(const D2RL::PluginContext* context, char* report, size_t reportSize) noexcept -> bool {
	const uint64_t HitDelayRva = g_hitDelay.rva;  // the part runs only when it resolved (its `uses`)
	if (AlreadyHooked(context->exeBase, HitDelayRva)) {
		std::snprintf(report, reportSize, "off: 0x%llx is already hooked (jmp [rip+x] at its entry)",
		              static_cast<unsigned long long>(HitDelayRva));
		return false;
	}
	const bool ok = context->InstallInlineHook(HitDelayRva, HitDelayEntry, sizeof(HitDelayEntry), HitDelay, &g_original);
	std::snprintf(report, reportSize, ok ? "on: whirlwind hit delay 0x%llx counted" : "off: hook on 0x%llx refused (entry bytes differ)",
	              static_cast<unsigned long long>(HitDelayRva));
	return ok;
}

auto HookExampleCalls() noexcept -> int64_t {
	return g_calls;
}
