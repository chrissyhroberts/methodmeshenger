plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "org.methodmeshenger.secure"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }
}

// Native Rust packaging is intentionally added by the eventual host app once
// its NDK/toolchain and keystore policy are fixed.
