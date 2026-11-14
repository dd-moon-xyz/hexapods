if(CMAKE_CXX_COMPILER OR CMAKE_CUDA_HOST_COMPILER OR DEFINED ENV{CXX} OR DEFINED ENV{CUDAHOSTCXX})
    return()
endif()

if(NOT CMAKE_CUDA_COMPILER)
    if(DEFINED ENV{CUDACXX})
        set(CMAKE_CUDA_COMPILER "$ENV{CUDACXX}")
    else()
        find_program(CMAKE_CUDA_COMPILER NAMES nvcc REQUIRED)
    endif()
endif()

find_program(HEXAPODS_DEFAULT_CXX NAMES g++ REQUIRED)
set(HEXAPODS_HOST_CANDIDATES "${HEXAPODS_DEFAULT_CXX}")
cmake_path(CONVERT "$ENV{PATH}" TO_CMAKE_PATH_LIST HEXAPODS_SEARCH_PATHS)

foreach(HEXAPODS_SEARCH_PATH IN LISTS HEXAPODS_SEARCH_PATHS)
    file(GLOB HEXAPODS_VERSIONED_CXX "${HEXAPODS_SEARCH_PATH}/g++-*")
    list(SORT HEXAPODS_VERSIONED_CXX COMPARE NATURAL ORDER DESCENDING)
    list(APPEND HEXAPODS_HOST_CANDIDATES ${HEXAPODS_VERSIONED_CXX})
endforeach()

list(REMOVE_DUPLICATES HEXAPODS_HOST_CANDIDATES)
set(HEXAPODS_PROBE_DIRECTORY "${CMAKE_BINARY_DIR}/CMakeFiles/hexapods-cuda-host")
file(MAKE_DIRECTORY "${HEXAPODS_PROBE_DIRECTORY}")
file(WRITE "${HEXAPODS_PROBE_DIRECTORY}/probe.cu"
    "#include <vector>\n#include <concepts>\n__global__ void probe() {}\nint main() { std::vector<int> values{1}; return values.front(); }\n"
)

foreach(HEXAPODS_HOST_CANDIDATE IN LISTS HEXAPODS_HOST_CANDIDATES)
    execute_process(
        COMMAND "${CMAKE_CUDA_COMPILER}" -std=c++20
            -ccbin "${HEXAPODS_HOST_CANDIDATE}"
            -c "${HEXAPODS_PROBE_DIRECTORY}/probe.cu"
            -o "${HEXAPODS_PROBE_DIRECTORY}/probe.o"
        RESULT_VARIABLE HEXAPODS_PROBE_RESULT
        OUTPUT_VARIABLE HEXAPODS_PROBE_OUTPUT
        ERROR_VARIABLE HEXAPODS_PROBE_ERROR
        TIMEOUT 30
    )

    file(APPEND "${HEXAPODS_PROBE_DIRECTORY}/results.log"
        "${HEXAPODS_HOST_CANDIDATE}: ${HEXAPODS_PROBE_RESULT}\n${HEXAPODS_PROBE_OUTPUT}${HEXAPODS_PROBE_ERROR}\n"
    )

    if(HEXAPODS_PROBE_RESULT STREQUAL "0")
        set(CMAKE_CXX_COMPILER "${HEXAPODS_HOST_CANDIDATE}" CACHE FILEPATH "C++ compiler")
        set(CMAKE_CUDA_HOST_COMPILER "${HEXAPODS_HOST_CANDIDATE}" CACHE FILEPATH "CUDA host compiler")

        if(NOT CMAKE_C_COMPILER AND NOT DEFINED ENV{CC})
            cmake_path(GET HEXAPODS_HOST_CANDIDATE PARENT_PATH HEXAPODS_HOST_DIRECTORY)
            cmake_path(GET HEXAPODS_HOST_CANDIDATE FILENAME HEXAPODS_HOST_NAME)
            string(REPLACE "g++" "gcc" HEXAPODS_C_NAME "${HEXAPODS_HOST_NAME}")
            find_program(HEXAPODS_C_COMPILER NAMES "${HEXAPODS_C_NAME}" PATHS "${HEXAPODS_HOST_DIRECTORY}" NO_DEFAULT_PATH)

            if(HEXAPODS_C_COMPILER)
                set(CMAKE_C_COMPILER "${HEXAPODS_C_COMPILER}" CACHE FILEPATH "C compiler")
            endif()
        endif()

        message(STATUS "Selected CUDA-compatible C++ compiler: ${HEXAPODS_HOST_CANDIDATE}")
        return()
    endif()

    message(STATUS "CUDA C++20 check failed for ${HEXAPODS_HOST_CANDIDATE}")
endforeach()

message(FATAL_ERROR
    "No installed g++ compiler passed the CUDA C++20 check. Install a compiler compatible "
    "with your CUDA Toolkit, or upgrade the Toolkit. Probe output: ${HEXAPODS_PROBE_DIRECTORY}/results.log"
)
