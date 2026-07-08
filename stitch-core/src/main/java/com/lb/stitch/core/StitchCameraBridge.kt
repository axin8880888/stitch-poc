package com.teleboost.camera.stitch.core

/**
 * CameraEngine 与 Stitch 模块之间的桥接接口。
 *
 * 这是 Camera → Stitch 架构中的"契约层"：
 * - CameraEngine 实现此接口，暴露给 Stitch 模块调用的能力
 * - Stitch 模块只通过此接口与 CameraEngine 交互，不直接触及 Camera2/CameraX API
 *
 * 红线约定：
 * - Stitch 模块不直接调用 CameraEngine 内部方法
 * - 只通过此接口请求拍照和获取 JPG 帧
 */
interface StitchCameraBridge {

    /**
     * 请求 CameraEngine 拍一张 JPG。
     * CameraEngine 负责实际拍照，拍照完成后通过 callback 返回 JPG 字节。
     */
    fun captureStill(callback: (ByteArray) -> Unit)

    /**
     * 判断 CameraEngine 是否正在处理上一张拍照（防止连拍重叠）
     */
    val isProcessing: Boolean

    /**
     * 获取当前镜头信息（用于 Session 元数据记录）
     */
    val currentLensInfo: String

    /**
     * 进入/退出接片模式（CameraEngine 可能需要调整输出目标）
     */
    fun onStitchModeEnter()
    fun onStitchModeExit()
}
