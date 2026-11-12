// Parts: the table every plugin built with this toolkit installs from. A part is one feature with its own install
// function and one word (the word the "<plugin>-off.txt" file uses to leave it out, and the label in the log and the
// status command). One table row per part:
//
//   parts::Part g_parts[] = {
//       {"envguard", false, InstallEnvironment},          // no game address: runs on any image
//       {"skills",   true,  InstallSkills},               // uses game addresses: installed only on the expected image
//       {"hook",     true,  InstallHook, HookState},      // optional: a live state line for the status command
//   };
//   parts::InstallAll(g_parts, std::size(g_parts), context, PluginName, d2r::Bind(context->exeBase));
//   // in the console command:
//   parts::WriteStatus(g_parts, std::size(g_parts), command);
//
// Rule 6: a part with `engine` set is never installed on an image other than the one rvas_93847.h describes (the
// caller passes the result of d2r::Bind()); its report says so instead.
#pragma once

#include <D2RLPlugin/api.h>

#include <cstddef>

namespace parts {

using InstallFn = void (*)(const D2RL::PluginContext* context, char* report, size_t size) noexcept;

struct Part;
// A live state line for the status command (counters, queue depth): writes into `out`. Optional.
using StateFn = void (*)(const Part& part, char* out, size_t size) noexcept;

struct Part {
	const char* word;  // off-file word and status label
	bool engine;       // uses game addresses: installed only on the expected image
	InstallFn install;
	StateFn state = nullptr;
	char report[512] = "";  // what the install said, or why the part is off
};

// Why a part is not installed ("" when it is): left out by the off file, or an engine part on an unexpected image.
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
