#include "OpenCvStitchSession.h"
#include <jni.h>

using namespace lb::stitch;

static OpenCvStitchSession* gSession = nullptr;

static JNINativeMethod gMethods[] = {
    {const_cast<char*>("initNative"),
     const_cast<char*>("(Ljava/lang/String;ZZLjava/lang/String;)Z"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring workDir,
                                  jboolean enableBlender,
                                  jboolean enableExposureCompensator,
                                  jstring cropMode) -> jboolean {
         const char* utf = env->GetStringUTFChars(workDir, nullptr);
         StitchConfig config;
         config.storePath = utf ? utf : "/tmp";
         config.sessionId = reinterpret_cast<int64_t>(thiz);
         config.blenderEnabled = enableBlender;
         config.exposureCompEnabled = enableExposureCompensator;
         if (utf) env->ReleaseStringUTFChars(workDir, utf);

         if (!gSession) gSession = new OpenCvStitchSession();
         return gSession->init(config) ? JNI_TRUE : JNI_FALSE;
     })},

    {const_cast<char*>("prepareNative"),
     const_cast<char*>("(III)Z"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jint frameCount,
                                  jint overlapHint, jint maxDimension) -> jboolean {
         (void)env; (void)thiz;
         return (gSession && gSession->prepare(frameCount, overlapHint, maxDimension))
                    ? JNI_TRUE
                    : JNI_FALSE;
     })},

    {const_cast<char*>("pushFrameNative"),
     const_cast<char*>("(ILjava/lang/String;JLjava/lang/String;ILjava/lang/String;)Z"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jint index,
                                  jstring imageRef, jlong timestamp,
                                  jstring exposureInfo, jint iso,
                                  jstring awb) -> jboolean {
         (void)thiz; (void)index; (void)timestamp; (void)exposureInfo;
         (void)iso; (void)awb;

         if (!gSession) return JNI_FALSE;

         const char* filePath = env->GetStringUTFChars(imageRef, nullptr);
         if (!filePath) return JNI_FALSE;

         FrameMeta frame;
         frame.filePath = filePath;
         frame.timestamp = timestamp;
         env->ReleaseStringUTFChars(imageRef, filePath);

         return gSession->pushFrame(frame) ? JNI_TRUE : JNI_FALSE;
     })},

    {const_cast<char*>("stitchNative"),
     const_cast<char*>("()Ljava/lang/String;"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz) -> jstring {
         (void)thiz;
         const std::string out = gSession ? gSession->stitch() : std::string();
         return env->NewStringUTF(out.c_str());
     })},

    {const_cast<char*>("suggestCropBoundsNative"),
     const_cast<char*>("(Ljava/lang/String;I)Ljava/lang/String;"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring stitchedRef,
                                  jint safetyMarginPx) -> jstring {
         (void)thiz;
         const char* ref = env->GetStringUTFChars(stitchedRef, nullptr);
         std::string refStr = ref ? ref : "";
         if (ref) env->ReleaseStringUTFChars(stitchedRef, ref);

         const std::string out = gSession
                                     ? gSession->suggestCropBounds(refStr, safetyMarginPx)
                                     : "0,0,0,0";
         return env->NewStringUTF(out.c_str());
     })},

    {const_cast<char*>("applyPureCropNative"),
     const_cast<char*>("(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring stitchedRef,
                                  jstring cropBoundsRef) -> jstring {
         (void)thiz;
         const char* src = env->GetStringUTFChars(stitchedRef, nullptr);
         const char* crop = env->GetStringUTFChars(cropBoundsRef, nullptr);
         std::string srcStr = src ? src : "";
         std::string cropStr = crop ? crop : "";
         if (src) env->ReleaseStringUTFChars(stitchedRef, src);
         if (crop) env->ReleaseStringUTFChars(cropBoundsRef, crop);

         const std::string out =
             gSession ? gSession->applyPureCrop(srcStr, cropStr) : srcStr;
         return env->NewStringUTF(out.c_str());
     })},

    {const_cast<char*>("writeResultNative"),
     const_cast<char*>("(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz, jstring outputDir,
                                  jstring fileName, jstring format) -> jstring {
         (void)thiz;
         const char* dir = env->GetStringUTFChars(outputDir, nullptr);
         const char* name = env->GetStringUTFChars(fileName, nullptr);
         const char* fmt = env->GetStringUTFChars(format, nullptr);
         std::string dirStr = dir ? dir : ".";
         std::string nameStr = name ? name : "stitch_result";
         std::string fmtStr = fmt ? fmt : "jpeg";
         if (dir) env->ReleaseStringUTFChars(outputDir, dir);
         if (name) env->ReleaseStringUTFChars(fileName, name);
         if (fmt) env->ReleaseStringUTFChars(format, fmt);

         const std::string out =
             gSession ? gSession->writeResult(dirStr, nameStr, fmtStr) : "";
         return env->NewStringUTF(out.c_str());
     })},

    {const_cast<char*>("releaseNative"),
     const_cast<char*>("()V"),
     reinterpret_cast<void*>(+[](JNIEnv* env, jobject thiz) -> void {
         (void)env; (void)thiz;
         if (gSession) {
             gSession->release();
             delete gSession;
             gSession = nullptr;
         }
     })}};

extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK || !env)
        return JNI_ERR;

    jclass clazz = env->FindClass("com/teleboost/camera/jni/NativeBridge");
    if (!clazz) return JNI_ERR;

    if (env->RegisterNatives(clazz, gMethods,
                             sizeof(gMethods) / sizeof(gMethods[0])) != 0)
        return JNI_ERR;

    return JNI_VERSION_1_6;
}
