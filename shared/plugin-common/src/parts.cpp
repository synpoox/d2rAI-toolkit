#include "parts.h"

#include "log.h"
#include "off_switch.h"

#include <cstdio>
#include <cstring>

namespace parts {

auto SkipReason(const Part& part, bool imageOk, const char* pluginName, char* out, size_t size) noexcept -> bool {
	if (off_switch::Off(part.word)) {
		std::snprintf(out, size, "off: left out by %s-off.txt", pluginName);
		return true;
	}
	if (part.engine && !imageOk) {
		std::snprintf(out, size, "off: game image differs from the one this plugin was built for");
		return true;
	}
	return false;
}

void InstallAll(Part* parts, size_t count, const D2RL::PluginContext* context, const char* pluginName,
                bool imageOk) noexcept {
	for (size_t i = 0; i < count; ++i) {
		Part& p = parts[i];
		p.report[0] = '\0';
		if (!SkipReason(p, imageOk, pluginName, p.report, sizeof(p.report)) && p.install != nullptr) {
			p.install(context, p.report, sizeof(p.report));
		}
		plog::Info("%s %s", p.word, p.report);
	}
}

void Line(const Part& part, char* out, size_t size) noexcept {
	if (part.state != nullptr && std::strncmp(part.report, "off", 3) != 0) {
		part.state(part, out, size);
		return;
	}
	std::snprintf(out, size, "%s", part.report);
}

void WriteStatus(const Part* parts, size_t count, const D2RL::ConsoleCommandContext* command) noexcept {
	if (command == nullptr || command->plugin == nullptr) {
		return;
	}
	for (size_t i = 0; i < count; ++i) {
		char state[900];
		Line(parts[i], state, sizeof(state));
		char line[1000];
		std::snprintf(line, sizeof(line), "%s %s", parts[i].word, state);
		command->plugin->WriteConsoleMessage(line);
	}
}

}  // namespace parts
