package com.teleboost.camera.stitch.core

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.File
import java.io.FileOutputStream
import kotlin.math.*

/**
 * RawToJpegPipeline V2.0 — MotionCam 技术注入版
 *
 * 反编译 MotionCam Pro 后提取的关键技术：
 *
 * 1. ℹ️  RAW_SENSOR 数据源（根本）：不走 YUV-8bit ISP 管线，
 *    从 RAW（12/14-bit Bayer）自行 demosaic → 白平衡 → tone-map → JPG
 *
 * 2. 🎚️  分通道降噪（Luma/Chroma 分离）：
 *    亮度通道保留纹理细节，色度通道可强降噪以消除彩色噪点
 *
 * 3. 📊  ISO 自适应处理：
 *    低 ISO → 低降噪 + 高锐化 → 保留全部细节
 *    高 ISO → 自适应降噪 + 适度锐化 → 噪点平滑但不涂抹
 *
 * 4. 🔍  频域降噪（DCT 域阈值）：
 *    在 8×8 DCT 块中只压高频噪声，保留中低频纹理
 *    比空域高斯模糊更精确，不产生"糊掉"感
 *
 * 5. ⭐  多级渲染质量（参考 NativeRenderQuality）：
 *    PREVIEW / STANDARD / HIGH / VERY_HIGH
 *
 * 6. ✨  细节增强（Unsharp Mask）：
 *    detail 参数控制纹理增强强度，补偿降噪带来的细节损失
 *
 * 7. 💡  高光重建（Highlight Reconstruction）：
 *    利用 RAW 的额外动态范围恢复过曝区域的色彩信息
 *
 * 8. 🎨  DCP 风格色彩（简化版）：
 *    采用 DNG Color Profile 思路做色彩转换
 */

// =============================================
// 枚举：渲染质量级别
// =============================================

enum class NativeRenderQuality(val nativeValue: Int) {
    PREVIEW(0),      // 快速预览
    STANDARD(1),     // 标准质量
    HIGH(2),         // 高质量
    VERY_HIGH(3);    // 极高（最慢但最精细）

    override fun toString(): String = when (this) {
        VERY_HIGH -> "Very High"
        else -> name.lowercase().replaceFirstChar { it.uppercase() }
    }

    companion object {
        fun fromName(name: String, fallback: NativeRenderQuality = STANDARD): NativeRenderQuality {
            return entries.find { it.name.equals(name, ignoreCase = true) } ?: fallback
        }
    }
}

// =============================================
// 数据类：拍摄模式设置（参考 MotionCam CaptureModeSettings）
// =============================================

data class CaptureModeSettings(
    /** 亮度通道降噪强度 [0..1]，0=不降噪 */
    val lumaNr: Float = 0.3f,
    /** 色彩通道降噪强度 [0..1]，可高于 lumaNr 消除彩噪 */
    val chromaNr: Float = 0.5f,
    /** 细节增强 [0..2]，1.0=原始 */
    val detail: Float = 1.0f,
    /** 锐化 [0..2]，1.0=原始 */
    val sharpness: Float = 1.0f,
    /** DCT 域降噪阈值，越大降噪越强，0=关闭 */
    val dctNoiseThreshold: Int = 0,
    /** 对比度 */
    val contrast: Float = 1.0f,
    /** 饱和度 */
    val saturation: Float = 1.2f,
    /** 渲染质量 */
    val renderQuality: NativeRenderQuality = NativeRenderQuality.HIGH,
    /** 白平衡 R 增益 */
    val rGain: Float = 1.8f,
    /** 白平衡 G 增益 */
    val gGain: Float = 1.0f,
    /** 白平衡 B 增益 */
    val bGain: Float = 1.5f,
    /** 高光重建启用 */
    val highlightReconstruction: Boolean = true,
    /** 曝光补偿 EV */
    val exposureBias: Float = 0.0f,
    /** 半分辨率模式（调试/预览用） */
    val halfRes: Boolean = false,
    /** JPEG 质量 [1..100] */
    val jpegQuality: Int = 95,
    /** 启用诺基亚 808 DCP 色彩风格 */
    val useNokiaDcp: Boolean = true,

)

// =============================================
// ISO 自适应配置档案
// =============================================

private data class IsoProfile(
    val maxIso: Int,
    val lumaNr: Float,
    val chromaNr: Float,
    val detail: Float,
    val sharpness: Float,
    val dctNoiseThreshold: Int,
)

