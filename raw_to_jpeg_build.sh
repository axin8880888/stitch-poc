#!/bin/bash
# 光边界 RawToJpegPipeline — Mac 编译脚本
# 手机端已写好 RawToJpegPipeline.kt，放在 opencv_stitch_poc/ 下
# 在 Mac 上跑这个脚本即可编译 APK

set -e

echo "=== 光边界接片 — RawToJpeg 编译 ==="
echo ""

# 1. 确认环境
echo "检查 JAVA_HOME..."
if [ -z "$JAVA_HOME" ]; then
    export JAVA_HOME=$(/usr/libexec/java_home 2>/dev/null || echo "/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home")
fi
echo "JAVA_HOME=$JAVA_HOME"

echo "检查 ANDROID_HOME..."
if [ -z "$ANDROID_HOME" ]; then
    echo "⚠️  ANDROID_HOME 未设置，请设置或修改路径"
    export ANDROID_HOME=~/Library/Android/sdk
fi
echo "ANDROID_HOME=$ANDROID_HOME"

# 2. 定位项目
PROJECT_DIR=$(dirname "$0")/opencv_stitch_poc
if [ ! -d "$PROJECT_DIR" ]; then
    # 尝试从当前目录找
    PROJECT_DIR=./opencv_stitch_poc
fi
echo "项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 3. 确认 RawToJpegPipeline.kt 已到位
KT_FILE="stitch-core/src/main/java/com/lb/stitch/core/RawToJpegPipeline.kt"
if [ -f "$KT_FILE" ]; then
    echo "✅ RawToJpegPipeline.kt 已就位"
    wc -l "$KT_FILE"
else
    echo "❌ 缺少 $KT_FILE，请先同步手机端的文件"
    exit 1
fi

# 4. 编译
echo ""
echo "=== 开始编译 ==="
./gradlew :app:assembleDebug

# 5. 输出 APK 路径
APK="app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK" ]; then
    echo ""
    echo "✅ 编译成功！"
    echo "APK 路径: $(pwd)/$APK"
    echo "文件大小: $(ls -lh "$APK" | awk '{print $5}')"
else
    echo "❌ 编译失败，APK 未生成"
    exit 1
fi

echo ""
echo "=== 安装测试 ==="
echo "adb install -r $APK"
echo ""
echo "打开 App 后点击「开始接片」触发 RawToJpegTest"
echo "JPG 输出路径: /storage/emulated/0/Download/篮筐整改/ (由 RawToJpegPipeline 生成)"
