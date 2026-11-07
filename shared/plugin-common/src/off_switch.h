// Diagnosis switch: "<plugin>-off.txt" lists the words of parts to leave out, separated by spaces, commas or lines,
// case-insensitive. Delete the file for normal play.
//
// Where the file sits is the plugin's choice: Read() takes a path and reads <dir>\<name>-off.txt beside it. Pass
// context->pluginPath for a file next to the DLL (mods\<Mod>\d2rloader\plugins\mod-core-off.txt, the template's
// choice) or context->pluginConfigPath for one next to the plugin's config (d2rloader\config\<name>-off.txt).
//
// Use it to bisect a crash or regression: leave half the parts out, restart the game, repeat. Build it in from day
// one, give every new part a word, and know the dependencies (a part whose calc codes other parts' formulas use can't
// be left out alone: the game may hang on load).
//
// Example file:   envguard soundguard
#pragma once

namespace off_switch {

// Reads <dir>\<name>-off.txt for `namedAfter` = <dir>\<name>.<ext>. No path, or no file: no words.
void Read(const wchar_t* namedAfter) noexcept;

// True when the file names this word (whole words only: "hook" does not match "hooks").
auto Off(const char* word) noexcept -> bool;

// The words read, lower case, separated by spaces ("" when there is no file).
auto Words() noexcept -> const char*;

}  // namespace off_switch
