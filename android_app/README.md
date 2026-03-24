# BeautyShape Android App 📱

离线可用的脸型分析安卓应用。

## 功能
- 📷 拍照 / 从相册导入
- 🔍 脸型分析（12种脸型分类）
- 📏 三庭五眼比例分析
- 💡 灯光推荐 + 调试建议
- 💾 经验数据库（本地存储）

## 环境要求

**⚠️ 必须在 Linux 环境构建**（macOS 不支持 Buildozer）

### 方式 1：Docker（最简单）
```bash
cd android_app
docker run --rm -v $(pwd):/home/user/host kivy/buildozer android debug
```

### 方式 2：WSL2 (Windows)
```powershell
# 安装 WSL2
wsl --install -d Ubuntu

# 进入 WSL
wsl
cd /mnt/c/Users/你的用户名/...
bash build.sh
```

### 方式 3：Linux 虚拟机
```bash
# Ubuntu/Debian
bash build.sh
```

### 方式 4：在线构建
上传到 GitHub，用 GitHub Actions 自动构建。

## 构建步骤

```bash
cd android_app
chmod +x build.sh
bash build.sh
```

首次构建需要下载 Android SDK/NDK（约 2-3GB），后续会快很多。

构建完成后：
```
bin/beautyshape-1.0.0-debug.apk
```

## 安装到手机

1. 把 APK 传到手机
2. 设置 → 安全 → 允许未知来源
3. 点击安装

## 文件说明
- `main.py` — Kivy 主程序（UI + 逻辑）
- `face_shape_engine.py` — 脸型分析引擎
- `experience_db.json` — 经验数据库
- `buildozer.spec` — Buildozer 构建配置
- `build.sh` — 一键构建脚本

## 注意
- APK 大小约 80-150MB（含 MediaPipe 模型）
- 首次启动可能需要 5-10 秒加载模型
- 所有数据在手机本地，不联网
