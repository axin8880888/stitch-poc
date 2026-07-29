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
import com.teleboost.camera.stitch.ui.StitchCameraScreen
import com.teleboost.camera.stitch.core.StitchCameraBridge
import android.graphics.BitmapFactory
import java.io.File
import java.io.FileOutputStream

class StitchEntryActivity : Activity() {
    private val vm = StitchSessionViewModel()
    private lateinit var statusText: TextView
    private lateinit var stitchButton: Button
    private lateinit var stitchModeButton: Button
    private lateinit var rawTestButton: Button
    private lateinit var previewImage: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        statusText = TextView(this).apply {
            text = "光·边界启动中..."
            setTextColor(Color.WHITE)
            textSize = 16f
        }
        stitchButton = Button(this).apply {
            text = "开始接片 (伪帧演示)"
            setOnClickListener { onStartStitch() }
        }
        stitchModeButton = Button(this).apply {
            text = "进入接片模式 (CameraEngine 对接)"
            setOnClickListener { onEnterStitchMode() }
        }
        rawTestButton = Button(this).apply {
            text = "RAW→JPG 测试"
            setOnClickListener { onRawToJpegTest() }
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
                addView(stitchModeButton)
                addView(rawTestButton)
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

    private fun onEnterStitchMode() {
        // P0: 进入接片模式。主工程对接时注入真实 StitchCameraBridge。
        // 当前 POC 中使用空实现占位，后续由 CameraEngine 实现。
        val placeholderBridge = object : StitchCameraBridge {
            override fun captureStill(callback: (ByteArray) -> Unit) {}
            override val isProcessing: Boolean get() = false
            override val currentLensInfo: String get() = "35mm"
            override fun onStitchModeEnter() {}
            override fun onStitchModeExit() {}
        }
        MainActivityBridge.openStitchFlow(this, placeholderBridge)
    }

    fun onOpenSettings() {}

    fun onExport(): String {
        val current = PocResultStore.current() ?: return "暂无结果可导出"
        return "/storage/emulated/0/Download/篮筐整改/saved-result.jpeg"
    }

    /**
     * RAW→JPG 测试：从 DCIM/Camera 目录读取第一张 .dng 文件，
     * 用 RawToJpegPipeline 转成 JPG 并保存，预览结果。
     */
    private fun onRawToJpegTest() {
        statusText.text = "RAW→JPG 测试中..."
        val saveDir = getExternalFilesDir(null) ?: return
        val dngDir = android.os.Environment.getExternalStoragePublicDirectory(
            android.os.Environment.DIRECTORY_DCIM + "/Camera"
        )
        val dngFile = dngDir.listFiles()?.filter { it.name.endsWith(".dng") }?.maxByOrNull { it.lastModified() }
        if (dngFile == null) {
            statusText.text = "❌ DCIM/Camera 中没有 .dng 文件"
            return
        }
        statusText.text = "找到 DNG: ${dngFile.name}\n正在处理..."

        Thread {
            try {
                // 读取 DNG 为 ByteArray
                val rawBytes = dngFile.readBytes()
                val bmp = BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size)
                if (bmp == null) {
                    runOnUiThread { statusText.text = "❌ BitmapFactory 无法解码 DNG" }
                    return@Thread
                }
                val jpgFile = File(saveDir, "raw_test_${System.currentTimeMillis()}.jpg")
                FileOutputStream(jpgFile).use { out ->
                    bmp.compress(Bitmap.CompressFormat.JPEG, 95, out)
                }
                bmp.recycle()
                runOnUiThread {
                    statusText.text = "✅ 测试 JPG 已保存:\n${jpgFile.absolutePath}"
                    previewImage.setImageBitmap(BitmapFactory.decodeFile(jpgFile.absolutePath))
                    previewImage.visibility = ViewGroup.VISIBLE
                }
            } catch (e: Exception) {
                runOnUiThread { statusText.text = "❌ 错误: ${e.message}" }
            }
        }.start()
    }
}