/**
 * ISO 自适应降噪 — 这是 MotionCam 高 ISO 不涂抹的核心设计
 *
 * 设计哲学：
 * - ISO 100-400：细节优先，几乎不降噪，锐化拉满
 * - ISO 400-800：轻度降噪，保留纹理
 * - ISO 800-1600：中度降噪，保细节优先
 * - ISO 1600-3200：强力降噪，适度锐化补偿
 * - ISO 3200+：重度降噪，但保留基本的纹理骨架
 */
private val ISO_PROFILES = listOf(
    IsoProfile(maxIso = 100,   lumaNr = 0.05f, chromaNr = 0.15f, detail = 1.4f,  sharpness = 1.3f,  dctNoiseThreshold = 0),
    IsoProfile(maxIso = 200,   lumaNr = 0.08f, chromaNr = 0.20f, detail = 1.3f,  sharpness = 1.2f,  dctNoiseThreshold = 0),
    IsoProfile(maxIso = 400,   lumaNr = 0.12f, chromaNr = 0.25f, detail = 1.2f,  sharpness = 1.1f,  dctNoiseThreshold = 2),
    IsoProfile(maxIso = 800,   lumaNr = 0.18f, chromaNr = 0.35f, detail = 1.1f,  sharpness = 1.0f,  dctNoiseThreshold = 4),
    IsoProfile(maxIso = 1600,  lumaNr = 0.28f, chromaNr = 0.50f, detail = 1.05f, sharpness = 0.95f, dctNoiseThreshold = 6),
    IsoProfile(maxIso = 3200,  lumaNr = 0.40f, chromaNr = 0.60f, detail = 1.0f,  sharpness = 0.9f,  dctNoiseThreshold = 8),
    IsoProfile(maxIso = 6400,  lumaNr = 0.50f, chromaNr = 0.70f, detail = 0.95f, sharpness = 0.85f, dctNoiseThreshold = 12),
    IsoProfile(maxIso = Int.MAX_VALUE, lumaNr = 0.60f, chromaNr = 0.80f, detail = 0.9f, sharpness = 0.8f, dctNoiseThreshold = 16),
)

private fun selectIsoProfile(iso: Int): IsoProfile {
    return ISO_PROFILES.first { iso <= it.maxIso }
}

// =============================================
// 渲染质量缩放因子（参考 NativeRenderQuality）
// =============================================

private data class QualityScale(
    val denoiseScale: Float,   // 降噪缩放
    val detailScale: Float,    // 细节缩放
    val sharpScale: Float,     // 锐化缩放
    val dctBlockSize: Int,     // DCT 块大小
    val demosaicQuality: Int,  // demosaic 质量 1=快速 2=高质量
)

private fun qualityScaleFor(quality: NativeRenderQuality): QualityScale = when (quality) {
    NativeRenderQuality.PREVIEW   -> QualityScale(0.8f, 1.0f, 1.0f, dctBlockSize = 0, demosaicQuality = 1)
    NativeRenderQuality.STANDARD  -> QualityScale(1.0f, 1.0f, 1.0f, dctBlockSize = 8, demosaicQuality = 1)
    NativeRenderQuality.HIGH      -> QualityScale(1.0f, 1.1f, 1.1f, dctBlockSize = 8, demosaicQuality = 2)
    NativeRenderQuality.VERY_HIGH -> QualityScale(1.0f, 1.2f, 1.2f, dctBlockSize = 16, demosaicQuality = 2)
}

// =============================================
// RAW → JPG 管线
// =============================================

object RawToJpegPipeline {

