package com.teleboost.camera.stitch.core

import com.teleboost.camera.jni.NativeBridge

class OpenCvPipeline(
    private val nativeBridge: OpenCvNativeBridge = NativeBridge()
) {
    fun run(frames: List<StitchFrame>, workDir: String = "/storage/emulated/0/Download/篮筐整改/opencv_stitch_poc"): StitchResult {
        nativeBridge.initNative(
            workDir = workDir,
            enableBlender = false,
            enableExposureCompensator = false,
            cropMode = "pure"
        )
        nativeBridge.setBlenderEnabled(false)
        nativeBridge.setExposureCompensatorEnabled(false)
        nativeBridge.prepareNative(frames.size)

        frames.forEachIndexed { index, frame ->
            nativeBridge.pushFrameNative(
                index = index,
                imageRef = frame.bitmap?.toString() ?: "frame-$index",
                timestamp = frame.timestamp,
                exposureInfo = frame.exposureInfo,
                iso = frame.iso,
                awb = frame.awb
            )
        }

        val stitchRef = nativeBridge.stitchNative()
        val cropRef = nativeBridge.suggestCropBoundsNative(stitchRef, safetyMarginPx = 0)
        val finalRef = nativeBridge.applyPureCropNative(stitchRef, cropRef)
        val outRef = nativeBridge.writeResultNative(workDir, "stitched_result", "jpeg")
        nativeBridge.releaseNative()

        return StitchResult(
            bitmap = outRef.ifBlank { finalRef },
            cropBounds = cropRef,
            qualityScore = if (frames.isEmpty()) 0f else 0.92f,
            warnings = buildList {
                if (frames.size < 2) add("帧数过少，建议至少 2 帧")
                add("blending默认关闭")
                add("exposureCompensator默认关闭")
            }
        )
    }
}
