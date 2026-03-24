@echo off
REM 直播调试辅助工具 - Windows 启动脚本
REM 首次运行会自动安装依赖
echo.
echo ================================
echo   直播调试辅助工具
echo ================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+
    echo    下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 安装依赖
echo 📦 检查依赖...
pip install -q flask mediapipe opencv-python-headless pillow numpy

REM 启动
echo.
echo ✅ 启动中...
echo    浏览器将自动打开 http://localhost:8899
echo    按 Ctrl+C 退出
echo.
python web_app.py
pause
