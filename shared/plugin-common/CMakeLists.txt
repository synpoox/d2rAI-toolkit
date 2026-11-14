# plugin-common: the code every D2RLoader plugin built with this toolkit shares (image guard, environment guard, off
# switches, log, crash guard, the build 93847 binding header and the D2R helpers), as one static library.
#
# Use it from a plugin project (README.md):
#   add_subdirectory(<toolkit>/shared/plugin-common plugin-common)
#   target_link_libraries(<your plugin> PRIVATE plugin_common)
# It adds the PluginSDK itself unless the project already did (PLUGIN_COMMON_SDK_DIR, default the toolkit's copy).
#
# Tests (Windows, MSVC): cmake -S shared/plugin-common -B <dir> -A x64 && cmake --build <dir> --config Release
#                        && ctest --test-dir <dir> -C Release
cmake_minimum_required(VERSION 3.29)
project(plugin_common LANGUAGES CXX)

if(NOT TARGET D2RLPlugin::D2RLPlugin)
	set(PLUGIN_COMMON_SDK_DIR "${CMAKE_CURRENT_LIST_DIR}/../../third_party/PluginSDK" CACHE PATH "D2RLoader PluginSDK directory")
	if(NOT EXISTS "${PLUGIN_COMMON_SDK_DIR}/CMakeLists.txt")
		message(FATAL_ERROR "PluginSDK not found at ${PLUGIN_COMMON_SDK_DIR}: run `git submodule update --init third_party/PluginSDK`")
	endif()
	set(D2RLPLUGIN_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
	set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
	add_subdirectory(${PLUGIN_COMMON_SDK_DIR} PluginSDK EXCLUDE_FROM_ALL)
endif()

add_library(plugin_common STATIC
	src/ai_registry.cpp
	src/calib.cpp
	src/d2r.cpp
	src/env_guard.cpp
	src/level_palette.cpp
	src/log.cpp
	src/off_switch.cpp
	src/parts.cpp
	src/sig.cpp
)
target_include_directories(plugin_common PUBLIC src)
target_link_libraries(plugin_common PUBLIC D2RLPlugin::D2RLPlugin)
target_compile_features(plugin_common PUBLIC cxx_std_20)
if(MSVC)
	target_compile_options(plugin_common PRIVATE $<$<COMPILE_LANGUAGE:CXX>:/W4 /permissive- /EHsc /utf-8>)
	set_property(TARGET plugin_common PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")  # static CRT, as the plugins
endif()

if(PROJECT_IS_TOP_LEVEL)
	enable_testing()
	# One executable per test file: tests/<name>.cpp builds plugin_common_<name> (add the name here).
	foreach(test guard_test ai_registry_test calib_test level_palette_test parts_test sig_test sig_dump_test)
		add_executable(plugin_common_${test} tests/${test}.cpp)
		target_link_libraries(plugin_common_${test} PRIVATE plugin_common)
		if(MSVC)
			target_compile_options(plugin_common_${test} PRIVATE /W4 /permissive- /EHsc /utf-8)
			set_property(TARGET plugin_common_${test} PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")
		endif()
		add_test(NAME plugin_common_${test} COMMAND plugin_common_${test})
		set_tests_properties(plugin_common_${test} PROPERTIES SKIP_RETURN_CODE 77)  # sig_dump_test without a dump
	endforeach()
endif()
