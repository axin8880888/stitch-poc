# 真实 OpenCV / JNI 第二段伪代码草案

> 目标：把第一段通路继续细化成接近实现的伪代码，便于后续直接落 JNI/C++。

---

## 一、JNI 层伪代码

### 1) initNative
```text
function initNative(workDir, enableBlender=false, enableExposureCompensator=false, cropMode="pure"):
    if session exists:
        releaseNative()
    session = new NativeSession()
    session.config.workDir = workDir
    session.config.enableBlender = enableBlender
    session.config.enableExposureCompensator = enableExposureCompensator
    session.config.cropMode = cropMode
    return session.init()
```

### 2) prepareNative
```text
function prepareNative(frameCount, overlapHint=30, maxDimension=4096):
    if session == null:
        return false
    session.prepare(frameCount, overlapHint, maxDimension)
    return true
```

### 3) pushFrameNative
```text
function pushFrameNative(index, imageRef, timestamp, exposureInfo, iso, awb):
    if session == null:
        return false
    frame = FrameMeta(index, imageRef, timestamp, exposureInfo, iso, awb)
    return session.pushFrame(frame)
```

### 4) stitchNative
```text
function stitchNative():
    if session == null:
        return ""
    stitchedRef = session.stitch()
    return stitchedRef
```

### 5) suggestCropBoundsNative
```text
function suggestCropBoundsNative(stitchResultRef, safetyMarginPx=0):
    if session == null:
        return ""
    return session.suggestCropBounds(stitchResultRef, safetyMarginPx)
```

### 6) applyPureCropNative
```text
function applyPureCropNative(stitchResultRef, cropBoundsRef):
    if session == null:
        return ""
    return session.applyPureCrop(stitchResultRef, cropBoundsRef)
```

### 7) writeResultNative
```text
function writeResultNative(outputDir, fileName, format="jpeg"):
    if session == null:
        return ""
    return session.writeResult(outputDir, fileName, format)
```

### 8) releaseNative
```text
function releaseNative():
    if session != null:
        session.release()
        session = null
```

---

## 二、C++ 侧伪代码

### 1) init
```text
method init(config):
    store config
    allocate working buffers
    create OpenCV context
    return true
```

### 2) prepare
```text
method prepare(frameCount, overlapHint, maxDimension):
    if frameCount < 2:
        add warning "frame count too low"
    reserve frame container
    set overlapHint and maxDimension
    return true
```

### 3) pushFrame
```text
method pushFrame(frame):
    validate frame meta
    append to frame list
    return true
```

### 4) stitch
```text
method stitch():
    features = extractFeatures(frames)
    matches = matchFeatures(features)
    geometry = estimateGeometry(matches)
    warped = warpFrames(frames, geometry)
    if config.enableExposureCompensator:
        applyExposureCompensator(warped)
    if config.enableBlender:
        blendFrames(warped)
    result = buildStitchedResult(warped)
    return result.ref
```

### 5) suggestCropBounds
```text
method suggestCropBounds(stitchResultRef, safetyMarginPx):
    bounds = detectSafeBounds(stitchResultRef)
    shrink by safetyMarginPx
    return bounds.ref
```

### 6) applyPureCrop
```text
method applyPureCrop(stitchResultRef, cropBoundsRef):
    crop = cropImage(stitchResultRef, cropBoundsRef)
    return crop.ref
```

### 7) writeResult
```text
method writeResult(outputDir, fileName, format):
    ensure directory exists
    encode and save image
    return saved path
```

### 8) release
```text
method release():
    clear frames
    clear buffers
    destroy OpenCV context
```

---

## 三、状态回写建议

### 结果对象更新时机
- `stitchNative()` 完成后：写 `status=stitched`
- `applyPureCropNative()` 完成后：写 `cropStatus=applied`
- `writeResultNative()` 完成后：写 `exportStatus=done`

### 预览页刷新时机
- `PocResultStore.save()` 后立即刷新
- 裁切按钮后立即刷新
- 导出按钮后立即刷新

---

## 四、后续可直接落地的接口签名块

### Kotlin
- `OpenCvNativeBridge`
- `OpenCvPipeline`
- `PocResultStore`

### JNI
- `Java_xxx_initNative`
- `Java_xxx_prepareNative`
- `Java_xxx_pushFrameNative`
- `Java_xxx_stitchNative`
- `Java_xxx_suggestCropBoundsNative`
- `Java_xxx_applyPureCropNative`
- `Java_xxx_writeResultNative`
- `Java_xxx_releaseNative`

### C++
- `OpenCvStitchSession::init`
- `OpenCvStitchSession::prepare`
- `OpenCvStitchSession::pushFrame`
- `OpenCvStitchSession::stitch`
- `OpenCvStitchSession::suggestCropBounds`
- `OpenCvStitchSession::applyPureCrop`
- `OpenCvStitchSession::writeResult`
- `OpenCvStitchSession::release`

---

## 五、结论

这份第二段伪代码的意义是：

> 让 OpenCV / JNI 接口从“签名草案”推进到“实现路线图”。

后面如果继续，就可以直接开始写 JNI 桥接骨架和 C++ 头文件骨架。
