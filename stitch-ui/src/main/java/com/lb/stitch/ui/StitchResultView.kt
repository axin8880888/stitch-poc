package com.teleboost.camera.stitch.ui

import com.teleboost.camera.stitch.PocResult

/**
 * 接片结果信息格式化视图。
 */
class StitchResultView {
    fun render(result: PocResult): String = buildString {
        appendLine("=== 光·边界 接片结果 ===")
        appendLine("标题: ${result.title}")
        appendLine("帧数: ${result.frameCount}")
        appendLine("状态: ${result.status}")
        appendLine("品质评分: ${result.qualityScore}")
        appendLine("裁切模式: ${result.cropMode}")
        appendLine("裁切状态: ${result.cropStatus}")
        appendLine("裁切范围: ${result.cropBoundsSummary}")
        appendLine("导出状态: ${result.exportStatus}")
        appendLine("blending: ${result.blendEnabled}")
        appendLine("曝光补偿: ${result.exposureCompensationEnabled}")
        if (result.warnings.isNotEmpty()) {
            appendLine("--- 警告 ---")
            result.warnings.forEach { appendLine("  • $it") }
        }
        if (result.notes.isNotEmpty()) {
            appendLine("--- 备注 ---")
            result.notes.forEach { appendLine("  • $it") }
        }
    }.trimEnd()

    fun render(resultText: String): String = resultText
}
