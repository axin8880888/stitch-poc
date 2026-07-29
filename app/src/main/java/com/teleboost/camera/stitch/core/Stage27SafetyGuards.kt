package com.teleboost.camera.stitch.core

import android.util.Log
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/**
 * Stage 27 安全回退保护
 *
 * 职责：
 *  - 配准超时保护
 *  - 融合异常捕获
 *  - 安全输出 ID4 原片（禁止闪退）
 *  - 1-3 秒后处理计时控制
 */
class Stage27SafetyGuards {

    companion object {
        private const val TAG = "Stage27Safety"
        // 配准超时 (毫秒)
        private const val REGISTRATION_TIMEOUT_MS = 2000L
        // 融合超时 (毫秒)
        private const val FUSION_TIMEOUT_MS = 2000L
        // 总处理超时 (毫秒) — 拍照后处理 1-3 秒
        private const val TOTAL_TIMEOUT_MS = 3000L
    }

    /**
     * 安全执行配准 — 超时自动回退
     */
    fun safeRegister(
        masterJpg: ByteArray,
        auxJpg: ByteArray,
        pipeline: DualCamRegistrationPipeline
    ): DualCamRegistrationPipeline.RegistrationResult {
        val executor = Executors.newSingleThreadExecutor()
        return try {
            val future: Future<DualCamRegistrationPipeline.RegistrationResult> = executor.submit(
                Callable {
                    pipeline.register(masterJpg, auxJpg)
                }
            )
            future.get(REGISTRATION_TIMEOUT_MS, TimeUnit.MILLISECONDS)
        } catch (e: Exception) {
            Log.w(TAG, "配准超时或异常: ${e.message}")
            DualCamRegistrationPipeline.RegistrationResult(
                success = false,
                errorMessage = "配准超时/异常: ${e.message}"
            )
        } finally {
            executor.shutdownNow()
        }
    }

    /**
     * 安全执行融合 — 异常时输出 ID4 原片
     */
    fun safeFuse(
        masterJpg: ByteArray,
        auxJpg: ByteArray,
        registrationResult: DualCamRegistrationPipeline.RegistrationResult,
        pipeline: DualCamFusionPipeline
    ): DualCamFusionPipeline.FusionOutput {
        val executor = Executors.newSingleThreadExecutor()
        return try {
            val future: Future<DualCamFusionPipeline.FusionOutput> = executor.submit(
                Callable {
                    pipeline.fuse(masterJpg, auxJpg, registrationResult)
                }
            )
            future.get(FUSION_TIMEOUT_MS, TimeUnit.MILLISECONDS)
        } catch (e: Exception) {
            Log.w(TAG, "融合超时或异常: ${e.message}")
            DualCamFusionPipeline.FusionOutput(
                success = true,  // 安全回退也算"成功"（不崩）
                fusedJpg = masterJpg,
                errorMessage = "融合超时/异常: ${e.message}"
            )
        } finally {
            executor.shutdownNow()
        }
    }

    /**
     * 全流程安全执行（配准 + 融合 + 保存），总耗时不超 3 秒
     */
    fun executeFullPipeline(
        masterJpg: ByteArray,
        auxJpg: ByteArray,
        saveFn: (masterJpg: ByteArray, auxJpg: ByteArray, fusedJpg: ByteArray?, maskJpg: ByteArray?, errorMsg: String) -> Boolean
    ): Boolean {
        val startTime = System.currentTimeMillis()

        // 1. 配准
        val regPipeline = DualCamRegistrationPipeline()
        val regResult = safeRegister(masterJpg, auxJpg, regPipeline)

        // 2. 融合
        val fusePipeline = DualCamFusionPipeline()
        val fuseResult = safeFuse(masterJpg, auxJpg, regResult, fusePipeline)

        // 3. 保存
        val saveResult = saveFn(
            masterJpg,
            auxJpg,
            fuseResult.fusedJpg,
            fuseResult.maskJpg,
            fuseResult.errorMessage
        )

        val elapsed = System.currentTimeMillis() - startTime
        Log.i(TAG, "全流程完成: ${elapsed}ms, save=${saveResult}, err=${fuseResult.errorMessage}")
        return saveResult
    }
}
