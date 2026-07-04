#include "OpenCvStitchSession.h"

namespace lb::stitch {

bool OpenCvStitchSession::init(const StitchConfig& config) { (void)config; return true; }
bool OpenCvStitchSession::prepare(int frameCount, int overlapHint, int maxDimension) { (void)frameCount; (void)overlapHint; (void)maxDimension; return true; }
bool OpenCvStitchSession::pushFrame(const FrameMeta& frame) { (void)frame; return true; }
std::string OpenCvStitchSession::stitch() { return "stitched-ref"; }
std::string OpenCvStitchSession::suggestCropBounds(const std::string& stitchedRef, int safetyMarginPx) { (void)stitchedRef; (void)safetyMarginPx; return "crop-bounds-ref"; }
std::string OpenCvStitchSession::applyPureCrop(const std::string& stitchedRef, const std::string& cropBoundsRef) { (void)stitchedRef; (void)cropBoundsRef; return "cropped-ref"; }
std::string OpenCvStitchSession::writeResult(const std::string& outputDir, const std::string& fileName, const std::string& format) { return outputDir + "/" + fileName + "." + format; }
void OpenCvStitchSession::setBlenderEnabled(bool enabled) { (void)enabled; }
void OpenCvStitchSession::setExposureCompensatorEnabled(bool enabled) { (void)enabled; }
void OpenCvStitchSession::release() {}

} // namespace lb::stitch
