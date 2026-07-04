package com.teleboost.camera.stitch.ui

class CropController {
    fun suggestCropBounds(result: Any): String = "safe-auto-crop"
    fun applyPureCrop(result: Any, bounds: String): String = "crop-applied:$bounds"
    fun manualAdjust(bounds: String): String = "manual:$bounds"
    fun disableCrop(): String = "crop-disabled"
    fun currentCropStatus(enabled: Boolean, bounds: String): String = if (enabled) "enabled:$bounds" else "disabled"
}
