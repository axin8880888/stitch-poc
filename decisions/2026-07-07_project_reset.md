# 光·边界 接片项目重构决定（Project Reset）

日期：2026-07-07

状态：执行

---

## 一、决定

终止当前 Stitch POC（空壳）路线。

原因：当前工程已经偏离光·边界母版。继续开发投入与最终目标不一致。
即日起停止在 Stitch POC 上继续增加任何功能。

## 二、为什么重构

经过连续多天开发及测试，确认当前 APK 实际完成内容主要为：
✓ UI / Activity / 假帧演示 / OpenCV 占位 / Stitch POC

未完成内容：
✗ CameraEngine 接入 / 真机预览 / 真机拍照 / JPG 采集 / Session / 真正接片

当前属于 Proof Of Concept，而不是光·边界真正的 Stitch。

## 三、不推倒的内容（全部保留）

绝不重做：
35mm / 70mm / 230mm / CameraEngine / 曝光系统 / AE / ISO / TeleStab / JPG / DNG / PCS / Overlay / UI / 镜头系统
这些全部属于成熟成果，继续作为唯一母版。

## 四、推倒内容

完全停止：
Stitch POC / FakeFrame / Fake Stitch / 假预览 / 演示 Activity / OpenCV Placeholder / 独立 Stitch APK
这些全部归档，以后不再继续修改。

## 五、新架构

唯一架构：
光·边界 → CameraEngine → 真实拍照 → Session → OpenCV → 输出

不是 Stitch → Camera
而是 Camera → Stitch

这是整个项目最大的架构调整。

## 六、开发原则

以后每一次提交只能完成一个目标。
任何版本禁止同时修改多个模块。

## 七、第一阶段目标（P0）

点击"接片" → 进入光·边界真实预览 → CameraEngine 正常工作 → 可以拍第一张 JPG → Session 成功记录 frame1.jpg
完成即收工，禁止继续开发第二阶段。

## 八、第二阶段（P1）

连续拍摄 frame1 → frame2 → frame3，全部进入 Session。仍然禁止拼接。

## 九、第三阶段（P2）

验证 OpenCV：Align → Warp → Blend → 生成第一张真正 Panorama。

## 十、开发纪律

① 母版永远只有一个
② 不重新造相机
③ CameraEngine 永远唯一
④ Stitch 永远只是模块
⑤ 每版只完成一个目标
⑥ 真机验证成功再进入下一阶段

## 十一、项目目标

最终不是做一个接片 APP，而是做拥有专业接片能力的《光·边界》。
接片只是能力。光·边界才是主体。

## 十二、执行状态

Stitch POC：终止。
光·边界母版：继续作为唯一开发基线。
新 Stitch：从 CameraEngine 模块开始重新接入。
状态：READY。
