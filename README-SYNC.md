# 状态同步快照 — 2026-07-06 13:52 GMT+8

## 当前来源设备
- **设备**: Android (Arm64)
- **项目路径**: `/storage/emulated/0/Download/篮筐整改/opencv_stitch_poc/`

## 已完成的工作

### 1. 闪退修复
- `StitchEntryActivity.onCreate()` 不再直接跑 `pipeline.run(frames)`
- 改成：只起壳、写默认 PocResult、不自动拼接
- 避免首帧启动导致闪退

### 2. 最小闭环链路
- 启动页已加 **"开始接片"** 按钮（程序化 UI）
- 点按钮后：写入一份伪结果（FakeFrameSource）→ 预览/裁切/导出状态可追
- 三个核心helper已补齐：
  - `stitch-ui` → `CropController` / `StitchPreviewActivity` / `StitchResultView`
  - `stitch-export` → `ExportManager`
  - `stitch-guard` → `StitchIsolationGuard`

### 3. 依赖精简
- 移除了 `androidx.core:core-ktx` / `appcompat` / `material`
- 主题使用 `@android:style/Theme.Black.NoTitleBar.Fullscreen`
- `app/build.gradle.kts` 不再引用外部 AAR → 避免 AAPT2 解包 issues

### 4. 编译验证
- `:stitch-core:compileDebugKotlin` ✅
- `:stitch-ui:compileDebugKotlin` ✅
- `:stitch-export:compileDebugKotlin` ✅
- `:stitch-guard:compileDebugKotlin` ✅
- `:app:compileDebugKotlin` ✅（需要 -x processDebugResources 绕过 AAPT2）

### 5. 当前阻断
- **AAPT2**: Android SDK 的 `build-tools/34.0.0/aapt2` 是 x86_64 ELF
- 当前 arm64 环境无法直接运行
- qemu-user-x86_64 已安装，但缺少 x86_64 glibc（ld-linux-x86-64.so.2）
- 所以 `:app:processDebugResources` 无法执行

## 关键改动文件清单（相对于 git base）

```
M app/build.gradle.kts                          # 移除外部 AAR 依赖
M app/src/main/java/.../StitchEntryActivity.kt  # 重写启动链 + 按钮 + 伪结果
M app/src/main/res/layout/activity_stitch_entry.xml
M app/src/main/res/layout/activity_stitch_preview.xml
M stitch-ui/src/.../CropController.kt            # 补齐实现（原 TODO）
M stitch-ui/src/.../StitchPreviewActivity.kt     # 补齐实现（原 TODO）
M stitch-ui/src/.../StitchResultView.kt          # 补齐实现（原 TODO）
M stitch-export/src/.../ExportManager.kt         # 补齐实现（原 TODO）
M stitch-guard/src/.../StitchIsolationGuard.kt   # 补齐实现（原 TODO）
```

## MacBook Air 上需要做的事

如果你想在这边打 APK，需要在 MacBook Air 上：

1. 把 `/storage/emulated/0/Download/篮筐整改/opencv_stitch_poc/` 按原路径复制过去
2. 确保 MacBook Air 上 Android SDK 完整（aapt2 arm64/universal 就可用）
3. 运行：
   ```bash
   cd opencv_stitch_poc
   ANDROID_HOME=~/Library/Android/sdk ./gradlew :app:assembleDebug
   ```

**预计结果**：一个不闪退、能进壳、点按钮出伪结果的接片演示 APK。

---

*以上是 Android 端会话已完成的状态。复制此文件给 MacBook Air 上的我，即可自动恢复上下文。*
