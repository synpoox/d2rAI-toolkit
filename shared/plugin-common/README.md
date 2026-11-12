# plugin-common: the shared plugin library

The code every D2RLoader plugin made with this toolkit needs, as one CMake static library (`plugin_common`). Link it
instead of copying these files into each project, so a fix lands once.

Target: **D2R 3.3.0 build 93847 + D2RLoader 1.3.1, PluginSDK 0.4.0.** `plugin-template/` is the working example.

| File | What it is |
| --- | --- |
| `src/build_guard.h` | Image check: the PE TimeDateStamp of the running game against `rva::ImageStamp` (`0x6ab3782c`), and the log/status line |
| `src/rvas_93847.h` | Engine facts for build 93847: `ImageStamp`, and the RVAs and record offsets by area in `src/rvas_93847/` (tables, damage, units, offsets, stats, items, levels, ai, client, pools). One header per build. The structures (`MissileParams`, `SummonParams` and the rest) and helpers are in `d2r.h` |
| `src/d2r.h`, `src/d2r.cpp` | `d2r::Bind()` (fails closed: binds nothing on any other image), the typed function table `d2r::api`, `Engine<Fn>`, `At<T>`, `UnitXY`, `EvalCalc`, `ValidMissile`, D2 RNG |
| `src/ai_registry.*` | `ai_registry::Register(context, monaiRow, d2rThink, classId, think)`: a monster think function by monai row and monstats class, D2R's think for every other monster (`ai_registry::Vanilla(row)`) |
| `src/env_guard.*` | Environment guard: another mod running, the DLL outside its mod folder, a second copy, other plugins |
| `src/off_switch.*` | Reads `<name>-off.txt` beside the path you pass (the DLL or the plugin's config): part words to leave out |
| `src/level_palette.*` | `level_palette::Install`: loads a level's own legacy palette when a level change crosses a `levels.txt` Pal (no load screen), through D2R's act palette load; `NeedsLoad`, `Counters` |
| `src/log.*` | Log helper (`plog::Info/Warn/Error`, `plog::Sample` for hot paths) |
| `src/crash_guard.h` | Logs a FAULT line when the game faults: address, why, whether this plugin is on the stack |

**Policy:** every RVA in these headers has a row in `knowledge/d2r-93847-addresses.md` (RVA, signature, meaning, evidence H/C/T/R/P/D). Add the row with the value; `tests/test_rva_knowledge.py` fails when one is missing.

Only generic engine facts go in here. A value or helper only one project uses stays in that project until a second
project needs the same code.

## Use it in a plugin project

Your project needs a checkout of this toolkit (a sibling folder or a submodule). In your `CMakeLists.txt`:

```cmake
add_subdirectory(<toolkit>/shared/plugin-common plugin-common)
target_link_libraries(<your plugin> PRIVATE plugin_common)
```

That brings the include path, the PluginSDK (`D2RLPlugin::D2RLPlugin`) and C++20. The library adds the toolkit's
PluginSDK (`third_party/PluginSDK`) unless your project added one before; pass `-DPLUGIN_COMMON_SDK_DIR=<dir>` to use
another copy. Build your plugin with the static CRT (`MultiThreaded`), as the library does.

At load, in this order (see `plugin-template/src/plugin.cpp`):

```cpp
plog::Init(context, PluginName);
crash_guard::Install(PluginVersion, context->exeBase);
off_switch::Read(context->pluginPath);            // or context->pluginConfigPath
const bool imageOk = d2r::Bind(context->exeBase); // false on any other image: install no engine part
```

and `crash_guard::Remove()` on unload.

## Record the toolkit commit

The library changes with the toolkit, so each project pins the toolkit commit it was built and tested with:

- as a git submodule, the pin is the submodule commit (`git submodule status`);
- as a sibling checkout, write the commit in the project (for example a `toolkit.lock` or a line in its README:
  `d2rAI-toolkit 1a2b3c4`, from `git -C <toolkit> rev-parse --short HEAD`) and check it out before you build.

Update the pin on purpose, rebuild, and rerun the project's game checks before you ship.

## Tests

The image guard has a test (a fake PE header with an unknown stamp must bind nothing). Windows with Visual Studio:

```powershell
cmake -S shared/plugin-common -B build/plugin-common -A x64
cmake --build build/plugin-common --config Release
ctest --test-dir build/plugin-common -C Release --output-on-failure
```
