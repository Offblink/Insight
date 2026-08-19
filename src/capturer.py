"""屏幕捕获:多屏 clamp + HiDPI 校正。

使用虚拟桌面坐标定位光标所在屏,再以屏幕本地坐标抓取,
修复 v1 只抓主屏的问题。grabWindow 返回带 DPR 的 pixmap,绘制时按逻辑尺寸缩放。
"""

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QGuiApplication, QPixmap


class Capturer:
    """从屏幕抓取以 (cx, cy) 为中心的 grab_size 见方区域(逻辑坐标)。"""

    def grab(self, cx: int, cy: int, grab_size: int) -> QPixmap:
        screen = QGuiApplication.screenAt(QPoint(cx, cy)) or QGuiApplication.primaryScreen()
        geo = screen.geometry()  # 逻辑坐标,副屏可为负

        gx = max(geo.x(), min(cx - grab_size // 2, geo.right() - grab_size + 1))
        gy = max(geo.y(), min(cy - grab_size // 2, geo.bottom() - grab_size + 1))

        # grabWindow 的 x/y 相对屏幕原点,需转本地坐标
        return screen.grabWindow(0, gx - geo.x(), gy - geo.y(), grab_size, grab_size)
