plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.teleboost.camera"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.teleboost.camera"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1"
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(project(":stitch-core"))
    implementation(project(":stitch-ui"))
    implementation(project(":stitch-export"))
    implementation(project(":stitch-guard"))
    // 注意：不要引入 appcompat 或 material，否则会与原始 APK 的 Compose 版本冲突
    // 所有 stitch Activity 直接继承 android.app.Activity
}
