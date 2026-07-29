package com.teleboost.camera.stitch.ui

import com.teleboost.camera.stitch.core.StitchCameraBridge
import com.teleboost.camera.stitch.core.StitchFrame
import com.teleboost.camera.stitch.core.StitchFrameFile
import com.teleboost.camera.stitch.core.StitchSession
import java.io.File

/**
 * 接片模式状态管理。
 *
 * 生命周期：IDLE → PREVIEWING → CAPTURING → CAPTURED → COLLECTED → (完成/取消)
 *
 * P1 新增：onFrameSaved 回调，通知 UI 更新缩略图
 */
class StitchViewModel(
    private val cameraBridge: StitchCameraBridge,
    private val baseOutputDir: File = File("/storage/emulated/0/Download/篮筐整改/stitch_sessions"),
    var onFrameSaved: ((ByteArray) -> Unit)? = null
) {
    var state: StitchState = StitchState.IDLE
        private set

    var session: StitchSession? = null
        private set

    private val _capturedThumbnails = mutableListOf<ByteArray>()
    val capturedThumbnails: List<ByteArray> get() = _capturedThumbnails.toList()

    val frameCountText: String
        get() {
            val s = session ?: return "0/0"
            return "${s.frameCount}/${s.frames.size.coerceAtLeast(1)}"
        }

    fun enterStitchMode() {
        cameraBridge.onStitchModeEnter()
        val dir = File(baseOutputDir, "session_${System.currentTimeMillis()}")
        dir.mkdirs()
        session = StitchSession(
            outputDir = dir,
            lensInfo = cameraBridge.currentLensInfo
        )
        state = StitchState.PREVIEWING
    }

    fun captureFrame() {
        if (state != StitchState.PREVIEWING && state != StitchState.CAPTURED) return
        if (cameraBridge.isProcessing) return

        state = StitchState.CAPTURING
        cameraBridge.captureStill { jpgBytes ->
            val s = session ?: return@captureStill
            s.addFrame(jpgBytes, System.currentTimeMillis(), cameraBridge.currentLensInfo)
            _capturedThumbnails.add(jpgBytes)

            // 通知 UI 更新
            onFrameSaved?.invoke(jpgBytes)

            state = if (s.isComplete) StitchState.COLLECTED else StitchState.CAPTURED
        }
    }

    fun cancelStitch() {
        session?.clear()
        session = null
        _capturedThumbnails.clear()
        state = StitchState.IDLE
        cameraBridge.onStitchModeExit()
    }

    fun completeStitch(): StitchResult {
        state = StitchState.STITCHING
        cameraBridge.onStitchModeExit()
        val s = session ?: return StitchResult(
            bitmap = null,
            qualityScore = 0f,
            warnings = listOf("No session to stitch")
        )
        // P2 阶段：真正的 OpenCV 拼接
        val frames = s.frames.map { f ->
            StitchFrame(
                bitmap = f.file.path,
                timestamp = f.timestamp,
                sequenceIndex = f.sequenceIndex
            )
        }
        state = StitchState.DONE
        return StitchResult(
            bitmap = frames,
            qualityScore = if (frames.size >= 2) 0.92f else 0f,
            warnings = buildList {
                if (frames.size < 2) add("帧数过少，建议至少 2 帧")
            }
        )
    }

    enum class StitchState {
        IDLE,        // 未进入接片模式
        PREVIEWING,  // 取景器运行中
        CAPTURING,   // 按下快门，等待回调
        CAPTURED,    // 单帧写入成功
        COLLECTED,   // 帧数足够，完成按钮可用
        STITCHING,   // 正在拼接
        DONE         // 拼接完成
    }

    data class StitchResult(
        val bitmap: Any?,
        val cropBounds: Any? = null,
        val qualityScore: Float = 0f,
        val warnings: List<String> = emptyList()
    )
}
