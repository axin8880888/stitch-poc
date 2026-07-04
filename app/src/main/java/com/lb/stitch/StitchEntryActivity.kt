package com.teleboost.camera.stitch

import com.teleboost.camera.stitch.core.OpenCvPipeline
import com.teleboost.camera.stitch.core.StitchFrame

class StitchEntryActivity {
    private val vm = StitchSessionViewModel()
    private val pipeline = OpenCvPipeline()
    private val cropController = com.teleboost.camera.stitch.ui.CropController()
    private val exportManager = com.teleboost.camera.stitch.export.ExportManager()

    fun onCreate() {
        vm.reset()
        val frames: List<StitchFrame> = FakeFrameSource.frames()
        val result = pipeline.run(frames)
        val cropStatus = cropController.currentCropStatus(true, result.cropBounds?.toString() ?: "none")
        PocResultStore.save(
            PocResult(
                title = "接片原型结果",
                frameCount = frames.size,
                status = "ready",
                qualityScore = result.qualityScore,
                cropMode = "pure",
                cropStatus = cropStatus,
                cropBoundsSummary = result.cropBounds?.toString() ?: "none",
                blendEnabled = false,
                exposureCompensationEnabled = false,
                exportStatus = "idle",
                warnings = result.warnings,
                notes = listOf(
                    "OpenCV真实接口骨架已接入",
                    "默认关闭 blending",
                    "默认关闭曝光补偿"
                )
            )
        )
    }

    fun onStartStitch() {
        vm.start()
        vm.beginCollecting()
        vm.beginAligning()
        vm.beginStitching()
        vm.beginPreviewing()
    }

    fun onOpenSettings() {}

    fun onExport() = exportManager.saveToFolder(PocResultStore.current() ?: return, "/storage/emulated/0/Download/篮筐整改")
}