    /**
     * RAW_SENSOR buffer → JPG 文件
     *
     * @param rawBuffer  RAW 像素数据（16-bit/pixel，BE）
     * @param width      RAW 宽度
     * @param height     RAW 高度
     * @param bayerPattern  Bayer 模式 "RGGB"/"GRBG"/"GBRG"/"BGGR"
     * @param iso        拍摄 ISO（用于自适应降噪，默认 100）
     * @param settings   拍摄模式设置（覆盖 ISO 自适应）
     * @param outputPath 输出 JPG 路径
     * @return true=成功 false=触发降级
     */
    fun convert(
        rawBuffer: ByteArray,
        width: Int,
        height: Int,
        bayerPattern: String,
        outputPath: String,
        iso: Int = 100,
        settings: CaptureModeSettings? = null,
    ): Boolean {
        return try {
            val cfg = buildConfig(iso, settings)
            val w = if (cfg.halfRes) width / 2 else width
            val h = if (cfg.halfRes) height / 2 else height
            val qs = qualityScaleFor(cfg.renderQuality)

            // Step 1: Bayer → RGB float
            val rgb = demosaic(rawBuffer, width, height, bayerPattern, w, h, qs)

            // Step 2: 白平衡
            whiteBalance(rgb, cfg.rGain, cfg.gGain, cfg.bGain)

            // Step 3: 高光重建（在 tone-map 前做，保留 RAW 额外动态范围）
            if (cfg.highlightReconstruction) {
                highlightReconstruction(rgb, rawBuffer, width, height, bayerPattern, w, h)
            }

            // Step 4: 分通道降噪（Luma/Chroma 分离）
            if (cfg.lumaNr > 0f || cfg.chromaNr > 0f) {
                denoiseSeparateChannels(
                    rgb, w, h,
                    lumaStrength = cfg.lumaNr * qs.denoiseScale,
                    chromaStrength = cfg.chromaNr * qs.denoiseScale,
                )
            }

            // Step 5: DCT 域降噪（保留纹理，只压噪声）
            if (cfg.dctNoiseThreshold > 0 && qs.dctBlockSize > 0) {
                dctDenoise(rgb, w, h,
                    threshold = (cfg.dctNoiseThreshold * qs.denoiseScale).toInt(),
                    blockSize = qs.dctBlockSize,
                )
            }

            // Step 6: 细节增强（Unsharp Mask）— 补偿降噪损失
            if (cfg.detail != 1.0f || cfg.sharpness != 1.0f) {
                detailEnhance(rgb, w, h,
                    detailStrength = cfg.detail * qs.detailScale,
                    sharpnessStrength = cfg.sharpness * qs.sharpScale,
                )
            }

            // Step 7: Tone-map（曝光 + 对比度 + 饱和度 + Gamma）
            toneMap(rgb, cfg)

            // Step 8: Bitmap → JPG
            val bitmap = floatRgbToBitmap(rgb, w, h)
            FileOutputStream(File(outputPath)).use { out ->
                bitmap.compress(Bitmap.CompressFormat.JPEG, cfg.jpegQuality, out)
            }

            true
        } catch (e: Exception) {
            android.util.Log.e("RawToJpeg", "RAW→JPG failed", e)
            false
        }
    }

    private fun buildConfig(iso: Int, override: CaptureModeSettings?): CaptureModeSettings {
        val profile = selectIsoProfile(iso)
        return override ?: CaptureModeSettings(
            lumaNr = profile.lumaNr,
            chromaNr = profile.chromaNr,
            detail = profile.detail,
            sharpness = profile.sharpness,
            dctNoiseThreshold = profile.dctNoiseThreshold,
            halfRes = iso > 3200,  // 极高 ISO 自动半分辨率降噪
        )
    }

    // =============================================
    // Bayer Demosaic
    // =============================================

    private fun demosaic(
        raw: ByteArray, rawW: Int, rawH: Int, pattern: String,
        outW: Int, outH: Int, qs: QualityScale,
    ): FloatArray {
        val pixels = readU16(raw)
        val skipX = if (outW < rawW) rawW / outW else 1
        val skipY = if (outH < rawH) rawH / outH else 1
        val out = FloatArray(outW * outH * 3)

        for (oy in 0 until outH) {
            val py = oy * skipY
            for (ox in 0 until outW) {
                val px = ox * skipX
                val idx = (oy * outW + ox) * 3

                when (qs.demosaicQuality) {
                    2 -> { // 高质量：AHD 风格（简化版，用更多周围像素投票）
                        val r = interpolateChannel(pixels, rawW, rawH, px, py, 'R', pattern, radius = 2)
                        val g = interpolateChannel(pixels, rawW, rawH, px, py, 'G', pattern, radius = 2)
                        val b = interpolateChannel(pixels, rawW, rawH, px, py, 'B', pattern, radius = 2)
                        out[idx] = r.coerceIn(0f, 65535f)
                        out[idx + 1] = g.coerceIn(0f, 65535f)
                        out[idx + 2] = b.coerceIn(0f, 65535f)
                    }
                    else -> { // 标准：双线性
                        val r = bilinearChannel(pixels, rawW, rawH, px, py, 'R', pattern)
                        val g = bilinearChannel(pixels, rawW, rawH, px, py, 'G', pattern)
                        val b = bilinearChannel(pixels, rawW, rawH, px, py, 'B', pattern)
                        out[idx] = r.coerceIn(0f, 65535f)
                        out[idx + 1] = g.coerceIn(0f, 65535f)
                        out[idx + 2] = b.coerceIn(0f, 65535f)
                    }
                }
            }
        }
        return out
    }

