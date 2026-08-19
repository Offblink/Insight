"""系统托盘:图标(运行时绘制)与菜单。

Task 1 仅提供图标与退出;完整菜单在 Task 4 扩展。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

_ACCENT = "#009faa"  # qfluentwidgets 默认主题色


def make_icon(size: int = 64) -> QIcon:
    """运行时绘制放大镜图标(圆环 + 手柄),避免二进制资源文件。"""
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
    """托盘控制器:持有图标与菜单,菜单项在 Task 4 扩展。"""

    def __init__(self, config):
        super().__init__(make_icon())
        self.config = config
        self.setToolTip("洞见 v2 — 圆形鼠标放大镜")
        self._build_menu()

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.addAction("退出", self._quit)
        self.setContextMenu(menu)

    def _quit(self) -> None:
        QApplication.quit()
