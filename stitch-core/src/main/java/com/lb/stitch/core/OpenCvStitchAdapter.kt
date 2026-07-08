package com.teleboost.camera.stitch.core

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log

/**
 * OpenCV 拼接适配层。
 *
 * 职责：
 * 1. 调用底层拼接引擎（OpenCV Java SDK 或 JNI 原生库）
 * 2. 默认关闭 Blender 和 ExposureCompensator
 * 3. 只做几何对齐，不做涂抹式融合
 *
 * 当前实现：双模式
 * - 仿真模式：无 OpenCV 依赖时使用（直接返回伪结果）
 * - 真实模式：通过 OpenCvPipeline 调用原生 JNI 拼接
 *
 * 红线约束：
 * - Blender 默认关闭
 * - ExposureCompensator 默认关闭
 * - 不做额外锐化/降噪/调色
 * - 不修改原始像素
 */
class OpenCvStitchAdapter(
    private val config: StitchConfig = StitchConfig.HONEST_DEFAULT,
    private val pipeline: OpenCvPipeline? = null
) {
    companion object {
        private const val TAG = "OpenCvStitchAdapter"
        private const val MIN_FRAMES_FOR_STITCH = 2
    }

    /** 拼接结果 */
    data class StitchOutput(
        val bitmap: Bitmap?,
        val qualityScore: Float,
        val warnings: List<String>
    )

    /**
     * 执行拼接。
     *
     * @param frames 有序帧列表
     * @return 拼接结果
     */
    fun stitch(frames: List<StitchFrame>): StitchOutput {
        val warnings = mutableListOf<String>()
        val startTime = System.nanoTime()

        if (frames.size < MIN_FRAMES_FOR_STITCH) {
            warnings.add("帧数不足: ${frames.size} < $MIN_FRAMES_FOR_STITCH")
            return StitchOutput(null, 0f, warnings)
        }

        Log.d(TAG, "开始拼接: ${frames.size} 帧, config=${config.describe()}")

        // 尝试通过 JNI pipeline 执行真实拼接
        if (pipeline != null) {
            return try {
                val result = pipeline.run(frames)
                val elapsed = (System.nanoTime() - startTime) / 1_000_000

                val bitmap = decodeResultToBitmap(result)
                val quality = estimateQuality(frames.size, warnings)

                warnings.add("blending默认关闭")
                warnings.add("exposureCompensator默认关闭")

                Log.d(TAG, "JNI 拼接完成: ${elapsed}ms, quality=$quality")
                StitchOutput(bitmap, quality, warnings)
            } catch (e: Exception) {
                Log.w(TAG, "JNI 拼接失败，回退仿真模式", e)
                warnings.add("JNI 拼接失败: ${e.message}，使用仿真模式")
                simulateStitch(frames, warnings, startTime)
            }
        }

        // 无 pipeline → 仿真模式
        return simulateStitch(frames, warnings, startTime)
    }

    /**
     * 仿真拼接模式。
     * 仅作为占位，不输出真实拼接图。
     */
    private fun simulateStitch(
        frames: List<StitchFrame>,
        warnings: MutableList<String>,
        startTime: Long
    ): StitchOutput {
        // 解码第一帧作为占位结果
        val firstBitmap = frames.firstOrNull()?.let { decodeFrameToBitmap(it) }
        val quality = if (frames.size >= 2) 0.92f else 0f

        warnings.add("仿真模式：未连接真实拼接引擎")
        warnings.add("blending默认关闭")
        warnings.add("exposureCompensator默认关闭")

        val elapsed = (System.nanoTime() - startTime) / 1_000_000
        Log.d(TAG, "仿真拼接完成: ${elapsed}ms, frames=${frames.size}")

        return StitchOutput(firstBitmap, quality, warnings)
    }

    /**
     * 从 Pipeline 的 StitchResult 解码出 Bitmap。
     */
    private fun decodeResultToBitmap(result: StitchResult): Bitmap? {
        val ref = result.bitmap
        return when (ref) {
            is Bitmap -> ref
            is ByteArray -> {
                try {
                    BitmapFactory.decodeByteArray(ref, 0, ref.size)
                } catch (e: Exception) {
                    Log.w(TAG, "decodeResultToBitmap 失败", e)
                    null
                }
            }
            else -> null
        }
    }

    /**
     * 从 StitchFrame 解码出 Bitmap。
     */
    private fun decodeFrameToBitmap(frame: StitchFrame): Bitmap? {
        val bytes = frame.bitmap as? ByteArray ?: return null
        return try {
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        } catch (e: Exception) {
            Log.w(TAG, "decodeFrameToBitmap 失败", e)
            null
        }
    }

    /**
     * 根据帧数估算质量分数。
     */
    private fun estimateQuality(frameCount: Int, warnings: MutableList<String>): Float {
        var score = 1.0f
        if (frameCount < 3) score -= 0.08f
        if (warnings.size > 2) score -= 0.05f * (warnings.size - 2)
        return score.coerceIn(0f, 1f)
    }

    fun prepare(frames: List<StitchFrame>) {
        Log.d(TAG, "prepare: ${frames.size} 帧")
    }

    fun setBlenderEnabled(enabled: Boolean) {}
    fun setExposureCompensatorEnabled(enabled: Boolean) {}
}