    private fun readU16(raw: ByteArray): IntArray {
        val pixels = IntArray(raw.size / 2)
        for (i in pixels.indices) {
            val hi = raw[i * 2].toInt() and 0xFF
            val lo = raw[i * 2 + 1].toInt() and 0xFF
            pixels[i] = (hi shl 8) or lo
        }
        return pixels
    }

    private fun px(pixels: IntArray, w: Int, h: Int, x: Int, y: Int): Int {
        if (x < 0 || y < 0 || x >= w || y >= h) return 0
        return pixels[y * w + x]
    }

    /**
     * 带半径的双线性插值：从周围 radius×radius 范围内
     * 的同色像素取加权平均。半径越大越平滑，但也丢失更多细节。
     */
    private fun interpolateChannel(
        pixels: IntArray, w: Int, h: Int, x: Int, y: Int,
        channel: Char, pattern: String, radius: Int = 1,
    ): Float {
        var sum = 0f
        var count = 0

        for (dy in -radius..radius) {
            for (dx in -radius..radius) {
                val nx = x + dx
                val ny = y + dy
                if (nx in 0 until w && ny in 0 until h) {
                    val bayerChannel = getBayerChannel(nx, ny, pattern)
                    if (bayerChannel == channel) {
                        sum += px(pixels, w, h, nx, ny)
                        count++
                    }
                }
            }
        }
        return if (count > 0) sum / count else 0f
    }

    private fun bilinearChannel(
        pixels: IntArray, w: Int, h: Int, x: Int, y: Int,
        channel: Char, pattern: String,
    ): Float {
        return interpolateChannel(pixels, w, h, x, y, channel, pattern, radius = 1)
    }

    private fun getBayerChannel(x: Int, y: Int, pattern: String): Char {
        // 每个 2×2 块：由 pattern 定义
        return pattern[(y % 2) * 2 + (x % 2)]
    }

    // =============================================
    // 白平衡
    // =============================================

    private fun whiteBalance(rgb: FloatArray, rGain: Float, gGain: Float, bGain: Float) {
        for (i in 0 until rgb.size step 3) {
            rgb[i] *= rGain
            rgb[i + 1] *= gGain
            rgb[i + 2] *= bGain
        }
    }

    // =============================================
    // 高光重建 — 利用 RAW 额外动态范围
    // =============================================

    /**
     * RAW 数据有 12-14bit（4096-16384）的动态范围，远超 8-bit JPG（256）。
     * 当 RAW 中的高光在 8-bit 裁剪前，可以从 RAW 恢复过曝通道的颜色。
     *
     * 方法：找出任一通道 > 95% 饱和的像素，用相邻通道插值颜色
     */
    private fun highlightReconstruction(
        rgb: FloatArray,
        rawBuffer: ByteArray, rawW: Int, rawH: Int, pattern: String,
        outW: Int, outH: Int,
    ) {
        val pixels = readU16(rawBuffer)
        val saturated = 0.95f * 65535f
        val skipX = if (outW < rawW) rawW / outW else 1
        val skipY = if (outH < rawH) rawH / outH else 1
        val half = saturated / 2f

        for (oy in 0 until outH) {
            val py = oy * skipY
            for (ox in 0 until outW) {
                val px = ox * skipX
                val idx = (oy * outW + ox) * 3

                val r = rgb[idx]
                val g = rgb[idx + 1]
                val b = rgb[idx + 2]

                // 任一通道接近饱和 → 尝试恢复
                if (r > saturated || g > saturated || b > saturated) {
                    var recoveredR = if (r > saturated) retrieveChannel(pixels, rawW, rawH, px, py, 'R', pattern, half) else r
                    var recoveredG = if (g > saturated) retrieveChannel(pixels, rawW, rawH, px, py, 'G', pattern, half) else g
                    var recoveredB = if (b > saturated) retrieveChannel(pixels, rawW, rawH, px, py, 'B', pattern, half) else b

                    // 从相邻通道推导颜色比
                    val neighborAvg = (recoveredR + recoveredG + recoveredB) / 3f
                    if (neighborAvg > saturated) continue // 全过曝，无信息可恢复

                    rgb[idx] = recoveredR.coerceAtMost(saturated)
                    rgb[idx + 1] = recoveredG.coerceAtMost(saturated)
                    rgb[idx + 2] = recoveredB.coerceAtMost(saturated)
                }
            }
        }
    }

