cmake_minimum_required(VERSION 3.22.1)
project(opencv_stitch_poc)

# OpenCV 路径（从环境变量或相对路径获取）
set(OpenCV_DIR /data/data/com.termux/files/home/.openclaw/workspace/opencv_sdk/OpenCV-android-sdk/sdk/native)
set(OPENCV_INCLUDE ${OpenCV_DIR}/jni/include)
set(OPENCV_LIB ${OpenCV_DIR}/libs/${ANDROID_ABI})
set(OPENCV_3RDPARTY ${OpenCV_DIR}/3rdparty/libs/${ANDROID_ABI})

add_library(native-lib SHARED
    native-lib.cpp
    jni_bridge.cpp
    OpenCvStitchSession.cpp
)

target_include_directories(native-lib PRIVATE ${OPENCV_INCLUDE})

find_library(log-lib log)

target_link_libraries(native-lib
    ${OPENCV_LIB}/libopencv_java4.so
    ${log-lib}
)

# 只保留 arm64-v8a
set(ANDROID_ABI "arm64-v8a" CACHE STRING "" FORCE)
