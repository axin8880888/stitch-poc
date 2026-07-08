package com.teleboost.camera.stitch.core

import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.TotalCaptureResult
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/**
 * 采集锁定控制器。
 *
 * 职责：
 * 1. 等待 AE/AWB 收敛（起手 0.5-1 秒，连续 N 帧稳定）
 * 2. 施加 AE_LOCK + AWB_LOCK
 * 3. 持续校验后续帧的曝光一致性
 * 4. 释放锁定
 *
 * 符合光边界白皮书：
 * - 使用 AE_LOCK，不用 AE_MODE=OFF
 * - 使用 AWB_LOCK
 * - 不干扰 CameraEngine 主链
 */
class LockController(
    private val policy: CapturePolicy = CapturePolicy.STITCH_DEFAULT
) {
    companion object {
        private const val TAG = "LockController"
    }

    /** 锁定状态 */
    enum class State {
        /** 未开始 */
        IDLE,
        /** 等待收敛 */
        CONVERGING,
        /** 已锁定 */
        LOCKED,
        /** 锁定失败 */
        FAILED,
        /** 已释放 */
        RELEASED
    }

    private val _state = AtomicReference(State.IDLE)
    val state: State get() = _state.get()

    /** 收敛计数器 */
    private var stableFrameCount = 0

    /** 上一帧 CaptureResult（用于曝光一致性比较） */
    private var previousResult: CaptureResult? = null

    /** 监听器 */
    private var onStateChange: ((State) -> Unit)? = null
    private var onExposureDrift: ((String) -> Unit)? = null

    // 内部 handler 用于超时/延迟
    private var handlerThread: HandlerThread? = null
    private var handler: Handler? = null

    /**
     * 开始锁定流程。
     * 1. 先施放常规参数（降噪关、边缘关等）
     * 2. 启动收敛等待
     * 3. 收敛完成后施放 AE_LOCK + AWB_LOCK
     *
     * @param session CameraCaptureSession，用于发送重复请求
     * @param templateRequest 基础 CaptureRequest.Builder（已设好目标 surface）
     */
    fun startLocking(
        session: CameraCaptureSession,
        templateRequest: CaptureRequest.Builder,
        onComplete: (Boolean) -> Unit
    ) {
        if (_state.get() != State.IDLE) {
            Log.w(TAG, "startLocking called but state is ${_state.get()}")
            return
        }

        _state.set(State.CONVERGING)
        onStateChange?.invoke(State.CONVERGING)
        Log.d(TAG, "开始收敛等待 (${policy.convergenceWaitMs}ms, ${policy.stableFrameCount}帧)")

        // 应用基础参数
        policy.applyTo(templateRequest)

        // 启动后台线程处理超时
        startHandlerThread()

        // 设置收敛超时（最大等待时间的 2 倍，防止死等）
        val maxWaitMs = policy.convergenceWaitMs * 2
        handler?.postDelayed({
            if (_state.get() == State.CONVERGING) {
                Log.w(TAG, "收敛超时 (${maxWaitMs}ms)，强制锁定")
                forceLock(session, templateRequest)
                onComplete(true)
            }
        }, maxWaitMs)

        // 开始发送带回调的重复请求
        sendConvergeRequest(session, templateRequest, onComplete)
    }

    /**
     * 对一帧 CaptureResult 做收敛检测。
     * 每帧调用一次，由外部（FrameCollector 的 callback）传入。
     *
     * @return true 表示仍在收敛中，false 表示已完成/出错
     */
    fun onCaptureResult(
        session: CameraCaptureSession,
        templateRequest: CaptureRequest.Builder,
        result: TotalCaptureResult,
        onComplete: (Boolean) -> Unit
    ): Boolean {
        if (_state.get() != State.CONVERGING) return false

        val validation = policy.validateResult(result, previousResult)
        previousResult = result

        if (validation.isStable) {
            stableFrameCount++
            Log.d(TAG, "稳定帧 #$stableFrameCount: ${validation.message}")
            if (stableFrameCount >= policy.stableFrameCount) {
                // 收敛完成，施放锁定
                Log.d(TAG, "收敛完成，施放 AE_LOCK + AWB_LOCK")
                forceLock(session, templateRequest)
                onComplete(true)
                return false
            }
        } else {
            // 还没稳定，重置计数
            if (stableFrameCount > 0) {
                Log.d(TAG, "稳定中断: ${validation.message}")
            }
            stableFrameCount = 0
        }

        // 继续发送重复请求
        sendConvergeRequest(session, templateRequest, onComplete)
        return true
    }

    /**
     * 强制施加锁定（不等收敛完成时强制设置 AE_LOCK）。
     */
    fun forceLock(session: CameraCaptureSession, templateRequest: CaptureRequest.Builder) {
        val oldState = _state.getAndSet(State.LOCKED)
        if (oldState == State.LOCKED || oldState == State.RELEASED) return

        policy.applyLocking(templateRequest)
        sendLockedRequest(session, templateRequest)

        onStateChange?.invoke(State.LOCKED)
        Log.d(TAG, "AE_LOCK + AWB_LOCK 已施加")
    }

    /**
     * 释放锁定（恢复自动曝光/白平衡）。
     */
    fun releaseLock(session: CameraCaptureSession, templateRequest: CaptureRequest.Builder) {
        val oldState = _state.getAndSet(State.RELEASED)
        if (oldState == State.RELEASED) return

        templateRequest.set(CaptureRequest.CONTROL_AE_LOCK, false)
        templateRequest.set(CaptureRequest.CONTROL_AWB_LOCK, false)
        sendLockedRequest(session, templateRequest)

        stopHandlerThread()
        onStateChange?.invoke(State.RELEASED)
        Log.d(TAG, "锁定已释放")
    }

    /**
     * 用于采集过程中的帧校验（锁定后每帧调用）。
     * 检查曝光/ISO/WB 是否漂移。
     */
    fun validateCapturedFrame(result: CaptureResult): Boolean {
        if (_state.get() != State.LOCKED) return true // 未锁定不校验

        val validation = policy.validateResult(result, previousResult)
        previousResult = result

        if (!validation.isStable) {
            Log.w(TAG, "采集过程曝光漂移: ${validation.message}")
            onExposureDrift?.invoke(validation.message)
        }
        return validation.isStable
    }

    /** 设置状态变化监听 */
    fun setOnStateChangeListener(listener: (State) -> Unit) {
        onStateChange = listener
    }

    /** 设置曝光漂移告警监听 */
    fun setOnExposureDriftListener(listener: (String) -> Unit) {
        onExposureDrift = listener
    }

    fun reset() {
        _state.set(State.IDLE)
        stableFrameCount = 0
        previousResult = null
        stopHandlerThread()
        Log.d(TAG, "LockController 已重置")
    }

    // --- 内部方法 ---

    private fun sendConvergeRequest(
        session: CameraCaptureSession,
        templateRequest: CaptureRequest.Builder,
        onComplete: (Boolean) -> Unit
    ) {
        try {
            val request = templateRequest.build()
            session.setRepeatingRequest(request, object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(
                    session: CameraCaptureSession,
                    request: CaptureRequest,
                    result: TotalCaptureResult
                ) {
                    super.onCaptureCompleted(session, request, result)
                    onCaptureResult(session, templateRequest, result, onComplete)
                }
            }, handler)
        } catch (e: Exception) {
            Log.e(TAG, "sendConvergeRequest 失败", e)
            _state.set(State.FAILED)
            onComplete(false)
        }
    }

    private fun sendLockedRequest(
        session: CameraCaptureSession,
        templateRequest: CaptureRequest.Builder
    ) {
        try {
            val request = templateRequest.build()
            session.setRepeatingRequest(request, null, handler)
        } catch (e: Exception) {
            Log.e(TAG, "sendLockedRequest 失败", e)
            _state.set(State.FAILED)
        }
    }

    private fun startHandlerThread() {
        if (handlerThread == null) {
            handlerThread = HandlerThread("LockController").apply { start() }
            handler = Handler(handlerThread!!.looper)
        }
    }

    private fun stopHandlerThread() {
        handler?.removeCallbacksAndMessages(null)
        handlerThread?.quitSafely()
        handlerThread = null
        handler = null
    }
}
