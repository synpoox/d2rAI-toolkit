// The parts table: engine parts stay off on another image, other parts install, reports and status lines. No game.
#include "log.h"
#include "parts.h"

#include <cstdio>
#include <cstring>

namespace {

int g_failures = 0;
int g_installs = 0;

void Check(bool ok, const char* what) {
	std::printf("%s: %s\n", ok ? "ok  " : "FAIL", what);
	g_failures += ok ? 0 : 1;
}

char g_logged[3200] = "";

void InstallLong(const D2RL::PluginContext*, char* report, size_t size) noexcept {
	std::memset(report, 'y', 2700);
	report[size > 2700 ? 2700 : size - 1] = '\0';
}

void InstallA(const D2RL::PluginContext*, char* report, size_t size) noexcept {
	++g_installs;
	std::snprintf(report, size, "on");
}
void InstallB(const D2RL::PluginContext*, char* report, size_t size) noexcept {
	++g_installs;
	std::snprintf(report, size, "on: 2/2");
}
void StateB(const parts::Part& part, char* out, size_t size) noexcept {
	std::snprintf(out, size, "%s (7 calls)", part.report);
}

}  // namespace

int main() {
	parts::Part table[] = {
		{"alpha", false, InstallA},
		{"beta", true, InstallB, StateB},
	};

	parts::InstallAll(table, 2, nullptr, "test-plugin", false);
	Check(g_installs == 1 && std::strcmp(table[0].report, "on") == 0, "a part without game addresses installs on any image");
	Check(std::strncmp(table[1].report, "off: game image differs", 23) == 0, "an engine part stays off on another image");

	parts::InstallAll(table, 2, nullptr, "test-plugin", true);
	Check(g_installs == 3 && std::strcmp(table[1].report, "on: 2/2") == 0, "an engine part installs on the expected image");

	char line[200];
	parts::Line(table[1], line, sizeof(line));
	Check(std::strcmp(line, "on: 2/2 (7 calls)") == 0, "a part with a state function reports its live line");
	parts::Line(table[0], line, sizeof(line));
	Check(std::strcmp(line, "on") == 0, "a part without one reports its install line");

	parts::InstallAll(table, 2, nullptr, "test-plugin", false);
	parts::Line(table[1], line, sizeof(line));
	Check(std::strncmp(line, "off", 3) == 0, "an off part shows why, not its live line");

	char why[200];
	Check(!parts::SkipReason(table[0], false, "test-plugin", why, sizeof(why)), "SkipReason: nothing to skip");
	Check(parts::SkipReason(table[1], false, "test-plugin", why, sizeof(why)), "SkipReason: an engine part on another image");

	// A report of one entry per installed slot is kept whole (it was cut at 511 bytes)
	parts::Part longPart {"long", false, nullptr};
	std::memset(longPart.report, 'x', 2500);
	longPart.report[2500] = '\0';
	static char big[parts::ReportSize];
	parts::Line(longPart, big, sizeof(big));
	Check(std::strlen(big) == 2500, "a 2500-byte report fits a part and its status line");

	// The install log line carries the whole report (plog's body was 2400 bytes and cut it)
	D2RL::PluginApi api {};
	api.apiSize = D2RL::PluginApiSize;
	api.logInfo = [](const D2RL::PluginContext*, const char* message) noexcept {
		std::snprintf(g_logged, sizeof(g_logged), "%s", message);
	};
	D2RL::PluginContext context {};
	context.contextSize = sizeof(context);
	context.api = &api;
	plog::Init(&context, "test-plugin");
	parts::Part longLogged {"long", false, InstallLong};
	parts::InstallAll(&longLogged, 1, &context, "test-plugin", true);
	Check(std::strlen(longLogged.report) == 2700 && std::strlen(g_logged) == std::strlen("test-plugin: long ") + 2700,
	      "the install log line holds a 2700-byte report whole");

	std::printf("%d failure(s)\n", g_failures);
	return g_failures == 0 ? 0 : 1;
}
