# 光·边界 — 接片模块 MacBook Air 构建指南

## 前置依赖

### 1. Android SDK
```bash
# 通过 Android Studio 安装 (默认路径 ~/Library/Android/sdk)
# 或者用 brew:
brew install --cask android-platform-tools

# 确保以下组件已安装:
# - Android SDK Platform 34
# - NDK 25.2.9519653
# - CMake 3.22.1+
```

### 2. OpenCV Android SDK (可选，用于 native 拼接)
```bash
# 下载 OpenCV 4.10.0 Android SDK
wget https://github.com/opencv/opencv/releases/download/4.10.0/opencv-4.10.0-android-sdk.zip
unzip opencv-4.10.0-android-sdk.zip -d ~/opencv-android-sdk

# 设置环境变量
export OPENCV_SDK_DIR=~/opencv-android-sdk
```

### 3. Java 17
```bash
brew install openjdk@17
export JAVA_HOME=/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
```

## 构建

### 一键构建 (推荐)
```bash
# 调试版
bash build_apk.sh debug

# 发布版
bash build_apk.sh release
```

### 手动构建
```bash
cd /path/to/opencv_stitch_poc
./gradlew assembleDebug
```

## 安装
```bash
# 找到 APK
ls app/build/outputs/apk/debug/*.apk

# 安装到已连接设备
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## 项目结构
```
opencv_stitch_poc/
├── app/                          # 主应用壳
│   └── src/main/java/.../
│       ├── StitchEntryActivity.kt   # 接片入口 Activity
│       ├── StitchSessionViewModel.kt # 接片 Session 管理
│       ├── MainActivityBridge.kt    # 桥接到主相机
│       ├── FakeFrameSource.kt       # 测试用伪数据源
│       ├── PocPipeline.kt           # 测试用 pipeline
│       └── StitchState.kt           # 状态枚举
├── stitch-core/                  # 核心拼接逻辑
│   ├── CMakeLists.txt            # JNI 构建配置
│   ├── src/main/java/.../core/
│   │   ├── StitchConfig.kt       # 拼接配置（红线约束在此）
│   │   ├── CapturePolicy.kt      # 采集策略
│   │   ├── LockController.kt     # AE/AWB 锁定器
│   │   ├── FrameCollector.kt     # 帧采集器
│   │   ├── OpenCvPipeline.kt     # 拼接 pipeline
│   │   ├── OpenCvStitchAdapter.kt # 拼接适配器
│   │   ├── OpenCvNativeBridge.kt # JNI 接口定义
│   │   ├── NativeBridge.kt       # JNI 桥接类
│   │   ├── StitchFrame.kt        # 帧数据类型
│   │   └── StitchResult.kt       # 结果数据类型
│   └── src/main/cpp/
│       ├── NativeBridge.cpp      # JNI RegisterNatives
│       ├── OpenCvStitchSession.* # OpenCV Stitch 引擎封装
│       └── native-lib.cpp        # 空壳保留
├── stitch-ui/                    # UI 层
│   ├── CropController.kt         # 裁切控制
│   ├── StitchPreviewActivity.kt  # 预览 Activity
│   └── StitchResultView.kt       # 结果展示 View
├── stitch-export/                # 导出层
│   └── ExportManager.kt          # 导出（相册/文件/分享）
└── stitch-guard/                 # 隔离层
    └── StitchIsolationGuard.kt   # 运行时红线校验
```

## 红线约束
- Blender (融合) 默认关闭
- ExposureCompensator 默认关闭
- 不修改原始像素
- 接片独立线程运行
- AE_LOCK + AWB_LOCK 锁定采集
