cmake_minimum_required(VERSION 3.22)
project("stitch-core-native")

# ============================================================
# OpenCV Stitch 原生模块
# 红线约束:
# - Blender 默认关闭
# - ExposureCompensator 默认关闭
# - 不做额外涂抹/调色/锐化
# ============================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_VISIBILITY_PRESET hidden)
set(CMAKE_CXX_VISIBILITY_PRESET hidden)

# --- OpenCV (来自 OpenCV Android SDK) ---
# 构建时需在环境变量中指定 OPENCV_SDK_DIR 指向 OpenCV-android-sdk
# 或者在 local.properties 中设置 opencv.dir
if(DEFINED ENV{OPENCV_SDK_DIR})
    set(OpenCV_DIR "$ENV{OPENCV_SDK_DIR}/sdk/native/jni")
else()
    # 默认尝试 local.properties 中读取
    set(OpenCV_DIR "/usr/local/opencv-android-sdk/sdk/native/jni")
endif()

find_package(OpenCV REQUIRED QUIET)
if(NOT OpenCV_FOUND)
    message(WARNING "OpenCV not found at ${OpenCV_DIR}. JNI stitching will be disabled.")
endif()

message(STATUS "OpenCV include: ${OpenCV_INCLUDE_DIRS}")
message(STATUS "OpenCV libs: ${OpenCV_LIBS}")

# --- 源码 ---
set(JNI_SRCS
    src/main/cpp/NativeBridge.cpp
    src/main/cpp/OpenCvStitchSession.cpp
    src/main/cpp/jni_bridge.cpp
    src/main/cpp/native-lib.cpp
)

# --- 编译目标 ---
add_library(stitch-native SHARED ${JNI_SRCS})

target_include_directories(stitch-native PRIVATE
    src/main/cpp
    ${OpenCV_INCLUDE_DIRS}
)

target_link_libraries(stitch-native
    ${OpenCV_LIBS}
    log
    android
    jnigraphics
)

# --- 强制不链接 OpenCV 中的 libc++_shared（避免冲突） ---
# 如果 OpenCV 自带 libc++_shared.so，我们需要在 APK 中用同一个版本
# 策略：使用系统/NDK 提供的 libc++
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)
