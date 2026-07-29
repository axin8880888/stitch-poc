package com.teleboost.camera.stitch.core

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.media.Image
import android.media.ImageReader
import android.os.ConditionVariable
import android.os.Handler
import android.os.HandlerThread
import android.util.Size
import android.view.Surface
import android.view.TextureView
import android.view.ViewGroup

/**
 * Camera2 实拍桥接 — 替换 placeholder，实现真正的 JPG 拍照。
 *
 * P1 修复（2026-07-12）：
 * - ImageReader 提前创建，与预览 Surface 一同加入 CaptureSession
 * - 拍照时直接复用已有 session，不再临时创建
 * - 优先选择后置摄像头，避免选到前置
 */
class Camera2CaptureBridge(private val context: Context) : StitchCameraBridge {

    private var cameraDevice: CameraDevice? = null
    private var cameraSession: CameraCaptureSession? = null
    private var previewSurface: SurfaceTexture? = null
    private var previewTextureView: TextureView? = null

    private val cameraHandlerThread = HandlerThread("Camera2Bridge").apply { start() }
    private val cameraHandler = Handler(cameraHandlerThread.looper)

    @Volatile
    override var isProcessing: Boolean = false
        private set

    override val currentLensInfo: String
        get() = getSelectedCameraLensInfo()

    private var currentCallback: ((ByteArray) -> Unit)? = null
    private var imageReader: ImageReader? = null
    private var previewSize: Size = Size(1920, 1080)
    private var selectedCameraId: String = "0"

    // 预览请求（重复播放）
    private var previewRequest: CaptureRequest? = null

    fun startPreview(container: ViewGroup) {
        val textureView = TextureView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            surfaceTextureListener = object : TextureView.SurfaceTextureListener {
                override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) {
                    previewSurface = surface
                    previewSize = Size(width, height)
                    openCamera()
                }

                override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) {
                    previewSurface = surface
                    previewSize = Size(width, height)
                }

                override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean {
                    previewSurface = null
                    closeCamera()
                    return true
                }

                override fun onSurfaceTextureUpdated(surface: SurfaceTexture) {}
            }
        }
        previewTextureView = textureView
        container.addView(textureView, 0)
    }

    fun stopPreview() {
        closeCamera()
    }

    override fun captureStill(callback: (ByteArray) -> Unit) {
        if (isProcessing || cameraDevice == null || imageReader == null) {
            return
        }
        isProcessing = true
        currentCallback = callback

        val captureRequest = cameraDevice?.createCaptureRequest(
            CameraDevice.TEMPLATE_STILL_CAPTURE
        )?.apply {
            addTarget(imageReader!!.surface)
            // 同时也要 preview surface，否则部分设备会报错
            previewSurface?.let { addTarget(Surface(it)) }
            set(CaptureRequest.JPEG_QUALITY, 95.toByte())
            set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
            set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)
        }

        try {
            cameraSession?.stopRepeating()
            cameraSession?.capture(
                captureRequest?.build()!!,
                object : CameraCaptureSession.CaptureCallback() {
                    override fun onCaptureCompleted(session: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
                        super.onCaptureCompleted(session, request, result)
                        // ImageReader onImageAvailable 会触发回调
                        // 拍照完成后恢复预览
                    }
                },
                cameraHandler
            )
        } catch (e: Exception) {
            isProcessing = false
            currentCallback = null
            resumePreview()
        }
    }

    override fun onStitchModeEnter() {}
    override fun onStitchModeExit() {}

    /**
     * 选择后置摄像头 — 优先找主摄
     */
    private fun selectBackCamera(): String {
        val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        return try {
            val ids = manager.cameraIdList
            // 找第一个后置摄像头
            for (id in ids) {
                val chars = manager.getCameraCharacteristics(id)
                val facing = chars.get(CameraCharacteristics.LENS_FACING)
                if (facing == CameraCharacteristics.LENS_FACING_BACK) {
                    // 记录镜头信息
                    val focalLengths = chars.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
                    if (focalLengths != null && focalLengths.isNotEmpty()) {
                        _lensInfo = "Camera2 ID=$id 焦距=%.1fmm".format(focalLengths[0])
                    }
                    return id
                }
            }
            // 没找到后置，退到 ID 0
            ids[0]
        } catch (e: Exception) {
            "0"
        }
    }

    private var _lensInfo: String = "Camera2"

    private fun getSelectedCameraLensInfo(): String = _lensInfo

    private fun openCamera() {
        selectedCameraId = selectBackCamera()
        val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager

        try {
            manager.openCamera(selectedCameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    cameraDevice = camera
                    // 拍照 ImageReader 与预览 session 一起创建
                    setupImageReader()
                    startPreviewSession()
                }

                override fun onDisconnected(camera: CameraDevice) {
                    camera.close()
                    cameraDevice = null
                }

                override fun onError(camera: CameraDevice, error: Int) {
                    camera.close()
                    cameraDevice = null
                }
            }, cameraHandler)
        } catch (e: SecurityException) {
            // 无相机权限
        }
    }

    private fun setupImageReader() {
        imageReader?.close()
        imageReader = ImageReader.newInstance(
            previewSize.width, previewSize.height,
            ImageFormat.JPEG, 2
        )
        imageReader?.setOnImageAvailableListener({ reader ->
            val image = reader.acquireLatestImage()
            if (image != null) {
                val bytes = imageToJpegBytes(image)
                image.close()
                val cb = currentCallback
                currentCallback = null
                cameraHandler.post {
                    isProcessing = false
                    cb?.invoke(bytes)
                    // 恢复预览
                    resumePreview()
                }
            }
        }, cameraHandler)
    }

    private fun startPreviewSession() {
        val camera = cameraDevice ?: return
        val st = previewSurface ?: return
        val reader = imageReader ?: return

        val previewSurfaceObj = Surface(st)
        val stillSurfaceObj = reader.surface

        // 构建预览请求
        previewRequest = camera.createCaptureRequest(
            CameraDevice.TEMPLATE_PREVIEW
        ).apply {
            addTarget(previewSurfaceObj)
        }.build()

        try {
            // 两个 surface 都要加入 session
            camera.createCaptureSession(
                listOf(previewSurfaceObj, stillSurfaceObj),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        cameraSession = session
                        resumePreview()
                    }

                    override fun onConfigureFailed(session: CameraCaptureSession) {
                        // session 配置失败
                    }
                },
                cameraHandler
            )
        } catch (e: Exception) {}
    }

    private fun resumePreview() {
        val session = cameraSession ?: return
        val request = previewRequest ?: return
        try {
            session.setRepeatingRequest(request, null, cameraHandler)
        } catch (_: Exception) {}
    }

    private fun closeCamera() {
        try {
            cameraSession?.close()
            cameraSession = null
            cameraDevice?.close()
            cameraDevice = null
            imageReader?.close()
            imageReader = null
        } catch (_: Exception) {}
    }

    private fun imageToJpegBytes(image: Image): ByteArray {
        val buffer = image.planes[0].buffer
        val bytes = ByteArray(buffer.remaining())
        buffer.get(bytes)
        return bytes
    }

    fun release() {
        closeCamera()
        cameraHandlerThread.quitSafely()
    }
}
