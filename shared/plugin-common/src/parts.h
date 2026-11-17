// Parts: the table every plugin built with this toolkit installs from. A part is one feature with its own install
// function and one word (the word the "<plugin>-off.txt" file uses to leave it out, and the label in the log and the
// status command). One table row per part:
//
//   parts::Part g_parts[] = {
//       {"envguard", false, InstallEnvironment},          // no game address: runs on any image
//       {"skills",   true,  InstallSkills},               // uses game addresses: installed only on the expected image
//       {"hook",     true,  InstallHook, HookState},      // optional: a live state line for the status command
//       {"calls",    true,  InstallCalls, nullptr, CallsUses},  // reads only signature entries: see below
//   };
//   parts::InstallAll(g_parts, std::size(g_parts), context, PluginName, d2r::Bind(context->exeBase));
//   // in the console command:
//   parts::WriteStatus(g_parts, std::size(g_parts), command);
//
// Rule 6, the image gate, two ways:
// - an engine part with `uses` (the signature entries it reads, sig.h / signatures.h):
//       sigscan::Entry* const CallsUses[] = {&d2r::sig::CreateMissile, &d2r::sig::SrvDoTable};
//   installs on any image where every one of them resolved; else it stays off and its report names the entry.
// - an engine part without `uses` (it reads fixed d2r::rva:: values) installs only on the image rvas_93847.h describes
//   (the caller passes the result of d2r::Bind()); its report says so instead.
#pragma once

#include "sig.h"

#include <D2RLPlugin/api.h>

#include <cstddef>
#include <span>

namespace parts {

using InstallFn = void (*)(const D2RL::PluginContext* context, char* report, size_t size) noexcept;

inline constexpr size_t ReportSize = 2800;  // room for a part that lists one entry per slot it installed

struct Part;
// A live state line for the status command (counters, queue depth): writes into `out`. Optional.
using StateFn = void (*)(const Part& part, char* out, size_t size) noexcept;

struct Part {
	const char* word;  // off-file word and status label
	bool engine;       // uses game addresses: installed only on the expected image
	InstallFn install;
	StateFn state = nullptr;
	std::span<sigscan::Entry* const> uses {};  // the signature entries it reads (engine parts gated by them, see above)
	char report[ReportSize] = "";  // what the install said, or why the part is off
};

// Why a part is not installed ("" when it is): left out by the off file, an entry in `uses` that did not resolve, or
// an engine part without `uses` on an image other than 93847's.
// Writes the reason into `out` and returns true when the part must be skipped.
auto SkipReason(const Part& part, bool imageOk, const char* pluginName, char* out, size_t size) noexcept -> bool;

// Fills every part's report (installing it unless skipped) and logs one line per part.
void InstallAll(Part* parts, size_t count, const D2RL::PluginContext* context, const char* pluginName,
                bool imageOk) noexcept;

// The status line of a part: its state function's line when it has one and the part is on, else its report.
void Line(const Part& part, char* out, size_t size) noexcept;

// Writes "<word> <line>" for every part to the console (and the log).
void WriteStatus(const Part* parts, size_t count, const D2RL::ConsoleCommandContext* command) noexcept;

}  // namespace parts
