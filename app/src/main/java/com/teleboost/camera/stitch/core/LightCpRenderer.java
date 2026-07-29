package com.teleboost.camera.stitch.core;

/**
 * OPPO libcp 完整 JNI 封装。
 *
 * 从 libnative-lib.so 的符号表反推全部 native 方法，
 * 包含未在 LibCpRenderer.smali 中声明的函数。
 * 保持与 light.co.gallery.utils.LibCpRenderer 包名一致
 * 以便与 libcp.so / libnative-lib.so 的 JNI 绑定兼容。
 */
public final class LightCpRenderer {

    static {
        System.loadLibrary("native-lib");
    }

    // ==================== Static native ====================

    /** 获取 libcp 库版本号，如 "0.26.3(3c966)" */
    public static native String nativeGetLibCpVersion();

    public static native int nativeGetLevelCount(long renderer);

    public static native int nativeGetSize(long renderer, int index);

    public static native long nativeTxGetLriMatrix(long renderer);

    public static native boolean nativeTxExists(long renderer);

    public static native void nativeTxReset(long renderer);

    public static native void nativeTxFlipX(long renderer, boolean flip);

    public static native void nativeTxFlipY(long renderer, boolean flip);

    public static native void nativeTxRot(long renderer, float degrees, int width, int height);

    public static native void nativeTxSetCrop(long renderer, float left, float top, float right, float bottom);

    public static native void nativeTxGetCrop(long renderer, float[] crop);

    public static native void nativeTxGetMatrix(long renderer, float[] matrix);

    // ==================== Instance native ====================

    /**
     * 创建渲染器实例。
     * @param type 渲染类型：0=auto, 1=portrait, 2=multiCam(三摄融合)
     * @return 渲染器句柄（long），0 表示失败
     */
    public native long nativeObtainRenderer(int type);

    /** 释放渲染器 */
    public native void nativeReleaseRenderer(long renderer);

    /**
     * 准备渲染器。
     * @param renderer  渲染器句柄
     * @param type      处理类型：0=JPG, 2=RAW, 4=YUV
     * @param inputPath 输入文件路径
     * @param outputDir 输出目录
     * @return 0=成功, 其他=错误码
     */
    public native int nativePrepareRenderer(long renderer, int type, String inputPath, String outputDir);

    /**
     * 执行渲染处理（暗部还原 / 整体增强）。
     * @param renderer 渲染器句柄
     * @return 0=成功
     */
    public native int nativeRender(long renderer);

    /**
     * 保存处理后的图像。
     * @param renderer    渲染器句柄
     * @param index       帧索引
     * @param width       目标宽度（-1=原始）
     * @param height      目标高度（-1=原始）
     * @param outputPath  输出文件路径
     * @param rotation    旋转角度（0/90/180/270）
     * @param highQuality 是否高画质（true=JPEG 高质量）
     * @return 0=成功
     */
    public native int nativeSaveImage(long renderer, int index, int width, int height,
                                      String outputPath, int rotation, boolean highQuality);

    /**
     * 获取渲染结果数据（即处理后的图像数据）。
     * @param renderer 渲染器句柄
     * @return byte[] 图像数据（格式由 prepareRenderer 决定）
     */
    public native byte[] nativeGetImage(long renderer);

    /**
     * 获取直方图数据。
     * @param renderer 渲染器句柄
     * @return int[] 直方图数据
     */
    public native int[] nativeGetHistogram(long renderer);

    /** 获取指定属性值 */
    public native float nativeGetProperty(long renderer, int key);

    /** 设置指定属性值 */
    public native void nativeSetProperty(long renderer, int key, float value);

    /** GET（获取整数参数） */
    public native int nativeGetParamInt(long renderer, int key);

    /** 从 state 文件获取浮点参数 */
    public native float nativeGetParamFloatFromStateFile(long renderer, String stateFile, String key);

    /** 设置状态 */
    public native void nativeSetState(long renderer, String stateJson);

    /** 保存状态 */
    public native void nativeSaveState(long renderer, String statePath);

    /** 设置景深数据 */
    public native void nativeSetDofDepth(long renderer, float depth);

    /** 获取指定坐标的景深值 */
    public native float nativeGetDepthAtPoint(long renderer, float x, float y);

    /** 设置用户评分（用于学习算法） */
    public native void nativeSetUserRating(long renderer, int rating);

    /** 获取用户评分 */
    public native int nativeGetUserRating(long renderer);

    /** 设置跟踪等级 */
    public native void nativeSetTraceLevels(long renderer, String levels);

    /** 中止渲染 */
    public native void nativeAbortRenderer(long renderer);

    // ==================== Java wrapper methods ====================

    /**
     * 简化保存预览（旋转90°）。
     */
    public int savePreview(long renderer, String path) {
        return nativeSaveImage(renderer, 0, -1, -1, path, 90, false);
    }

    /**
     * 通用的单帧图像增强管线。
     *
     * @param jpegPath  输入 JPEG 文件路径
     * @param outputPath 输出 JPEG 文件路径
     * @return true=成功, false=失败
     */
    public boolean enhanceSingleFrame(String jpegPath, String outputPath) {
        long renderer = nativeObtainRenderer(0);
        if (renderer == 0) {
            return false;
        }
        try {
            // 0 表示 JPG 类型
            // outputDir 这里传入输出目录，nativeSaveImage 需要完整路径
            int ret = nativePrepareRenderer(renderer, 0, jpegPath, outputPath);
            if (ret != 0) {
                return false;
            }
            ret = nativeRender(renderer);
            if (ret != 0) {
                return false;
            }
            ret = nativeSaveImage(renderer, 0, -1, -1, outputPath, 0, true);
            return ret == 0;
        } finally {
            nativeReleaseRenderer(renderer);
        }
    }

    // ==================== Stub methods ====================

    public boolean renderBitmap(int[] argb, int width, int height, int inWidth, int inHeight, int rotation) {
        return true;
    }

    public void depthMapIsReady() {}

    public void setProgress(int progress) {}
}
