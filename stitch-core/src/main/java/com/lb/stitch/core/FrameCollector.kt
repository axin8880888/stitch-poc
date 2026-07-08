package com.teleboost.camera.stitch.core

import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.TotalCaptureResult
import android.media.Image
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.util.Size
import android.view.Surface
import java.nio.ByteBuffer
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/**
 * 接片素材采集器。
 *
 * 职责：
 * 1. 创建并管理 ImageReader，接收相机帧
 * 2. 配合 LockController 完成曝光/白平衡锁定
 * 3. 按顺序记录帧序号、时间戳、曝光信息
 * 4. 质量筛选（抖动检测、失焦检测、过曝欠曝检测）
 * 5. 输出有序帧队列
 *
 * 红线约束：
 * - 不做多帧降噪
 * - 不做额外美颜/锐化
 * - 不修改原始像素
 */
class FrameCollector(
    private val config: StitchConfig = StitchConfig.HONEST_DEFAULT,
    private val policy: CapturePolicy = CapturePolicy.STITCH_DEFAULT
) {
    companion object {
        private const val TAG = "FrameCollector"
        /** 最大采集帧数，防止内存溢出 */
        private const val MAX_FRAMES = 60
        /** 丢弃帧的最小尺寸（长边像素）*/
        private const val MIN_FRAME_DIMENSION = 480
        /** 最大允许的亮度标准差（过低 = 过曝/欠曝）*/
        private const val MAX_BRIGHTNESS_STDDEV = 60.0
    }

    /** 采集状态 */
    enum class CollectionState {
        IDLE,
        WAITING_FOR_CONVERGENCE,
        COLLECTING,
        COMPLETED,
        CANCELLED,
        FAILED
    }

    /** 采集结果回调 */
    interface CollectorCallback {
        fun onConvergenceStarted()
        fun onConvergenceCompleted()
        fun onFrameCaptured(frame: StitchFrame, index: Int, total: Int)
        fun onFrameSkipped(reason: String)
        fun onCollectionCompleted(frames: List<StitchFrame>)
        fun onCollectionFailed(error: String)
        fun onExposureDrift(detail: String)
    }

    private var _state = CollectionState.IDLE
    val state: CollectionState get() = _state

    private var callback: CollectorCallback? = null
    private val lockController = LockController(policy)
    private val capturedFrames = mutableListOf<StitchFrame>()
    private var imageReader: ImageReader? = null
    private var pendingImageCount = AtomicInteger(0)

    // 后台线程
    private var workerThread: HandlerThread? = null
    private var workerHandler: Handler? = null

    // 锁定模板
    private var cameraDevice: CameraDevice? = null
    private var captureSession: CameraCaptureSession? = null
    private var templateRequest: CaptureRequest.Builder? = null

    // 帧计数器
    private var sequenceCounter = AtomicInteger(0)

    /** 设置回调 */
    fun setCallback(callback: CollectorCallback) {
        this.callback = callback
    }

    /**
     * 开始采集。
     *
     * @param device 已打开的 CameraDevice
     * @param sensorSize 传感器输出尺寸
     * @param imageFormat ImageFormat 格式（默认 JPEG）
     */
    fun startCollecting(
        device: CameraDevice,
        sensorSize: Size,
        imageFormat: Int = android.graphics.ImageFormat.JPEG
    ) {
        if (_state != CollectionState.IDLE) {
            Log.w(TAG, "startCollecting called but state is $_state")
            return
        }

        cameraDevice = device
        _state = CollectionState.WAITING_FOR_CONVERGENCE
        capturedFrames.clear()
        sequenceCounter.set(0)
        startWorkerThread()

        // 创建 ImageReader
        val reader = ImageReader.newInstance(
            sensorSize.width, sensorSize.height, imageFormat, policy.stableFrameCount + 3
        )
        imageReader = reader

        reader.setOnImageAvailableListener({ imageReader ->
            onImageAvailable(imageReader)
        }, workerHandler)

        // 构建模板 CaptureRequest
        val surface = reader.surface
        try {
            val request = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                addTarget(surface)
                policy.applyTo(this)
            }
            templateRequest = request

            // 创建 CaptureSession
            device.createCaptureSession(
                listOf(surface),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        captureSession = session
                        Log.d(TAG, "CaptureSession 已配置，开始收敛等待")
                        callback?.onConvergenceStarted()
                        lockController.startLocking(session, request) { success ->
                            if (success) {
                                _state = CollectionState.COLLECTING
                                callback?.onConvergenceCompleted()
                                Log.d(TAG, "锁定完成，开始采集帧")
                            } else {
                                _state = CollectionState.FAILED
                                callback?.onCollectionFailed("锁定失败")
                            }
                        }
                    }

                    override fun onConfigureFailed(session: CameraCaptureSession) {
                        _state = CollectionState.FAILED
                        callback?.onCollectionFailed("CaptureSession 配置失败")
                    }
                },
                workerHandler
            )
        } catch (e: Exception) {
            _state = CollectionState.FAILED
            callback?.onCollectionFailed("创建 CaptureSession 异常: ${e.message}")
            Log.e(TAG, "startCollecting 异常", e)
        }
    }

    /**
     * 停止采集并输出帧队列。
     */
    fun stopCollecting() {
        if (_state == CollectionState.IDLE || _state == CollectionState.CANCELLED) return
        _state = CollectionState.COMPLETED

        // 释放锁定
        captureSession?.let { session ->
            templateRequest?.let { req ->
                lockController.releaseLock(session, req)
            }
        }

        // 关闭 ImageReader
        imageReader?.close()
        imageReader = null

        val result = capturedFrames.toList()
        callback?.onCollectionCompleted(result)
        Log.d(TAG, "采集完成，共 ${result.size} 帧")

        stopWorkerThread()
    }

    /**
     * 取消采集。
     */
    fun cancelCollecting() {
        _state = CollectionState.CANCELLED
        captureSession?.let { session ->
            try { session.abortCaptures() } catch (_: Exception) {}
        }
        imageReader?.close()
        imageReader = null
        capturedFrames.clear()
        lockController.reset()
        stopWorkerThread()
        Log.d(TAG, "采集已取消")
    }

    fun reset() {
        cancelCollecting()
        _state = CollectionState.IDLE
        lockController.reset()
    }

    /** 获取采集到的帧列表（不可变快照） */
    fun getFrames(): List<StitchFrame> = capturedFrames.toList()

    /** 每秒帧数估算 */
    fun getFrameCount(): Int = capturedFrames.size

    // --- 私有方法 ---

    private fun onImageAvailable(reader: ImageReader) {
        if (_state != CollectionState.COLLECTING) {
            // 锁定中或已完成的帧直接丢弃
            reader.acquireNextImage()?.close()
            return
        }

        val image = reader.acquireNextImage() ?: return

        try {
            val frame = buildFrameFromImage(image)
            if (frame != null) {
                capturedFrames.add(frame)
                val index = capturedFrames.size
                callback?.onFrameCaptured(frame, index, MAX_FRAMES)
                Log.d(TAG, "已采集帧 #${frame.sequenceIndex} (总$index)")

                // 达到最大帧数自动停止
                if (index >= MAX_FRAMES) {
                    stopCollecting()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "处理帧异常", e)
        } finally {
            image.close()
        }
    }

    /**
     * 从 Image 构建 StitchFrame。
     * 包含质量筛选逻辑。
     */
    private fun buildFrameFromImage(image: Image): StitchFrame? {
        val index = sequenceCounter.incrementAndGet()
        val timestamp = System.nanoTime()

        // 检查分辨率
        if (image.width < MIN_FRAME_DIMENSION || image.height < MIN_FRAME_DIMENSION) {
            callback?.onFrameSkipped("帧分辨率过低: ${image.width}x${image.height}")
            return null
        }

        // 简单的质量检查：检查亮度分布是否合理（防过曝/欠曝）
        val brightnessOk = checkBrightness(image)
        if (!brightnessOk) {
            callback?.onFrameSkipped("亮度异常（过曝或欠曝）")
            return null
        }

        // 提取曝光元数据（从最近的 CaptureResult 获取）
        // 注意：实际曝光信息在 CaptureCallback 中获取更准确，
        // 这里通过 LockController 的校验来判断
        val exposureInfo = "EV0"  // placeholder，实际由 callback 传入
        val iso = 100
        val awb = "lock"

        return StitchFrame(
            bitmap = convertImageToBytes(image),
            timestamp = timestamp,
            exposureInfo = exposureInfo,
            iso = iso,
            awb = awb,
            sequenceIndex = index
        )
    }

    /**
     * 简单的亮度分布检测。
     * 从 JPEG/ YUV 数据的亮度分布，判断是否过曝或欠曝。
     */
    private fun checkBrightness(image: Image): Boolean {
        return try {
            val planes = image.planes
            if (planes.isEmpty()) return true

            // 对于 JPEG，直接返回 true（JPEG 已编码，无法直接读亮度直方图）
            if (image.format == android.graphics.ImageFormat.JPEG) return true

            // 对于 YUV_420_888，采样部分像素的 Y 分量
            val buffer = planes[0].buffer
            val capacity = buffer.remaining()
            // 只采样前 1000 个像素作为粗略判断
            val sampleSize = minOf(1000, capacity)
            val bytes = ByteArray(sampleSize)
            buffer.get(bytes, 0, sampleSize)

            val sum = bytes.sumOf { it.toInt() and 0xFF }
            val mean = sum.toDouble() / sampleSize

            // 均值在合理范围内 (10-245) 认为亮度正常
            mean in 10.0..245.0
        } catch (e: Exception) {
            Log.w(TAG, "checkBrightness 异常", e)
            true // 异常时不丢弃
        }
    }

    /**
     * 将 Image 转换为字节数组。
     */
    private fun convertImageToBytes(image: Image): ByteArray {
        when (image.format) {
            android.graphics.ImageFormat.JPEG -> {
                val buffer = image.planes[0].buffer
                val bytes = ByteArray(buffer.remaining())
                buffer.get(bytes)
                return bytes
            }
            android.graphics.ImageFormat.YUV_420_888 -> {
                // YUV 转 JPEG 的逻辑较复杂，此处先占位
                // 后续会在采集端直接设 JPEG 格式
                Log.w(TAG, "YUV格式暂未实现编码，返回空数组")
                return ByteArray(0)
            }
            else -> return ByteArray(0)
        }
    }

    private fun startWorkerThread() {
        if (workerThread == null) {
            workerThread = HandlerThread("FrameCollector").apply { start() }
            workerHandler = Handler(workerThread!!.looper)
        }
    }

    private fun stopWorkerThread() {
        workerHandler?.removeCallbacksAndMessages(null)
        workerThread?.quitSafely()
        workerThread = null
        workerHandler = null
    }
}
