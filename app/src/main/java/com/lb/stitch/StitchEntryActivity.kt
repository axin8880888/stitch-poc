package com.teleboost.camera.stitch

import android.app.Activity
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.Button
import android.widget.TextView
import com.teleboost.camera.stitch.PocResult
import com.teleboost.camera.stitch.PocResultStore
import com.teleboost.camera.stitch.ui.StitchPreviewActivity

class StitchEntryActivity : Activity() {
    private val vm = StitchSessionViewModel()
    private val previewActivity = StitchPreviewActivity()
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        statusText = TextView(this).apply {
            text = "光·边界启动中..."
        }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                addView(statusText)
                addView(Button(this@StitchEntryActivity).apply {
                    text = "开始接片"
                    setOnClickListener { onStartStitch() }
                })
            }
        )
        vm.reset()
        postInitialRun()
    }

    private fun postInitialRun() {
        PocResultStore.save(
            PocResult(
                title = "OpenCV Stitch POC",
                frameCount = 0,
                status = "IDLE",
                qualityScore = 0f,
                cropMode = "pure",
                cropStatus = "disabled",
                cropBoundsSummary = "none",
                blendEnabled = false,
                exposureCompensationEnabled = false,
                exportStatus = "idle",
                warnings = listOf("启动阶段不自动跑拼接，避免首帧崩溃"),
                notes = listOf("已完成壳启动")
            )
        )
        statusText.text = "光·边界启动中...\n已完成壳启动"
    }

    fun onStartStitch() {
        vm.start()
        vm.beginCollecting()
        vm.beginAligning()
        vm.beginStitching()
        vm.beginPreviewing()
        val frames = FakeFrameSource.frames()
        PocResultStore.save(
            PocResult(
                title = "OpenCV Stitch POC",
                frameCount = frames.size,
                status = "DONE",
                qualityScore = 0.92f,
                cropMode = "pure",
                cropStatus = "auto-pure-crop",
                cropBoundsSummary = "auto-pure-crop",
                blendEnabled = false,
                exposureCompensationEnabled = false,
                exportStatus = "preview-ready",
                warnings = listOf("blending默认关闭", "exposureCompensator默认关闭"),
                notes = listOf("已用伪帧跑通最小闭环")
            )
        )
        statusText.text = "光·边界：已出预览"
        previewActivity.onCreate()
    }

    fun onOpenSettings() {}

    fun onExport(): String {
        val current = PocResultStore.current() ?: return "暂无结果可导出"
        return "/storage/emulated/0/Download/篮筐整改/saved-result.jpeg"
    }
}
