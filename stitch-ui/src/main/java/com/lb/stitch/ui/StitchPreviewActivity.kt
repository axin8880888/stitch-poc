package com.teleboost.camera.stitch.ui

import android.graphics.Bitmap
import android.graphics.Rect
import android.util.Log
import com.teleboost.camera.stitch.PocResult
import com.teleboost.camera.stitch.PocResultStore
import com.teleboost.camera.stitch.core.StitchConfig

/**
 * 接片结果预览 Activity（无 UI，仅逻辑层）。
 *
 * 职责：
 * - 展示拼接结果信息
 * - 提供裁切逻辑入口
 * - 导出预览就绪信号
 */
class StitchPreviewActivity(
    private val config: StitchConfig = StitchConfig.HONEST_DEFAULT
) {
    companion object {
        private const val TAG = "StitchPreview"
    }

    private val cropController = CropController()
    private var stitchBitmap: Bitmap? = null
    private var cropBounds: Rect? = null
    private var cropEnabled: Boolean = true

    /**
     * 加载拼接结果并建议裁切边界。
     */
    fun loadResult(bitmap: Bitmap) {
        stitchBitmap = bitmap
        cropBounds = suggestCropBounds(bitmap)
        Log.d(TAG, "结果加载: ${bitmap.width}x${bitmap.height}, 裁切建议: $cropBounds")
    }

    /**
     * 建议裁切边界。
     */
    fun suggestCropBounds(bitmap: Bitmap): Rect? {
        return cropController.suggestCropBounds(bitmap, safetyMarginPx = 0)
    }

    /**
     * 执行裁切并返回裁切后的 Bitmap。
     */
    fun applyCrop(customBounds: Rect? = null): Bitmap? {
        val bitmap = stitchBitmap ?: return null
        val bounds = customBounds ?: cropBounds ?: return bitmap

        if (!cropEnabled) {
            Log.d(TAG, "裁切已禁用，返回全图")
            return bitmap
        }

        val cropped = cropController.applyPureCrop(bitmap, bounds)
        Log.d(TAG, "裁切完成: $bounds → ${cropped?.width}x${cropped?.height}")
        return cropped
    }

    /**
     * 禁用/启用裁切。
     */
    fun setCropEnabled(enabled: Boolean) {
        cropEnabled = enabled
        Log.d(TAG, "裁切: ${if (enabled) "启用" else "禁用"}")
    }

    /**
     * 用户手动调整裁切框。
     */
    fun manualAdjustCrop(dx: Int, dy: Int) {
        val bitmap = stitchBitmap ?: return
        val current = cropBounds ?: return
        cropBounds = cropController.manualAdjust(
            current, dx, dy, bitmap.width, bitmap.height
        )
        Log.d(TAG, "裁切手动调整: $dx, $dy → $cropBounds")
    }

    /**
     * 重置裁切。
     */
    fun resetCrop() {
        stitchBitmap?.let { cropBounds = suggestCropBounds(it) }
        Log.d(TAG, "裁切已重置")
    }

    fun getPreviewInfo(): String {
        val bitmap = stitchBitmap ?: return "暂无结果"
        val bounds = cropBounds
        return buildString {
            appendLine("尺寸: ${bitmap.width}x${bitmap.height}")
            if (bounds != null) {
                appendLine("裁切: ${bounds.toShortString()}")
                appendLine("裁切后: ${bounds.width()}x${bounds.height()}")
            }
            appendLine("裁切模式: ${config.cropMode}")
            appendLine("blending: ${config.blendEnabled}")
        }.trimEnd()
    }

    /**
     * 点击裁切按钮后的逻辑。
     */
    fun onCropClicked(): String {
        val r = PocResultStore.current() ?: return "暂无结果可裁切"
        val bounds = cropBounds
        return if (bounds != null) {
            PocResultStore.save(
                r.copy(
                    cropStatus = "applied",
                    cropBoundsSummary = bounds.toShortString(),
                    notes = r.notes + "自动裁切: ${bounds.toShortString()}"
                )
            )
            "已应用自动裁切: ${bounds.toShortString()}"
        } else {
            "无需裁切（已接近全图）"
        }
    }

    /**
     * 导出点击逻辑。
     */
    fun onExportClicked(): String {
        val r = PocResultStore.current() ?: return "暂无结果可导出"
        val cropped = applyCrop()
        if (cropped == null) return "裁切失败，无法导出"

        PocResultStore.save(
            r.copy(
                exportStatus = "export-ready",
                notes = r.notes + "裁切后导出: ${cropped.width}x${cropped.height}"
            )
        )
        return "导出就绪: ${cropped.width}x${cropped.height}"
    }
}
