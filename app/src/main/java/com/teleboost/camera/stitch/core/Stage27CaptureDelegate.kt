package com.teleboost.camera.stitch.core

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.util.Log
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Stage 27 双摄融合委托 — 协调 ID4 Master + ID2 Aux 的拍照、配准、融合、保存全流程。
 *
 * 使用 MediaStore API 写入，兼容 Android 10+ Scoped Storage。
 */
class Stage27CaptureDelegate(
    private val context: Context,
    private val outputBaseDir: File
) {

    companion object {
        private const val TAG = "Stage27Delegate"
    }

    data class CaptureSessionOutput(
        val success: Boolean,
        val outputDir: File? = null,
        val masterFile: File? = null,
        val auxFile: File? = null,
        val fusedFile: File? = null,
        val maskFile: File? = null,
        val jsonFile: File? = null,
        val errorMessage: String = ""
    )

    /**
     * 处理一次双摄拍照结果
     *
     * @param masterJpg ID4 master JPEG
     * @param auxJpg    ID2 aux JPEG
     * @param sessionDirName 会话目录名（可选，自动生成）
     */
    fun processCapture(
        masterJpg: ByteArray,
        auxJpg: ByteArray,
        sessionDirName: String? = null
    ): CaptureSessionOutput {
        val startTime = System.currentTimeMillis()
        val dirName = sessionDirName ?: "fusion_${System.currentTimeMillis()}"
        val sessionDir = File(outputBaseDir, dirName)
        sessionDir.mkdirs()

        try {
            // 1. 保存原片到 MediaStore
            Log.i(TAG, "保存 ID4 master...")
            val masterUri = saveToMediaStore("cam4_master_original.jpg", masterJpg, "image/jpeg")
            val masterFile = File(sessionDir, "cam4_master_original.jpg")
            masterFile.writeBytes(masterJpg)

            Log.i(TAG, "保存 ID2 aux...")
            val auxUri = saveToMediaStore("cam2_aux_original.jpg", auxJpg, "image/jpeg")
            val auxFile = File(sessionDir, "cam2_aux_original.jpg")
            auxFile.writeBytes(auxJpg)

            // 2. 配准
            Log.i(TAG, "配准 ID2 → ID4...")
            val regPipeline = DualCamRegistrationPipeline()
            val regResult = regPipeline.register(masterJpg, auxJpg)

            if (!regResult.success) {
                Log.w(TAG, "配准失败，回退 ID4: ${regResult.errorMessage}")
                return saveFallback(sessionDir, masterFile, auxFile, regResult.errorMessage, startTime)
            }

            // 3. 融合
            Log.i(TAG, "融合中...")
            val fusePipeline = DualCamFusionPipeline()
            val fuseResult = fusePipeline.fuse(masterJpg, auxJpg, regResult)

            if (!fuseResult.success) {
                Log.w(TAG, "融合失败，回退 ID4: ${fuseResult.errorMessage}")
                return saveFallback(sessionDir, masterFile, auxFile, fuseResult.errorMessage, startTime)
            }

            // 4. 保存融合产物
            val fusedFile = File(sessionDir, "fusion_result.jpg")
            if (fuseResult.fusedJpg != null) {
                fusedFile.writeBytes(fuseResult.fusedJpg)
                saveToMediaStore("fusion_result.jpg", fuseResult.fusedJpg, "image/jpeg")
            } else {
                fusedFile.writeBytes(masterJpg)
            }

            val maskFile: File?
            if (fuseResult.maskJpg != null) {
                maskFile = File(sessionDir, "fusion_mask.jpg")
                maskFile.writeBytes(fuseResult.maskJpg)
                saveToMediaStore("fusion_mask.jpg", fuseResult.maskJpg, "image/jpeg")
            } else {
                maskFile = null
            }

            // 5. 写入元数据 JSON
            val jsonFile = File(sessionDir, "capture_pair.json")
            val meta = buildMetadata(
                sessionDir.name, masterJpg.size, auxJpg.size,
                fusedFile.length(), maskFile?.length() ?: 0,
                regResult, fuseResult, startTime
            )
            jsonFile.writeText(meta.toString(2))
            saveToMediaStore("capture_pair.json", meta.toString(2).toByteArray(), "application/json")

            val elapsed = System.currentTimeMillis() - startTime
            Log.i(TAG, "双摄融合完成: ${elapsed}ms → ${sessionDir.absolutePath}")

            return CaptureSessionOutput(
                success = true,
                outputDir = sessionDir,
                masterFile = masterFile,
                auxFile = auxFile,
                fusedFile = fusedFile,
                maskFile = maskFile,
                jsonFile = jsonFile
            )
        } catch (e: Exception) {
            Log.e(TAG, "处理异常", e)
            val masterFile = File(sessionDir, "cam4_master_original.jpg")
            if (!masterFile.exists()) masterFile.writeBytes(masterJpg)
            return CaptureSessionOutput(
                success = false,
                outputDir = sessionDir,
                masterFile = if (masterFile.exists()) masterFile else null,
                errorMessage = "处理异常: ${e.message}"
            )
        }
    }

    /** 用 MediaStore API 保存文件到 Pictures/Stage27/ */
    private fun saveToMediaStore(fileName: String, data: ByteArray, mimeType: String): Uri? {
        return try {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, mimeType)
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/Stage27")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
            }
            val uri = context.contentResolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
            )
            if (uri != null) {
                context.contentResolver.openOutputStream(uri)?.use { os ->
                    os.write(data)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    values.clear()
                    values.put(MediaStore.Images.Media.IS_PENDING, 0)
                    context.contentResolver.update(uri, values, null, null)
                }
            }
            uri
        } catch (e: Exception) {
            Log.e(TAG, "MediaStore 保存失败: ${e.message}")
            null
        }
    }

    /**
     * 配准/融合失败时安全回退输出 ID4
     */
    private fun saveFallback(
        sessionDir: File,
        masterFile: File,
        auxFile: File,
        errorMsg: String,
        startTime: Long
    ): CaptureSessionOutput {
        // 融合结果 = ID4 原片
        val fusedFile = File(sessionDir, "fusion_result.jpg")
        fusedFile.writeBytes(masterFile.readBytes())

        val jsonFile = File(sessionDir, "capture_pair.json")
        val meta = JSONObject().apply {
            put("sessionId", sessionDir.name)
            put("status", "fallback")
            put("reason", errorMsg)
            put("masterFile", masterFile.name)
            put("auxFile", auxFile.name)
            put("fusedFile", fusedFile.name)
            put("elapsedMs", System.currentTimeMillis() - startTime)
        }
        jsonFile.writeText(meta.toString(2))

        Log.w(TAG, "安全回退: ${errorMsg}")
        return CaptureSessionOutput(
            success = false,
            outputDir = sessionDir,
            masterFile = masterFile,
            auxFile = auxFile,
            fusedFile = fusedFile,
            jsonFile = jsonFile,
            errorMessage = errorMsg
        )
    }

    /**
     * 构建配准-融合完整元数据
     */
    private fun buildMetadata(
        sessionId: String,
        masterSize: Int,
        auxSize: Int,
        fusedSize: Long,
        maskSize: Long,
        regResult: DualCamRegistrationPipeline.RegistrationResult,
        fuseResult: DualCamFusionPipeline.FusionOutput,
        startTime: Long
    ): JSONObject {
        return JSONObject().apply {
            put("sessionId", sessionId)
            put("timestamp", SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)
                .format(Date()))
            put("stage", "27")
            put("status", if (fuseResult.success) "success" else "fallback")

            put("files", JSONObject().apply {
                put("master", "cam4_master_original.jpg")
                put("aux", "cam2_aux_original.jpg")
                put("fused", "fusion_result.jpg")
                put("mask", "fusion_mask.jpg")
                put("metadata", "capture_pair.json")
            })

            put("fileSizes", JSONObject().apply {
                put("masterBytes", masterSize)
                put("auxBytes", auxSize)
                put("fusedBytes", fusedSize)
                put("maskBytes", maskSize)
            })

            put("registration", JSONObject().apply {
                put("success", regResult.success)
                put("score", regResult.score.toDouble())
                put("opticalScale", regResult.usedScale.toDouble())
                put("rotationDeg", regResult.usedRotation.toDouble())
                put("error", regResult.errorMessage)
            })

            put("fusion", JSONObject().apply {
                put("success", fuseResult.success)
                put("error", fuseResult.errorMessage)
            })

            put("performance", JSONObject().apply {
                put("elapsedMs", System.currentTimeMillis() - startTime)
                put("targetMs", "1000-3000")
            })

            put("config", JSONObject().apply {
                put("masterCamId", "4")
                put("auxCamId", "2")
                put("outputWidth", -1)  // 实际融合尺寸同 ID4
                put("outputHeight", -1)
            })
        }
    }
}
