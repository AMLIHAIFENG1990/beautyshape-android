"""
脸型分析引擎 v2 - 修复版
使用完整脸部轮廓点进行精确分类
"""
import cv2
import numpy as np
import math
import mediapipe as mp

class FaceAnalyzerV2:
    """人脸分析引擎 v2"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        # 脸部轮廓点索引（从左太阳穴沿脸部边缘到右太阳穴）
        self.FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 
                          361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 
                          176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 
                          162, 21, 54, 103, 67, 109, 10]
        
        # 下巴轮廓点
        self.JAW_LINE = [172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 
                         379, 365, 397, 288, 361, 323]
        
        # 关键点
        self.LANDMARKS = {
            'nose_tip': 1,
            'chin': 152,
            'brow_center': 9,
            'left_eye_outer': 33,
            'left_eye_inner': 133,
            'right_eye_inner': 362,
            'right_eye_outer': 263,
            'nose_bottom': 2,
            'left_mouth': 61,
            'right_mouth': 291,
            'forehead': 10,
        }
    
    def get_points(self, image):
        """获取关键点"""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None
        
        lm = results.multi_face_landmarks[0]
        h, w = image.shape[:2]
        
        points = {}
        for i, landmark in enumerate(lm.landmark):
            points[i] = (int(landmark.x * w), int(landmark.y * h))
        
        return points
    
    def measure_face(self, points):
        """精确测量脸部特征"""
        # 脸部边界框
        face_pts = [points[i] for i in self.FACE_OVAL if i in points]
        if len(face_pts) < 10:
            return None
        
        xs = [p[0] for p in face_pts]
        ys = [p[1] for p in face_pts]
        
        face_left = min(xs)
        face_right = max(xs)
        face_top = min(ys)
        face_bottom = max(ys)
        
        face_width = face_right - face_left
        face_height = face_bottom - face_top
        
        if face_width < 10 or face_height < 10:
            return None
        
        # 在不同高度测量脸部宽度
        def width_at_y_ratio(y_ratio):
            """在特定高度比例处测量宽度"""
            target_y = face_top + face_height * y_ratio
            left_candidates = []
            right_candidates = []
            for idx in self.FACE_OVAL:
                if idx not in points:
                    continue
                x, y = points[idx]
                if abs(y - target_y) < face_height * 0.1:
                    if x < face_left + face_width * 0.5:
                        left_candidates.append(x)
                    else:
                        right_candidates.append(x)
            if left_candidates and right_candidates:
                return max(right_candidates) - min(left_candidates)
            return None
        
        # 各区域宽度
        forehead_w = width_at_y_ratio(0.15) or face_width * 0.82
        cheek_w = width_at_y_ratio(0.45) or face_width
        jaw_w = width_at_y_ratio(0.75) or face_width * 0.62
        
        chin_pt = points.get(152)  # 下巴尖
        brow_pt = points.get(self.LANDMARKS['brow_center'])
        
        if not chin_pt or not brow_pt:
            return None
        
        # 下巴角度 — 使用下巴轮廓点 148-152-377
        jaw_left = points.get(176) or points.get(148)  # 下巴左侧
        jaw_right = points.get(400) or points.get(377)  # 下巴右侧
        
        if jaw_left and jaw_right:
            lp = np.array(jaw_left)
            cp = np.array(chin_pt)
            rp = np.array(jaw_right)
            v1 = lp - cp
            v2 = rp - cp
            cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
            jaw_angle = math.degrees(math.acos(np.clip(cos_a, -1, 1)))
        else:
            jaw_angle = 120
        
        # 宽度轮廓（8个高度）
        width_profile = []
        for ratio in [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]:
            target_y = face_top + face_height * ratio
            lefts = [x for x,y in face_pts if abs(y - target_y) < face_height * 0.08 and x < face_left + face_width * 0.5]
            rights = [x for x,y in face_pts if abs(y - target_y) < face_height * 0.08 and x >= face_left + face_width * 0.5]
            if lefts and rights:
                width_profile.append((max(rights) - min(lefts)) / face_width)
            else:
                width_profile.append(None)
        
        # 比率
        wh_ratio = face_width / face_height
        forehead_cheek_ratio = forehead_w / cheek_w if cheek_w > 0 else 1
        jaw_cheek_ratio = jaw_w / cheek_w if cheek_w > 0 else 0.7
        jaw_forehead_ratio = jaw_w / forehead_w if forehead_w > 0 else 1
        
        return {
            'face_width': face_width,
            'face_height': face_height,
            'wh_ratio': wh_ratio,
            'forehead_w': forehead_w,
            'cheek_w': cheek_w,
            'jaw_w': jaw_w,
            'jaw_angle': jaw_angle,
            'forehead_cheek_ratio': forehead_cheek_ratio,
            'jaw_cheek_ratio': jaw_cheek_ratio,
            'jaw_forehead_ratio': jaw_forehead_ratio,
            'width_profile': width_profile,
        }
    
    def classify_face_shape(self, m):
        """根据测量数据分类脸型 — 宽度轮廓 + 比率综合判定"""
        wh = m['wh_ratio']
        fc_ratio = m['forehead_cheek_ratio']
        jc_ratio = m['jaw_cheek_ratio']
        
        # 从宽度轮廓获取更详细信息
        profile = m.get('width_profile')
        if profile and not None in profile:
            w15,w25,w35,w45,w55,w65,w75,w85 = profile
            taper = (w75+w85)/2 / ((w15+w25)/2)  # 下巴/额头比
            rapid_taper = w55 - w85  # 中下部收窄速度
            forehead_r = w15 / max(profile)
        else:
            taper = jc_ratio
            rapid_taper = 0.15
            forehead_r = fc_ratio
        
        # 决策树分类
        if wh < 0.60:
            shape = '目字脸'
        elif wh < 0.68:
            shape = '长形脸'
        elif rapid_taper > 0.18 and forehead_r < 0.92:
            shape = '心形脸'
        elif rapid_taper > 0.14 and forehead_r < 0.95:
            shape = '瓜子脸'
        elif rapid_taper > 0.12:
            if wh > 0.85:
                shape = '甲字脸'
            elif rapid_taper > 0.20:
                shape = '心形脸'
            else:
                shape = '甲字脸'
        elif taper > 0.82 and wh > 0.82:
            shape = '圆形脸'
        elif rapid_taper > 0.08:
            if forehead_r < 0.90:
                shape = '菱形脸'
            elif wh < 0.80:
                shape = '鹅蛋脸'
            else:
                shape = '鹅蛋脸'
        elif taper > 0.88:
            shape = '方圆脸'
        else:
            shape = '鹅蛋脸'
        
        scores = self._calc_scores(wh, m['jaw_angle'], fc_ratio, jc_ratio, m['jaw_forehead_ratio'])
        
        return {
            'shape': shape,
            'width_height_ratio': wh,
            'jaw_angle': m['jaw_angle'],
            'forehead_cheek_ratio': fc_ratio,
            'jaw_cheek_ratio': jc_ratio,
            'jaw_forehead_ratio': m['jaw_forehead_ratio'],
            'width_profile': profile,
            'scores': {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]},
            'description': self._get_desc(shape),
        }
    
    def _calc_scores(self, wh, jaw_angle, fc_ratio, jc_ratio, jf_ratio):
        """计算各脸型匹配分数（供参考）"""
        scores = {}
        # 基于实测数据范围的评分
        scores['鹅蛋脸'] = 4 - abs(wh - 0.82)*8 - abs(jaw_angle - 102)/15 - abs(jc_ratio - 0.68)*4
        scores['圆形脸'] = 4 - abs(wh - 0.89)*8 - max(0, (105 - jaw_angle)/20) - abs(jc_ratio - 0.78)*3
        scores['瓜子脸'] = 4 - abs(wh - 0.83)*8 - abs(jaw_angle - 95)/10 - abs(jc_ratio - 0.62)*4
        scores['甲字脸'] = 4 - abs(wh - 0.85)*8 - abs(jaw_angle - 98)/12 - abs(jc_ratio - 0.72)*3
        scores['心形脸'] = 4 - abs(wh - 0.80)*8 - abs(jaw_angle - 94)/10 - abs(jc_ratio - 0.55)*4
        scores['方形脸'] = 4 - abs(wh - 0.85)*5 - abs(jaw_angle - 110)/15 - abs(jc_ratio - 0.85)*3
        scores['菱形脸'] = 4 - abs(wh - 0.78)*8 - abs(jaw_angle - 100)/15 - abs(jc_ratio - 0.60)*4
        scores['长形脸'] = 4 - abs(wh - 0.63)*10 - abs(jaw_angle - 100)/20 - abs(jc_ratio - 0.65)*3
        scores['方圆脸'] = 4 - abs(wh - 0.88)*6 - abs(jaw_angle - 108)/12 - abs(jc_ratio - 0.78)*3
        scores['梨形脸'] = 4 - abs(wh - 0.82)*6 - abs(jaw_angle - 105)/15 - abs(jc_ratio - 0.82)*3
        scores['国字脸'] = 4 - abs(wh - 0.84)*5 - abs(jaw_angle - 115)/15 - abs(jc_ratio - 0.88)*3
        scores['目字脸'] = 4 - abs(wh - 0.55)*10 - abs(jaw_angle - 100)/20 - abs(jc_ratio - 0.60)*3
        return scores
    
    def _get_desc(self, shape):
        descs = {
            '鹅蛋脸': '最标准脸型，线条流畅，适合各种发型',
            '圆形脸': '脸型短圆，显得可爱，需纵向拉长视觉',
            '方形脸': '下颌角明显，有气场，需柔化棱角',
            '长形脸': '脸型偏长，需横向拉宽视觉',
            '心形脸': '下巴尖，额头宽，需平衡上下比例',
            '菱形脸': '颧骨突出，额头下巴窄，需柔化颧骨',
            '梨形脸': '下颌宽，额头窄，需平衡上下宽度',
            '国字脸': '棱角分明，偏方正，需柔化线条',
            '申字脸': '中间宽两头窄，需增加额头下巴光',
            '甲字脸': '上窄下宽，需增加上半脸视觉宽度',
            '由字脸': '上宽下窄，需增加下半脸视觉宽度',
            '目字脸': '整体偏窄长，需横向拉宽视觉',
        }
        return descs.get(shape, '')
    
    def analyze_three_courts(self, points):
        """三庭分析"""
        chin = points.get(self.LANDMARKS['chin'])
        brow = points.get(self.LANDMARKS['brow_center'])
        nose = points.get(self.LANDMARKS['nose_bottom'])
        forehead = points.get(self.LANDMARKS['forehead'])
        
        if not all([chin, brow, nose, forehead]):
            return None
        
        # 用脸部轮廓点估算发际线
        face_pts = [(i, points[i]) for i in self.FACE_OVAL if i in points]
        top_y = min(p[1] for _, p in face_pts)
        
        # 三庭高度
        upper = brow[1] - top_y
        middle = nose[1] - brow[1]
        lower = chin[1] - nose[1]
        total = chin[1] - top_y
        
        if total <= 0:
            return None
        
        upper_r = upper / total
        middle_r = middle / total
        lower_r = lower / total
        
        issues = []
        suggestions = []
        ideal = 1/3
        
        if upper_r < ideal - 0.04:
            issues.append(f"上庭偏短 ({upper_r:.1%})")
            suggestions.append("• 发型：露额头或蓬松头顶拉长上庭")
            suggestions.append("• 打光：额头上方加发灯提亮")
        elif upper_r > ideal + 0.04:
            issues.append(f"上庭偏长 ({upper_r:.1%})")
            suggestions.append("• 发型：刘海遮盖额头缩短上庭")
            suggestions.append("• 打光：减少额头光照")
        
        if middle_r < ideal - 0.04:
            issues.append(f"中庭偏短 ({middle_r:.1%})")
            suggestions.append("• 修容：鼻子高光拉长中庭")
        elif middle_r > ideal + 0.04:
            issues.append(f"中庭偏长 ({middle_r:.1%})")
            suggestions.append("• 打光：面部中部柔光减少阴影")
        
        if lower_r < ideal - 0.04:
            issues.append(f"下庭偏短 ({lower_r:.1%})")
            suggestions.append("• 打光：下巴下方补光")
        elif lower_r > ideal + 0.04:
            issues.append(f"下庭偏长 ({lower_r:.1%})")
            suggestions.append("• 打光：下巴阴影减弱")
        
        return {
            'upper': upper_r, 'middle': middle_r, 'lower': lower_r,
            'is_standard': len(issues) == 0,
            'issues': issues, 'suggestions': suggestions
        }
    
    def analyze_five_eyes(self, points):
        """五眼分析"""
        lo = points.get(self.LANDMARKS['left_eye_outer'])
        li = points.get(self.LANDMARKS['left_eye_inner'])
        ri = points.get(self.LANDMARKS['right_eye_inner'])
        ro = points.get(self.LANDMARKS['right_eye_outer'])
        
        if not all([lo, li, ri, ro]):
            return None
        
        w1 = li[0] - lo[0]   # 左眼宽度
        w2 = ri[0] - li[0]   # 两眼间距
        w3 = ro[0] - ri[0]   # 右眼宽度
        total = ro[0] - lo[0]
        
        if total <= 0:
            return None
        
        r1 = w1 / total
        gap = w2 / total
        r3 = w3 / total
        
        issues = []
        suggestions = []
        
        if gap > 0.28:
            issues.append(f"两眼间距偏宽 ({gap:.1%})")
            suggestions.append("• 妆容：内眼角眼线拉近")
            suggestions.append("• 打光：鼻梁高光连接两眼")
        elif gap < 0.16:
            issues.append(f"两眼间距偏窄 ({gap:.1%})")
            suggestions.append("• 妆容：外眼角眼线拉长")
            suggestions.append("• 打光：眼侧阴影增加宽度感")
        
        if abs(r1 - r3) > 0.06:
            issues.append("左右眼不对称")
            suggestions.append("• 妆容：通过眼线微调平衡")
        
        return {
            'left_eye': r1, 'gap': gap, 'right_eye': r3,
            'is_standard': len(issues) == 0,
            'issues': issues, 'suggestions': suggestions
        }
    
    def get_lighting(self, face_shape, three_court, five_eye):
        """灯光推荐"""
        shape = face_shape['shape'] if face_shape else '鹅蛋脸'
        
        configs = {
            '鹅蛋脸': ('9灯正面光', [
                '主灯×2：方形柔光箱（正面45°）',
                '发灯×2：球形柔光箱（顶光后方）',
                '轮廓灯×2：长条柔光箱（侧后方）',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '标准脸型，正面光为主，立体感通过轮廓灯营造'),
            
            '圆形脸': ('11灯正面光', [
                '主灯×2：方形柔光箱（稍高位45°）',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：长条柔光箱（侧面加深阴影）',
                '下巴补光×1：小型LED（向下打）',
                '环境灯×2：LED平板灯',
                '背景灯×2：RGB氛围灯'
            ], '侧面阴影拉长视觉，高位光拉长脸部线条，避免正面平光'),
            
            '方形脸': ('10灯正面光', [
                '主灯×2：大型八角柔光箱（柔化棱角）',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：柔光长条（柔和过渡）',
                '下巴柔光×1：反光板',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '用大柔光箱柔化下颌棱角，避免硬光侧打'),
            
            '心形脸': ('9灯正面光', [
                '主灯×2：方形柔光箱',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：长条柔光箱',
                '下巴补光×1：反光板',
                '环境灯×1：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '下巴区域适当补光，避免下巴过尖'),
            
            '菱形脸': ('10灯正面光', [
                '主灯×2：大型柔光箱（正面宽光）',
                '发灯×2：球形柔光箱',
                '颧骨柔化×2：反光板侧补',
                '轮廓灯×1：柔光条',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '正面宽光弱化颧骨突出感，额头和下巴适当补光'),
        }
        
        default = configs['鹅蛋脸']
        config, lights, tips = configs.get(shape, default)
        
        # 12种脸型都有对应灯光
        extra_configs = {
            '长形脸': ('8灯正面光', [
                '主灯×2：方形柔光箱（低角度，增加横向光）',
                '发灯×1：球形柔光箱',
                '轮廓灯×2：长条柔光箱',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '低角度主光拉宽脸部视觉，避免高位光拉长'),
            
            '梨形脸': ('10灯正面光', [
                '主灯×2：方形柔光箱（偏高位）',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：长条柔光箱（侧面上部加强）',
                '下颌柔化×1：反光板',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '上半脸加强光照，下半脸柔化阴影'),
            
            '国字脸': ('10灯正面光', [
                '主灯×2：大型柔光箱（柔化方正线条）',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：柔光条（柔化下颌角）',
                '下巴柔化×1：反光板',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '柔光箱大面积柔化下颌角棱角'),
            
            '甲字脸': ('9灯正面光', [
                '主灯×2：方形柔光箱（偏下位置）',
                '发灯×2：球形柔光箱',
                '轮廓灯×2：长条柔光箱',
                '下巴补光×1：小型LED',
                '环境灯×1：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '下巴区域补光平衡上下比例'),
            
            '由字脸': ('9灯正面光', [
                '主灯×2：方形柔光箱（偏上位置）',
                '发灯×1：球形柔光箱',
                '轮廓灯×2：长条柔光箱',
                '额头补光×1：小型LED',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '额头区域加强光照平衡上下比例'),
            
            '申字脸': ('10灯正面光', [
                '主灯×2：大型柔光箱（正面均匀光）',
                '发灯×2：球形柔光箱（提亮额头）',
                '轮廓灯×2：长条柔光箱',
                '下巴补光×1：反光板',
                '环境灯×2：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '额头和下巴都需补光，正面均匀光照'),
            
            '目字脸': ('8灯正面光', [
                '主灯×2：方形柔光箱（横向宽光）',
                '轮廓灯×2：长条柔光箱（拉宽视觉）',
                '环境灯×3：LED平板灯',
                '背景灯×1：RGB氛围灯'
            ], '横向宽光拉宽视觉，避免纵向光'),
        }
        
        if shape in extra_configs:
            config, lights, tips = extra_configs[shape]
        
        # 调整建议
        suggestions = []
        if three_court:
            suggestions.extend(three_court['suggestions'])
        if five_eye:
            suggestions.extend(five_eye['suggestions'])
        
        if three_court and not three_court['is_standard']:
            if three_court['upper'] < 1/3 - 0.04:
                suggestions.append("⬆️ 上庭偏短：发灯向上移动，提亮额头")
            if three_court['lower'] > 1/3 + 0.04:
                suggestions.append("⬇️ 下庭偏长：下巴加阴影灯，缩短视觉")
        
        if five_eye and not five_eye['is_standard']:
            if five_eye['gap'] > 0.28:
                suggestions.append("👁 间距宽：鼻梁两侧加小型聚光灯")
            if five_eye['gap'] < 0.16:
                suggestions.append("👁 间距窄：外眼角侧补光拉开距离")
        
        return {
            'shape': shape, 'config': config,
            'lights': lights, 'tips': tips,
            'all_suggestions': suggestions
        }
    
    def analyze_image(self, image):
        """完整分析"""
        points = self.get_points(image)
        if points is None:
            return None
        
        measurement = self.measure_face(points)
        if measurement is None:
            return None
        
        face_shape = self.classify_face_shape(measurement)
        three_court = self.analyze_three_courts(points)
        five_eye = self.analyze_five_eyes(points)
        lighting = self.get_lighting(face_shape, three_court, five_eye)
        
        return {
            'points': points,
            'measurement': measurement,
            'face_shape': face_shape,
            'three_court': three_court,
            'five_eye': five_eye,
            'lighting': lighting,
        }
    
    def draw_analysis(self, image, result):
        """绘制分析结果"""
        img = image.copy()
        if result is None:
            return img
        
        pts = result['points']
        h, w = img.shape[:2]
        
        # 绘制脸部轮廓
        oval_pts = [pts[i] for i in self.FACE_OVAL if i in pts]
        for i in range(len(oval_pts) - 1):
            cv2.line(img, oval_pts[i], oval_pts[i+1], (0, 255, 0), 1, cv2.LINE_AA)
        
        # 三庭线
        tc = result.get('three_court')
        if tc:
            brow = pts.get(self.LANDMARKS['brow_center'])
            nose = pts.get(self.LANDMARKS['nose_bottom'])
            chin = pts.get(self.LANDMARKS['chin'])
            
            if brow:
                cv2.line(img, (0, brow[1]), (w, brow[1]), (255, 200, 0), 2, cv2.LINE_AA)
                cv2.putText(img, f"Upper {tc['upper']:.0%}", (5, brow[1]-8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
            if nose:
                cv2.line(img, (0, nose[1]), (w, nose[1]), (0, 200, 255), 2, cv2.LINE_AA)
                cv2.putText(img, f"Middle {tc['middle']:.0%}", (5, nose[1]-8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            if chin:
                cv2.putText(img, f"Lower {tc['lower']:.0%}", (5, chin[1]-8), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 255), 1)
        
        # 五眼线
        fe = result.get('five_eye')
        if fe:
            for key in ['left_eye_outer', 'left_eye_inner', 'right_eye_inner', 'right_eye_outer']:
                pt = pts.get(self.LANDMARKS[key])
                if pt:
                    cv2.line(img, (pt[0], 0), (pt[0], h), (0, 255, 255), 1, cv2.LINE_AA)
        
        # 脸型标注
        if result.get('face_shape'):
            fs = result['face_shape']
            cv2.putText(img, f"{fs['shape']}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.putText(img, f"wh={fs['width_height_ratio']:.2f} angle={fs['jaw_angle']:.0f}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)
        
        return img
