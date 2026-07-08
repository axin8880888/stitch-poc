package com.teleboost.camera.stitch

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import com.teleboost.camera.stitch.core.StitchFrame
import java.io.ByteArrayOutputStream

/**
 * 伪帧数据源。
 *
 * 生成占位的 StitchFrame 列表，每个 frame 包含一个 PNG 编码的 Bitmap 字节数组，
 * 供仿真拼接模式（无 JNI）通过 BitmapFactory.decodeByteArray 正确解码。
 * 帧内容为 300x200 的纯色画布上绘制序号数字，方便肉眼区分。
 */
object FakeFrameSource {

    private const val FRAME_WIDTH = 300
    private const val FRAME_HEIGHT = 200
    private const val TEXT_COLOR = Color.WHITE
    private const val TEXT_SIZE = 72f

    fun frames(): List<StitchFrame> = listOf(
        makeFrame(sequenceIndex = 1, timestamp = 1L, bgColor = Color.rgb(60, 70, 80)),
        makeFrame(sequenceIndex = 2, timestamp = 2L, bgColor = Color.rgb(70, 80, 60)),
        makeFrame(sequenceIndex = 3, timestamp = 3L, bgColor = Color.rgb(80, 60, 70))
    )

    private fun makeFrame(
        sequenceIndex: Int,
        timestamp: Long,
        bgColor: Int
    ): StitchFrame {
        val bitmap = Bitmap.createBitmap(FRAME_WIDTH, FRAME_HEIGHT, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(bgColor)

        val paint = Paint().apply {
            color = TEXT_COLOR
            textSize = TEXT_SIZE
            isAntiAlias = true
            textAlign = Paint.Align.CENTER
        }
        val x = FRAME_WIDTH / 2f
        val y = FRAME_HEIGHT / 2f + paint.textSize / 3f
        canvas.drawText("#$sequenceIndex", x, y, paint)

        // 用 PNG 编码压缩，这样 BitmapFactory.decodeByteArray 才能解码
        val pngBytes = compressToPng(bitmap)
        bitmap.recycle()

        return StitchFrame(
            bitmap = pngBytes,
            sequenceIndex = sequenceIndex,
            timestamp = timestamp,
            exposureInfo = "EV0",
            iso = 100,
            awb = "lock"
        )
    }

    private fun compressToPng(bitmap: Bitmap): ByteArray {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
        return stream.toByteArray()
    }
}