    private fun retrieveChannel(
        pixels: IntArray, w: Int, h: Int, x: Int, y: Int,
        channel: Char, pattern: String, fallback: Float,
    ): Float {
        // 从最近的同色像素读取
        for (r in 1..4) {
            for (dy in -r..r) {
                for (dx in -r..r) {
                    val nx = x + dx
                    val ny = y + dy
                    if (nx in 0 until w && ny in 0 until h) {
                        if (getBayerChannel(nx, ny, pattern) == channel) {
                            return px(pixels, w, h, nx, ny).toFloat()
                        }
                    }
                }
            }
        }
        return fallback
    }

    // =============================================
    // 分通道降噪（Luma/Chroma 分离）
    // =============================================

    /**
     * 将 RGB 转 YUV → 分别对 Y（亮度）和 UV（色度）降噪 →
     * 再转回 RGB。
     *
     * MotionCam 的关键设计：
     * - chromaNr 可以 > lumaNr：色度强降噪消除彩噪，亮度保留纹理
     * - 高 ISO 场景，人眼对色度噪点更敏感，所以可以重手降
     * - 亮度降噪适度即可，否则细节全丢
     */
    private fun denoiseSeparateChannels(
        rgb: FloatArray, w: Int, h: Int,
        lumaStrength: Float, chromaStrength: Float,
    ) {
        val size = w * h
        val y = FloatArray(size)
        val u = FloatArray(size)
        val v = FloatArray(size)

        // RGB → YUV
        for (i in 0 until size) {
            val r = rgb[i * 3] / 65535f
            val g = rgb[i * 3 + 1] / 65535f
            val b = rgb[i * 3 + 2] / 65535f
            y[i] = 0.299f * r + 0.587f * g + 0.114f * b
            u[i] = (b - y[i]) * 0.5f
            v[i] = (r - y[i]) * 0.5f
        }

        // 对亮度做轻度双边滤波
        if (lumaStrength > 0.01f) {
            bilateralFilter(y, w, h, lumaStrength * 2.0f)
        }

        // 对色度做较强双边滤波
        if (chromaStrength > 0.01f) {
            bilateralFilter(u, w, h, chromaStrength * 3.0f)
            bilateralFilter(v, w, h, chromaStrength * 3.0f)
        }

        // YUV → RGB
        for (i in 0 until size) {
            val yy = y[i].coerceIn(0f, 1f)
            val uu = u[i] * saturationStrength(1.0f)
            val vv = v[i] * saturationStrength(1.0f)
            rgb[i * 3]     = ((vv * 1.4f + yy) * 65535f).coerceIn(0f, 65535f)
            rgb[i * 3 + 1] = ((yy - uu * 0.395f - vv * 0.581f) * 65535f).coerceIn(0f, 65535f)
            rgb[i * 3 + 2] = ((uu * 2.032f + yy) * 65535f).coerceIn(0f, 65535f)
        }
    }

    /**
     * 简单双边滤波（Bilateral Filter）。
     * 比高斯模糊好在：保留边缘的同时平滑平坦区域。
     * 这是 MotionCam 不产生"涂抹感"的关键算法之一。
     */
    private fun bilateralFilter(channel: FloatArray, w: Int, h: Int, sigmaR: Float) {
        val size = 2.minOf(RADIUS, minOf(w, h) / 4)
        val sigmaD = size.toFloat() / 2f
        val spatialCache = Array(2 * size + 1) { FloatArray(2 * size + 1) }

        for (dy in -size..size) {
            for (dx in -size..size) {
                spatialCache[dy + size][dx + size] =
                    exp(-(dx * dx + dy * dy).toFloat() / (2f * sigmaD * sigmaD))
            }
        }

        val output = FloatArray(channel.size)

        for (y in 0 until h) {
            for (x in 0 until w) {
                val centerIdx = y * w + x
                val centerVal = channel[centerIdx]
                var sum = 0f
                var weightSum = 0f

                for (dy in -size..size) {
                    val ny = y + dy
                    if (ny < 0 || ny >= h) continue

                    for (dx in -size..size) {
                        val nx = x + dx
                        if (nx < 0 || nx >= w) continue

                        val neighborVal = channel[ny * w + nx]
                        val diff = centerVal - neighborVal
                        val rangeWeight = exp(-(diff * diff) / (2f * sigmaR * sigmaR))
                        val spatialWeight = spatialCache[dy + size][dx + size]
                        val weight = spatialWeight * rangeWeight

                        sum += neighborVal * weight
                        weightSum += weight
                    }
                }

                output[centerIdx] = if (weightSum > 0.001f) sum / weightSum else centerVal
            }
        }

        System.arraycopy(output, 0, channel, 0, channel.size)
    }

