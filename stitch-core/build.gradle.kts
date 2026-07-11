plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.teleboost.camera.stitch.core"
    ndkVersion = "25.2.9519653"
    compileSdk = 34
    defaultConfig {
        minSdk = 26
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
        // 预置空 .so，跳过 cmake native 构建（Android 手机无法运行 x86_64 cmake）
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }
    buildFeatures {
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    // JNI 原生构建（已禁用——手机环境无法运行 x86_64 cmake，使用预置空 .so）
    // externalNativeBuild {
    //     cmake {
    //         path = file("CMakeLists.txt")
    //         version = "3.22.1"
    //     }
    // }
}

dependencies {
    implementation("androidx.annotation:annotation:1.7.0")
}
