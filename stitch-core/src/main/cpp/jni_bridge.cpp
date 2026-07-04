#include "OpenCvStitchSession.h"
#include <jni.h>

using namespace lb::stitch;

static OpenCvStitchSession* gSession = nullptr;

static JNINativeMethod gMethods[] = {
    {const_cast<char*>("initNative"), const_cast<char*>("(Ljava/lang/String;ZZLjava/lang/String;)Z"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring workDir, jboolean enableBlender, jboolean enableExposureCompensator, jstring cropMode) -> jboolean {
        (void)env; (void)thiz; (void)workDir; (void)enableBlender; (void)enableExposureCompensator; (void)cropMode;
        if (!gSession) gSession = new OpenCvStitchSession();
        ::lb::stitch::StitchConfig config;
        config.enableBlender = enableBlender;
        config.enableExposureCompensator = enableExposureCompensator;
        config.cropMode = "pure";
        return gSession->init(config) ? JNI_TRUE : JNI_FALSE;
    })},
    {const_cast<char*>("prepareNative"), const_cast<char*>("(III)Z"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jint frameCount, jint overlapHint, jint maxDimension) -> jboolean {
        (void)env; (void)thiz;
        return (gSession && gSession->prepare(frameCount, overlapHint, maxDimension)) ? JNI_TRUE : JNI_FALSE;
    })},
    {const_cast<char*>("pushFrameNative"), const_cast<char*>("(ILjava/lang/String;JLjava/lang/String;ILjava/lang/String;)Z"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jint index, jstring imageRef, jlong timestamp, jstring exposureInfo, jint iso, jstring awb) -> jboolean {
        (void)env; (void)thiz; (void)index; (void)imageRef; (void)timestamp; (void)exposureInfo; (void)iso; (void)awb;
        return (gSession) ? JNI_TRUE : JNI_FALSE;
    })},
    {const_cast<char*>("stitchNative"), const_cast<char*>("()Ljava/lang/String;"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz) -> jstring {
        (void)thiz;
        const std::string out = gSession ? gSession->stitch() : std::string();
        return env->NewStringUTF(out.c_str());
    })},
    {const_cast<char*>("suggestCropBoundsNative"), const_cast<char*>("(Ljava/lang/String;I)Ljava/lang/String;"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring stitchedRef, jint safetyMarginPx) -> jstring {
        (void)thiz; (void)stitchedRef;
        const std::string out = gSession ? gSession->suggestCropBounds("stitched-ref", safetyMarginPx) : std::string();
        return env->NewStringUTF(out.c_str());
    })},
    {const_cast<char*>("applyPureCropNative"), const_cast<char*>("(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring stitchedRef, jstring cropBoundsRef) -> jstring {
        (void)thiz; (void)stitchedRef; (void)cropBoundsRef;
        const std::string out = gSession ? gSession->applyPureCrop("stitched-ref", "crop-bounds-ref") : std::string();
        return env->NewStringUTF(out.c_str());
    })},
    {const_cast<char*>("writeResultNative"), const_cast<char*>("(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring outputDir, jstring fileName, jstring format) -> jstring {
        (void)thiz; (void)outputDir; (void)fileName; (void)format;
        const std::string out = gSession ? gSession->writeResult("/storage/emulated/0/Download/篮筐整改", "stitched_result", "jpeg") : std::string();
        return env->NewStringUTF(out.c_str());
    })},
    {const_cast<char*>("releaseNative"), const_cast<char*>("()V"), reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz) -> void {
        (void)env; (void)thiz;
        if (gSession) { gSession->release(); delete gSession; gSession = nullptr; }
    })}
};

extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK || !env) return JNI_ERR;
    jclass clazz = env->FindClass("com/teleboost/camera/jni/NativeBridge");
    if (!clazz) return JNI_ERR;
    if (env->RegisterNatives(clazz, gMethods, sizeof(gMethods) / sizeof(gMethods[0])) != 0) return JNI_ERR;
    return JNI_VERSION_1_6;
}
