plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "org.compass.wasmer.mobile"
    compileSdk = 34

    defaultConfig {
        applicationId = "org.compass.wasmer.mobile"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.12.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
}

afterEvaluate {
    tasks.named("preBuild").configure {
        dependsOn("syncCompassAssets")
    }
}

tasks.register("syncCompassAssets") {
    doLast {
        val script = rootProject.projectDir.resolve("../sync-assets.sh")
        val pb = ProcessBuilder("bash", script.absolutePath)
            .directory(rootProject.projectDir)
            .inheritIO()
        val code = pb.start().waitFor()
        if (code != 0) {
            throw GradleException("sync-assets.sh exited $code")
        }
    }
}
