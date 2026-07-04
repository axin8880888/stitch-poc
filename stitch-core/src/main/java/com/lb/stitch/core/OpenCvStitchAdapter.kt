package com.teleboost.camera.stitch.core

class OpenCvStitchAdapter {
    fun prepare(frames: List<StitchFrame>) {
        // 真实拼接入口的骨架：后续接 OpenCV 特征提取、匹配、对齐、warp
    }

    fun stitch(frames: List<StitchFrame>): StitchResult {
        val quality = if (frames.isEmpty()) 0f else 0.92f
        val warnings = buildList {
            if (frames.size < 2) add("帧数过少，建议至少 2 帧")
            add("blending默认关闭")
            add("exposureCompensator默认关闭")
        }
        return StitchResult(
            bitmap = "opencv-stitch-placeholder:${frames.size}",
            cropBounds = "auto-pure-crop",
            qualityScore = quality,
            warnings = warnings
        )
    }

    fun setBlenderEnabled(enabled: Boolean) {}
    fun setExposureCompensatorEnabled(enabled: Boolean) {}
}