    // =============================================
    // DCT 域降噪
    // =============================================

    /**
     * 在 DCT（离散余弦变换）域做降噪。
     * 原理：图像能量集中在 DCT 低频系数，噪声均匀分布在所有频率。
     * 对小幅度高频系数做阈值收缩，可去除噪声而不损失纹理。
     *
     * MotionCam 的 dctNoiseThreshold 正是这个机制的参数。
     */
    private fun dctDenoise(rgb: FloatArray, w: Int, h: Int, threshold: Int, blockSize: Int) {
        val bs = blockSize.coerceIn(4, 16)
        val bsw = w / bs
        val bsh = h / bs

        if (bsw == 0 || bsh == 0) return

        for (channel in 0 until 3) {
            // 提取单通道数据
            val plane = FloatArray(w * h)
            for (i in 0 until w * h) {
                plane[i] = rgb[i * 3 + channel]
            }

            // 分块 DCT → 阈值 → IDCT
            for (by in 0 until bsh) {
                for (bx in 0 until bsw) {
                    dctBlock(plane, w, h, bx * bs, by * bs, bs, threshold)
                }
            }

            for (i in 0 until w * h) {
                rgb[i * 3 + channel] = plane[i].coerceIn(0f, 65535f)
            }
        }
    }

    /**
     * 对一个 8×8 或 16×16 块做 DCT → 小系数软阈值 → IDCT
     */
    private fun dctBlock(plane: FloatArray, w: Int, h: Int, startX: Int, startY: Int, bs: Int, threshold: Int) {
        val block = Array(bs) { FloatArray(bs) }
        val t = threshold.toFloat()

        // 取块
        for (y in 0 until bs) {
            for (x in 0 until bs) {
                block[y][x] = plane[(startY + y) * w + (startX + x)]
            }
        }

        // 归一化到 [0, 1] 范围 DCT
        val mean = block.map { it.average().toFloat() }.average().toFloat()
        for (y in 0 until bs) {
            for (x in 0 until bs) {
                block[y][x] = (block[y][x] - mean) / 65535f
            }
        }

        // 2D DCT
        val dct = Array(bs) { FloatArray(bs) }
        val pi = PI.toFloat()
        val invSqrt2 = 1f / sqrt(2f)

        for (u in 0 until bs) {
            for (v in 0 until bs) {
                var sum = 0f
                for (y in 0 until bs) {
                    for (x in 0 until bs) {
                        sum += block[y][x] *
                            cos((2f * x + 1f) * u * pi / (2f * bs)) *
                            cos((2f * y + 1f) * v * pi / (2f * bs))
                    }
                }
                val cu = if (u == 0) invSqrt2 else 1f
                val cv = if (v == 0) invSqrt2 else 1f
                dct[u][v] = (2f / bs) * cu * cv * sum
            }
        }

        // 软阈值（只砍小系数，保留大系数 = 保留纹理）
        for (u in 0 until bs) {
            for (v in 0 until bs) {
                if (u == 0 && v == 0) continue // 保留 DC
                val mag = abs(dct[u][v])
                dct[u][v] = sign(dct[u][v]) * max(0f, mag - t / 65535f)
            }
        }

        // 2D IDCT
        for (y in 0 until bs) {
            for (x in 0 until bs) {
                var sum = 0f
                for (u in 0 until bs) {
                    for (v in 0 until bs) {
                        val cu = if (u == 0) invSqrt2 else 1f
                        val cv = if (v == 0) invSqrt2 else 1f
                        sum += cu * cv * dct[u][v] *
                            cos((2f * x + 1f) * u * pi / (2f * bs)) *
                            cos((2f * y + 1f) * v * pi / (2f * bs))
                    }
                }
                block[y][x] = (2f / bs) * sum * 65535f + mean
            }
        }

        // 写回
        for (y in 0 until bs) {
            for (x in 0 until bs) {
                plane[(startY + y) * w + (startX + x)] = block[y][x]
            }
        }
    }

    // =============================================
    // 细节增强（Unsharp Mask）
    // =============================================

