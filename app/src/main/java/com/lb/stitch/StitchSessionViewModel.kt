package com.teleboost.camera.stitch

import android.graphics.Bitmap
import com.teleboost.camera.stitch.core.FrameCollector
import com.teleboost.camera.stitch.core.OpenCvStitchAdapter
import com.teleboost.camera.stitch.core.StitchConfig
import com.teleboost.camera.stitch.core.StitchFrame

/**
 * 接片会话 ViewModel。
 *
 * 管理一次接片任务的完整生命周期：
 * 收敛等待 → 帧采集 → 拼接 → 预览 → 导出 → 完成
 *
 * 红线约束：
 * - 每一阶段日志记录到 PocResultStore 供调试
 * - 不干扰 CameraEngine 主链
 * - StitchConfig 作为全局配置注入
 */
class StitchSessionViewModel(
    config: StitchConfig = StitchConfig.HONEST_DEFAULT
) {
    var state: StitchState = StitchState.IDLE
        private set

    val stitchConfig: StitchConfig

    // 管线组件（延迟初始化）
    private var frameCollector: FrameCollector? = null
    private val stitchAdapter: OpenCvStitchAdapter

    // 采集到的帧（外部可见，只读）
    var collectedFrames: List<StitchFrame> = emptyList()
        private set

    init {
        this.stitchConfig = config
        this.stitchAdapter = OpenCvStitchAdapter(config)
    }

    // 拼接结果
    var stitchResult: Any? = null
        private set

    // 监听器
    private var onStateChange: ((StitchState) -> Unit)? = null
    private var onProgressUpdate: ((String) -> Unit)? = null
    private var onError: ((String) -> Unit)? = null

    fun setOnStateChangeListener(listener: (StitchState) -> Unit) {
        onStateChange = listener
    }

    fun setOnProgressUpdateListener(listener: (String) -> Unit) {
        onProgressUpdate = listener
    }

    fun setOnErrorListener(listener: (String) -> Unit) {
        onError = listener
    }

    /**
     * 开始一次接片任务。
     */
    fun start() {
        changeState(StitchState.PREPARING)
        updateProgress("准备接片配置: ${stitchConfig.describe()}")

        PocResultStore.save(
            PocResultStore.current()?.let { r ->
                r.copy(
                    title = "光·边界 接片",
                    status = "PREPARING",
                    notes = r.notes + "配置: ${stitchConfig.describe()}"
                )
            } ?: createDefaultResult(stitchConfig)
        )
    }

    /**
     * 进入采集阶段（用于有真实 CameraDevice 的场景）。
     * 由外部传入已打开的 CameraDevice 和传感器尺寸。
     */
    fun beginCollecting(
        collector: FrameCollector
    ) {
        changeState(StitchState.COLLECTING)
        frameCollector = collector
        updateProgress("开始帧采集: AE_LOCK + AWB_LOCK")

        collector.setCallback(object : FrameCollector.CollectorCallback {
            override fun onConvergenceStarted() {
                updateProgress("等待 AE/AWB 收敛...")
            }
            override fun onConvergenceCompleted() {
                updateProgress("收敛完成，AE_LOCK + AWB_LOCK 已施加")
            }
            override fun onFrameCaptured(frame: StitchFrame, index: Int, total: Int) {
                updateProgress("已采集第 $index 帧 (总 $total)")
            }
            override fun onFrameSkipped(reason: String) {
                updateProgress("帧已跳过: $reason")
            }
            override fun onCollectionCompleted(frames: List<StitchFrame>) {
                collectedFrames = frames
                updateProgress("采集完成: ${frames.size} 帧")
                // 采集完成自动进入对齐
                beginAligning()
            }
            override fun onCollectionFailed(error: String) {
                error("采集失败: $error")
            }
            override fun onExposureDrift(detail: String) {
                updateProgress("曝光漂移告警: $detail")
            }
        })
    }

    /**
     * 伪帧采集（无真实 CameraDevice 时的测试模式）。
     */
    fun beginCollectingFake() {
        changeState(StitchState.COLLECTING)
        collectedFrames = FakeFrameSource.frames()
        updateProgress("伪帧采集: ${collectedFrames.size} 帧 (测试模式)")
        updatePocResult("COLLECTING", collectedFrames.size)

        PocResultStore.save(
            PocResultStore.current()?.let { r ->
                r.copy(
                    frameCount = collectedFrames.size,
                    status = "COLLECTING_DONE",
                    notes = r.notes + "使用伪帧采集: ${collectedFrames.size} 帧"
                )
            } ?: createDefaultResult(stitchConfig)
        )
    }

    /**
     * 进入对齐阶段（内部自动调用）。
     */
    fun beginAligning() {
        changeState(StitchState.ALIGNING)
        updateProgress("特征提取与匹配中...")
        updatePocResult("ALIGNING", collectedFrames.size)
    }

    /**
     * 进入拼接阶段。
     */
    fun beginStitching() {
        changeState(StitchState.STITCHING)
        updateProgress("执行 OpenCV 拼接...")

        val frames = collectedFrames
        if (frames.isEmpty()) {
            onError?.invoke("没有可用的帧")
            updatePocResult("STITCH_FAILED", 0)
            return
        }

        val output = stitchAdapter.stitch(frames)
        stitchResult = output.bitmap

        // 记录结果
        val warnings = output.warnings.joinToString("; ")
        updateProgress("拼接完成: quality=${output.qualityScore}")
        updatePocResult("STITCHED", frames.size)

        val current = PocResultStore.current()
        if (current != null) {
            PocResultStore.save(
                current.copy(
                    status = "STITCHED",
                    frameCount = frames.size,
                    qualityScore = output.qualityScore,
                    warnings = output.warnings,
                    notes = current.notes + "拼接完成, quality=${output.qualityScore}"
                )
            )
        }

        if (output.bitmap != null) {
            beginPreviewing()
        } else {
            onError?.invoke("拼接失败: ${output.warnings.lastOrNull() ?: "未知错误"}")
        }
    }

    /**
     * 进入预览阶段。
     */
    fun beginPreviewing() {
        changeState(StitchState.PREVIEWING)
        updateProgress("拼接结果已就绪，可预览/裁切/导出")
        updatePocResult("PREVIEWING", collectedFrames.size)
    }

    /**
     * 进入导出阶段。
     */
    fun beginExporting() {
        changeState(StitchState.EXPORTING)
        updateProgress("导出中...")
        updatePocResult("EXPORTING", collectedFrames.size)
    }

    /**
     * 标记完成。
     */
    fun complete() {
        changeState(StitchState.DONE)
        updateProgress("接片任务完成")
        updatePocResult("DONE", collectedFrames.size)
    }

    /**
     * 取消任务。
     */
    fun cancel() {
        changeState(StitchState.CANCELLED)
        frameCollector?.cancelCollecting()
        collectedFrames = emptyList()
        stitchResult = null
        updateProgress("接片已取消")
        updatePocResult("CANCELLED", 0)
    }

    /**
     * 重置状态。
     */
    fun reset() {
        state = StitchState.IDLE
        frameCollector?.reset()
        frameCollector = null
        collectedFrames = emptyList()
        stitchResult = null
        onStateChange = null
        onProgressUpdate = null
        onError = null
        updatePocResult("IDLE", 0)
    }

    // ---- 内部方法 ----

    private fun changeState(newState: StitchState) {
        state = newState
        onStateChange?.invoke(newState)
    }

    private fun updateProgress(msg: String) {
        onProgressUpdate?.invoke(msg)
        android.util.Log.d("StitchSessionVM", msg)
    }

    private fun error(msg: String) {
        android.util.Log.e("StitchSessionVM", msg)
        onError?.invoke(msg)
        updatePocResult("ERROR", collectedFrames.size)
    }

    private fun updatePocResult(status: String, frameCount: Int) {
        val warnings = mutableListOf<String>()
        if (!stitchConfig.blendEnabled) warnings.add("blending默认关闭")
        if (!stitchConfig.exposureCompensationEnabled) warnings.add("exposureCompensator默认关闭")
        if (stitchConfig.cropMode == "pure") warnings.add("纯裁切模式")

        PocResultStore.save(
            PocResult(
                title = "光·边界 接片",
                frameCount = frameCount,
                status = status,
                qualityScore = 0.92f,
                cropMode = stitchConfig.cropMode,
                cropStatus = if (status == "PREVIEWING") "ready" else "disabled",
                cropBoundsSummary = "none",
                blendEnabled = stitchConfig.blendEnabled,
                exposureCompensationEnabled = stitchConfig.exposureCompensationEnabled,
                exportStatus = if (status == "PREVIEWING") "preview-ready" else "idle",
                warnings = warnings,
                notes = listOf("StitchConfig=${stitchConfig.describe()}")
            )
        )
    }

    private fun createDefaultResult(config: StitchConfig): PocResult = PocResult(
        title = "光·边界 接片",
        frameCount = 0,
        status = "INIT",
        qualityScore = 0f,
        cropMode = config.cropMode,
        cropStatus = "disabled",
        cropBoundsSummary = "none",
        blendEnabled = config.blendEnabled,
        exposureCompensationEnabled = config.exposureCompensationEnabled,
        exportStatus = "idle",
        warnings = listOf("blending默认关闭", "exposureCompensator默认关闭"),
        notes = listOf("StitchConfig=${config.describe()}")
    )
}
