package com.teleboost.camera.stitch.core

import java.io.File
import java.util.UUID

/**
 * 接片会话 — 管理拍帧、存文件、元数据。
 *
 * 职责：
 *   - addFrame(): 接收 CameraEngine 输出的 JPG 字节，写入磁盘
 *   - 维护帧序列和元数据
 *   - 提供 frameCount / frames / session.json
 *
 * 红线约定：
 *   - 不碰 DNG/RAW 输出
 *   - 不碰主相机拍照触发
 *   - 只做"拍照完成后的帧存储与编排"
 */
class StitchSession(
    val sessionId: String = UUID.randomUUID().toString(),
    val outputDir: File,
    val lensInfo: String = "",
    private val minFrames: Int = 2
) {
    private val _frames = mutableListOf<StitchFrameFile>()
    val frames: List<StitchFrameFile> get() = _frames.toList()
    val frameCount: Int get() = _frames.size
    val isComplete: Boolean get() = frameCount >= minFrames

    /**
     * 加入一帧。owner（CameraEngine 等）调用此方法传入已拍好的 JPG 字节。
     */
    fun addFrame(jpgBytes: ByteArray, timestamp: Long, exifInfo: String = ""): Int {
        val index = _frames.size + 1
        val file = File(outputDir, "frame_%03d.jpg".format(index))
        file.parentFile?.mkdirs()
        file.writeBytes(jpgBytes)
        _frames.add(
            StitchFrameFile(
                sequenceIndex = index,
                file = file,
                timestamp = timestamp,
                exifInfo = exifInfo
            )
        )
        writeSessionMeta()
        return index
    }

    /**
     * 清空会话（取消/退出时调用）
     */
    fun clear() {
        _frames.forEach { it.file.delete() }
        _frames.clear()
        File(outputDir, "session.json").delete()
    }

    private fun writeSessionMeta() {
        val meta = buildString {
            appendLine("{")
            appendLine("  \"sessionId\": \"$sessionId\",")
            appendLine("  \"lensInfo\": \"$lensInfo\",")
            appendLine("  \"frameCount\": $frameCount,")
            appendLine("  \"frames\": [")
            _frames.forEachIndexed { i, f ->
                appendLine("    {\"index\": ${f.sequenceIndex}, \"file\": \"${f.file.name}\", \"timestamp\": ${f.timestamp}}${if (i < _frames.size - 1) "," else ""}")
            }
            appendLine("  ]")
            appendLine("}")
        }
        File(outputDir, "session.json").writeText(meta)
    }
}

data class StitchFrameFile(
    val sequenceIndex: Int,
    val file: File,
    val timestamp: Long,
    val exifInfo: String = ""
)
