#!/usr/bin/env python3
"""
直播调试辅助工具 - Windows 打包脚本
使用方法：
  1. 在 Windows 上安装 Python 3.9+
  2. pip install flask mediapipe opencv-python-headless pillow numpy pyinstaller
  3. python build_exe.py
  4. 输出 dist/直播调试工具.exe
"""
import subprocess
import sys
import os

def install_deps():
    deps = [
        'flask>=3.0',
        'mediapipe>=0.10',
        'opencv-python-headless>=4.8',
        'pillow>=10.0',
        'numpy>=1.24',
        'pyinstaller>=6.0',
    ]
    print("📦 安装依赖...")
    for dep in deps:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', dep])

def build():
    here = os.path.dirname(os.path.abspath(__file__))
    entry = os.path.join(here, 'web_app.py')
    
    # 收集数据文件
    datas = []
    for f in ['face_shape_engine.py', 'experience_db.json', 'face_shape_calibration.json']:
        fp = os.path.join(here, f)
        if os.path.exists(fp):
            datas.append(f'--add-data={fp};.')
    
    # MediaPipe 模型文件
    mp_path = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages', 'mediapipe')
    if os.path.exists(mp_path):
        datas.append(f'--add-data={mp_path};mediapipe')
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name=直播调试工具',
        '--icon=NONE',
        '--noconsole',
        '--clean',
        '--hidden-import=cv2',
        '--hidden-import=mediapipe',
        '--hidden-import=mediapipe.python.solutions',
        '--hidden-import=mediapipe.python.solutions.face_mesh',
        '--hidden-import=PIL',
        '--hidden-import=flask',
        '--hidden-import=numpy',
        '--collect-all=mediapipe',
        '--collect-all=cv2',
        *datas,
        entry,
    ]
    
    print("🔨 打包中...")
    print(' '.join(cmd))
    subprocess.check_call(cmd)
    
    dist = os.path.join(here, 'dist')
    exe = os.path.join(dist, '直播调试工具.exe')
    if os.path.exists(exe):
        size_mb = os.path.getsize(exe) / 1024 / 1024
        print(f"\n✅ 打包成功！")
        print(f"   📁 {exe}")
        print(f"   📏 {size_mb:.0f} MB")
        print(f"\n使用：双击运行，自动打开浏览器 http://localhost:8899")

if __name__ == '__main__':
    install_deps()
    build()
