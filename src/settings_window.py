"""设置窗口：FluentWindow（隐藏导航） + SettingCardGroup，Windows 11 设置质感。

滑杆卡片直接绑定 ConfigItem;zoom 为浮点，QSlider 只有 int，
故 zoom 用自建 FloatSliderCard（内部按 0.1 步进缩放）。
"""

import sys
import winreg
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QKeySequenceEdit,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ConfigItem,
    FluentIcon,
    FluentWindow,
    MessageBox,
    PrimaryPushSettingCard,
    PushSettingCard,
    SettingCard,
    SettingCardGroup,
    Slider,
    SwitchSettingCard,
    qconfig,
)

from src.config import Config
from src.tray import make_icon

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "洞见"


def _autostart_command() -> str:
    """开机自启命令行：pythonw + main.pyw（静默无控制台）。"""
    exe = Path(sys.executable)
    if exe.name.lower() != "pythonw.exe":
        pw = exe.with_name("pythonw.exe")
        if pw.exists():
            exe = pw
    script = Path(__file__).resolve().parents[1] / "main.pyw"
    return f'"{exe}" "{script}"'


def set_autostart(enabled: bool) -> None:
    """写/删 HKCU Run 键；幂等，可安全重复调用。"""
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
    """浮点滑杆卡片：内部按 step 缩放为 int，显示保留小数。"""

    def __init__(self, config_item, icon, title, content, lo, hi, step=0.1, parent=None):
        super().__init__(icon, title, content, parent)
        self._item = config_item
        self._step = step

        self._label = QLabel(self)
        self._label.setObjectName("valueLabel")
        self._slider = Slider(Qt.Orientation.Horizontal, self)
        self._slider.setMinimumWidth(268)
        # round 而非 int:1.0/0.1=9.999…，int() 截断会把范围缩成 9–79
        self._slider.setRange(int(round(lo / step)), int(round(hi / step)))

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
    """单页设置窗口，导航面板隐藏。"""

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
                configItem=self.config.ctrl_peek, icon=FluentIcon.SEARCH,
                title="Ctrl 触发", content="按住 Ctrl 临时放大，松开收回",
            )
        )
        self.hotkey_card = PushSettingCard("点击修改", FluentIcon.PLAY, "常驻热键", self._hotkey_text())
        self.hotkey_card.clicked.connect(self._edit_hotkey)
        self.config.hotkey.valueChanged.connect(
            lambda _v: self.hotkey_card.setContent(self._hotkey_text())
        )
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
        reset_card = PrimaryPushSettingCard(
            "恢复默认设置", FluentIcon.ROTATE, "恢复默认", "将所有设置重置为初始值"
        )
        reset_card.clicked.connect(self._reset_all)
        general_group.addSettingCard(reset_card)
        layout.addWidget(general_group)

        layout.addStretch(1)
        scroll.setWidget(page)
        self.addSubInterface(scroll, FluentIcon.SETTING, "设置")
        self.navigationInterface.hide()  # 单页，隐藏导航面板

    def _hotkey_text(self) -> str:
        return f"当前：{self.config.hotkey.value}"

    def _edit_hotkey(self) -> None:
        """QKeySequenceEdit 直接感应用户键入的快捷键组合。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("设置常驻热键")
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("按下新的快捷键组合（须包含 Ctrl/Alt 之一）", dlg))
        editor = QKeySequenceEdit(dlg)
        editor.setMaximumSequenceLength(1)
        editor.setKeySequence(QKeySequence(_hotkey_to_qseq_text(self.config.hotkey.value)))
        editor.setFocus()
        layout.addWidget(editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dlg
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if not dlg.exec():
            return
        hotkey = _qseq_to_hotkey(
            editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        )
        if not hotkey:
            MessageBox("无效热键", "需包含 Ctrl/Alt 修饰键，且不含 Win 键", self).exec()
            return
        self.config.set(self.config.hotkey, hotkey)

    def _reset_all(self) -> None:
        box = MessageBox("恢复默认设置", "确定将所有设置恢复为默认值？", self)
        box.yesButton.setText("恢复")
        box.cancelButton.setText("取消")
        if box.exec():
            reset_all(self.config)

    def closeEvent(self, event) -> None:
        self.hide()  # 关窗隐藏，不退出
        event.ignore()


def _hotkey_to_qseq_text(hotkey: str) -> str:
    """'ctrl+alt+m' → 'Ctrl+Alt+M'(Qt PortableText;win 键记作 Meta)。"""
    names = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Meta"}
    return "+".join(names.get(p, p.capitalize()) for p in hotkey.split("+"))


def _qseq_to_hotkey(text: str) -> str | None:
    """PortableText('Ctrl+Alt+M') → 'ctrl+alt+m'。

    拒绝：Win 键（Meta，与系统冲突）、无 Ctrl/Alt 的组合（Shift 裸组合会干扰打字）。
    """
    names = {"Ctrl": "ctrl", "Alt": "alt", "Shift": "shift"}
    parts = [p.strip() for p in text.split("+")]
    if len(parts) < 2:
        return None
    key = parts[-1].lower()
    mods = parts[:-1]
    if "Meta" in mods:  # Win 键会触发系统快捷键
        return None
    result = [names[p] for p in mods if p in names]
    if not any(m in ("ctrl", "alt") for m in result) or not key:
        return None
    return "+".join(result + [key])


def reset_all(config) -> None:
    """将所有配置项恢复为默认值。"""
    for name in dir(Config):
        item = getattr(Config, name)
        if isinstance(item, ConfigItem):
            qconfig.set(item, item.defaultValue)
