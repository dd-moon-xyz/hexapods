cmake_minimum_required(VERSION 3.24)
cmake_policy(VERSION 3.24)

include(cmake/select_cuda_host.cmake)

project(Hexapods LANGUAGES CUDA CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_STANDARD 20)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_ARCHITECTURES 61)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/build)

add_executable(lenia
    source/lenia/lenia.cpp
    source/lenia/stream_hexapod.cu
)
target_include_directories(lenia PRIVATE ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})
target_compile_options(lenia PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-O3 -Wall -Wextra -Werror>
    $<$<COMPILE_LANGUAGE:CUDA>:--ptxas-options=-O3>
)

if(BUILD_TESTING)
    add_executable(stream_resize_test tests/stream_resize.cpp)
    target_include_directories(stream_resize_test PRIVATE source/lenia)
    add_test(NAME compilation
        COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR}
            --clean-first --target lenia --config $<CONFIG> --parallel
    )
    set_tests_properties(compilation PROPERTIES RUN_SERIAL TRUE)
endif()
