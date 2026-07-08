package com.teleboost.camera.stitch

import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.teleboost.camera.stitch.core.StitchConfig

/**
 * 接片入口 Activity — 修复版
 * 使用最稳妥的程序化 UI，确保所有元素可见
 */
class StitchEntryActivity : Activity() {
    companion object {
        private const val TAG = "StitchEntry"
    }

    private val vm = StitchSessionViewModel(StitchConfig.HONEST_DEFAULT)
    private lateinit var statusText: TextView
    private lateinit var actionButton: Button
    private lateinit var logText: TextView
    private val logLines = mutableListOf<String>()
    private var uiReady = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate: 修复版")

        // 构建 root 布局
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setPadding(24, 48, 24, 24)
            gravity = Gravity.TOP
        }

        // 标题
        root.addView(TextView(this).apply {
            text = "光·边界 — 接片"
            textSize = 22f
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        })

        // 配置信息
        root.addView(TextView(this).apply {
            text = "配置: ${vm.stitchConfig.describe()}"
            textSize = 11f
            setPadding(0, 8, 0, 8)
        })

        // 状态文本
        statusText = TextView(this).apply {
            text = "就绪"
            textSize = 14f
            setPadding(0, 16, 0, 16)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
        root.addView(statusText)

        // 操作按钮
        actionButton = Button(this).apply {
            text = "开始接片（伪帧测试）"
            setOnClickListener { onStartStitch() }
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
        root.addView(actionButton)

        // 日志区域
        logText = TextView(this).apply {
            textSize = 10f
        }
        root.addView(ScrollView(this).apply {
            addView(logText)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0
            ).apply { weight = 1f }
        })

        setContentView(root)
        uiReady = true

        // 连接 ViewModel 回调
        vm.setOnProgressUpdateListener { msg ->
            Log.d(TAG, "progress: $msg")
            runOnUiThread { updateUI(msg) }
        }
        vm.setOnStateChangeListener { state ->
            Log.d(TAG, "state: $state")
            runOnUiThread { updateStateUI(state) }
        }
        vm.setOnErrorListener { error ->
            Log.e(TAG, "error: $error")
            runOnUiThread {
                statusText.text = "错误: $error"
                log("❌ 错误: $error")
            }
        }

        // 启动
        log("光·边界接片模块已启动")
        log("红线: blending=${vm.stitchConfig.blendEnabled}")
        log("红线: exposureComp=${vm.stitchConfig.exposureCompensationEnabled}")
        log("红线: cropMode=${vm.stitchConfig.cropMode}")
        log("等待操作: 点击按钮开始伪帧测试")
        statusText.text = "就绪 — 点击下方按钮开始测试"

        Log.d(TAG, "onCreate 完成: UI 就绪")
    }

    private fun updateUI(msg: String) {
        if (!uiReady) return
        statusText.text = msg
        log("📝 $msg")
    }

    private fun updateStateUI(state: StitchState) {
        if (!uiReady) return
        log("🔵 状态: $state")
        actionButton.text = when (state) {
            StitchState.IDLE -> "开始接片（伪帧测试）"
            StitchState.COLLECTING -> "采集中..."
            StitchState.STITCHING -> "拼接中..."
            StitchState.PREVIEWING -> "已出预览"
            StitchState.DONE -> "完成"
            StitchState.CANCELLED -> "已取消，重新开始"
            else -> "处理中..."
        }
        actionButton.isEnabled = (state == StitchState.IDLE ||
                state == StitchState.DONE ||
                state == StitchState.CANCELLED)
    }

    private fun onStartStitch() {
        log("🔄 开始接片流程...")
        vm.start()
        vm.beginCollectingFake()
        vm.beginAligning()
        vm.beginStitching()
        log("✅ 伪帧链路过完")
        log("📸 帧数: ${vm.collectedFrames.size}")
        log("🎯 结果: ${if (vm.stitchResult != null) "有" else "无（仿真模式）"}")
    }

    private fun log(msg: String) {
        logLines.add(msg)
        Log.d(TAG, msg)
        if (uiReady) {
            logText.text = logLines.joinToString("\n")
        }
    }
}
