package com.teleboost.camera.stitch

import kotlin.properties.Delegates

data class PocResult(
    val title: String,
    val frameCount: Int,
    val status: String,
    val qualityScore: Float,
    val cropMode: String,
    val cropStatus: String,
    val cropBoundsSummary: String,
    val blendEnabled: Boolean,
    val exposureCompensationEnabled: Boolean,
    val exportStatus: String,
    val warnings: List<String>,
    val notes: List<String>
)

object PocResultStore {
    private var latest: PocResult? = null
    private val listeners = mutableListOf<(PocResult) -> Unit>()

    fun save(result: PocResult) {
        latest = result
        listeners.toList().forEach { it(result) }
    }

    fun current(): PocResult? = latest

    fun observe(listener: (PocResult) -> Unit) {
        listeners += listener
        latest?.let(listener)
    }
}
