# 🎨 直播调试辅助工具

基于 MediaPipe FaceMesh 的脸型分析 & 打光推荐工具。

## 功能

- 📐 **脸型分类**：12种脸型（鹅蛋/圆形/方形/瓜子/心形/甲字/菱形/长形/梨形/倒三角/方圆/国字）
- 📏 **三庭五眼**：自动检测并标注偏差
- 💡 **打光推荐**：根据脸型推荐灯光配置
- ✂️ **框选截取**：截屏后拖拽选区
- 📚 **经验库**：手动修正标签，积累标准数据

## 快速开始

### macOS
```bash
bash 启动工具.sh
# 或
pip3 install flask mediapipe opencv-python-headless pillow numpy
python3 web_app.py
```

### Windows
```cmd
双击 启动工具.bat
# 或
pip install flask mediapipe opencv-python-headless pillow numpy
python web_app.py
```

### 打包成 exe
```cmd
python build_exe.py
# 输出 dist/直播调试工具.exe
```

## 浏览器打开

http://localhost:8899

## 依赖

- Python 3.9+
- Flask
- MediaPipe
- OpenCV
- NumPy
- Pillow

## 文件说明

| 文件 | 说明 |
|------|------|
| web_app.py | 主程序（Flask Web） |
| face_shape_engine.py | 脸型分析引擎 v4 |
| experience_db.json | 经验数据库（自动生成） |
| build_exe.py | PyInstaller 打包脚本 |
| 启动工具.bat | Windows 启动脚本 |
| 启动工具.sh | macOS 启动脚本 |
