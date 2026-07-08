#!/usr/bin/env bash
# ============================================================
# MacBook Air 一键构建脚本 — 光·边界 接片模块
# 用法: bash build_apk.sh [release|debug]
# ============================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_TYPE="${1:-debug}"
APK_DIR="${PROJECT_DIR}/app/build/outputs/apk/${BUILD_TYPE}"

echo "=============================================="
echo "光·边界 接片 — APK 构建"
echo "项目目录: ${PROJECT_DIR}"
echo "构建类型: ${BUILD_TYPE}"
echo "=============================================="

# --- 1. 环境检查 ---
echo ""
echo "[1/5] 检查环境..."

# Java
if ! command -v java &>/dev/null; then
    echo "❌ 需要 Java 17+ (brew install openjdk@17)"
    exit 1
fi
JAVA_VER=$(java -version 2>&1 | head -1 | sed 's/.*"\(.*\)".*/\1/')
echo "   Java: ${JAVA_VER}"

# Android SDK
if [ -z "${ANDROID_HOME:-}" ]; then
    if [ -d "$HOME/Library/Android/sdk" ]; then
        export ANDROID_HOME="$HOME/Library/Android/sdk"
        echo "   ANDROID_HOME 自动检测: ${ANDROID_HOME}"
    else
        echo "❌ 请设置 ANDROID_HOME 环境变量"
        echo "   建议: export ANDROID_HOME=\$HOME/Library/Android/sdk"
        exit 1
    fi
fi
echo "   SDK: ${ANDROID_HOME}"

# OpenCV SDK
if [ -z "${OPENCV_SDK_DIR:-}" ]; then
    # 常见位置
    for dir in "$HOME/opencv-android-sdk" "$HOME/OpenCV-android-sdk" /usr/local/opencv-android-sdk; do
        if [ -d "$dir" ]; then
            export OPENCV_SDK_DIR="$dir"
            break
        fi
    done
fi

if [ -z "${OPENCV_SDK_DIR:-}" ]; then
    echo "⚠️  未检测到 OpenCV Android SDK，JNI native 层将不可用"
    echo "   下载: https://github.com/opencv/opencv/releases/tag/4.10.0"
    echo "   解压后设置: export OPENCV_SDK_DIR=/path/to/OpenCV-android-sdk"
    echo ""
    echo "   继续纯 Java 层编译（无 native 拼接）..."
    BUILD_NATIVE=false
else
    echo "   OpenCV: ${OPENCV_SDK_DIR}"
    BUILD_NATIVE=true
fi

# --- 2. 生成 local.properties ---
echo ""
echo "[2/5] 配置 local.properties..."
cat > "${PROJECT_DIR}/local.properties" <<PROP
sdk.dir=${ANDROID_HOME}
ndk.dir=${ANDROID_HOME}/ndk/25.2.9519653
PROP

if [ "$BUILD_NATIVE" = true ]; then
    echo "opencv.sdk.dir=${OPENCV_SDK_DIR}" >> "${PROJECT_DIR}/local.properties"
fi
echo "   ✅ local.properties 已生成"

# --- 3. 清理 ---
echo ""
echo "[3/5] 清理旧构建..."
cd "${PROJECT_DIR}"
./gradlew clean --no-daemon > /dev/null 2>&1 || true
echo "   ✅ 清理完成"

# --- 4. 构建 ---
echo ""
echo "[4/5] 开始构建 APK..."
BUILD_FLAGS=""
if [ "$BUILD_TYPE" = "release" ]; then
    BUILD_FLAGS="assembleRelease"
else
    BUILD_FLAGS="assembleDebug"
fi

echo "   正在编译...（可能需要 2-5 分钟）"
set +e
BUILD_OUTPUT=$(./gradlew ${BUILD_FLAGS} --no-daemon 2>&1)
BUILD_EXIT=$?
set -e

if [ $BUILD_EXIT -ne 0 ]; then
    echo "❌ 构建失败! 错误信息:"
    echo "${BUILD_OUTPUT}" | tail -40
    exit 1
fi
echo "   ✅ 构建成功"

# --- 5. 签名 & 输出 ---
echo ""
echo "[5/5] 检查 APK 输出..."

APK_FILE=""
if [ "$BUILD_TYPE" = "release" ]; then
    APK_FILE=$(find "${APK_DIR}" -name "app-release-unsigned.apk" 2>/dev/null | head -1)
    if [ -n "$APK_FILE" ]; then
        SIGNED_APK="${APK_FILE%.apk}_signed.apk"
        echo "   签名 APK..."
        # debug 签名（开发测试用）
        if [ -f "${PROJECT_DIR}/debug.keystore" ]; then
            jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
                -keystore "${PROJECT_DIR}/debug.keystore" \
                -storepass android -keypass android \
                "${APK_FILE}" androiddebugkey 2>/dev/null || true
        fi
    fi
else
    APK_FILE=$(find "${APK_DIR}" -name "*.apk" 2>/dev/null | head -1)
fi

if [ -n "$APK_FILE" ]; then
    APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
    echo ""
    echo "=============================================="
    echo "✅ 构建完成!"
    echo "   APK: ${APK_FILE}"
    echo "   大小: ${APK_SIZE}"
    echo "=============================================="
    echo ""
    echo "安装到设备: adb install -r \"${APK_FILE}\""
else
    echo "⚠️  未找到 APK 文件，请检查 ${APK_DIR}"
fi

echo ""
echo "--- 构建详情 ---"
echo "${BUILD_OUTPUT}" | grep -E "(BUILD|ASSEMBLE|install)" | tail -5 || true
