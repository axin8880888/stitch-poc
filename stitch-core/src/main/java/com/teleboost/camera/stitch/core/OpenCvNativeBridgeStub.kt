package com.teleboost.camera.stitch.core

@Deprecated("Stub retained only as fallback during migration")
class OpenCvNativeBridgeStub : OpenCvNativeBridge {
    override fun initNative(workDir: String, enableBlender: Boolean, enableExposureCompensator: Boolean, cropMode: String): Boolean = true
    override fun prepareNative(frameCount: Int, overlapHint: Int, maxDimension: Int): Boolean = frameCount > 0
    override fun pushFrameNative(index: Int, imageRef: String, timestamp: Long, exposureInfo: String?, iso: Int?, awb: String?): Boolean = true
    override fun stitchNative(): String = "native-stitch-placeholder"
    override fun suggestCropBoundsNative(stitchResultRef: String, safetyMarginPx: Int): String = "crop-bounds-placeholder"
    override fun applyPureCropNative(stitchResultRef: String, cropBoundsRef: String): String = "cropped-placeholder"
    override fun writeResultNative(outputDir: String, fileName: String, format: String): String = "$outputDir/$fileName.$format"
    override fun setBlenderEnabled(enabled: Boolean) {}
    override fun setExposureCompensatorEnabled(enabled: Boolean) {}
    override fun releaseNative() {}
}
