# OpenCV / C++ 原生侧函数草案

> 与 Kotlin/JNI 层接口签名一一对应。
> 目标：只做几何接片与纯裁切，默认关闭 blending 与 exposure compensator。

---

## 一、头文件草案

```cpp
#pragma once
#include <string>
#include <vector>

namespace lb::stitch {

struct FrameMeta {
    int index;
    std::string imageRef;
    long long timestamp;
    std::string exposureInfo;
    int iso;
    std::string awb;
};

struct StitchConfig {
    std::string workDir;
    bool enableBlender = false;
    bool enableExposureCompensator = false;
    std::string cropMode = "pure";
    int overlapHint = 30;
    int maxDimension = 4096;
};

struct CropBounds {
    int left;
    int top;
    int right;
    int bottom;
};

struct StitchResult {
    std::string stitchedRef;
    std::string cropBoundsRef;
    std::string outputRef;
    float qualityScore = 0.f;
    std::vector<std::string> warnings;
};

class OpenCvStitchSession {
public:
    bool init(const StitchConfig& config);
    bool prepare(int frameCount, int overlapHint, int maxDimension);
    bool pushFrame(const FrameMeta& frame);
    std::string stitch();
    std::string suggestCropBounds(const std::string& stitchedRef, int safetyMarginPx = 0);
    std::string applyPureCrop(const std::string& stitchedRef, const std::string& cropBoundsRef);
    std::string writeResult(const std::string& outputDir, const std::string& fileName, const std::string& format = "jpeg");
    void setBlenderEnabled(bool enabled);
    void setExposureCompensatorEnabled(bool enabled);
    void release();
};

} // namespace lb::stitch
```

---

## 二、源文件职责划分

### 1) `init`
- 初始化 OpenCV 环境
- 配置工作目录
- 锁定拼接模式
- 默认关闭 blending / exposure compensator

### 2) `prepare`
- 分配内部缓冲
- 记录帧数和拼接参数
- 校验最小帧数

### 3) `pushFrame`
- 接收单帧素材引用
- 记录元信息
- 进入待拼接缓存

### 4) `stitch`
- 特征提取
- 特征匹配
- 相机位姿估计
- warp
- 输出拼接结果引用

### 5) `suggestCropBounds`
- 计算纯裁切边界
- 输出安全裁切框

### 6) `applyPureCrop`
- 只裁切外圈毛边
- 不做羽化
- 不做 blending

### 7) `writeResult`
- 写出最终文件
- 返回保存路径或结果引用

---

## 三、内部算法模块草案

```text
OpenCvStitchSession
├── FeatureExtractor
├── Matcher
├── CameraEstimator
├── Warper
├── CropBoundarySolver
└── ResultWriter
```

### FeatureExtractor
- 提取特征点与描述子

### Matcher
- 进行帧间匹配
- 计算重叠质量

### CameraEstimator
- 估计几何关系
- 生成对齐模型

### Warper
- 执行投影变换
- 生成拼接 canvas

### CropBoundarySolver
- 只计算裁切边界
- 不参与融合

### ResultWriter
- 输出 JPEG / PNG
- 维护结果路径

---

## 四、默认配置约束

- `enableBlender = false`
- `enableExposureCompensator = false`
- `cropMode = "pure"`
- `overlapHint = 30`
- `maxDimension = 4096`

---

## 五、JNI 对应关系

| Kotlin/JNI | C++ |
|---|---|
| `initNative()` | `init()` |
| `prepareNative()` | `prepare()` |
| `pushFrameNative()` | `pushFrame()` |
| `stitchNative()` | `stitch()` |
| `suggestCropBoundsNative()` | `suggestCropBounds()` |
| `applyPureCropNative()` | `applyPureCrop()` |
| `writeResultNative()` | `writeResult()` |
| `releaseNative()` | `release()` |

---

## 六、实现原则

1. 只做几何接片。
2. 默认关闭 blending。
3. 默认关闭 exposure compensator。
4. 裁切只做纯裁切。
5. 不污染光边界主拍照链。

---

## 七、结论

这个 C++ 草案已经把 native 侧的职责切干净了：

- Kotlin 管调度
- JNI 管桥接
- C++/OpenCV 管几何拼接与裁切

这样后续真正落地时，结构会很稳。
