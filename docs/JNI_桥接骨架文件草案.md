# JNI 桥接骨架文件草案

## 目标
快速把 Kotlin 与 C++ / OpenCV 打通，形成可替换的桥接层。

---

## 一、文件结构建议

```text
stitch-core/src/main/cpp/
├── CMakeLists.txt
├── native-lib.cpp
├── OpenCvStitchSession.h
├── OpenCvStitchSession.cpp
└── jni_bridge.cpp
```

---

## 二、职责划分

### 1) `native-lib.cpp`
- JNI 入口定义
- 方法注册
- Kotlin 侧方法映射

### 2) `jni_bridge.cpp`
- JNI 与 C++ 会话对象桥接
- 处理参数转换
- 管理 session 指针

### 3) `OpenCvStitchSession.h/.cpp`
- 真正的 OpenCV 拼接会话
- 特征提取 / 匹配 / warp / 裁切 / 输出

### 4) `CMakeLists.txt`
- 编译 native 库
- 连接 OpenCV 依赖

---

## 三、JNI 入口函数建议

```cpp
extern "C" JNIEXPORT jboolean JNICALL
Java_com_lb_stitch_core_NativeBridge_initNative(...)

extern "C" JNIEXPORT jboolean JNICALL
Java_com_lb_stitch_core_NativeBridge_prepareNative(...)

extern "C" JNIEXPORT jboolean JNICALL
Java_com_lb_stitch_core_NativeBridge_pushFrameNative(...)

extern "C" JNIEXPORT jstring JNICALL
Java_com_lb_stitch_core_NativeBridge_stitchNative(...)

extern "C" JNIEXPORT jstring JNICALL
Java_com_lb_stitch_core_NativeBridge_suggestCropBoundsNative(...)

extern "C" JNIEXPORT jstring JNICALL
Java_com_lb_stitch_core_NativeBridge_applyPureCropNative(...)

extern "C" JNIEXPORT jstring JNICALL
Java_com_lb_stitch_core_NativeBridge_writeResultNative(...)

extern "C" JNIEXPORT void JNICALL
Java_com_lb_stitch_core_NativeBridge_releaseNative(...)
```

---

## 四、桥接原则

- Kotlin 只认接口，不碰 native 细节
- native 只做会话与算法
- session 生命周期必须明确
- 导出路径必须可控
- 默认关闭 blending / exposure compensator

---

## 五、最小实现顺序

1. 先写 `OpenCvStitchSession.h/.cpp`
2. 再写 `jni_bridge.cpp`
3. 再写 `native-lib.cpp`
4. 最后补 `CMakeLists.txt`

---

## 六、关键风险点

- JNI 字符串转换
- session 指针释放
- OpenCV 依赖接入方式
- 导出路径权限
- 64 位 ABI 兼容

---

## 七、结论

这套桥接骨架的目的只有一个：

> 让 Android 侧尽快连到 native，先把成品级 APK 的路径打通。
