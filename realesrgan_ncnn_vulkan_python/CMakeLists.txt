cmake_policy(SET CMP0091 NEW)
set(CMAKE_POLICY_DEFAULT_CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

project(realesrgan-ncnn-vulkan-python)

cmake_minimum_required(VERSION 3.9)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE release CACHE STRING "Choose the type of build" FORCE)
endif()

option(USE_SYSTEM_NCNN "build with system libncnn" OFF)
option(USE_SYSTEM_WEBP "build with system libwebp" OFF)
option(USE_STATIC_MOLTENVK "link moltenvk static library" OFF)

find_package(Threads)
find_package(OpenMP)
find_package(Vulkan REQUIRED)

# Python
if (DEFINED PY_VERSION)
  if (${CMAKE_VERSION} VERSION_LESS "3.15")
  	find_package(Python ${PY_VERSION} EXACT REQUIRED)
  else()
   	find_package(Python ${PY_VERSION} EXACT REQUIRED COMPONENTS Development)
  endif()
else()
  if (${CMAKE_VERSION} VERSION_LESS "3.15")
    find_package(Python REQUIRED)
  else()
    find_package(Python REQUIRED COMPONENTS Development)
  endif()
endif()

# SWIG
find_package(SWIG REQUIRED COMPONENTS python)
if(SWIG_FOUND)
  message("SWIG found: ${SWIG_EXECUTABLE}")
  include(${SWIG_USE_FILE})
endif()

find_program(GLSLANGVALIDATOR_EXECUTABLE NAMES glslangValidator PATHS $ENV{VULKAN_SDK}/bin NO_CMAKE_FIND_ROOT_PATH)
message(STATUS "Found glslangValidator: ${GLSLANGVALIDATOR_EXECUTABLE}")

macro(compile_shader SHADER_SRC)
    set(SHADER_SRC_FULLPATH ${CMAKE_CURRENT_SOURCE_DIR}/realesrgan-ncnn-vulkan/src/${SHADER_SRC})

    get_filename_component(SHADER_SRC_NAME_WE ${SHADER_SRC} NAME_WE)
    set(SHADER_SPV_HEX_FILE ${CMAKE_CURRENT_BINARY_DIR}/realesrgan-ncnn-vulkan/src/${SHADER_SRC_NAME_WE}.spv.hex.h)
    add_custom_command(
        OUTPUT ${SHADER_SPV_HEX_FILE}
        COMMAND ${GLSLANGVALIDATOR_EXECUTABLE}
        ARGS -V -s -x -o ${SHADER_SPV_HEX_FILE} ${SHADER_SRC_FULLPATH}
        DEPENDS ${SHADER_SRC_FULLPATH}
        COMMENT "Building SPIR-V module ${SHADER_SRC_NAME_WE}.spv"
        VERBATIM
    )
    set_source_files_properties(${SHADER_SPV_HEX_FILE} PROPERTIES GENERATED TRUE)
    list(APPEND SHADER_SPV_HEX_FILES ${SHADER_SPV_HEX_FILE})

    # fp16 storage
    set(SHADER_fp16s_SRC_NAME_WE "${SHADER_SRC_NAME_WE}_fp16s")

    set(SHADER_fp16s_SPV_HEX_FILE ${CMAKE_CURRENT_BINARY_DIR}/realesrgan-ncnn-vulkan/src/${SHADER_fp16s_SRC_NAME_WE}.spv.hex.h)
    add_custom_command(
        OUTPUT ${SHADER_fp16s_SPV_HEX_FILE}
        COMMAND ${GLSLANGVALIDATOR_EXECUTABLE}
        ARGS -DNCNN_fp16_storage=1 -V -s -x -o ${SHADER_fp16s_SPV_HEX_FILE} ${SHADER_SRC_FULLPATH}
        DEPENDS ${SHADER_SRC_FULLPATH}
        COMMENT "Building SPIR-V module ${SHADER_fp16s_SRC_NAME_WE}.spv"
        VERBATIM
    )
    set_source_files_properties(${SHADER_fp16s_SPV_HEX_FILE} PROPERTIES GENERATED TRUE)
    list(APPEND SHADER_SPV_HEX_FILES ${SHADER_fp16s_SPV_HEX_FILE})

    # int8 storage
    set(SHADER_int8s_SRC_NAME_WE "${SHADER_SRC_NAME_WE}_int8s")

    set(SHADER_int8s_SPV_HEX_FILE ${CMAKE_CURRENT_BINARY_DIR}/realesrgan-ncnn-vulkan/src/${SHADER_int8s_SRC_NAME_WE}.spv.hex.h)
    add_custom_command(
        OUTPUT ${SHADER_int8s_SPV_HEX_FILE}
        COMMAND ${GLSLANGVALIDATOR_EXECUTABLE}
        ARGS -DNCNN_fp16_storage=1 -DNCNN_int8_storage=1 -V -s -x -o ${SHADER_int8s_SPV_HEX_FILE} ${SHADER_SRC_FULLPATH}
        DEPENDS ${SHADER_SRC_FULLPATH}
        COMMENT "Building SPIR-V module ${SHADER_int8s_SRC_NAME_WE}.spv"
        VERBATIM
    )
    set_source_files_properties(${SHADER_int8s_SPV_HEX_FILE} PROPERTIES GENERATED TRUE)
    list(APPEND SHADER_SPV_HEX_FILES ${SHADER_int8s_SPV_HEX_FILE})
