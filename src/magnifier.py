"""圆形放大镜窗口：弹性弹出/收回动画、屏幕内容绘制、peek 与常驻跟随。

窗口为无边框置顶透明窗口，鼠标事件穿透；内容每 33ms（约 30fps）重新抓取。
动画通过 progress 属性驱动：pop = OutBack 弹性放大 + 淡入，retract = InCubic 收回。
"""

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen, QCursor
from PyQt6.QtWidgets import QWidget

from src.capturer import Capturer

_ACCENT = QColor("#009faa")


class MagnifierWindow(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.capturer = Capturer()

        self._progress = 0.0          # 动画进度 0..1
        self._source = None           # 最近一次抓取的屏幕 pixmap
        self._persistent = False      # 常驻跟随模式
        self._zoom = 2.5
        self._size = 220
        self._offset = 15

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowTitle("洞见放大镜")

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30fps
        self._timer.timeout.connect(self._tick)

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.finished.connect(self._on_anim_finished)

        self.apply_config()

    # ── 动画属性 ──
    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = pyqtProperty(float, get_progress, set_progress)

    # ── 配置 ──
    def apply_config(self) -> None:
        self._zoom = float(self.config.zoom.value)
        self._size = int(self.config.size.value)
        self._offset = int(self.config.offset.value)
        self.setFixedSize(self._size, self._size)

    # ── 显示控制 ──
    def pop(self) -> None:
        """弹出放大镜并开始跟随（peek 与常驻共用）。"""
        self._move_to_cursor()
        self._capture()
        self.show()
        self._start_anim(220, QEasingCurve.Type.OutBack, 1.0)
        self._timer.start()

    def retract(self) -> None:
        """收回放大镜。"""
        if not self.isVisible():
            return
        self._start_anim(150, QEasingCurve.Type.InCubic, 0.0)

    def set_persistent(self, on: bool) -> None:
        """切换常驻跟随模式。"""
        if on == self._persistent:
            return
        self._persistent = on
        if on:
            self.pop()
        else:
            self.retract()

    @property
    def is_persistent(self) -> bool:
        return self._persistent

    # ── 内部 ──
    def _start_anim(self, duration: int, easing: QEasingCurve.Type, end: float) -> None:
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(easing)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        # 仅收回动画结束时隐藏；弹出动画结束保持显示
        if float(self._anim.endValue()) == 0.0:
            self._timer.stop()
            self.hide()
            self._progress = 0.0

    def _move_to_cursor(self) -> None:
        cur = QCursor.pos()
        screen = QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        geo = screen.geometry()
        off = self._offset
        x, y = cur.x() + off, cur.y() + off
        if x + self._size > geo.right():
            x = cur.x() - self._size - off
        if y + self._size > geo.bottom():
            y = cur.y() - self._size - off
        x = max(geo.x(), min(x, geo.right() - self._size + 1))
        y = max(geo.y(), min(y, geo.bottom() - self._size + 1))
        self.move(int(x), int(y))

    def _capture(self) -> None:
        cur = QCursor.pos()
        grab_size = max(16, int(self._size / self._zoom))
        self._source = self.capturer.grab(cur.x(), cur.y(), grab_size)

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._move_to_cursor()
        self._capture()
        self.update()

    # ── 绘制 ──
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        center = QPointF(self._size / 2, self._size / 2)
        eased = max(0.0, min(self._progress, 1.0))
        d = self._size * (0.6 + 0.4 * eased)  # 缩放弹出手感

        if self._source and d > 1:
            path = QPainterPath()
            path.addEllipse(center, d / 2, d / 2)
            painter.save()
            painter.setClipPath(path)
            target = QRectF(center.x() - d / 2, center.y() - d / 2, d, d)
            painter.drawPixmap(target, self._source, QRectF(self._source.rect()))
            painter.restore()

        if self._progress <= 0.02:
            return

        # 主题色圆环
        ring = QPen(QColor(_ACCENT.red(), _ACCENT.green(), _ACCENT.blue(), int(230 * eased)), 3.0)
        painter.setPen(ring)
        painter.drawEllipse(center, d / 2, d / 2)

        # 中心十字准星
        cross = QPen(QColor(_ACCENT.red(), _ACCENT.green(), _ACCENT.blue(), int(180 * eased)), 1.0)
        painter.setPen(cross)
        cx, cy, r, g = center.x(), center.y(), 6.0, 12.0
        painter.drawLine(QPointF(cx - g, cy), QPointF(cx - r, cy))
        painter.drawLine(QPointF(cx + r, cy), QPointF(cx + g, cy))
        painter.drawLine(QPointF(cx, cy - g), QPointF(cx, cy - r))
        painter.drawLine(QPointF(cx, cy + r), QPointF(cx, cy + g))
