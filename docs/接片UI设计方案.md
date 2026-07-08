# 光·边界 接片模式 UI 设计方案

版本：v0.1 设计提案
目标：P0 — 点击接片 → 进入真实预览 → 拍第一张 JPG → Session 记录

---

## 一、交互流程

```
[主相机界面]
    │
    ├── 快门按钮 → 正常拍照 (DNG+JPG)
    │
    └── 「接片」入口按钮 → 进入 Stitch Mode
             │
             ▼
    [Stitch Camera Preview]
         │                    ┌──────────────────┐
         │  ├─ 取景器 (真实 CameraX 预览)       │
         │  ├─ 叠层: 当前帧/总帧 (如 1/5)      │
         │  ├─ 叠层: 接片方向指示条            │
         │  ├─ 叠层: 重叠引导线 (半透明网格)    │
         │  └─ 底部: 快门 + 取消                │
         │
         ├── 拍 N 帧 → Session 管理
         │       ↓
         │   每拍一张:
         │   1. CameraEngine → captureStill()
         │   2. JPG → Session.frameN.jpg
         │   3. 缩略图 → 接片轨道上
         │   4. 震动/音效反馈
         │
         └── 「完成」→ 进入拼接流程 (P2 阶段)
```

---

## 二、UI 布局 (垂直方向, 全面屏)

```
┌────────────────────────────┐
│  Status Bar (半透明)       │
├────────────────────────────┤
│                            │
│   ┌──── 取景器 ──────┐    │
│   │   (CameraX 全屏)   │    │
│   │                    │    │
│   │   ═══ 重叠引导线 ═══  │    │
│   │                    │    │
│   │                    │    │
│   └────────────────────┘    │
│                            │
│  ┌──────────────────────┐  │
│  │ [1/5]  ←→  [3/5]    │  │ ← 缩略图轨道
│  │ 缩略1 缩略2 缩略3    │  │
│  └──────────────────────┘  │
│                            │
│  [取消]       [◎快门]    │
│                 [✓ 完成]   │
└────────────────────────────┘
```

### 2.1 关键 UI 元素

| 元素 | 位置 | 说明 |
|------|------|------|
| 取景器 | 全屏 | 复用 CameraEngine 预览 Surface |
| 重叠引导线 | 取景器内 | 半透明垂直线，提示上一帧边界 |
| 帧计数 | 左上角 | "3/8" 简洁 |
| 缩略图轨道 | 底部上方 | 已拍帧的 JPG 缩略图，可滚动 |
| 快门按钮 | 底部中央 | 大圆按钮 |
| 完成按钮 | 底部右侧 | 足够帧数后才激活 |
| 取消 | 底部左侧 | 退回到主相机 |

### 2.2 状态

```
IDLE → PREVIEWING → CAPTURING → CAPTURED → COLLECTED → (完成/取消)

- IDLE: 初始态，未进入 Stitch Mode
- PREVIEWING: 取景器运行中
- CAPTURING: 按下快门，等待 ImageReader 回调
- CAPTURED: 单帧写入 Session 成功
- COLLECTED: 收集到足够帧数，完成按钮可用
```

---

## 三、模块结构 (Camera → Stitch)

```
CameraViewModel (现有)
  │
  ├── capturePhoto()          ← 正常快门
  │
  └── captureStitchFrame()    ← 接片快门 (新增)
        │
        ▼
CameraEngine.captureStill()
        │
        ▼
ImageReader → processCapturedImage
        │
        ▼
CameraViewModel.processAndSavePhoto()
        │
        ├── JPG → saveToGallery() [现有]
        │
        └── StitchSession.addFrame() [新增]
              │
              ▼
        Session 存储:
        - frame_001.jpg
        - frame_002.jpg
        - ...
        - session.json (元数据)
```

### 3.1 StitchSession 设计

```kotlin
class StitchSession(
    val sessionId: String = UUID.randomUUID().toString(),
    val outputDir: File,
    val frames: MutableList<StitchFrame> = mutableListOf()
) {
    fun addFrame(jpgBytes: ByteArray, timestamp: Long, lensInfo: String): Int {
        val index = frames.size + 1
        val file = File(outputDir, "frame_%03d.jpg".format(index))
        file.writeBytes(jpgBytes)
        frames.add(StitchFrame(index, file, timestamp, lensInfo))
        return index
    }

    val frameCount: Int get() = frames.size
    val isComplete: Boolean get() = frameCount >= MIN_FRAMES
}
```

---

## 四、需要修改/新增的文件

### 新增
| 文件 | 职责 |
|------|------|
| `StitchCameraScreen.kt` | 接片模式 UI (Compose) |
| `StitchViewModel.kt` | 接片状态管理 |
| `StitchSession.kt` | Session 管理 (已存在 StitchSession.kt 参考) |
| `StitchOverlay.kt` | 重叠引导线绘制 |
| `FrameThumbnailStrip.kt` | 缩略图轨道组件 |

### 修改
| 文件 | 修改 |
|------|------|
| `CameraViewModel.kt` | 新增 `captureStitchFrame()` |
| `CameraEngine.kt` | 接片模式下的目标输出判断 |
| `CameraScreen.kt` | 新增「接片」入口按钮 |

---

## 五、边界条件

| 情况 | 处理 |
|------|------|
| 帧数不够就点完成 | 按钮置灰，提示"至少 N 帧" |
| 中途退出 | 清空当前 Session，回到主相机 |
| 拍摄时相机断开 | 自动保存已拍帧，提示用户 |
| 快速连拍 | `isProcessing` 防止重复提交 |
| 存储空间不足 | 拍照前检查，不足时警告 |
| 多焦段切换 | 每帧记录当前 lens info |

---

## 六、P0 验收标准

- [ ] 主相机界面有「接片」入口按钮
- [ ] 点击进入接片预览模式，CameraEngine 正常预览
- [ ] 点击快门 → 拍照 → JPG 写入 Session → 缩略图显示
- [ ] 帧数递增显示 (1/N)
- [ ] 取消 → 清理并回到主相机
- [ ] 不崩溃，不退相机

---

## 七、后续阶段

| 阶段 | 内容 |
|------|------|
| P0 | ✅ 上述验收标准 |
| P1 | 连续拍 frame1→2→3，Session 完整 |
| P2 | OpenCV 拼接输出全景 |
| P3 | 裁切 / 导出 / 分享 |
