cmake_minimum_required(VERSION 3.22.1)
project(opencv_stitch_poc)

add_library(native-lib SHARED
    native-lib.cpp
    jni_bridge.cpp
    OpenCvStitchSession.cpp
)

find_library(log-lib log)

# OpenCV 依赖后续接入；当前先保证骨架可识别。

target_link_libraries(native-lib
    ${log-lib}
)
