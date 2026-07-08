# 真实 OpenCV / JNI 第一段实现草案

## 目标
先把 JNI 第一次真正接上，让 Kotlin → JNI → C++ 的入口链跑通。

## 第一段优先实现

### 1. 初始化会话
- `initNative(workDir, enableBlender=false, enableExposureCompensator=false, cropMode="pure")`

### 2. 准备拼接
- `prepareNative(frameCount, overlapHint, maxDimension)`

### 3. 逐帧送入
- `pushFrameNative(index, imageRef, timestamp, exposureInfo, iso, awb)`

### 4. 执行拼接
- `stitchNative()`

### 5. 裁切建议
- `suggestCropBoundsNative(stitchResultRef, safetyMarginPx=0)`

### 6. 纯裁切
- `applyPureCropNative(stitchResultRef, cropBoundsRef)`

### 7. 写出结果
- `writeResultNative(outputDir, fileName, format="jpeg")`

## 第一段实现原则
- 先跑通通路，不追求完整算法优化
- 先用 stub 替身保证 Kotlin 层可调度
- 先确保状态流与 UI 回写稳定
- 先默认关闭 blending / exposure compensator

## 后续再补
- 特征提取优化
- 匹配优化
- warp 优化
- 边界裁切优化
- 结果写出优化
