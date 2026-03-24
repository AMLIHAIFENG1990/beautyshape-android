[app]
title = BeautyShape
package.name = beautyshape
package.domain = com.beautyshape.app
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0.0

# 全屏
fullscreen = 0

# 方向（竖屏）
orientation = portrait

# 依赖
requirements = python3,kivy,pillow,opencv-contrib-python-headless,numpy,mediapipe,plyer

# Android 权限
android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 最低 API
android.minapi = 26
android.api = 33
android.ndk = 25b

# 图标
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# 日志级别
log_level = 2

[buildozer]
warn_on_root = 1
