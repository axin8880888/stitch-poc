cmake_minimum_required(VERSION 3.22)
project("stitch-core-native-stub")

# 精简桩：编译一个什么都不做的 .so，满足 Gradle native build 流程
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(stitch-native SHARED src/main/cpp/stub.cpp)
