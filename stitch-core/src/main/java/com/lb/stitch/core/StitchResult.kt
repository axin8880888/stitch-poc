package com.teleboost.camera.stitch.core

data class StitchResult(
    val bitmap: Any?,
    val cropBounds: Any? = null,
    val qualityScore: Float = 0f,
    val warnings: List<String> = emptyList()
)
