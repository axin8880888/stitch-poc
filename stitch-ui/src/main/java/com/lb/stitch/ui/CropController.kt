package com.teleboost.camera.stitch.ui

import android.graphics.Bitmap
import android.graphics.Rect
import android.util.Log

/**
 * 纯裁切控制器。
 *
 * 红线约束：
 * - 只裁毛边，不做羽化、不做融合
 * - 不生成新像素
 * - 裁切框为纯矩形，不做透视变换
 */
class CropController {
    companion object {
        private const val TAG = "CropController"
    }

    /**
     * 从拼接结果中建议裁切边界。
     * 策略：识别非黑色/非透明边缘，找到最小的有效矩形。
     *
     * @param bitmap 拼接结果 Bitmap（含 warp 后的黑色/透明毛边）
     * @param safetyMarginPx 安全边距（防止裁到有效内容）
     * @return Rect 建议裁切框，null 表示无需裁切
     */
    fun suggestCropBounds(bitmap: Bitmap?, safetyMarginPx: Int = 0): Rect? {
        if (bitmap == null) return null

        val width = bitmap.width
        val height = bitmap.height
        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)

        var left = width
        var top = height
        var right = 0
        var bottom = 0

        // 扫描非黑色(或非透明)像素边界
        for (y in 0 until height) {
            for (x in 0 until width) {
                val pixel = pixels[y * width + x]
                if (!isBlackOrTransparent(pixel)) {
                    if (x < left) left = x
                    if (x > right) right = x
                    if (y < top) top = y
                    if (y > bottom) bottom = y
                }
            }
        }

        // 检查是否找到了有效内容
        if (left >= right || top >= bottom) {
            Log.w(TAG, "无法找到有效内容边界")
            return null
        }

        // 加上安全边距
        left = (left - safetyMarginPx).coerceAtLeast(0)
        top = (top - safetyMarginPx).coerceAtLeast(0)
        right = (right + safetyMarginPx).coerceAtMost(width - 1)
        bottom = (bottom + safetyMarginPx).coerceAtMost(height - 1)

        // 如果接近全图，则不裁切
        val contentArea = (right - left + 1) * (bottom - top + 1)
        val totalArea = width * height
        if (contentArea > totalArea * 0.98) {
            Log.d(TAG, "内容接近全图，无需裁切")
            return null
        }

        val rect = Rect(left, top, right, bottom)
        Log.d(TAG, "建议裁切: $rect (原图 ${width}x$height)")
        return rect
    }

    /**
     * 执行纯裁切。
     * 不做羽化、不做融合、不生成新像素。
     *
     * @param bitmap 源 Bitmap
     * @param bounds 裁切区域
     * @return 裁切后的 Bitmap
     */
    fun applyPureCrop(bitmap: Bitmap, bounds: Rect): Bitmap? {
        // 边界检查
        val safeBounds = Rect(
            bounds.left.coerceAtLeast(0),
            bounds.top.coerceAtLeast(0),
            bounds.right.coerceAtMost(bitmap.width - 1),
            bounds.bottom.coerceAtMost(bitmap.height - 1)
        )
        val width = safeBounds.width()
        val height = safeBounds.height()
        if (width <= 0 || height <= 0) return null

        return Bitmap.createBitmap(bitmap, safeBounds.left, safeBounds.top, width, height)
    }

    /**
     * 手动调整裁切框（用户微调入口）。
     *
     * @param currentBounds 当前裁切框
     * @param dx 水平偏移像素
     * @param dy 垂直偏移像素
     * @param bitmapWidth 图像宽度（限制边界）
     * @param bitmapHeight 图像高度（限制边界）
     * @return 调整后的 Rect
     */
    fun manualAdjust(
        currentBounds: Rect,
        dx: Int, dy: Int,
        bitmapWidth: Int, bitmapHeight: Int
    ): Rect {
        return Rect(
            (currentBounds.left + dx).coerceIn(0, bitmapWidth - 1),
            (currentBounds.top + dy).coerceIn(0, bitmapHeight - 1),
            (currentBounds.right + dx).coerceIn(0, bitmapWidth - 1),
            (currentBounds.bottom + dy).coerceIn(0, bitmapHeight - 1)
        )
    }

    /**
     * 禁用裁切（返回全图）。
     */
    fun disableCrop(bitmap: Bitmap): Bitmap = bitmap

    /**
     * 判断像素是否为黑色或透明（毛边）。
     */
    private fun isBlackOrTransparent(pixel: Int): Boolean {
        val alpha = (pixel shr 24) and 0xFF
        val red = (pixel shr 16) and 0xFF
        val green = (pixel shr 8) and 0xFF
        val blue = pixel and 0xFF

        // 透明
        if (alpha < 10) return true
        // 接近全黑
        return (red < 5 && green < 5 && blue < 5)
    }
}
