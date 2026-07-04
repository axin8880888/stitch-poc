# OpenCV / JNI 接口签名草案

## 设计目标
将接片能力拆为可控 JNI 接口，后续由 Kotlin 调度、C++/OpenCV 执行。

## 接口签名

### initNative
```text
initNative(workDir: String, enableBlender: Boolean = false, enableExposureCompensator: Boolean = false, cropMode: String = "pure"): Boolean
```
职责：初始化一次接片会话。

### prepareNative
```text
prepareNative(frameCount: Int, overlapHint: Int = 30, maxDimension: Int = 4096): Boolean
```
职责：准备拼接环境。

### pushFrameNative
```text
pushFrameNative(index: Int, imageRef: String, timestamp: Long, exposureInfo: String?, iso: Int?, awb: String?): Boolean
```
职责：逐帧送入原始素材引用。

### stitchNative
```text
stitchNative(): String
```
职责：执行几何拼接，返回结果引用。

### suggestCropBoundsNative
```text
suggestCropBoundsNative(stitchResultRef: String, safetyMarginPx: Int = 0): String
```
职责：给出纯裁切建议。

### applyPureCropNative
```text
applyPureCropNative(stitchResultRef: String, cropBoundsRef: String): String
```
职责：执行纯裁切。

### writeResultNative
```text
writeResultNative(outputDir: String, fileName: String, format: String = "jpeg"): String
```
职责：写出结果文件。

## 默认约束
- blending 默认关闭
- exposure compensator 默认关闭
- 只做几何对齐与纯裁切
- 不进入光边界主拍照链
