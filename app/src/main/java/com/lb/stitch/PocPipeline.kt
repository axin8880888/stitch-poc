package com.teleboost.camera.stitch

import com.teleboost.camera.stitch.core.OpenCvStitchAdapter

object PocPipeline {
    private val adapter = OpenCvStitchAdapter()

    fun runFakeStitch(): Any {
        val frames = FakeFrameSource.frames()
        adapter.prepare(frames)
        return adapter.stitch(frames)
    }
}
