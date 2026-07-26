package com.teleboost.camera.stitch.core

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import java.io.File
import java.io.FileOutputStream

/**
 * RAW → JPG 管线
 *
 * 流程：RAW_SENSOR buffer → demosaic（Bayer）→ 白平衡 → tone-map → JPG
 *
 * 设计原则：
 * 1. 所有中间步骤用 ByteArray / FloatArray 操作，不走 Bitmap（避免不必要的编码解码）
 * 2. 最终 JPG 压缩质量可配置（默认 95）
 * 3. 半分辨率模式用于快速预览/验证
 * 4. 失败降级 — 如果 RAW 不可用，自动 fallback 到旧的 YUV-JPG 路径
 */
object RawToJpegPipeline {

    // ---- 输出配置 ----
    var jpegQuality = 95
    var demosaicMethod = "bilinear" // "bilinear" | "malvar"

    // ---- Tone-map 控制 ----
    var exposureBias = 0.0f          // ±EV
    var contrastStrength = 1.0f      // 1.0 = 原始
    var saturationStrength = 1.2f    // 略增饱和度补偿 demosaic 损失

    // ---- 半分辨率模式 ----
    var halfRes = false

    /**
     * 将 RAW_SENSOR buffer 转换为 JPG 文件
     *
     * @param rawBuffer  RAW 像素数据（16-bit/像素，BE）
     * @param width      RAW 宽度
     * @param height     RAW 高度
     * @param bayerPattern  Bayer 模式 "RGGB" / "GRBG" / "GBRG" / "BGGR"
     * @param outputPath  输出 JPG 路径
     * @param rGain    红色通道增益（白平衡）
     * @param gGain    绿色通道增益
     * @param bGain    蓝色通道增益
     * @return true=成功 false=失败触发降级
     */
    fun convert(
        rawBuffer: ByteArray,
        width: Int,
        height: Int,
        bayerPattern: String,
        outputPath: String,
        rGain: Float = 1.8f,
        gGain: Float = 1.0f,
        bGain: Float = 1.5f
    ): Boolean {
        return try {
            val w = if (halfRes) width / 2 else width
            val h = if (halfRes) height / 2 else height

            // Step 1: Demosaic → RGB float array
            val rgb = demosaic(rawBuffer, width, height, bayerPattern, w, h)

            // Step 2: 白平衡
            whiteBalance(rgb, rGain, gGain, bGain)

            // Step 3: Tone-map（曝光 + 对比度 + 饱和度）
            toneMap(rgb)

            // Step 4: 转 Bitmap
            val bitmap = floatRgbToBitmap(rgb, w, h)

            // Step 5: JPEG 编码
            FileOutputStream(File(outputPath)).use { out ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, jpegQuality, out)
            }

            true
        } catch (e: Exception) {
            android.util.Log.e("RawToJpeg", "RAW→JPG failed", e)
            false // 触发降级
        }
    }

    // =============================================
    // Bayer Demosaic — 双线性插值
    // =============================================

    private fun demosaic(
        raw: ByteArray,
        rawW: Int, rawH: Int,
        pattern: String,
        outW: Int, outH: Int
    ): FloatArray {
        // 16-bit BE → ushort
        val pixels = ShortArray(raw.size / 2)
        for (i in pixels.indices) {
            val hi = raw[i * 2].toInt() and 0xFF
            val lo = raw[i * 2 + 1].toInt() and 0xFF
            pixels[i] = ((hi shl 8) or lo).toShort()
        }

        val w = rawW
        val h = rawH
        val skipX = if (halfRes) 2 else 1
        val skipY = if (halfRes) 2 else 1

        val out = FloatArray(outW * outH * 3) // RGB float

        for (oy in 0 until outH) {
            val py = oy * skipY
            for (ox in 0 until outW) {
                val px = ox * skipX
                val idx = oy * outW + ox
                val base = idx * 3

                val (r, g1, g2, b) = getBayerQuads(pixels, w, h, px, py, pattern)
                val z = exposureBias

                // 双线性插值：取相邻同色通道平均
                val rVal = bilinearChannel(pixels, w, h, px, py, 'R', pattern) + z
                val gVal = bilinearChannel(pixels, w, h, px, py, 'G', pattern) + z
                val bVal = bilinearChannel(pixels, w, h, px, py, 'B', pattern) + z

                out[base] = rVal.coerceIn(0f, 65535f)
                out[base + 1] = gVal.coerceIn(0f, 65535f)
                out[base + 2] = bVal.coerceIn(0f, 65535f)
            }
        }

        return out
    }

    private fun getBayerQuads(
        pixels: ShortArray, w: Int, h: Int, x: Int, y: Int, pattern: String
    ): List<Short> {
        return pattern.map { ch ->
            when (ch) {
                'R' -> pixelAt(pixels, w, h, x, y)
                'G' -> pixelAt(pixels, w, h, x, y)
                'B' -> pixelAt(pixels, w, h, x, y)
                else -> 0
            }
        }.map { it.toShort() }
    }

    private fun pixelAt(pixels: ShortArray, w: Int, h: Int, x: Int, y: Int): Int {
        if (x < 0 || y < 0 || x >= w || y >= h) return 0
        return pixels[y * w + x].toInt() and 0xFFFF
    }

    /**
     * 对给定通道做双线性插值。
     * Bayer 模式下，每个像素只保存 1 个通道值，
     * 需要从相邻同色像素插值得到其他两个通道。
     */
    private fun bilinearChannel(
        pixels: ShortArray, w: Int, h: Int, x: Int, y: Int,
        channel: Char, pattern: String
    ): Float {
        val offsets = bayerOffsets(channel, pattern)
        var sum = 0f
        var count = 0

        for ((dx, dy) in offsets) {
            val nx = x + dx
            val ny = y + dy
            if (nx in 0 until w && ny in 0 until h) {
                sum += pixelAt(pixels, w, h, nx, ny)
                count++
            }
        }

        return if (count > 0) sum / count else 0f
    }

    /**
     * 返回 channel 在给定 Bayer 模式下的采样偏移量。
     * 每个 2×2 块里，每个颜色出现一次。
     */
    private fun bayerOffsets(channel: Char, pattern: String): List<Pair<Int, Int>> {
        // 简化实现：以 2×2 块为单位返回同色像素位置
        // R 在 (0,0) / (1,1) 对角
        // G 在 (0,1) / (1,0)
        // B 在 (1,1) / (0,0) 对角（跟 R 互换）
        return when (channel) {
            'R' -> listOf(0 to 0, 1 to 1, 0 to 2, 2 to 0, 2 to 2)
            'B' -> listOf(1 to 0, 0 to 1, 2 to 1, 1 to 2, 3 to 0, 0 to 3)
            'G' -> listOf(0 to 1, 1 to 0, 1 to 2, 2 to 1, 2 to 3, 3 to 2)
            else -> emptyList()
        }
    }

    // =============================================
    // 白平衡
    // =============================================

    private fun whiteBalance(rgb: FloatArray, rGain: Float, gGain: Float, bGain: Float) {
        for (i in 0 until rgb.size step 3) {
            rgb[i] *= rGain          // R
            rgb[i + 1] *= gGain      // G
            rgb[i + 2] *= bGain      // B
        }
    }

    // =============================================
    // Tone-map — 曝光 + 对比度 + 饱和度
    // =============================================

    private fun toneMap(rgb: FloatArray) {
        // 先将 16-bit 范围归一化到 [0, 1]
        for (i in rgb.indices) {
            rgb[i] /= 65535f
        }

        // 对比度
        if (contrastStrength != 1.0f) {
            val pivot = 0.5f
            val slope = contrastStrength
            for (i in rgb.indices) {
                rgb[i] = ((rgb[i] - pivot) * slope + pivot).coerceIn(0f, 1f)
            }
        }

        // 饱和度（RGB->YUV 调整 UV 分量）
        if (saturationStrength != 1.0f) {
            for (i in 0 until rgb.size step 3) {
                val r = rgb[i]
                val g = rgb[i + 1]
                val b = rgb[i + 2]
                val y = 0.299f * r + 0.587f * g + 0.114f * b
                val u = (b - y) * saturationStrength + y
                val v = (r - y) * saturationStrength + y
                rgb[i] = v.coerceIn(0f, 1f)
                rgb[i + 1] = g  // 保留 G
                rgb[i + 2] = u.coerceIn(0f, 1f)
            }
        }

        // Gamma 校正（sRGB 近似）
        for (i in rgb.indices) {
            rgb[i] = linearToSrgb(rgb[i])
        }

        // 转回 8-bit [0, 255]
        for (i in rgb.indices) {
            rgb[i] = (rgb[i] * 255f).coerceIn(0f, 255f)
        }
    }

    private fun linearToSrgb(c: Float): Float {
        return if (c <= 0.0031308f) {
            12.92f * c
        } else {
            1.055f * kotlin.math.pow(c.toDouble(), 1.0 / 2.4).toFloat() - 0.055f
        }
    }

    // =============================================
    // Float RGB → Bitmap（ARGB_8888）
    // =============================================

    private fun floatRgbToBitmap(rgb: FloatArray, w: Int, h: Int): Bitmap {
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val pixels = IntArray(w * h)

        for (y in 0 until h) {
            for (x in 0 until w) {
                val idx = (y * w + x) * 3
                val r = rgb[idx].toInt().coerceIn(0, 255)
                val g = rgb[idx + 1].toInt().coerceIn(0, 255)
                val b = rgb[idx + 2].toInt().coerceIn(0, 255)
                pixels[y * w + x] = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
            }
        }

        bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
        return bitmap
    }

    // =============================================
    // RAW 回调集成 — 在现有 DNG 拍照回调里调用
    // =============================================

    /**
     * 在 RAW 回调中生成 JPG（与 DNG 并存）
     *
     * @param rawBuffer    从 ImageReader 读到的 RAW_SENSOR buffer
     * @param width,height  尺寸
     * @param bayerPattern  从 EXIF / CameraCharacteristics 获取
     * @param saveDir      保存目录
     * @return 生成的 JPG 文件路径，或 null（降级）
     */
    fun processRawToJpeg(
        rawBuffer: ByteArray,
        width: Int, height: Int,
        bayerPattern: String,
        saveDir: String
    ): String? {
        val jpgPath = "$saveDir/stitch_frame_raw_${System.currentTimeMillis()}.jpg"

        val ok = convert(
            rawBuffer = rawBuffer,
            width = width,
            height = height,
            bayerPattern = bayerPattern,
            outputPath = jpgPath,
            halfRes = true // 调试阶段用半分辨率
        )

        return if (ok) jpgPath else null
    }
}
