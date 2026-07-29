package com.teleboost.camera.stitch.core

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.hardware.camera2.params.OutputConfiguration
import android.hardware.camera2.params.SessionConfiguration
import android.media.Image
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.view.Surface
import android.view.TextureView
import android.view.ViewGroup
import java.util.concurrent.Executors

/**
 * Stage 27 双摄桥接 — ID4 Master + ID2 Aux 同步 Capture
 *
 * 预览显示逻辑摄像头默认画面。
 * 拍照时同时输出 ID4 JPEG + ID2 JPEG。
 * 融合在后台线程执行。
 */
class Stage27CameraBridge(private val context: Context) {

    companion object {
        private const val TAG = "Stage27Bridge"
        val MASTER_CAM_ID = "4"
        val AUX_CAM_ID = "2"
        private const val JPEG_WIDTH = 4096
        private const val JPEG_HEIGHT = 3072
        // 至少 2 个 buffer 让 ImageReader 能排队
        private const val MAX_IMAGES = 2
    }

    private var cameraDevice: CameraDevice? = null
    private var cameraSession: CameraCaptureSession? = null
    private val handlerThread = HandlerThread("Stage27Bridge").apply { start() }
    private val handler = Handler(handlerThread.looper)
    private val executor = Executors.newSingleThreadExecutor()

    private var masterReader: ImageReader? = null
    private var auxReader: ImageReader? = null
    private var previewSurface: Surface? = null

    var onCaptureResult: ((masterJpg: ByteArray, auxJpg: ByteArray) -> Unit)? = null
    var onStatusUpdate: ((String) -> Unit)? = null
    var onError: ((String) -> Unit)? = null

    @Volatile
    var isCapturing: Boolean = false
        private set

    private var masterBytes: ByteArray? = null
    private var auxBytes: ByteArray? = null

    // ==================== 预览 ====================

    fun startPreview(container: ViewGroup) {
        val tv = TextureView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }

