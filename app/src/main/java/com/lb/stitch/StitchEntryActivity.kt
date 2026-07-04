package com.teleboost.camera.stitch

import android.app.Activity
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.TextView
import com.teleboost.camera.stitch.core.OpenCvPipeline
import com.teleboost.camera.stitch.core.StitchFrame

class StitchEntryActivity : Activity() {
    private val vm = StitchSessionViewModel()
    private val pipeline = OpenCvPipeline()
    private val cropController = com.teleboost.camera.stitch.ui.CropController()
    private val exportManager = com.teleboost.camera.stitch.export.ExportManager()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(TextView(context).apply { text = "光·边界启动中..." })
            }
        )
        vm.reset()
        postInitialRun()
    }

    private fun postInitialRun() {
        window.decorView.post {
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
    }

    fun onStartStitch() {
        vm.start()
        vm.beginCollecting()
        vm.beginAligning()
        vm.beginStitching()
        vm.beginPreviewing()
    }

    fun onOpenSettings() {}

    fun onExport(): String {
        val current = PocResultStore.current() ?: return "暂无结果可导出"
        return exportManager.saveToFolder(current, "/storage/emulated/0/Download/篮筐整改")
    }
}
