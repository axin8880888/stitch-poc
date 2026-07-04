package com.teleboost.camera.stitch

object FakeFrameSource {
    fun frames(): List<StitchFrame> = listOf(
        StitchFrame(sequenceIndex = 1, timestamp = 1L, exposureInfo = "EV0", iso = 100, awb = "lock"),
        StitchFrame(sequenceIndex = 2, timestamp = 2L, exposureInfo = "EV0", iso = 100, awb = "lock"),
        StitchFrame(sequenceIndex = 3, timestamp = 3L, exposureInfo = "EV0", iso = 100, awb = "lock")
    )
}
