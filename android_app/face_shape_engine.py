"""
脸型分类引擎 v4 — 宽度轮廓 + 脸颊流畅度 + 倾斜角度
参考：8种标准脸型图谱 + MediaPipe FaceMesh
"""
import cv2
import numpy as np
import math
import os
import json
import mediapipe as mp

class FaceShapeEngine:
    """脸型分析引擎 v4"""
    
    FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,
                 379,378,400,377,152,148,176,149,150,136,172,58,132,93,
                 234,127,162,21,54,103,67,109,10]
    
    # 下巴轮廓（左脸颊→下巴→右脸颊）
    JAW_LEFT = [234, 172, 136, 150, 149, 176, 148, 152]
    JAW_RIGHT = [152, 377, 400, 365, 397, 454]
    
    LANDMARKS = {
        'brow_center': 9, 'chin': 152, 'nose_bottom': 2,
        'left_eye_outer': 33, 'left_eye_inner': 133,
        'right_eye_inner': 362, 'right_eye_outer': 263,
    }
    
    SHAPE_TEMPLATES = {
        '鹅蛋脸': {
            'profile': [0.92, 1.00, 0.93, 0.72],
            'wh_range': (0.65, 0.80),
            'desc': '最标准脸型，颧骨最宽，线条流畅渐收',
        },
        '长形脸': {
            'profile': [0.90, 1.00, 0.90, 0.70],
            'wh_range': (0.50, 0.65),
            'desc': '脸型偏长，需横向修饰增加宽度感',
        },
        '圆形脸': {
            'profile': [0.95, 1.00, 0.98, 0.88],
            'wh_range': (0.78, 0.95),
            'desc': '脸型短圆，各段宽度接近，下巴圆润',
        },
        '方形脸': {
            'profile': [0.98, 1.00, 0.98, 0.68],
            'wh_range': (0.75, 0.90),
            'desc': '额/颧/颊等宽，棱角分明',
        },
        '心形脸': {
            'profile': [1.00, 0.93, 0.82, 0.55],
            'wh_range': (0.65, 0.82),
            'desc': '额头最宽，下巴尖窄，上宽下窄',
        },
        '菱形脸': {
            'profile': [0.82, 1.00, 0.82, 0.62],
            'wh_range': (0.62, 0.78),
            'desc': '颧骨突出，额头和下巴都窄',
        },
        '倒三角脸': {
            'profile': [1.00, 0.95, 0.78, 0.50],
            'wh_range': (0.68, 0.85),
            'desc': '额头宽，下巴极尖，视觉冲击力强',
        },
        '梨形脸': {
            'profile': [0.82, 0.95, 1.00, 0.78],
            'wh_range': (0.72, 0.88),
            'desc': '脸颊/下颌最宽，额头偏窄',
        },
    }
    
    # 灯光推荐
    LIGHTING = {
        '鹅蛋脸': ('9灯正面光', [
            '主灯×1：方形柔光箱（正面45°）',
            '辅灯×1：球形柔光箱（顶光后方）',
            '轮廓灯×2：长条柔光箱（侧后方）',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '标准脸型，正面光为主，轮廓灯营造立体感'),
        '圆形脸': ('11灯正面光', [
            '主灯×1：方形柔光箱（稍高位45°）',
            '辅灯×1：球形柔光箱',
            '轮廓灯×2：长条柔光箱（侧面加深阴影）',
            '下巴补光×1：小型LED',
            '环境灯×2：LED平板灯',
            '背景灯×2：RGB氛围灯',
        ], '侧面阴影拉长视觉，高位光拉长线条，避免正面平光'),
        '方形脸': ('10灯正面光', [
            '主灯×1：大型八角柔光箱（柔化棱角）',
            '辅灯×1：球形柔光箱',
            '轮廓灯×2：柔光长条',
            '下巴柔光×1：反光板',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '大柔光箱柔化下颌棱角，避免硬光侧打'),
        '心形脸': ('9灯正面光', [
            '主灯×1：方形柔光箱',
            '辅灯×1：球形柔光箱',
            '下巴补光×2：反光板+小型LED',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '下巴区域适当补光，避免过尖'),
        '菱形脸': ('10灯正面光', [
            '主灯×1：大型柔光箱（正面宽光）',
            '辅灯×1：球形柔光箱',
            '颧骨柔化×2：反光板侧补',
            '轮廓灯×1：柔光条',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '正面宽光弱化颧骨，额头下巴补光'),
        '长形脸': ('8灯正面光', [
            '主灯×1：方形柔光箱（低角度横向光）',
            '辅灯×1：球形柔光箱',
            '轮廓灯×2：长条柔光箱',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '低角度拉宽视觉，避免高位光'),
        '倒三角脸': ('9灯正面光', [
            '主灯×1：方形柔光箱（偏下位置）',
            '辅灯×1：球形柔光箱（提亮额头）',
            '下巴补光×1：反光板',
            '轮廓灯×1：柔光条',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '下巴补光平衡上下比例'),
        '梨形脸': ('10灯正面光', [
            '主灯×1：方形柔光箱（偏高位）',
            '辅灯×1：球形柔光箱',
            '轮廓灯×2：长条柔光箱（侧面上部加强）',
            '下颌柔化×1：反光板',
            '环境灯×2：LED平板灯',
            '背景灯×1：RGB氛围灯',
        ], '上半脸加强光照，下半脸柔化阴影'),
    }
    
    # 关键点索引
    LANDMARKS = {
        'brow_center': 9,
        'chin': 152,
        'nose_bottom': 2,
        'left_eye_outer': 33,
        'left_eye_inner': 133,
        'right_eye_inner': 362,
        'right_eye_outer': 263,
    }
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        # 加载经验数据库
        self.exp_templates = {}
        self._load_experience()
    
    def _load_experience(self):
        """从经验数据库加载校准模板"""
        exp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'experience_db.json')
        if not os.path.exists(exp_path):
            return
        try:
            with open(exp_path, 'r') as f:
                db = json.load(f)
            groups = {}
            for s in db.get('samples', []):
                shape = s.get('correct')
                profile = s.get('profile')
                if shape and profile and len(profile) == 4:
                    if shape not in groups:
                        groups[shape] = []
                    groups[shape].append(profile)
            # 计算每种脸型的经验均值
            for shape, profiles in groups.items():
                if len(profiles) >= 1:
                    avg = [sum(p[i] for p in profiles) / len(profiles) for i in range(4)]
                    self.exp_templates[shape] = {'profile': avg, 'count': len(profiles)}
        except Exception:
            pass
    
    def reload_experience(self):
        """重新加载经验数据（每次分析时调用）"""
        self._load_experience()
    
    def get_landmarks(self, image):
        """获取关键点"""
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None
        lm = results.multi_face_landmarks[0]
        h, w = image.shape[:2]
        points = {i: (int(l.x * w), int(l.y * h)) for i, l in enumerate(lm.landmark)}
        return points
    
    def measure_width_profile(self, points):
        """测量四段宽度轮廓（额/颧/颊/下巴）"""
        oval = [points[i] for i in self.FACE_OVAL if i in points]
        if len(oval) < 10:
            return None
        
        xs = [x for x, y in oval]
        ys = [y for x, y in oval]
        face_left = min(xs)
        face_right = max(xs)
        face_top = min(ys)
        face_bottom = max(ys)
        fw = face_right - face_left
        fh = face_bottom - face_top
        
        if fw < 20 or fh < 20:
            return None
        
        # 4个关键高度：额头(15%)、颧骨(35%)、脸颊(55%)、下巴(82%)
        key_ratios = [0.15, 0.35, 0.55, 0.82]
        key_labels = ['forehead', 'cheekbone', 'cheek', 'chin']
        
        widths = []
        for ratio in key_ratios:
            target_y = face_top + fh * ratio
            lefts = [x for x, y in oval if abs(y - target_y) < fh * 0.1 and x < face_left + fw * 0.5]
            rights = [x for x, y in oval if abs(y - target_y) < fh * 0.1 and x >= face_left + fw * 0.5]
            if lefts and rights:
                widths.append(max(rights) - min(lefts))
            else:
                widths.append(None)
        
        if None in widths:
            return None
        
        # 归一化到最宽=1.0
        max_w = max(widths)
        norm = [w / max_w for w in widths]
        
        # 宽高比
        wh_ratio = fw / fh
        
        # 下巴轮廓分析
        jawline = self.analyze_jawline(points)
        
        return {
            'raw_widths': widths,
            'profile': norm,
            'wh_ratio': wh_ratio,
            'face_size': (fw, fh),
            'labels': key_labels,
            'jawline': jawline,
        }
    
    def analyze_jawline(self, points):
        """分析脸颊轮廓流畅度和倾斜角度"""
        left_pts = [points[i] for i in self.JAW_LEFT if i in points]
        if len(left_pts) < 4:
            return None
        
        # 逐段倾斜角（与垂直线的夹角）
        segment_angles = []
        for i in range(len(left_pts) - 1):
            dx = left_pts[i+1][0] - left_pts[i][0]
            dy = left_pts[i+1][1] - left_pts[i][1]
            if dy > 0:
                segment_angles.append(math.degrees(math.atan(abs(dx) / dy)))
        
        if len(segment_angles) < 3:
            return None
        
        mid = len(segment_angles) // 2
        upper_angle = float(np.mean(segment_angles[:mid]))  # 脸颊段
        lower_angle = float(np.mean(segment_angles[mid:]))  # 下巴段
        slope_diff = lower_angle - upper_angle
        
        # 流畅度：角度变化方差的倒数
        diffs = [abs(segment_angles[i+1] - segment_angles[i]) for i in range(len(segment_angles)-1)]
        smoothness = 1.0 / (1.0 + float(np.std(diffs)))
        
        # 曲率：二次拟合
        jaw_x = [p[0] for p in left_pts]
        jaw_y = [p[1] for p in left_pts]
        try:
            coeffs = np.polyfit(jaw_y, jaw_x, 2)
            curvature = abs(coeffs[0]) * 1000
        except:
            curvature = 0
        
        # 整体倾斜角度
        cheek = left_pts[0]
        chin = left_pts[-1]
        dx = abs(chin[0] - cheek[0])
        dy = chin[1] - cheek[1]
        overall_angle = math.degrees(math.atan(dx / dy)) if dy > 0 else 45
        
        return {
            'upper_angle': upper_angle,
            'lower_angle': lower_angle,
            'slope_diff': slope_diff,
            'smoothness': smoothness,
            'curvature': curvature,
            'overall_angle': overall_angle,
            'segment_angles': segment_angles,
        }
    
    def classify(self, measurement):
        """综合宽度轮廓 + 脸颊流畅度 + 倾斜角度 + 经验数据 分类脸型"""
        profile = measurement['profile']
        wh = measurement['wh_ratio']
        fh, cb, ch, cn = profile
        
        jawline = measurement.get('jawline')
        if jawline:
            ua = jawline['upper_angle']
            la = jawline['lower_angle']
            sd = jawline['slope_diff']
            sm = jawline['smoothness']
            cu = jawline['curvature']
        else:
            ua, la, sd, sm, cu = 35, 65, 30, 0.5, 5
        
        # === 第一步：规则决策树 ===
        if wh < 0.66:
            rule_shape = '长形脸'
        elif cn > 0.83 and sm > 0.65 and sd < 35:
            rule_shape = '圆形脸'
        elif abs(fh - ch) < 0.04 and abs(cb - ch) < 0.04 and cn < 0.78:
            rule_shape = '方形脸' if (sm < 0.6 or sd > 30) else '方圆脸'
        elif fh >= cb and cn < 0.60 and sd > 25:
            rule_shape = '心形脸'
        elif fh == max(profile) and cn < 0.55 and cu > 8:
            rule_shape = '倒三角脸'
        elif cb == max(profile) and fh < 0.88 and cn < 0.70:
            rule_shape = '菱形脸'
        elif cn < 0.72 and sm > 0.55 and sd > 18 and cu > 4:
            rule_shape = '瓜子脸'
        elif cn < 0.75 and sd > 15:
            rule_shape = '甲字脸' if fh < cb else '瓜子脸'
        elif ch > fh + 0.06:
            rule_shape = '梨形脸'
        elif 0.70 < cn < 0.85 and sm > 0.65:
            rule_shape = '鹅蛋脸'
        elif cn > 0.82:
            rule_shape = '圆形脸'
        elif sd > 25:
            rule_shape = '瓜子脸'
        else:
            rule_shape = '鹅蛋脸'
        
        # === 第二步：经验模板匹配 ===
        exp_scores = {}
        if self.exp_templates:
            for shape, exp in self.exp_templates.items():
                ep = exp['profile']
                dist = math.sqrt(sum((p - ep[i])**2 for i, p in enumerate(profile)))
                count = exp['count']
                # 样本越多，权重越高
                weight = min(1.0, count / 5) * 0.6 + 0.4
                exp_scores[shape] = round((1.0 - dist) * 10 * weight, 2)
        
        # === 第三步：融合规则 + 经验 ===
        scores = {}
        for s, t in self.SHAPE_TEMPLATES.items():
            dist = math.sqrt(sum((p - t['profile'][i])**2 for i, p in enumerate(profile)))
            if t['wh_range'][0] <= wh <= t['wh_range'][1]:
                dist *= 0.8
            base_score = round(10 - dist * 5, 2)
            
            # 如果有经验数据，融合得分
            if s in exp_scores:
                # 经验数据占40%权重（样本越多权重越高）
                exp_w = min(1.0, self.exp_templates[s]['count'] / 3) * 0.4
                scores[s] = round(base_score * (1 - exp_w) + exp_scores[s] * exp_w, 2)
            else:
                scores[s] = base_score
        
        # 如果有经验数据中有不在模板里的类型，也加入
        for s in exp_scores:
            if s not in scores:
                scores[s] = exp_scores[s]
        
        # 选择最高分的脸型（而非规则决策树）
        sorted_scores = dict(sorted(scores.items(), key=lambda x: -x[1]))
        best_shape = list(sorted_scores.keys())[0] if sorted_scores else rule_shape
        
        # 如果规则和经验一致，提高置信度
        if best_shape == rule_shape:
            conf_boost = 1.1
        else:
            conf_boost = 0.95
        
        return {
            'shape': best_shape,
            'rule_shape': rule_shape,  # 规则结果（参考）
            'confidence': round(sorted_scores.get(best_shape, 0) * conf_boost, 1),
            'profile': profile,
            'wh_ratio': wh,
            'jawline': jawline,
            'scores': dict(list(sorted_scores.items())[:5]),
            'description': self.SHAPE_TEMPLATES.get(best_shape, {}).get('desc', ''),
            'has_exp': bool(self.exp_templates),
        }
    
    def analyze_three_courts(self, points):
        """三庭分析"""
        chin = points.get(self.LANDMARKS['chin'])
        brow = points.get(self.LANDMARKS['brow_center'])
        nose = points.get(self.LANDMARKS['nose_bottom'])
        
        if not all([chin, brow, nose]):
            return None
        
        # 发际线估算
        oval = [points[i] for i in self.FACE_OVAL if i in points]
        top_y = min(y for x, y in oval)
        
        upper = brow[1] - top_y
        middle = nose[1] - brow[1]
        lower = chin[1] - nose[1]
        total = chin[1] - top_y
        
        if total <= 0:
            return None
        
        u, m, l = upper / total, middle / total, lower / total
        
        issues = []
        suggestions = []
        ideal = 1/3
        
        for label, val, sug_short, sug_long in [
            ('上庭', u, '发灯提亮额头', '刘海遮盖缩短'),
            ('中庭', m, '鼻子高光拉长', '面部中部柔光'),
            ('下庭', l, '下巴下方补光', '下巴阴影减弱'),
        ]:
            if val < ideal - 0.04:
                issues.append(f'{label}偏短 ({val:.1%})')
                suggestions.append(f'• {sug_short}')
            elif val > ideal + 0.04:
                issues.append(f'{label}偏长 ({val:.1%})')
                suggestions.append(f'• {sug_long}')
        
        return {
            'upper': u, 'middle': m, 'lower': l,
            'is_standard': len(issues) == 0,
            'issues': issues, 'suggestions': suggestions,
            'lines': {'top': top_y, 'brow': brow[1], 'nose': nose[1], 'chin': chin[1]},
        }
    
    def analyze_five_eyes(self, points):
        """五眼分析"""
        lo = points.get(self.LANDMARKS['left_eye_outer'])
        li = points.get(self.LANDMARKS['left_eye_inner'])
        ri = points.get(self.LANDMARKS['right_eye_inner'])
        ro = points.get(self.LANDMARKS['right_eye_outer'])
        
        if not all([lo, li, ri, ro]):
            return None
        
        w1 = li[0] - lo[0]
        w2 = ri[0] - li[0]
        w3 = ro[0] - ri[0]
        total = ro[0] - lo[0]
        
        if total <= 0:
            return None
        
        r1, gap, r3 = w1 / total, w2 / total, w3 / total
        
        issues = []
        suggestions = []
        
        if gap > 0.28:
            issues.append(f'两眼间距偏宽 ({gap:.1%})')
            suggestions.append('• 内眼角眼线拉近')
        elif gap < 0.16:
            issues.append(f'两眼间距偏窄 ({gap:.1%})')
            suggestions.append('• 外眼角眼线拉长')
        
        if abs(r1 - r3) > 0.06:
            issues.append('左右眼不对称')
            suggestions.append('• 眼线微调平衡')
        
        return {
            'left_eye': r1, 'gap': gap, 'right_eye': r3,
            'is_standard': len(issues) == 0,
            'issues': issues, 'suggestions': suggestions,
            'coords': {'lo': lo[0], 'li': li[0], 'ri': ri[0], 'ro': ro[0]},
        }
    
    def get_lighting(self, shape):
        """获取打光推荐"""
        config = self.LIGHTING.get(shape, self.LIGHTING['鹅蛋脸'])
        return {
            'shape': shape,
            'config': config[0],
            'lights': config[1],
            'tips': config[2],
        }
    
    def analyze_image(self, image):
        """完整分析一张图片"""
        # 每次分析前重新加载经验数据
        self.reload_experience()
        
        points = self.get_landmarks(image)
        if points is None:
            return None
        
        measurement = self.measure_width_profile(points)
        if measurement is None:
            return None
        
        face_shape = self.classify(measurement)
        three_court = self.analyze_three_courts(points)
        five_eye = self.analyze_five_eyes(points)
        lighting = self.get_lighting(face_shape['shape'])
        
        # 合并建议
        all_suggestions = []
        if three_court:
            all_suggestions.extend(three_court['suggestions'])
        if five_eye:
            all_suggestions.extend(five_eye['suggestions'])
        lighting['all_suggestions'] = all_suggestions
        
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
            cv2.line(img, oval_pts[i], oval_pts[i + 1], (0, 255, 0), 2, cv2.LINE_AA)
        
        # 四段宽度线
        m = result['measurement']
        face_top = min(y for x, y in oval_pts)
        face_bottom = max(y for x, y in oval_pts)
        fh = face_bottom - face_top
        
        colors = [(255, 200, 0), (0, 255, 255), (255, 100, 255), (100, 255, 100)]
        labels = ['额', '颧', '颊', '下']
        
        for i, (ratio, color, label) in enumerate(zip([0.15, 0.35, 0.55, 0.82], colors, labels)):
            y_pos = int(face_top + fh * ratio)
            cv2.line(img, (0, y_pos), (w, y_pos), color, 1, cv2.LINE_AA)
            profile_val = m['profile'][i]
            cv2.putText(img, f'{label} {profile_val:.0%}', (5, y_pos - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 三庭线
        tc = result.get('three_court')
        if tc:
            brow = pts.get(self.LANDMARKS['brow_center'])
            nose = pts.get(self.LANDMARKS['nose_bottom'])
            if brow:
                cv2.line(img, (0, brow[1]), (w, brow[1]), (255, 255, 0), 2, cv2.LINE_AA)
            if nose:
                cv2.line(img, (0, nose[1]), (w, nose[1]), (0, 255, 255), 2, cv2.LINE_AA)
        
        # 五眼线
        fe = result.get('five_eye')
        if fe:
            for key in ['left_eye_outer', 'left_eye_inner', 'right_eye_inner', 'right_eye_outer']:
                pt = pts.get(self.LANDMARKS[key])
                if pt:
                    cv2.line(img, (pt[0], 0), (pt[0], h), (0, 255, 255), 1, cv2.LINE_AA)
        
        # 脸型标注
        fs = result.get('face_shape')
        if fs:
            cv2.putText(img, fs['shape'], (10, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            conf_line = f"conf:{fs['confidence']:.1f}  wh:{fs['wh_ratio']:.2f}"
            if fs.get('jawline'):
                j = fs['jawline']
                conf_line += f"  角度:{j['upper_angle']:.0f}→{j['lower_angle']:.0f}° 流畅:{j['smoothness']:.2f}"
            cv2.putText(img, conf_line, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 0), 1)
        
        # 绘制下巴轮廓线
        jaw_left_pts = [pts[i] for i in self.JAW_LEFT if i in pts]
        for i in range(len(jaw_left_pts) - 1):
            cv2.line(img, jaw_left_pts[i], jaw_left_pts[i+1], (0, 150, 255), 2, cv2.LINE_AA)
        jaw_right_pts = [pts[i] for i in self.JAW_RIGHT if i in pts]
        for i in range(len(jaw_right_pts) - 1):
            cv2.line(img, jaw_right_pts[i], jaw_right_pts[i+1], (0, 150, 255), 2, cv2.LINE_AA)
        
        return img
