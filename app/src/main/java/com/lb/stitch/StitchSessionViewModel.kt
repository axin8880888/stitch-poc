package com.teleboost.camera.stitch

class StitchSessionViewModel {
    var state: StitchState = StitchState.IDLE
        private set

    fun start() { state = StitchState.PREPARING }
    fun beginCollecting() { state = StitchState.COLLECTING }
    fun beginAligning() { state = StitchState.ALIGNING }
    fun beginStitching() { state = StitchState.STITCHING }
    fun beginPreviewing() { state = StitchState.PREVIEWING }
    fun beginExporting() { state = StitchState.EXPORTING }
    fun complete() { state = StitchState.DONE }
    fun cancel() { state = StitchState.CANCELLED }
    fun reset() { state = StitchState.IDLE }
}
