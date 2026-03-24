"""
BeautyShape — Android 版主程序
离线使用，所有计算在手机上完成
"""
import os
import json
import base64
import threading
import io

# Kivy 设置（必须在其他 kivy import 之前）
os.environ['KIVY_LOG_LEVEL'] = 'warning'

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp, sp

import cv2
import numpy as np

# 分析引擎路径
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════ KV Layout ═══════════════
KV = '''
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp
#:import FadeTransition kivy.uix.screenmanager.FadeTransition

<RootManager>:
    transition: FadeTransition(duration=0.2)
    MainScreen:
    ResultScreen:
    ExperienceScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        # 顶部导航
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: [dp(16), dp(8)]
            canvas.before:
                Color:
                    rgba: 0.06, 0.06, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: '🦞 BeautyShape'
                font_size: sp(20)
                bold: True
                color: 1, 1, 1, 1
                halign: 'left'
                text_size: self.size
                valign: 'center'
            Button:
                text: '◈ 经验库'
                size_hint_x: None
                width: dp(80)
                background_color: 0, 0, 0, 0
                color: 0.55, 0.36, 0.96, 1
                font_size: sp(13)
                on_release: app.root.current = 'experience'

        # 图片区域
        BoxLayout:
            id: image_area
            padding: dp(12)
            canvas.before:
                Color:
                    rgba: 0.08, 0.08, 0.15, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12)]
            Label:
                id: placeholder
                text: '导入照片或拍照\\n开始脸型分析'
                halign: 'center'
                color: 0.4, 0.4, 0.5, 1
                font_size: sp(16)
            KivyImage:
                id: preview
                opacity: 0
                allow_stretch: True
                keep_ratio: True

        # 操作按钮
        BoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: [dp(12), dp(8)]
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.06, 0.06, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '📷 拍照'
                background_color: 0.55, 0.36, 0.96, 0.3
                color: 1, 1, 1, 1
                font_size: sp(14)
                on_release: root.take_photo()
            Button:
                text: '🖼 相册'
                background_color: 0.55, 0.36, 0.96, 0.3
                color: 1, 1, 1, 1
                font_size: sp(14)
                on_release: root.pick_image()
            Button:
                id: analyze_btn
                text: '🔍 分析'
                background_color: 0.55, 0.36, 0.96, 1
                color: 1, 1, 1, 1
                font_size: sp(14)
                bold: True
                on_release: root.do_analyze()
                disabled: True

<ResultScreen>:
    name: 'result'
    BoxLayout:
        orientation: 'vertical'
        # 顶部
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: [dp(12), dp(8)]
            canvas.before:
                Color:
                    rgba: 0.06, 0.06, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '← 返回'
                size_hint_x: None
                width: dp(70)
                background_color: 0, 0, 0, 0
                color: 0.55, 0.36, 0.96, 1
                font_size: sp(14)
                on_release: app.root.current = 'main'
            Label:
                text: '分析结果'
                font_size: sp(18)
                bold: True
                color: 1, 1, 1, 1

        # 滚动结果
        ScrollView:
            BoxLayout:
                id: result_content
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(12)
                spacing: dp(10)

<ExperienceScreen>:
    name: 'experience'
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: [dp(12), dp(8)]
            canvas.before:
                Color:
                    rgba: 0.06, 0.06, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '← 返回'
                size_hint_x: None
                width: dp(70)
                background_color: 0, 0, 0, 0
                color: 0.55, 0.36, 0.96, 1
                font_size: sp(14)
                on_release: app.root.current = 'main'
            Label:
                text: '◈ 经验库'
                font_size: sp(18)
                bold: True
                color: 1, 1, 1, 1

        ScrollView:
            BoxLayout:
                id: exp_content
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(12)
                spacing: dp(8)

<Card@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: dp(14)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.18, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
'''

Builder.load_string(KV)


