# 光·边界 接片模块架构分析（供 K3 深度分析用）

## 反编译来源
跳转版解码_v3 — apktool 反编译的光·边界 APK
包名：com.teleboost.camera

---

## 一、现有 stitch 模块（smali_classes7）

### 目录结构
```
com/teleboost/camera/stitch/
├── StitchEntryActivity           → 老的独立入口 Activity（纯 demo）
├── StitchPreviewActivity         → 预览页
├── PocResultStore                → 结果存储
├── PocResult                     → 结果数据类
├── core/
│   ├── FrameCollector            ← ★ 核心：帧采集引擎
│   ├── OpenCvPipeline            → OpenCV 管线
│   ├── OpenCvStitchAdapter       → JNI 桥接
│   ├── OpenCvNativeBridge        → native 接口定义
│   ├── OpenCvNativeBridgeStub    → native stub
│   ├── StitchConfig              → 配置参数（13字段）
│   ├── StitchFrame               → 帧数据模型
│   ├── StitchResult              → 接片结果
│   ├── CapturePolicy             → 采集策略（曝光锁定/帧验证）
│   └── LockController            → AE/AF 锁定控制
├── ui/
│   ├── CropController            → 裁切
│   └── StitchResultView          → 结果展示
├── export/
│   └── ExportManager             → 导出管理
└── guard/
    └── StitchIsolationGuard      → 隔离保护
```

### FrameCollector 关键字段
- `config: StitchConfig`
- `policy: CapturePolicy`
- `_state: CollectionState` (IDLE/PREVIEWING/CAPTURING/CAPTURED/COLLECTED)
- `callback: CollectorCallback`
- `lockController: LockController`
- `capturedFrames: List<StitchFrame>`
- `imageReader: ImageReader`
- `cameraDevice: CameraDevice`
- `captureSession: CameraCaptureSession`
- `sequenceCounter: AtomicInteger`

### FrameCollector 关键方法
- `startCollecting(device, sensorSize, imageFormat)` — 直连 Camera2 API
- `stopCollecting()` / `cancelCollecting()` / `reset()`
- `getFrames(): List<StitchFrame>` / `getFrameCount(): Int`
- `onImageAvailable(reader)` — ImageReader 回调
- `buildFrameFromImage(image): StitchFrame`
- `checkBrightness(image): Boolean`
- `convertImageToBytes(image): ByteArray`

### LockController 关键方法
- `startLocking(session, templateRequest, onComplete)` — 开始曝光/AF 锁定
- `releaseLock(session, templateRequest)`
- `forceLock(result)` — 强制锁定
- `validateCapturedFrame(result): Boolean`
- `sendConvergeRequest(session, templateRequest, onComplete)`
- `sendLockedRequest(session, templateRequest, onComplete)`

### CapturePolicy 字段
- `lockExposure: Boolean`
- `lockWhiteBalance: Boolean`
- `lockedIso: Int?`
- `noiseReductionMode: Int` (CameraMetadata.NR_MODE_*)
- `edgeMode: Int` (CameraMetadata.EDGE_MODE_*)
- `convergenceWaitMs: Long` (默认 1500ms)
- `stableFrameCount: Int`

### StitchConfig 字段
- `blendEnabled: Boolean`
- `exposureCompensationEnabled: Boolean`
- `cropMode: String` (默认 "pure")
- `overlapHint: Int` (默认 30%)
- `outputFormat: String` (默认 "jpeg")
- OpenCV 参数: featuresType(orb), matcherType(homography), warperType(spherical), estimatorType(homography), bundleAdjusterType(ray)
- `maxDimension: Int` (4096), `jpegQuality: Int` (97), `writeExif: Boolean` (true)
- 两个预设: HONEST_DEFAULT, WITH_BLEND_REFERENCE

### StitchFrame 字段
- `bitmap: Any?` — 帧图像数据
- `timestamp: Long`
- `exposureInfo: String?`
- `iso: Int?`
- `awb: String?`
- `sequenceIndex: Int`

