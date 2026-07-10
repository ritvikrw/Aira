pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // Required by the LiveKit Android SDK's transitive dependencies.
        maven { url = uri("https://jitpack.io") }
    }
}

rootProject.name = "AIRA"
include(":app")
