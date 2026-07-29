package com.teleboost.camera.stitch.core

import android.content.ContentValues
import android.content.Context
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.hardware.camera2.params.OutputConfiguration
import android.hardware.camera2.params.SessionConfiguration
import android.media.Image
import android.media.ImageReader
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.provider.MediaStore
import android.util.Log
import android.util.Size
import android.view.Surface
import android.view.TextureView
import android.view.ViewGroup
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

/**
 * Stage 27 双摄融合 Bridge — ID4 Master + ID2 Aux 双摄 + libcp 融合。
 *
 * 工作流程：
 * 1. 打开逻辑摄像头
 * 2. 创建 ID4 (Master) 和 ID2 (Aux) 的 ImageReader（JPEG 输出）
 * 3. 同步触发 capture
 * 4. 两个 JPEG 回传后，传给 LibCpRenderer 做融合（保留诺基亚色彩管线）
 * 5. 保存五个产物：
 *    - cam4_master_original.jpg
 *    - cam2_aux_original.jpg
 *    - fusion_result.jpg
 *    - fusion_mask.jpg
 *    - capture_pair.json
 */
class MultiCamCaptureBridge(private val context: Context) {

    companion object {
        private const val TAG = "Stage27Bridge"
        val MASTER_CAM_ID = "4"
        val AUX_CAM_ID = "2"
        private const val JPEG_WIDTH = 4096
        private const val JPEG_HEIGHT = 3072
        private const val MAX_IMAGES = 2
    }

    private var cameraDevice: CameraDevice? = null
    private var cameraSession: CameraCaptureSession? = null
    private val cameraHandlerThread = HandlerThread("Stage27Bridge").apply { start() }
    private val cameraHandler = Handler(cameraHandlerThread.looper)
    private val executor = Executors.newSingleThreadExecutor()

    private var masterReader: ImageReader? = null
    private var auxReader: ImageReader? = null
    private var previewSurface: Surface? = null

    // libcp 渲染器（诺基亚色彩管线）
    private var libCpRenderer: LibCpRenderer? = null
    private var rendererHandle: Long = 0

    @Volatile
    var isProcessing: Boolean = false
        private set
    @Volatile
    var libCpVersion: String = ""
        private set

    var onStatusUpdate: ((String) -> Unit)? = null
    var onCaptureComplete: ((File) -> Unit)? = null
    var onError: ((String) -> Unit)? = null

    private var masterBytes: ByteArray? = null
    private var auxBytes: ByteArray? = null

    // ==================== libcp 初始化 ====================

    fun initLibCp(): Boolean {
        return try {
            Log.i(TAG, "加载 libcp...")
            System.loadLibrary("c++_shared")
            Log.i(TAG, "c++_shared 加载成功")
            System.loadLibrary("ceres")
            Log.i(TAG, "ceres 加载成功")
            System.loadLibrary("cp")
            Log.i(TAG, "cp 加载成功")
            System.loadLibrary("lricompression")
            Log.i(TAG, "lricompression 加载成功")
            System.loadLibrary("native-lib")
            Log.i(TAG, "native-lib 加载成功")

            libCpVersion = LibCpRenderer.nativeGetLibCpVersion()
            Log.i(TAG, "libcp 版本: $libCpVersion")
            libCpRenderer = LibCpRenderer()
            rendererHandle = libCpRenderer!!.nativeObtainRenderer(1)
            Log.i(TAG, "renderer 句柄: 0x${rendererHandle.toULong().toString(16)}")

            if (rendererHandle == 0L) {
                onStatusUpdate?.invoke("渲染器初始化失败: nativeObtainRenderer 返回 0")
                return false
            }

            onStatusUpdate?.invoke("libcp: $libCpVersion")
            true
        } catch (e: UnsatisfiedLinkError) {
            val msg = "libcp 加载失败(链接错误): ${e.message}"
            Log.e(TAG, msg, e)
            onStatusUpdate?.invoke(msg)
            false
        } catch (e: Throwable) {
            val msg = "libcp 初始化失败: ${e.message}"
            Log.e(TAG, msg, e)
            onStatusUpdate?.invoke(msg)
            false
        }
    }

