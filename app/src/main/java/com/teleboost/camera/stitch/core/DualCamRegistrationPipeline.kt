package com.teleboost.camera.stitch.core

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.graphics.Canvas
import android.util.Log

/**
 * 双摄配准管道 — Stage 27
 *
 * 全部在缩略图上操作以避免 OOM。
 * 缩略图 1/8，大约 512x384。
 * warp 变换矩阵参数已经实测确认。
 */
class DualCamRegistrationPipeline {

    companion object {
        private const val TAG = "DualCamReg"
        const val INITIAL_OPTICAL_SCALE = 2.929153f
        const val INITIAL_ROTATION_DEG = -0.232461f
        private const val INV_TX = 380.598492f
        private const val INV_TY = 495.979659f
        private const val CONFIDENCE_THRESHOLD = 0.35f
        private const val DISPARITY_THRESHOLD = 8
        const val THUMB_SCALE = 8
    }

    data class RegistrationResult(
        val success: Boolean,
        val warpedAuxBitmap: Bitmap? = null,
        val confidenceMask: Bitmap? = null,
        val fusionDecisionMask: Bitmap? = null,
        val score: Float = 0f,
        val usedScale: Float = INITIAL_OPTICAL_SCALE,
        val usedRotation: Float = INITIAL_ROTATION_DEG,
        val errorMessage: String = "",
        /** master（ID4）缩略图 bitmat, 融合阶段要用 */
        val masterThumb: Bitmap? = null,
        /** aux（ID2）缩略图, 融合阶段要用 */
        val auxThumb: Bitmap? = null
    )

    fun register(masterJpg: ByteArray, auxJpg: ByteArray): RegistrationResult {
        return try {
            val thumbOpts = BitmapFactory.Options().apply { inSampleSize = THUMB_SCALE }
            val masterThumb = BitmapFactory.decodeByteArray(masterJpg, 0, masterJpg.size, thumbOpts)
            val auxThumb = BitmapFactory.decodeByteArray(auxJpg, 0, auxJpg.size, thumbOpts)
            if (masterThumb == null || auxThumb == null) {
                return RegistrationResult(false, errorMessage = "缩略图解码失败")
            }

            val tw = masterThumb.width
            val th = masterThumb.height

            // 1. warp ID2 → ID4 坐标系（缩略图级别）
            val warpedThumb = warpAuxToMasterThumb(auxThumb, tw, th)
            if (warpedThumb == null) return RegistrationResult(false, errorMessage = "warp 失败")

            // 2. NCC 置信度
            val confidence = computeNccConfidence(masterThumb, warpedThumb)

            // 3. 决策 mask（缩略图尺寸）
            val maskThumb = computeDecisionMaskThumb(masterThumb, warpedThumb, confidence)

            // 4. masterThumb 保留给 fusion 用
            RegistrationResult(
                success = true,
                warpedAuxBitmap = warpedThumb,
                fusionDecisionMask = maskThumb,
                score = confidence,
                usedScale = INITIAL_OPTICAL_SCALE,
                usedRotation = INITIAL_ROTATION_DEG,
                masterThumb = masterThumb,
                auxThumb = auxThumb
            )
        } catch (e: Exception) {
            Log.e(TAG, "配准异常", e)
            RegistrationResult(false, errorMessage = "配准异常: ${e.message}")
        }
    }

    /**
     * 缩略图级别 warp。
     * 逆变换矩阵 (ID4 target → ID2 source) 的平移分量需要按 THUMB_SCALE 缩放。
     */
    private fun warpAuxToMasterThumb(auxThumb: Bitmap, targetW: Int, targetH: Int): Bitmap? {
        return try {
            val cosR = Math.cos(Math.toRadians(INITIAL_ROTATION_DEG.toDouble())).toFloat()
            val sinR = Math.sin(Math.toRadians(INITIAL_ROTATION_DEG.toDouble())).toFloat()
            val s = INITIAL_OPTICAL_SCALE

            // 缩略图级别的正变换矩阵
            val m = Matrix()
            m.setValues(floatArrayOf(
                cosR / s, -sinR / s, -INV_TX / (s * THUMB_SCALE),
                sinR / s,  cosR / s, -INV_TY / (s * THUMB_SCALE),
                0f, 0f, 1f
            ))

            val result = Bitmap.createBitmap(targetW, targetH, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(result)
            canvas.drawBitmap(auxThumb, m, null)
            canvas.setBitmap(null)
            result
        } catch (e: Exception) {
            Log.e(TAG, "warp 异常", e)
            null
        }
    }

    /** NCC 置信度 — 缩略图 */
    private fun computeNccConfidence(master: Bitmap, warped: Bitmap): Float {
        if (master.width != warped.width || master.height != warped.height) return 0f
        val w = master.width
        val h = master.height
        val n = w * h

        val mPix = IntArray(n)
        val wPix = IntArray(n)
        master.getPixels(mPix, 0, w, 0, 0, w, h)
        warped.getPixels(wPix, 0, w, 0, 0, w, h)

        var sumM = 0.0; var sumW = 0.0
        for (i in 0 until n) { sumM += luma(mPix[i]).toDouble(); sumW += luma(wPix[i]).toDouble() }
        val meanM = (sumM / n).toFloat()
        val meanW = (sumW / n).toFloat()

        var cov = 0.0; var varM = 0.0; var varW = 0.0
        for (i in 0 until n) {
            val dm = luma(mPix[i]) - meanM; val dw = luma(wPix[i]) - meanW
            cov += dm * dw; varM += dm * dm; varW += dw * dw
        }
        val denom = Math.sqrt(varM * varW)
        val ncc = if (denom > 1e-8) (cov / denom).toFloat() else 0f
        return ((ncc + 1f) / 2f).coerceIn(0f, 1f)
    }

    /** 决策 mask — 缩略图 */
    private fun computeDecisionMaskThumb(master: Bitmap, warped: Bitmap, confidence: Float): Bitmap {
        val w = master.width; val h = master.height; val n = w * h
        val mPix = IntArray(n); val wPix = IntArray(n)
        master.getPixels(mPix, 0, w, 0, 0, w, h)
        warped.getPixels(wPix, 0, w, 0, 0, w, h)
        val maskPixels = IntArray(n)
        val cf = (confidence / 0.5f).coerceIn(0.2f, 2.0f)

        for (i in 0 until n) {
            val diff = Math.abs(luma(mPix[i]) - luma(wPix[i]))
            if (diff < DISPARITY_THRESHOLD && confidence > CONFIDENCE_THRESHOLD) {
                val w = ((DISPARITY_THRESHOLD - diff).toFloat() / DISPARITY_THRESHOLD * 255f * cf).toInt().coerceIn(0, 255)
                maskPixels[i] = (0xFF shl 24) or (w shl 16) or (w shl 8) or w
            } else {
                maskPixels[i] = 0xFF000000.toInt()
            }
        }
        val mask = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        mask.setPixels(maskPixels, 0, w, 0, 0, w, h)
        return mask
    }

    private fun luma(pixel: Int): Int {
        return ((0.299f * ((pixel shr 16) and 0xFF) + 0.587f * ((pixel shr 8) and 0xFF) + 0.114f * (pixel and 0xFF)).toInt().coerceIn(0, 255))
    }

    fun release() {}
}
