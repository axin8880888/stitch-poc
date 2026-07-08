package com.teleboost.camera.stitch.core

data class StitchFrame(
    val bitmap: Any? = null,
    val timestamp: Long = 0L,
    val exposureInfo: String? = null,
    val iso: Int? = null,
    val awb: String? = null,
    val sequenceIndex: Int = 0
)
