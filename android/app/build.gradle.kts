plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "org.methodmeshenger.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.methodmeshenger.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

dependencies {
    implementation(project(":methodmeshenger-secure"))
}
