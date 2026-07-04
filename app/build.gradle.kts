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
}

dependencies {
    implementation(project(":stitch-core"))
    implementation(project(":stitch-ui"))
    implementation(project(":stitch-export"))
    implementation(project(":stitch-guard"))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
}
