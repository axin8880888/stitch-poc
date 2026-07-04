package com.teleboost.camera.stitch

enum class StitchState {
    IDLE,
    PREPARING,
    COLLECTING,
    ALIGNING,
    STITCHING,
    PREVIEWING,
    EXPORTING,
    DONE,
    CANCELLED
}
