package com.teleboost.camera.stitch.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View

/**
 * 接片模式下的取景器叠加层。
 *
 * 绘制内容：
 * - 当前帧数/总帧数 (左上角)
 * - 重叠引导线 (半透明垂直线，提示上一帧边界)
 * - 拼接方向指示条
 */
class StitchOverlay(
    context: Context,
    private val textPaint: Paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 48f
        isAntiAlias = true
    },
    private val guideLinePaint: Paint = Paint().apply {
        color = Color.argb(120, 255, 255, 255)
        strokeWidth = 3f
        style = Paint.Style.STROKE
    },
    private val progressPaint: Paint = Paint().apply {
        color = Color.argb(80, 255, 200, 0)
        style = Paint.Style.FILL
    }
) : View(context) {

    var currentFrame: Int = 0
        set(value) { field = value; invalidate() }
    var totalFrames: Int = 5
        set(value) { field = value; invalidate() }
    var frameCaptured: Boolean = false
        set(value) { field = value; invalidate() }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        // 1. 帧计数 - 左上角
        val countText = "$currentFrame/$totalFrames"
        canvas.drawText(countText, 24f, textPaint.textSize + 16f, textPaint)

        // 2. 重叠引导线 - 取景器右侧 1/3 位置
        val guideX = width * 0.66f
        canvas.drawLine(guideX, 0f, guideX, height.toFloat(), guideLinePaint)

        // 3. 已拍帧进度条 - 底部细条
        val barHeight = 6f
        val barY = height - barHeight - 8f
        val barWidth = width.toFloat() - 32f
        val progress = if (totalFrames > 0) currentFrame.toFloat() / totalFrames else 0f
        canvas.drawRect(16f, barY, 16f + barWidth * progress, barY + barHeight, progressPaint)

        // 4. 拍帧提示
        if (frameCaptured && currentFrame < totalFrames) {
            val hintPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(200, 100, 255, 100)
                textSize = 36f
            }
            canvas.drawText("✓ 已拍 $currentFrame 张，继续平移", 24f, height - 80f, hintPaint)
        }
    }
}
