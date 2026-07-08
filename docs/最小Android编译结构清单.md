# 最小 Android 编译结构清单

> 目标：让 OpenCV 接片最小可运行原型具备最小编译骨架。

---

## 一、项目根目录

```text
opencv_stitch_poc/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── app/
├── stitch-core/
├── stitch-ui/
├── stitch-export/
├── stitch-guard/
└── docs/
```

---

## 二、模块职责

### 1) app
- 入口壳
- 原型首页
- 预览结果展示调用
- 与主项目的跳转桥接

### 2) stitch-core
- OpenCV 接口层
- JNI 桥接占位
- 拼接与纯裁切逻辑

### 3) stitch-ui
- 结果预览
- 裁切控制
- 极简 UI 文案

### 4) stitch-export
- 保存、分享、导出

### 5) stitch-guard
- 隔离守护
- 验证不污染主链

---

## 三、最小 Kotlin 文件清单

### app
- `StitchEntryActivity.kt`
- `StitchSessionViewModel.kt`
- `StitchState.kt`
- `MainActivityBridge.kt`
- `FakeFrameSource.kt`
- `PocPipeline.kt`
- `PocResultStore.kt`

### stitch-core
- `StitchFrame.kt`
- `StitchResult.kt`
- `StitchConfig.kt`
- `OpenCvNativeBridge.kt`
- `OpenCvNativeBridgeStub.kt`
- `OpenCvPipeline.kt`
- `OpenCvStitchAdapter.kt`

### stitch-ui
- `StitchPreviewActivity.kt`
- `StitchResultView.kt`
- `CropController.kt`

### stitch-export
- `ExportManager.kt`

### stitch-guard
- `StitchIsolationGuard.kt`

---

## 四、最小 Android 资源清单

### app/src/main
- `AndroidManifest.xml`
- `res/layout/activity_stitch_entry.xml`
- `res/values/strings.xml`
- `res/values/colors.xml`
- `res/values/themes.xml`

---

## 五、最小编译依赖清单

### app/build.gradle.kts
- `com.android.application`
- `org.jetbrains.kotlin.android`
- `androidx.core:core-ktx`
- `androidx.appcompat:appcompat`
- `com.google.android.material:material`

### 其余模块
- `org.jetbrains.kotlin.android`

---

## 六、建议的最小 UI 资源

### `strings.xml`
- app 名称
- 接片首页标题
- 预览页标题
- 导出按钮文案

### `colors.xml`
- black
- white
- gray
- pcsAccent（淡青或淡琥珀）

### `themes.xml`
- 极简主题
- 无多余装饰

---

## 七、最小编译目标

### 第一目标
- 工程能被 Android Studio / Gradle 识别

### 第二目标
- 主模块能看到启动入口

### 第三目标
- 原型页能读取 `PocResultStore`

### 第四目标
- 预留 JNI / native 接口，不强行实现真实 OpenCV

---

## 八、后续补齐顺序

1. 补 `AndroidManifest.xml`
2. 补 `strings/colors/themes`
3. 补最小启动 Activity
4. 补预览页布局
5. 补导出按钮壳
6. 接入 JNI 占位

---

## 九、当前结论

这个清单的意义在于：

> 让接片原型从“设计文档”进一步变成“可编译工程骨架”。
