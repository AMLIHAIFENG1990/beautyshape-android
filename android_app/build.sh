#!/bin/bash
# BeautyShape Android 构建脚本
# 需要在 Linux 或 WSL 环境运行（macOS 不支持 Buildozer）

set -e

echo "🦞 BeautyShape Android 构建"
echo "=============================="

# 检查环境
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "⚠️  macOS 不支持 Buildozer 直接打包"
    echo "请选择："
    echo "  1. 用 Docker 构建（推荐）"
    echo "  2. 用 Linux 虚拟机/WSL"
    echo ""
    echo "Docker 构建命令："
    echo "  docker run --rm -v \$(pwd):/home/user/host kivy/buildozer android debug"
    echo ""
    echo "或者安装 WSL2 (Ubuntu) 后运行此脚本"
    exit 1
fi

# 安装依赖
echo "📦 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv \
    build-essential git zip unzip \
    openjdk-17-jdk autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev

# 安装 buildozer
echo "📦 安装 Buildozer..."
pip3 install --user buildozer cython==0.29.33

# 安装 Android SDK/NDK（首次会自动下载）
echo "📱 准备 Android SDK（首次运行会自动下载，约 2-3GB）..."
echo "   请耐心等待..."

# 构建 APK
echo "🔨 开始构建 APK..."
buildozer android debug

echo ""
echo "✅ 构建完成！"
echo "APK 位置: ./bin/beautyshape-1.0.0-debug.apk"
echo "传输到手机安装即可使用"
