# modkit_add_plugin(): builds one D2RLoader plugin DLL. A project with several plugins includes this file and calls it once
# per DLL (the plugin template does, and so can any mod's own plugin project). It needs the plugin_common target, so
# call it after add_subdirectory(<toolkit>/shared/plugin-common). The default VERSION is MODKIT_PLUGIN_VERSION.
# One plugin DLL <id>.dll in <build>/<config>/. The sources are the plugin's own (it needs a main file like plugin.cpp
# and plugin.rc, the ABI manifest resource D2RLoader rejects the DLL without). Every plugin links plugin_common.
function(modkit_add_plugin id)
	cmake_parse_arguments(P "" "VERSION;MOD;SOUND_ROWS" "SOURCES" ${ARGN})
	if(NOT P_SOURCES)
		message(FATAL_ERROR "modkit_add_plugin(${id}): SOURCES is empty")
	endif()
	if(NOT P_VERSION)
		set(P_VERSION "${MODKIT_PLUGIN_VERSION}")
	endif()
	if(NOT P_SOUND_ROWS)
		set(P_SOUND_ROWS 0)
	endif()
	string(MAKE_C_IDENTIFIER "${id}" tgt)
	set(tgt "plugin_${tgt}")
	add_library(${tgt} SHARED ${P_SOURCES})
	target_link_libraries(${tgt} PRIVATE plugin_common)
	target_compile_definitions(${tgt} PRIVATE
		MODKIT_PLUGIN_NAME="${id}"
		MODKIT_PLUGIN_VERSION="${P_VERSION}"
		MODKIT_MOD_NAME="${P_MOD}"
		MODKIT_SOUND_ROWS=${P_SOUND_ROWS}
	)
	set_target_properties(${tgt} PROPERTIES OUTPUT_NAME "${id}")
	if(MSVC)
		target_compile_options(${tgt} PRIVATE $<$<COMPILE_LANGUAGE:CXX>:/W4 /permissive- /EHsc /utf-8>)
		set_property(TARGET ${tgt} PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")  # static CRT: no VC++ runtime dependency
	endif()
endfunction()
