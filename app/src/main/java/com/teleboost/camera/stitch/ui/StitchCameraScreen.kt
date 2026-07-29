package com.teleboost.camera.stitch.ui

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.core.view.setPadding
import com.teleboost.camera.stitch.core.Camera2CaptureBridge
import com.teleboost.camera.stitch.core.StitchCameraBridge
import com.teleboost.camera.stitch.core.StitchSession
import com.teleboost.camera.stitch.ui.StitchViewModel.StitchState
import java.io.File

/**
 * 接片模式 Activity — 带 Camera2 实拍能力。
 *
 * 布局（竖屏全面屏）：
 * ┌──────────────────────────┐
 * │  Camera2 预览 + Overlay   │
 * ├──────────────────────────┤
 * │  FrameThumbnailStrip    │
 * ├──────────────────────────┤
 * │ [取消]   [◎快门]  [完成] │
 * └──────────────────────────┘
 *
 * P1：按一次快门拍一帧，全部写入 Session
 */
class StitchCameraScreen : Activity() {

    private lateinit var viewModel: StitchViewModel
    private val camera2Bridge: Camera2CaptureBridge by lazy {
        Camera2CaptureBridge(this)
    }
    private val cameraBridge: StitchCameraBridge get() = camera2Bridge
    private var previewContainerId: Int = 0

    private lateinit var overlay: StitchOverlay
    private lateinit var thumbnailStrip: FrameThumbnailStrip
    private lateinit var shutterButton: Button
    private lateinit var cancelButton: Button
    private lateinit var completeButton: Button

    init {
        // Activity 自己创建 Camera2 桥接，不再需要外部注入
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawable(ColorDrawable(Color.BLACK))

        // 检查相机权限
        if (!checkCameraPermission()) {
            Toast.makeText(this, "需要相机权限", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        // 初始化 ViewModel (使用 Camera2 桥接)
        viewModel = StitchViewModel(
            cameraBridge = cameraBridge,
            baseOutputDir = File("/storage/emulated/0/Download/篮筐整改/stitch_sessions"),
            onFrameSaved = { jpgBytes ->
                runOnUiThread {
                    overlay.currentFrame = viewModel.session?.frameCount ?: 0
                    overlay.frameCaptured = true
                    thumbnailStrip.addThumbnail(jpgBytes)
                    updateUI()
                }
            }
        )

        // 创建 UI 控件
        overlay = StitchOverlay(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        }

        thumbnailStrip = FrameThumbnailStrip(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                100.dpToPx()
            )
        }

        shutterButton = createStitchButton("◎", 64)
        cancelButton = createStitchButton("✕ 取消", 36)
        completeButton = createStitchButton("✓ 完成", 36).apply {
            isEnabled = false
        }

        // 取景器容器 (Camera2 preview 将插入到此容器中)
        val previewContainer = FrameLayout(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
            addView(this@StitchCameraScreen.overlay)
        }
        previewContainerId = View.generateViewId()
        previewContainer.id = previewContainerId

        // 底部按钮栏
        val buttonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(16, 8, 16, 24)
            addView(cancelButton)
            addView(
                shutterButton.also {
                    it.layoutParams = LinearLayout.LayoutParams(
                        0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f
                    ).apply { gravity = Gravity.CENTER }
                }
            )
            addView(completeButton)
        }

        // 根布局
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
                addView(previewContainer)
                addView(thumbnailStrip)
                addView(buttonRow)
            }
        )

        // 启动 Camera2 预览
        camera2Bridge.startPreview(previewContainer)

        // 绑定事件
        setupButtons()
        viewModel.enterStitchMode()
        updateUI()
    }

    fun getPreviewContainerId(): Int = previewContainerId

    private fun checkCameraPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= 23) {
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
                    PackageManager.PERMISSION_GRANTED
        } else true
    }

    private fun createStitchButton(text: String, textSize: Int): Button {
        return Button(this).apply {
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.argb(80, 255, 255, 255))
            setPadding(20, 8, 20, 8)
            setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, textSize.toFloat())
            this.text = text
            minWidth = 0
            minimumWidth = 0
        }
    }

    private fun setupButtons() {
        shutterButton.setOnClickListener {
            viewModel.captureFrame()
            updateUI()
        }

        cancelButton.setOnClickListener {
            camera2Bridge.stopPreview()
            viewModel.cancelStitch()
            finish()
        }

        completeButton.setOnClickListener {
            camera2Bridge.stopPreview()
            viewModel.completeStitch()
            finish()
        }
    }

    private fun updateUI() {
        completeButton.isEnabled = viewModel.session?.isComplete == true
        shutterButton.isEnabled = !cameraBridge.isProcessing &&
                (viewModel.state == StitchState.PREVIEWING || viewModel.state == StitchState.CAPTURED)
    }

    override fun onPause() {
        super.onPause()
        if (isFinishing) {
            camera2Bridge.stopPreview()
            if (viewModel.state != StitchState.IDLE && viewModel.state != StitchState.DONE) {
                viewModel.cancelStitch()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        camera2Bridge.release()
    }

    private fun Int.dpToPx(): Int =
        (this * resources.displayMetrics.density).toInt()
}
