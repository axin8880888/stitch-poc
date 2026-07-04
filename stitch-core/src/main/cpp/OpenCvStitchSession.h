#pragma once

#include <string>
#include <vector>

namespace lb::stitch {

struct FrameMeta {
    int index = 0;
    std::string imageRef;
    long long timestamp = 0;
    std::string exposureInfo;
    int iso = 0;
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