endmacro()

include_directories(${CMAKE_CURRENT_BINARY_DIR}/realesrgan-ncnn-vulkan/src)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/realesrgan-ncnn-vulkan/src)
include_directories(.)

if(OPENMP_FOUND)
  set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
  set(CMAKE_EXE_LINKER_FLAGS
      "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")
endif()

# enable global link time optimization
cmake_policy(SET CMP0069 NEW)
set(CMAKE_POLICY_DEFAULT_CMP0069 NEW)
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported OUTPUT ipo_supported_output)
if(ipo_supported)
  set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
else()
  message(WARNING "IPO is not supported: ${ipo_supported_output}")
endif()

if(USE_SYSTEM_NCNN)
  set(GLSLANG_TARGET_DIR
      "GLSLANG-NOTFOUND"
      CACHE PATH "Absolute path to glslangTargets.cmake directory")
  if(NOT GLSLANG_TARGET_DIR AND NOT DEFINED ENV{GLSLANG_TARGET_DIR})
    message(
      WARNING
        "GLSLANG_TARGET_DIR must be defined! USE_SYSTEM_NCNN will be turned off."
    )
    set(USE_SYSTEM_NCNN OFF)
  else()
    message(STATUS "Using glslang install located at ${GLSLANG_TARGET_DIR}")

    find_package(Threads)

    include("${GLSLANG_TARGET_DIR}/OSDependentTargets.cmake")
    include("${GLSLANG_TARGET_DIR}/OGLCompilerTargets.cmake")
    if(EXISTS "${GLSLANG_TARGET_DIR}/HLSLTargets.cmake")
      # hlsl support can be optional
      include("${GLSLANG_TARGET_DIR}/HLSLTargets.cmake")
    endif()
    include("${GLSLANG_TARGET_DIR}/glslangTargets.cmake")
    include("${GLSLANG_TARGET_DIR}/SPIRVTargets.cmake")

    if(NOT TARGET glslang OR NOT TARGET SPIRV)
      message(
        WARNING
          "glslang or SPIRV target not found! USE_SYSTEM_NCNN will be turned off."
      )
      set(USE_SYSTEM_NCNN OFF)
    endif()
  endif()
endif()

if(USE_SYSTEM_NCNN)
  find_package(ncnn)
  if(NOT TARGET ncnn)
    message(
      WARNING "ncnn target not found! USE_SYSTEM_NCNN will be turned off.")
    set(USE_SYSTEM_NCNN OFF)
  endif()
endif()