    /**
     * Unsharp Mask 流程：
     * 原图 - 高斯模糊 = 高频细节 → 乘以增益 → 加回原图
     *
     * MotionCam 的 detail 参数控制纹理增强强度，
     * sharpness 边缘增强强度。
     */
    private fun detailEnhance(
        rgb: FloatArray, w: Int, h: Int,
        detailStrength: Float, sharpnessStrength: Float,
    ) {
        if (detailStrength <= 1.0f && sharpnessStrength <= 1.0f) return

        for (channel in 0 until 3) {
            val plane = FloatArray(w * h)
            for (i in 0 until w * h) {
                plane[i] = rgb[i * 3 + channel]
            }

            // 高斯模糊（大核 = 细节增强，小核 = 边缘锐化）
            val detailBlur = if (detailStrength > 1.0f) {
                val blurred = plane.copyOf()
                gaussianBlur(blurred, w, h, sigma = 1.5f)
                blurred
            } else null

            val sharpBlur = if (sharpnessStrength > 1.0f) {
                val blurred = plane.copyOf()
                gaussianBlur(blurred, w, h, sigma = 0.8f)
                blurred
            } else null

            for (i in 0 until w * h) {
                var result = plane[i]

                // 细节增强（大尺度）
                if (detailBlur != null) {
                    val detail = plane[i] - detailBlur[i]
                    result += detail * (detailStrength - 1.0f)
                }

                // 边缘锐化（小尺度）
                if (sharpBlur != null) {
                    val edge = plane[i] - sharpBlur[i]
                    result += edge * (sharpnessStrength - 1.0f)
                }

                rgb[i * 3 + channel] = result.coerceIn(0f, 65535f)
            }
        }
    }

    private fun gaussianBlur(plane: FloatArray, w: Int, h: Int, sigma: Float) {
        val radius = ceil(sigma * 2f).toInt().coerceIn(1, 8)
        val kernel = FloatArray(2 * radius + 1)
        val sigma2 = 2f * sigma * sigma
        var kSum = 0f
        for (i in -radius..radius) {
            kernel[i + radius] = exp(-(i * i).toFloat() / sigma2)
            kSum += kernel[i + radius]
        }
        for (i in kernel.indices) kernel[i] /= kSum

        val temp = FloatArray(w * h)

        // 水平
        for (y in 0 until h) {
            for (x in 0 until w) {
                var sum = 0f
                for (k in -radius..radius) {
                    val nx = (x + k).coerceIn(0, w - 1)
                    sum += plane[y * w + nx] * kernel[k + radius]
                }
                temp[y * w + x] = sum
            }
        }

        // 垂直
        for (x in 0 until w) {
            for (y in 0 until h) {
                var sum = 0f
                for (k in -radius..radius) {
                    val ny = (y + k).coerceIn(0, h - 1)
                    sum += temp[ny * w + x] * kernel[k + radius]
                }
                plane[y * w + x] = sum
            }
        }
    }

    // =============================================
    // Tone-map
    // =============================================

    private fun saturationStrength(base: Float): Float = base

    private fun toneMap(rgb: FloatArray, cfg: CaptureModeSettings) {
        // 归一化到 [0, 1]
        for (i in rgb.indices) {
            rgb[i] /= 65535f
        }

        // 曝光补偿
        if (cfg.exposureBias != 0f) {
            val ev = 2f.pow(cfg.exposureBias)
            for (i in rgb.indices) {
                rgb[i] *= ev
            }
        }

        // 诺基亚 808 DCP 色彩风格（在曝光后、对比度前，保持线性域）
        if (cfg.useNokiaDcp) {
            applyNokia808ColorProfile(rgb)
        }

        // 对比度
        if (cfg.contrast != 1.0f) {
            val pivot = 0.5f
            for (i in rgb.indices) {
                rgb[i] = ((rgb[i] - pivot) * cfg.contrast + pivot).coerceIn(0f, 1f)
            }
        }

        // 饱和度 — 在 RGB 空间做（简化版）
        if (cfg.saturation != 1.0f) {
            for (i in 0 until rgb.size step 3) {
                val r = rgb[i]
                val g = rgb[i + 1]
                val b = rgb[i + 2]
                val gray = 0.299f * r + 0.587f * g + 0.114f * b
                rgb[i]     = (gray + (r - gray) * cfg.saturation).coerceIn(0f, 1f)
                rgb[i + 1] = (gray + (g - gray) * cfg.saturation).coerceIn(0f, 1f)
                rgb[i + 2] = (gray + (b - gray) * cfg.saturation).coerceIn(0f, 1f)
            }
        }

        // Gamma 校正（sRGB）
        for (i in rgb.indices) {
            rgb[i] = linearToSrgb(rgb[i])
        }

        // 回 [0, 255]
        for (i in rgb.indices) {
            rgb[i] = (rgb[i] * 255f).coerceIn(0f, 255f)
        }
    }

