package com.teleboost.camera.stitch.ui

import android.app.Activity
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import androidx.core.view.setPadding
import com.teleboost.camera.stitch.core.StitchCameraBridge
import com.teleboost.camera.stitch.core.StitchSession
import com.teleboost.camera.stitch.ui.StitchViewModel.StitchState
import java.io.File

/**
 * 接片模式 Activity。
 *
 * 布局（竖屏全面屏）：
 * ┌──────────────────────────┐
 * │  取景器（CameraEngine Surface）│
 * │  StitchOverlay 叠加层      │
 * │                          │
 * ├──────────────────────────┤
 * │  FrameThumbnailStrip    │
 * ├──────────────────────────┤
 * │ [取消]   [◎快门]  [完成] │
 * └──────────────────────────┘
 *
 * 红线约定：
 * - 取景器 Surface 由外部通过 setCameraPreview() 传入
 * - 不直接操作 Camera2/CameraX API
 * - 拍照通过 StitchCameraBridge 委托给 CameraEngine
 */
class StitchCameraScreen : Activity() {

    private lateinit var viewModel: StitchViewModel
    private lateinit var cameraBridge: StitchCameraBridge
    private var previewContainerId: Int = 0

    private lateinit var overlay: StitchOverlay
    private lateinit var thumbnailStrip: FrameThumbnailStrip
    private lateinit var shutterButton: Button
    private lateinit var cancelButton: Button
    private lateinit var completeButton: Button

    /**
     * 外部通过此方法注入 CameraEngine 桥接实例
     */
    fun setCameraBridge(bridge: StitchCameraBridge) {
        cameraBridge = bridge
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setBackgroundDrawable(ColorDrawable(Color.BLACK))

        // 初始化 ViewModel
        viewModel = StitchViewModel(
            cameraBridge = cameraBridge,
            baseOutputDir = File("/storage/emulated/0/Download/篮筐整改/stitch_sessions")
        )

        // 创建 UI
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

        // 取景器容器 + 叠加层
        val previewContainer = FrameLayout(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
            // CameraEngine 的 SurfaceView/TextureView 会被插入到这里
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
                shutterButton.also { it.layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    gravity = Gravity.CENTER
                }}
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

        // 绑定事件
        setupButtons()
        viewModel.enterStitchMode()
        updateUI()
    }

    /**
     * 返回取景器容器 ID，CameraEngine 将预览 Surface 添加到这个容器中
     */
    fun getPreviewContainerId(): Int = previewContainerId

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
            viewModel.cancelStitch()
            finish()
        }

        completeButton.setOnClickListener {
            val result = viewModel.completeStitch()
            // P2 阶段：启动拼接流程
            // StitchResultActivity 或返回主相机显示结果
            finish()
        }
    }

    override fun onPause() {
        super.onPause()
        if (isFinishing && viewModel.state != StitchState.IDLE && viewModel.state != StitchState.DONE) {
            viewModel.cancelStitch()
        }
    }

    // 这些回调由 CameraEngine 在拍照完成时调用
    fun onFrameCaptured(jpgBytes: ByteArray) {
        runOnUiThread {
            overlay.currentFrame = viewModel.session?.frameCount ?: 0
            overlay.frameCaptured = true
            thumbnailStrip.addThumbnail(jpgBytes)
            updateUI()
        }
    }

    private fun updateUI() {
        completeButton.isEnabled = viewModel.session?.isComplete == true
        shutterButton.isEnabled = !cameraBridge.isProcessing &&
                (viewModel.state == StitchState.PREVIEWING || viewModel.state == StitchState.CAPTURED)
    }

    private fun Int.dpToPx(): Int =
        (this * resources.displayMetrics.density).toInt()
}
