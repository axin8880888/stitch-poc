package com.teleboost.camera.stitch.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.View

/**
 * 已拍帧缩略图轨道。
 *
 * 位于取景器底部上方，水平排列已拍帧的 JPG 缩略图。
 * 每拍一帧自动追加到最后。
 */
class FrameThumbnailStrip(
    context: Context
) : View(context) {

    private val thumbWidth = 80f
    private val thumbHeight = 60f
    private val thumbGap = 8f
    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }
    private val emptyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(60, 255, 255, 255)
        style = Paint.Style.FILL
    }

    private val _thumbnails = mutableListOf<Bitmap>()
    val thumbnails: List<Bitmap> get() = _thumbnails.toList()

    var activeIndex: Int = -1
        set(value) { field = value; invalidate() }

    /**
     * 添加一张缩略图（从 JPG 字节解码）
     */
    fun addThumbnail(jpgBytes: ByteArray) {
        val bmp = BitmapFactory.decodeByteArray(jpgBytes, 0, jpgBytes.size)
            ?: return
        // 缩放到统一大小
        val scaled = Bitmap.createScaledBitmap(bmp, thumbWidth.toInt(), thumbHeight.toInt(), true)
        _thumbnails.add(scaled)
        activeIndex = _thumbnails.size - 1
        invalidate()
    }

    fun clear() {
        _thumbnails.forEach { it.recycle() }
        _thumbnails.clear()
        activeIndex = -1
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val startX = 16f
        val centerY = height / 2f - thumbHeight / 2f

        _thumbnails.forEachIndexed { index, bmp ->
            val x = startX + index * (thumbWidth + thumbGap)
            val rect = RectF(x, centerY, x + thumbWidth, centerY + thumbHeight)

            // 缩略图
            canvas.drawBitmap(bmp, x, centerY, null)

            // 边框 (当前活动帧高亮)
            val paint = if (index == activeIndex) {
                Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color = Color.argb(200, 255, 200, 0)
                    style = Paint.Style.STROKE
                    strokeWidth = 3f
                }
            } else borderPaint
            canvas.drawRoundRect(rect, 4f, 4f, paint)
        }

        // 如果没有任何缩略图，显示占位
        if (_thumbnails.isEmpty()) {
            val placeholderRect = RectF(startX, centerY, startX + thumbWidth, centerY + thumbHeight)
            canvas.drawRoundRect(placeholderRect, 4f, 4f, emptyPaint)
            val hintPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(120, 255, 255, 255)
                textSize = 24f
                textAlign = Paint.Align.CENTER
            }
            canvas.drawText("拍帧", startX + thumbWidth / 2f, centerY + thumbHeight / 2f + 8f, hintPaint)
        }
    }
}
