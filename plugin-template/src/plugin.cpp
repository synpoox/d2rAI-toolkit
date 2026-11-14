// D2RLoader plugin entry point (template). Copy plugin-template/ into your mod project and extend it. The guards, off
// switch, log, crash guard and game bindings come from the toolkit's shared library (shared/plugin-common).
//
// Target: D2R 3.3.0 build 93847 under D2RLoader 1.3.1, PluginSDK 0.4.0.
//
// What it does at load:
//  - declares itself Shared (server + client behaviour), ModScopedOnly (loads only from
//    <game>/mods/<Mod>/d2rloader/plugins/ while that mod runs) and NativeHooks (patches game code);
//  - log.h: one log line for the plugin (version, D2R version, image stamp, mod, this DLL's path) and one per part;
//  - d2r::Bind() and build_guard.h: find the engine addresses by signature (a known build's cache, else a scan of the
//    image). A part gated on its addresses (`uses`) installs where all of them are found exactly once and stays off,
//    naming the address, where one is not; a part reading fixed RVAs installs only on build 93847's image. So a
//    D2R/D2RLoader update cannot make the plugin patch random code;
//  - off_switch.h: reads "<plugin>-off.txt" next to the DLL: words naming parts to leave out (bisecting a crash);
//  - crash_guard.h: logs a FAULT line (address, why, whether this plugin is on the stack) when the game faults;
//  - env_guard.h: warns when D2RLoader runs another mod, when this DLL is not in the mod's own folder, or when a second
//    copy of it is loaded; names the other plugins (no game address: runs even on a wrong image);
//  - installs each part and logs one line per part;
//  - registers the console command "<plugin>" that prints the state of every part.
//
// Adding a part: write Install<Part>(context, report, size) in its own file, add a row to g_parts (parts.h in plugin-common) with a one-word
// name (the word the off-file uses), whether it uses game addresses, if wanted a live state line, and the signature
// entries it reads (`uses`, see skill_functions.cpp and hook_example.cpp). It shows up in the log and the status command.
#include <D2RLPlugin/api.h>

#include "build_guard.h"
#include "crash_guard.h"
#include "d2r.h"
#include "env_guard.h"
#include "hook_example.h"
#include "item_type_check.h"
#include "log.h"
#include "off_switch.h"
#include "parts.h"
#include "skill_functions.h"
#include "sound_guard.h"

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iterator>

#ifndef MODKIT_PLUGIN_NAME
#define MODKIT_PLUGIN_NAME "mod-core"
#endif
#ifndef MODKIT_PLUGIN_VERSION
#define MODKIT_PLUGIN_VERSION "0.1.0"
#endif
#ifndef MODKIT_MOD_NAME
#define MODKIT_MOD_NAME ""  // the mod folder this plugin ships in (mods\<name>); "" skips the mod checks
#endif
#ifndef MODKIT_SOUND_ROWS
#define MODKIT_SOUND_ROWS 0  // rows of the mod's sounds.txt; 0 = the mod adds no sounds (no restart warning)
#endif