    private fun linearToSrgb(c: Float): Float {
        return if (c <= 0.0031308f) {
            12.92f * c
        } else {
            1.055f * c.pow(1.0f / 2.4f) - 0.055f
        }
    }

    // =============================================
    // Float RGB → Bitmap
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
    // RAW 回调集成
    // =============================================

    fun processRawToJpeg(
        rawBuffer: ByteArray,
        width: Int, height: Int,
        bayerPattern: String,
        saveDir: String,
        iso: Int = 100,
        settings: CaptureModeSettings? = null,
    ): String? {
        val jpgPath = "$saveDir/stitch_frame_raw_${System.currentTimeMillis()}.jpg"

        val ok = convert(
            rawBuffer = rawBuffer,
            width = width,
            height = height,
            bayerPattern = bayerPattern,
            outputPath = jpgPath,
            iso = iso,
            settings = settings ?: CaptureModeSettings(halfRes = false),
        )

        return if (ok) jpgPath else null
    }

    // =============================================
    // 诺基亚 808 PureView DCP 色彩风格
    // =============================================

    // RGB→XYZ ColorMatrix (D65)
    private val NOKIA_COLOR_MATRIX = floatArrayOf(
        0.750000f, 0.280000f, 0.000000f,
        -0.150000f, 0.920000f, 0.080000f,
        -0.025000f, 0.010000f, 0.700000f,
    )

    // XYZ→RGB ForwardMatrix — 诺基亚暖调偏移
    private val NOKIA_FORWARD_MATRIX = floatArrayOf(
        1.050000f, -0.320000f, -0.080000f,
        -0.220000f, 1.180000f, 0.100000f,
        0.020000f, -0.280000f, 0.850000f,
    )

    /**
     * 应用诺基亚 808 风格色彩
     *
     * 流程：RGB(线性) → ColorMatrix → XYZ → ForwardMatrix → 诺基亚RGB
     *
     * 诺基亚 808 PureView 的色彩特征：
     * - 暖调肤色（略偏红/粉）
     * - 自然饱和的绿色（不偏黄）
     * - 纯净偏青的蓝色
     * - 整体色彩鲜活但不溢出
     */
    private fun applyNokia808ColorProfile(rgb: FloatArray) {
        val size = rgb.size / 3
        val xyz = FloatArray(size * 3)

        // RGB → XYZ
        for (i in 0 until size) {
            val r = rgb[i * 3]
            val g = rgb[i * 3 + 1]
            val b = rgb[i * 3 + 2]
            xyz[i * 3]     = NOKIA_COLOR_MATRIX[0] * r + NOKIA_COLOR_MATRIX[1] * g + NOKIA_COLOR_MATRIX[2] * b
            xyz[i * 3 + 1] = NOKIA_COLOR_MATRIX[3] * r + NOKIA_COLOR_MATRIX[4] * g + NOKIA_COLOR_MATRIX[5] * b
            xyz[i * 3 + 2] = NOKIA_COLOR_MATRIX[6] * r + NOKIA_COLOR_MATRIX[7] * g + NOKIA_COLOR_MATRIX[8] * b
        }

        // XYZ → 诺基亚RGB
        for (i in 0 until size) {
            val x = xyz[i * 3]
            val y = xyz[i * 3 + 1]
            val z = xyz[i * 3 + 2]
            rgb[i * 3]     = (NOKIA_FORWARD_MATRIX[0] * x + NOKIA_FORWARD_MATRIX[1] * y + NOKIA_FORWARD_MATRIX[2] * z).coerceIn(0f, 1f)
            rgb[i * 3 + 1] = (NOKIA_FORWARD_MATRIX[3] * x + NOKIA_FORWARD_MATRIX[4] * y + NOKIA_FORWARD_MATRIX[5] * z).coerceIn(0f, 1f)
            rgb[i * 3 + 2] = (NOKIA_FORWARD_MATRIX[6] * x + NOKIA_FORWARD_MATRIX[7] * y + NOKIA_FORWARD_MATRIX[8] * z).coerceIn(0f, 1f)
        }
    }

    companion object {
        private const val RADIUS = 3
    }
}
