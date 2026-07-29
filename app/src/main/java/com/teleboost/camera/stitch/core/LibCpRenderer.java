package com.teleboost.camera.stitch.core;

/**
 * OPPO libcp 三摄融合 JNI 封装。
 *
 * 从 light.co.gallery.utils.LibCpRenderer 反编译还原，
 * 保持与 libcp.so 相同的 native 接口。
 */
public final class LibCpRenderer {

    // ==================== Static native ====================

    /** 获取 libcp 库版本号，如 "0.26.3(3c966)" */
    public static native String nativeGetLibCpVersion();

    /** 获取指定 level 下的帧数 */
    public static native int nativeGetLevelCount(long renderer);

    /** 获取指定索引的图像尺寸 */
    public static native int nativeGetSize(long renderer, int index);

    // ==================== Instance native ====================

    /** 创建渲染器实例，type=2 表示三摄融合 */
    public native long nativeObtainRenderer(int type);

    /** 释放渲染器 */
    public native void nativeReleaseRenderer(long renderer);

    /**
     * 准备渲染器。
     * @param renderer  渲染器句柄
     * @param type      0:JPG, 1:YUV, 2:RAW
     * @param inputPath 输入文件路径
     * @param outputDir 输出目录
     * @return 0 成功
     */
    public native int nativePrepareRenderer(long renderer, int type, String inputPath, String outputDir);

    /**
     * 融合并保存图像。
     * @param renderer  渲染器句柄
     * @param index     帧索引
     * @param width     目标宽度
     * @param height    目标高度
     * @param path      输出路径
     * @param rotation  旋转角度（0/90/180/270）
     * @param highQuality 高画质
     * @return 0 成功
     */
    public native int nativeSaveImage(long renderer, int index, int width, int height,
                                      String path, int rotation, boolean highQuality);

    /** 获取属性值 */
    public native float nativeGetProperty(long renderer, int key);

    /** 设置属性值 */
    public native void nativeSetProperty(long renderer, int key, float value);

    // ==================== Java wrappers ====================

    public int savePreview(long renderer, String path) {
        return nativeSaveImage(renderer, 0, -1, -1, path, 90, false);
    }

    // ==================== Stub methods (来自原版) ====================

    public boolean renderBitmap(int[] argb, int width, int height, int inWidth, int inHeight, int rotation) {
        return true;
    }

    public void depthMapIsReady() {}

    public void setProgress(int progress) {}
}
