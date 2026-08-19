"""系统托盘：图标（运行时绘制）与菜单。

菜单结构：
- 倍率预设（1.5x / 2x / 2.5x / 3x / 5x，当前倍率勾选）
- 跟随模式（勾选，切换常驻跟随）
- 设置…
- 退出
双击托盘 = 切换常驻跟随。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

_ACCENT = "#009faa"
_ZOOM_PRESETS = (1.5, 2.0, 2.5, 3.0, 5.0)


def make_icon(size: int = 64) -> QIcon:
    """运行时绘制放大镜图标（圆环 + 手柄），避免二进制资源文件。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    ring = QPen(QColor(_ACCENT), size * 0.09)
    ring.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(ring)
    painter.drawEllipse(int(size * 0.18), int(size * 0.18), int(size * 0.48), int(size * 0.48))

    handle = QPen(QColor(_ACCENT), size * 0.12)
    handle.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(handle)
    painter.drawLine(int(size * 0.56), int(size * 0.56), int(size * 0.82), int(size * 0.82))

    painter.end()
    return QIcon(pixmap)


class TrayController(QSystemTrayIcon):
    """托盘控制器：持有图标与菜单，动作直接驱动 config / magnifier。"""

    def __init__(self, config, magnifier, on_open_settings=None):
        super().__init__(make_icon())
        self.config = config
        self.magnifier = magnifier
        self._on_open_settings = on_open_settings or (lambda: None)
        self.setToolTip("Insight")
        self._zoom_actions: dict[float, object] = {}
        self._build_menu()
        self.activated.connect(self._on_activated)

    # ── 菜单 ──
    def _build_menu(self) -> None:
        self._menu = QMenu()
        self._zoom_menu = QMenu("倍率预设", self._menu)
        for preset in _ZOOM_PRESETS:
            action = self._zoom_menu.addAction(f"{preset:g}x")
            action.setCheckable(True)
            action.triggered.connect(lambda _checked, p=preset: self.config.set(self.config.zoom, p))
            self._zoom_actions[preset] = action
        self._menu.addMenu(self._zoom_menu)

        self._follow_action = self._menu.addAction("跟随模式")
        self._follow_action.setCheckable(True)
        self._follow_action.toggled.connect(self._on_follow_toggled)

        self._menu.addSeparator()
        self._menu.addAction("设置…", self._on_open_settings)
        self._menu.addAction("退出", self._quit)

        # 打开前刷新勾选状态
        self._menu.aboutToShow.connect(self._refresh_checks)
        self.setContextMenu(self._menu)

    def _refresh_checks(self) -> None:
        zoom = float(self.config.zoom.value)
        for preset, action in self._zoom_actions.items():
            action.setChecked(abs(preset - zoom) < 1e-6)
        self._follow_action.blockSignals(True)
        self._follow_action.setChecked(self.magnifier.is_persistent)
        self._follow_action.blockSignals(False)

    def _on_follow_toggled(self, checked: bool) -> None:
        self.magnifier.set_persistent(checked)

    def _on_open_settings(self) -> None:
        self._on_open_settings()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.magnifier.set_persistent(not self.magnifier.is_persistent)

    def _quit(self) -> None:
        QApplication.quit()
