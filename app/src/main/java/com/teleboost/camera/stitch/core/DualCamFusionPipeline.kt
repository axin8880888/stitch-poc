package com.teleboost.camera.stitch.core

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import java.io.ByteArrayOutputStream

/**
 * 双摄融合管道 — Stage 27
 *
 * ID4 Master × ID2 Auxiliary 像素级融合。
 * ID4 决定构图、颜色、细节和输出尺寸。
 * ID2 只参与低视差的高光恢复区域。
 */
class DualCamFusionPipeline {

    companion object {
        private const val TAG = "DualCamFusion"
        // 高光检测阈值（亮度 0~1）
        private const val HIGHLIGHT_THRESHOLD = 0.70f
        // ID2 融合强度系数
        private const val FUSION_STRENGTH = 0.65f
    }

    data class FusionOutput(
        val success: Boolean,
        val fusedJpg: ByteArray? = null,
        val maskJpg: ByteArray? = null,
        val errorMessage: String = ""
    )

    /**
     * 执行 ID4 + ID2 融合
     */
    fun fuse(
        masterJpg: ByteArray,
        auxJpg: ByteArray,
        registrationResult: DualCamRegistrationPipeline.RegistrationResult
    ): FusionOutput {
        return try {
            if (!registrationResult.success) {
                // 配准失败 → 安全输出 ID4 原片
                return FusionOutput(true, fusedJpg = masterJpg,
                    errorMessage = "配准失败，已回退 ID4 原片")
            }

            val masterBmp = BitmapFactory.decodeByteArray(masterJpg, 0, masterJpg.size)
            val warpedAuxBmp = registrationResult.warpedAuxBitmap
            val decisionMaskBmp = registrationResult.fusionDecisionMask

            if (masterBmp == null || warpedAuxBmp == null || decisionMaskBmp == null) {
                return FusionOutput(true, fusedJpg = masterJpg,
                    errorMessage = "位图无效，已回退 ID4 原片")
            }

            val fusedBmp = performFusion(masterBmp, warpedAuxBmp, decisionMaskBmp)

            // 编码 JPEG
            val fusedJpg = bmpToJpeg(fusedBmp, 95)
            val maskJpg = bmpToJpeg(decisionMaskBmp, 90)

            masterBmp.recycle()
            warpedAuxBmp.recycle()
            fusedBmp.recycle()

            FusionOutput(success = true, fusedJpg = fusedJpg, maskJpg = maskJpg)
        } catch (e: Exception) {
            Log.e(TAG, "融合异常", e)
            FusionOutput(true, fusedJpg = masterJpg,
                errorMessage = "融合异常: ${e.message}，已回退 ID4 原片")
        }
    }

    /**
     * 像素级融合
     */
    private fun performFusion(master: Bitmap, warpedAux: Bitmap, decisionMask: Bitmap): Bitmap {
        val w = master.width
        val h = master.height
        val result = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)

        val masterPixels = IntArray(w * h)
        val auxPixels = IntArray(w * h)
        val maskPixels = IntArray(w * h)
        master.getPixels(masterPixels, 0, w, 0, 0, w, h)
        warpedAux.getPixels(auxPixels, 0, w, 0, 0, w, h)
        decisionMask.getPixels(maskPixels, 0, w, 0, 0, w, h)

        val resultPixels = IntArray(w * h)

        for (i in masterPixels.indices) {
            val maskW = (maskPixels[i] shr 16) and 0xFF
            if (maskW == 0) {
                resultPixels[i] = masterPixels[i]
                continue
            }

            val mR = (masterPixels[i] shr 16) and 0xFF
            val mG = (masterPixels[i] shr 8) and 0xFF
            val mB = masterPixels[i] and 0xFF
            val aR = (auxPixels[i] shr 16) and 0xFF
            val aG = (auxPixels[i] shr 8) and 0xFF
            val aB = auxPixels[i] and 0xFF

            // 主图亮度
            val mb = (0.299f * mR + 0.587f * mG + 0.114f * mB) / 255f

            // 高光判断：亮度越高越倾向用 ID2 恢复细节
            val hf = if (mb > HIGHLIGHT_THRESHOLD) 1.0f else (mb / HIGHLIGHT_THRESHOLD * 0.5f).coerceIn(0f, 0.5f)
            val weight = (maskW / 255f) * hf * FUSION_STRENGTH

            val fR = (mR * (1f - weight) + aR * weight).toInt().coerceIn(0, 255)
            val fG = (mG * (1f - weight) + aG * weight).toInt().coerceIn(0, 255)
            val fB = (mB * (1f - weight) + aB * weight).toInt().coerceIn(0, 255)

            resultPixels[i] = (0xFF shl 24) or (fR shl 16) or (fG shl 8) or fB
        }

        result.setPixels(resultPixels, 0, w, 0, 0, w, h)
        return result
    }

    private fun bmpToJpeg(bmp: Bitmap, quality: Int): ByteArray {
        val os = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, quality, os)
        return os.toByteArray()
    }
}
