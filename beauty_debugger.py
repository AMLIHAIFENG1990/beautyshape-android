#!/usr/bin/env python3
"""
直播调试辅助工具 - 脸型分析 & 打光推荐
基于「三庭五眼」框架 + 灯光图谱

功能：
  1. 屏幕截图/摄像头捕获/导入图片
  2. 人脸检测 + 68 关键点定位
  3. 三庭五眼比例分析
  4. 脸型自动分类（12种）
  5. 打光方案推荐（6-11灯配置）
  6. 调试思路建议

依赖: opencv-python, mediapipe, numpy, Pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageGrab
import os
import sys
import json
import math

# ============================================================
# 核心分析引擎
# ============================================================

class FaceAnalyzer:
    """人脸分析引擎 - 使用 MediaPipe FaceMesh"""
    
    # 三庭五眼关键点索引 (MediaPipe FaceMesh 468 点)
    # 三庭：上庭（发际线-眉心）、中庭（眉心-鼻底）、下庭（鼻底-下巴）
    # 五眼：左外眼角-左内眼角-两眼间-右内眼角-右外眼角
    
    LANDMARK_INDICES = {
        # 三庭参考点
        'forehead_top': 10,        # 额头顶部
        'hairline': 10,            # 发际线（近似）
        'brow_center': 9,          # 眉心
        'nose_bottom': 2,          # 鼻底
        'chin': 152,               # 下巴
        
        # 五眼参考点
        'left_eye_outer': 33,      # 左眼外角
        'left_eye_inner': 133,     # 左眼内角
        'right_eye_inner': 362,    # 右眼内角
        'right_eye_outer': 263,    # 右眼外角
        
        # 脸型参考点
        'left_cheek': 234,         # 左脸颊
        'right_cheek': 454,        # 右脸颊
        'jaw_left': 172,           # 下颌左
        'jaw_right': 397,          # 下颌右
        'jaw_center': 152,         # 下颌中心
        'left_temple': 70,         # 左太阳穴
        'right_temple': 300,       # 右太阳穴
        
        # 鼻子
        'nose_tip': 1,             # 鼻尖
        'nose_left': 129,          # 鼻翼左
        'nose_right': 358,         # 鼻翼右
        
        # 嘴巴
        'mouth_left': 61,          # 嘴角左
        'mouth_right': 291,        # 嘴角右
        'mouth_top': 13,           # 上唇中
        'mouth_bottom': 14,        # 下唇中
        
        # 眉毛
        'left_brow_inner': 70,     # 左眉头
        'left_brow_outer': 107,    # 左眉尾
        'right_brow_inner': 300,   # 右眉头
        'right_brow_outer': 336,   # 右眉尾
    }
    
    # 12种脸型定义
    FACE_SHAPES = {
        '鹅蛋脸': {'desc': '最标准脸型，线条流畅', 'width_ratio': 0.7, 'jaw_angle': 'rounded'},
        '圆形脸': {'desc': '脸型短圆，显得可爱', 'width_ratio': 0.8, 'jaw_angle': 'round'},
        '方形脸': {'desc': '下颌角明显，有气场', 'width_ratio': 0.75, 'jaw_angle': 'square'},
        '长形脸': {'desc': '脸型偏长，需横向修饰', 'width_ratio': 0.6, 'jaw_angle': 'rounded'},
        '心形脸': {'desc': '下巴尖，额头宽', 'width_ratio': 0.65, 'jaw_angle': 'pointed'},
        '菱形脸': {'desc': '颧骨突出，额头下巴窄', 'width_ratio': 0.68, 'jaw_angle': 'pointed'},
        '梨形脸': {'desc': '下颌宽，额头窄', 'width_ratio': 0.72, 'jaw_angle': 'wide'},
        '国字脸': {'desc': '棱角分明，偏方正', 'width_ratio': 0.78, 'jaw_angle': 'square'},
        '申字脸': {'desc': '中间宽两头窄', 'width_ratio': 0.7, 'jaw_angle': 'pointed'},
        '甲字脸': {'desc': '上窄下宽', 'width_ratio': 0.73, 'jaw_angle': 'wide'},
        '由字脸': {'desc': '上宽下窄', 'width_ratio': 0.67, 'jaw_angle': 'narrow'},
        '目字脸': {'desc': '整体偏窄长', 'width_ratio': 0.55, 'jaw_angle': 'narrow'},
    }
    
    def __init__(self):
        self.mp_face_mesh = None
        self.face_mesh = None
        self._init_mediapipe()
    
    def _init_mediapipe(self):
        """初始化 MediaPipe"""
        import mediapipe as mp
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
    
    def detect_face(self, image):
        """检测人脸并返回关键点"""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            return None
        
        landmarks = results.multi_face_landmarks[0]
        h, w = image.shape[:2]
        
        # 转换为像素坐标
        points = {}
        for name, idx in self.LANDMARK_INDICES.items():
            if idx < len(landmarks.landmark):
                lm = landmarks.landmark[idx]
                points[name] = (int(lm.x * w), int(lm.y * h))
        
        # 获取全部468个点（用于可视化）
        all_points = []
        for lm in landmarks.landmark:
            all_points.append((int(lm.x * w), int(lm.y * h)))
        
        return {
            'points': points,
            'all_points': all_points,
            'landmarks': landmarks,
            'image_size': (w, h)
        }
    
    def analyze_three_courts(self, face_data):
        """三庭分析"""
        p = face_data['points']
        
        required = ['brow_center', 'nose_bottom', 'chin']
        if not all(k in p for k in required):
            return None
        
        # 三庭高度
        brow_y = p['brow_center'][1]
        nose_y = p['nose_bottom'][1]
        chin_y = p['chin'][1]
        
        upper = brow_y - 0  # 上庭（从图片顶部到眉心，实际应从发际线算）
        middle = nose_y - brow_y  # 中庭
        lower = chin_y - nose_y  # 下庭
        total = chin_y
        
        if total == 0:
            return None
        
        # 标准比例：三庭等分
        upper_ratio = upper / total
        middle_ratio = middle / total
        lower_ratio = lower / total
        
        # 判断是否标准（偏差 < 5% 为标准）
        ideal = 1/3
        upper_diff = abs(upper_ratio - ideal)
        middle_diff = abs(middle_ratio - ideal)
        lower_diff = abs(lower_ratio - ideal)
        
        issues = []
        suggestions = []
        
        if upper_ratio < ideal - 0.05:
            issues.append(f"上庭偏短 ({upper_ratio:.1%})")
            suggestions.append("• 发型：露额头或蓬松头顶拉长上庭")
            suggestions.append("• 打光：额头上方加发灯提亮")
        elif upper_ratio > ideal + 0.05:
            issues.append(f"上庭偏长 ({upper_ratio:.1%})")
            suggestions.append("• 发型：刘海遮盖额头缩短上庭")
            suggestions.append("• 打光：减少额头光照")
        
        if middle_ratio < ideal - 0.05:
            issues.append(f"中庭偏短 ({middle_ratio:.1%})")
            suggestions.append("• 修容：鼻子高光拉长中庭")
        elif middle_ratio > ideal + 0.05:
            issues.append(f"中庭偏长 ({middle_ratio:.1%})")
            suggestions.append("• 打光：面部中部柔光减少阴影")
            suggestions.append("• 妆容：腮红位置下移")
        
        if lower_ratio < ideal - 0.05:
            issues.append(f"下庭偏短 ({lower_ratio:.1%})")
            suggestions.append("• 打光：下巴下方补光")
        elif lower_ratio > ideal + 0.05:
            issues.append(f"下庭偏长 ({lower_ratio:.1%})")
            suggestions.append("• 打光：下巴阴影减弱")
            suggestions.append("• 妆容：下唇下方加重阴影")
        
        is_standard = len(issues) == 0
        
        return {
            'upper': upper_ratio,
            'middle': middle_ratio,
            'lower': lower_ratio,
            'is_standard': is_standard,
            'issues': issues,
            'suggestions': suggestions
        }
    
    def analyze_five_eyes(self, face_data):
        """五眼分析"""
        p = face_data['points']
        
        required = ['left_eye_outer', 'left_eye_inner', 'right_eye_inner', 'right_eye_outer']
        if not all(k in p for k in required):
            return None
        
        left_outer = p['left_eye_outer'][0]
        left_inner = p['left_eye_inner'][0]
        right_inner = p['right_eye_inner'][0]
        right_outer = p['right_eye_outer'][0]
        
        # 五眼宽度
        eye1 = left_inner - left_outer         # 左外侧
        eye2 = left_inner - left_inner  # = 0 placeholder
        eye_width_left = right_inner - left_inner  # 中间（两眼间距）
        eye_width = (left_inner - left_outer + right_outer - right_inner) / 2  # 单眼宽度
        eye3 = right_outer - right_inner       # 右外侧
        
        # 更精确的五眼
        w1 = left_inner - left_outer           # 左眼宽度
        w2 = right_inner - left_inner          # 两眼间距
        w3 = right_outer - right_inner         # 右眼宽度
        
        total_width = right_outer - left_outer
        if total_width == 0:
            return None
        
        # 标准五眼：5等分
        ideal_eye = total_width / 5
        
        r1 = w1 / ideal_eye  # 左眼比例
        r2 = w2 / ideal_eye  # 两眼间距比例（应为1个眼宽）
        r3 = w3 / ideal_eye  # 右眼比例
        
        # 实际占比
        left_ratio = w1 / total_width
        gap_ratio = w2 / total_width
        right_ratio = w3 / total_width
        
        issues = []
        suggestions = []
        
        if gap_ratio > 0.25:
            issues.append(f"两眼间距偏宽 ({gap_ratio:.1%})")
            suggestions.append("• 妆容：内眼角眼线拉近")
            suggestions.append("• 打光：鼻梁高光连接两眼")
        elif gap_ratio < 0.15:
            issues.append(f"两眼间距偏窄 ({gap_ratio:.1%})")
            suggestions.append("• 妆容：外眼角眼线拉长")
            suggestions.append("• 打光：眼侧阴影增加宽度感")
        
        if abs(left_ratio - right_ratio) > 0.05:
            issues.append("左右眼不对称")
            suggestions.append("• 妆容：通过眼线微调平衡")
            suggestions.append("• 打光：较小一侧加强眼周光")
        
        is_standard = len(issues) == 0
        
        return {
            'left_eye': left_ratio,
            'gap': gap_ratio,
            'right_eye': right_ratio,
            'is_standard': is_standard,
            'issues': issues,
            'suggestions': suggestions
        }
    
    def classify_face_shape(self, face_data):
        """脸型分类"""
        p = face_data['points']
        
        required = ['left_cheek', 'right_cheek', 'chin', 'brow_center', 
                     'left_temple', 'right_temple', 'jaw_left', 'jaw_right']
        if not all(k in p for k in required):
            return None
        
        # 脸部宽度（脸颊）
        face_width = p['right_cheek'][0] - p['left_cheek'][0]
        # 脸部高度
        face_height = p['chin'][1] - p['brow_center'][1]
        # 额头宽度
        forehead_width = p['right_temple'][0] - p['left_temple'][0]
        # 下颌宽度
        jaw_width = p['jaw_right'][0] - p['jaw_left'][0]
        
        if face_height == 0 or face_width == 0:
            return None
        
        # 关键比率
        width_height_ratio = face_width / face_height
        forehead_face_ratio = forehead_width / face_width
        jaw_face_ratio = jaw_width / face_width
        jaw_forehead_ratio = jaw_width / forehead_width if forehead_width > 0 else 1
        
        # 下颌角度（通过下颌点计算）
        jaw_left = np.array(p['jaw_left'])
        jaw_right = np.array(p['jaw_right'])
        jaw_center = np.array(p['chin'])
        
        v1 = jaw_left - jaw_center
        v2 = jaw_right - jaw_center
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        jaw_angle_deg = math.degrees(math.acos(np.clip(cos_angle, -1, 1)))
        
        # 分类逻辑
        shape = self._classify_by_ratios(
            width_height_ratio, forehead_face_ratio, 
            jaw_face_ratio, jaw_angle_deg, jaw_forehead_ratio
        )
        
        return {
            'shape': shape,
            'face_width': face_width,
            'face_height': face_height,
            'width_height_ratio': width_height_ratio,
            'forehead_ratio': forehead_face_ratio,
            'jaw_ratio': jaw_face_ratio,
            'jaw_angle': jaw_angle_deg,
            'description': self.FACE_SHAPES.get(shape, {}).get('desc', '')
        }
    
    def _classify_by_ratios(self, wh_ratio, forehead_r, jaw_r, jaw_angle, jaw_forehead):
        """根据比率分类脸型"""
        # 长脸
        if wh_ratio < 0.6:
            return '长形脸'
        # 目字脸（极窄）
        if wh_ratio < 0.55:
            return '目字脸'
        
        # 方形/国字脸（下颌角度大）
        if jaw_angle > 140 and jaw_r > 0.7:
            if jaw_forehead > 0.95:
                return '方形脸'
            else:
                return '国字脸'
        
        # 心形脸（下巴尖，额头宽）
        if jaw_angle < 110 and jaw_forehead < 0.8:
            return '心形脸'
        
        # 菱形脸（颧骨突出）
        if forehead_r < 0.65 and jaw_r < 0.65:
            return '菱形脸'
        
        # 梨形脸（下颌宽）
        if jaw_forehead > 1.1:
            return '梨形脸'
        
        # 申字脸（中间宽）
        if forehead_r < 0.7 and jaw_r < 0.7:
            return '申字脸'
        
        # 甲字脸（上窄下宽）
        if jaw_forehead > 1.05 and jaw_r > forehead_r:
            return '甲字脸'
        
        # 由字脸（上宽下窄）
        if jaw_forehead < 0.85 and forehead_r > jaw_r:
            return '由字脸'
        
        # 圆脸
        if wh_ratio > 0.75 and jaw_angle > 130:
            return '圆形脸'
        
        # 鹅蛋脸（标准）
        if 0.65 <= wh_ratio <= 0.75 and 100 <= jaw_angle <= 130:
            return '鹅蛋脸'
        
        # 默认
        if wh_ratio > 0.75:
            return '圆形脸'
        return '鹅蛋脸'
    
    def get_lighting_recommendations(self, face_shape, three_court, five_eye):
        """根据分析结果推荐灯光方案"""
        recommendations = []
        
        shape = face_shape['shape'] if face_shape else '鹅蛋脸'
        
        # 基础灯光配置
        base_lights = {
            '鹅蛋脸': {
                'config': '9灯正面光',
                'lights': [
                    '主灯×2：AE200+方形柔光箱（正面45°）',
                    '发灯×2：AE200+球形柔光箱（顶光后方）',
                    '轮廓灯×2：AE200+长条柔光箱（侧后方）',
                    '环境灯×2：LED平板灯（背景补光）',
                    '背景灯×1：RGB氛围灯'
                ],
                'tips': '标准脸型，正面光为主，立体感通过轮廓灯营造'
            },
            '圆形脸': {
                'config': '11灯正面光',
                'lights': [
                    '主灯×2：AE200+方形柔光箱（稍高位45°）',
                    '发灯×2：AE200+球形柔光箱',
                    '轮廓灯×2：AE200+长条柔光箱（侧面加深阴影）',
                    '下巴补光×1：小型LED（向下打）',
                    '环境灯×2：LED平板灯',
                    '背景灯×2：RGB氛围灯'
                ],
                'tips': '侧面阴影拉长视觉，高位光拉长脸部线条，避免正面平光'
            },
            '方形脸': {
                'config': '10灯正面光',
                'lights': [
                    '主灯×2：AE200+大型八角柔光箱（柔化棱角）',
                    '发灯×2：AE200+球形柔光箱',
                    '轮廓灯×2：柔光长条（柔和过渡）',
                    '下巴柔光×1：反光板或小灯',
                    '环境灯×2：LED平板灯',
                    '背景灯×1：RGB氛围灯'
                ],
                'tips': '用大柔光箱柔化下颌棱角，避免硬光侧打'
            },
            '心形脸': {
                'config': '9灯正面光',
                'lights': [
                    '主灯×2：AE200+方形柔光箱',
                    '发灯×2：AE200+球形柔光箱',
                    '轮廓灯×2：AE200+长条柔光箱',
                    '下巴补光×1：反光板',
                    '环境灯×1：LED平板灯',
                    '背景灯×1：RGB氛围灯'
                ],
                'tips': '下巴区域适当补光，避免下巴过尖显得刻薄'
            },
            '菱形脸': {
                'config': '10灯正面光',
                'lights': [
                    '主灯×2：AE200+大型柔光箱（正面宽光）',
                    '发灯×2：AE200+球形柔光箱',
                    '颧骨柔化×2：反光板侧补',
                    '轮廓灯×1：柔光条',
                    '环境灯×2：LED平板灯',
                    '背景灯×1：RGB氛围灯'
                ],
                'tips': '正面宽光弱化颧骨突出感，额头和下巴适当补光'
            },
        }
        
        # 默认配置
        default_config = base_lights.get('鹅蛋脸')
        config = base_lights.get(shape, default_config)
        
        # 三庭调整建议
        court_adjustments = []
        if three_court and not three_court['is_standard']:
            if three_court['upper'] < 1/3 - 0.05:
                court_adjustments.append("⬆️ 上庭偏短：发灯向上移动，提亮额头")
            if three_court['lower'] > 1/3 + 0.05:
                court_adjustments.append("⬇️ 下庭偏长：下巴加阴影灯，缩短视觉比例")
        
        # 五眼调整建议
        eye_adjustments = []
        if five_eye and not five_eye['is_standard']:
            if five_eye['gap'] > 0.25:
                eye_adjustments.append("👁 两眼间距宽：鼻梁两侧加小型聚光灯")
            if five_eye['gap'] < 0.15:
                eye_adjustments.append("👁 两眼间距窄：外眼角侧补光拉开视觉距离")
        
        return {
            'shape': shape,
            'config': config['config'],
            'lights': config['lights'],
            'tips': config['tips'],
            'court_adjustments': court_adjustments,
            'eye_adjustments': eye_adjustments,
            'all_suggestions': (
                (three_court['suggestions'] if three_court else []) +
                (five_eye['suggestions'] if five_eye else []) +
                court_adjustments + eye_adjustments
            )
        }
    
    def analyze_image(self, image):
        """完整分析一张图片"""
        face_data = self.detect_face(image)
        if face_data is None:
            return None
        
        three_court = self.analyze_three_courts(face_data)
        five_eye = self.analyze_five_eyes(face_data)
        face_shape = self.classify_face_shape(face_data)
        lighting = self.get_lighting_recommendations(face_shape, three_court, five_eye)
        
        return {
            'face_data': face_data,
            'three_court': three_court,
            'five_eye': five_eye,
            'face_shape': face_shape,
            'lighting': lighting,
            'has_face': True
        }
    
    def draw_analysis(self, image, result):
        """在图片上绘制分析结果"""
        if result is None:
            return image
        
        img = image.copy()
        face_data = result['face_data']
        all_points = face_data['all_points']
        
        # 绘制关键点
        for i, (x, y) in enumerate(all_points):
            cv2.circle(img, (x, y), 1, (0, 255, 0), -1)
        
        # 绘制三庭线
        p = face_data['points']
        h, w = img.shape[:2]
        
        if 'brow_center' in p:
            cv2.line(img, (0, p['brow_center'][1]), (w, p['brow_center'][1]), 
                    (255, 200, 0), 1, cv2.LINE_AA)
            cv2.putText(img, "Upper", (10, p['brow_center'][1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
        
        if 'nose_bottom' in p:
            cv2.line(img, (0, p['nose_bottom'][1]), (w, p['nose_bottom'][1]), 
                    (0, 200, 255), 1, cv2.LINE_AA)
            cv2.putText(img, "Middle", (10, p['nose_bottom'][1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
        
        if 'chin' in p:
            cv2.line(img, (0, p['chin'][1]), (w, p['chin'][1]), 
                    (200, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(img, "Lower", (10, p['chin'][1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 0, 255), 1)
        
        # 绘制五眼线
        if all(k in p for k in ['left_eye_outer', 'left_eye_inner', 'right_eye_inner', 'right_eye_outer']):
            eye_y = (p['left_eye_outer'][1] + p['right_eye_outer'][1]) // 2
            for x_key in ['left_eye_outer', 'left_eye_inner', 'right_eye_inner', 'right_eye_outer']:
                x = p[x_key][0]
                cv2.line(img, (x, 0), (x, h), (0, 255, 255), 1, cv2.LINE_AA)
        
        # 绘制脸型轮廓
        if 'left_cheek' in p and 'right_cheek' in p:
            cv2.circle(img, p['left_cheek'], 3, (0, 0, 255), -1)
            cv2.circle(img, p['right_cheek'], 3, (0, 0, 255), -1)
        
        # 标注脸型
        if result['face_shape']:
            shape = result['face_shape']['shape']
            cv2.putText(img, f"Shape: {shape}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return img


# ============================================================
# GUI 界面
# ============================================================

class BeautyToolGUI:
    """直播调试辅助工具 GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎨 直播调试辅助工具 — 脸型分析 & 打光推荐")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        self.analyzer = FaceAnalyzer()
        self.current_image = None
        self.current_result = None
        
        self._setup_styles()
        self._build_ui()
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('PingFang SC', 16, 'bold'), 
                       foreground='#e94560', background='#1a1a2e')
        style.configure('Subtitle.TLabel', font=('PingFang SC', 12), 
                       foreground='#eaeaea', background='#1a1a2e')
        style.configure('Result.TLabel', font=('PingFang SC', 11), 
                       foreground='#cccccc', background='#16213e')
        style.configure('TFrame', background='#1a1a2e')
        style.configure('Card.TFrame', background='#16213e')
        style.configure('TButton', font=('PingFang SC', 11))
    
    def _build_ui(self):
        # 顶部标题
        header = ttk.Frame(self.root, style='TFrame')
        header.pack(fill='x', padx=20, pady=10)
        ttk.Label(header, text="🎨 直播调试辅助工具", style='Title.TLabel').pack(side='left')
        ttk.Label(header, text="  基于三庭五眼框架 · 脸型分析 · 打光推荐", 
                 style='Subtitle.TLabel').pack(side='left', padx=10)
        
        # 按钮栏
        btn_frame = ttk.Frame(self.root, style='TFrame')
        btn_frame.pack(fill='x', padx=20, pady=5)
        
        ttk.Button(btn_frame, text="📷 截取屏幕", command=self.capture_screen).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🖼 导入图片", command=self.load_image).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="📹 摄像头", command=self.capture_camera).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔍 开始分析", command=self.analyze).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="💾 保存结果", command=self.save_result).pack(side='left', padx=5)
        
        # 主内容区
        main_frame = ttk.Frame(self.root, style='TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # 左侧：图片显示
        left_frame = ttk.Frame(main_frame, style='Card.TFrame')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        self.canvas = tk.Canvas(left_frame, bg='#0f3460', width=600, height=600)
        self.canvas.pack(fill='both', expand=True, padx=5, pady=5)
        self.canvas.create_text(300, 300, text="点击「截取屏幕」或「导入图片」开始", 
                               fill='#666', font=('PingFang SC', 14))
        
        # 右侧：分析结果
        right_frame = ttk.Frame(main_frame, style='Card.TFrame', width=450)
        right_frame.pack(side='right', fill='y')
        right_frame.pack_propagate(False)
        
        # 结果标题
        ttk.Label(right_frame, text="📊 分析结果", style='Title.TLabel').pack(pady=10)
        
        # 滚动文本框
        self.result_text = tk.Text(right_frame, bg='#16213e', fg='#eaeaea', 
                                   font=('PingFang SC', 11), wrap='word',
                                   relief='flat', padx=15, pady=10)
        self.result_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 插入默认提示
        self.result_text.insert('1.0', 
            "欢迎使用直播调试辅助工具！\n\n"
            "使用方法：\n"
            "1. 点击「截取屏幕」捕获直播画面\n"
            "2. 或点击「导入图片」选择照片\n"
            "3. 点击「开始分析」\n\n"
            "分析内容：\n"
            "• 三庭五眼比例检测\n"
            "• 12种脸型自动分类\n"
            "• 灯光配置推荐\n"
            "• 调试思路建议"
        )
        self.result_text.configure(state='disabled')
    
    def capture_screen(self):
        """截取屏幕"""
        self.root.iconify()  # 最小化窗口
        self.root.after(500, self._do_capture)
    
    def _do_capture(self):
        try:
            screenshot = ImageGrab.grab()
            self.root.deiconify()
            
            # 转换为 OpenCV 格式
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            self.current_image = img
            self._display_image(img)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("错误", f"截图失败: {e}")
    
    def load_image(self):
        """导入图片"""
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp")]
        )
        if path:
            img = cv2.imread(path)
            if img is not None:
                self.current_image = img
                self._display_image(img)
            else:
                messagebox.showerror("错误", "无法读取图片")
    
    def capture_camera(self):
        """摄像头捕获"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("错误", "无法打开摄像头")
            return
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            self.current_image = frame
            self._display_image(frame)
        else:
            messagebox.showerror("错误", "摄像头捕获失败")
    
    def _display_image(self, cv_image):
        """在画布上显示图片"""
        h, w = cv_image.shape[:2]
        canvas_w = self.canvas.winfo_width() or 600
        canvas_h = self.canvas.winfo_height() or 600
        
        scale = min(canvas_w / w, canvas_h / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized = cv2.resize(cv_image, (new_w, new_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self.tk_img = ImageTk.PhotoImage(pil_img)
        
        self.canvas.delete("all")
        self.canvas.create_image(canvas_w // 2, canvas_h // 2, 
                                image=self.tk_img, anchor='center')
    
    def analyze(self):
        """执行分析"""
        if self.current_image is None:
            messagebox.showwarning("提示", "请先截取屏幕或导入图片")
            return
        
        try:
            result = self.analyzer.analyze_image(self.current_image)
            
            if result is None:
                self._show_result_text("❌ 未检测到人脸\n\n请确保图片中包含清晰的正面人脸")
                return
            
            self.current_result = result
            
            # 绘制分析图
            analyzed_img = self.analyzer.draw_analysis(self.current_image, result)
            self._display_image(analyzed_img)
            
            # 生成报告
            report = self._generate_report(result)
            self._show_result_text(report)
            
        except Exception as e:
            messagebox.showerror("分析错误", f"分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_report(self, result):
        """生成分析报告"""
        lines = []
        lines.append("=" * 40)
        lines.append("🎨 脸型分析报告")
        lines.append("=" * 40)
        lines.append("")
        
        # 脸型
        if result['face_shape']:
            fs = result['face_shape']
            lines.append(f"📐 脸型：{fs['shape']}")
            lines.append(f"   {fs['description']}")
            lines.append(f"   宽高比: {fs['width_height_ratio']:.2f}")
            lines.append(f"   下颌角: {fs['jaw_angle']:.0f}°")
            lines.append("")
        
        # 三庭
        lines.append("📏 三庭分析")
        lines.append("-" * 30)
        if result['three_court']:
            tc = result['three_court']
            lines.append(f"  上庭: {tc['upper']:.1%}  {'✅' if abs(tc['upper']-1/3)<0.05 else '⚠️'}")
            lines.append(f"  中庭: {tc['middle']:.1%}  {'✅' if abs(tc['middle']-1/3)<0.05 else '⚠️'}")
            lines.append(f"  下庭: {tc['lower']:.1%}  {'✅' if abs(tc['lower']-1/3)<0.05 else '⚠️'}")
            lines.append(f"  标准: {'✅ 三庭均等' if tc['is_standard'] else '⚠️ 有偏差'}")
            if tc['issues']:
                lines.append("")
                lines.append("  问题:")
                for issue in tc['issues']:
                    lines.append(f"    • {issue}")
        else:
            lines.append("  ⚠️ 无法分析（关键点不完整）")
        lines.append("")
        
        # 五眼
        lines.append("👁 五眼分析")
        lines.append("-" * 30)
        if result['five_eye']:
            fe = result['five_eye']
            lines.append(f"  左眼占比: {fe['left_eye']:.1%}")
            lines.append(f"  间距占比: {fe['gap']:.1%}")
            lines.append(f"  右眼占比: {fe['right_eye']:.1%}")
            lines.append(f"  标准: {'✅ 五眼均等' if fe['is_standard'] else '⚠️ 有偏差'}")
            if fe['issues']:
                lines.append("")
                lines.append("  问题:")
                for issue in fe['issues']:
                    lines.append(f"    • {issue}")
        else:
            lines.append("  ⚠️ 无法分析")
        lines.append("")
        
        # 灯光推荐
        lines.append("=" * 40)
        lines.append("💡 打光方案推荐")
        lines.append("=" * 40)
        lines.append("")
        
        lighting = result['lighting']
        lines.append(f"推荐配置: {lighting['config']}")
        lines.append("")
        lines.append("灯光布置:")
        for light in lighting['lights']:
            lines.append(f"  • {light}")
        lines.append("")
        lines.append(f"💡 核心思路: {lighting['tips']}")
        lines.append("")
        
        # 调试建议
        if lighting['all_suggestions']:
            lines.append("🔧 调试建议:")
            lines.append("-" * 30)
            for sug in lighting['all_suggestions']:
                lines.append(f"  {sug}")
            lines.append("")
        
        # 总结
        lines.append("=" * 40)
        lines.append("📝 调试思路总结")
        lines.append("=" * 40)
        lines.append("")
        
        shape = result['face_shape']['shape'] if result['face_shape'] else '标准'
        lines.append(f"1. 确认脸型为「{shape}」")
        lines.append(f"2. 选择对应灯光配置「{lighting['config']}」")
        lines.append(f"3. 调整主灯位置和角度")
        if result['three_court'] and not result['three_court']['is_standard']:
            lines.append(f"4. 根据三庭偏差调整发灯/补光位置")
        if result['five_eye'] and not result['five_eye']['is_standard']:
            lines.append(f"5. 根据五眼调整眼周光线")
        lines.append(f"6. 微调轮廓灯营造立体感")
        lines.append(f"7. 背景灯配合风格调色")
        
        return '\n'.join(lines)
    
    def _show_result_text(self, text):
        """更新结果文本"""
        self.result_text.configure(state='normal')
        self.result_text.delete('1.0', 'end')
        self.result_text.insert('1.0', text)
        self.result_text.configure(state='disabled')
    
    def save_result(self):
        """保存结果"""
        if self.current_result is None:
            messagebox.showwarning("提示", "请先进行分析")
            return
        
        path = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("图片", "*.png")]
        )
        if path:
            if path.endswith('.json'):
                # 保存为 JSON
                data = {
                    'face_shape': self.current_result['face_shape'],
                    'three_court': self.current_result['three_court'],
                    'five_eye': self.current_result['five_eye'],
                    'lighting': {
                        'config': self.current_result['lighting']['config'],
                        'tips': self.current_result['lighting']['tips'],
                    }
                }
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                # 保存图片
                if self.current_image is not None:
                    analyzed = self.analyzer.draw_analysis(self.current_image, self.current_result)
                    cv2.imwrite(path, analyzed)
            
            messagebox.showinfo("成功", f"结果已保存到: {path}")
    
    def run(self):
        self.root.mainloop()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    print("🎨 直播调试辅助工具 启动中...")
    print("   依赖: OpenCV, MediaPipe, NumPy, Pillow")
    print("")
    app = BeautyToolGUI()
    app.run()
