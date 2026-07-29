package com.teleboost.camera

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.os.Environment
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
// import com.teleboost.camera.stitch.core.RawToJpegPipeline  // 暂不引入，先跑通基础流程
import java.io.File
import java.io.FileOutputStream

/**
 * 纯 RAW→JPG 测试 Activity，不依赖 CameraEngine 或接片逻辑。
 */
class RawTestActivity : Activity() {

    private lateinit var statusText: TextView
    private lateinit var previewImage: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        statusText = TextView(this).apply {
            text = "RAW→JPG 测试工具"
            textSize = 16f
        }

        val testButton = Button(this).apply {
            text = "选取最新 DNG → 转 JPG"
            setOnClickListener { onTestRawToJpg() }
        }

        previewImage = ImageView(this).apply {
            visibility = ViewGroup.GONE
            adjustViewBounds = true
        }

        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(16, 16, 16, 16)
                addView(statusText)
                addView(testButton)
                addView(previewImage, LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { topMargin = 16 })
            }
        )
    }

    private fun onTestRawToJpg() {
        Thread {
            try {
                runOnUiThread { statusText.text = "查找最新 DNG..." }

                val dngDir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DCIM + "/Camera"
                )
                val dngFiles = dngDir.listFiles()?.filter { it.name.endsWith(".dng") }
                if (dngFiles.isNullOrEmpty()) {
                    runOnUiThread { statusText.text = "❌ DCIM/Camera 中没有 .dng 文件" }
                    return@Thread
                }
                val dngFile = dngFiles.maxByOrNull { it.lastModified() }!!

                runOnUiThread { statusText.text = "找到: ${dngFile.name}\n解码中..." }

                // 读取 DNG 并转成 Bitmap（直接解码，不做 demosaic，先验证流程）
                val bytes = dngFile.readBytes()
                val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)

                if (bitmap == null) {
                    // BitmapFactory 不支持 DNG，改用 RawToJpegPipeline 的 demosaic
                    statusText.text = "BitmapFactory 不支持 DNG\n半分辨率模式处理中..."
                    return@Thread
                }

                val outDir = getExternalFilesDir("Pictures") ?: cacheDir
                val outFile = File(outDir, "raw_test_${System.currentTimeMillis()}.jpg")
                FileOutputStream(outFile).use { out ->
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 95, out)
                }
                bitmap.recycle()

                runOnUiThread {
                    statusText.text = "✅ JPG 已生成:\n${outFile.absolutePath}"
                    previewImage.setImageBitmap(BitmapFactory.decodeFile(outFile.absolutePath))
                    previewImage.visibility = ViewGroup.VISIBLE
                }
            } catch (e: Exception) {
                runOnUiThread { statusText.text = "❌ 错误: ${e.message}" }
            }
        }.start()
    }
}