if(NOT USE_SYSTEM_NCNN)
  # build ncnn library
  if(NOT EXISTS
     "${CMAKE_CURRENT_SOURCE_DIR}/realesrgan-ncnn-vulkan/src/ncnn/CMakeLists.txt")
    message(
      FATAL_ERROR
        "The submodules were not downloaded! Please update submodules with \"git submodule update --init --recursive\" and try again."
    )
  endif()

  option(NCNN_INSTALL_SDK "" OFF)
  option(NCNN_PIXEL_ROTATE "" OFF)
  option(NCNN_PIXEL_AFFINE "" OFF)
  option(NCNN_PIXEL_DRAWING "" OFF)
  option(NCNN_VULKAN "" ON)
  option(NCNN_VULKAN_ONLINE_SPIRV "" ON)
  option(NCNN_BUILD_BENCHMARK "" OFF)
  option(NCNN_BUILD_TESTS "" OFF)
  option(NCNN_BUILD_TOOLS "" OFF)
  option(NCNN_BUILD_EXAMPLES "" OFF)
  option(NCNN_DISABLE_RTTI "" ON)
  option(NCNN_DISABLE_EXCEPTION "" ON)
  option(NCNN_INT8 "" OFF)

  option(WITH_LAYER_absval "" OFF)
  option(WITH_LAYER_argmax "" OFF)
  option(WITH_LAYER_batchnorm "" OFF)
  option(WITH_LAYER_bias "" OFF)
  option(WITH_LAYER_bnll "" OFF)
  option(WITH_LAYER_concat "" ON)
  option(WITH_LAYER_convolution "" ON)
  option(WITH_LAYER_crop "" ON)
  option(WITH_LAYER_deconvolution "" ON)
  option(WITH_LAYER_dropout "" OFF)
  option(WITH_LAYER_eltwise "" ON)
  option(WITH_LAYER_elu "" OFF)
  option(WITH_LAYER_embed "" OFF)
  option(WITH_LAYER_exp "" OFF)
  option(WITH_LAYER_flatten "" ON)
  option(WITH_LAYER_innerproduct "" ON)
  option(WITH_LAYER_input "" ON)
  option(WITH_LAYER_log "" OFF)
  option(WITH_LAYER_lrn "" OFF)
  option(WITH_LAYER_memorydata "" OFF)
  option(WITH_LAYER_mvn "" OFF)
  option(WITH_LAYER_pooling "" ON)
  option(WITH_LAYER_power "" OFF)
  option(WITH_LAYER_prelu "" ON)
  option(WITH_LAYER_proposal "" OFF)
  option(WITH_LAYER_reduction "" OFF)
  option(WITH_LAYER_relu "" ON)
  option(WITH_LAYER_reshape "" OFF)
  option(WITH_LAYER_roipooling "" OFF)
  option(WITH_LAYER_scale "" OFF)
  option(WITH_LAYER_sigmoid "" ON)
  option(WITH_LAYER_slice "" ON)
  option(WITH_LAYER_softmax "" OFF)
  option(WITH_LAYER_split "" ON)
  option(WITH_LAYER_spp "" OFF)
  option(WITH_LAYER_tanh "" OFF)
  option(WITH_LAYER_threshold "" OFF)
  option(WITH_LAYER_tile "" OFF)
  option(WITH_LAYER_rnn "" OFF)
  option(WITH_LAYER_lstm "" OFF)
  option(WITH_LAYER_binaryop "" ON)
  option(WITH_LAYER_unaryop "" ON)
  option(WITH_LAYER_convolutiondepthwise "" OFF)
  option(WITH_LAYER_padding "" ON)
  option(WITH_LAYER_squeeze "" OFF)
  option(WITH_LAYER_expanddims "" OFF)
  option(WITH_LAYER_normalize "" OFF)
  option(WITH_LAYER_permute "" OFF)
  option(WITH_LAYER_priorbox "" OFF)
  option(WITH_LAYER_detectionoutput "" OFF)
  option(WITH_LAYER_interp "" ON)
  option(WITH_LAYER_deconvolutiondepthwise "" OFF)
  option(WITH_LAYER_shufflechannel "" OFF)
  option(WITH_LAYER_instancenorm "" OFF)
  option(WITH_LAYER_clip "" ON)
  option(WITH_LAYER_reorg "" OFF)
  option(WITH_LAYER_yolodetectionoutput "" OFF)
  option(WITH_LAYER_quantize "" OFF)
  option(WITH_LAYER_dequantize "" OFF)
  option(WITH_LAYER_yolov3detectionoutput "" OFF)
  option(WITH_LAYER_psroipooling "" OFF)
  option(WITH_LAYER_roialign "" OFF)
  option(WITH_LAYER_packing "" ON)
  option(WITH_LAYER_requantize "" OFF)
  option(WITH_LAYER_cast "" ON)
  option(WITH_LAYER_hardsigmoid "" OFF)
  option(WITH_LAYER_selu "" OFF)
  option(WITH_LAYER_hardswish "" OFF)
  option(WITH_LAYER_noop "" OFF)
  option(WITH_LAYER_pixelshuffle "" ON)
  option(WITH_LAYER_deepcopy "" OFF)
  option(WITH_LAYER_mish "" OFF)
  option(WITH_LAYER_statisticspooling "" OFF)
  option(WITH_LAYER_swish "" OFF)
  option(WITH_LAYER_gemm "" OFF)
  option(WITH_LAYER_groupnorm "" OFF)
  option(WITH_LAYER_layernorm "" OFF)
  option(WITH_LAYER_softplus "" OFF)
  option(WITH_LAYER_gru "" OFF)
  option(WITH_LAYER_multiheadattention "" OFF)
  option(WITH_LAYER_gelu "" OFF)
  option(WITH_LAYER_convolution1d "" OFF)
  option(WITH_LAYER_pooling1d "" OFF)
  option(WITH_LAYER_convolutiondepthwise1d "" OFF)
  option(WITH_LAYER_convolution3d "" OFF)
  option(WITH_LAYER_convolutiondepthwise3d "" OFF)
  option(WITH_LAYER_pooling3d "" OFF)
  option(WITH_LAYER_matmul "" OFF)
  option(WITH_LAYER_deconvolution1d "" OFF)
  option(WITH_LAYER_deconvolutiondepthwise1d "" OFF)
  option(WITH_LAYER_deconvolution3d "" OFF)
  option(WITH_LAYER_deconvolutiondepthwise3d "" OFF)
  option(WITH_LAYER_einsum "" OFF)
  option(WITH_LAYER_deformableconv2d "" OFF)

  add_subdirectory("realesrgan-ncnn-vulkan/src/ncnn")
