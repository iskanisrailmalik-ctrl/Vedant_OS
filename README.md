# Verdant OS — Android launcher

**Verdant OS is an Android home-screen launcher with an animated nature wallpaper**, designed for Android 12+ and the Moto Edge 50 Fusion. It is delivered as an installable APK, but its product role is the system HOME experience: users can select it as their default launcher and it discovers and launches installed applications.

## Visual implementation

- The home scene uses a high-resolution photographic PNG asset, not custom Canvas-painted illustrations.
- Jetpack Compose animates that PNG with gentle parallax and zoom. Reduce Motion and wind settings control the animation.
- The live wallpaper service uses the same local PNG, composited to Android's wallpaper surface and animated with low-amplitude motion. Canvas is only the platform surface used to blit the bitmap; no hand-painted paths, fruits, leaves, or geometric scenery are drawn.
- App-drawer icons come from Android's installed application packages and use a spring response when pressed.
- The wallpaper is prepared as a local PNG during source assembly; the running launcher does not fetch images from the network.
- The current build process downloads the source photograph from Unsplash under its license: [photo and contributor details](https://unsplash.com/photos/the-sun-is-shining-through-the-trees-in-the-forest-iLGdHvAQHUc).

## Build and verification

The GitHub Actions workflow reconstructs the checked source package, applies the image-first launcher patch, runs static project verification, then runs unit tests, lint and a debug APK build. It also attempts an emulator smoke test that checks Android HOME registration and app launch. A green hosted build is not a substitute for physical-device testing; confirm the default-home flow, app drawer, gestures, widgets, wallpaper motion and restore-to-stock-launcher path on the Moto Edge 50 Fusion before daily use.

Latest source: https://github.com/iskanisrailmalik-ctrl/Vedant_OS