namespace {

constexpr const char* PluginName = MODKIT_PLUGIN_NAME;
constexpr const char* PluginVersion = MODKIT_PLUGIN_VERSION;

const D2RL::PluginContext* g_context = nullptr;
uint32_t g_stamp = 0;
char g_selfPath[520] = "?";

constexpr D2RL::PluginInfo Info {
	.infoSize    = D2RL::PluginInfoSize,
	.abiVersion  = D2RL_PLUGIN_ABI_VERSION,
	.id          = MODKIT_PLUGIN_NAME,
	.name        = MODKIT_PLUGIN_NAME,
	.version     = MODKIT_PLUGIN_VERSION,
	.author      = "d2r-modkit",
	.description = "Engine changes for this mod (skill functions, hooks, guards).",
	.flags       = D2RL::PluginFlags::Shared | D2RL::PluginFlags::ModScopedOnly | D2RL::PluginFlags::NativeHooks,
};

// --- Parts (the table and its install/status code are parts.h in plugin-common) ----------------------------------
void InstallSkills(const D2RL::PluginContext* context, char* report, size_t size) noexcept {
	char slots[400];
	const int n = InstallSkillFunctions(context, slots, sizeof(slots));
	std::snprintf(report, size, "%d/%d installed:%s", n, SkillFunctionCount(), slots);
}

void InstallHook(const D2RL::PluginContext* context, char* report, size_t size) noexcept {
	(void)InstallHookExample(context, report, size);
}

void InstallSounds(const D2RL::PluginContext* context, char* report, size_t size) noexcept {
	(void)InstallSoundGuard(context, MODKIT_SOUND_ROWS, report, size);
}

void InstallTypeIds(const D2RL::PluginContext* context, char* report, size_t size) noexcept {
	(void)CheckItemTypeIds(context, report, size);
}

void InstallEnvironment(const D2RL::PluginContext* context, char* report, size_t size) noexcept {
	StartEnvironmentGuard(context, MODKIT_MOD_NAME);
	EnvironmentStatus(report, size);
}

void EnvironmentState(const parts::Part&, char* out, size_t size) noexcept {
	EnvironmentStatus(out, size);
}

void SoundState(const parts::Part& part, char* out, size_t size) noexcept {
	char live[300];
	SoundGuardStatus(live, sizeof(live));
	std::snprintf(out, size, "%s | %s", part.report, live);
}

void HookState(const parts::Part& part, char* out, size_t size) noexcept {
	if (std::strncmp(part.report, "on", 2) != 0) {
		std::snprintf(out, size, "%s", part.report);
		return;
	}
	std::snprintf(out, size, "%s (%lld calls)", part.report, static_cast<long long>(HookExampleCalls()));
}

parts::Part g_parts[] = {
	{"envguard", false, InstallEnvironment, EnvironmentState},
	{"soundguard", true, InstallSounds, SoundState},
	{"typeids", true, InstallTypeIds},
	{"skills", true, InstallSkills, nullptr, SkillFunctionUses()},  // any build where its addresses are found
	{"hook", true, InstallHook, HookState, HookExampleUses()},
};

// --- Console command ----------------------------------------------------------------------------------------------
auto StatusCommand(D2R::Game::Client* client, const D2RL::ConsoleCommandContext* command, void* userData) noexcept
	-> D2RL::ConsoleCommandResult {
	(void)client;
	(void)userData;
	if (command == nullptr || command->plugin == nullptr || g_context == nullptr) {
		return D2RL::ConsoleCommandResult::Failed;
	}
	char line[1100];
	char image[200];
	build_guard::Describe(image, sizeof(image), g_stamp, g_context->buildVersion);
	std::snprintf(line, sizeof(line), "%s %s | %s | mod %s | file %s", PluginName, PluginVersion, image,
	              g_context->activeMod != nullptr ? g_context->activeMod : "?", g_selfPath);
	command->plugin->WriteConsoleMessage(line);
	if (off_switch::Words()[0] != '\0') {
		std::snprintf(line, sizeof(line), "off-file: %s", off_switch::Words());
		command->plugin->WriteConsoleMessage(line);
	}
	parts::WriteStatus(g_parts, std::size(g_parts), command);
	OtherPlugins(line, sizeof(line));
	command->plugin->WriteConsoleMessage(line);
	plog::Info("%s", line);  // also in the plugin log, for crash reports
	return D2RL::ConsoleCommandResult::Handled;
}

}  // namespace

D2RL_PLUGIN_EXPORT auto D2RLoaderGetPluginInfo() noexcept -> const D2RL::PluginInfo* {
	return &Info;
}

D2RL_PLUGIN_EXPORT auto D2RLoaderLoadPlugin(const D2RL::PluginContext* context) noexcept -> bool {
	if (context == nullptr) {
		return false;
	}
	g_context = context;
	plog::Init(context, PluginName);
	crash_guard::Install(PluginVersion, context->exeBase);
	g_stamp = build_guard::ImageStamp(context->exeBase);
	if (context->pluginPath != nullptr) {
		std::snprintf(g_selfPath, sizeof(g_selfPath), "%ls", context->pluginPath);
	}
	char image[200];
	build_guard::Describe(image, sizeof(image), g_stamp, context->buildVersion);
	plog::Info("%s loaded (mod %s, %s, file %s)", PluginVersion, context->activeMod != nullptr ? context->activeMod : "?", image, g_selfPath);
	off_switch::Read(context->pluginPath);
	if (off_switch::Words()[0] != '\0') {
		plog::Info("%s-off.txt leaves out: %s", PluginName, off_switch::Words());
	}
	// Resolves the shared engine addresses (d2r::sig) on any image; true only on build 93847, which parts without
	// `uses` (fixed d2r::rva:: values) need. Then this plugin's own entries.
	const bool imageOk = d2r::Bind(context->exeBase);
	ResolveHookExample(context->exeBase);
	if (!imageOk) {
		plog::Warn("not build 93847's image: parts with fixed addresses stay off, parts gated by signatures run where "
		           "their addresses are found");
	}
	parts::InstallAll(g_parts, std::size(g_parts), context, PluginName, imageOk);
	return context->RegisterConsoleCommand(PluginName, StatusCommand, "Status of this mod's engine plugin and its guards.");
}

D2RL_PLUGIN_EXPORT void D2RLoaderUnloadPlugin() noexcept {
	crash_guard::Remove();
	g_context = nullptr;
}
