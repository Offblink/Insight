"""设置窗口:FluentWindow(隐藏导航) + SettingCardGroup,Windows 11 设置质感。

滑杆卡片直接绑定 ConfigItem;zoom 为浮点,QSlider 只有 int,
故 zoom 用自建 FloatSliderCard(内部按 0.1 步进缩放)。
"""

import sys
import winreg
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QLabel, QScrollArea, QVBoxLayout, QWidget
from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    PushSettingCard,
    SettingCard,
    SettingCardGroup,
    Slider,
    SwitchSettingCard,
    qconfig,
)

from src.tray import make_icon

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "洞见"


def _autostart_command() -> str:
    """开机自启命令行:pythonw + main.pyw(静默无控制台)。"""
    exe = Path(sys.executable)
    if exe.name.lower() != "pythonw.exe":
        pw = exe.with_name("pythonw.exe")
        if pw.exists():
            exe = pw
    script = Path(__file__).resolve().parents[1] / "main.pyw"
    return f'"{exe}" "{script}"'


def set_autostart(enabled: bool) -> None:
    """写/删 HKCU Run 键;幂等,可安全重复调用。"""
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY)
    try:
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _autostart_command())
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


class FloatSliderCard(SettingCard):
    """浮点滑杆卡片:内部按 step 缩放为 int,显示保留小数。"""

    def __init__(self, config_item, icon, title, content, lo, hi, step=0.1, parent=None):
        super().__init__(icon, title, content, parent)
        self._item = config_item
        self._step = step

        self._label = QLabel(self)
        self._label.setObjectName("valueLabel")
        self._slider = Slider(Qt.Orientation.Horizontal, self)
        self._slider.setMinimumWidth(268)
        self._slider.setRange(int(lo / step), int(hi / step))

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self._slider, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self._slider.valueChanged.connect(self._on_slider)
        config_item.valueChanged.connect(lambda _v: self._refresh())
        self._refresh()

    def _refresh(self) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(int(round(self._item.value / self._step)))
        self._slider.blockSignals(False)
        self._label.setText(f"{self._item.value:g}")

    def _on_slider(self, value: int) -> None:
        qconfig.set(self._item, round(value * self._step, 2))
        self._label.setText(f"{self._item.value:g}")


class SettingsWindow(FluentWindow):
    """单页设置窗口,导航面板隐藏。"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("洞见设置")
        self.setWindowIcon(make_icon())
        self.resize(560, 640)
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("settingsInterface")  # addSubInterface 要求非空 objectName
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── 放大 ──
        zoom_group = SettingCardGroup("放大", page)
        zoom_group.addSettingCard(
            FloatSliderCard(self.config.zoom, FluentIcon.ZOOM, "放大倍数", "1.0 – 8.0", 1.0, 8.0, 0.1)
        )
        zoom_group.addSettingCard(
            FloatSliderCard(self.config.size, FluentIcon.FULL_SCREEN, "窗口大小", "120 – 400 px", 120, 400, 5)
        )
        zoom_group.addSettingCard(
            FloatSliderCard(self.config.offset, FluentIcon.MOVE, "偏移距离", "0 – 60 px", 0, 60, 1)
        )
        layout.addWidget(zoom_group)

        # ── 交互 ──
        interact_group = SettingCardGroup("交互", page)
        interact_group.addSettingCard(
            SwitchSettingCard(
                configItem=self.config.right_click, icon=FluentIcon.SEARCH,
                title="右键触发", content="按住右键临时放大,松开收回",
            )
        )
        self.hotkey_card = PushSettingCard("点击修改", FluentIcon.PLAY, "常驻热键", self._hotkey_text())
        self.hotkey_card.clicked.connect(self._edit_hotkey)
        interact_group.addSettingCard(self.hotkey_card)
        interact_group.addSettingCard(
            SwitchSettingCard(
                configItem=self.config.follow_on_start, icon=FluentIcon.RIGHT_ARROW,
                title="启动时跟随", content="启动后直接进入常驻跟随模式",
            )
        )
        layout.addWidget(interact_group)

        # ── 常规 ──
        general_group = SettingCardGroup("常规", page)
        general_group.addSettingCard(
            SwitchSettingCard(
                configItem=self.config.autostart, icon=FluentIcon.SPEED_HIGH,
                title="开机自启", content="登录 Windows 后静默运行",
            )
        )
        layout.addWidget(general_group)

        layout.addStretch(1)
        scroll.setWidget(page)
        self.addSubInterface(scroll, FluentIcon.SETTING, "设置")
        self.navigationInterface.hide()  # 单页,隐藏导航面板

    def _hotkey_text(self) -> str:
        return f"当前: {self.config.hotkey.value}"

    def _edit_hotkey(self) -> None:
        text, ok = QInputDialog.getText(self, "常驻热键", "格式: ctrl+alt+m", text=self.config.hotkey.value)
        if ok and text.strip():
            self.config.set(self.config.hotkey, text.strip())
            self.hotkey_card.setContent(self._hotkey_text())

    def closeEvent(self, event) -> None:
        self.hide()  # 关窗隐藏,不退出
        event.ignore()
