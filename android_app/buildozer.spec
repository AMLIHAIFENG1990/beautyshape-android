[app]
title = BeautyShape
package.name = beautyshape
package.domain = com.beautyshape.app
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0.0
fullscreen = 0
orientation = portrait
requirements = python3,kivy,pillow,opencv-contrib-python-headless,numpy,mediapipe,plyer
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.minapi = 26
android.api = 33
android.ndk = 25b
android.build_tools_version = 34.0.0
android.archs = armeabi-v7a
log_level = 2

[buildozer]
warn_on_root = 1