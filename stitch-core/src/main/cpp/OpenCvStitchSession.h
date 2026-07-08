#ifndef OPENCV_STITCH_SESSION_H
#define OPENCV_STITCH_SESSION_H

#include <string>
#include <vector>

namespace lb::stitch {

struct FrameMeta {
    std::string filePath;   // 图像文件路径
    int64_t timestamp;      // 拍摄时间戳
    float rotation;         // 旋转角度（度）
    float exposure;         // 曝光补偿值（EV）
};

struct StitchConfig {
    std::string storePath;  // 临时存储目录
    int64_t sessionId;      // 会话 ID
    bool blenderEnabled = false;
    bool exposureCompEnabled = false;
};

class OpenCvStitchSession {
public:
    bool init(const StitchConfig &config);
    bool prepare(int frameCount, int overlapHint, int maxDimension);
    bool pushFrame(const FrameMeta &frame);
    std::string stitch();
    std::string suggestCropBounds(const std::string &stitchedRef, int safetyMarginPx);
    std::string applyPureCrop(const std::string &stitchedRef, const std::string &cropBoundsRef);
    std::string writeResult(const std::string &outputDir, const std::string &fileName, const std::string &format);
    void setBlenderEnabled(bool enabled);
    void setExposureCompensatorEnabled(bool enabled);
    void release();
};

} // namespace lb::stitch

#endif // OPENCV_STITCH_SESSION_H
