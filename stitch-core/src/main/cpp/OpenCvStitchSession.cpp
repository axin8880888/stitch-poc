#include "OpenCvStitchSession.h"
#include <opencv2/stitching.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/core.hpp>
#include <android/log.h>
#include <sstream>
#include <cstdlib>

#define LOG_TAG "OpenCvStitchSession"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace lb::stitch {

namespace {
    std::string storeDir;
    std::vector<cv::Mat> frames;
    bool blenderEnabled = false;
    bool exposureCompEnabled = false;
    int64_t sessionId = 0;
}

bool OpenCvStitchSession::init(const StitchConfig& config) {
    LOGI("init() session=%lld", (long long)config.sessionId);
    storeDir = config.storePath;
    sessionId = config.sessionId;
    blenderEnabled = config.blenderEnabled;
    exposureCompEnabled = config.exposureCompEnabled;
    frames.clear();
    return true;
}

bool OpenCvStitchSession::prepare(int frameCount, int overlapHint, int maxDimension) {
    LOGI("prepare: %d frames, overlap=%d, maxDim=%d", frameCount, overlapHint, maxDimension);
    frames.reserve(frameCount);
    return true;
}

bool OpenCvStitchSession::pushFrame(const FrameMeta& frame) {
    cv::Mat img = cv::imread(frame.filePath, cv::IMREAD_COLOR);
    if (img.empty()) {
        LOGE("pushFrame: failed to load %s", frame.filePath.c_str());
        return false;
    }
    // 缩放到合理大小（最大长边2048）
    int maxDim = 2048;
    if (img.cols > maxDim || img.rows > maxDim) {
        double scale = (double)maxDim / std::max(img.cols, img.rows);
        cv::Mat small;
        cv::resize(img, small, cv::Size(), scale, scale, cv::INTER_AREA);
        frames.push_back(small);
    } else {
        frames.push_back(img.clone());
    }
    LOGI("pushFrame #%zu: %s (%dx%d)", frames.size(), frame.filePath.c_str(),
         frames.back().cols, frames.back().rows);
    return true;
}

std::string OpenCvStitchSession::stitch() {
    LOGI("stitch: %zu frames", frames.size());
    if (frames.size() < 2) {
        LOGE("need >=2 frames");
        return "";
    }

    cv::Ptr<cv::Stitcher> stitcher = cv::Stitcher::create(cv::Stitcher::SCANS);

    // 默认关闭融合和曝光补偿
    if (blenderEnabled) {
        stitcher->setBlender(cv::detail::Blender::createDefault(cv::detail::Blender::MULTI_BAND));
    } else {
        stitcher->setBlender(cv::detail::Blender::createDefault(cv::detail::Blender::NO));
    }

    if (exposureCompEnabled) {
        stitcher->setExposureCompensator(cv::detail::ExposureCompensator::createDefault(
            cv::detail::ExposureCompensator::GAIN_BLOCKS));
    } else {
        stitcher->setExposureCompensator(cv::detail::ExposureCompensator::createDefault(
            cv::detail::ExposureCompensator::NO));
    }

    // 只做几何对齐
    stitcher->setPanoConfidenceThresh(0.6);
    stitcher->setSeamEstimationResol(0.001);
    stitcher->setSeamFinder(cv::detail::SeamFinder::createDefault(cv::detail::SeamFinder::NO));
    stitcher->setWaveCorrection(false);

    cv::Mat pano;
    cv::Stitcher::Status status = stitcher->stitch(frames, pano);

    if (status != cv::Stitcher::OK) {
        LOGE("stitch failed: status=%d", status);
        return "";
    }

    LOGI("stitch OK: pano=%dx%d", pano.cols, pano.rows);

    std::string outPath = storeDir + "/stitch_" + std::to_string(sessionId) + "_pano.jpg";
    cv::imwrite(outPath, pano, {cv::IMWRITE_JPEG_QUALITY, 95});
    LOGI("saved: %s", outPath.c_str());
    frames.clear();
    return outPath;
}

std::string OpenCvStitchSession::suggestCropBounds(
    const std::string& stitchedRef, int safetyMarginPx) {
    LOGI("suggestCropBounds: safetyMargin=%d", safetyMarginPx);
    cv::Mat pano = cv::imread(stitchedRef, cv::IMREAD_COLOR);
    if (pano.empty()) return "0,0,0,0";

    cv::Mat gray;
    cv::cvtColor(pano, gray, cv::COLOR_BGR2GRAY);
    cv::Mat mask = gray > 0;

    int top = 0, bottom = pano.rows, left = 0, right = pano.cols;
    for (int y = 0; y < pano.rows; y++)
        if (cv::countNonZero(mask.row(y)) > pano.cols * 0.1) { top = y; break; }
    for (int y = pano.rows - 1; y >= 0; y--)
        if (cv::countNonZero(mask.row(y)) > pano.cols * 0.1) { bottom = y; break; }
    for (int x = 0; x < pano.cols; x++)
        if (cv::countNonZero(mask.col(x)) > pano.rows * 0.1) { left = x; break; }
    for (int x = pano.cols - 1; x >= 0; x--)
        if (cv::countNonZero(mask.col(x)) > pano.rows * 0.1) { right = x; break; }

    top = std::max(0, top - safetyMarginPx);
    bottom = std::min(pano.rows, bottom + safetyMarginPx);
    left = std::max(0, left - safetyMarginPx);
    right = std::min(pano.cols, right + safetyMarginPx);

    return std::to_string(left) + "," + std::to_string(top) + "," +
           std::to_string(right) + "," + std::to_string(bottom);
}

std::string OpenCvStitchSession::applyPureCrop(
    const std::string& stitchedRef, const std::string& cropBoundsRef) {
    cv::Mat pano = cv::imread(stitchedRef, cv::IMREAD_COLOR);
    if (pano.empty()) return stitchedRef;

    int left, top, right, bottom;
    sscanf(cropBoundsRef.c_str(), "%d,%d,%d,%d", &left, &top, &right, &bottom);
    cv::Rect roi(left, top, right - left, bottom - top);
    cv::Mat cropped = pano(roi).clone();

    std::string outPath = storeDir + "/stitch_" + std::to_string(sessionId) + "_final.jpg";
    cv::imwrite(outPath, cropped, {cv::IMWRITE_JPEG_QUALITY, 95});
    return outPath;
}

std::string OpenCvStitchSession::writeResult(
    const std::string& outputDir, const std::string& fileName, const std::string& format) {
    return outputDir + "/" + fileName + "." + format;
}

void OpenCvStitchSession::setBlenderEnabled(bool enabled) {
    blenderEnabled = enabled;
    LOGI("blender=%d", blenderEnabled);
}

void OpenCvStitchSession::setExposureCompensatorEnabled(bool enabled) {
    exposureCompEnabled = enabled;
    LOGI("exposureComp=%d", exposureCompEnabled);
}

void OpenCvStitchSession::release() {
    LOGI("release");
    frames.clear();
}

} // namespace lb::stitch
