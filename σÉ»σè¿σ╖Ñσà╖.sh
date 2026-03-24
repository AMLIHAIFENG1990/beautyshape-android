#!/bin/bash
# 直播调试辅助工具 - macOS 启动脚本
cd "$(dirname "$0")"
echo "🎨 直播调试辅助工具"
echo "   http://localhost:8899"
pip3 install -q flask mediapipe opencv-python-headless pillow numpy 2>/dev/null
python3 web_app.py
