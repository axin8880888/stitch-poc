package com.teleboost.camera.jni

import com.teleboost.camera.stitch.core.OpenCvNativeBridge
import com.teleboost.camera.stitch.core.OpenCvNativeBridgeStub

/**
 * 与 Kotlin 层直接对接的 JNI 桥接类名占位。
 * 后续由 native-lib.cpp 中的 JNI 方法实现。
 */
class NativeBridge : OpenCvNativeBridge by OpenCvNativeBridgeStub()
