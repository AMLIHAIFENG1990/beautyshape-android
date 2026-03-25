[app]
title = BeautyShape
package.name = beau tyshape
package.domain = com.beautyshape.app
 source.dir = .
source.include_exts = py,png,j pg,kv,json
version = 1.0.0

# 全屏
fullscre en = 0

# 方向（竖屏）
orientation = po rtrait

# 依赖
requirements = python3,kivy, pillow,opencv-contrib-python-headless,numpy,m ediapipe,plyer

# Android 权限
android.perm issions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_ EXTERNAL_STORAGE

# 最低 API
android.build_tools_version = 34.0.0
android.minapi  = 26
android.api = 33
android.ndk = 25b

# � ��标
# icon.filename = %(source.dir)s/icon.p ng
# presplash.filename = %(source.dir)s/pres plash.png

# 日志级别
log_level = 2

[bui ldozer]
warn_on_root = 1
 