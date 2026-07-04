package com.teleboost.camera.stitch

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
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
        Handler(Looper.getMainLooper()).post {
            val frames: List<StitchFrame> = FakeFrameSource.frames()
            val result = pipeline.run(frames)
            val cropStatus = cropController.currentCropStatus(true, result.cropBounds?.toString() ?: "none")
            window.decorView.post {
                (findViewById<TextView>(android.R.id.content) ?: return@post).text =
                    "光·边界启动中...\n已完成基础初始化"
            }
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