# ═══════════════ Screens ═══════════════
class MainScreen(Screen):
    """主界面：导入照片 + 分析"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_image = None  # numpy array
        self.app = App.get_running_app()

    def take_photo(self):
        """调用相机拍照"""
        try:
            from plyer import camera
            path = os.path.join(self.app.user_data_dir, 'capture.jpg')
            camera.take_picture(filename=path, on_complete=self._on_photo)
        except Exception as e:
            self._show_msg(f'相机不可用: {e}')

    def _on_photo(self, path):
        Clock.schedule_once(lambda dt: self._load_image(path))

    def pick_image(self):
        """从相册选择"""
        try:
            from plyer import filechooser
            filechooser.open_file(on_selection=self._on_file, filters=[("Images", "*.jpg","*.jpeg","*.png","*.bmp")])
        except Exception as e:
            # Fallback: 直接用 Android intent
            self._show_msg(f'文件选择器不可用: {e}')

    def _on_file(self, selection):
        if selection:
            Clock.schedule_once(lambda dt: self._load_image(selection[0]))

    def _load_image(self, path):
        """加载图片到预览"""
        if not path or not os.path.exists(path):
            return
        self.current_image = cv2.imread(path)
        if self.current_image is None:
            self._show_msg('无法读取图片')
            return
        # 显示预览
        preview = self.ids.preview
        preview.source = path
        preview.opacity = 1
        self.ids.placeholder.opacity = 0
        self.ids.analyze_btn.disabled = False

    def do_analyze(self):
        """分析脸型"""
        if self.current_image is None:
            return
        app = App.get_running_app()
        # 在后台线程分析
        self.ids.analyze_btn.text = '⏳ 分析中...'
        self.ids.analyze_btn.disabled = True
        threading.Thread(target=self._analyze_thread, daemon=True).start()

    def _analyze_thread(self):
        try:
            result = app.analyzer.analyze_image(self.current_image)
            Clock.schedule_once(lambda dt: self._show_result(result))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_msg(f'分析失败: {e}'))
            Clock.schedule_once(lambda dt: self._reset_btn())

    def _show_result(self, result):
        if result is None:
            self._show_msg('未检测到人脸，请换张照片试试')
            self._reset_btn()
            return
        app = App.get_running_app()
        app.last_result = result
        # 跳转结果页
        app.root.current = 'result'
        app.root.get_screen('result').show_results(result)
        self._reset_btn()

    def _reset_btn(self):
        self.ids.analyze_btn.text = '🔍 分析'
        self.ids.analyze_btn.disabled = (self.current_image is None)

    def _show_msg(self, msg):
        popup = Popup(title='提示', content=Label(text=msg, color=(1,1,1,1)),
                      size_hint=(0.8, 0.3))
        popup.open()


class ResultScreen(Screen):
    """结果界面"""
    def show_results(self, result):
        content = self.ids.result_content
        content.clear_widgets()

        # 脸型
        if result.get('face_shape'):
            fs = result['face_shape']
            card = self._make_card('脸型分类', [
                ('形状', fs['shape']),
                ('置信度', f"{fs.get('confidence', 0):.1f}"),
                ('宽高比', f"{fs.get('wh_ratio', 0):.2f}"),
            ])
            content.add_widget(card)

        # 三庭
        if result.get('three_court'):
            tc = result['three_court']
            card = self._make_card('三庭比例', [
                ('上庭', f"{tc['upper']*100:.1f}% {'✓标准' if abs(tc['upper']-1/3)<.05 else '⚠偏差'}"),
                ('中庭', f"{tc['middle']*100:.1f}% {'✓标准' if abs(tc['middle']-1/3)<.05 else '⚠偏差'}"),
                ('下庭', f"{tc['lower']*100:.1f}% {'✓标准' if abs(tc['lower']-1/3)<.05 else '⚠偏差'}"),
            ])
            content.add_widget(card)

        # 五眼
        if result.get('five_eye'):
            fe = result['five_eye']
            card = self._make_card('五眼比例', [
                ('左眼', f"{fe['left_eye']*100:.1f}%"),
                ('眼距', f"{fe['gap']*100:.1f}% {'✓标准' if .16<fe['gap']<.28 else '⚠偏差'}"),
                ('右眼', f"{fe['right_eye']*100:.1f}%"),
            ])
            content.add_widget(card)

        # 灯光推荐
        if result.get('lighting'):
            lt = result['lighting']
            lines = [lt['config'], lt['tips']] + lt.get('lights', [])
            card = self._make_card('灯光推荐', [(f'💡', l) for l in lines])
            content.add_widget(card)

        # 调试建议
        if result.get('all_suggestions'):
            sug = result['all_suggestions']
            card = self._make_card('调试建议', [(f'▸', s) for s in sug])
            content.add_widget(card)

        # 保存经验按钮
        save_btn = Button(
            text='💾 保存此经验',
            size_hint_y=None, height=dp(48),
            background_color=(0.55, 0.36, 0.96, 1),
            color=(1,1,1,1), font_size=sp(15), bold=True
        )
        save_btn.bind(on_release=self._save_exp)
        content.add_widget(save_btn)

    def _make_card(self, title, items):
        """创建结果卡片"""
        card = BoxLayout(orientation='vertical', size_hint_y=None,
                         padding=dp(14), spacing=dp(6))
        card.bind(minimum_height=card.setter('height'))

        with card.canvas.before:
            Color(0.1, 0.1, 0.18, 1)
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
        card.bind(pos=lambda i,v: setattr(card.bg, 'pos', v),
                  size=lambda i,v: setattr(card.bg, 'size', v))

        # 标题
        title_lbl = Label(text=title, size_hint_y=None, height=dp(28),
                          font_size=sp(15), bold=True, color=(0.55, 0.36, 0.96, 1),
                          halign='left', text_size=(dp(300), None))
        card.add_widget(title_lbl)

        for label, value in items:
            row = BoxLayout(size_hint_y=None, height=dp(28))
            lbl = Label(text=label, size_hint_x=0.35, font_size=sp(13),
                        color=(0.6, 0.6, 0.7, 1), halign='left', text_size=(dp(100), None))
            val = Label(text=value, size_hint_x=0.65, font_size=sp(13),
                        color=(0.95, 0.95, 0.95, 1), halign='left', text_size=(dp(200), None))
            row.add_widget(lbl)
            row.add_widget(val)
            card.add_widget(row)

        return card

    def _save_exp(self, instance):
        """保存经验"""
        app = App.get_running_app()
        result = app.last_result
        if not result or not result.get('face_shape'):
            return
        fs = result['face_shape']
        sample = {
            'detected': fs['shape'],
            'correct': fs['shape'],
            'profile': fs.get('profile'),
            'wh_ratio': fs.get('wh_ratio'),
            'jawline': fs.get('jawline'),
            'note': '',
            'ts': int(__import__('time').time() * 1000),
        }
        app.save_experience(sample)
        popup = Popup(title='✅', content=Label(text='已保存到经验库'),
                      size_hint=(0.6, 0.25))
        popup.open()


class ExperienceScreen(Screen):
    """经验库界面"""
    def on_enter(self):
        self.load_data()

    def load_data(self):
        app = App.get_running_app()
        db = app.load_db()
        content = self.ids.exp_content
        content.clear_widgets()

        samples = db.get('samples', [])
        if not samples:
            content.add_widget(Label(
                text='暂无数据\n分析照片后修正保存',
                size_hint_y=None, height=dp(80),
                color=(0.4,0.4,0.5,1), font_size=sp(14), halign='center'))
            return

        # 统计
        counts = {}
        for s in samples:
            shape = s.get('correct', '?')
            counts[shape] = counts.get(shape, 0) + 1

        stat_text = f"📊 总样本: {len(samples)}    " + "  ".join(f"{k}:{v}" for k,v in sorted(counts.items(), key=lambda x:-x[1]))
        content.add_widget(Label(text=stat_text, size_hint_y=None, height=dp(36),
                                 font_size=sp(12), color=(0.6,0.6,0.7,1)))

        # 列表
        for i, s in enumerate(samples):
            row = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(8), dp(4)])
            with row.canvas.before:
                Color(0.1, 0.1, 0.18, 1)
                row.bg = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(8)])
            row.bind(pos=lambda i,v,bg=row.bg: setattr(bg,'pos',v),
                     size=lambda i,v,bg=row.bg: setattr(bg,'size',v))

            shape = s.get('correct', '?')
            det = s.get('detected', '')
            note = f"原判:{det}" if det != shape else ''
            txt = f"{shape}  {note}"
            lbl = Label(text=txt, font_size=sp(13), color=(0.9,0.9,0.95,1),
                        halign='left', text_size=(dp(250), None))
            row.add_widget(lbl)

            del_btn = Button(text='✕', size_hint_x=None, width=dp(36),
                             background_color=(0,0,0,0), color=(0.9,0.3,0.3,1),
                             font_size=sp(16))
            del_btn.bind(on_release=lambda x,idx=i: self._delete(idx))
            row.add_widget(del_btn)
            content.add_widget(row)

    def _delete(self, idx):
        app = App.get_running_app()
        db = app.load_db()
        samples = db.get('samples', [])
        if 0 <= idx < len(samples):
            samples.pop(idx)
            app.save_db(db)
            self.load_data()


# ═══════════════ App ═══════════════
class BeautyShapeApp(App):
    def build(self):
        self.title = 'BeautyShape'
        self.icon = 'icon.png' if os.path.exists(os.path.join(APP_DIR, 'icon.png')) else ''

        # 加载分析引擎
        from face_shape_engine import FaceShapeEngine
        self.analyzer = FaceShapeEngine()
        self.last_result = None

        return RootManager()

    @property
    def db_path(self):
        return os.path.join(self.user_data_dir, 'experience_db.json')

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return {'samples': []}

    def save_db(self, db):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    def save_experience(self, sample):
        db = self.load_db()
        db['samples'].append(sample)
        self.save_db(db)
        # 重载引擎经验
        self.analyzer.reload_experience()


class RootManager(ScreenManager):
    pass


if __name__ == '__main__':
    BeautyShapeApp().run()
