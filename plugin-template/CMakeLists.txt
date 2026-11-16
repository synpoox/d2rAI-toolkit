# D2RLoader plugin template (D2R 3.3.0 build 93847, D2RLoader 1.3.1, PluginSDK 0.4.0).
#
# Build:  powershell -ExecutionPolicy Bypass -File build.ps1            (or by hand:)
#         cmake -S . -B build -A x64 -DMODKIT_PLUGIN_NAME=mod-core
#         cmake --build build --config Release
# Output: build/Release/<MODKIT_PLUGIN_NAME>.dll -> copy to <game>/mods/<Mod>/d2rloader/plugins/
#
# Where things are: the toolkit is found by the shared finder (cmake/FindD2rToolkit.cmake; docs/toolkit-finder.md):
# -DMODKIT_TOOLKIT_DIR, else the environment variable D2R_TOOLKIT, else the toolkit around this folder, else a walk up
# to a "d2rAI-toolkit" folder. From it come the PluginSDK (third_party/PluginSDK; init the submodule first:
# `git submodule update --init third_party/PluginSDK`) and the shared library (shared/plugin-common). MODKIT_SDK_DIR and
# MODKIT_COMMON_DIR still override either path.
#
# One project can build several plugins: call modkit_add_plugin() once per DLL (see the end of this file). Each plugin has
# its own id, version, mod name and sound-row count, and all share plugin-common.
cmake_minimum_required(VERSION 3.29)
project(modkit_plugin LANGUAGES CXX RC)

set(MODKIT_TOOLKIT_DIR "" CACHE PATH "The d2rAI-toolkit checkout (empty = find it)")
if(MODKIT_TOOLKIT_DIR)
	set(ENV{D2R_TOOLKIT} "${MODKIT_TOOLKIT_DIR}")
endif()
if(DEFINED ENV{D2R_TOOLKIT})
	if(NOT EXISTS "$ENV{D2R_TOOLKIT}/cmake/FindD2rToolkit.cmake")
		message(FATAL_ERROR "MODKIT_TOOLKIT_DIR / D2R_TOOLKIT=$ENV{D2R_TOOLKIT} is not a d2rAI-toolkit checkout (cmake/FindD2rToolkit.cmake is missing)")
	endif()
	list(APPEND CMAKE_MODULE_PATH "$ENV{D2R_TOOLKIT}/cmake")
elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../cmake/FindD2rToolkit.cmake")
	list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake")  # this template, still inside the toolkit
else()
	set(_d "${CMAKE_CURRENT_SOURCE_DIR}")
	while(NOT EXISTS "${_d}/d2rAI-toolkit/cmake/FindD2rToolkit.cmake")
		get_filename_component(_p "${_d}" DIRECTORY)
		if(_p STREQUAL _d)
			message(FATAL_ERROR "d2rAI-toolkit not found: pass -DMODKIT_TOOLKIT_DIR=<folder> or set D2R_TOOLKIT")
		endif()
		set(_d "${_p}")
	endwhile()
	list(APPEND CMAKE_MODULE_PATH "${_d}/d2rAI-toolkit/cmake")
endif()
find_package(D2rToolkit REQUIRED)  # sets D2R_TOOLKIT_DIR, checks the mod's toolkit.version pin

set(MODKIT_SDK_DIR "" CACHE PATH "D2RLoader PluginSDK directory (empty = <toolkit>/third_party/PluginSDK)")
set(MODKIT_COMMON_DIR "" CACHE PATH "The toolkit's shared plugin library (empty = <toolkit>/shared/plugin-common)")
set(_sdk "${MODKIT_SDK_DIR}")
if(NOT _sdk)
	set(_sdk "${D2R_TOOLKIT_DIR}/third_party/PluginSDK")
endif()
set(_common "${MODKIT_COMMON_DIR}")
if(NOT _common)
	set(_common "${D2R_TOOLKIT_DIR}/shared/plugin-common")
endif()
if(NOT EXISTS "${_sdk}/CMakeLists.txt")
	message(FATAL_ERROR "PluginSDK not found at ${_sdk}: run `git submodule update --init third_party/PluginSDK` in the toolkit")
endif()

set(MODKIT_PLUGIN_NAME "mod-core" CACHE STRING "Plugin id, DLL name, console command and <name>-off.txt prefix (the template's own plugin)")
set(MODKIT_PLUGIN_VERSION "0.1.0" CACHE STRING "PluginInfo::version (shared plugins must match in multiplayer)")
set(MODKIT_MOD_NAME "" CACHE STRING "Mod folder the plugin ships in (mods/<name>); the environment guard warns when another runs")
set(MODKIT_SOUND_ROWS "0" CACHE STRING "Rows of the mod's sounds.txt (0 = no new sounds); below it the sound guard asks for a restart")

set(D2RLPLUGIN_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(${_sdk} PluginSDK EXCLUDE_FROM_ALL)
add_subdirectory(${_common} plugin-common)

# modkit_add_plugin(<id> [VERSION <v>] [MOD <mod folder>] [SOUND_ROWS <n>] SOURCES <files...>), from cmake/ModkitPlugin.cmake:
# one plugin DLL <id>.dll per call, every plugin linked to plugin_common.
include(ModkitPlugin)

set(MODKIT_SOURCES
	src/plugin.cpp
	src/sound_guard.cpp
	src/item_type_check.cpp
	src/skill_functions.cpp
	src/skill_router.cpp
	src/hook_example.cpp
	src/plugin.rc
)
# The template's own plugin. A project with more plugins adds more calls, each with its own id and sources, e.g.
#   modkit_add_plugin(my-mod-ui VERSION 0.1.0 MOD MyMod SOURCES ui/plugin.cpp ui/plugin.rc)
modkit_add_plugin(${MODKIT_PLUGIN_NAME} VERSION ${MODKIT_PLUGIN_VERSION} MOD "${MODKIT_MOD_NAME}"
	SOUND_ROWS ${MODKIT_SOUND_ROWS} SOURCES ${MODKIT_SOURCES})

# Tests that need no game: cmake ... -DMODKIT_BUILD_TESTS=ON, then ctest -C Release
option(MODKIT_BUILD_TESTS "Build the template's tests" OFF)
if(MODKIT_BUILD_TESTS)
	enable_testing()
	add_executable(skill_router_test tests/skill_router_test.cpp src/skill_router.cpp)
	target_include_directories(skill_router_test PRIVATE src)
	target_link_libraries(skill_router_test PRIVATE plugin_common)
	if(MSVC)
		target_compile_options(skill_router_test PRIVATE /W4 /permissive- /EHsc /utf-8)
		set_property(TARGET skill_router_test PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")
	endif()
	add_test(NAME skill_router_test COMMAND skill_router_test)
endif()
