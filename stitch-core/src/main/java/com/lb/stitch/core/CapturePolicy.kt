package com.teleboost.camera.stitch.core

import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult

/**
 * 接片采集时的相机参数锁定策略。
 *
 * 红线约束（来自光边界白皮书）：
 * 1. 接片前让画面在中等亮度处收敛 0.5–1 秒
 * 2. 使用 AE_LOCK，不用 AE_MODE=OFF
 * 3. 使用 AWB_LOCK
 * 4. 不做多帧降噪、不做美颜、不做涂抹
 *
 * 本类负责生成「锁定态的 CaptureRequest builder 模板」，
 * 以及校验 CaptureResult 是否满足锁定一致性。
 */
data class CapturePolicy(
    /** 锁定 AE（自动曝光）：默认 true */
    val lockExposure: Boolean = true,

    /** 锁定 AWB（自动白平衡）：默认 true */
    val lockWhiteBalance: Boolean = true,

    /** 锁定 ISO：为 null 时不强制，为非 null 时将 ISO 固定为指定值 */
    val lockedIso: Int? = null,

    /** 降噪模式：默认 NOISE_REDUCTION_MODE_OFF */
    val noiseReductionMode: Int = CaptureRequest.NOISE_REDUCTION_MODE_OFF,

    /** 边缘增强模式：默认 EDGE_MODE_OFF */
    val edgeMode: Int = CaptureRequest.EDGE_MODE_OFF,

    /** 是否禁用多帧处理：默认 true */
    val disableMultiFrameProcessing: Boolean = true,

    /** 是否禁用 HDR：默认 true */
    val disableHdr: Boolean = true,

    /** 收敛等待时间（毫秒）：起手后等待 AE/AWB 稳定再开始采集 */
    val convergenceWaitMs: Long = 800L,

    /** 稳定阶段稳定帧数：连续 N 帧曝光一致后才认为收敛完成 */
    val stableFrameCount: Int = 3
) {
    companion object {
        /** 接片默认锁定策略，符合光边界红线 */
        val STITCH_DEFAULT = CapturePolicy()

        /** 最严格的锁定策略（测试用） */
        val STRICT_LOCK = CapturePolicy(
            lockExposure = true,
            lockWhiteBalance = true,
            lockedIso = 100,
            noiseReductionMode = CaptureRequest.NOISE_REDUCTION_MODE_OFF,
            edgeMode = CaptureRequest.EDGE_MODE_OFF
        )
    }

    /**
     * 将该策略应用到 CaptureRequest.Builder。
     */
    fun applyTo(builder: CaptureRequest.Builder) {
        // 降噪关
        builder.set(CaptureRequest.NOISE_REDUCTION_MODE, noiseReductionMode)
        // 边缘增强关
        builder.set(CaptureRequest.EDGE_MODE, edgeMode)
        // 禁用多帧处理
        if (disableMultiFrameProcessing) {
            builder.set(CaptureRequest.CONTROL_ENABLE_ZSL, false)
        }
        // 禁用 HDR
        if (disableHdr) {
            builder.set(CaptureRequest.CONTROL_SCENE_MODE, CaptureRequest.CONTROL_SCENE_MODE_DISABLED)
            builder.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
        }
        // 锁定 ISO（如果指定）
        lockedIso?.let { builder.set(CaptureRequest.SENSOR_SENSITIVITY, it) }
    }

    /**
     * 在收敛阶段之后应用锁定。
     * AE_LOCK / AWB_LOCK 不能在起手时直接设，需等收敛后再锁。
     */
    fun applyLocking(builder: CaptureRequest.Builder) {
        if (lockExposure) {
            builder.set(CaptureRequest.CONTROL_AE_LOCK, true)
        }
        if (lockWhiteBalance) {
            builder.set(CaptureRequest.CONTROL_AWB_LOCK, true)
        }
    }

    /**
     * 校验 CaptureResult 是否满足锁定一致性。
     * 用于判断收敛是否完成，以及采集期间曝光是否漂移。
     */
    fun validateResult(result: CaptureResult, previous: CaptureResult?): ValidationResult {
        val aeLock = result.get(CaptureResult.CONTROL_AE_LOCK)
        val awbLock = result.get(CaptureResult.CONTROL_AWB_LOCK)
        val aeState = result.get(CaptureResult.CONTROL_AE_STATE)
        val sensitivity = result.get(CaptureResult.SENSOR_SENSITIVITY)
        val exposureTime = result.get(CaptureResult.SENSOR_EXPOSURE_TIME)

        if (lockExposure && (aeLock == null || !aeLock)) {
            return ValidationResult(false, "AE_LOCK not yet applied")
        }
        if (lockWhiteBalance && (awbLock == null || !awbLock)) {
            return ValidationResult(false, "AWB_LOCK not yet applied")
        }

        // 检查与前帧曝光一致性
        if (previous != null) {
            val prevSensitivity = previous.get(CaptureResult.SENSOR_SENSITIVITY)
            val prevExposureTime = previous.get(CaptureResult.SENSOR_EXPOSURE_TIME)
            if (sensitivity != null && prevSensitivity != null && sensitivity != prevSensitivity) {
                return ValidationResult(false, "ISO drifted: $prevSensitivity → $sensitivity")
            }
            if (exposureTime != null && prevExposureTime != null && exposureTime != prevExposureTime) {
                return ValidationResult(false, "exposure time drifted: $prevExposureTime → $exposureTime")
            }
        }

        // 检查收敛状态
        if (aeState == CaptureResult.CONTROL_AE_STATE_CONVERGED ||
            aeState == CaptureResult.CONTROL_AE_STATE_LOCKED
        ) {
            return ValidationResult(true, "stable")
        }

        return ValidationResult(false, "AE_STATE=$aeState, not yet converged")
    }

    data class ValidationResult(
        val isStable: Boolean,
        val message: String
    )
}