endif()

compile_shader(realesrgan_preproc.comp)
compile_shader(realesrgan_postproc.comp)
compile_shader(realesrgan_preproc_tta.comp)
compile_shader(realesrgan_postproc_tta.comp)

add_custom_target(generate-spirv DEPENDS ${SHADER_SPV_HEX_FILES})

set(REALESRGAN_LINK_LIBRARIES ncnn ${Vulkan_LIBRARY})

if(USE_STATIC_MOLTENVK)
  find_library(CoreFoundation NAMES CoreFoundation)
  find_library(Foundation NAMES Foundation)
  find_library(Metal NAMES Metal)
  find_library(QuartzCore NAMES QuartzCore)
  find_library(CoreGraphics NAMES CoreGraphics)
  find_library(Cocoa NAMES Cocoa)
  find_library(IOKit NAMES IOKit)
  find_library(IOSurface NAMES IOSurface)

  list(
    APPEND
    REALESRGAN_LINK_LIBRARIES
    ${Metal}
    ${QuartzCore}
    ${CoreGraphics}
    ${Cocoa}
    ${IOKit}
    ${IOSurface}
    ${Foundation}
    ${CoreFoundation})
endif()

set(UseSWIG_TARGET_NAME_PREFERENCE STANDARD)
set_property(SOURCE realesrgan.i PROPERTY CPLUSPLUS ON DEPENDS generate-spirv)

# set output directory for the .py file
set_property(SOURCE realesrgan.i PROPERTY OUTFILE_DIR ${CMAKE_CURRENT_BINARY_DIR})
set_property(
  SOURCE realesrgan.i PROPERTY OUTPUT_DIR
                         ${CMAKE_CURRENT_BINARY_DIR}/realesrgan_ncnn_vulkan_python)

swig_add_library(
  realesrgan_ncnn_vulkan_wrapper
  TYPE MODULE
  LANGUAGE python
  SOURCES realesrgan.i
          realesrgan-ncnn-vulkan/src/realesrgan.cpp
          realesrgan_wrapped.cpp
          OUTPUT_DIR
          ${CMAKE_CURRENT_BINARY_DIR}/realesrgan_ncnn_vulkan_python
          OUTFILE_DIR
          ${CMAKE_CURRENT_BINARY_DIR}/realesrgan_ncnn_vulkan_python)

add_dependencies(realesrgan_ncnn_vulkan_wrapper generate-spirv)
target_compile_options(realesrgan_ncnn_vulkan_wrapper PUBLIC -fexceptions)

# set output directory of the .so file
if(CALL_FROM_SETUP_PY)
  set_target_properties(
    realesrgan_ncnn_vulkan_wrapper PROPERTIES LIBRARY_OUTPUT_DIRECTORY
                                        ${CMAKE_CURRENT_BINARY_DIR})
else()
  set_target_properties(
    realesrgan_ncnn_vulkan_wrapper
    PROPERTIES LIBRARY_OUTPUT_DIRECTORY
               ${CMAKE_CURRENT_BINARY_DIR}/realesrgan_ncnn_vulkan_python)
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.15")
  include_directories(${PYTHON_INCLUDE_DIRS})
  target_link_libraries(realesrgan_ncnn_vulkan_wrapper ${REALESRGAN_LINK_LIBRARIES}
                        ${PYTHON_LIBRARIES})
else()
  target_link_libraries(realesrgan_ncnn_vulkan_wrapper ${REALESRGAN_LINK_LIBRARIES}
                        Python::Module)
endif()

# Get the autogenerated Python file
get_property(
  WRAPPER_PY_FILE
  TARGET realesrgan_ncnn_vulkan_wrapper
  PROPERTY SWIG_SUPPORT_FILES)

if(CALL_FROM_SETUP_PY)
  # Install the autogenerated Python file
  install(FILES ${WRAPPER_PY_FILE} DESTINATION ${CMAKE_INSTALL_PREFIX})

  install(TARGETS realesrgan_ncnn_vulkan_wrapper
          LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX})
  install(FILES realesrgan_ncnn_vulkan.py DESTINATION ${CMAKE_INSTALL_PREFIX})
else()
  file(COPY realesrgan_ncnn_vulkan.py
       DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/realesrgan_ncnn_vulkan_python)
endif()
