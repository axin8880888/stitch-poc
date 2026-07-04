package com.teleboost.camera.stitch.ui

import com.teleboost.camera.stitch.PocResult
import com.teleboost.camera.stitch.PocResultStore

class StitchPreviewActivity {
    private var latestText: String = "暂无结果"

    fun onCreate() {
        PocResultStore.observe { result ->
            latestText = format(result)
        }
    }

    fun renderFields(): List<String> = latestText.lineSequence().toList()

    fun onCropClicked(): String {
        val r = PocResultStore.current() ?: return "暂无结果可裁切"
        PocResultStore.save(
            r.copy(
                cropStatus = "manual-adjust-requested",
                exportStatus = "pending",
                notes = r.notes + "用户请求裁切"
            )
        )
        return "已进入裁切"
    }

    fun onExportClicked(): String {
        val r = PocResultStore.current() ?: return "暂无结果可导出"
        PocResultStore.save(
            r.copy(
                exportStatus = "exporting",
                notes = r.notes + "用户请求导出"
            )
        )
        return "已开始导出"
    }

    private fun format(r: PocResult): String = buildString {
        appendLine("title: ${r.title}")
        appendLine("frameCount: ${r.frameCount}")
        appendLine("status: ${r.status}")
        appendLine("qualityScore: ${r.qualityScore}")
        appendLine("cropMode: ${r.cropMode}")
        appendLine("cropStatus: ${r.cropStatus}")
        appendLine("cropBounds: ${r.cropBoundsSummary}")
        appendLine("exportStatus: ${r.exportStatus}")
        appendLine("blendEnabled: ${r.blendEnabled}")
        appendLine("exposureCompensationEnabled: ${r.exposureCompensationEnabled}")
        r.warnings.forEach { appendLine("warning: $it") }
        r.notes.forEach { appendLine("note: $it") }
    }.trimEnd()
}
