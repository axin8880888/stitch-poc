package com.teleboost.camera.stitch.core

import com.teleboost.camera.stitch.core.StitchFrame

/**
 * 真实 OpenCV / JNI 接口签名草案。
 *
 * 约束：
 * - 仅做几何接片
 * - 默认关闭 blending
 * - 默认关闭 exposure compensator
 * - 不进入光边界主拍照链
 */
interface OpenCvNativeBridge {
    fun initNative(
        workDir: String,
        enableBlender: Boolean = false,
        enableExposureCompensator: Boolean = false,
        cropMode: String = "pure"
    ): Boolean

    fun prepareNative(
        frameCount: Int,
        overlapHint: Int = 30,
        maxDimension: Int = 4096
    ): Boolean

    fun pushFrameNative(
        index: Int,
        imageRef: String,
        timestamp: Long,
        exposureInfo: String?,
        iso: Int?,
        awb: String?
    ): Boolean

    fun stitchNative(): String

    fun suggestCropBoundsNative(
        stitchResultRef: String,
        safetyMarginPx: Int = 0
    ): String

    fun applyPureCropNative(
        stitchResultRef: String,
        cropBoundsRef: String
    ): String

    fun writeResultNative(
        outputDir: String,
        fileName: String,
        format: String = "jpeg"
    ): String

    fun setBlenderEnabled(enabled: Boolean)
    fun setExposureCompensatorEnabled(enabled: Boolean)
    fun releaseNative()
}
