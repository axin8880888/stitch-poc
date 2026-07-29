package com.teleboost.camera.stitch.core

data class StitchConfig(
    val blendEnabled: Boolean = false,
    val exposureCompensationEnabled: Boolean = false,
    val cropMode: String = "pure",
    val overlapHint: Int = 30,
    val outputFormat: String = "jpeg"
)
