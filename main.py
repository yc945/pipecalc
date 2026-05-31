#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
农村安全供水管道水力计算  Android/Kivy版
参照: GB 50013-2018 | SL 310-2019 | GB/T 10002.1 | 水力计算手册
OD <= 110mm 免费使用，OD > 110mm 需注册激活
"""

# ── Config 必须在其他 kivy 导入之前 ──────────────────────────────────────────
from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'system')
Config.set('graphics', 'resizable', '1')

import os, sys, math, hashlib, uuid
from datetime import datetime
from typing import Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
import kivy

# 白色背景（解决默认黑色问题）
Window.clearcolor = (0.96, 0.96, 0.97, 1)
Window.softinput_mode = 'below_target'


# ══════════════════════════════════════════════════════════════════════════════
# CJK 字体（优先 Windows simhei → Android 系统 → 本地 → 内置兜底）
# ══════════════════════════════════════════════════════════════════════════════
def _find_cjk_font() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    _wf = (os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Fonts') + os.sep
           if sys.platform == 'win32' else '/mnt/c/Windows/Fonts/')
    candidates = [
        os.path.join(_here, 'fonts', 'CJK.ttf'),
        os.path.join(_here, 'fonts', 'simhei.ttf'),
        _wf + 'simhei.ttf',
        _wf + 'simkai.ttf',
        _wf + 'STFANGSO.TTF',
        _wf + 'msyh.ttc',
        '/system/fonts/NotoSansCJK-Regular.ttc',
        '/system/fonts/DroidSansFallback.ttf',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    ]
    for fp in candidates:
        if os.path.exists(fp):
            return fp
    return os.path.join(kivy.kivy_data_dir, 'fonts', 'Roboto-Regular.ttf')

try:
    LabelBase.register('CJK', fn_regular=_find_cjk_font())
except Exception:
    LabelBase.register('CJK', fn_regular=os.path.join(
        kivy.kivy_data_dir, 'fonts', 'Roboto-Regular.ttf'))


# ══════════════════════════════════════════════════════════════════════════════
# 注册验证系统（与 keygen.py 保持一致）
# ══════════════════════════════════════════════════════════════════════════════
_LICENSE_SECRET = "YCShuiLi@2025#HydroCalc"
FREE_OD_MAX     = 110          # OD <= 110mm 免费；> 110mm 需注册


def _compute_license(device_id: str) -> str:
    raw = hashlib.sha256(
        f"{device_id.strip().upper()}{_LICENSE_SECRET}".encode('utf-8')
    ).hexdigest().upper()
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


def verify_license(device_id: str, code: str) -> bool:
    return code.strip().upper() == _compute_license(device_id)


class LicenseManager:
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._id_file  = os.path.join(data_dir, '.device_id')
        self._lic_file = os.path.join(data_dir, '.license')
        self._device_id:  Optional[str] = None
        self._registered: Optional[bool] = None

    def get_device_id(self) -> str:
        if self._device_id:
            return self._device_id
        if os.path.exists(self._id_file):
            try:
                did = open(self._id_file).read().strip()
                if did:
                    self._device_id = did
                    return did
            except Exception:
                pass
        did = str(uuid.uuid4()).replace('-', '')[:16].upper()
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            open(self._id_file, 'w').write(did)
        except Exception:
            pass
        self._device_id = did
        return did

    def is_registered(self) -> bool:
        if self._registered is not None:
            return self._registered
        try:
            if os.path.exists(self._lic_file):
                code = open(self._lic_file).read().strip()
                if code and verify_license(self.get_device_id(), code):
                    self._registered = True
                    return True
        except Exception:
            pass
        self._registered = False
        return False

    def activate(self, code: str) -> bool:
        if verify_license(self.get_device_id(), code):
            try:
                os.makedirs(self._data_dir, exist_ok=True)
                open(self._lic_file, 'w').write(code.strip().upper())
                self._registered = True
                return True
            except Exception:
                pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# PVC-U 管材规格表  GB/T 10002.1-2021
# ══════════════════════════════════════════════════════════════════════════════
PVC_SPECS = {
    20:  {0.63: None, 1.0: 1.5,  1.25: 1.5,  1.6: 1.5 },
    25:  {0.63: 1.5,  1.0: 1.5,  1.25: 1.5,  1.6: 1.9 },
    32:  {0.63: 1.5,  1.0: 1.6,  1.25: 2.0,  1.6: 2.4 },
    40:  {0.63: 1.5,  1.0: 1.8,  1.25: 2.4,  1.6: 3.0 },
    50:  {0.63: 1.8,  1.0: 2.4,  1.25: 3.0,  1.6: 3.7 },
    63:  {0.63: 1.9,  1.0: 3.0,  1.25: 3.8,  1.6: 4.7 },
    75:  {0.63: 2.2,  1.0: 3.6,  1.25: 4.5,  1.6: 5.6 },
    90:  {0.63: 2.7,  1.0: 4.3,  1.25: 5.4,  1.6: 6.7 },
    110: {0.63: 3.2,  1.0: 5.3,  1.25: 6.6,  1.6: 8.1 },   # ← 免费上限
    125: {0.63: 3.7,  1.0: 6.0,  1.25: 7.4,  1.6: 9.2 },   # 以下需注册
    140: {0.63: 4.1,  1.0: 6.7,  1.25: 8.3,  1.6: 10.3},
    160: {0.63: 4.7,  1.0: 7.7,  1.25: 9.5,  1.6: 11.8},
    200: {0.63: 5.9,  1.0: 9.6,  1.25: 11.9, 1.6: 14.7},
    250: {0.63: 7.3,  1.0: 11.9, 1.25: 14.8, 1.6: 18.4},
    315: {0.63: 9.2,  1.0: 15.0, 1.25: 18.7, 1.6: 23.2},
}
OD_LIST = [str(k) for k in sorted(PVC_SPECS.keys())]
PN_LIST  = ['0.63', '1.0', '1.25', '1.6']
HW_C     = 140
V_MIN, V_MAX = 0.3, 2.5


# ══════════════════════════════════════════════════════════════════════════════
# 水力计算
# ══════════════════════════════════════════════════════════════════════════════
def inner_diameter(od: int, pn: float) -> Optional[float]:
    wall = PVC_SPECS.get(od, {}).get(pn)
    return None if wall is None else od - 2 * wall

def hw_headloss(Q: float, D_mm: float, L: float, C: int = HW_C) -> float:
    q, d = Q / 3600.0, D_mm / 1000.0
    if q <= 0 or d <= 0 or L <= 0:
        return 0.0
    return 10.67 * L * (q ** 1.852) / ((C ** 1.852) * (d ** 4.87))

def flow_velocity(Q: float, D_mm: float) -> float:
    q, d = Q / 3600.0, D_mm / 1000.0
    a = math.pi * d ** 2 / 4.0
    return q / a if a > 0 else 0.0

def max_flow_by_head(D_mm: float, L: float, avail: float, C: int = HW_C) -> float:
    hf = avail / 1.10
    if hf <= 0:
        return 0.0
    d = D_mm / 1000.0
    return ((hf * (C ** 1.852) * (d ** 4.87)) / (10.67 * L)) ** (1 / 1.852) * 3600

def vel_warn(v: float) -> str:
    if v < V_MIN: return f'  流速{v:.3f}m/s偏低(<{V_MIN}) 易淤积'
    if v > V_MAX: return f'  流速{v:.3f}m/s过高(>{V_MAX}) 水锤风险'
    return ''


# ══════════════════════════════════════════════════════════════════════════════
# 注册弹窗（Python 构建，不依赖 KV）
# ══════════════════════════════════════════════════════════════════════════════
class RegisterPopup(Popup):
    def __init__(self, on_cancel=None, **kw):
        kw.setdefault('title', '激活注册  OD>110mm 专业版')
        kw.setdefault('title_color', (0.1, 0.36, 0.54, 1))
        kw.setdefault('title_size', sp(14))
        kw.setdefault('title_font', 'CJK')
        kw.setdefault('size_hint', (0.92, None))
        kw.setdefault('height', dp(380))
        kw.setdefault('separator_color', (0.18, 0.50, 0.72, 1))
        kw.setdefault('background_color', (0.97, 0.97, 0.98, 1))
        super().__init__(**kw)
        self._on_cancel = on_cancel
        self._build()

    def _lbl(self, text, size=13, color=(0.15, 0.15, 0.2, 1), bold=False,
             h=None, halign='left'):
        lbl = Label(
            text=text, font_name='CJK', font_size=sp(size),
            color=color, bold=bold,
            size_hint_y=None, height=h or dp(28),
            halign=halign, valign='middle',
        )
        lbl.bind(size=lambda w, *_: setattr(w, 'text_size', w.size))
        return lbl

    def _build(self):
        app = App.get_running_app()
        did = app.license_mgr.get_device_id()

        box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(6))

        box.add_widget(self._lbl(
            'OD 125~315mm 管径为专业版功能\n请将设备码发给开发者获取注册码',
            size=12, color=(0.5, 0.1, 0.1, 1), h=dp(44)))

        # 设备码行
        box.add_widget(self._lbl('设备码（发给开发者）:', size=12,
                                  color=(0.3, 0.3, 0.3, 1)))
        did_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self._did_inp = TextInput(
            text=did, readonly=True, font_name='CJK', font_size=sp(13),
            background_color=(0.90, 0.95, 1, 1),
            foreground_color=(0.05, 0.05, 0.35, 1))
        copy_btn = Button(
            text='复制', font_name='CJK', font_size=sp(13),
            size_hint_x=None, width=dp(58),
            background_color=(0.12, 0.46, 0.70, 1),
            background_normal='', color=(1, 1, 1, 1))
        copy_btn.bind(on_press=lambda *_: self._copy(did))
        did_row.add_widget(self._did_inp)
        did_row.add_widget(copy_btn)
        box.add_widget(did_row)

        # 注册码输入
        box.add_widget(self._lbl('输入注册码（XXXX-XXXX-XXXX-XXXX）:',
                                  size=12, color=(0.3, 0.3, 0.3, 1)))
        self._code_inp = TextInput(
            hint_text='XXXX-XXXX-XXXX-XXXX',
            font_name='CJK', font_size=sp(15),
            background_color=(0.93, 0.97, 1, 1),
            foreground_color=(0, 0, 0, 1),
            size_hint_y=None, height=dp(48))
        box.add_widget(self._code_inp)

        # 状态行
        self._status = self._lbl('', size=12, color=(0.8, 0.1, 0.1, 1), h=dp(24))
        box.add_widget(self._status)

        # 按钮行
        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        act = Button(text='激活注册', font_name='CJK', font_size=sp(15),
                     bold=True, background_color=(0.09, 0.64, 0.35, 1),
                     background_normal='', color=(1, 1, 1, 1))
        act.bind(on_press=self._activate)
        cancel = Button(text='取消', font_name='CJK', font_size=sp(13),
                        size_hint_x=None, width=dp(80),
                        background_color=(0.55, 0.55, 0.55, 1),
                        background_normal='', color=(1, 1, 1, 1))
        cancel.bind(on_press=self._cancel)
        btn_row.add_widget(act)
        btn_row.add_widget(cancel)
        box.add_widget(btn_row)

        self.content = box

    def _copy(self, text):
        try:
            Clipboard.copy(text)
            self._status.text = '设备码已复制到剪贴板'
            self._status.color = (0.1, 0.5, 0.1, 1)
        except Exception:
            self._status.text = '复制失败，请手动选择'

    def _activate(self, *_):
        code = self._code_inp.text.strip()
        if not code:
            self._status.text = '请输入注册码'
            self._status.color = (0.8, 0.1, 0.1, 1)
            return
        app = App.get_running_app()
        if app.license_mgr.activate(code):
            self._status.text = '注册成功！欢迎使用专业版'
            self._status.color = (0.1, 0.5, 0.1, 1)
            Clock.schedule_once(lambda dt: self.dismiss(), 1.2)
        else:
            self._status.text = '注册码无效，请重新检查'
            self._status.color = (0.8, 0.1, 0.1, 1)

    def _cancel(self, *_):
        if self._on_cancel:
            self._on_cancel()
        self.dismiss()


# ══════════════════════════════════════════════════════════════════════════════
# KV 界面布局（所有控件均设 font_name: 'CJK'，所有 Screen 设白色背景）
# ══════════════════════════════════════════════════════════════════════════════
KV = '''
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

# ── 全局字体覆盖 ──────────────────────────────────────────────────────────────
<Label>:
    font_name: 'CJK'
<Button>:
    font_name: 'CJK'
<TextInput>:
    font_name: 'CJK'
<Spinner>:
    font_name: 'CJK'
<SpinnerOption>:
    font_name: 'CJK'

# ── 可复用模板 ────────────────────────────────────────────────────────────────
<ML@Label>:
    size_hint_x: 0.46
    font_size: sp(13)
    font_name: 'CJK'
    halign: 'right'
    valign: 'middle'
    text_size: self.size
    color: 0.15, 0.15, 0.2, 1
    padding: dp(4), 0

<MI@TextInput>:
    size_hint_x: 0.54
    font_size: sp(14)
    font_name: 'CJK'
    multiline: False
    background_color: 0.94, 0.96, 1, 1
    foreground_color: 0, 0, 0, 1
    padding: dp(6), dp(8)
    cursor_color: 0.1, 0.36, 0.54, 1

<MS@Spinner>:
    size_hint_x: 0.54
    font_size: sp(13)
    font_name: 'CJK'
    background_color: 0.12, 0.46, 0.70, 1
    background_normal: ''
    color: 1, 1, 1, 1
    option_cls: 'MSO'

<MSO@SpinnerOption>:
    font_size: sp(13)
    font_name: 'CJK'
    height: dp(44)
    background_color: 0.92, 0.96, 1, 1

<SH@Label>:
    size_hint_y: None
    height: dp(30)
    font_size: sp(13)
    font_name: 'CJK'
    bold: True
    color: 1, 1, 1, 1
    halign: 'left'
    valign: 'middle'
    text_size: self.size
    padding: dp(8), 0
    canvas.before:
        Color:
            rgba: 0.18, 0.50, 0.72, 1
        Rectangle:
            pos: self.pos
            size: self.size

<FR@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(50)
    spacing: dp(4)
    padding: dp(8), dp(3)

<CB@Button>:
    size_hint_y: None
    height: dp(54)
    font_size: sp(16)
    font_name: 'CJK'
    bold: True
    background_color: 0.09, 0.64, 0.35, 1
    background_normal: ''
    color: 1, 1, 1, 1

<NB@Button>:
    font_name: 'CJK'
    background_normal: ''
    background_color: 0.1, 0.36, 0.54, 1
    color: 1, 1, 1, 1
    font_size: sp(12)
    bold: True

# ── 根布局 ────────────────────────────────────────────────────────────────────
<RootBox>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(46)
        canvas.before:
            Color:
                rgba: 0.1, 0.36, 0.54, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: '农村供水管道水力计算'
            font_size: sp(16)
            font_name: 'CJK'
            bold: True
            color: 1, 1, 1, 1

    ScreenManager:
        id: sm

    BoxLayout:
        size_hint_y: None
        height: dp(50)
        spacing: dp(1)
        padding: dp(1)
        canvas.before:
            Color:
                rgba: 0.08, 0.28, 0.42, 1
            Rectangle:
                pos: self.pos
                size: self.size
        NB:
            text: '▼ 重力流'
            on_press: app.go('gravity')
        NB:
            text: '▲ 水泵提水'
            on_press: app.go('pump')
        NB:
            text: '○ 管材表'
            on_press: app.go('pvc')

# ── 重力流界面 ────────────────────────────────────────────────────────────────
<GravityScreen>:
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size
    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(2)
            padding: 0, 0, 0, dp(20)

            SH:
                text: '  高程参数（现场实测）'
            FR:
                ML:
                    text: '水源点高程 Z1(m):'
                MI:
                    id: gz1
                    text: '100.00'
            FR:
                ML:
                    text: '用水点高程 Z2(m):'
                MI:
                    id: gz2
                    text: '93.00'

            SH:
                text: '  管道及流量参数'
            FR:
                ML:
                    text: '管道长度 L(m):'
                MI:
                    id: gL
                    text: '500'
            FR:
                ML:
                    text: '设计流量 Q(m3/h):'
                MI:
                    id: gQ
                    text: '5.0'

            SH:
                text: '  管材选择（PVC-U）'
            FR:
                ML:
                    text: '外径 OD(mm):'
                MS:
                    id: god
                    text: '110'
                    values: ['20','25','32','40','50','63','75','90','110','125','140','160','200','250','315']
                    on_text: root.upd_id()
            FR:
                ML:
                    text: '压力等级 PN(MPa):'
                MS:
                    id: gpn
                    text: '1.0'
                    values: ['0.63','1.0','1.25','1.6']
                    on_text: root.upd_id()
            FR:
                ML:
                    text: '管道内径:'
                Label:
                    id: gid
                    text: '99.4 mm'
                    font_size: sp(14)
                    font_name: 'CJK'
                    bold: True
                    color: 0.1, 0.4, 0.7, 1
                    size_hint_x: 0.54
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    padding: dp(6), 0
            FR:
                ML:
                    text: '局部损失(%):'
                MI:
                    id: glocal
                    text: '10'
            FR:
                ML:
                    text: '最小剩余水头(m):'
                MI:
                    id: gminp
                    text: '5.0'

            BoxLayout:
                size_hint_y: None
                height: dp(62)
                padding: dp(8), dp(4)
                CB:
                    text: '开  始  计  算'
                    on_press: root.calc()

            SH:
                text: '  计算结果'
            Label:
                id: gres
                text: '请填写参数后点击"开始计算"'
                font_size: sp(12)
                font_name: 'CJK'
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: max(self.texture_size[1] + dp(16), dp(80))
                padding: dp(8), dp(6)
                color: 0.08, 0.08, 0.15, 1

# ── 水泵提水界面 ──────────────────────────────────────────────────────────────
<PumpScreen>:
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size
    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(2)
            padding: 0, 0, 0, dp(20)

            SH:
                text: '  高程参数（现场实测）'
            FR:
                ML:
                    text: '泵站地面高程 Z1(m):'
                MI:
                    id: pz1
                    text: '85.00'
            FR:
                ML:
                    text: '水源最低水位(m):'
                MI:
                    id: pzwl
                    text: '83.50'
            FR:
                ML:
                    text: '用水点高程 Z2(m):'
                MI:
                    id: pz2
                    text: '120.00'

            SH:
                text: '  水泵参数'
            FR:
                ML:
                    text: '水泵额定扬程 H(m):'
                MI:
                    id: pH
                    text: '60.0'
            FR:
                ML:
                    text: '水泵额定流量(m3/h):'
                MI:
                    id: pQp
                    text: '10.0'

            SH:
                text: '  管道参数'
            FR:
                ML:
                    text: '管道长度 L(m):'
                MI:
                    id: pL
                    text: '1000'
            FR:
                ML:
                    text: '设计流量 Q(m3/h):'
                MI:
                    id: pQ
                    text: '10.0'

            SH:
                text: '  管材选择（PVC-U）'
            FR:
                ML:
                    text: '外径 OD(mm):'
                MS:
                    id: pod
                    text: '110'
                    values: ['20','25','32','40','50','63','75','90','110','125','140','160','200','250','315']
                    on_text: root.upd_id()
            FR:
                ML:
                    text: '压力等级 PN(MPa):'
                MS:
                    id: ppn
                    text: '1.0'
                    values: ['0.63','1.0','1.25','1.6']
                    on_text: root.upd_id()
            FR:
                ML:
                    text: '管道内径:'
                Label:
                    id: pid
                    text: '99.4 mm'
                    font_size: sp(14)
                    font_name: 'CJK'
                    bold: True
                    color: 0.1, 0.4, 0.7, 1
                    size_hint_x: 0.54
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    padding: dp(6), 0
            FR:
                ML:
                    text: '局部损失(%):'
                MI:
                    id: plocal
                    text: '10'
            FR:
                ML:
                    text: '最小剩余水头(m):'
                MI:
                    id: pminp
                    text: '5.0'

            BoxLayout:
                size_hint_y: None
                height: dp(62)
                padding: dp(8), dp(4)
                CB:
                    text: '开  始  计  算'
                    on_press: root.calc()

            SH:
                text: '  计算结果'
            Label:
                id: pres
                text: '请填写参数后点击"开始计算"'
                font_size: sp(12)
                font_name: 'CJK'
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: max(self.texture_size[1] + dp(16), dp(80))
                padding: dp(8), dp(6)
                color: 0.08, 0.08, 0.15, 1

# ── PVC 管材表界面 ────────────────────────────────────────────────────────────
<PvcScreen>:
    canvas.before:
        Color:
            rgba: 0.96, 0.96, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'

        SH:
            text: '  PVC-U 管材规格（GB/T 10002.1）'

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(8), dp(6)
            spacing: dp(8)
            Label:
                text: '选择压力等级 PN(MPa):'
                font_size: sp(13)
                font_name: 'CJK'
                size_hint_x: 0.55
                halign: 'right'
                valign: 'middle'
                text_size: self.size
            Spinner:
                id: pvc_pn
                text: '1.0'
                values: ['0.63','1.0','1.25','1.6']
                size_hint_x: 0.45
                font_size: sp(13)
                font_name: 'CJK'
                background_color: 0.12, 0.46, 0.70, 1
                background_normal: ''
                color: 1, 1, 1, 1
                option_cls: 'MSO'
                on_text: root.refresh_table()

        BoxLayout:
            size_hint_y: None
            height: dp(34)
            padding: dp(4), 0
            canvas.before:
                Color:
                    rgba: 0.82, 0.89, 0.96, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: '外径OD(mm)'
                font_size: sp(13)
                font_name: 'CJK'
                bold: True
                color: 0.1, 0.2, 0.4, 1
            Label:
                text: '壁厚e(mm)'
                font_size: sp(13)
                font_name: 'CJK'
                bold: True
                color: 0.1, 0.2, 0.4, 1
            Label:
                text: '内径D(mm)'
                font_size: sp(13)
                font_name: 'CJK'
                bold: True
                color: 0.1, 0.35, 0.1, 1

        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: pvc_grid
                cols: 3
                size_hint_y: None
                height: self.minimum_height
                row_default_height: dp(38)
                spacing: dp(1), dp(1)
                padding: dp(4), dp(2)
'''


# ══════════════════════════════════════════════════════════════════════════════
# Screen 类
# ══════════════════════════════════════════════════════════════════════════════

class RootBox(BoxLayout):
    pass


def _is_premium_od(od: int) -> bool:
    return od > FREE_OD_MAX


def _check_license_for_od(od: int, on_cancel_reset) -> bool:
    """若 OD 为付费规格且未注册，弹出注册窗并返回 False"""
    if not _is_premium_od(od):
        return True
    app = App.get_running_app()
    if app.license_mgr.is_registered():
        return True
    # 弹出注册框，取消时回调重置
    Clock.schedule_once(
        lambda dt: RegisterPopup(on_cancel=on_cancel_reset).open(), 0.05)
    return False


class GravityScreen(Screen):
    _lock = False   # 防止 Spinner 回调递归

    def upd_id(self, *_):
        if self._lock:
            return
        try:
            od = int(self.ids.god.text)
            pn = float(self.ids.gpn.text)
        except Exception:
            return
        if not _check_license_for_od(od, self._reset_od):
            return
        d = inner_diameter(od, pn)
        self.ids.gid.text = f'{d:.1f} mm' if d else '无此规格'

    def _reset_od(self):
        self._lock = True
        self.ids.god.text = str(FREE_OD_MAX)
        self._lock = False
        self.upd_id()

    def calc(self):
        try:
            z1 = float(self.ids.gz1.text)
            z2 = float(self.ids.gz2.text)
            L  = float(self.ids.gL.text)
            Q  = float(self.ids.gQ.text)
            od = int(self.ids.god.text)
            pn = float(self.ids.gpn.text)
            kl = float(self.ids.glocal.text) / 100.0
            mp = float(self.ids.gminp.text)
        except ValueError:
            self.ids.gres.text = '错误: 请检查所有输入项为有效数字'
            return

        if not _check_license_for_od(od, self._reset_od):
            self.ids.gres.text = f'OD {od}mm 需注册后使用，请先完成激活'
            return

        D = inner_diameter(od, pn)
        if not D:
            self.ids.gres.text = '错误: 所选OD/PN无对应规格'
            return

        hf = hw_headloss(Q, D, L)
        hj = hf * kl;  ht = hf + hj
        dz = z1 - z2;  res = dz - ht
        v  = flow_velocity(Q, D)
        i  = hf / L * 1000.0
        qm = max_flow_by_head(D, L, dz - mp) if dz > mp else 0.0
        ok = res >= mp

        t = [
            '═════════════════════════',
            '   重力流水力计算报告',
            '═════════════════════════',
            f'Z1={z1:.2f}m  Z2={z2:.2f}m',
            f'高程差={dz:.3f}m  管长={L:.0f}m',
            f'Q={Q:.3f}m3/h',
            f'OD{od}/PN{pn}/D={D:.1f}mm',
            '─────────────────────────',
            f'沿程损失 hf = {hf:.4f} m',
            f'局部损失 hj = {hj:.4f} m',
            f'总水头损失  = {ht:.4f} m',
            f'水力坡降 i  = {i:.2f} ‰',
            f'管内流速 v  = {v:.4f} m/s',
            '─────────────────────────',
            f'可用高程差   = {dz:.3f} m',
            f'剩余水头     = {res:.3f} m',
            f'最低要求水头 = {mp:.1f} m',
            f'最大可供流量 = {qm:.2f} m3/h',
            '═════════════════════════',
            ('  结论: 可以供水' if ok else '  结论: 无法供水'),
        ]
        if ok:
            t.append(f'  剩余{res:.2f}m >= 要求{mp:.1f}m')
        else:
            t.append(f'  缺水头 {mp - res:.3f} m')
            t.append('  建议: 增大管径或加压泵')
        w = vel_warn(v)
        if w:
            t.append(w)
        t.append(f'\n{datetime.now():%Y-%m-%d %H:%M}')
        self.ids.gres.text = '\n'.join(t)


class PumpScreen(Screen):
    _lock = False

    def upd_id(self, *_):
        if self._lock:
            return
        try:
            od = int(self.ids.pod.text)
            pn = float(self.ids.ppn.text)
        except Exception:
            return
        if not _check_license_for_od(od, self._reset_od):
            return
        d = inner_diameter(od, pn)
        self.ids.pid.text = f'{d:.1f} mm' if d else '无此规格'

    def _reset_od(self):
        self._lock = True
        self.ids.pod.text = str(FREE_OD_MAX)
        self._lock = False
        self.upd_id()

    def calc(self):
        try:
            z1  = float(self.ids.pz1.text)
            zwl = float(self.ids.pzwl.text)
            z2  = float(self.ids.pz2.text)
            H   = float(self.ids.pH.text)
            Qp  = float(self.ids.pQp.text)
            L   = float(self.ids.pL.text)
            Q   = float(self.ids.pQ.text)
            od  = int(self.ids.pod.text)
            pn  = float(self.ids.ppn.text)
            kl  = float(self.ids.plocal.text) / 100.0
            mp  = float(self.ids.pminp.text)
        except ValueError:
            self.ids.pres.text = '错误: 请检查所有输入项为有效数字'
            return

        if not _check_license_for_od(od, self._reset_od):
            self.ids.pres.text = f'OD {od}mm 需注册后使用，请先完成激活'
            return

        D = inner_diameter(od, pn)
        if not D:
            self.ids.pres.text = '错误: 所选OD/PN无对应规格'
            return

        nh  = H + zwl - z2
        hf  = hw_headloss(Q, D, L)
        hj  = hf * kl;  ht = hf + hj
        res = nh - ht
        v   = flow_velocity(Q, D)
        i   = hf / L * 1000.0
        qm  = max_flow_by_head(D, L, nh - mp) if nh > mp else 0.0
        ok  = res >= mp
        geo = z2 - zwl

        t = [
            '═════════════════════════',
            '   水泵提水水力计算报告',
            '═════════════════════════',
            f'Zwl={zwl:.2f}m  Z2={z2:.2f}m',
            f'几何扬程={geo:.2f}m  L={L:.0f}m',
            f'泵扬程H={H:.2f}m  Q={Q:.3f}m3/h',
            f'OD{od}/PN{pn}/D={D:.1f}mm',
            '─────────────────────────',
            f'沿程损失 hf = {hf:.4f} m',
            f'局部损失 hj = {hj:.4f} m',
            f'总水头损失  = {ht:.4f} m',
            f'水力坡降 i  = {i:.2f} ‰',
            f'管内流速 v  = {v:.4f} m/s',
            '─────────────────────────',
            f'净可用扬程 =H+Zwl-Z2={nh:.3f}m',
            f'总损失     = {ht:.3f} m',
            f'剩余水头   = {res:.3f} m',
            f'最低要求   = {mp:.1f} m',
            f'最大流量   = {qm:.2f} m3/h',
            '═════════════════════════',
            ('  结论: 可以供水' if ok else '  结论: 无法供水'),
        ]
        if ok:
            t.append(f'  剩余{res:.2f}m >= 要求{mp:.1f}m')
        else:
            needed = ht + geo + mp
            t.append(f'  需扬程>={needed:.2f}m 现{H:.2f}m')
            t.append('  建议: 换大扬程泵或增大管径')
        if Q > Qp * 1.05:
            t.append(f'  流量超泵额定{Qp:.1f}m3/h')
        if z1 - zwl > 6.0:
            t.append(f'  吸水高度{z1-zwl:.1f}m>6m 请核查!')
        w = vel_warn(v)
        if w:
            t.append(w)
        t.append(f'\n{datetime.now():%Y-%m-%d %H:%M}')
        self.ids.pres.text = '\n'.join(t)


class PvcScreen(Screen):

    def on_enter(self, *_):
        self.refresh_table()

    def refresh_table(self, *_):
        grid = self.ids.pvc_grid
        grid.clear_widgets()
        try:
            pn = float(self.ids.pvc_pn.text)
        except Exception:
            return

        app = App.get_running_app()
        registered = app.license_mgr.is_registered()

        for idx, od in enumerate(sorted(PVC_SPECS.keys())):
            premium = _is_premium_od(od)
            wall    = PVC_SPECS[od].get(pn)

            if premium and not registered:
                od_txt   = f'{od} *'
                wall_txt = '--'
                id_txt   = '需注册'
                c_id = (0.65, 0.15, 0.15, 1)
            else:
                od_txt   = str(od)
                wall_txt = f'{wall:.1f}' if wall else '—'
                id_txt   = f'{od - 2*wall:.1f}' if wall else '—'
                c_id = (0.05, 0.45, 0.10, 1) if wall else (0.60, 0.60, 0.60, 1)

            base = (0.08, 0.12, 0.30, 1) if idx % 2 == 0 else (0.20, 0.20, 0.25, 1)

            for txt, clr in [(od_txt, base), (wall_txt, base), (id_txt, c_id)]:
                grid.add_widget(Label(
                    text=txt, font_name='CJK', font_size=sp(13), color=clr))


# ══════════════════════════════════════════════════════════════════════════════
# App
# ══════════════════════════════════════════════════════════════════════════════

class PipeCalcApp(App):
    license_mgr: LicenseManager = None   # type: ignore

    def build(self):
        self.license_mgr = LicenseManager(self.user_data_dir)
        Builder.load_string(KV)
        root = RootBox()
        sm   = root.ids.sm
        sm.transition = FadeTransition(duration=0.15)
        sm.add_widget(GravityScreen(name='gravity'))
        sm.add_widget(PumpScreen(name='pump'))
        sm.add_widget(PvcScreen(name='pvc'))
        return root

    def go(self, name: str):
        self.root.ids.sm.current = name


if __name__ == '__main__':
    PipeCalcApp().run()