### StitchEntryActivity
纯 demo Activity: 显示 "Stitch Camera" 标题 + 3 个按钮（Start Collection, Preview & Export）
**没有接入 CameraEngine，是独立占位**

---

## 二、CameraViewModel（smali_classes4, 4243 行）

### 包名
`com.teleboost.camera.CameraViewModel`

### 已存在的 toggle 方法（模式）
1. `toggleEis()` — 切换 EIS，操作 stabilizationEngine.start()/stop()
2. `toggleFaceDetection()` — 切换人脸检测，调 cameraEngine.setFaceDetectionMode()
3. `toggleGridOverlay()` — 网格线开关
4. `toggleMirror()` — 镜像翻转
5. `togglePortraitMode()` — 人像模式
6. `toggleTeleLensOverlayState()` — 长焦叠层

### ❌ 未存在的
**toggleStitchMode()** — 还没有！这是 P0 需要加的。

### 关键状态字段（使用 MutableState 委托）
```
portraitMode$delegate       → togglePortraitMode()
faceDetectionMode$delegate  → toggleFaceDetection()
eisEnabled$delegate         → toggleEis()
mirrorEnabled$delegate      → toggleMirror()
gridOverlayEnabled$delegate → toggleGridOverlay()
streetCaptureMode$delegate  → toggleStreetCaptureMode()（在 CameraEngine 中）
```

### 其他关键字段
- `cameraEngine: CameraEngine`
- `stabilizationEngine: StabilizationEngine`
- `portraitEngine: PortraitEngine`
- `colorProcessor: ColorProcessor`
- `detailEnhancer: DetailEnhancer`
- `photoScope: CoroutineScope`
- `textureView: TextureView`
- `previewSize: Size?`
- `isProcessing: Boolean`

---

## 三、CameraScreenKt（smali_classes5, 22136 行）

### 函数列表
1. `CameraScreen(viewModel, composer, changed)` — 主 Composable（第387行）
2. `FeatureToggleItem(label, emoji, enabled, onToggle)` — 可复用 toggle 组件
3. `ColorPresetSelector(currentPreset, onPresetSelected, modifier)` — 色彩预设选择器
4. `ProControlPanel(controls, capabilities, onControlChanged)` — 专业控制面板

### CameraScreen 内部状态
- `captureJustCompleted: MutableState<Boolean>` — 拍照完成标志
- `streetCaptureMode: MutableState<Boolean>` — 街拍模式
- `portraitMode` / `faceDetectionMode` 等

### UI 结构（从源码注释可知）
CameraScreen 约在 36-383 行 Kotlin 源码中定义
- 使用了 Compose 框架
- 布局含 TextureView（相机预览）、FeatureToggleItem 等
- FeatureToggleItem 模式：label + emoji + enabled toggle

---

## 四、架构缺口分析

### 当前问题
1. **StitchEntryActivity 是独立占位**，没有接入 CameraEngine
2. **CameraViewModel 缺少 stitchMode state 和 toggleStitchMode()**
3. **CameraScreenKt 缺少 stitch UI 入口**
4. **FrameCollector 直连 Camera2 API**，应该改为通过 CameraEngine/CameraBridge 委托
5. **已有模块间没有串起来** — FrameCollector / LockController / CapturePolicy 各自独立

### P0 要做的事（按顺序）
1. CameraViewModel: 加 `stitchMode` state + `toggleStitchMode()`
2. CameraScreenKt: 加接片入口按钮，stitchMode UI 切换（隐藏预设栏、显示引导线）
3. CameraEngine bridge: stitch 模式下的拍照走 StitchCameraBridge
4. FrameCollector 集成: 接入真实预览 Surface 而非独立 Camera2 会话
5. Session 管理: 每拍一帧存 JPG + 记录元数据

### P1 要做的事
1. 连续帧采集（frame1→frame2→frame3）
2. Session 持久化
3. 缩略图轨道显示

### P2 要做的事
1. OpenCV Align→Warp→Blend
2. 全景输出
