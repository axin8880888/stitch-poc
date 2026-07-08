package com.teleboost.camera.stitch.core

/**
 * 接片全局配置，注入到整个管线。
 *
 * 红线约束：
 * - blendEnabled 默认 false（不涂抹）
 * - exposureCompensationEnabled 默认 false（不调色原始像素）
 * - cropMode 默认 "pure"（纯裁切，不羽化不融合）
 */
data class StitchConfig(
    /** 是否启用 OpenCV Blender（多频段融合），默认关闭 */
    val blendEnabled: Boolean = false,

    /** 是否启用曝光补偿，默认关闭 */
    val exposureCompensationEnabled: Boolean = false,

    /** 裁切模式："pure" = 纯裁毛边，"disabled" = 不裁切 */
    val cropMode: String = "pure",

    /** 预计重叠率（百分比），用于优化特征搜索范围 */
    val overlapHint: Int = 30,

    /** 输出图片格式 */
    val outputFormat: String = "jpeg",

    /** 特征检测器类型："orb" | "sift" | "akaze"，默认 orb（免专利费） */
    val featuresType: String = "orb",

    /** 匹配器类型："homography" | "affine" */
    val matcherType: String = "homography",

    /** warp 类型："spherical" | "cylindrical" | "plane" */
    val warperType: String = "spherical",

    /** 估算器类型："homography" | "affine" | "no" */
    val estimatorType: String = "homography",

    /** 波束法平差："ray" | "reproj" | "no" */
    val bundleAdjusterType: String = "ray",

    /** 最大输出尺寸（长边像素），超出则缩放到此限制 */
    val maxDimension: Int = 4096,

    /** 输出 JPEG 质量 1-100 */
    val jpegQuality: Int = 97,

    /** 是否写 EXIF 到输出图 */
    val writeExif: Boolean = true
) {
    companion object {
        /** 诚实影像默认配置，符合光边界红线 */
        val HONEST_DEFAULT = StitchConfig()

        /** 带 blending 的参考配置（仅对比测试用，不用于正式输出） */
        val WITH_BLEND_REFERENCE = StitchConfig(
            blendEnabled = true,
            exposureCompensationEnabled = true
        )
    }

    /** 快照描述，用于日志和 PocResult 记录 */
    fun describe(): String = buildString {
        append("StitchConfig[")
        append("blend=$blendEnabled, ")
        append("expComp=$exposureCompensationEnabled, ")
        append("crop=$cropMode, ")
        append("features=$featuresType, ")
        append("warper=$warperType")
        append("]")
    }
}