    fun releaseLibCp() {
        if (rendererHandle != 0L) {
            try { libCpRenderer?.nativeReleaseRenderer(rendererHandle) } catch (_: Throwable) {}
            rendererHandle = 0L
        }
        libCpRenderer = null
    }

    // ==================== 预览 ====================

    fun startPreview(container: ViewGroup) {
        val textureView = TextureView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            surfaceTextureListener = object : TextureView.SurfaceTextureListener {
                override fun onSurfaceTextureAvailable(surface: SurfaceTexture, w: Int, h: Int) {
                    previewSurface = Surface(surface)
                    openMultiCam()
                }
                override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, w: Int, h: Int) {
                    previewSurface = Surface(surface)
                }
                override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean {
                    previewSurface = null
                    closeCamera()
                    return true
                }
                override fun onSurfaceTextureUpdated(surface: SurfaceTexture) {}
            }
        }
        container.addView(textureView, 0)
    }

    fun stopPreview() { closeCamera() }

    // ==================== 双摄拍照 ====================

    fun captureFused(outputDir: File) {
        if (isProcessing || cameraDevice == null) {
            onStatusUpdate?.invoke("相机未就绪")
            return
        }
        if (rendererHandle == 0L) {
            onStatusUpdate?.invoke("渲染器未初始化")
            return
        }

        isProcessing = true
        masterBytes = null
        auxBytes = null
        outputDir.mkdirs()

        onStatusUpdate?.invoke("双摄拍照中...")

        masterReader?.setOnImageAvailableListener({ reader ->
            val img = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
            try {
                val buf = img.planes[0].buffer
                masterBytes = ByteArray(buf.remaining()).also { buf.get(it) }
                Log.i(TAG, "ID4 master 捕获: ${masterBytes!!.size / 1024}KB")
                tryFusion(outputDir)
            } finally {
                img.close()
                reader.setOnImageAvailableListener(null, null)
            }
        }, cameraHandler)

        auxReader?.setOnImageAvailableListener({ reader ->
            val img = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
            try {
                val buf = img.planes[0].buffer
                auxBytes = ByteArray(buf.remaining()).also { buf.get(it) }
                Log.i(TAG, "ID2 aux 捕获: ${auxBytes!!.size / 1024}KB")
                tryFusion(outputDir)
            } finally {
                img.close()
                reader.setOnImageAvailableListener(null, null)
            }
        }, cameraHandler)

        triggerCapture()
    }

    private fun tryFusion(outputDir: File) {
        val m = masterBytes ?: return
        val a = auxBytes ?: return

        // 两个都到了，执行 libcp 融合 + 保存
        executor.execute {
            doFusion(outputDir, m, a)
        }
    }

    // ==================== libcp 融合 ====================

    private fun doFusion(outputDir: File, masterJpg: ByteArray, auxJpg: ByteArray) {
        val startTime = System.currentTimeMillis()
        try {
            onStatusUpdate?.invoke("融合中...")

            // 1. 保存原片
            val masterFile = File(outputDir, "cam4_master_original.jpg")
            masterFile.writeBytes(masterJpg)
            saveToMediaStore("cam4_master_original.jpg", masterJpg, "image/jpeg")

            val auxFile = File(outputDir, "cam2_aux_original.jpg")
            auxFile.writeBytes(auxJpg)
            saveToMediaStore("cam2_aux_original.jpg", auxJpg, "image/jpeg")

            // 2. 保存输入文件给 libcp 使用
            val cacheDir = File(context.cacheDir, "dualcam").also { it.mkdirs() }
            val cam4File = File(cacheDir, "input_cam4.jpg").also { it.writeBytes(masterJpg) }
            val cam2File = File(cacheDir, "input_cam2.jpg").also { it.writeBytes(auxJpg) }

            // 3. 调用 libcp 融合（诺基亚色彩管线）
            val prepareResult = libCpRenderer?.nativePrepareRenderer(
                rendererHandle, 0,
                cam4File.absolutePath, outputDir.absolutePath
            ) ?: -1

            if (prepareResult != 0) {
                // libcp 失败，回退输出 ID4 原片
                val fusedFile = File(outputDir, "fusion_result.jpg")
                fusedFile.writeBytes(masterJpg)
                saveToMediaStore("fusion_result.jpg", masterJpg, "image/jpeg")
                writeMetadata(outputDir, startTime, false, "libcp 准备失败: code=$prepareResult", "/fused on: ID4 fallback")
                isProcessing = false
                resumePreview()
                return
            }

            // 4. 执行融合
            val outputPath = File(outputDir, "fusion_result_${System.currentTimeMillis()}.jpg").absolutePath
            val saveResult = libCpRenderer?.nativeSaveImage(
                rendererHandle, 0,
                JPEG_WIDTH, JPEG_HEIGHT,
                outputPath, 0, true
            ) ?: -1

            if (saveResult == 0) {
                val fusedFile = File(outputPath)
                // 重命名为标准名称
                val finalFused = File(outputDir, "fusion_result.jpg")
                fusedFile.renameTo(finalFused)
                saveToMediaStore("fusion_result.jpg", finalFused.readBytes(), "image/jpeg")
                onStatusUpdate?.invoke("融合成功: ${finalFused.absolutePath} (${finalFused.length() / 1024}KB)")
                onCaptureComplete?.invoke(finalFused)

                // 保存 mask（libcp 可能有 mask 输出）
                val maskFile = File(outputDir, "fusion_mask.jpg")
                val maskPath = maskFile.absolutePath
                val maskResult = libCpRenderer?.nativeSaveImage(
                    rendererHandle, 0,
                    JPEG_WIDTH, JPEG_HEIGHT,
                    maskPath, 0, false
                ) ?: -1
                if (maskResult == 0 && maskFile.exists()) {
                    saveToMediaStore("fusion_mask.jpg", maskFile.readBytes(), "image/jpeg")
                }

                writeMetadata(outputDir, startTime, true, "", outputPath)
            } else {
                // 融合失败，回退输出 ID4 原片
                val fusedFile = File(outputDir, "fusion_result.jpg")
                fusedFile.writeBytes(masterJpg)
                saveToMediaStore("fusion_result.jpg", masterJpg, "image/jpeg")
                writeMetadata(outputDir, startTime, false, "libcp 融合失败: code=$saveResult", "ID4 fallback")
                onStatusUpdate?.invoke("融合失败: code=$saveResult，已回退 ID4 原片")
            }
        } catch (e: Exception) {
            Log.e(TAG, "融合异常", e)
            val fusedFile = File(outputDir, "fusion_result.jpg")
            try { fusedFile.writeBytes(masterJpg) } catch (_: Exception) {}
            writeMetadata(outputDir, startTime, false, "异常: ${e.message}", "ID4 fallback")
            onStatusUpdate?.invoke("融合异常: ${e.message}，已回退 ID4")
        } finally {
            isProcessing = false
            resumePreview()
        }
    }

    // ==================== 保存 ====================

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

    private fun writeMetadata(outputDir: File, startTime: Long, success: Boolean, error: String, fusedPath: String) {
        try {
            val jsonFile = File(outputDir, "capture_pair.json")
            val meta = JSONObject().apply {
                put("sessionId", outputDir.name)
                put("timestamp", SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).format(Date()))
                put("stage", "27")
                put("status", if (success) "success" else "fallback")
                put("masterCamId", MASTER_CAM_ID)
                put("auxCamId", AUX_CAM_ID)
                put("libCpVersion", libCpVersion)
                put("files", JSONObject().apply {
                    put("master", "cam4_master_original.jpg")
                    put("aux", "cam2_aux_original.jpg")
                    put("fused", "fusion_result.jpg")
                    put("mask", "fusion_mask.jpg")
                    put("metadata", "capture_pair.json")
                })
                put("fusion", JSONObject().apply {
                    put("success", success)
                    put("error", error)
                    put("outputPath", fusedPath)
                })
                put("performance", JSONObject().apply {
                    put("elapsedMs", System.currentTimeMillis() - startTime)
                })
            }
            jsonFile.writeText(meta.toString(2))
        } catch (e: Exception) {
            Log.e(TAG, "元数据写入失败: ${e.message}")
        }
    }

    // ==================== Camera2 内部 ====================

    private fun openMultiCam() {
        val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val cameraId = findLogicalCamera(manager) ?: run {
            onError?.invoke("未找到逻辑摄像头")
            return
        }
        try {
            manager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    cameraDevice = camera
                    setupReaders()
                    startSession()
                    onStatusUpdate?.invoke("双摄已打开 (ID4 Master + ID2 Aux)")
                }
                override fun onDisconnected(camera: CameraDevice) { camera.close(); cameraDevice = null }
                override fun onError(camera: CameraDevice, err: Int) {
                    camera.close(); cameraDevice = null
                    onError?.invoke("摄像头错误: $err")
                }
            }, cameraHandler)
        } catch (e: Exception) {
            onError?.invoke("打开摄像头失败: ${e.message}")
        }
    }

    private fun findLogicalCamera(manager: CameraManager): String? {
        for (id in manager.cameraIdList) {
            try {
                val chars = manager.getCameraCharacteristics(id)
                if (chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK) {
                    val physical = chars.physicalCameraIds
                    if (physical?.contains(MASTER_CAM_ID) == true && physical.contains(AUX_CAM_ID)) {
                        Log.i(TAG, "逻辑摄像头: $id, 物理: ${physical.joinToString(",")}")
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
        masterReader = ImageReader.newInstance(JPEG_WIDTH, JPEG_HEIGHT, ImageFormat.JPEG, MAX_IMAGES)
        auxReader = ImageReader.newInstance(JPEG_WIDTH, JPEG_HEIGHT, ImageFormat.JPEG, MAX_IMAGES)
    }

    private fun startSession() {
        val camera = cameraDevice ?: return
        val st = previewSurface ?: return

        val outputs = mutableListOf<OutputConfiguration>().apply {
            // preview 绑定到 ID4 物理摄像头
            add(OutputConfiguration(st).apply { setPhysicalCameraId(MASTER_CAM_ID) })
            masterReader?.let { add(OutputConfiguration(it.surface).apply { setPhysicalCameraId(MASTER_CAM_ID) }) }
            auxReader?.let { add(OutputConfiguration(it.surface).apply { setPhysicalCameraId(AUX_CAM_ID) }) }
        }

        val sessionConfig = SessionConfiguration(
            SessionConfiguration.SESSION_REGULAR, outputs, executor,
            object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(session: CameraCaptureSession) {
                    cameraSession = session
                    startPreview()
                    onStatusUpdate?.invoke("双摄预览就绪")
                }
                override fun onConfigureFailed(session: CameraCaptureSession) {
                    onError?.invoke("Session 配置失败")
                }
            }
        )
        camera.createCaptureSession(sessionConfig)
    }

    private fun startPreview() {
        val session = cameraSession ?: return
        val camera = cameraDevice ?: return
        try {
            val req = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                previewSurface?.let { addTarget(it) }
                set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
                set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)
            }.build()
            session.setRepeatingRequest(req, null, cameraHandler)
        } catch (_: Exception) {}
    }

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
                set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)
            }.build()
            session.stopRepeating()
            session.capture(req, object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(session: CameraCaptureSession,
                                                 request: CaptureRequest,
                                                 result: TotalCaptureResult) {
                    Log.i(TAG, "capture 完成")
                }
                override fun onCaptureSequenceCompleted(session: CameraCaptureSession,
                                                         requestId: Int,
                                                         sequenceId: Long) {
                    restorePreview()
                }
            }, cameraHandler)
        } catch (e: Exception) {
            onError?.invoke("capture 失败: ${e.message}")
            isProcessing = false
            restorePreview()
        }
    }

    private fun restorePreview() {
        val session = cameraSession ?: return
        val camera = cameraDevice ?: return
        try {
            val req = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply {
                previewSurface?.let { addTarget(it) }
                set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO)
            }.build()
            session.setRepeatingRequest(req, null, cameraHandler)
        } catch (_: Exception) {}
    }

    private fun resumePreview() {
        restorePreview()
    }

    private fun closeCamera() {
        try { cameraSession?.close() } catch (_: Exception) {}
        try { cameraDevice?.close() } catch (_: Exception) {}
        try { masterReader?.close() } catch (_: Exception) {}
        try { auxReader?.close() } catch (_: Exception) {}
        cameraSession = null; cameraDevice = null
        masterReader = null; auxReader = null
    }

    fun release() {
        releaseLibCp()
        closeCamera()
        cameraHandlerThread.quitSafely()
        executor.shutdown()
    }
}