        tv.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(surface: SurfaceTexture, w: Int, h: Int) {
                previewSurface = Surface(surface)
                // 尝试用系统默认比例，不手动设 Matrix
                // 如果画面拉伸，用 TextureView 的 scaleType 修正
                openCamera()
            }
            override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, w: Int, h: Int) {
                previewSurface = Surface(surface)
            }
            override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean {
                previewSurface = null
                close()
                return true
            }
            override fun onSurfaceTextureUpdated(surface: SurfaceTexture) {}
        }
        container.addView(tv, 0)
    }

    fun stopPreview() { close() }

    // ==================== 双摄拍照 ====================

    fun capture() {
        if (isCapturing || cameraDevice == null) {
            onStatusUpdate?.invoke("相机未就绪")
            return
        }
        isCapturing = true
        masterBytes = null
        auxBytes = null

        onStatusUpdate?.invoke("双摄拍照中...")

        // 先注册监听器，再触发 capture
        // 两个 ImageReader 独立监听
        masterReader?.setOnImageAvailableListener(masterListener, handler)
        auxReader?.setOnImageAvailableListener(auxListener, handler)

        triggerCapture()
    }

    /** ID4 Master JPEG 回调 */
    private val masterListener = ImageReader.OnImageAvailableListener { reader ->
        val img: Image = reader.acquireLatestImage() ?: return@OnImageAvailableListener
        try {
            val buf = img.planes[0].buffer
            val bytes = ByteArray(buf.remaining()).also { buf.get(it) }
            masterBytes = bytes
            Log.i(TAG, "ID4 master 捕获: ${bytes.size / 1024}KB")
            // 立即关闭监听器，释放 buffer
            reader.setOnImageAvailableListener(null, null)
            tryFusion()
        } finally {
            img.close()
        }
    }

    /** ID2 Aux JPEG 回调 */
    private val auxListener = ImageReader.OnImageAvailableListener { reader ->
        val img: Image = reader.acquireLatestImage() ?: return@OnImageAvailableListener
        try {
            val buf = img.planes[0].buffer
            val bytes = ByteArray(buf.remaining()).also { buf.get(it) }
            auxBytes = bytes
            Log.i(TAG, "ID2 aux 捕获: ${bytes.size / 1024}KB")
            reader.setOnImageAvailableListener(null, null)
            tryFusion()
        } finally {
            img.close()
        }
    }

    private fun tryFusion() {
        val m = masterBytes
        val a = auxBytes
        if (m == null || a == null) return
        isCapturing = false
        onCaptureResult?.invoke(m, a)
    }

    // ==================== 内部 ====================

    private fun openCamera() {
        val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val logicalId = findLogicalCam(manager) ?: run {
            onError?.invoke("未找到逻辑摄像头")
            return
        }
        try {
            manager.openCamera(logicalId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    cameraDevice = camera
                    setupReaders()
                    startSession()
                    onStatusUpdate?.invoke("双摄已打开")
                }
                override fun onDisconnected(camera: CameraDevice) { camera.close(); cameraDevice = null }
                override fun onError(camera: CameraDevice, err: Int) {
                    camera.close(); cameraDevice = null
                    onError?.invoke("摄像头错误: $err")
                }
            }, handler)
        } catch (e: Exception) {
            onError?.invoke("打开摄像头失败: ${e.message}")
        }
    }

    private fun findLogicalCam(manager: CameraManager): String? {
        for (id in manager.cameraIdList) {
            try {
                val chars = manager.getCameraCharacteristics(id)
                if (chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK) {
                    val physical = chars.physicalCameraIds
                    if (physical?.contains(MASTER_CAM_ID) == true && physical.contains(AUX_CAM_ID)) {
                        return id
                    }
                }
            } catch (_: Exception) {}
        }
        return manager.cameraIdList.firstOrNull { id ->
            try { manager.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK }
            catch (_: Exception) { false }
        }
    }

    private fun setupReaders() {
        masterReader?.close()
        auxReader?.close()
        // MAX_IMAGES=2 确保 ImageReader 有足够缓冲
        masterReader = ImageReader.newInstance(JPEG_WIDTH, JPEG_HEIGHT, ImageFormat.JPEG, MAX_IMAGES)
        auxReader = ImageReader.newInstance(JPEG_WIDTH, JPEG_HEIGHT, ImageFormat.JPEG, MAX_IMAGES)
    }

    private fun startSession() {
        val camera = cameraDevice ?: return
        val st = previewSurface ?: return

        // 预览 Surface 绑定到 ID4 物理摄像头
        val previewConfig = OutputConfiguration(st).apply {
            setPhysicalCameraId(MASTER_CAM_ID)
        }

        val outputs = mutableListOf<OutputConfiguration>().apply {
            add(previewConfig)
            masterReader?.let { add(OutputConfiguration(it.surface).apply { setPhysicalCameraId(MASTER_CAM_ID) }) }
            auxReader?.let { add(OutputConfiguration(it.surface).apply { setPhysicalCameraId(AUX_CAM_ID) }) }
        }

        val config = SessionConfiguration(
            SessionConfiguration.SESSION_REGULAR, outputs, executor,
            object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(session: CameraCaptureSession) {
                    cameraSession = session
                    startPreview()
                    onStatusUpdate?.invoke("ID4 预览就绪")
                }
                override fun onConfigureFailed(session: CameraCaptureSession) {
                    onError?.invoke("Session 配置失败")
                }
            }
        )
        camera.createCaptureSession(config)
    }

    /** 预览流 — 纯 preview，不加任何 zoom ratio */
    private var previewReq: CaptureRequest? = null

    private fun startPreview() {
        val session = cameraSession ?: return
        val camera = cameraDevice ?: return
        try {
            val req = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                previewSurface?.let { addTarget(it) }
                set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
            }.build()
            previewReq = req
            session.setRepeatingRequest(req, null, handler)
        } catch (e: Exception) {
            Log.e(TAG, "preview 启动失败: ${e.message}")
        }
    }

    /** 触发射击 */
    private fun triggerCapture() {
        val session = cameraSession ?: return
        val camera = cameraDevice ?: return
        try {
            val req = camera.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE).apply {
                masterReader?.surface?.let { addTarget(it) }
                auxReader?.surface?.let { addTarget(it) }
                previewSurface?.let { addTarget(it) }
                set(CaptureRequest.JPEG_QUALITY, 95.toByte())
                set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
            }.build()
            session.stopRepeating()
            session.capture(req, captureCallback, handler)
        } catch (e: Exception) {
            onError?.invoke("capture 失败: ${e.message}")
            isCapturing = false
            restorePreview()
        }
    }

    /** capture 完成后恢复预览 */
    private var captureCallback = object : CameraCaptureSession.CaptureCallback() {
        override fun onCaptureSequenceCompleted(session: CameraCaptureSession,
                                                  requestId: Int,
                                                  sequenceId: Long) {
            restorePreview()
        }
    }

    private fun restorePreview() {
        previewReq?.let { req ->
            cameraSession?.setRepeatingRequest(req, null, handler)
        }
    }

    private fun close() {
        try { cameraSession?.close() } catch (_: Exception) {}
        try { cameraDevice?.close() } catch (_: Exception) {}
        try { masterReader?.close() } catch (_: Exception) {}
        try { auxReader?.close() } catch (_: Exception) {}
        cameraSession = null; cameraDevice = null
        masterReader = null; auxReader = null
    }

    fun release() {
        close()
        handlerThread.quitSafely()
        executor.shutdown()
    }
}
