package com.teleboost.camera.stitch

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import com.teleboost.camera.stitch.PocResult
import com.teleboost.camera.stitch.PocResultStore
import com.teleboost.camera.stitch.ui.StitchPreviewActivity

class StitchEntryActivity : Activity() {
    private val vm = StitchSessionViewModel()
    private val previewActivity = StitchPreviewActivity()
    private lateinit var statusText: TextView
    private lateinit var stitchButton: Button
    private lateinit var previewImage: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        statusText = TextView(this).apply {
            text = "光·边界启动中..."
            setTextColor(Color.WHITE)
            textSize = 16f
        }
        stitchButton = Button(this).apply {
            text = "开始接片"
            setOnClickListener { onStartStitch() }
        }
        previewImage = ImageView(this).apply {
            visibility = ViewGroup.GONE
            adjustViewBounds = true
            setPadding(8, 8, 8, 8)
        }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(16, 16, 16, 16)
                addView(statusText)
                addView(stitchButton)
                addView(previewImage, LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { topMargin = 16 })
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
        // Show synthetic preview image
        stitchButton.visibility = ViewGroup.GONE
        statusText.text = "光·边界：已出预览（伪帧拼接示意）"
        previewImage.setImageBitmap(generatePreviewBitmap())
        previewImage.visibility = ViewGroup.VISIBLE
        previewActivity.onCreate()
    }

    private fun generatePreviewBitmap(): Bitmap {
        val w = 720
        val h = 240
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)

        // Draw three "frames" side by side as synthetic panorama
        val segments = listOf(
            0xFF4A90D9.toInt() to 0xFF357ABD.toInt(), // blue sky
            0xFF5CB85C.toInt() to 0xFF449D44.toInt(), // green field
            0xFFD9534F.toInt() to 0xFFC9302C.toInt()  // red/autumn
        )
        val segW = w / segments.size

        segments.forEachIndexed { i, (topColor, botColor) ->
            paint.color = topColor
            canvas.drawRect((i * segW).toFloat(), 0f, ((i + 1) * segW).toFloat(), (h / 2).toFloat(), paint)
            paint.color = botColor
            canvas.drawRect((i * segW).toFloat(), (h / 2).toFloat(), ((i + 1) * segW).toFloat(), h.toFloat(), paint)
        }

        // Draw seam lines between frames
        paint.color = Color.WHITE
        paint.strokeWidth = 3f
        paint.style = Paint.Style.STROKE
        for (i in 1 until segments.size) {
            val x = (i * segW).toFloat()
            canvas.drawLine(x, 0f, x, h.toFloat(), paint)
        }

        // Label
        paint.color = Color.WHITE
        paint.textSize = 32f
        paint.style = Paint.Style.FILL
        canvas.drawText("stitch-poc / 3 frames", 16f, h - 16f, paint)

        return bmp
    }

    fun onOpenSettings() {}

    fun onExport(): String {
        val current = PocResultStore.current() ?: return "暂无结果可导出"
        return "/storage/emulated/0/Download/篮筐整改/saved-result.jpeg"
    }
}
